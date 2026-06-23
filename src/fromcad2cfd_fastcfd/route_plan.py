"""Route Plan Compiler for turning M5 route selections into reviewable plans."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any

from .file_io import ensure_dir, path_is_file, read_json_file, write_json_file, write_text_file
from .flow_pack import build_flow_pack
from .physics_validator import CS_LATTICE, MACH_RECOMMENDED_MAX, contract_has_blocking_errors, validate_physics
from .route_selector import select_route
from .schemas import FastCFDJob


ROUTE_PLAN_SCHEMA_VERSION = "fastfluent_route_plan_v1"
ROUTE_PLAN_VALIDATION_SCHEMA_VERSION = "fastfluent_route_plan_validation_v1"

DEFAULT_LBM_KINEMATIC_VISCOSITY_MM2_S = 0.02
DEFAULT_LBM_RELAXATION_TIME = 0.56
DEFAULT_TOTAL_STEPS = 200
DEFAULT_OUTPUT_INTERVAL = 50
DEFAULT_THREAD_NUM = 1


def compile_route_plan(
    route_selection: str | Path,
    *,
    output_dir: str | Path,
    profile: str = "agent",
    materialize_job: bool = True,
) -> dict[str, Any]:
    """Compile a route selection into a concrete pre-execution route plan."""

    selection_path = _resolve_route_selection_path(route_selection)
    selection = _read_json(selection_path)
    root = Path(output_dir)
    ensure_dir(root)
    flow_pack_dir = Path(str(selection.get("source_flow_pack_dir", "")))
    case_payload = _read_json(flow_pack_dir / "case.json")
    route = str(selection.get("recommended_route") or "")
    artifacts: dict[str, str] = {
        "route_plan": str(root / "route_plan.json"),
        "route_plan_report": str(root / "route_plan_report.md"),
        "approval_gate": str(root / "approval_gate.json"),
    }
    warnings: list[str] = []
    errors: list[str] = []
    materialized: dict[str, Any] | None = None

    if materialize_job and route == "native_fastfluent_structured":
        materialized = _materialize_structured_fastfluent_job(case_payload, root=root, profile=profile)
        artifacts.update(materialized.get("artifacts", {}))
        warnings.extend(materialized.get("warnings", []))
        errors.extend(materialized.get("errors", []))
    elif materialize_job:
        warnings.append(f"No job materializer is implemented for route: {route}.")

    approval_gate = _approval_gate(route, materialized, errors, warnings)
    plan = {
        "schema_version": ROUTE_PLAN_SCHEMA_VERSION,
        "status": approval_gate["status"],
        "source_route_selection": str(selection_path),
        "source_flow_pack_dir": str(flow_pack_dir),
        "case_id": selection.get("case_id") or case_payload.get("case_id"),
        "case_type": selection.get("case_type") or case_payload.get("case_type"),
        "recommended_route": route,
        "route_confidence": selection.get("confidence"),
        "plan_kind": "pre_execution_review",
        "steps": _route_steps(route, materialized),
        "materialized_job": materialized,
        "approval_gate": approval_gate,
        "artifacts": artifacts,
        "warnings": warnings,
        "errors": errors,
        "execution_boundary": {
            "compiler_executes_solver": False,
            "compiler_launches_fluent": False,
            "compiler_runs_arbitrary_code": False,
            "run_commands_require_explicit_user_approval": True,
        },
    }
    _write_json(root / "route_plan.json", plan)
    _write_json(root / "approval_gate.json", approval_gate)
    write_text_file(root / "route_plan_report.md", route_plan_markdown(plan))
    return plan


def validate_route_plan(route_plan: str | Path) -> dict[str, Any]:
    """Validate a Route Plan file or directory."""

    path = _resolve_route_plan_path(route_plan)
    if not path_is_file(path):
        return _validation_failed(["route_plan.json is missing."])
    try:
        plan = read_json_file(path)
    except json.JSONDecodeError as exc:
        return _validation_failed([f"route_plan.json is invalid JSON: {exc}"])

    errors: list[str] = []
    warnings: list[str] = []
    if plan.get("schema_version") != ROUTE_PLAN_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {plan.get('schema_version')!r}")
    if plan.get("execution_boundary", {}).get("compiler_executes_solver") is not False:
        errors.append("Route Plan compiler must not claim solver execution.")
    if not isinstance(plan.get("steps"), list) or not plan["steps"]:
        errors.append("steps must be a non-empty list.")
    artifacts = plan.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be an object.")
    else:
        for name in ("route_plan", "route_plan_report", "approval_gate"):
            artifact_path = artifacts.get(name)
            if not isinstance(artifact_path, str) or not path_is_file(artifact_path):
                errors.append(f"Required artifact is missing: {name}")
    materialized = plan.get("materialized_job")
    if isinstance(materialized, dict) and materialized.get("job_path"):
        if not path_is_file(str(materialized["job_path"])):
            errors.append("materialized job_path does not exist.")
        if materialized.get("physics_passport_path") and not path_is_file(str(materialized["physics_passport_path"])):
            errors.append("materialized physics_passport_path does not exist.")
    if plan.get("status") == "blocked":
        warnings.append("Route Plan is blocked by validation or approval-gate checks.")

    status = "failed" if errors else "passed"
    return {
        "schema_version": ROUTE_PLAN_VALIDATION_SCHEMA_VERSION,
        "status": status,
        "passed": status == "passed",
        "plan_status": plan.get("status"),
        "recommended_route": plan.get("recommended_route"),
        "errors": errors,
        "warnings": warnings,
    }


def run_route_plan_demo(output_dir: str | Path) -> dict[str, Any]:
    """Build a public Flow Pack, select a route, and compile an M6 route plan."""

    root = Path(output_dir)
    flow_pack_dir = root / "f"
    route_selection_dir = root / "s"
    build_flow_pack(
        "examples/fastcfd/casespec_v3/channel_flow_case.json",
        output_dir=flow_pack_dir,
        mesh_mode="structured-demo",
    )
    selection = select_route(flow_pack_dir, output_dir=route_selection_dir)
    route_selection_path = Path(selection["artifacts"]["route_selection"])
    plan = compile_route_plan(route_selection_path, output_dir=root / "p")
    result = {
        "status": plan["status"],
        "operation": "route_plan_demo",
        "outputs": {
            "flow_pack_dir": str(flow_pack_dir),
            "route_selection_dir": str(route_selection_dir),
            "route_plan_dir": str(root / "p"),
            "recommended_route": plan.get("recommended_route"),
            "approval_status": plan.get("approval_gate", {}).get("status"),
            "artifacts": {
                "flow_pack": str(flow_pack_dir / "flow_pack.json"),
                "route_selection": str(route_selection_path),
                "route_plan": str(root / "p" / "route_plan.json"),
                "route_plan_report": str(root / "p" / "route_plan_report.md"),
                "approval_gate": str(root / "p" / "approval_gate.json"),
            },
        },
        "errors": plan.get("errors", []),
    }
    _write_json(root / "demo_status.json", result)
    return result


def route_plan_markdown(plan: dict[str, Any]) -> str:
    """Render a route plan report."""

    lines = [
        "# FastFluent Route Plan",
        "",
        f"- Status: `{plan.get('status')}`",
        f"- Case ID: `{plan.get('case_id')}`",
        f"- Case type: `{plan.get('case_type')}`",
        f"- Recommended route: `{plan.get('recommended_route')}`",
        f"- Compiler executes solver: `{plan.get('execution_boundary', {}).get('compiler_executes_solver')}`",
        "",
        "## Steps",
        "",
    ]
    for step in plan.get("steps", []):
        lines.append(f"- `{step.get('id')}`: {step.get('title')} (`{step.get('status')}`)")
    materialized = plan.get("materialized_job") if isinstance(plan.get("materialized_job"), dict) else {}
    if materialized:
        lines.extend(
            [
                "",
                "## Materialized Job",
                "",
                f"- Job path: `{materialized.get('job_path')}`",
                f"- Physics passport: `{materialized.get('physics_passport_path')}`",
                f"- Physics status: `{materialized.get('physics_status')}`",
                f"- Mapping policy: `{materialized.get('mapping_policy')}`",
            ]
        )
    approval = plan.get("approval_gate", {})
    lines.extend(["", "## Approval Gate", ""])
    lines.append(f"- Status: `{approval.get('status')}`")
    for item in approval.get("required_reviews", []):
        lines.append(f"- Review: {item}")
    lines.extend(["", "## Commands After Explicit Approval", ""])
    for item in approval.get("commands_after_approval", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Warnings", ""])
    warnings = plan.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Errors", ""])
    errors = plan.get("errors", [])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def route_plan_validation_markdown(validation: dict[str, Any]) -> str:
    """Render a route plan validation result."""

    lines = [
        "# FastFluent Route Plan Validation",
        "",
        f"- Status: `{validation.get('status')}`",
        f"- Plan status: `{validation.get('plan_status')}`",
        f"- Recommended route: `{validation.get('recommended_route')}`",
        "",
        "## Warnings",
        "",
    ]
    warnings = validation.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Errors", ""])
    errors = validation.get("errors", [])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _materialize_structured_fastfluent_job(case_payload: dict[str, Any], *, root: Path, profile: str) -> dict[str, Any]:
    case_id = _safe_name(str(case_payload.get("case_id") or "flow_pack_case"))
    geometry = case_payload.get("geometry") if isinstance(case_payload.get("geometry"), dict) else {}
    mesh = case_payload.get("mesh") if isinstance(case_payload.get("mesh"), dict) else {}
    parameters = geometry.get("parameters") if isinstance(geometry.get("parameters"), dict) else {}
    length_mm = float(parameters.get("length_m", 1.0)) * 1000.0
    height_mm = float(parameters.get("height_m", 0.1)) * 1000.0
    nx_hint = _positive_int_or_default(mesh.get("nx"), 100)
    ny_hint = _positive_int_or_default(mesh.get("ny"), 20)
    dx = length_mm / nx_hint
    dy = height_mm / ny_hint
    cell_length_mm = max(1e-9, min(dx, dy))
    nx = max(1, int(round(length_mm / cell_length_mm)))
    ny = max(1, int(round(height_mm / cell_length_mm)))
    velocity_mm_s = _safe_lbm_velocity(length_mm=length_mm, nx=nx)
    job_dir = root / "job"
    ensure_dir(job_dir)
    job = FastCFDJob(
        case_type="channel2d",
        backend="fastfluent",
        output_dir=str(root / "planned_run_output"),
        model_name=f"{case_id}_m6_channel2d",
        dimensions={"nx": nx, "ny": ny, "cell_length_mm": cell_length_mm},
        physical_properties={
            "rho_ref_g_per_mm3": 0.001,
            "kinematic_viscosity_mm2_s": DEFAULT_LBM_KINEMATIC_VISCOSITY_MM2_S,
        },
        boundary_conditions={"inlet_velocity_mm_s": velocity_mm_s, "outlet": "pressure_outlet", "walls": ["top", "bottom"]},
        solver_settings={
            "total_steps": DEFAULT_TOTAL_STEPS,
            "output_interval": DEFAULT_OUTPUT_INTERVAL,
            "relaxation_time": DEFAULT_LBM_RELAXATION_TIME,
            "thread_num": DEFAULT_THREAD_NUM,
        },
        metadata={
            "generated_by": "fastfluent_route_plan_v1",
            "source_case_id": str(case_payload.get("case_id") or ""),
            "mapping_policy": "geometry_from_casespec_safe_lbm_starter_physics",
            "source_case_type": str(case_payload.get("case_type") or ""),
            "review_note": "CaseSpec SI physical values are preserved in the route plan mapping summary, but this starter job uses safe LBM scaling.",
        },
    )
    job_path = job.write(job_dir / "job.json")
    physics = validate_physics(job, profile=profile)
    physics_path = _write_json(job_dir / "physics_passport.json", physics.to_dict())
    mapping = {
        "schema_version": "fastfluent_route_plan_job_mapping_v1",
        "case_id": case_payload.get("case_id"),
        "source_geometry": geometry,
        "source_mesh": mesh,
        "source_materials": case_payload.get("materials", {}),
        "source_boundary_conditions": case_payload.get("boundary_conditions", {}),
        "job_dimensions": job.dimensions,
        "job_physical_properties": job.physical_properties,
        "job_boundary_conditions": job.boundary_conditions,
        "mapping_policy": "geometry_from_casespec_safe_lbm_starter_physics",
        "warnings": [
            "This job is a controlled starter scaffold. It is not a direct physical-unit reproduction of the CaseSpec.",
            "Review LBM scaling before executing a real FastFluent run.",
        ],
    }
    mapping_path = _write_json(job_dir / "job_mapping.json", mapping)
    errors: list[str] = []
    if contract_has_blocking_errors(physics):
        errors.append("Materialized job physics passport has blocking errors.")
    return {
        "status": "blocked" if errors else "ready_for_review",
        "job_path": str(job_path),
        "physics_passport_path": str(physics_path),
        "job_mapping_path": str(mapping_path),
        "physics_status": physics.status,
        "mapping_policy": "geometry_from_casespec_safe_lbm_starter_physics",
        "artifacts": {
            "job": str(job_path),
            "physics_passport": str(physics_path),
            "job_mapping": str(mapping_path),
        },
        "warnings": mapping["warnings"],
        "errors": errors,
    }


def _route_steps(route: str, materialized: dict[str, Any] | None) -> list[dict[str, Any]]:
    if route == "native_fastfluent_structured":
        job_path = materialized.get("job_path") if materialized else "<job.json>"
        return [
            {
                "id": "review_route_selection",
                "title": "Review M5 route selection and rationale.",
                "status": "ready",
                "evidence": ["route_selection.json"],
            },
            {
                "id": "review_materialized_job",
                "title": "Review materialized FastCFD job scaffold and mapping policy.",
                "status": "ready" if materialized else "not_materialized",
                "evidence": [str(job_path)],
            },
            {
                "id": "review_physics_passport",
                "title": "Review physics passport before any native run.",
                "status": "ready" if materialized else "not_materialized",
                "evidence": [materialized.get("physics_passport_path", "") if materialized else ""],
            },
            {
                "id": "execute_after_approval",
                "title": "Run the controlled FastFluent job only after explicit approval.",
                "status": "requires_user_approval",
                "evidence": [str(job_path)],
            },
        ]
    return [
        {
            "id": "review_route_selection",
            "title": "Review M5 route selection and route catalog entry.",
            "status": "ready",
            "evidence": ["route_selection.json"],
        },
        {
            "id": "complete_route_specific_adapter",
            "title": f"Use the route-specific adapter for {route}.",
            "status": "manual_review",
            "evidence": [],
        },
    ]


def _approval_gate(route: str, materialized: dict[str, Any] | None, errors: list[str], warnings: list[str]) -> dict[str, Any]:
    commands: list[str] = []
    required_reviews = ["route_selection_report.md", "route_plan_report.md"]
    if materialized and materialized.get("job_path"):
        job_path = str(materialized["job_path"])
        required_reviews.extend(["job.json", "physics_passport.json", "job_mapping.json"])
        commands = [
            f"python -m fromcad2cfd fastcfd validate-job --job-file \"{job_path}\"",
            f"python -m fromcad2cfd fastcfd run-fastfluent-job --job-file \"{job_path}\"",
        ]
    status = "blocked" if errors else ("ready_for_approval" if route == "native_fastfluent_structured" and materialized else "review_only")
    return {
        "schema_version": "fastfluent_route_plan_approval_gate_v1",
        "status": status,
        "route": route,
        "required_reviews": required_reviews,
        "warnings": warnings,
        "blocking_errors": errors,
        "commands_after_approval": commands,
        "approval_required": True,
    }


def _safe_lbm_velocity(*, length_mm: float, nx: int) -> float:
    target_lattice_velocity = MACH_RECOMMENDED_MAX * CS_LATTICE * 0.8
    nu_lattice = (1.0 / 3.0) * (DEFAULT_LBM_RELAXATION_TIME - 0.5)
    cap = target_lattice_velocity * DEFAULT_LBM_KINEMATIC_VISCOSITY_MM2_S * nx / max(length_mm * nu_lattice, 1e-12)
    return max(1e-9, min(0.03, cap))


def _resolve_route_selection_path(route_selection: str | Path) -> Path:
    path = Path(route_selection)
    if path.is_dir():
        return path / "route_selection.json"
    return path


def _resolve_route_plan_path(route_plan: str | Path) -> Path:
    path = Path(route_plan)
    if path.is_dir():
        return path / "route_plan.json"
    return path


def _validation_failed(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": ROUTE_PLAN_VALIDATION_SCHEMA_VERSION,
        "status": "failed",
        "passed": False,
        "errors": errors,
        "warnings": [],
    }


def _positive_int_or_default(value: Any, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _safe_name(text: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", text.strip())
    safe = safe.strip("._-")
    return safe[:80] or "fastfluent_case"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = read_json_file(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return write_json_file(path, payload)
