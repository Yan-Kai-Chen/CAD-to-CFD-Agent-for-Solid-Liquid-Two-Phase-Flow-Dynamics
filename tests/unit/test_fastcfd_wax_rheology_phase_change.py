from __future__ import annotations

import json
import math

import pytest

from fromcad2cfd_fastcfd.wax_rheology_phase_change import (
    GAS_CONSTANT_J_MOL_K,
    WAX_RHEOLOGY_CASE_SCHEMA_VERSION,
    WAX_RHEOLOGY_HINTS_SCHEMA_VERSION,
    WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION,
    arrhenius_viscosity_pa_s,
    build_wax_rheology_phase_change_fluent_hints,
    build_wax_rheology_phase_change_passport,
    classify_fit_range,
    classify_phase_change_stiffness,
    classify_softening_regime,
    classify_viscosity_sensitivity,
    compute_wax_rheology_phase_change_quantities,
    create_demo_wax_rheology_case,
    run_wax_rheology_handoff_demo,
    validate_wax_rheology_phase_change_case_file,
)


def test_valid_demo_case_produces_pass_or_warn_passport(tmp_path):
    case = create_demo_wax_rheology_case()
    case_file = tmp_path / "wax_rheology_phase_change_case.json"
    case_file.write_text(json.dumps(case), encoding="utf-8")

    result = validate_wax_rheology_phase_change_case_file(case_file, output_dir=tmp_path / "passport")
    passport = result["outputs"]["passport"]
    hints = result["outputs"]["fluent_hints"]

    assert result["status"] == "success"
    assert case["schema_version"] == WAX_RHEOLOGY_CASE_SCHEMA_VERSION
    assert passport["schema_version"] == WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION
    assert hints["schema_version"] == WAX_RHEOLOGY_HINTS_SCHEMA_VERSION
    assert passport["status"] in {"pass", "warn"}
    assert hints["metadata"]["fluent_launched"] is False
    assert (tmp_path / "passport" / "wax_rheology_phase_change_report.md").exists()


def test_invalid_case_fails_closed():
    case = create_demo_wax_rheology_case()
    case["time_step_s"] = -0.01

    passport = build_wax_rheology_phase_change_passport(case)

    assert passport["status"] == "block"
    assert any("time_step_s" in error for error in passport["blocking_errors"])
    assert passport["metadata"]["fluent_launched"] is False


def test_arrhenius_viscosity_and_thermal_quantities_are_verified():
    case = create_demo_wax_rheology_case()

    computed = compute_wax_rheology_phase_change_quantities(case)
    arrhenius = computed["arrhenius"]
    thermal = computed["thermal"]
    phase = computed["phase_change"]
    storage = computed["storage_modulus"]
    heating = computed["heating"]

    eta_min_temp = math.exp(case["arrhenius_A"] + case["arrhenius_B_K"] / case["temperature_min_K"])
    eta_max_temp = math.exp(case["arrhenius_A"] + case["arrhenius_B_K"] / case["temperature_max_K"])
    eta_reference = math.exp(case["arrhenius_A"] + case["arrhenius_B_K"] / case["reference_temperature_K"])
    alpha = case["thermal_conductivity_W_mK"] / (case["density_solid_kg_m3"] * case["specific_heat_J_kgK"])
    cell_time = case["cell_size_m"] ** 2 / alpha
    softening_time = (case["softening_temperature_90_K"] - case["softening_temperature_50_K"]) / case["heating_rate_K_s"]

    assert arrhenius_viscosity_pa_s(case["reference_temperature_K"], case["arrhenius_A"], case["arrhenius_B_K"]) == pytest.approx(eta_reference)
    assert arrhenius["eta_at_temperature_min_Pa_s"] == pytest.approx(eta_min_temp)
    assert arrhenius["eta_at_temperature_max_Pa_s"] == pytest.approx(eta_max_temp)
    assert arrhenius["eta_at_reference_temperature_Pa_s"] == pytest.approx(eta_reference)
    assert arrhenius["eta_ratio_over_range"] == pytest.approx(max(eta_min_temp, eta_max_temp) / min(eta_min_temp, eta_max_temp))
    assert arrhenius["activation_energy_J_mol"] == pytest.approx(case["arrhenius_B_K"] * GAS_CONSTANT_J_MOL_K)
    assert thermal["thermal_diffusivity_m2_s"] == pytest.approx(alpha)
    assert thermal["cell_diffusion_time_s"] == pytest.approx(cell_time)
    assert thermal["thermal_time_step_ratio"] == pytest.approx(case["time_step_s"] / cell_time)
    assert storage["storage_modulus_drop_ratio"] == pytest.approx(case["storage_modulus_low_temp_Pa"] / case["storage_modulus_high_temp_Pa"])
    assert heating["softening_heating_time_s"] == pytest.approx(softening_time)
    assert phase["stefan_number"] == pytest.approx(case["specific_heat_J_kgK"] * (case["temperature_max_K"] - case["temperature_min_K"]) / case["latent_heat_J_kg"])
    assert phase["phase_change_energy_density_J_m3"] == pytest.approx(case["density_solid_kg_m3"] * case["latent_heat_J_kg"])
    assert phase["phase_change_power_density_scale_W_m3"] == pytest.approx(case["density_solid_kg_m3"] * case["latent_heat_J_kg"] / case["time_step_s"])
    assert computed["recommendation"]["recommended_time_step_s"] == pytest.approx(case["time_step_s"])


