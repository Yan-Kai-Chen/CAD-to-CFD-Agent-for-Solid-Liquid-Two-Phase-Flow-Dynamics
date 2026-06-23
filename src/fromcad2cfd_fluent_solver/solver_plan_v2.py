"""Preview-only Fluent Solver Plan v2 schema and validation helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


SOLVER_PLAN_V2_SCHEMA_VERSION = "fromcad2cfd_fluent_solver_plan_v2"

ALLOWED_PLAN_STATUSES = {
    "draft",
    "ready_for_review",
    "approved_for_template_generation",
    "blocked",
}
ALLOWED_DIMENSIONS = {"2d", "3d"}
ALLOWED_PRECISIONS = {"single", "double"}
ALLOWED_SOLVER_TYPES = {"pressure-based", "density-based"}
ALLOWED_TIME_MODES = {"steady", "transient"}
ALLOWED_INITIAL_DISCRETIZATION = {
    "first-order-upwind",
    "second-order-upwind",
    "second-order",
    "quick",
    "power-law",
    "review-required",
}
DANGEROUS_KEYS = {
    "shell",
    "command",
    "cmd",
    "executable",
    "subprocess",
    "python",
    "python_code",
    "source_code",
    "cpp_code",
    "c_code",
    "udf_code",
    "delete",
    "remove_file",
    "raw_tui",
    "raw_pyfluent",
    "journal",
    "system",
    "eval",
    "exec",
}
REQUIRED_TOP_LEVEL_KEYS = (
    "schema_version",
    "case_name",
    "status",
    "runtime",
    "mesh",
    "physics",
    "materials",
    "boundaries",
    "numerics",
    "initialization",
    "transient",
    "monitors",
    "source_terms",
    "autosave",
    "postprocessing",
    "acceptance_criteria",
    "recovery_policy",
    "warnings",
    "blocking_errors",
    "limitations",
    "metadata",
)


@dataclass(frozen=True)
class SolverPlanV2ValidationResult:
    """Structured validation result for preview-only solver plans."""

    is_valid: bool
    status: str
    warnings: list[str]
    blocking_errors: list[str]
    normalized_plan: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status,
            "warnings": list(self.warnings),
            "blocking_errors": list(self.blocking_errors),
            "normalized_plan": deepcopy(self.normalized_plan),
        }


def create_minimal_solver_plan_v2(case_name: str) -> dict[str, Any]:
    """Create a public synthetic Fluent Solver Plan v2 preview object."""

    return {
        "schema_version": SOLVER_PLAN_V2_SCHEMA_VERSION,
        "case_name": str(case_name),
        "status": "ready_for_review",
        "runtime": {
            "fluent_version": "review-required",
            "dimension": "3d",
            "precision": "double",
            "processor_count": 1,
            "mode": "solver",
            "execution_policy": "preview_only",
            "working_directory_policy": "relative_or_configured_only",
        },
        "mesh": {
            "mesh_file": None,
            "mesh_source": "review-required",
            "cell_zones": [],
            "face_zones": [],
            "named_zone_contract": [],
            "mesh_quality_requirements": {
                "max_skewness": 0.95,
                "min_orthogonal_quality": 0.01,
                "negative_volume_allowed": False,
            },
        },
        "physics": {
            "solver": {"type": "pressure-based"},
            "time": "transient",
            "energy": {"enabled": False},
            "species_transport": {"enabled": False, "species": []},
            "multiphase": {"enabled": False, "model": None},
            "turbulence": {"model": "laminar", "near_wall_treatment": "review-required"},
            "material_model": "review-required",
            "mixture": {"species": []},
        },
        "materials": {
            "materials": [],
            "mixtures": [],
            "property_models": ["review-required"],
        },
        "boundaries": {
            "boundary_conditions": [],
            "required_boundary_roles": ["inlet", "outlet", "wall"],
            "unresolved_boundaries": [],
        },
        "numerics": {
            "pressure_velocity_coupling": "review-required",
            "initial_discretization": "first-order-upwind",
            "later_discretization": "second-order-upwind-after-stable-warmup",
            "gradient": "least-squares-cell-based",
            "under_relaxation": {},
            "source_term_controls": {"ramping": False, "clamp": False, "nan_guard": True},
        },
        "initialization": {
            "method": "hybrid-or-review-required",
            "initial_fields": {},
            "patch_initialization": [],
            "review_required": True,
        },
        "transient": {
            "initial_time_step_s": None,
            "adaptive_time_step": {"enabled": False, "max_courant_number": None},
            "total_time_s": None,
            "max_time_steps": None,
            "checkpoint_policy": "review-required",
        },
        "monitors": {
            "global": [],
            "wall": [],
            "residuals": {"enabled": True, "targets": {}},
            "mass_balance": {"enabled": False},
            "energy_balance": {"enabled": False},
        },
        "source_terms": {
            "terms": [],
            "source_term_policy": {
                "allow_arbitrary_code": False,
                "allow_arbitrary_udf": False,
                "review_required": True,
            },
        },
        "autosave": {
            "enabled": True,
            "case_interval": "review-required",
            "data_interval": "review-required",
            "checkpoint_on_warning": True,
        },
        "postprocessing": {
            "required_outputs": [],
            "report_definitions": [],
            "export_policy": "preview_only",
        },
        "acceptance_criteria": [],
        "recovery_policy": {
            "enabled": False,
            "policy": "not_implemented_in_this_goal",
            "allowed_actions": [],
        },
        "warnings": [
            "This is a preview-only Fluent solver plan artifact. It has not launched Fluent and has not modified any Fluent case/data file."
        ],
        "blocking_errors": [],
        "limitations": [
            "Reviewer approval is required before any future executable Fluent template generation.",
            "Mesh, materials, boundary values, and time controls remain review-required in this public synthetic plan.",
        ],
        "metadata": {
            "created_by": "fromcad2cfd_fluent_solver",
            "artifact_type": "preview_only_solver_plan_v2",
        },
    }


def validate_solver_plan_v2(plan: dict[str, Any]) -> SolverPlanV2ValidationResult:
    """Validate a preview-only Fluent Solver Plan v2 object."""

    if not isinstance(plan, dict):
        return SolverPlanV2ValidationResult(
            is_valid=False,
            status="failed",
            warnings=[],
            blocking_errors=["Solver Plan v2 payload must be a JSON object."],
            normalized_plan={},
        )

    normalized = deepcopy(plan)
    warnings: list[str] = []
    blocking_errors: list[str] = []

    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in normalized]
    blocking_errors.extend(f"Missing required top-level key: {key}." for key in missing)

    if normalized.get("schema_version") != SOLVER_PLAN_V2_SCHEMA_VERSION:
        blocking_errors.append(f"schema_version must be {SOLVER_PLAN_V2_SCHEMA_VERSION}.")

    case_name = normalized.get("case_name")
    if not isinstance(case_name, str) or not case_name.strip():
        blocking_errors.append("case_name must be a non-empty string.")

    status = normalized.get("status")
    if status not in ALLOWED_PLAN_STATUSES:
        blocking_errors.append("status must be one of: " + ", ".join(sorted(ALLOWED_PLAN_STATUSES)) + ".")
    elif status == "approved_for_template_generation":
        warnings.append("Plan is marked approved_for_template_generation; this goal only produces preview artifacts.")

    dangerous = find_dangerous_keys(normalized)
    if dangerous:
        blocking_errors.append("Dangerous key names found: " + ", ".join(dangerous))

    _validate_runtime(_section(normalized, "runtime", blocking_errors), blocking_errors)
    _validate_mesh(_section(normalized, "mesh", blocking_errors), warnings, blocking_errors)
    _validate_physics(_section(normalized, "physics", blocking_errors), blocking_errors)
    _validate_materials(_section(normalized, "materials", blocking_errors), warnings, blocking_errors)
    _validate_boundaries(_section(normalized, "boundaries", blocking_errors), warnings, blocking_errors)
    _validate_numerics(_section(normalized, "numerics", blocking_errors), blocking_errors)
    _validate_transient(_section(normalized, "transient", blocking_errors), _section(normalized, "physics", blocking_errors), warnings, blocking_errors)
    _validate_monitors(_section(normalized, "monitors", blocking_errors), blocking_errors)
    _validate_source_terms(_section(normalized, "source_terms", blocking_errors), warnings, blocking_errors)
    _validate_recovery_policy(_section(normalized, "recovery_policy", blocking_errors), blocking_errors)
    _validate_postprocessing(_section(normalized, "postprocessing", blocking_errors), blocking_errors)

    for list_key in ("warnings", "blocking_errors", "limitations"):
        if list_key in normalized and not isinstance(normalized[list_key], list):
            blocking_errors.append(f"{list_key} must be a list.")

    normalized_warnings = list(normalized.get("warnings", [])) if isinstance(normalized.get("warnings"), list) else []
    normalized_blocking = list(normalized.get("blocking_errors", [])) if isinstance(normalized.get("blocking_errors"), list) else []
    warnings = _dedupe_preserve_order(normalized_warnings + warnings)
    blocking_errors = _dedupe_preserve_order(normalized_blocking + blocking_errors)

    normalized["warnings"] = warnings
    normalized["blocking_errors"] = blocking_errors
    normalized["status"] = "blocked" if blocking_errors else "ready_for_review"

    return SolverPlanV2ValidationResult(
        is_valid=not blocking_errors,
        status="passed" if not blocking_errors else "failed",
        warnings=warnings,
        blocking_errors=blocking_errors,
        normalized_plan=normalized,
    )


def write_solver_plan_v2_json(plan: dict[str, Any], path: Path) -> None:
    """Validate and write a Solver Plan v2 JSON artifact."""

    validation = validate_solver_plan_v2(plan)
    payload = validation.normalized_plan
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(_windows_long_path(target), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")


def write_solver_plan_v2_report(plan: dict[str, Any], path: Path) -> None:
    """Write a Markdown report for a Solver Plan v2 preview."""

    validation = validate_solver_plan_v2(plan)
    payload = validation.normalized_plan
    lines = [
        "# Fluent Solver Plan v2 Preview Report",
        "",
        "This is a preview-only Fluent solver plan artifact. It has not launched Fluent and has not modified any Fluent case/data file.",
        "",
        f"- Case name: `{payload.get('case_name')}`",
        f"- Schema version: `{payload.get('schema_version')}`",
        f"- Validation status: `{validation.status}`",
        f"- Plan status: `{payload.get('status')}`",
        f"- Execution policy: `{payload.get('runtime', {}).get('execution_policy')}`",
        "",
        "## Physics Summary",
        "",
        f"- Solver: `{payload.get('physics', {}).get('solver', {}).get('type')}`",
        f"- Time: `{payload.get('physics', {}).get('time')}`",
        f"- Energy enabled: `{payload.get('physics', {}).get('energy', {}).get('enabled')}`",
        f"- Species transport enabled: `{payload.get('physics', {}).get('species_transport', {}).get('enabled')}`",
        f"- Turbulence model: `{payload.get('physics', {}).get('turbulence', {}).get('model')}`",
        "",
        "## Review Warnings",
        "",
    ]
    lines.extend(f"- {item}" for item in validation.warnings) if validation.warnings else lines.append("- None")
    lines.extend(["", "## Blocking Errors", ""])
    lines.extend(f"- {item}" for item in validation.blocking_errors) if validation.blocking_errors else lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    limitations = payload.get("limitations", [])
    lines.extend(f"- {item}" for item in limitations) if limitations else lines.append("- None")
    lines.append("")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(_windows_long_path(target), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def find_dangerous_keys(obj: Any, path: str = "$") -> list[str]:
    """Return recursive locations whose key names are forbidden."""

    findings: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}"
            if key_text.lower() in DANGEROUS_KEYS:
                findings.append(next_path)
            findings.extend(find_dangerous_keys(value, next_path))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            findings.extend(find_dangerous_keys(value, f"{path}[{index}]"))
    return findings


def _section(plan: dict[str, Any], key: str, blocking_errors: list[str]) -> dict[str, Any]:
    value = plan.get(key, {})
    if not isinstance(value, dict):
        blocking_errors.append(f"{key} must be an object.")
        return {}
    return value


def _validate_runtime(runtime: dict[str, Any], blocking_errors: list[str]) -> None:
    if runtime.get("dimension") not in ALLOWED_DIMENSIONS:
        blocking_errors.append("runtime.dimension must be 2d or 3d.")
    if runtime.get("precision") not in ALLOWED_PRECISIONS:
        blocking_errors.append("runtime.precision must be single or double.")
    if _positive_int(runtime.get("processor_count")) is None:
        blocking_errors.append("runtime.processor_count must be a positive integer.")
    if runtime.get("execution_policy") != "preview_only":
        blocking_errors.append("runtime.execution_policy must remain preview_only.")


def _validate_mesh(mesh: dict[str, Any], warnings: list[str], blocking_errors: list[str]) -> None:
    if mesh.get("mesh_file") is None:
        warnings.append("mesh.mesh_file is not set; mesh selection remains reviewer-owned.")
    named_zones = mesh.get("named_zone_contract", [])
    if not isinstance(named_zones, list):
        blocking_errors.append("mesh.named_zone_contract must be a list.")
        return
    for index, zone in enumerate(named_zones):
        if not isinstance(zone, dict):
            blocking_errors.append(f"mesh.named_zone_contract[{index}] must be an object.")
            continue
        for field_name in ("name", "type", "role"):
            if not zone.get(field_name):
                blocking_errors.append(f"mesh.named_zone_contract[{index}] is missing {field_name}.")


def _validate_physics(physics: dict[str, Any], blocking_errors: list[str]) -> None:
    solver = physics.get("solver", {})
    if not isinstance(solver, dict) or solver.get("type") not in ALLOWED_SOLVER_TYPES:
        blocking_errors.append("physics.solver.type must be pressure-based or density-based.")
    if physics.get("time") not in ALLOWED_TIME_MODES:
        blocking_errors.append("physics.time must be steady or transient.")
    energy = physics.get("energy", {})
    if not isinstance(energy, dict) or not isinstance(energy.get("enabled"), bool):
        blocking_errors.append("physics.energy.enabled must be a boolean.")
    species_transport = physics.get("species_transport", {})
    if not isinstance(species_transport, dict) or not isinstance(species_transport.get("enabled"), bool):
        blocking_errors.append("physics.species_transport.enabled must be a boolean.")
    mixture = physics.get("mixture", {})
    mixture_species = mixture.get("species") if isinstance(mixture, dict) else None
    if not isinstance(mixture_species, list):
        blocking_errors.append("physics.mixture.species must be a list.")
    if isinstance(species_transport, dict) and species_transport.get("enabled") is True and not mixture_species:
        blocking_errors.append("physics.mixture.species must not be empty when species_transport.enabled is true.")


def _validate_materials(materials: dict[str, Any], warnings: list[str], blocking_errors: list[str]) -> None:
    if not materials.get("materials") and not materials.get("mixtures"):
        warnings.append("materials are incomplete and remain review-required.")
    for key in ("materials", "mixtures", "property_models"):
        if key in materials and not isinstance(materials[key], list):
            blocking_errors.append(f"materials.{key} must be a list.")


def _validate_boundaries(boundaries: dict[str, Any], warnings: list[str], blocking_errors: list[str]) -> None:
    conditions = boundaries.get("boundary_conditions", [])
    if not isinstance(conditions, list):
        blocking_errors.append("boundaries.boundary_conditions must be a list.")
    else:
        for index, condition in enumerate(conditions):
            if not isinstance(condition, dict):
                blocking_errors.append(f"boundaries.boundary_conditions[{index}] must be an object.")
                continue
            for field_name in ("name", "role", "type", "zone_name"):
                if not condition.get(field_name):
                    blocking_errors.append(f"boundaries.boundary_conditions[{index}] is missing {field_name}.")
            if "settings" in condition and not isinstance(condition.get("settings"), dict):
                blocking_errors.append(f"boundaries.boundary_conditions[{index}].settings must be an object.")
    unresolved = boundaries.get("unresolved_boundaries", [])
    if unresolved:
        warnings.append("boundaries.unresolved_boundaries is not empty.")


def _validate_numerics(numerics: dict[str, Any], blocking_errors: list[str]) -> None:
    if numerics.get("initial_discretization") not in ALLOWED_INITIAL_DISCRETIZATION:
        blocking_errors.append("numerics.initial_discretization is not allowlisted.")
    controls = numerics.get("source_term_controls", {})
    if not isinstance(controls, dict):
        blocking_errors.append("numerics.source_term_controls must be an object.")
        return
    for key in ("ramping", "clamp", "nan_guard"):
        if key in controls and not isinstance(controls[key], bool):
            blocking_errors.append(f"numerics.source_term_controls.{key} must be a boolean.")


def _validate_transient(
    transient: dict[str, Any],
    physics: dict[str, Any],
    warnings: list[str],
    blocking_errors: list[str],
) -> None:
    if physics.get("time") == "transient" and _positive_float(transient.get("initial_time_step_s")) is None:
        warnings.append("physics.time is transient but transient.initial_time_step_s is not positive.")
    adaptive = transient.get("adaptive_time_step", {})
    if adaptive and not isinstance(adaptive, dict):
        blocking_errors.append("transient.adaptive_time_step must be an object.")
        return
    if isinstance(adaptive, dict):
        max_cfl = adaptive.get("max_courant_number")
        if max_cfl is not None and _positive_float(max_cfl) is None:
            blocking_errors.append("transient.adaptive_time_step.max_courant_number must be positive if provided.")


def _validate_monitors(monitors: dict[str, Any], blocking_errors: list[str]) -> None:
    for key in ("global", "wall"):
        items = monitors.get(key, [])
        if not isinstance(items, list):
            blocking_errors.append(f"monitors.{key} must be a list.")
            continue
        for index, monitor in enumerate(items):
            if not isinstance(monitor, dict):
                blocking_errors.append(f"monitors.{key}[{index}] must be an object.")
                continue
            for field_name in ("name", "quantity"):
                if not monitor.get(field_name):
                    blocking_errors.append(f"monitors.{key}[{index}] is missing {field_name}.")


def _validate_source_terms(source_terms: dict[str, Any], warnings: list[str], blocking_errors: list[str]) -> None:
    policy = source_terms.get("source_term_policy", {})
    if not isinstance(policy, dict):
        blocking_errors.append("source_terms.source_term_policy must be an object.")
    else:
        if policy.get("allow_arbitrary_code") is not False:
            blocking_errors.append("source_terms.source_term_policy.allow_arbitrary_code must be false.")
        if policy.get("allow_arbitrary_udf") is not False:
            blocking_errors.append("source_terms.source_term_policy.allow_arbitrary_udf must be false.")
    terms = source_terms.get("terms", [])
    if not isinstance(terms, list):
        blocking_errors.append("source_terms.terms must be a list.")
    else:
        for index, term in enumerate(terms):
            if not isinstance(term, dict):
                blocking_errors.append(f"source_terms.terms[{index}] must be an object.")
                continue
            for field_name in ("units", "sign_convention"):
                if field_name not in term:
                    warnings.append(f"source_terms.terms[{index}] should include {field_name}.")


def _validate_recovery_policy(recovery_policy: dict[str, Any], blocking_errors: list[str]) -> None:
    if recovery_policy.get("enabled") not in {False, None}:
        blocking_errors.append("recovery_policy.enabled must remain false in this goal.")
    allowed_actions = recovery_policy.get("allowed_actions", [])
    if allowed_actions:
        blocking_errors.append("recovery_policy.allowed_actions must remain empty in this goal.")


def _validate_postprocessing(postprocessing: dict[str, Any], blocking_errors: list[str]) -> None:
    if postprocessing.get("export_policy") not in {"preview_only", None}:
        blocking_errors.append("postprocessing.export_policy must remain preview_only.")


def _positive_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def _positive_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


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


def _windows_long_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved
