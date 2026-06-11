from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .connection import connect_solidworks
from .documents import close_document, open_part_document, save_as, save_current
from .errors import SolidWorksOperationError
from .geometry import solid_body_inventory
from .inspect_model import document_inventory
from .paths import project_output_dir, project_reports_dir, require_under_workspace, timestamp, unique_path
from .rebuild import rebuild_document
from .reports import write_json_report, write_markdown_report


SAFE_EDIT_SCHEMA_VERSION = "fromcad2cfd_solidworks_safe_edit_v1"


def _safe_slug(value: str, default: str = "safe_edit") -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._-")
    return slug or default


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _com_get(obj: Any, name: str, *args: Any) -> Any:
    value = getattr(obj, name)
    if args:
        return value(*args)
    if callable(value):
        try:
            return value()
        except Exception:
            return value
    return value


def _short_parameter_name(full_name: str) -> str:
    parts = str(full_name).split("@")
    if len(parts) >= 2:
        return "@".join(parts[:2])
    return full_name


def scan_dimensions(doc: Any, *, feature_limit: int = 300, dimension_limit_per_feature: int = 80) -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = []
    try:
        feature = _com_get(doc, "FirstFeature")
    except Exception:
        feature = None

    feature_index = 0
    while feature is not None and feature_index < feature_limit:
        try:
            feature_name = str(_com_get(feature, "Name"))
        except Exception:
            feature_name = None
        try:
            feature_type = str(_com_get(feature, "GetTypeName2"))
        except Exception:
            feature_type = None

        try:
            display_dimension = _com_get(feature, "GetFirstDisplayDimension")
        except Exception:
            display_dimension = None

        dimension_index = 0
        while display_dimension is not None and dimension_index < dimension_limit_per_feature:
            record: dict[str, Any] = {
                "feature_index": feature_index,
                "feature_name": feature_name,
                "feature_type": feature_type,
                "dimension_index": dimension_index,
            }
            try:
                display_name = _com_get(display_dimension, "GetNameForSelection")
                record["display_name"] = str(display_name) if display_name is not None else None
            except Exception as exc:
                record["display_name_error"] = f"{type(exc).__name__}: {exc}"

            try:
                dim = _com_get(display_dimension, "GetDimension")
                record["dimension_object_available"] = dim is not None
                if dim is not None:
                    try:
                        record["name"] = str(_com_get(dim, "Name"))
                    except Exception as exc:
                        record["name_error"] = f"{type(exc).__name__}: {exc}"
                    try:
                        full_name = str(_com_get(dim, "FullName"))
                        record["full_name"] = full_name
                        record["parameter_name"] = _short_parameter_name(full_name)
                    except Exception as exc:
                        record["full_name_error"] = f"{type(exc).__name__}: {exc}"
                    try:
                        record["system_value_m"] = float(_com_get(dim, "SystemValue"))
                    except Exception as exc:
                        record["system_value_error"] = f"{type(exc).__name__}: {exc}"
                    try:
                        record["value_mm"] = float(_com_get(dim, "Value"))
                    except Exception as exc:
                        record["value_error"] = f"{type(exc).__name__}: {exc}"
            except Exception as exc:
                record["dimension_error"] = f"{type(exc).__name__}: {exc}"

            dimensions.append(record)
            try:
                display_dimension = feature.GetNextDisplayDimension(display_dimension)
            except Exception:
                break
            dimension_index += 1

        try:
            feature = _com_get(feature, "GetNextFeature")
        except Exception:
            break
        feature_index += 1

    return dimensions


def scan_model_for_safe_edit(doc: Any) -> dict[str, Any]:
    return {
        "document": document_inventory(doc),
        "body_inventory": solid_body_inventory(doc),
        "dimensions": scan_dimensions(doc),
    }


def _dimension_matches(record: dict[str, Any], selector: dict[str, Any]) -> bool:
    for key in ("parameter_name", "full_name", "feature_name", "name", "display_name"):
        expected = selector.get(key)
        if expected is not None and str(record.get(key)) != str(expected):
            return False
    contains = selector.get("contains")
    if contains is not None:
        haystack = " ".join(str(record.get(key, "")) for key in ("parameter_name", "full_name", "feature_name", "name", "display_name"))
        if str(contains) not in haystack:
            return False
    return True