def test_softening_and_sensitivity_classifications_are_explicit():
    assert classify_softening_regime(300.0, 320.0, 330.0, 341.0) == "solid_like"
    assert classify_softening_regime(342.0, 360.0, 330.0, 341.0) == "flow_dominant"
    assert classify_softening_regime(320.0, 335.0, 330.0, 341.0) == "softening_transition"
    assert classify_softening_regime(320.0, 350.0, 330.0, 341.0) == "crosses_softening_transition"
    assert classify_softening_regime(320.0, 350.0, None, 341.0) == "unknown"

    assert classify_viscosity_sensitivity(5.0) == "low"
    assert classify_viscosity_sensitivity(50.0) == "moderate"
    assert classify_viscosity_sensitivity(500.0) == "high"
    assert classify_viscosity_sensitivity(50000.0) == "extreme"

    assert classify_fit_range(353.0, 373.0, 300.0, 400.0) == "inside_fit_range"
    assert classify_fit_range(353.0, 373.0, 360.0, 400.0) == "partly_outside_fit_range"
    assert classify_fit_range(353.0, 373.0, 280.0, 320.0) == "outside_fit_range"
    assert classify_fit_range(353.0, 373.0, None, 400.0) == "unknown"


def test_phase_change_stiffness_classification_ladder():
    case = create_demo_wax_rheology_case()

    no_phase_case = dict(case, phase_change_model="none")
    narrow_interval_case = dict(case, melting_temperature_max_K=330.65)
    assert classify_phase_change_stiffness({"thermal_time_step_ratio": 0.01}, {"stefan_number": 0.2}, no_phase_case) == "low"
    assert classify_phase_change_stiffness({"thermal_time_step_ratio": 0.01}, {"stefan_number": 0.5, "phase_change_power_density_scale_W_m3": 1.0e6}, case) == "low"
    assert classify_phase_change_stiffness({"thermal_time_step_ratio": 0.2}, {"stefan_number": 0.5, "phase_change_power_density_scale_W_m3": 1.0e6}, case) == "moderate"
    assert classify_phase_change_stiffness({"thermal_time_step_ratio": 0.2}, {"stefan_number": 0.05, "phase_change_power_density_scale_W_m3": 1.0e8}, case) == "high"
    assert classify_phase_change_stiffness({"thermal_time_step_ratio": 2.0}, {"stefan_number": 0.05, "phase_change_power_density_scale_W_m3": 1.0e12}, narrow_interval_case) == "extreme"


def test_fluent_hints_are_non_executing_review_artifacts():
    passport = build_wax_rheology_phase_change_passport(create_demo_wax_rheology_case())

    hints = build_wax_rheology_phase_change_fluent_hints(passport)
    text = json.dumps(hints, sort_keys=True)

    assert hints["status"] in {"ready", "ready_with_warnings", "blocked"}
    assert hints["recommended_physics"]["energy"] is True
    assert hints["recommended_numerics"]["source_term_ramping"] is True
    assert "temperature_min_max" in hints["recommended_monitors"]
    assert hints["metadata"]["fluent_launched"] is False
    assert "udf_code" not in text
    assert "raw_pyfluent" not in text


def test_wax_handoff_demo_writes_expected_tree(tmp_path):
    output_dir = tmp_path / "wax_demo"

    result = run_wax_rheology_handoff_demo(output_dir=output_dir)

    assert result["status"] in {"success", "partial"}
    for relative in [
        "wax_rheology_phase_change_case.json",
        "passport/wax_rheology_phase_change_passport.json",
        "passport/wax_rheology_phase_change_fluent_hints.json",
        "passport/wax_rheology_phase_change_report.md",
        "solver_plan_patch.json",
        "solver_plan_patch_report.md",
    ]:
        assert (output_dir / relative).exists(), relative
