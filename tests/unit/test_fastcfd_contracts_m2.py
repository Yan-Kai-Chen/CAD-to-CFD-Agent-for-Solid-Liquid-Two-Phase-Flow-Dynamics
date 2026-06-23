from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.boundary.boundary_contract import demo_boundary_conditions, validate_boundary_contract
from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.core.units import validate_unit_contract
from fromcad2cfd_fastcfd.materials.material_contract import demo_materials, validate_material_contract


def test_unit_contract_checks_case_like_quantities():
    payload = {
        "geometry": {"length_m": 1.0, "height_m": 0.1},
        "materials": {"fluid": {"density_kg_m3": 1.225, "viscosity_pa_s": 1.8e-5}},
        "boundary_conditions": {"inlet": {"velocity_m_s": [1.0, 0.0]}},
        "numerics": {"time_step_s": 0.01},
    }

    report = validate_unit_contract(payload)

    assert report["status"] == "passed"
    assert len(report["checked_quantities"]) >= 5


def test_unit_contract_rejects_negative_positive_quantity():
    report = validate_unit_contract({"materials": {"fluid": {"density_kg_m3": -1.0}}})

    assert report["status"] == "failed"
    assert any("density_kg_m3" in error for error in report["errors"])


def test_boundary_contract_validates_public_demo():
    report = validate_boundary_contract(demo_boundary_conditions(), zones=["inlet", "outlet", "top_wall", "bottom_wall", "fluid"])

    assert report["status"] == "passed"
    assert report["type_counts"]["velocity_inlet"] == 1
    assert report["type_counts"]["pressure_outlet"] == 1


def test_boundary_contract_fails_missing_velocity():
    report = validate_boundary_contract({"inlet": {"type": "velocity_inlet"}, "outlet": {"type": "pressure_outlet"}})

    assert report["status"] == "failed"
    assert any("velocity_m_s" in error for error in report["errors"])


def test_material_contract_validates_public_demo():
    report = validate_material_contract(demo_materials())

    assert report["status"] == "passed"
    assert report["material_count"] == 3
    assert report["materials"]["air"]["type"] == "constant_fluid"


def test_material_contract_fails_negative_viscosity():
    materials = {"bad": {"name": "bad", "type": "constant_fluid", "density_kg_m3": 1.0, "viscosity_pa_s": -1.0}}
    report = validate_material_contract(materials)

    assert report["status"] == "failed"
    assert any("viscosity_pa_s" in error for error in report["errors"])


def test_boundary_contract_cli_demo_pack(tmp_path, capsys):
    output_dir = tmp_path / "bc_demo"
    exit_code = fastcfd_main(["bc", "validate-demo-pack", "--output-dir", str(output_dir), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["boundary_contract"]).exists()
    assert (output_dir / "fluent_boundary_hints.json").exists()


def test_material_contract_cli_demo_pack(tmp_path, capsys):
    output_dir = tmp_path / "material_demo"
    exit_code = fastcfd_main(["materials", "validate-demo-pack", "--output-dir", str(output_dir), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["material_contract"]).exists()
    assert (output_dir / "material_property_table.csv").exists()
