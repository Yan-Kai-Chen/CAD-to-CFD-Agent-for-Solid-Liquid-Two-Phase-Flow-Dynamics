from __future__ import annotations

from fromcad2cfd_fastcfd.practical_scalar_transport import (
    demo_scalar_transport_case,
    run_bounded_scalar_transport_comparison,
    run_scalar_advection_diffusion_1d_case,
)


def test_scalar_transport_reports_cfl_mass_and_front(tmp_path):
    output_dir = tmp_path / "scalar"

    result = run_scalar_advection_diffusion_1d_case(output_dir=output_dir)

    assert result["status"] == "pass"
    assert result["stability_summary"]["cfl"] <= 1.0
    assert result["stability_summary"]["diffusion_number"] <= 0.5
    assert "phi_mass_relative_change" in result["qoi_summary"]
    assert result["qoi_summary"]["front_position_m"] >= 0.0
    assert (output_dir / "scalar_history.csv").exists()
    assert (output_dir / "scalar_field_final.csv").exists()


def test_unstable_scalar_transport_blocks(tmp_path):
    case = demo_scalar_transport_case()
    case["velocity_m_s"] = 5.0
    case["time_step_s"] = 0.1

    result = run_scalar_advection_diffusion_1d_case(case, output_dir=tmp_path / "scalar_unstable")

    assert result["status"] == "block"
    assert result["stability_summary"]["stability_flag"] == "unstable"
    assert result["blocking_errors"]


def test_bounded_scalar_transport_comparison_writes_summary(tmp_path):
    output_dir = tmp_path / "bounded"

    comparison = run_bounded_scalar_transport_comparison(output_dir)

    assert comparison["fluent_launched"] is False
    assert (output_dir / "without_clamp" / "scalar_field_final.csv").exists()
    assert (output_dir / "with_clamp" / "scalar_field_final.csv").exists()
    assert (output_dir / "comparison_summary.json").exists()
    assert comparison["with_clamp_violation_count"] <= comparison["without_clamp_violation_count"]
