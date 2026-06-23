"""CaseSpec v3 contract for the general FastFluent evidence layer."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


CASE_SPEC_SCHEMA_VERSION = "fastfluent_case_spec_v3"

ALLOWED_CLAIM_LEVELS = {
    "setup_only",
    "screening",
    "native_evidence",
    "fluent_aligned",
    "engineering_candidate",
}
ALLOWED_GEOMETRY_SOURCES = {"analytic", "mesh", "cad_manifest", "none"}
ALLOWED_DIMENSIONS = {"1d", "2d", "3d"}
ALLOWED_MESH_SOURCES = {"structured", "gmsh", "unstructured", "analytic", "none"}
ALLOWED_TIME_MODES = {"steady", "transient"}
ALLOWED_BOUNDARY_TYPES = {
    "velocity_inlet",
    "mass_flow_inlet",
    "pressure_inlet",
    "pressure_outlet",
    "outflow",
    "wall",
    "wall_no_slip",
    "wall_slip",
    "symmetry",
    "periodic",
    "heat_flux_wall",
    "convective_wall",
    "temperature_wall",
    "porous_jump",
    "fan_boundary",
    "source_zone",
    "interface",
    "opening",
}
ALLOWED_CASE_PREFIXES = {
    "flow.",
    "thermal.",
    "scalar.",
    "porous.",
    "rheology.",
    "turbulence.",
    "multiphase_lite.",
    "particle.",
    "handoff.",
    "benchmark.",
}
DANGEROUS_KEYS = {
    "argv",
    "c_code",
    "cmd",
    "command",
    "command_line",
    "cpp_code",
    "delete",
    "eval",
    "exec",
    "executable",
    "journal",
    "python",
    "python_code",
    "raw_pyfluent",
    "raw_tui",
    "remove_file",
    "shell",
    "source_code",
    "subprocess",
    "system",
    "udf_code",
}


@dataclass(frozen=True)
class CaseSpecValidation:
    """Validation result for a CaseSpec v3 document."""

    status: str
    case_id: str | None = None
    claim_level: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unsupported_features: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fastfluent_case_spec_validation_v1",
            "status": self.status,
            "passed": self.passed,
            "case_id": self.case_id,
            "claim_level": self.claim_level,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "unsupported_features": list(self.unsupported_features),
        }


def read_case_spec(path: str | Path) -> dict[str, Any]:
    """Read a CaseSpec v3 JSON file and reject unsafe key names."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    dangerous = find_dangerous_keys(payload)
    if dangerous:
        raise ValueError("Dangerous key names found: " + ", ".join(dangerous))
    return payload


def validate_case_spec(payload: dict[str, Any]) -> CaseSpecValidation:
    """Validate a CaseSpec v3 payload using fail-closed structural checks."""

    errors: list[str] = []
    warnings: list[str] = []
    unsupported: list[str] = []

    if not isinstance(payload, dict):
        return CaseSpecValidation(status="failed", errors=["CaseSpec must be a JSON object."])

    dangerous = find_dangerous_keys(payload)
    if dangerous:
        errors.append("Dangerous key names found: " + ", ".join(dangerous))

    if payload.get("schema_version") != CASE_SPEC_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {payload.get('schema_version')!r}")

    case_id = payload.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        errors.append("case_id must be a non-empty string.")
        case_id = None
    elif any(ch in case_id for ch in "\\/:*?\"<>|"):
        errors.append("case_id must be filesystem-safe.")

    case_type = payload.get("case_type")
    if not isinstance(case_type, str) or not case_type.strip():
        errors.append("case_type must be a non-empty string.")
    elif not any(case_type.startswith(prefix) for prefix in ALLOWED_CASE_PREFIXES):
        unsupported.append(f"Unsupported case_type namespace: {case_type}")

    claim_level = payload.get("claim_level")
    if claim_level not in ALLOWED_CLAIM_LEVELS:
        errors.append(f"claim_level must be one of {sorted(ALLOWED_CLAIM_LEVELS)}.")

    geometry = _require_object(payload, "geometry", errors)
    mesh = _require_object(payload, "mesh", errors)
    materials = _require_object(payload, "materials", errors)
    boundary_conditions = _require_object(payload, "boundary_conditions", errors)
    numerics = _require_object(payload, "numerics", errors)
    handoff = _optional_object(payload, "handoff", errors)

    if geometry is not None:
        _validate_geometry(geometry, errors, warnings)
    if mesh is not None:
        _validate_mesh(mesh, errors, warnings)
    if materials is not None:
        _validate_materials(materials, errors, warnings)
    if boundary_conditions is not None:
        _validate_boundary_conditions(boundary_conditions, errors, warnings, unsupported)
        if geometry is not None:
            _validate_boundary_zones_against_geometry(geometry, boundary_conditions, warnings)
    if numerics is not None:
        _validate_numerics(numerics, errors, warnings)
    if handoff is not None:
        _validate_handoff(handoff, errors)

    qoi_targets = payload.get("qoi_targets")
    if not isinstance(qoi_targets, list) or not all(isinstance(item, str) and item for item in qoi_targets):
        errors.append("qoi_targets must be a list of non-empty strings.")

    return CaseSpecValidation(
        status="failed" if errors else "passed",
        case_id=case_id,
        claim_level=claim_level if isinstance(claim_level, str) else None,
        errors=errors,
        warnings=warnings,
        unsupported_features=unsupported,
    )


def explain_case_spec_markdown(payload: dict[str, Any], validation: CaseSpecValidation | None = None) -> str:
    """Render a concise human-readable CaseSpec v3 summary."""

    validation = validation or validate_case_spec(payload)
    geometry = payload.get("geometry") if isinstance(payload.get("geometry"), dict) else {}
    mesh = payload.get("mesh") if isinstance(payload.get("mesh"), dict) else {}
    materials = payload.get("materials") if isinstance(payload.get("materials"), dict) else {}
    boundaries = payload.get("boundary_conditions") if isinstance(payload.get("boundary_conditions"), dict) else {}
    numerics = payload.get("numerics") if isinstance(payload.get("numerics"), dict) else {}
    qoi_targets = payload.get("qoi_targets") if isinstance(payload.get("qoi_targets"), list) else []
    lines = [
        "# FastFluent CaseSpec v3 Summary",
        "",
        f"- Case ID: `{payload.get('case_id')}`",
        f"- Case type: `{payload.get('case_type')}`",
        f"- Claim level: `{payload.get('claim_level')}`",
        f"- Validation: `{validation.status}`",
        "",
        "## Geometry",
        "",
        f"- Source: `{geometry.get('source')}`",
        f"- Dimension: `{geometry.get('dimension')}`",
        f"- Zones: `{', '.join(_zone_names(geometry)) or 'none'}`",
        "",
        "## Mesh",
        "",
        f"- Source: `{mesh.get('source')}`",
        f"- Quality gates: `{sorted((mesh.get('quality_gates') or {}).keys())}`",
        "",
        "## Materials",
        "",
        f"- Material entries: `{', '.join(sorted(materials)) or 'none'}`",
        "",
        "## Boundary Conditions",
        "",
    ]
    for name, spec in sorted(boundaries.items()):
        bc_type = spec.get("type") if isinstance(spec, dict) else "invalid"
        lines.append(f"- `{name}`: `{bc_type}`")
    lines.extend(
        [
            "",
            "## Numerics",
            "",
            f"- Time mode: `{numerics.get('time_mode')}`",
            f"- Solver: `{numerics.get('solver')}`",
            "",
            "## QoI Targets",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in qoi_targets) if qoi_targets else lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in validation.warnings) if validation.warnings else lines.append("- None")
    lines.extend(["", "## Unsupported Features", ""])
    lines.extend(f"- {item}" for item in validation.unsupported_features) if validation.unsupported_features else lines.append("- None")
    lines.extend(["", "## Errors", ""])
    lines.extend(f"- {item}" for item in validation.errors) if validation.errors else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def find_dangerous_keys(obj: Any, path: str = "$") -> list[str]:
    """Return recursive locations whose key names are unsafe for agent-facing artifacts."""

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


def _require_object(payload: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any] | None:
    value = payload.get(key)
    if not isinstance(value, dict) or not value:
        errors.append(f"{key} must be a non-empty object.")
        return None
    return value


def _optional_object(payload: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any] | None:
    value = payload.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object when provided.")
        return None
    return value


def _validate_geometry(geometry: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if geometry.get("source") not in ALLOWED_GEOMETRY_SOURCES:
        errors.append(f"geometry.source must be one of {sorted(ALLOWED_GEOMETRY_SOURCES)}.")
    if geometry.get("dimension") not in ALLOWED_DIMENSIONS:
        errors.append(f"geometry.dimension must be one of {sorted(ALLOWED_DIMENSIONS)}.")
    zones = geometry.get("zones", [])
    if zones and not isinstance(zones, list):
        errors.append("geometry.zones must be a list when provided.")
    if not _zone_names(geometry):
        warnings.append("geometry.zones is empty; boundary-zone cross-checks will be limited.")


def _validate_mesh(mesh: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if mesh.get("source") not in ALLOWED_MESH_SOURCES:
        errors.append(f"mesh.source must be one of {sorted(ALLOWED_MESH_SOURCES)}.")
    for key in ("nx", "ny", "nz"):
        if key in mesh:
            _require_positive_number(mesh[key], f"mesh.{key}", errors)
    quality_gates = mesh.get("quality_gates", {})
    if quality_gates is not None and not isinstance(quality_gates, dict):
        errors.append("mesh.quality_gates must be an object when provided.")
    if mesh.get("source") in {"gmsh", "unstructured"} and not mesh.get("mesh_file"):
        warnings.append("mesh_file is not set for an unstructured mesh source.")


def _validate_materials(materials: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    for name, material in materials.items():
        if not isinstance(material, dict):
            errors.append(f"materials.{name} must be an object.")
            continue
        for key in ("density_kg_m3", "viscosity_pa_s", "thermal_conductivity_w_m_k", "specific_heat_j_kg_k"):
            if key in material:
                _require_positive_number(material[key], f"materials.{name}.{key}", errors)
        if "name" not in material:
            warnings.append(f"materials.{name} has no material name.")


def _validate_boundary_conditions(
    boundary_conditions: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    unsupported: list[str],
) -> None:
    has_inlet = False
    has_outlet = False
    for name, boundary in boundary_conditions.items():
        if not isinstance(boundary, dict):
            errors.append(f"boundary_conditions.{name} must be an object.")
            continue
        bc_type = boundary.get("type")
        if bc_type not in ALLOWED_BOUNDARY_TYPES:
            unsupported.append(f"Unsupported boundary type for {name}: {bc_type}")
        if bc_type in {"velocity_inlet", "mass_flow_inlet", "pressure_inlet"}:
            has_inlet = True
        if bc_type in {"pressure_outlet", "outflow"}:
            has_outlet = True
    if not has_inlet:
        warnings.append("No inlet-like boundary condition was found.")
    if not has_outlet:
        warnings.append("No outlet-like boundary condition was found.")


def _validate_boundary_zones_against_geometry(
    geometry: dict[str, Any],
    boundary_conditions: dict[str, Any],
    warnings: list[str],
) -> None:
    zones = set(_zone_names(geometry))
    if not zones:
        return
    missing = sorted(name for name in boundary_conditions if name not in zones)
    if missing:
        warnings.append("Boundary conditions reference zones not listed in geometry.zones: " + ", ".join(missing))


def _validate_numerics(numerics: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if numerics.get("time_mode") not in ALLOWED_TIME_MODES:
        errors.append(f"numerics.time_mode must be one of {sorted(ALLOWED_TIME_MODES)}.")
    if not isinstance(numerics.get("solver"), str) or not numerics.get("solver"):
        errors.append("numerics.solver must be a non-empty string.")
    if "max_iterations" in numerics:
        _require_positive_number(numerics["max_iterations"], "numerics.max_iterations", errors)
    if "time_step_s" in numerics:
        _require_positive_number(numerics["time_step_s"], "numerics.time_step_s", errors)
    if numerics.get("time_mode") == "transient" and "time_step_s" not in numerics:
        warnings.append("Transient numerics should include time_step_s.")


def _validate_handoff(handoff: dict[str, Any], errors: list[str]) -> None:
    for key in ("generate_fluent_hints", "generate_solver_plan_patch"):
        if key in handoff and not isinstance(handoff[key], bool):
            errors.append(f"handoff.{key} must be boolean when provided.")


def _zone_names(geometry: dict[str, Any]) -> list[str]:
    zones = geometry.get("zones", [])
    names: list[str] = []
    if isinstance(zones, list):
        for item in zones:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
    return names


def _require_positive_number(value: Any, label: str, errors: list[str]) -> None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be numeric when provided.")
        return
    if number <= 0:
        errors.append(f"{label} must be positive when provided.")
