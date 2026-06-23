"""Solver-dispatch preflight for FastFluent motion adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .motion import MOTION_EVIDENCE_LEVEL
from .motion_adapter import MOTION_ADAPTER_SCHEMA_VERSION


MOTION_SOLVER_PREFLIGHT_SCHEMA_VERSION = "fastfluent_motion_solver_preflight_v1"
SUPPORTED_SOLVER_FAMILIES = {"steady_incompressible"}
SUPPORTED_EXECUTION_MODES = {"static_grid_motion_evidence", "require_dynamic_mesh", "block_on_motion"}


def run_motion_solver_preflight(
    motion_adapter_file: str | Path,
    output_dir: str | Path,
    *,
    solver_family: str = "steady_incompressible",
    execution_mode: str = "static_grid_motion_evidence",
    case_file: str | Path | None = None,
) -> dict[str, Any]:
    """Validate whether a motion adapter can be attached before solver dispatch."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    adapter_path = Path(motion_adapter_file)
    adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
    result = build_motion_solver_preflight(
        adapter,
        motion_adapter_file=adapter_path,
        solver_family=solver_family,
        execution_mode=execution_mode,
        case_file=case_file,
    )
    artifacts = {
        "motion_solver_preflight": str(root / "preflight.json"),
        "motion_solver_decision": str(root / "decision.md"),
    }
    result["artifacts"] = artifacts
    _write_json(root / "preflight.json", result)
    _write_text(root / "decision.md", motion_solver_preflight_markdown(result))
    return result


def build_motion_solver_preflight(
    motion_adapter: dict[str, Any],
    *,
    motion_adapter_file: str | Path | None = None,
    solver_family: str = "steady_incompressible",
    execution_mode: str = "static_grid_motion_evidence",
    case_file: str | Path | None = None,
) -> dict[str, Any]:
    """Build the in-memory motion solver preflight decision."""

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(motion_adapter, dict):
        errors.append("motion_adapter must be a JSON object.")
        motion_adapter = {}
    if motion_adapter.get("schema_version") != MOTION_ADAPTER_SCHEMA_VERSION:
        errors.append(f"motion_adapter.schema_version must be {MOTION_ADAPTER_SCHEMA_VERSION!r}.")
    adapter_status = motion_adapter.get("status")
    if adapter_status == "failed":
        errors.append("motion adapter status is failed.")
    elif adapter_status == "warning":
        warnings.append("motion adapter reported warnings.")
    elif adapter_status != "passed":
        errors.append("motion adapter status must be passed, warning, or failed.")
    if motion_adapter.get("blocking_errors"):
        errors.extend(str(item) for item in motion_adapter.get("blocking_errors", []))
    warnings.extend(str(item) for item in motion_adapter.get("warnings", []))

    if solver_family not in SUPPORTED_SOLVER_FAMILIES:
        errors.append(f"solver_family {solver_family!r} is not motion-preflight supported.")
    if execution_mode not in SUPPORTED_EXECUTION_MODES:
        errors.append(f"execution_mode {execution_mode!r} is not supported.")

    bindings = motion_adapter.get("bindings", [])
    if not isinstance(bindings, list) or not bindings:
        errors.append("motion adapter must contain at least one binding.")
        bindings = []

    binding_reports = [_validate_binding(item, index) for index, item in enumerate(bindings)]
    for report in binding_reports:
        errors.extend(report["blocking_errors"])
        warnings.extend(report["warnings"])

    active_motion_count = sum(1 for report in binding_reports if report["active_motion"])
    max_motion_courant = max((report["motion_courant"] for report in binding_reports), default=0.0)

    if execution_mode == "require_dynamic_mesh" and active_motion_count:
        errors.append("dynamic mesh execution was requested, but FastFluent has no dynamic-mesh solver route in this stage.")
    if execution_mode == "block_on_motion" and active_motion_count:
        errors.append("active motion is present and execution_mode is block_on_motion.")

    solver_dispatch_allowed = not errors
    status = "failed" if errors else "warning" if warnings else "passed"
    solver_execution_mode = (
        "blocked"
        if not solver_dispatch_allowed
        else "static_grid_with_motion_evidence" if active_motion_count else "static_grid_stationary"
    )
    return {
        "schema_version": MOTION_SOLVER_PREFLIGHT_SCHEMA_VERSION,
        "status": status,
        "solver_dispatch_allowed": solver_dispatch_allowed,
        "evidence_level": MOTION_EVIDENCE_LEVEL,
        "motion_adapter_file": str(motion_adapter_file) if motion_adapter_file else None,
        "case_file": str(case_file) if case_file else None,
        "solver_family": solver_family,
        "requested_execution_mode": execution_mode,
        "solver_execution_mode": solver_execution_mode,
        "active_motion_count": active_motion_count,
        "binding_count": len(binding_reports),
        "max_motion_courant": max_motion_courant,
        "binding_reports": binding_reports,
        "blocking_errors": errors,
        "warnings": warnings,
        "decision": _decision_text(solver_dispatch_allowed, solver_execution_mode, active_motion_count),
        "limitations": [
            "This preflight allows static-grid solver execution with attached motion evidence only.",
            "It does not deform the mesh.",
            "It does not apply time-dependent boundary displacement during the solve.",
            "It blocks requests that require dynamic mesh in the current stage.",
        ],
    }


