"""Reusable boundary-condition contract checks for FastFluent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BOUNDARY_CONTRACT_SCHEMA_VERSION = "fastfluent_boundary_contract_v1"

SUPPORTED_BOUNDARY_TYPES = {
    "velocity_inlet",
    "mass_flow_inlet",
    "pressure_inlet",
    "pressure_outlet",
    "outflow",
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
INLET_TYPES = {"velocity_inlet", "mass_flow_inlet", "pressure_inlet"}
OUTLET_TYPES = {"pressure_outlet", "outflow", "opening"}
WALL_TYPES = {"wall_no_slip", "wall_slip", "heat_flux_wall", "convective_wall", "temperature_wall"}


def validate_boundary_contract(
    boundary_conditions: dict[str, Any],
    *,
    zones: list[str] | None = None,
) -> dict[str, Any]:
    """Validate a zone-keyed boundary-condition map."""

    errors: list[str] = []
    warnings: list[str] = []
    zone_set = set(zones or [])
    normalized: dict[str, dict[str, Any]] = {}
    type_counts: dict[str, int] = {}
    if not isinstance(boundary_conditions, dict) or not boundary_conditions:
        return {
            "schema_version": BOUNDARY_CONTRACT_SCHEMA_VERSION,
            "status": "failed",
            "boundary_count": 0,
            "type_counts": {},
            "normalized_boundaries": {},
            "errors": ["boundary_conditions must be a non-empty object."],
            "warnings": [],
        }

    for zone, condition in sorted(boundary_conditions.items()):
        if not isinstance(condition, dict):
            errors.append(f"{zone} boundary condition must be an object.")
            continue
        bc_type = condition.get("type")
        if bc_type not in SUPPORTED_BOUNDARY_TYPES:
            errors.append(f"{zone} uses unsupported boundary type: {bc_type}")
            continue
        if zone_set and zone not in zone_set:
            warnings.append(f"{zone} is not listed in the geometry or mesh zones.")
        _validate_required_parameters(zone, condition, errors, warnings)
        normalized[zone] = {"type": bc_type, "parameters": {key: value for key, value in condition.items() if key != "type"}}
        type_counts[bc_type] = type_counts.get(bc_type, 0) + 1

    if not any(item.get("type") in INLET_TYPES for item in boundary_conditions.values() if isinstance(item, dict)):
        warnings.append("No inlet boundary was found.")
    if not any(item.get("type") in OUTLET_TYPES for item in boundary_conditions.values() if isinstance(item, dict)):
        warnings.append("No outlet boundary was found.")

    periodic_boundaries = {zone: condition for zone, condition in boundary_conditions.items() if isinstance(condition, dict) and condition.get("type") == "periodic"}
    for zone, condition in periodic_boundaries.items():
        paired = condition.get("paired_zone")
        if not isinstance(paired, str) or not paired:
            errors.append(f"{zone} periodic boundary requires paired_zone.")
        elif paired not in periodic_boundaries:
            errors.append(f"{zone} periodic paired_zone does not reference another periodic boundary: {paired}")

    if type_counts.get("pressure_outlet", 0) > 1:
        warnings.append("Multiple pressure outlets exist; confirm pressure reference handling.")

    return {
        "schema_version": BOUNDARY_CONTRACT_SCHEMA_VERSION,
        "status": "failed" if errors else "passed",
        "boundary_count": len(normalized),
        "type_counts": type_counts,
        "normalized_boundaries": normalized,
        "errors": errors,
        "warnings": warnings,
        "supported_boundary_types": sorted(SUPPORTED_BOUNDARY_TYPES),
    }


def boundary_contract_markdown(report: dict[str, Any]) -> str:
    """Render a boundary-contract report."""

    lines = [
        "# FastFluent Boundary Contract Report",
        "",
        f"Status: `{report.get('status')}`",
        f"Boundary count: `{report.get('boundary_count')}`",
        "",
        "## Boundary Types",
        "",
    ]
    type_counts = report.get("type_counts", {})
    if type_counts:
        lines.extend(f"- `{key}`: `{value}`" for key, value in sorted(type_counts.items()))
    else:
        lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    warnings = report.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Errors", ""])
    errors = report.get("errors", [])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def demo_boundary_conditions() -> dict[str, Any]:
    """Return a public-safe boundary-condition demo."""

    return {
        "inlet": {"type": "velocity_inlet", "velocity_m_s": [1.0, 0.0]},
        "outlet": {"type": "pressure_outlet", "gauge_pressure_pa": 0.0},
        "top_wall": {"type": "wall_no_slip"},
        "bottom_wall": {"type": "wall_no_slip"},
    }


def run_boundary_contract_demo(output_dir: str | Path) -> dict[str, Any]:
    """Write a public boundary-condition contract demo pack."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    zones = ["inlet", "outlet", "top_wall", "bottom_wall", "fluid"]
    boundary_conditions = demo_boundary_conditions()
    report = validate_boundary_contract(boundary_conditions, zones=zones)
    artifacts = {
        "boundary_conditions": str(root / "boundary_conditions.json"),
        "boundary_contract": str(root / "boundary_contract.json"),
        "boundary_validation": str(root / "boundary_validation.md"),
        "fluent_boundary_hints": str(root / "fluent_boundary_hints.json"),
    }
    (root / "boundary_conditions.json").write_text(json.dumps(boundary_conditions, ensure_ascii=True, indent=2), encoding="utf-8")
    (root / "boundary_contract.json").write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    (root / "boundary_validation.md").write_text(boundary_contract_markdown(report), encoding="utf-8")
    (root / "fluent_boundary_hints.json").write_text(json.dumps(_fluent_boundary_hints(report), ensure_ascii=True, indent=2), encoding="utf-8")
    return {"status": "success" if report["status"] == "passed" else "failed", "outputs": {"contract": report, "artifacts": artifacts}}


def _validate_required_parameters(zone: str, condition: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    bc_type = condition.get("type")
    if bc_type == "velocity_inlet" and "velocity_m_s" not in condition:
        errors.append(f"{zone} velocity_inlet requires velocity_m_s.")
    if bc_type == "mass_flow_inlet" and "mass_flow_kg_s" not in condition:
        errors.append(f"{zone} mass_flow_inlet requires mass_flow_kg_s.")
    if bc_type in {"pressure_inlet", "pressure_outlet"} and "gauge_pressure_pa" not in condition and "pressure_pa" not in condition:
        warnings.append(f"{zone} pressure boundary has no explicit pressure value.")
    if bc_type in WALL_TYPES and zone.lower() in {"inlet", "outlet"}:
        warnings.append(f"{zone} is named like a flow opening but uses a wall-type boundary.")


def _fluent_boundary_hints(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "fastfluent_fluent_boundary_hints_v1",
        "status": report.get("status"),
        "hints": [
            {
                "category": "boundary_conditions",
                "recommendation": "Map validated FastFluent boundary types to Fluent boundary zones before solver setup.",
                "evidence": "boundary_contract.json",
            }
        ],
        "limitations": ["This file contains setup hints only and does not edit a Fluent case."],
    }
