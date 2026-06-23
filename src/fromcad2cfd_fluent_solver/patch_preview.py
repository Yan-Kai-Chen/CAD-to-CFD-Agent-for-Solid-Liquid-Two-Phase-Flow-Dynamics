"""Safe preview application for FastFluent solver-plan patches."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from fromcad2cfd_fastcfd.solver_plan_patch import (
    SOLVER_PLAN_PATCH_SCHEMA_VERSION,
    validate_solver_plan_patch,
)

from .solver_plan_v2 import (
    SOLVER_PLAN_V2_SCHEMA_VERSION,
    create_minimal_solver_plan_v2,
    find_dangerous_keys,
    validate_solver_plan_v2,
    write_solver_plan_v2_json,
    write_solver_plan_v2_report,
)


PREVIEW_ONLY_NOTICE = (
    "This is a preview-only Fluent solver plan artifact. It has not launched Fluent and has not modified any Fluent case/data file."
)

ALLOWED_TOP_LEVEL_PATHS = (
    "/runtime",
    "/mesh",
    "/physics",
    "/materials",
    "/boundaries",
    "/numerics",
    "/initialization",
    "/transient",
    "/monitors",
    "/source_terms",
    "/autosave",
    "/postprocessing",
    "/acceptance_criteria",
    "/recovery_policy",
    "/warnings",
    "/blocking_errors",
    "/limitations",
    "/metadata",
)


@dataclass(frozen=True)
class PatchPreviewResult:
    """Result of applying a FastFluent patch to a Solver Plan v2 preview."""

    preview_status: str
    base_plan: dict[str, Any]
    patch: dict[str, Any]
    patched_plan: dict[str, Any]
    applied_operations: list[dict[str, Any]]
    skipped_operations: list[dict[str, Any]]
    warnings: list[str]
    blocking_errors: list[str]
    conflicts: list[dict[str, Any]]
    changed_paths: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "preview_status": self.preview_status,
            "base_plan": deepcopy(self.base_plan),
            "patch": deepcopy(self.patch),
            "patched_plan": deepcopy(self.patched_plan),
            "applied_operations": deepcopy(self.applied_operations),
            "skipped_operations": deepcopy(self.skipped_operations),
            "warnings": list(self.warnings),
            "blocking_errors": list(self.blocking_errors),
            "conflicts": deepcopy(self.conflicts),
            "changed_paths": deepcopy(self.changed_paths),
        }


def apply_solver_plan_patch_preview(base_plan: dict[str, Any], patch: dict[str, Any]) -> PatchPreviewResult:
    """Apply a non-executing FastFluent patch to a Solver Plan v2 preview object."""

    base = deepcopy(base_plan)
    patch_payload = deepcopy(patch)
    patched = deepcopy(base_plan)
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocking_errors: list[str] = []
    conflicts: list[dict[str, Any]] = []
    changed_paths: list[dict[str, Any]] = []

    base_validation = validate_solver_plan_v2(base)
    if not base_validation.is_valid:
        blocking_errors.extend(f"Base plan validation error: {item}" for item in base_validation.blocking_errors)
        conflicts.append(_conflict("base_plan_invalid", "block", "/", "Base Solver Plan v2 is invalid.", [], "Fix the base plan before applying patches."))
        patched = base_validation.normalized_plan
        return _finalize_result(base, patch_payload, patched, applied, skipped, warnings, blocking_errors, conflicts, changed_paths)

    patched = base_validation.normalized_plan
    patch_validation = validate_solver_plan_patch(patch_payload)
    warnings.extend(f"Patch validation warning: {item}" for item in patch_validation.warnings)
    if not patch_validation.passed:
        blocking_errors.extend(f"Patch validation error: {item}" for item in patch_validation.errors)
        conflicts.append(
            _conflict(
                "patch_validation_failed",
                "block",
                "/",
                "FastFluent solver_plan_patch.json failed validation.",
                [],
                "Regenerate or repair the patch artifact before preview.",
            )
        )
        return _finalize_result(base, patch_payload, patched, applied, skipped, warnings, blocking_errors, conflicts, changed_paths)

    if patch_payload.get("status") == "block":
        blocking_errors.extend(str(item) for item in patch_payload.get("blocking_errors", []))

    replace_conflict_paths = _find_replace_conflicts(patch_payload.get("patches", []), conflicts)
    operations = patch_payload.get("patches", [])
    for index, operation in enumerate(operations):
        op = operation.get("op")
        path = operation.get("path")
        value = deepcopy(operation.get("value"))
        reason = str(operation.get("reason") or "")
        evidence_refs = list(operation.get("evidence_refs") or [])
        op_record = {
            "index": index,
            "op": op,
            "path": path,
            "reason": reason,
            "evidence_refs": evidence_refs,
        }

        safety_error = _operation_safety_error(operation)
        if safety_error:
            conflicts.append(_conflict(f"unsafe_operation_{index}", "block", str(path), safety_error, [index], "Remove or rewrite the unsafe patch operation."))
            skipped.append({**op_record, "reason_skipped": safety_error})
            continue

        if op == "replace" and path in replace_conflict_paths:
            message = "Conflicting replace operations target this path; fail-closed preview skipped the path."
            skipped.append({**op_record, "reason_skipped": message})
            continue

        if op == "warn":
            warnings.append(reason or f"Patch warning at {path}.")
            applied.append({**op_record, "action": "warning_added"})
            continue

        if op == "block":
            message = reason or f"Patch block at {path}."
            blocking_errors.append(message)
            conflicts.append(_conflict(f"patch_block_{index}", "block", str(path), message, [index], "Resolve the FastFluent blocking condition before execution planning."))
            applied.append({**op_record, "action": "blocking_error_added"})
            continue

        try:
            old_value, new_value = _apply_mutation(patched, op, str(path), value)
        except ValueError as exc:
            message = str(exc)
            conflicts.append(_conflict(f"apply_failed_{index}", "block", str(path), message, [index], "Review the patch path and target field type."))
            skipped.append({**op_record, "reason_skipped": message})
            continue
        applied.append({**op_record, "action": "applied"})
        if old_value != new_value:
            changed_paths.append(
                {
                    "path": path,
                    "old_value": old_value,
                    "new_value": new_value,
                    "reason": reason,
                    "evidence_refs": evidence_refs,
                    "patch_index": index,
                }
            )

    patched["warnings"] = []
    patched["blocking_errors"] = []
    patched_validation = validate_solver_plan_v2(patched)
    warnings.extend(patched_validation.warnings)
    if not patched_validation.is_valid:
        for error in patched_validation.blocking_errors:
            conflicts.append(
                _conflict(
                    f"patched_plan_invalid_{len(conflicts) + 1}",
                    "block",
                    "/",
                    f"Patched Solver Plan v2 validation error: {error}",
                    [],
                    "Review patch operations and base plan compatibility.",
                )
            )
        blocking_errors.extend(patched_validation.blocking_errors)
    patched = patched_validation.normalized_plan
    return _finalize_result(base, patch_payload, patched, applied, skipped, warnings, blocking_errors, conflicts, changed_paths)


def write_patch_preview_bundle(result: PatchPreviewResult, output_dir: Path) -> None:
    """Write all required preview artifacts."""

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write_json(target / "patched_solver_plan_preview.json", result.patched_plan)
    write_patch_application_report(result, target / "patch_application_report.md")
    write_conflict_report(result, target / "conflict_report.json")
    write_before_after_diff(result, target / "before_after_diff.md")
    write_reviewer_checklist(result, target / "reviewer_checklist.md")


def write_patch_application_report(result: PatchPreviewResult, path: Path) -> None:
    evidence = result.patch.get("evidence", []) if isinstance(result.patch, dict) else []
    lines = [
        "# Fluent Solver Plan v2 Patch Application Report",
        "",
        PREVIEW_ONLY_NOTICE,
        "",
        f"- Case name: `{result.patched_plan.get('case_name')}`",
        f"- Base solver plan status: `{result.base_plan.get('status')}`",
        f"- Patch status: `{result.patch.get('status')}`",
        f"- Preview status: `{result.preview_status}`",
        f"- Applied operations: `{len(result.applied_operations)}`",
        f"- Skipped operations: `{len(result.skipped_operations)}`",
        f"- Warnings: `{len(result.warnings)}`",
        f"- Conflicts: `{len(result.conflicts)}`",
        f"- Blocking errors: `{len(result.blocking_errors)}`",
        "",
        "## Patch Operations",
        "",
        "| # | Op | Path | Action | Evidence | Reason |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    operation_map = {item["index"]: item for item in result.applied_operations}
    skipped_map = {item["index"]: item for item in result.skipped_operations}
    for index, operation in enumerate(result.patch.get("patches", [])):
        action = operation_map.get(index, skipped_map.get(index, {})).get("action", "skipped")
        if index in skipped_map:
            action = "skipped"
        refs = ", ".join(operation.get("evidence_refs") or [])
        lines.append(
            f"| {index} | `{operation.get('op')}` | `{operation.get('path')}` | `{action}` | `{refs}` | {_escape_table(str(operation.get('reason') or ''))} |"
        )
    lines.extend(["", "## Evidence Summary", "", "| Evidence ID | Quantity | Value | Interpretation |", "| --- | --- | --- | --- |"])
    for item in evidence:
        lines.append(
            f"| `{item.get('evidence_id')}` | `{item.get('quantity_name')}` | `{item.get('quantity_value')} {item.get('quantity_units', '')}` | "
            f"{_escape_table(str(item.get('interpretation') or ''))} |"
        )
    lines.extend(["", "## Conflict Summary", ""])
    lines.extend(f"- `{item['severity']}` `{item['path']}`: {item['message']}" for item in result.conflicts) if result.conflicts else lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    limitations = list(result.patch.get("limitations", [])) + list(result.patched_plan.get("limitations", []))
    lines.extend(f"- {item}" for item in _dedupe_preserve_order(limitations)) if limitations else lines.append("- None")
    lines.append("")
    _write_text(path, "\n".join(lines))


def write_conflict_report(result: PatchPreviewResult, path: Path) -> None:
    _write_json(
        path,
        {
            "preview_status": result.preview_status,
            "conflict_count": len(result.conflicts),
            "blocking_error_count": len(result.blocking_errors),
            "conflicts": result.conflicts,
            "blocking_errors": result.blocking_errors,
            "warnings": result.warnings,
        },
    )


def write_before_after_diff(result: PatchPreviewResult, path: Path) -> None:
    lines = [
        "# Fluent Solver Plan v2 Before/After Diff",
        "",
        PREVIEW_ONLY_NOTICE,
        "",
        "| Path | Old value | New value | Reason | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in result.changed_paths:
        lines.append(
            f"| `{item.get('path')}` | `{_json_inline(item.get('old_value'))}` | `{_json_inline(item.get('new_value'))}` | "
            f"{_escape_table(str(item.get('reason') or ''))} | `{', '.join(item.get('evidence_refs') or [])}` |"
        )
    if not result.changed_paths:
        lines.append("| None | None | None | No value changes were applied. | None |")
    lines.append("")
    _write_text(path, "\n".join(lines))


def write_reviewer_checklist(result: PatchPreviewResult, path: Path) -> None:
    required_monitors = [
        monitor.get("name")
        for section in ("global", "wall")
        for monitor in result.patched_plan.get("monitors", {}).get(section, [])
        if isinstance(monitor, dict) and monitor.get("required")
    ]
    lines = [
        "# Fluent Solver Plan v2 Reviewer Checklist",
        "",
        PREVIEW_ONLY_NOTICE,
        "",
        "## Physics",
        "- [ ] Confirm solver type.",
        "- [ ] Confirm transient or steady assumption.",
        "- [ ] Confirm energy equation requirement.",
        "- [ ] Confirm species transport requirement.",
        "- [ ] Confirm multiphase model decision.",
        "- [ ] Confirm turbulence model decision.",
        "",
        "## Materials",
        "- [ ] Confirm material property models.",
        "- [ ] Confirm mixture species.",
        "- [ ] Confirm density model.",
        "- [ ] Confirm viscosity and thermal property assumptions.",
        "",
        "## Boundaries",
        "- [ ] Confirm inlet type and values.",
        "- [ ] Confirm outlet type and backflow settings.",
        "- [ ] Confirm wall thermal boundary condition.",
        "- [ ] Confirm named zones.",
        "",
        "## Numerics",
        "- [ ] Confirm first-order warm-up.",
        "- [ ] Confirm later second-order transition.",
        "- [ ] Confirm pressure-velocity coupling.",
        "- [ ] Confirm source ramp and clamp.",
        "",
        "## Transient Controls",
        "- [ ] Confirm initial time step.",
        "- [ ] Confirm adaptive time stepping.",
        "- [ ] Confirm total simulated time.",
        "- [ ] Confirm checkpoint policy.",
        "",
        "## Monitors",
        "- [ ] Confirm residual targets.",
        "- [ ] Confirm max/min temperature monitors.",
        "- [ ] Confirm species bound monitors.",
        "- [ ] Confirm wall heat transfer monitor.",
        "- [ ] Confirm mass and energy balance monitors.",
    ]
    if required_monitors:
        lines.extend(["", "Required monitor names found in preview:"])
        lines.extend(f"- `{name}`" for name in required_monitors)
    lines.extend(
        [
            "",
            "## Source Terms",
            "- [ ] Confirm source term dimensions.",
            "- [ ] Confirm sign convention.",
            "- [ ] Confirm bounds and NaN guard.",
            "- [ ] Confirm UDF or built-in model strategy.",
            "",
            "## Execution Readiness",
            "- [ ] Confirm mesh quality.",
            "- [ ] Confirm no unresolved boundary zones.",
            "- [ ] Confirm acceptance criteria.",
            "- [ ] Confirm this preview has not executed Fluent.",
            "",
        ]
    )
    _write_text(path, "\n".join(lines))


def create_synthetic_solver_plan_patch(case_name: str = "public_solver_plan_v2_patch_demo") -> dict[str, Any]:
    """Create a small public-safe patch for the convenience demo."""

    return {
        "schema_version": SOLVER_PLAN_PATCH_SCHEMA_VERSION,
        "case_name": case_name,
        "created_by": "fromcad2cfd_fluent_solver_preview_demo",
        "status": "warn",
        "summary": "Synthetic preview-only patch for public Solver Plan v2 receiver demonstration.",
        "evidence": [
            {
                "evidence_id": "synthetic_energy_review",
                "source_module": "fromcad2cfd_fluent_solver.patch_preview",
                "source_artifact": "synthetic_inline_patch",
                "source_schema_version": SOLVER_PLAN_PATCH_SCHEMA_VERSION,
                "source_status": "warn",
                "quantity_name": "energy_equation_review",
                "quantity_value": "required",
                "quantity_units": "review",
                "threshold_or_rule": "thermal cases require explicit reviewer confirmation",
                "interpretation": "Enable energy in the preview so reviewer-facing reports include thermal setup checks.",
                "confidence": "medium",
                "limitations": ["Synthetic evidence only; not derived from a physical FastFluent run."],
            }
        ],
        "patches": [
            {
                "op": "replace",
                "path": "/physics/energy/enabled",
                "value": True,
                "reason": "Synthetic public preview marks the energy equation for reviewer confirmation.",
                "evidence_refs": ["synthetic_energy_review"],
                "confidence": "medium",
                "limitations": ["No Fluent execution is implied."],
            },
            {
                "op": "append_unique",
                "path": "/monitors/global",
                "value": {"name": "max_temperature", "quantity": "temperature", "reduction": "max", "required": True},
                "reason": "Reviewer should inspect maximum temperature in thermal solver plans.",
                "evidence_refs": ["synthetic_energy_review"],
                "confidence": "medium",
                "limitations": [],
            },
            {
                "op": "warn",
                "path": "/physics/energy/enabled",
                "value": "Synthetic patch requires reviewer-owned physics confirmation.",
                "reason": "Synthetic patch requires reviewer-owned physics confirmation.",
                "evidence_refs": ["synthetic_energy_review"],
                "confidence": "medium",
                "limitations": [],
            },
        ],
        "warnings": ["Synthetic public patch used because no FastFluent patch was provided."],
        "blocking_errors": [],
        "limitations": ["Synthetic patch is not physical evidence."],
        "metadata": {"preview_only": True},
    }


def write_plan_v2_patch_preview_demo(*, output_dir: str | Path, patch: str | Path | None = None, case_name: str = "public_solver_plan_v2_patch_demo") -> dict[str, Any]:
    """Write the full public demo tree for the Solver Plan v2 receiver."""

    target = Path(output_dir)
    patch_dir = target / "patch"
    preview_dir = target / "preview"
    target.mkdir(parents=True, exist_ok=True)
    patch_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    base_plan = create_minimal_solver_plan_v2(case_name)
    write_solver_plan_v2_json(base_plan, target / "base_solver_plan_v2.json")
    write_solver_plan_v2_report(base_plan, target / "base_solver_plan_v2_report.md")

    if patch is None:
        patch_payload = create_synthetic_solver_plan_patch(case_name=case_name)
        patch_source = "synthetic_inline_patch"
    else:
        patch_path = Path(patch)
        with open(_windows_long_path(patch_path), "r", encoding="utf-8") as handle:
            patch_payload = json.load(handle)
        patch_source = str(patch_path)
    _write_json(patch_dir / "solver_plan_patch.json", patch_payload)

    preview = apply_solver_plan_patch_preview(base_plan, patch_payload)
    write_patch_preview_bundle(preview, preview_dir)

    return {
        "status": "success" if preview.preview_status != "blocked" else "blocked",
        "preview_status": preview.preview_status,
        "patch_source": patch_source,
        "artifacts": {
            "base_solver_plan_v2": str(target / "base_solver_plan_v2.json"),
            "base_solver_plan_v2_report": str(target / "base_solver_plan_v2_report.md"),
            "solver_plan_patch": str(patch_dir / "solver_plan_patch.json"),
            "patched_solver_plan_preview": str(preview_dir / "patched_solver_plan_preview.json"),
            "patch_application_report": str(preview_dir / "patch_application_report.md"),
            "conflict_report": str(preview_dir / "conflict_report.json"),
            "before_after_diff": str(preview_dir / "before_after_diff.md"),
            "reviewer_checklist": str(preview_dir / "reviewer_checklist.md"),
        },
        "conflict_count": len(preview.conflicts),
        "blocking_error_count": len(preview.blocking_errors),
    }


def _finalize_result(
    base_plan: dict[str, Any],
    patch: dict[str, Any],
    patched_plan: dict[str, Any],
    applied_operations: list[dict[str, Any]],
    skipped_operations: list[dict[str, Any]],
    warnings: list[str],
    blocking_errors: list[str],
    conflicts: list[dict[str, Any]],
    changed_paths: list[dict[str, Any]],
) -> PatchPreviewResult:
    warnings = _dedupe_preserve_order([item for item in warnings if item])
    blocking_errors = _dedupe_preserve_order([item for item in blocking_errors if item])
    preview_status = "blocked" if blocking_errors or any(item.get("severity") == "block" for item in conflicts) else "ready_for_review"
    patched = deepcopy(patched_plan)
    patched["schema_version"] = SOLVER_PLAN_V2_SCHEMA_VERSION
    patched["status"] = "blocked" if preview_status == "blocked" else "ready_for_review"
    patched["warnings"] = warnings
    patched["blocking_errors"] = blocking_errors
    if PREVIEW_ONLY_NOTICE not in patched.get("warnings", []):
        patched["warnings"] = [PREVIEW_ONLY_NOTICE] + list(patched.get("warnings", []))
    metadata = patched.get("metadata", {})
    if isinstance(metadata, dict):
        metadata["patch_preview_status"] = preview_status
        metadata["patch_preview_applied_operations"] = len(applied_operations)
        metadata["patch_preview_conflicts"] = len(conflicts)
        patched["metadata"] = metadata
    return PatchPreviewResult(
        preview_status=preview_status,
        base_plan=deepcopy(base_plan),
        patch=deepcopy(patch),
        patched_plan=patched,
        applied_operations=deepcopy(applied_operations),
        skipped_operations=deepcopy(skipped_operations),
        warnings=warnings,
        blocking_errors=blocking_errors,
        conflicts=deepcopy(conflicts),
        changed_paths=deepcopy(changed_paths),
    )


def _find_replace_conflicts(operations: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> set[str]:
    replace_by_path: dict[str, tuple[Any, list[int]]] = {}
    conflicted: set[str] = set()
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or operation.get("op") != "replace":
            continue
        path = operation.get("path")
        if not isinstance(path, str):
            continue
        value = operation.get("value")
        if path not in replace_by_path:
            replace_by_path[path] = (value, [index])
            continue
        previous_value, indices = replace_by_path[path]
        indices.append(index)
        if previous_value != value:
            conflicted.add(path)
            conflicts.append(
                _conflict(
                    f"conflicting_replace_{len(conflicts) + 1}",
                    "block",
                    path,
                    "Two replace patches target the same path with different values.",
                    indices,
                    "Merge the evidence manually and keep one replacement value.",
                )
            )
    return conflicted


def _operation_safety_error(operation: dict[str, Any]) -> str | None:
    path = operation.get("path")
    value = operation.get("value")
    if operation.get("op") not in {"add", "replace", "append_unique", "warn", "block"}:
        return f"Unsupported patch operation: {operation.get('op')!r}."
    if not isinstance(path, str):
        return "Patch operation path must be a string."
    if not _path_is_allowed(path):
        return f"Patch path is outside Solver Plan v2 allowlist: {path}."
    if path == "/schema_version" or path.startswith("/schema_version/"):
        return "schema_version modification is not allowed."
    components = _path_components(path)
    if not components:
        return f"Unsafe patch path: {path}."
    if path == "/runtime/execution_policy" and value != "preview_only":
        return "runtime.execution_policy must remain preview_only."
    dangerous = find_dangerous_keys(value)
    if dangerous:
        return "Dangerous key names found in patch value: " + ", ".join(dangerous)
    return None


def _apply_mutation(target: dict[str, Any], op: str, path: str, value: Any) -> tuple[Any, Any]:
    parent, leaf = _resolve_parent(target, path)
    if op == "replace":
        old_value = deepcopy(parent.get(leaf))
        parent[leaf] = deepcopy(value)
        return old_value, deepcopy(parent.get(leaf))
    if op == "add":
        old_value = deepcopy(parent.get(leaf))
        if leaf not in parent:
            parent[leaf] = deepcopy(value)
        return old_value, deepcopy(parent.get(leaf))
    if op == "append_unique":
        if leaf not in parent:
            parent[leaf] = []
        if not isinstance(parent[leaf], list):
            raise ValueError(f"append_unique target is not a list: {path}")
        old_value = deepcopy(parent[leaf])
        if not _list_contains(parent[leaf], value):
            parent[leaf].append(deepcopy(value))
        return old_value, deepcopy(parent[leaf])
    raise ValueError(f"Unsupported mutation op: {op}")


def _resolve_parent(target: dict[str, Any], path: str) -> tuple[dict[str, Any], str]:
    components = _path_components(path)
    if not components:
        raise ValueError(f"Unsafe patch path: {path}")
    current: Any = target
    for component in components[:-1]:
        if not isinstance(current, dict):
            raise ValueError(f"Cannot traverse non-object path component: {component}")
        if component not in current:
            current[component] = {}
        current = current[component]
    if not isinstance(current, dict):
        raise ValueError(f"Patch parent path is not an object: {path}")
    return current, components[-1]


def _path_components(path: str) -> list[str]:
    if not path.startswith("/"):
        return []
    components = path.split("/")[1:]
    if not components:
        return []
    if any(component in {"", ".", ".."} or "\\" in component for component in components):
        return []
    return components


def _path_is_allowed(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in ALLOWED_TOP_LEVEL_PATHS)


def _conflict(
    conflict_id: str,
    severity: str,
    path: str,
    message: str,
    patch_indices: list[int],
    recommended_resolution: str,
) -> dict[str, Any]:
    return {
        "conflict_id": conflict_id,
        "severity": severity,
        "path": path,
        "message": message,
        "patch_indices": list(patch_indices),
        "recommended_resolution": recommended_resolution,
    }


def _list_contains(items: list[Any], value: Any) -> bool:
    value_key = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    return any(json.dumps(item, ensure_ascii=True, sort_keys=True, default=str) == value_key for item in items)


def _json_inline(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    if len(text) > 240:
        return text[:237] + "..."
    return text.replace("|", "\\|")


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _dedupe_preserve_order(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        key = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(_windows_long_path(target), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")


def _write_text(path: Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(_windows_long_path(target), "w", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def _windows_long_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved
