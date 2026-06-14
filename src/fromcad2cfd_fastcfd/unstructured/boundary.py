"""Boundary-condition contract for unstructured FastFluent benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .mesh import UnstructuredMesh


BOUNDARY_CONTRACT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_boundary_contract_v1"


@dataclass(frozen=True)
class BoundaryCondition:
    patch: str
    kind: str
    role: str
    parameters: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"patch": self.patch, "kind": self.kind, "role": self.role}
        if self.parameters:
            payload["parameters"] = dict(self.parameters)
        return payload


DEFAULT_BOUNDARY_CONDITIONS = {
    "inlet": BoundaryCondition(patch="inlet", kind="velocity_dirichlet", role="benchmark inlet patch"),
    "outlet": BoundaryCondition(patch="outlet", kind="pressure_reference", role="benchmark outlet patch"),
    "wall": BoundaryCondition(patch="wall", kind="no_slip_wall", role="benchmark wall patch"),
}

SUPPORTED_BOUNDARY_KINDS = {
    "velocity_dirichlet",
    "velocity_profile_dirichlet",
    "velocity_inlet",
    "mass_flow_inlet",
    "pressure_reference",
    "pressure_outlet",
    "outflow",
    "opening",
    "no_slip_wall",
    "symmetry",
}

NUMERIC_PARAMETER_KEYS = {
    "pressure": ("pressure_reference", "pressure_outlet", "opening"),
    "mass_flow_rate": ("mass_flow_inlet",),
    "area": ("mass_flow_inlet",),
}

VECTOR_PARAMETER_KEYS = {
    "velocity": ("velocity_dirichlet", "velocity_inlet", "opening"),
    "normal": ("symmetry",),
}


def boundary_conditions_from_dict(payload: dict[str, Any]) -> dict[str, BoundaryCondition]:
    """Convert a JSON-style boundary-condition map to typed conditions.

    The parser is intentionally conservative. It accepts both:

    ``{"inlet": {"kind": "velocity_inlet", "velocity": [1, 0]}}``

    and:

    ``{"inlet": {"kind": "velocity_inlet", "parameters": {"velocity": [1, 0]}}}``
    """

    conditions: dict[str, BoundaryCondition] = {}
    for patch, raw in payload.items():
        if not isinstance(raw, dict):
            raise ValueError(f"Boundary condition for patch {patch!r} must be an object.")
        kind = raw.get("kind")
        if not isinstance(kind, str) or not kind:
            raise ValueError(f"Boundary condition for patch {patch!r} must include a non-empty kind.")
        role = raw.get("role")
        if role is not None and not isinstance(role, str):
            raise ValueError(f"Boundary condition role for patch {patch!r} must be a string when provided.")
        parameters = dict(raw.get("parameters") or {})
        for key, value in raw.items():
            if key not in {"kind", "role", "parameters"}:
                parameters[key] = value
        conditions[str(patch)] = BoundaryCondition(
            patch=str(patch),
            kind=kind,
            role=role or f"{kind} on {patch}",
            parameters=parameters or None,
        )
    return conditions


def validate_boundary_contract(
    mesh: UnstructuredMesh,
    *,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
    boundary_conditions: dict[str, BoundaryCondition] | None = None,
) -> dict[str, Any]:
    """Validate named boundary patches before any flow benchmark execution."""

    conditions = boundary_conditions or DEFAULT_BOUNDARY_CONDITIONS
    zone_counts = mesh.boundary_zone_counts()
    missing_required = [name for name in required_patches if zone_counts.get(name, 0) <= 0]
    missing_conditions = [name for name in required_patches if name not in conditions]
    unsupported = sorted({condition.kind for condition in conditions.values() if condition.kind not in SUPPORTED_BOUNDARY_KINDS})
    unused_conditions = sorted(name for name in conditions if name not in zone_counts)
    parameter_errors = _validate_condition_parameters(conditions)
    errors = []
    if missing_required:
        errors.append(f"Missing required boundary patches: {', '.join(missing_required)}")
    if missing_conditions:
        errors.append(f"Missing boundary-condition definitions: {', '.join(missing_conditions)}")
    if unsupported:
        errors.append(f"Unsupported boundary-condition kinds: {', '.join(unsupported)}")
    errors.extend(parameter_errors)
    return {
        "schema_version": BOUNDARY_CONTRACT_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "status": "passed" if not errors else "failed",
        "required_patches": list(required_patches),
        "boundary_zone_counts": zone_counts,
        "conditions": {name: conditions[name].to_dict() for name in sorted(conditions) if name in zone_counts or name in required_patches},
        "missing_required_patches": missing_required,
        "missing_condition_definitions": missing_conditions,
        "unsupported_boundary_kinds": unsupported,
        "parameter_errors": parameter_errors,
        "unused_condition_definitions": unused_conditions,
        "blocking_errors": errors,
        "limitations": [
            "This contract is a benchmark gate for controlled unstructured FastFluent routes.",
            "It validates agent-safe boundary metadata but is not a full Fluent boundary-condition model.",
            "Unsupported or missing required patches block flow benchmark execution.",
        ],
    }


def _validate_condition_parameters(conditions: dict[str, BoundaryCondition]) -> list[str]:
    errors: list[str] = []
    for patch, condition in sorted(conditions.items()):
        params = condition.parameters or {}
        if condition.kind == "velocity_inlet":
            if "velocity" not in params:
                errors.append(f"Boundary condition {patch!r} of kind {condition.kind!r} requires a velocity parameter.")
            elif not _is_numeric_vector(params["velocity"], min_length=2, max_length=3):
                errors.append(f"Boundary condition {patch!r} has invalid velocity parameter; expected two or three numbers.")
        if condition.kind == "velocity_dirichlet" and "velocity" in params and not _is_numeric_vector(params["velocity"], min_length=2, max_length=3):
            errors.append(f"Boundary condition {patch!r} has invalid velocity parameter; expected two or three numbers.")
        if condition.kind in {"pressure_reference", "pressure_outlet"}:
            if "pressure" in params and not _is_number(params["pressure"]):
                errors.append(f"Boundary condition {patch!r} has invalid pressure parameter; expected a number.")
        if condition.kind == "mass_flow_inlet":
            if "mass_flow_rate" not in params or not _is_number(params["mass_flow_rate"]):
                errors.append(f"Boundary condition {patch!r} of kind 'mass_flow_inlet' requires numeric mass_flow_rate.")
            if "area" in params and (not _is_number(params["area"]) or float(params["area"]) <= 0.0):
                errors.append(f"Boundary condition {patch!r} has invalid area parameter; expected a positive number.")
        if condition.kind == "opening":
            if "pressure" in params and not _is_number(params["pressure"]):
                errors.append(f"Boundary condition {patch!r} has invalid opening pressure; expected a number.")
            if "velocity" in params and not _is_numeric_vector(params["velocity"], min_length=2, max_length=3):
                errors.append(f"Boundary condition {patch!r} has invalid opening velocity; expected two or three numbers.")
        if condition.kind == "symmetry" and "normal" in params and not _is_numeric_vector(params["normal"], min_length=2, max_length=3):
            errors.append(f"Boundary condition {patch!r} has invalid symmetry normal; expected two or three numbers.")
        for key, kinds in NUMERIC_PARAMETER_KEYS.items():
            if condition.kind in kinds and key in params and not _is_number(params[key]):
                errors.append(f"Boundary condition {patch!r} has invalid {key}; expected a number.")
        for key, kinds in VECTOR_PARAMETER_KEYS.items():
            if condition.kind in kinds and key in params and not _is_numeric_vector(params[key], min_length=2, max_length=3):
                errors.append(f"Boundary condition {patch!r} has invalid {key}; expected two or three numbers.")
    return errors


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_numeric_vector(value: Any, *, min_length: int, max_length: int) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    if not (min_length <= len(value) <= max_length):
        return False
    return all(_is_number(item) for item in value)
