"""Machine-readable FastCFD capability registry."""

from __future__ import annotations

from typing import Any

from .registry import CASE_REGISTRY, COLLISION_REGISTRY, LATTICE_REGISTRY


CAPABILITY_REGISTRY: dict[str, Any] = {
    "backend": "fastcfd",
    "status": "foundation",
    "role": "low-cost preliminary CFD prediction and physics-screening layer before high-fidelity Fluent validation",
    "validation_gates": {
        "semantic_scene_compiler": {
            "status": "implemented",
            "checks": ["case template", "domain size", "cell length", "required zones", "boundary semantics", "obstacle clearance"],
            "entrypoint": "fromcad2cfd fastcfd compile-scene",
        },
        "physics_passport": {
            "status": "implemented",
            "checks": ["density", "viscosity", "Re", "tau/RT", "omega", "lattice Mach", "cell count", "step cadence"],
            "entrypoint": "fromcad2cfd fastcfd validate-job",
        },
        "prediction_report": {
            "status": "implemented",
            "checks": ["physics regime", "expected flow behavior", "numerical trace quality", "design implications", "parameter suggestions"],
            "entrypoint": "fromcad2cfd fastcfd predict-from-output",
        },
        "bounded_parameter_screening": {
            "status": "implemented",
            "checks": ["finite variant count", "velocity sensitivity", "cell-length sensitivity", "physics passport per variant", "ranked candidate list"],
            "entrypoint": "fromcad2cfd fastcfd screen-parameters",
        },
    },
    "allowed_case_templates": {name: case.to_dict() for name, case in CASE_REGISTRY.items()},
    "lattice_sets": list(LATTICE_REGISTRY),
    "collision_models": list(COLLISION_REGISTRY),
    "safe_backends": ["mock", "fastfluent"],
    "disabled_capabilities": [
        "arbitrary_shell",
        "arbitrary_python",
        "arbitrary_cpp_generation",
        "arbitrary_fastfluent_case_path",
        "raw_solver_source_edit_from_mcp",
        "validation_bypass_from_mcp",
        "unbounded_parameter_sweep",
    ],
}


def capability_inventory() -> dict[str, Any]:
    return dict(CAPABILITY_REGISTRY)


def capability_markdown() -> str:
    lines = [
        "# FastCFD Capability Inventory",
        "",
        f"Status: `{CAPABILITY_REGISTRY['status']}`",
        f"Role: {CAPABILITY_REGISTRY['role']}",
        "",
        "## Validation Gates",
        "",
    ]
    for name, info in CAPABILITY_REGISTRY["validation_gates"].items():
        lines.extend(
            [
                f"### `{name}`",
                "",
                f"- Status: `{info['status']}`",
                f"- Entrypoint: `{info['entrypoint']}`",
                f"- Checks: `{', '.join(info['checks'])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Allowed Case Templates",
            "",
        ]
    )
    for name, info in CAPABILITY_REGISTRY["allowed_case_templates"].items():
        lines.extend(
            [
                f"### `{name}`",
                "",
                f"- Status: `{info['status']}`",
                f"- Source asset: `{info['source_asset']}`",
                f"- Lattice: `{info['lattice']}`",
                f"- Boundaries: `{', '.join(info['boundaries'])}`",
                f"- Outputs: `{', '.join(info['outputs'])}`",
                "",
            ]
        )
    lines.extend(["## Disabled Capabilities", ""])
    lines.extend(f"- `{item}`" for item in CAPABILITY_REGISTRY["disabled_capabilities"])
    lines.append("")
    return "\n".join(lines)


def require_case_template(case_type: str) -> dict[str, Any]:
    try:
        return CAPABILITY_REGISTRY["allowed_case_templates"][case_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported FastCFD case template: {case_type}") from exc
