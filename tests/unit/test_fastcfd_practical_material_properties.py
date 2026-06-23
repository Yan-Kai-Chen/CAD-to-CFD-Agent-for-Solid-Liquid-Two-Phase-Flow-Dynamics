from __future__ import annotations

import pytest

from fromcad2cfd_fastcfd.practical_material_properties import (
    evaluate_property_value,
    run_arrhenius_viscosity_field_demo,
    run_property_field_case,
)


def test_arrhenius_viscosity_field_reports_range_and_ratio(tmp_path):
    output_dir = tmp_path / "arrhenius"

    result = run_arrhenius_viscosity_field_demo(output_dir)

    assert result["status"] == "pass"
    assert result["qoi_summary"]["property_min"] > 0
    assert result["qoi_summary"]["property_max"] > result["qoi_summary"]["property_min"]
    assert result["qoi_summary"]["property_ratio"] > 1.0
    assert result["qoi_summary"]["outside_fit_range_count"] == 0
    assert (output_dir / "viscosity_field.csv").exists()
    assert (output_dir / "property_field_summary.json").exists()


def test_constant_linear_and_piecewise_property_evaluators():
    assert evaluate_property_value(300.0, {"property_model": "constant", "constant_value": 2.0}) == pytest.approx(2.0)
    assert evaluate_property_value(310.0, {"property_model": "linear", "reference_temperature_K": 300.0, "reference_value": 2.0, "slope_per_K": 0.1}) == pytest.approx(3.0)
    piecewise = {
        "property_model": "piecewise_linear",
        "points": [
            {"temperature_K": 300.0, "value": 1.0},
            {"temperature_K": 320.0, "value": 3.0},
        ],
    }
    assert evaluate_property_value(310.0, piecewise) == pytest.approx(2.0)


def test_property_field_outside_fit_range_warns(tmp_path):
    case = {
        "case_id": "outside_fit",
        "case_name": "Outside Fit Range",
        "property_name": "dynamic_viscosity",
        "property_model": "arrhenius",
        "arrhenius_A": -46.7601,
        "arrhenius_B_K": 16488.4,
        "temperature_min_K": 353.15,
        "temperature_max_K": 373.15,
        "fit_temperature_min_K": 300.0,
        "fit_temperature_max_K": 360.0,
        "nx": 11,
        "length_m": 0.01,
    }

    result = run_property_field_case(case, tmp_path / "outside_fit")

    assert result["status"] == "warn"
    assert result["qoi_summary"]["outside_fit_range_count"] > 0
