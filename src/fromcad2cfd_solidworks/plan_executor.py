from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .connection import connect_solidworks
from .documents import close_document, create_new_part, save_as
from .errors import SolidWorksOperationError
from .geometry import (
    apply_all_edge_chamfer,
    apply_all_edge_fillet,
    apply_shell,
    apply_uniform_scale,
    combine_bodies,
    create_circular_boss,
    create_circular_sweep,
    create_coordinate_system,
    create_loft_between_circles,
    create_offset_rectangle_sketch,
    create_offset_reference_plane,
    create_rectangular_prism,
    create_reference_axis_from_planes,
    create_revolved_boss,
    create_web_rib,
    cut_counterbore_hole,
    cut_circular_hole,
    cut_hole_grid,
    delete_or_keep_body,
    mirror_body_across_plane,
    move_copy_body,
    offset_selected_face,
    solid_body_inventory,
    thicken_selected_face,
)
from .inspect_model import document_inventory
from .paths import is_under_workspace, project_output_dir, project_reports_dir, require_under_workspace, timestamp, unique_path
from .rebuild import rebuild_document
from .reports import write_json_report, write_markdown_report


PLAN_SCHEMA_VERSION = "fromcad2cfd_solidworks_plan_v1"


OperationCallable = Callable[..., dict[str, Any]]


SUPPORTED_OPERATIONS: dict[str, OperationCallable] = {
    "apply_all_edge_chamfer": apply_all_edge_chamfer,
    "apply_all_edge_fillet": apply_all_edge_fillet,
    "apply_shell": apply_shell,
    "apply_uniform_scale": apply_uniform_scale,
    "combine_bodies": combine_bodies,
    "create_circular_boss": create_circular_boss,
    "create_circular_sweep": create_circular_sweep,
    "create_coordinate_system": create_coordinate_system,
    "create_loft_between_circles": create_loft_between_circles,
    "create_offset_rectangle_sketch": create_offset_rectangle_sketch,
    "create_offset_reference_plane": create_offset_reference_plane,
    "create_rectangular_prism": create_rectangular_prism,
    "create_reference_axis_from_planes": create_reference_axis_from_planes,
    "create_revolved_boss": create_revolved_boss,
    "create_web_rib": create_web_rib,
    "cut_counterbore_hole": cut_counterbore_hole,
    "cut_circular_hole": cut_circular_hole,
    "cut_hole_grid": cut_hole_grid,
    "delete_or_keep_body": delete_or_keep_body,
    "mirror_body_across_plane": mirror_body_across_plane,
    "move_copy_body": move_copy_body,
    "offset_selected_face": offset_selected_face,
    "thicken_selected_face": thicken_selected_face,
}


def safe_slug(value: str, default: str = "model") -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._-")
    return slug or default


def _require_project_name(project: str) -> str:
    raw = str(project).strip()
    if not raw:
        raise SolidWorksOperationError("Plan project cannot be empty.")
    project_path = Path(raw)
    if project_path.is_absolute() or ".." in project_path.parts:
        raise SolidWorksOperationError(f"Plan project must be a workspace project name, not a path: {project}")
    return raw


def _load_json_plan(plan_path: Path) -> dict[str, Any]:
    full = require_under_workspace(plan_path)
    if not full.exists():
        raise SolidWorksOperationError(f"Plan file does not exist: {full}")
    if not full.is_file():
        raise SolidWorksOperationError(f"Plan path is not a file: {full}")
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SolidWorksOperationError(f"Plan JSON parse failed at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise SolidWorksOperationError("Plan root must be a JSON object.")
    return data


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    version = plan.get("schema_version")
    if version != PLAN_SCHEMA_VERSION:
        raise SolidWorksOperationError(f"Unsupported plan schema_version: {version!r}; expected {PLAN_SCHEMA_VERSION!r}.")

    project = _require_project_name(str(plan.get("project", "phase5_plan_execution")))
    model_name = safe_slug(str(plan.get("model_name", "solidworks_plan_model")))

    document = plan.get("document") or {}
    if not isinstance(document, dict):
        raise SolidWorksOperationError("Plan document must be an object when provided.")
    doc_type = str(document.get("type", "part")).lower()
    if doc_type != "part":
        raise SolidWorksOperationError(f"Phase5 only supports document.type='part'; got {doc_type!r}.")

    operations = plan.get("operations")
    if not isinstance(operations, list) or not operations:
        raise SolidWorksOperationError("Plan operations must be a non-empty array.")

    seen_ids: set[str] = set()
    normalized_ops: list[dict[str, Any]] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise SolidWorksOperationError(f"Operation {index} must be an object.")
        op_name = str(operation.get("op", "")).strip()
        if op_name not in SUPPORTED_OPERATIONS:
            allowed = ", ".join(sorted(SUPPORTED_OPERATIONS))
            raise SolidWorksOperationError(f"Operation {index} uses unsupported op {op_name!r}. Allowed: {allowed}")
        op_id = safe_slug(str(operation.get("id") or f"{index + 1:03d}_{op_name}"), default=f"op_{index + 1:03d}")
        if op_id in seen_ids:
            raise SolidWorksOperationError(f"Duplicate operation id after normalization: {op_id}")
        seen_ids.add(op_id)
        args = operation.get("args", {})
        if not isinstance(args, dict):
            raise SolidWorksOperationError(f"Operation {op_id} args must be an object.")
        normalized_ops.append(
            {
                "id": op_id,
                "op": op_name,
                "args": args,
                "rebuild": bool(operation.get("rebuild", True)),
                "record_body_inventory": bool(operation.get("record_body_inventory", True)),
            }
        )

    execution = plan.get("execution") or {}
    if not isinstance(execution, dict):
        raise SolidWorksOperationError("Plan execution must be an object when provided.")

    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "project": project,
        "model_name": model_name,
        "description": str(plan.get("description", "")),
        "document": {
            "type": "part",
            "save_part": bool(document.get("save_part", True)),
            "export_step": bool(document.get("export_step", True)),
            "close_document": bool(document.get("close_document", True)),
        },
        "execution": {
            "stop_on_error": bool(execution.get("stop_on_error", True)),
            "visible": bool(execution.get("visible", True)),
        },
        "operations": normalized_ops,
    }


