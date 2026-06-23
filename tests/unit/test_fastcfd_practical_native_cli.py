from __future__ import annotations

import json

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fastcfd.practical_native_demo_pack import run_practical_native_demo_pack


def test_practical_native_demo_pack_writes_expected_tree(tmp_path):
    output_dir = tmp_path / "pack"

    result = run_practical_native_demo_pack(output_dir)
    manifest = result["outputs"]["manifest"]

    assert result["status"] == "success"
    assert manifest["schema_version"] == "fromcad2cfd_fastfluent_practical_native_pack_v1"
    assert manifest["acceptance_summary"]["fluent_launched"] is False
    for relative in [
        "heat_diffusion_1d/input_case.json",
        "heat_diffusion_1d/temperature_history.csv",
        "heat_diffusion_2d/temperature_field.csv",
        "scalar_advection_diffusion_1d/scalar_history.csv",
        "bounded_scalar_transport/comparison_summary.json",
        "arrhenius_viscosity_field/viscosity_field.csv",
        "source_term_ramp_clamp/comparison_summary.json",
        "practical_parameter_sweep/sweep_summary.csv",
        "wax_application_demo/temperature_history.csv",
        "wax_application_demo/viscosity_field.csv",
        "wax_application_demo/source_history.csv",
        "practical_native_manifest.json",
        "practical_native_summary.md",
    ]:
        assert (output_dir / relative).exists(), relative


def test_practical_native_demo_pack_cli(tmp_path, capsys):
    output_dir = tmp_path / "cli_pack"

    exit_code = root_main(["fastcfd", "practical-native-demo-pack", "--output-dir", str(output_dir)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["metadata"]["fluent_launched"] is False
    assert (output_dir / "practical_native_manifest.json").exists()
