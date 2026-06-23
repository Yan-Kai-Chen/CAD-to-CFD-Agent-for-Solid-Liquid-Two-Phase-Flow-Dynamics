from __future__ import annotations

import json

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fastcfd.practical_heat_diffusion import run_heat_diffusion_1d_case
from fromcad2cfd_fastcfd.practical_scalar_transport import run_scalar_advection_diffusion_1d_case
from fromcad2cfd_fastcfd.practical_setup import (
    PRACTICAL_CASE_TEMPLATE_SCHEMA_VERSION,
    build_boundary_condition_contract,
    build_channel_2d_geometry,
    build_line_1d_geometry,
    build_case_templates,
    field_initialization_summary,
    initial_field_rows,
    run_practical_native_setup_demo,
    validate_boundary_condition_contract,
    write_initial_field_files,
)


def test_line_and_channel_geometry_have_required_zones():
    line = build_line_1d_geometry(length_m=0.02, nx=11)
    channel = build_channel_2d_geometry(length_m=0.1, height_m=0.02, nx=31, ny=11)

    assert line["grid"]["node_count"] == 11
    assert line["boundary_zones"]["left"] == 1
    assert line["boundary_zones"]["right"] == 1
    assert channel["boundary_zones"]["inlet"] > 0
    assert channel["boundary_zones"]["outlet"] > 0
    assert channel["boundary_zones"]["wall"] > 0
    assert channel["boundary_zones"]["obstacle"] > 0
    assert channel["grid"]["active_node_count"] < channel["grid"]["node_count"]
    assert channel["metadata"]["fluent_launched"] is False


def test_boundary_condition_contract_validates_and_fails_closed():
    channel = build_channel_2d_geometry()

    contract = build_boundary_condition_contract(channel)
    validation = validate_boundary_condition_contract(contract, channel)
    bad_validation = validate_boundary_condition_contract({"required_zones": ["inlet", "outlet", "wall"], "conditions": {"inlet": {}}}, channel)

    assert contract["validation"]["passed"]
    assert validation["passed"]
    assert not bad_validation["passed"]
    assert any("outlet" in error or "wall" in error for error in bad_validation["errors"])


def test_initial_field_generation_is_finite_and_writes_csv(tmp_path):
    channel = build_channel_2d_geometry()
    contract = build_boundary_condition_contract(channel)

    rows = initial_field_rows(channel, contract)
    summary = field_initialization_summary(rows)
    artifacts = write_initial_field_files(channel, contract, tmp_path / "fields")

    assert summary["nonfinite_count"] == 0
    assert summary["temperature_max_K"] > summary["temperature_min_K"]
    assert summary["scalar_min"] == 0.0
    assert summary["scalar_max"] == 1.0
    assert summary["velocity_max_m_s"] > 0.0
    for path in artifacts.values():
        assert path
    assert (tmp_path / "fields" / "temperature_field.csv").exists()
    assert (tmp_path / "fields" / "scalar_field.csv").exists()
    assert (tmp_path / "fields" / "velocity_field.csv").exists()


def test_case_templates_are_s2_compatible(tmp_path):
    line = build_line_1d_geometry()
    channel = build_channel_2d_geometry()
    paths = build_case_templates(line, channel, tmp_path / "templates")
    heat_case = json.loads((tmp_path / "templates" / "heat_diffusion_1d_case.json").read_text(encoding="utf-8"))
    scalar_case = json.loads((tmp_path / "templates" / "scalar_transport_1d_case.json").read_text(encoding="utf-8"))

    assert heat_case["schema_version"] == PRACTICAL_CASE_TEMPLATE_SCHEMA_VERSION
    assert scalar_case["schema_version"] == PRACTICAL_CASE_TEMPLATE_SCHEMA_VERSION
    assert "wax_practical_case" in paths

    heat_result = run_heat_diffusion_1d_case(heat_case, tmp_path / "heat_run")
    scalar_result = run_scalar_advection_diffusion_1d_case(scalar_case, tmp_path / "scalar_run")

    assert heat_result["status"] == "pass"
    assert scalar_result["status"] == "pass"


def test_practical_native_setup_demo_writes_expected_tree(tmp_path):
    output_dir = tmp_path / "setup_pack"

    result = run_practical_native_setup_demo(output_dir)
    manifest = result["outputs"]["manifest"]

    assert result["status"] == "success"
    assert manifest["schema_version"] == "fromcad2cfd_fastfluent_practical_setup_pack_v1"
    assert manifest["acceptance_summary"]["boundary_condition_contract_valid"] is True
    assert manifest["metadata"]["fluent_launched"] is False
    for relative in [
        "geometry/line_1d_geometry_manifest.json",
        "geometry/channel_2d_geometry_manifest.json",
        "boundary_conditions/boundary_condition_contract.json",
        "initial_fields/temperature_field.csv",
        "initial_fields/scalar_field.csv",
        "initial_fields/velocity_field.csv",
        "case_templates/heat_diffusion_1d_case.json",
        "case_templates/scalar_transport_1d_case.json",
        "case_templates/wax_practical_case.json",
        "practical_setup_manifest.json",
        "practical_setup_summary.md",
    ]:
        assert (output_dir / relative).exists(), relative


def test_practical_native_setup_demo_cli(tmp_path, capsys):
    output_dir = tmp_path / "cli_setup_pack"

    exit_code = root_main(["fastcfd", "practical-native-setup-demo", "--output-dir", str(output_dir)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["metadata"]["fluent_launched"] is False
    assert (output_dir / "practical_setup_manifest.json").exists()