def _operation_step_name(index: int, operation: dict[str, Any]) -> str:
    return f"operation_{index + 1:03d}_{operation['id']}_{operation['op']}"


def execute_plan_file(plan_path: Path, *, visible: bool | None = None) -> dict[str, Any]:
    full_plan_path = require_under_workspace(plan_path)
    stamp = timestamp()
    data: dict[str, Any] = {
        "title": "SolidWorks Agent Phase5 Plan Execution",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "summary": [],
        "steps": [],
        "outputs": {},
        "request": {"plan_path": str(full_plan_path)},
        "plan": None,
        "error": None,
    }

    connection = None
    doc = None
    try:
        raw_plan = _load_json_plan(full_plan_path)
        plan = validate_plan(raw_plan)
        if visible is not None:
            plan["execution"]["visible"] = bool(visible)
        data["plan"] = plan

        project = plan["project"]
        output_dir = project_output_dir(project)
        reports_dir = project_reports_dir(project)
        base = safe_slug(f"fromcad2cfd_solidworks_plan_{plan['model_name']}_{stamp}", default=f"fromcad2cfd_solidworks_plan_{stamp}")
        md_path = unique_path(reports_dir / f"{base}.md")
        json_path = unique_path(reports_dir / f"{base}.json")
        part_path = unique_path(output_dir / f"{base}.SLDPRT")
        step_path = unique_path(output_dir / f"{base}.STEP")
        for candidate in (md_path, json_path, part_path, step_path):
            if not is_under_workspace(candidate):
                raise SolidWorksOperationError(f"Refusing output outside workspace: {candidate}")

        data["outputs"] = {
            "markdown_report": str(md_path),
            "json_report": str(json_path),
            "part": str(part_path),
            "step": str(step_path),
            "project_output_dir": str(output_dir),
        }

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

        doc = create_new_part(connection.app)
        data["steps"].append({"name": "create_new_part", "success": True, "details": document_inventory(doc)})

        failed_ops = 0
        for index, operation in enumerate(plan["operations"]):
            step_name = _operation_step_name(index, operation)
            fn = SUPPORTED_OPERATIONS[operation["op"]]
            try:
                result = fn(doc, **operation["args"])
                details: dict[str, Any] = {"operation": operation, "result": result}
                if operation["rebuild"]:
                    details["rebuild"] = rebuild_document(doc)
                if operation["record_body_inventory"]:
                    details["body_inventory"] = solid_body_inventory(doc)
                data["steps"].append({"name": step_name, "success": True, "details": details})
            except Exception as exc:
                failed_ops += 1
                message = f"{type(exc).__name__}: {exc}"
                data["steps"].append({"name": step_name, "success": False, "message": message, "details": {"operation": operation}})
                if plan["execution"]["stop_on_error"]:
                    raise

        data["steps"].append({"name": "final_inventory", "success": True, "details": document_inventory(doc)})
        data["steps"].append({"name": "final_body_inventory", "success": True, "details": solid_body_inventory(doc)})

        if plan["document"]["save_part"]:
            data["steps"].append({"name": "save_part", "success": True, "details": save_as(doc, part_path)})
        if plan["document"]["export_step"]:
            data["steps"].append({"name": "export_step", "success": True, "details": save_as(doc, step_path)})

        if plan["document"]["close_document"]:
            close_info = close_document(connection.app, doc, save=False)
            data["steps"].append({"name": "close_document", "success": True, "details": close_info})
            doc = None

        success_ops = len(plan["operations"]) - failed_ops
        data["status"] = "success" if failed_ops == 0 else "partial"
        data["summary"] = [
            f"Plan schema: {plan['schema_version']}",
            f"Project: {project}",
            f"Operations run: {len(plan['operations'])}",
            f"Successful operations: {success_ops}",
            f"Failed operations: {failed_ops}",
            f"Part output: {part_path}",
            f"STEP output: {step_path}",
        ]
    except Exception as exc:
        data["status"] = "error"
        data["error"] = f"{type(exc).__name__}: {exc}"
        data["steps"].append({"name": "execute_plan_error", "success": False, "message": data["error"]})
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
        project = "phase5_plan_execution"
        reports_dir = project_reports_dir(project)
        base = f"fromcad2cfd_solidworks_plan_error_{stamp}"
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