def motion_solver_preflight_markdown(result: dict[str, Any]) -> str:
    """Render a solver preflight decision report."""

    lines = [
        "# FastFluent Motion Solver Preflight",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Solver dispatch allowed: `{result.get('solver_dispatch_allowed')}`",
        f"- Solver family: `{result.get('solver_family')}`",
        f"- Requested mode: `{result.get('requested_execution_mode')}`",
        f"- Solver execution mode: `{result.get('solver_execution_mode')}`",
        f"- Active motion count: `{result.get('active_motion_count')}`",
        f"- Max motion Courant: `{result.get('max_motion_courant')}`",
        "",
        "## Decision",
        "",
        result.get("decision", ""),
        "",
        "## Bindings",
        "",
        "| Motion | Patch | Status | Active | Motion CFL | Reason |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for item in result.get("binding_reports", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item.get('motion_id')}`",
                    f"`{item.get('patch_name')}`",
                    f"`{item.get('status')}`",
                    f"`{item.get('active_motion')}`",
                    str(item.get("motion_courant")),
                    str(item.get("reason")),
                ]
            )
            + " |"
        )
    if result.get("blocking_errors"):
        lines.extend(["", "## Blocking Errors", ""])
        lines.extend(f"- {item}" for item in result["blocking_errors"])
    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in result["warnings"])
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in result.get("limitations", []))
    lines.append("")
    return "\n".join(lines)


def _validate_binding(binding: Any, index: int) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(binding, dict):
        return {
            "index": index,
            "motion_id": None,
            "patch_name": None,
            "status": "failed",
            "active_motion": False,
            "motion_courant": 0.0,
            "reason": "binding is not an object",
            "blocking_errors": [f"bindings[{index}] must be an object."],
            "warnings": [],
        }
    motion_id = str(binding.get("motion_id") or f"binding_{index}")
    patch_name = str(binding.get("patch_name") or "")
    status = str(binding.get("status") or "")
    if status == "failed":
        errors.append(f"binding {motion_id} status is failed.")
    elif status == "warning":
        warnings.append(f"binding {motion_id} reported warnings.")
    elif status != "passed":
        errors.append(f"binding {motion_id} status must be passed, warning, or failed.")
    if not patch_name:
        errors.append(f"binding {motion_id} has no patch_name.")
    if int(binding.get("node_count") or 0) <= 0:
        errors.append(f"binding {motion_id} has no boundary nodes.")
    if int(binding.get("boundary_element_count") or 0) <= 0:
        errors.append(f"binding {motion_id} has no boundary elements.")
    qoi = binding.get("motion_qoi", {})
    if not isinstance(qoi, dict):
        qoi = {}
        errors.append(f"binding {motion_id} has no motion_qoi object.")
    motion_courant = _float_value(qoi.get("motion_courant"), default=0.0)
    max_speed = _float_value(qoi.get("max_effective_speed_m_s"), default=0.0)
    max_translation = _float_value(qoi.get("max_translation_m"), default=0.0)
    max_angle = _float_value(qoi.get("max_abs_angle_rad"), default=0.0)
    active_motion = max_speed > 0.0 or max_translation > 0.0 or max_angle > 0.0
    reason = "active kinematic motion evidence attached" if active_motion else "stationary or zero-motion evidence attached"
    return {
        "index": index,
        "motion_id": motion_id,
        "patch_name": patch_name,
        "status": "failed" if errors else "warning" if warnings else "passed",
        "active_motion": active_motion,
        "motion_courant": motion_courant,
        "max_effective_speed_m_s": max_speed,
        "max_translation_m": max_translation,
        "max_abs_angle_rad": max_angle,
        "reason": reason,
        "blocking_errors": errors,
        "warnings": warnings,
    }


def _decision_text(solver_dispatch_allowed: bool, solver_execution_mode: str, active_motion_count: int) -> str:
    if not solver_dispatch_allowed:
        return "Solver dispatch is blocked by motion preflight."
    if active_motion_count:
        return (
            "Solver dispatch is allowed only as a static-grid run with attached motion evidence. "
            "No moving mesh or time-dependent boundary displacement is applied."
        )
    return "Solver dispatch is allowed; the attached motion evidence is stationary or zero-motion."


def _float_value(value: Any, *, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    value = float(value)
    return value if value == value and value not in (float("inf"), float("-inf")) else default


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path
