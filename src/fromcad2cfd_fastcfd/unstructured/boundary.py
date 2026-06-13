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

SUPPORTED_BOUNDARY_KINDS = {"velocity_dirichlet", "velocity_profile_dirichlet", "pressure_reference", "no_slip_wall", "symmetry"}


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
    errors = []
    if missing_required:
        errors.append(f"Missing required boundary patches: {', '.join(missing_required)}")
    if missing_conditions:
        errors.append(f"Missing boundary-condition definitions: {', '.join(missing_conditions)}")
    if unsupported:
        errors.append(f"Unsupported boundary-condition kinds: {', '.join(unsupported)}")
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
        "unused_condition_definitions": unused_conditions,
        "blocking_errors": errors,
        "limitations": [
            "This contract is a benchmark gate for controlled unstructured FastFluent routes.",
            "It is not a full Fluent boundary-condition model.",
            "Unsupported or missing required patches block flow benchmark execution.",
        ],
    }