def resolve_unique_dimension(dimensions: list[dict[str, Any]], selector: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(selector, dict) or not selector:
        raise SolidWorksOperationError("Dimension selector must be a non-empty object.")
    matches = [record for record in dimensions if _dimension_matches(record, selector)]
    if len(matches) != 1:
        raise SolidWorksOperationError(f"Dimension selector must match exactly one dimension; matched {len(matches)} for selector {selector}")
    return matches[0]


def _target_value_m(edit: dict[str, Any]) -> float:
    if "value_m" in edit:
        return float(edit["value_m"])
    if "value_mm" in edit:
        return float(edit["value_mm"]) / 1000.0
    raise SolidWorksOperationError("set_dimension edit requires value_mm or value_m.")


def apply_dimension_edit(doc: Any, edit: dict[str, Any], dimensions_before: list[dict[str, Any]]) -> dict[str, Any]:
    selector = edit.get("selector")
    if not isinstance(selector, dict):
        raise SolidWorksOperationError("set_dimension edit requires selector object.")
    target = resolve_unique_dimension(dimensions_before, selector)
    parameter_name = target.get("parameter_name")
    if not parameter_name:
        raise SolidWorksOperationError(f"Matched dimension has no parameter_name: {target}")

    target_value_m = _target_value_m(edit)
    parameter = doc.Parameter(str(parameter_name))
    if parameter is None:
        raise SolidWorksOperationError(f"doc.Parameter returned None for {parameter_name}")

    old_value_m = float(_com_get(parameter, "SystemValue"))
    attempts: list[str] = []
    try:
        result = parameter.SetSystemValue3(target_value_m, 0, None)
        new_value_m = float(_com_get(parameter, "SystemValue"))
        return {
            "success": True,
            "method": "Dimension.SetSystemValue3",
            "parameter_name": parameter_name,
            "selector": selector,
            "old_value_m": old_value_m,
            "old_value_mm": old_value_m * 1000.0,
            "new_value_m": new_value_m,
            "new_value_mm": new_value_m * 1000.0,
            "requested_value_m": target_value_m,
            "requested_value_mm": target_value_m * 1000.0,
            "raw_result": result,
            "matched_dimension": target,
        }
    except Exception as exc:
        attempts.append(f"SetSystemValue3: {type(exc).__name__}: {exc}")

    try:
        parameter.SystemValue = target_value_m
        new_value_m = float(_com_get(parameter, "SystemValue"))
        return {
            "success": True,
            "method": "Dimension.SystemValue assignment",
            "parameter_name": parameter_name,
            "selector": selector,
            "old_value_m": old_value_m,
            "old_value_mm": old_value_m * 1000.0,
            "new_value_m": new_value_m,
            "new_value_mm": new_value_m * 1000.0,
            "requested_value_m": target_value_m,
            "requested_value_mm": target_value_m * 1000.0,
            "matched_dimension": target,
            "prior_attempts": attempts,
        }
    except Exception as exc:
        attempts.append(f"SystemValue assignment: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Dimension edit failed. " + " | ".join(attempts))


def validate_safe_edit_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("schema_version") != SAFE_EDIT_SCHEMA_VERSION:
        raise SolidWorksOperationError(f"Unsupported safe-edit schema_version: {plan.get('schema_version')!r}")
    project = str(plan.get("project", "phase6_safe_edit_demo")).strip()
    if not project or Path(project).is_absolute() or ".." in Path(project).parts:
        raise SolidWorksOperationError(f"Safe-edit project must be a workspace project name, not a path: {project}")
    input_file = plan.get("input_file")
    if not input_file:
        raise SolidWorksOperationError("Safe-edit plan requires input_file.")
    input_path = require_under_workspace(Path(str(input_file)))
    if not input_path.exists():
        raise SolidWorksOperationError(f"Safe-edit input file does not exist: {input_path}")
    if input_path.suffix.lower() != ".sldprt":
        raise SolidWorksOperationError(f"Safe-edit input file must be .SLDPRT: {input_path}")

    edits = plan.get("edits")
    if not isinstance(edits, list) or not edits:
        raise SolidWorksOperationError("Safe-edit plan requires a non-empty edits array.")
    normalized_edits: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, edit in enumerate(edits):
        if not isinstance(edit, dict):
            raise SolidWorksOperationError(f"Edit {index} must be an object.")
        edit_type = str(edit.get("type", "")).strip()
        if edit_type != "set_dimension":
            raise SolidWorksOperationError(f"Unsupported safe-edit type {edit_type!r}; only 'set_dimension' is supported in v1.")
        edit_id = _safe_slug(str(edit.get("id") or f"{index + 1:03d}_{edit_type}"))
        if edit_id in seen_ids:
            raise SolidWorksOperationError(f"Duplicate edit id after normalization: {edit_id}")
        seen_ids.add(edit_id)
        normalized_edit = dict(edit)
        normalized_edit["id"] = edit_id
        normalized_edit["type"] = edit_type
        normalized_edits.append(normalized_edit)

    return {
        "schema_version": SAFE_EDIT_SCHEMA_VERSION,
        "project": project,
        "model_name": _safe_slug(str(plan.get("model_name") or input_path.stem)),
        "description": str(plan.get("description", "")),
        "input_file": str(input_path),
        "edits": normalized_edits,
        "execution": {
            "visible": bool((plan.get("execution") or {}).get("visible", False)),
            "stop_on_error": bool((plan.get("execution") or {}).get("stop_on_error", True)),
        },
    }


def execute_safe_edit_plan_file(plan_path: Path, *, visible: bool | None = None) -> dict[str, Any]:
    plan_path = require_under_workspace(plan_path)
    stamp = timestamp()
    data: dict[str, Any] = {
        "title": "SolidWorks Agent Phase6 Safe Existing-Model Edit",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "summary": [],
        "steps": [],
        "outputs": {},
        "request": {"plan_path": str(plan_path)},
        "plan": None,
        "error": None,
    }

    connection = None
    doc = None
    input_hash_before = None
    input_hash_after = None
    try:
        raw_plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if not isinstance(raw_plan, dict):
            raise SolidWorksOperationError("Safe-edit plan root must be a JSON object.")
        plan = validate_safe_edit_plan(raw_plan)
        if visible is not None:
            plan["execution"]["visible"] = bool(visible)
        data["plan"] = plan

        input_path = Path(plan["input_file"])
        input_hash_before = _file_sha256(input_path)
        output_dir = project_output_dir(plan["project"])
        reports_dir = project_reports_dir(plan["project"])
        base = _safe_slug(f"fromcad2cfd_solidworks_safe_edit_{plan['model_name']}_{stamp}")
        copied_part_path = unique_path(output_dir / f"{base}.SLDPRT")
        step_path = unique_path(output_dir / f"{base}.STEP")
        md_path = unique_path(reports_dir / f"{base}.md")
        json_path = unique_path(reports_dir / f"{base}.json")
        data["outputs"] = {
            "input_file": str(input_path),
            "edited_part": str(copied_part_path),
            "step": str(step_path),
            "markdown_report": str(md_path),
            "json_report": str(json_path),
            "project_output_dir": str(output_dir),
        }

        copied_part_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_path, copied_part_path)
        data["steps"].append(
            {
                "name": "copy_input_to_output",
                "success": True,
                "details": {
                    "source": str(input_path),
                    "destination": str(copied_part_path),
                    "source_sha256_before": input_hash_before,
                    "destination_exists": copied_part_path.exists(),
                    "destination_size": copied_part_path.stat().st_size if copied_part_path.exists() else 0,
                },
            }
        )

        connection = connect_solidworks(visible=bool(plan["execution"]["visible"]), allow_launch=True)
        data["steps"].append(
            {
                "name": "connect_solidworks",
                "success": True,
                "details": {
                    "launched_by_agent": connection.launched_by_agent,
                    "attached_to_running_process": connection.attached_to_running_process,
                },
            }
        )

        opened = open_part_document(connection.app, copied_part_path, silent=True)
        doc = opened.pop("doc")
        data["steps"].append({"name": "open_copied_part", "success": True, "details": opened})

        scan_before = scan_model_for_safe_edit(doc)
        data["steps"].append({"name": "scan_before_edit", "success": True, "details": scan_before})

        failed_edits = 0
        for edit in plan["edits"]:
            step_name = f"edit_{edit['id']}_{edit['type']}"
            try:
                dimensions_current = scan_dimensions(doc)
                result = apply_dimension_edit(doc, edit, dimensions_current)
                rebuild = rebuild_document(doc)
                body_inventory = solid_body_inventory(doc)
                data["steps"].append(
                    {
                        "name": step_name,
                        "success": True,
                        "details": {
                            "edit": edit,
                            "result": result,
                            "rebuild": rebuild,
                            "body_inventory": body_inventory,
                        },
                    }
                )
            except Exception as exc:
                failed_edits += 1
                data["steps"].append({"name": step_name, "success": False, "message": f"{type(exc).__name__}: {exc}", "details": {"edit": edit}})
                if plan["execution"]["stop_on_error"]:
                    raise

        scan_after = scan_model_for_safe_edit(doc)
        data["steps"].append({"name": "scan_after_edit", "success": True, "details": scan_after})
        data["steps"].append({"name": "save_edited_copy", "success": True, "details": save_current(doc)})
        data["steps"].append({"name": "export_step", "success": True, "details": save_as(doc, step_path)})

        close_info = close_document(connection.app, doc, save=False)
        data["steps"].append({"name": "close_document", "success": True, "details": close_info})
        doc = None

        input_hash_after = _file_sha256(input_path)
        original_unchanged = input_hash_before == input_hash_after
        data["steps"].append(
            {
                "name": "verify_input_unchanged",
                "success": original_unchanged,
                "details": {
                    "input_file": str(input_path),
                    "sha256_before": input_hash_before,
                    "sha256_after": input_hash_after,
                    "unchanged": original_unchanged,
                },
            }
        )
        if not original_unchanged:
            raise SolidWorksOperationError("Input original changed during safe edit; this violates safe-edit rules.")

        success_edits = len(plan["edits"]) - failed_edits
        data["status"] = "success" if failed_edits == 0 else "partial"
        data["summary"] = [
            f"Safe-edit schema: {SAFE_EDIT_SCHEMA_VERSION}",
            f"Project: {plan['project']}",
            f"Input original: {input_path}",
            f"Edited copy: {copied_part_path}",
            f"Edits run: {len(plan['edits'])}",
            f"Successful edits: {success_edits}",
            f"Failed edits: {failed_edits}",
            f"Input original unchanged: {original_unchanged}",
            f"STEP output: {step_path}",
        ]
    except Exception as exc:
        data["status"] = "error"
        data["error"] = f"{type(exc).__name__}: {exc}"
        data["steps"].append({"name": "safe_edit_error", "success": False, "message": data["error"]})
    finally:
        if doc is not None and connection is not None:
            try:
                close_info = close_document(connection.app, doc, save=False)
                data["steps"].append({"name": "close_document_after_error", "success": True, "details": close_info})
            except Exception as exc:
                data["steps"].append({"name": "close_document_after_error", "success": False, "message": f"{type(exc).__name__}: {exc}"})
        if connection and connection.launched_by_agent:
            try:
                connection.app.ExitApp()
                data["steps"].append({"name": "exit_app_if_launched", "success": True})
            except Exception as exc:
                data["steps"].append({"name": "exit_app_if_launched", "success": False, "message": f"{type(exc).__name__}: {exc}"})

    if not data["outputs"]:
        reports_dir = project_reports_dir("phase6_safe_edit_demo")
        base = f"fromcad2cfd_solidworks_safe_edit_error_{stamp}"
        data["outputs"] = {
            "markdown_report": str(unique_path(reports_dir / f"{base}.md")),
            "json_report": str(unique_path(reports_dir / f"{base}.json")),
        }

    json_written = write_json_report(Path(data["outputs"]["json_report"]), data)
    md_written = write_markdown_report(Path(data["outputs"]["markdown_report"]), data)
    data["outputs"]["json_report"] = str(json_written)
    data["outputs"]["markdown_report"] = str(md_written)
    json_written.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return data

