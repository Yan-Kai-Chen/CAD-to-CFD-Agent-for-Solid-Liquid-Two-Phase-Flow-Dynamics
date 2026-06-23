from __future__ import annotations

import json

import pytest

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fastcfd.fluent_patch_compiler import compile_solver_plan_patch_from_passport
from fromcad2cfd_fastcfd.solver_plan_patch import validate_solver_plan_patch
from fromcad2cfd_fastcfd.steam_air_condensation_v2 import (
    STEAM_AIR_V2_CASE_SCHEMA_VERSION,
    STEAM_AIR_V2_FLUENT_HINTS_SCHEMA_VERSION,
    STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION,
    build_steam_air_condensation_passport_v2,
    build_steam_air_fluent_hints_v2,
    demo_steam_air_condensation_case_v2,
    run_steam_air_v2_demo,
    validate_steam_air_condensation_v2_case_file,
)


def test_valid_v2_case_passes_with_expected_schema(tmp_path):
    case = demo_steam_air_condensation_case_v2()
    case_file = tmp_path / "steam_air_condensation_case_v2.json"
    case_file.write_text(json.dumps(case), encoding="utf-8")

    result = validate_steam_air_condensation_v2_case_file(case_file, output_dir=tmp_path / "passport")
    passport = result["outputs"]["passport"]
    hints = result["outputs"]["fluent_hints"]

    assert result["status"] == "success"
    assert case["schema_version"] == STEAM_AIR_V2_CASE_SCHEMA_VERSION
    assert passport["schema_version"] == STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION
    assert hints["schema_version"] == STEAM_AIR_V2_FLUENT_HINTS_SCHEMA_VERSION
    assert passport["status"] in {"pass", "warn"}
    assert (tmp_path / "passport" / "steam_air_condensation_report_v2.md").exists()


def test_invalid_species_fraction_sum_fails_closed():
    case = demo_steam_air_condensation_case_v2()
    case["air_mass_fraction"] = 0.2

    passport = build_steam_air_condensation_passport_v2(case)

    assert passport["status"] == "block"
    assert any("must equal 1" in error for error in passport["blocking_errors"])


def test_reynolds_number_is_verified():
    case = demo_steam_air_condensation_case_v2()

    passport = build_steam_air_condensation_passport_v2(case)
    computed = passport["computed_quantities"]
    expected = (
        case["mixture_density_kg_m3"]
        * case["reference_velocity_m_s"]
        * case["hydraulic_diameter_m"]
        / case["mixture_dynamic_viscosity_pa_s"]
    )

    assert computed["reynolds_number"] == pytest.approx(expected)
    assert computed["flow_regime"] == "turbulent"


def test_prandtl_number_is_verified():
    case = demo_steam_air_condensation_case_v2()

    passport = build_steam_air_condensation_passport_v2(case)
    computed = passport["computed_quantities"]
    expected = (
        case["mixture_dynamic_viscosity_pa_s"]
        * case["mixture_specific_heat_j_kg_k"]
        / case["mixture_thermal_conductivity_w_m_k"]
    )

    assert computed["prandtl_number"] == pytest.approx(expected)
    assert computed["peclet_number"] == pytest.approx(computed["reynolds_number"] * computed["prandtl_number"])


def test_jakob_number_is_verified():
    case = demo_steam_air_condensation_case_v2()

    passport = build_steam_air_condensation_passport_v2(case)
    computed = passport["computed_quantities"]
    expected = (
        case["mixture_specific_heat_j_kg_k"]
        * (computed["estimated_saturation_temperature_K"] - case["wall_temperature_K"])
        / case["latent_heat_j_kg"]
    )

    assert computed["jakob_number"] == pytest.approx(expected)
    assert computed["stefan_number"] == pytest.approx(expected)


def test_heat_transfer_and_mass_transfer_estimates_are_present():
    passport = build_steam_air_condensation_passport_v2(demo_steam_air_condensation_case_v2())
    computed = passport["computed_quantities"]

    assert computed["estimated_nusselt_number"] > 0
    assert computed["estimated_htc_W_m2K"] > 0
    assert computed["estimated_heat_flux_W_m2"] > 0
    assert computed["estimated_heat_transfer_rate_W"] > 0
    assert computed["heat_transfer_correlation"]["correlation_name"]
    assert computed["schmidt_number"] > 0
    assert computed["sherwood_number"] > 0
    assert computed["mass_transfer_coefficient_m_s"] > 0
    assert computed["mass_transfer_resistance"] in {"low", "moderate", "high"}
    assert computed["mass_transfer_correlation"]["validity_range"]


def test_source_term_checks_are_present_and_consistent():
    passport = build_steam_air_condensation_passport_v2(demo_steam_air_condensation_case_v2())
    computed = passport["computed_quantities"]

    assert computed["source_term_dimension_check"] == "pass"
    assert computed["source_term_sign_check"] == "pass"
    assert computed["latent_heat_consistency"] == "pass"
    assert computed["source_term_stiffness_level"] in {"low", "moderate", "high", "extreme"}


def test_v2_patch_generation_is_valid_and_expanded():
    passport = build_steam_air_condensation_passport_v2(demo_steam_air_condensation_case_v2())

    patch = compile_solver_plan_patch_from_passport(passport)
    validation = validate_solver_plan_patch(patch)

    assert validation.passed
    assert _operation(patch, "/physics/energy/enabled")["value"] is True
    assert _operation(patch, "/physics/species_transport/enabled")["value"] is True
    assert _operation(patch, "/physics/turbulence/model")["value"] == "k-omega-sst-review-required"
    assert _operation(patch, "/source_terms/condensation/ramping")["value"] is True
    assert _operation(patch, "/source_terms/condensation/clamp")["value"] is True
    assert any(op["path"] == "/monitors/global" and op["value"]["name"] == "source_term_integral" for op in patch["patches"])
    assert any(op["path"] == "/monitors/wall" and op["value"]["name"] == "wall_heat_transfer_rate" for op in patch["patches"])


def test_v2_hints_can_compile_as_review_warnings():
    passport = build_steam_air_condensation_passport_v2(demo_steam_air_condensation_case_v2())
    hints = build_steam_air_fluent_hints_v2(passport)

    patch = compile_solver_plan_patch_from_passport(hints)

    assert validate_solver_plan_patch(patch).passed
    assert patch["status"] == "warn"
    assert all(operation["op"] == "warn" for operation in patch["patches"])


def test_v2_demo_generation_writes_expected_artifacts(tmp_path):
    result = run_steam_air_v2_demo(output_dir=tmp_path / "steam_air_v2_demo")
    artifacts = result["outputs"]["artifacts"]

    assert result["status"] in {"success", "partial"}
    for path in artifacts.values():
        assert path
    for relative in [
        "steam_air_condensation_case_v2.json",
        "steam_air_condensation_passport_v2.json",
        "steam_air_condensation_fluent_hints_v2.json",
        "solver_plan_patch.json",
        "solver_plan_patch_report.md",
        "steam_air_condensation_report_v2.md",
    ]:
        assert (tmp_path / "steam_air_v2_demo" / relative).exists(), relative


def test_steam_air_v2_demo_cli(tmp_path, capsys):
    output_dir = tmp_path / "cli_demo"

    exit_code = root_main(["fastcfd", "steam-air-v2-demo", "--output-dir", str(output_dir)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] in {"success", "partial"}
    assert (output_dir / "solver_plan_patch.json").exists()


def _operation(patch: dict, path: str) -> dict:
    for operation in patch["patches"]:
        if operation["path"] == path:
            return operation
    raise AssertionError(f"Missing operation path: {path}")

