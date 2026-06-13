"""FastCFD registry of allowed solver concepts and case templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CaseTemplate:
    """Agent-visible case template declaration."""

    name: str
    status: str
    source_asset: str
    lattice: str
    boundaries: tuple[str, ...]
    outputs: tuple[str, ...]
    required_zones: tuple[str, ...] = ()
    supported_backends: tuple[str, ...] = ("mock",)
    real_backend: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_asset": self.source_asset,
            "lattice": self.lattice,
            "boundaries": list(self.boundaries),
            "outputs": list(self.outputs),
            "required_zones": list(self.required_zones),
            "supported_backends": list(self.supported_backends),
            "real_backend": self.real_backend,
            "notes": self.notes,
        }


CASE_REGISTRY: dict[str, CaseTemplate] = {
    "cavity2d": CaseTemplate(
        name="cavity2d",
        status="mock_ready_real_backend_supported",
        source_asset="FastFluent examples/cavity2d",
        lattice="D2Q9",
        boundaries=("moving_wall", "no_slip_wall"),
        outputs=(
            "generated.ini",
            "convergence.csv",
            "fastfluent_native_summary.json",
            "fastfluent_native_convergence.csv",
            "qoi.json",
            "field_qoi.json",
            "flow_fingerprint.json",
            "result_manifest.json",
            "fluent_hints.json",
            "VTK XML",
        ),
        required_zones=("fluid", "moving_wall", "stationary_walls"),
        supported_backends=("mock", "fastfluent"),
        real_backend="fastfluent",
    ),
    "channel2d": CaseTemplate(
        name="channel2d",
        status="mock_ready_real_backend_supported",
        source_asset="FastFluent examples/openboundary2d",
        lattice="D2Q9",
        boundaries=("inlet", "outlet", "no_slip_wall"),
        outputs=(
            "generated.ini",
            "fastfluent_native_summary.json",
            "fastfluent_native_convergence.csv",
            "qoi.json",
            "field_qoi.json",
            "flow_fingerprint.json",
            "result_manifest.json",
            "fluent_hints.json",
            "VTK XML",
        ),
        required_zones=("fluid", "inlet", "outlet", "walls"),
        supported_backends=("mock", "fastfluent"),
        real_backend="fastfluent",
        notes="Uses the controlled FastFluent openboundary2d example as the first real inlet/outlet channel route.",
    ),
    "obstacle2d": CaseTemplate(
        name="obstacle2d",
        status="mock_ready_real_backend_supported",
        source_asset="FastFluent generated controlled obstacle2d recipe over openboundary2d",
        lattice="D2Q9",
        boundaries=("inlet", "outlet", "no_slip_wall", "obstacle_wall"),
        outputs=(
            "generated.ini",
            "generated_source.cpp",
            "fastfluent_native_summary.json",
            "fastfluent_native_convergence.csv",
            "qoi.json",
            "field_qoi.json",
            "flow_fingerprint.json",
            "result_manifest.json",
            "fluent_hints.json",
            "VTK XML",
        ),
        required_zones=("fluid", "inlet", "outlet", "walls", "obstacle"),
        supported_backends=("mock", "fastfluent"),
        real_backend="fastfluent",
        notes="Supports controlled circle and rectangle recipe obstacles first; arbitrary CAD rasterization is not part of this gate.",
    ),
    "dambreak2d": CaseTemplate(
        name="dambreak2d",
        status="research_planned",
        source_asset="FastFluent examples/dambreak2d",
        lattice="D2Q9",
        boundaries=("free_surface", "wall"),
        outputs=("free_surface_qoi.json", "fluent_hints.json"),
        required_zones=("fluid", "walls"),
        supported_backends=("mock",),
        notes="Free-surface execution waits until the single-phase scene/registry/passport route is stable.",
    ),
}

LATTICE_REGISTRY: dict[str, dict[str, Any]] = {
    "D2Q9": {"dimension": 2, "status": "implemented", "cs2": 1.0 / 3.0},
    "D3Q19": {"dimension": 3, "status": "planned", "cs2": 1.0 / 3.0},
    "D3Q27": {"dimension": 3, "status": "planned", "cs2": 1.0 / 3.0},
}

BOUNDARY_REGISTRY: dict[str, dict[str, Any]] = {
    "moving_wall": {"status": "implemented", "semantic_zone": "wall"},
    "no_slip_wall": {"status": "implemented", "semantic_zone": "wall"},
    "inlet": {"status": "scene_compile_mock_ready", "semantic_zone": "inlet"},
    "outlet": {"status": "scene_compile_mock_ready", "semantic_zone": "outlet"},
    "obstacle_wall": {"status": "scene_compile_mock_ready", "semantic_zone": "wall"},
    "free_surface": {"status": "research_planned", "semantic_zone": "interface"},
}

COLLISION_REGISTRY: dict[str, dict[str, Any]] = {
    "BGK": {"status": "implemented", "default": True},
    "MRT": {"status": "planned", "default": False},
    "LES_candidate": {"status": "research_planned", "default": False},
}


def registry_inventory() -> dict[str, Any]:
    """Return the full FastCFD source-of-truth registry."""

    return {
        "schema": "fromcad2cfd_fastcfd_registry_v1",
        "cases": {name: case.to_dict() for name, case in CASE_REGISTRY.items()},
        "lattice_sets": LATTICE_REGISTRY,
        "boundary_types": BOUNDARY_REGISTRY,
        "collision_models": COLLISION_REGISTRY,
    }


def registry_markdown() -> str:
    """Return a human-readable registry summary."""

    lines = ["# FastCFD Registry", "", "## Case Templates", ""]
    for name, case in CASE_REGISTRY.items():
        lines.extend(
            [
                f"### `{name}`",
                "",
                f"- Status: `{case.status}`",
                f"- Source asset: `{case.source_asset}`",
                f"- Lattice: `{case.lattice}`",
                f"- Boundaries: `{', '.join(case.boundaries)}`",
                f"- Supported backends: `{', '.join(case.supported_backends)}`",
                f"- Required zones: `{', '.join(case.required_zones)}`",
                "",
            ]
        )
    lines.extend(["## Lattice Sets", ""])
    for name, info in LATTICE_REGISTRY.items():
        lines.append(f"- `{name}`: dimension `{info['dimension']}`, status `{info['status']}`")
    lines.extend(["", "## Boundary Types", ""])
    for name, info in BOUNDARY_REGISTRY.items():
        lines.append(f"- `{name}`: status `{info['status']}`, semantic zone `{info['semantic_zone']}`")
    lines.append("")
    return "\n".join(lines)


def require_case_template(case_type: str) -> CaseTemplate:
    """Return a case declaration or fail with an explicit error."""

    try:
        return CASE_REGISTRY[case_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported FastCFD case template: {case_type}") from exc


def require_backend_for_case(case_type: str, backend: str) -> None:
    """Fail when a backend is not allowed for a case template."""

    case = require_case_template(case_type)
    if backend not in case.supported_backends:
        raise ValueError(f"Backend '{backend}' is not supported for FastCFD case '{case_type}'.")


def require_boundary_type(boundary_type: str) -> None:
    """Fail when a semantic boundary type is unknown."""

    if boundary_type not in BOUNDARY_REGISTRY:
        raise ValueError(f"Unsupported FastCFD boundary type: {boundary_type}")
