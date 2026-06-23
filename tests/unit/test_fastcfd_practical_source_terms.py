from __future__ import annotations

from fromcad2cfd_fastcfd.practical_source_terms import (
    apply_source_controls,
    demo_source_term_case,
    run_source_ramp_clamp_comparison,
    run_source_term_cell_model,
    source_value,
)


def test_source_term_cell_model_generates_history_and_integral(tmp_path):
    output_dir = tmp_path / "source"

    result = run_source_term_cell_model(output_dir=output_dir)

    assert result["status"] in {"pass", "warn"}
    assert result["qoi_summary"]["source_integral_J_m3"] > 0
    assert result["qoi_summary"]["nonfinite_count"] == 0
    assert (output_dir / "source_history.csv").exists()
    assert (output_dir / "temperature_history.csv").exists()


def test_source_activation_and_controls_are_explicit():
    case = demo_source_term_case(ramp_enabled=True, clamp_enabled=True)

    assert source_value(335.0, 1.0, case) == case["source_strength_W_m3"]
    assert source_value(320.0, 1.0, case) == 0.0
    assert apply_source_controls(case["source_strength_W_m3"], 0.5, case) <= case["source_max_W_m3"]


def test_source_ramp_clamp_comparison_writes_outputs(tmp_path):
    output_dir = tmp_path / "source_compare"

    comparison = run_source_ramp_clamp_comparison(output_dir)

    assert comparison["fluent_launched"] is False
    assert (output_dir / "no_ramp_no_clamp" / "source_history.csv").exists()
    assert (output_dir / "with_ramp_and_clamp" / "source_history.csv").exists()
    assert (output_dir / "comparison_summary.json").exists()
    assert comparison["max_temperature_with_ramp_and_clamp_K"] <= 380.0
