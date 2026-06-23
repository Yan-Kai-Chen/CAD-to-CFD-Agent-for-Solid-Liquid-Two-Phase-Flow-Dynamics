from __future__ import annotations

import json

from fromcad2cfd_fastcfd.practical_heat_diffusion import (
    demo_heat_diffusion_1d_case,
    run_heat_diffusion_1d_case,
    run_heat_diffusion_2d_case,
)


def test_stable_1d_heat_diffusion_writes_finite_outputs(tmp_path):
    output_dir = tmp_path / "heat_1d"

    result = run_heat_diffusion_1d_case(output_dir=output_dir)

    assert result["status"] == "pass"
    assert result["stability_summary"]["fourier_number"] <= 0.5
    assert result["qoi_summary"]["nonfinite_count"] == 0
    assert result["qoi_summary"]["max_temperature_K"] >= result["qoi_summary"]["min_temperature_K"]
    assert (output_dir / "temperature_history.csv").exists()
    assert (output_dir / "temperature_field_final.csv").exists()
    assert (output_dir / "simulation_result.json").exists()


def test_unstable_1d_heat_diffusion_blocks(tmp_path):
    case = demo_heat_diffusion_1d_case()
    case["time_step_s"] = 10.0

    result = run_heat_diffusion_1d_case(case, output_dir=tmp_path / "heat_unstable")

    assert result["status"] == "block"
    assert result["stability_summary"]["stability_flag"] == "unstable"
    assert result["blocking_errors"]


def test_2d_heat_diffusion_demo_writes_field(tmp_path):
    output_dir = tmp_path / "heat_2d"

    result = run_heat_diffusion_2d_case(output_dir=output_dir)

    assert result["status"] == "pass"
    assert result["stability_summary"]["fourier_number_sum"] <= 0.5
    assert result["qoi_summary"]["nonfinite_count"] == 0
    assert (output_dir / "temperature_field.csv").exists()
    payload = json.loads((output_dir / "simulation_result.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "fromcad2cfd_fastfluent_practical_native_result_v1"
    assert payload["metadata"]["fluent_launched"] is False
