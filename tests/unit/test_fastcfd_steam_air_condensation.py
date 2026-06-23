from __future__ import annotations

import json

from fromcad2cfd_fastcfd.steam_air_condensation import (
    build_steam_air_condensation_passport,
    demo_steam_air_condensation_case,
    validate_steam_air_condensation_case_file,
)


def test_valid_demo_case_produces_warn_passport_and_report(tmp_path):
    case = demo_steam_air_condensation_case()
    case_file = tmp_path / "steam_air_condensation_case.json"
    case_file.write_text(json.dumps(case), encoding="utf-8")

    result = validate_steam_air_condensation_case_file(case_file, output_dir=tmp_path / "passport")
    passport = result["outputs"]["passport"]

    assert result["status"] == "success"
    assert passport["status"] in {"pass", "warn"}
    assert passport["computed_quantities"]["wall_subcooling_K"] > 0
    assert (tmp_path / "passport" / "steam_air_condensation_report.md").exists()


def test_species_fraction_sum_fails_closed():
    case = demo_steam_air_condensation_case()
    case["air_mass_fraction"] = 0.2

    passport = build_steam_air_condensation_passport(case)

    assert passport["status"] == "block"
    assert any("must equal 1" in error for error in passport["blocking_errors"])


def test_negative_pressure_fails_closed():
    case = demo_steam_air_condensation_case()
    case["pressure_pa"] = -1.0

    passport = build_steam_air_condensation_passport(case)

    assert passport["status"] == "block"
    assert any("pressure_pa" in error for error in passport["blocking_errors"])


def test_wall_temperature_above_saturation_warns_no_condensation():
    case = demo_steam_air_condensation_case()
    case["wall_temperature_K"] = 500.0

    passport = build_steam_air_condensation_passport(case)

    assert passport["status"] == "warn"
    assert any("condensation is unlikely" in warning for warning in passport["warnings"])


def test_high_air_fraction_gives_high_noncondensable_risk():
    case = demo_steam_air_condensation_case()
    case["steam_mass_fraction"] = 0.9
    case["air_mass_fraction"] = 0.1

    passport = build_steam_air_condensation_passport(case)

    assert passport["computed_quantities"]["non_condensable_layer_risk"] == "high"


def test_large_time_step_warns_or_blocks():
    case = demo_steam_air_condensation_case()
    case["time_step_s"] = 0.1

    passport = build_steam_air_condensation_passport(case)

    assert passport["status"] in {"warn", "block"}
    assert passport["computed_quantities"].get("source_term_stiffness_risk") in {"moderate", "high", None}


def test_dangerous_key_is_rejected():
    case = demo_steam_air_condensation_case()
    case["metadata"]["python_code"] = "print('unsafe')"

    passport = build_steam_air_condensation_passport(case)

    assert passport["status"] == "block"
    assert any("Dangerous key names" in error for error in passport["blocking_errors"])
