"""Reusable material-model contract checks for FastFluent."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


MATERIAL_CONTRACT_SCHEMA_VERSION = "fastfluent_material_contract_v1"

SUPPORTED_MATERIAL_TYPES = {
    "constant_fluid",
    "temperature_dependent_fluid",
    "ideal_gas_lite",
    "solid_thermal",
    "porous_medium",
    "non_newtonian_fluid",
    "particle_phase",
    "two_phase_pair",
}


def validate_material_contract(materials: dict[str, Any]) -> dict[str, Any]:
    """Validate a CaseSpec-style material dictionary."""

    errors: list[str] = []
    warnings: list[str] = []
    normalized: dict[str, dict[str, Any]] = {}
    if not isinstance(materials, dict) or not materials:
        return {
            "schema_version": MATERIAL_CONTRACT_SCHEMA_VERSION,
            "status": "failed",
            "material_count": 0,
            "materials": {},
            "errors": ["materials must be a non-empty object."],
            "warnings": [],
        }

    for key, material in sorted(materials.items()):
        if not isinstance(material, dict):
            errors.append(f"materials.{key} must be an object.")
            continue
        material_type = material.get("type") or _infer_material_type(material)
        if material_type not in SUPPORTED_MATERIAL_TYPES:
            errors.append(f"materials.{key} uses unsupported material type: {material_type}")
            continue
        _validate_material_fields(key, material_type, material, errors, warnings)
        normalized[key] = {
            "name": material.get("name") or key,
            "type": material_type,
            "properties": {prop: value for prop, value in material.items() if prop not in {"name", "type"}},
        }

    return {
        "schema_version": MATERIAL_CONTRACT_SCHEMA_VERSION,
        "status": "failed" if errors else "passed",
        "material_count": len(normalized),
        "materials": normalized,
        "errors": errors,
        "warnings": warnings,
        "supported_material_types": sorted(SUPPORTED_MATERIAL_TYPES),
    }


def material_contract_markdown(report: dict[str, Any]) -> str:
    """Render a material-contract report."""

    lines = [
        "# FastFluent Material Contract Report",
        "",
        f"Status: `{report.get('status')}`",
        f"Material count: `{report.get('material_count')}`",
        "",
        "## Materials",
        "",
    ]
    materials = report.get("materials", {})
    if materials:
        for key, material in sorted(materials.items()):
            lines.append(f"- `{key}`: `{material.get('type')}` / `{material.get('name')}`")
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


def demo_materials() -> dict[str, Any]:
    """Return public-safe material-contract demo inputs."""

    return {
        "air": {
            "name": "air",
            "type": "constant_fluid",
            "density_kg_m3": 1.225,
            "viscosity_pa_s": 1.8e-5,
        },
        "wall": {
            "name": "aluminum",
            "type": "solid_thermal",
            "density_kg_m3": 2700.0,
            "thermal_conductivity_w_m_k": 205.0,
            "specific_heat_j_kg_k": 900.0,
        },
        "slurry_particles": {
            "name": "silica_particles",
            "type": "particle_phase",
            "density_kg_m3": 2650.0,
            "diameter_m": 0.0001,
        },
    }


def run_material_contract_demo(output_dir: str | Path) -> dict[str, Any]:
    """Write a public material-contract demo pack."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    materials = demo_materials()
    report = validate_material_contract(materials)
    artifacts = {
        "materials": str(root / "materials.json"),
        "material_contract": str(root / "material_contract.json"),
        "material_property_table": str(root / "material_property_table.csv"),
        "material_model_report": str(root / "material_model_report.md"),
        "fluent_material_hints": str(root / "fluent_material_hints.json"),
    }
    (root / "materials.json").write_text(json.dumps(materials, ensure_ascii=True, indent=2), encoding="utf-8")
    (root / "material_contract.json").write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    _write_material_table(report, root / "material_property_table.csv")
    (root / "material_model_report.md").write_text(material_contract_markdown(report), encoding="utf-8")
    (root / "fluent_material_hints.json").write_text(json.dumps(_fluent_material_hints(report), ensure_ascii=True, indent=2), encoding="utf-8")
    return {"status": "success" if report["status"] == "passed" else "failed", "outputs": {"contract": report, "artifacts": artifacts}}


def _infer_material_type(material: dict[str, Any]) -> str:
    if "phases" in material:
        return "two_phase_pair"
    if "power_law_index" in material or "yield_stress_pa" in material:
        return "non_newtonian_fluid"
    if "permeability_m2" in material:
        return "porous_medium"
    if "diameter_m" in material:
        return "particle_phase"
    if "thermal_conductivity_w_m_k" in material and "viscosity_pa_s" not in material:
        return "solid_thermal"
    if "temperature_points_k" in material:
        return "temperature_dependent_fluid"
    if "gas_constant_j_kg_k" in material:
        return "ideal_gas_lite"
    return "constant_fluid"


def _validate_material_fields(key: str, material_type: str, material: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if "name" not in material:
        warnings.append(f"materials.{key} has no explicit name.")
    for field_name in (
        "density_kg_m3",
        "viscosity_pa_s",
        "thermal_conductivity_w_m_k",
        "specific_heat_j_kg_k",
        "diameter_m",
        "permeability_m2",
    ):
        if field_name in material:
            _require_positive_number(material[field_name], f"materials.{key}.{field_name}", errors)
    if material_type in {"constant_fluid", "temperature_dependent_fluid", "non_newtonian_fluid"}:
        if "density_kg_m3" not in material:
            errors.append(f"materials.{key} requires density_kg_m3.")
        if material_type == "constant_fluid" and "viscosity_pa_s" not in material:
            errors.append(f"materials.{key} constant_fluid requires viscosity_pa_s.")
    if material_type == "solid_thermal":
        for field_name in ("thermal_conductivity_w_m_k", "specific_heat_j_kg_k"):
            if field_name not in material:
                errors.append(f"materials.{key} solid_thermal requires {field_name}.")
    if material_type == "particle_phase" and "diameter_m" not in material:
        errors.append(f"materials.{key} particle_phase requires diameter_m.")
    if material_type == "porous_medium" and "permeability_m2" not in material:
        errors.append(f"materials.{key} porous_medium requires permeability_m2.")
    if material_type == "two_phase_pair" and not isinstance(material.get("phases"), list):
        errors.append(f"materials.{key} two_phase_pair requires phases as a list.")


def _require_positive_number(value: Any, label: str, errors: list[str]) -> None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be numeric.")
        return
    if number <= 0:
        errors.append(f"{label} must be positive.")


def _write_material_table(report: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["material_key", "name", "type", "property", "value"])
        for key, material in sorted(report.get("materials", {}).items()):
            for prop, value in sorted(material.get("properties", {}).items()):
                writer.writerow([key, material.get("name"), material.get("type"), prop, value])


def _fluent_material_hints(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "fastfluent_fluent_material_hints_v1",
        "status": report.get("status"),
        "hints": [
            {
                "category": "materials",
                "recommendation": "Map validated FastFluent material contracts to Fluent material definitions before solver execution.",
                "evidence": "material_contract.json",
            }
        ],
        "limitations": ["This file contains setup hints only and does not edit a Fluent case."],
    }
