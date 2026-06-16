"""Validated public-safe Fluent Solver plan schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .monitor_contract import GLOBAL_REPORT_DEFS, WALL_REPORT_DEFS, monitor_contract


SOLVER_PLAN_SCHEMA_VERSION = "fromcad2cfd_fluent_solver_plan_v1"
RESUME_PLAN_SCHEMA_VERSION = "fromcad2cfd_fluent_solver_resume_plan_v1"

ALLOWED_SOURCE_MODELS = {
    "none",
    "constant_mass_energy_sink",
    "equivalent_condensation_mass_energy_v1",
    "near_wall_limited_condensation_v1",
}


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def validate_solver_plan(payload: dict[str, Any], *, public_mode: bool = True) -> dict[str, Any]:
    """Validate a public-safe Fluent Solver plan and return a report."""

    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("schema_version") != SOLVER_PLAN_SCHEMA_VERSION:
        errors.append(f"schema_version must be {SOLVER_PLAN_SCHEMA_VERSION}.")
    for key in ("plan_name", "mesh_input", "case_output", "data_output", "physics", "boundaries", "transient"):
        if key not in payload:
            errors.append(f"Missing required key: {key}.")

    for key in ("mesh_input", "case_output", "data_output"):
        if key in payload:
            _validate_public_path(str(payload[key]), key, public_mode, errors)

    physics = payload.get("physics") if isinstance(payload.get("physics"), dict) else {}
    if not physics:
        errors.append("physics must be an object.")
    else:
        if "energy" not in physics:
            errors.append("physics.energy must be specified.")
        if physics.get("species_model") not in {"none", "species-transport", "mixture"}:
            errors.append("physics.species_model must be one of: none, species-transport, mixture.")
        if not isinstance(physics.get("turbulence_model", ""), str):
            errors.append("physics.turbulence_model must be a string.")

    boundaries = payload.get("boundaries") if isinstance(payload.get("boundaries"), dict) else {}
    if not boundaries:
        errors.append("boundaries must be an object keyed by Fluent zone name.")
    else:
        for zone_name, zone in boundaries.items():
            if not isinstance(zone, dict):
                errors.append(f"boundary {zone_name} must be an object.")
                continue
            if "type" not in zone:
                errors.append(f"boundary {zone_name} is missing type.")

    transient = payload.get("transient") if isinstance(payload.get("transient"), dict) else {}
    _validate_transient(transient, errors)

    autosave = payload.get("autosave", {})
    if autosave:
        if not isinstance(autosave, dict):
            errors.append("autosave must be an object.")
        else:
            frequency = autosave.get("data_frequency_steps")
            if frequency is not None and _positive_int(frequency) is None:
                errors.append("autosave.data_frequency_steps must be a positive integer.")

    source_terms = payload.get("source_terms", [])
    if source_terms:
        if not isinstance(source_terms, list):
            errors.append("source_terms must be a list.")
        else:
            for index, source in enumerate(source_terms):
                _validate_source_term(index, source, errors, warnings)

    monitor_errors = _validate_monitor_defs(payload.get("monitors", {}))
    errors.extend(monitor_errors)

    return {
        "status": "passed" if not errors else "failed",
        "schema_version": SOLVER_PLAN_SCHEMA_VERSION,
        "plan_name": payload.get("plan_name"),
        "public_mode": public_mode,
        "errors": errors,
        "warnings": warnings,
        "monitor_contract": monitor_contract(),
    }


def validate_resume_plan(payload: dict[str, Any], *, public_mode: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("schema_version") != RESUME_PLAN_SCHEMA_VERSION:
        errors.append(f"schema_version must be {RESUME_PLAN_SCHEMA_VERSION}.")
    for key in ("resume_name", "case_input", "data_input", "target_flow_time_s", "resume_flow_time_s"):
        if key not in payload:
            errors.append(f"Missing required key: {key}.")
    for key in ("case_input", "data_input"):
        if key in payload:
            _validate_public_path(str(payload[key]), key, public_mode, errors)
    target = _positive_float(payload.get("target_flow_time_s"))
    resume = _positive_float(payload.get("resume_flow_time_s"), allow_zero=True)
    if target is None:
        errors.append("target_flow_time_s must be positive.")
    if resume is None:
        errors.append("resume_flow_time_s must be non-negative.")
    if target is not None and resume is not None and target <= resume:
        errors.append("target_flow_time_s must be greater than resume_flow_time_s.")
    size = payload.get("data_file_size_bytes")
    minimum = payload.get("minimum_expected_data_size_bytes")
    if size is not None and minimum is not None:
        size_int = _positive_int(size)
        min_int = _positive_int(minimum)
        if size_int is None or min_int is None:
            errors.append("data_file_size_bytes and minimum_expected_data_size_bytes must be positive integers.")
        elif size_int < min_int:
            errors.append("data_input appears suspiciously small for the expected checkpoint size.")
    processor_count = payload.get("processor_count")
    if processor_count is not None and _positive_int(processor_count) is None:
        errors.append("processor_count must be a positive integer.")
    if not payload.get("no_standard_initialize", True):
        errors.append("resume plans must not run standard initialization.")
    if payload.get("total_time_is_absolute", True) is not True:
        errors.append("Fluent adaptive resume plans must treat total_time as the absolute target flow time.")
    return {
        "status": "passed" if not errors else "failed",
        "schema_version": RESUME_PLAN_SCHEMA_VERSION,
        "resume_name": payload.get("resume_name"),
        "public_mode": public_mode,
        "errors": errors,
        "warnings": warnings,
    }


def pyfluent_template(plan: dict[str, Any]) -> str:
    """Generate a public-safe PyFluent setup template from a validated plan."""

    validation = validate_solver_plan(plan, public_mode=False)
    if validation["status"] != "passed":
        raise ValueError("Invalid solver plan: " + "; ".join(validation["errors"]))
    lines = [
        "# Generated by FromCAD2CFD. Review before running in a licensed Fluent environment.",
        "# This template intentionally avoids local absolute paths and raw unvalidated commands.",
        "from pathlib import Path",
        "import ansys.fluent.core as pyfluent",
        "",
        f"PLAN_NAME = {plan['plan_name']!r}",
        f"MESH_INPUT = Path({plan['mesh_input']!r})",
        f"CASE_OUTPUT = Path({plan['case_output']!r})",
        f"DATA_OUTPUT = Path({plan['data_output']!r})",
        "",
        "def configure_solver(solver):",
        "    setup = solver.settings.setup",
        "    solution = solver.settings.solution",
        "    # TODO: apply physics, material, boundary, source, monitor, and transient controls.",
        "    # Use the validated JSON plan as the authoritative configuration record.",
        f"    plan = {json.dumps(plan, ensure_ascii=True, indent=4)!r}",
        "    return plan",
        "",
        "def main():",
        "    solver = pyfluent.launch_fluent(mode='solver', ui_mode='no_gui')",
        "    try:",
        "        solver.file.read_mesh(file_name=str(MESH_INPUT))",
        "        configure_solver(solver)",
        "        solver.file.write_case(file_name=str(CASE_OUTPUT))",
        "        solver.file.write_data(file_name=str(DATA_OUTPUT))",
        "    finally:",
        "        solver.exit()",
        "",
        "if __name__ == '__main__':",
        "    main()",
        "",
    ]
    return "\n".join(lines)


def _validate_public_path(path_value: str, field: str, public_mode: bool, errors: list[str]) -> None:
    path = Path(path_value)
    if public_mode and path.is_absolute():
        errors.append(f"{field} must be a relative public path, not an absolute local path.")
    text = path_value.replace("\\", "/").lower()
    private_markers = ["d:/cyk2", "d:\\cyk2", "application_download", "ansys inc", "license"]
    if public_mode and any(marker in text for marker in private_markers):
        errors.append(f"{field} contains a private or local-system path marker.")


def _validate_transient(transient: dict[str, Any], errors: list[str]) -> None:
    if not isinstance(transient, dict) or not transient:
        errors.append("transient must be an object.")
        return
    mode = transient.get("mode")
    if mode not in {"fixed", "adaptive"}:
        errors.append("transient.mode must be fixed or adaptive.")
        return
    if _positive_float(transient.get("total_time_s")) is None:
        errors.append("transient.total_time_s must be positive.")
    if _positive_int(transient.get("max_iterations_per_step")) is None:
        errors.append("transient.max_iterations_per_step must be a positive integer.")
    if mode == "fixed":
        if _positive_float(transient.get("time_step_s")) is None:
            errors.append("fixed transient plans require transient.time_step_s.")
    if mode == "adaptive":
        for key in ("initial_time_step_s", "min_time_step_s", "max_time_step_s", "courant_number"):
            if _positive_float(transient.get(key)) is None:
                errors.append(f"adaptive transient plans require positive transient.{key}.")


def _validate_source_term(index: int, source: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(source, dict):
        errors.append(f"source_terms[{index}] must be an object.")
        return
    model = source.get("source_model", "none")
    if model not in ALLOWED_SOURCE_MODELS:
        errors.append(f"source_terms[{index}].source_model is not an allowed public source model.")
    if "raw_expression" in source:
        errors.append(f"source_terms[{index}] must not contain raw_expression in the public plan.")
    if model != "none" and not source.get("parameters"):
        warnings.append(f"source_terms[{index}] has no parameters; generated templates will be advisory only.")


def _validate_monitor_defs(monitors: Any) -> list[str]:
    errors: list[str] = []
    if not monitors:
        return errors
    if not isinstance(monitors, dict):
        return ["monitors must be an object."]
    global_defs = monitors.get("global", [])
    wall_defs = monitors.get("wall", [])
    if global_defs:
        missing = [item for item in GLOBAL_REPORT_DEFS if item not in global_defs]
        if missing:
            errors.append("monitors.global is missing required definitions: " + ", ".join(missing))
    if wall_defs:
        missing = [item for item in WALL_REPORT_DEFS if item not in wall_defs]
        if missing:
            errors.append("monitors.wall is missing required definitions: " + ", ".join(missing))
    return errors


def _positive_float(value: Any, *, allow_zero: bool = False) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if allow_zero:
        return result if result >= 0 else None
    return result if result > 0 else None


def _positive_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None
