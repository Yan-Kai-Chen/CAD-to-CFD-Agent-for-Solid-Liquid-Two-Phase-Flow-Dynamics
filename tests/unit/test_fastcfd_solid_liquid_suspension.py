from __future__ import annotations

import json

import pytest

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fastcfd.fluent_patch_compiler import compile_solver_plan_patch_from_passport
from fromcad2cfd_fastcfd.solid_liquid_suspension import (
    SOLID_LIQUID_CASE_SCHEMA_VERSION,
    SOLID_LIQUID_HINTS_SCHEMA_VERSION,
    SOLID_LIQUID_PASSPORT_SCHEMA_VERSION,
    build_solid_liquid_fluent_hints,
    build_solid_liquid_suspension_passport,
    demo_solid_liquid_suspension_case,
    run_solid_liquid_handoff_demo,
    validate_solid_liquid_suspension_case_file,
)
from fromcad2cfd_fastcfd.solver_plan_patch import validate_solver_plan_patch


def test_valid_demo_case_produces_pass_or_warn_passport(tmp_path):
    case = demo_solid_liquid_suspension_case()
    case_file = tmp_path / "solid_liquid_suspension_case.json"
    case_file.write_text(json.dumps(case), encoding="utf-8")

    result = validate_solid_liquid_suspension_case_file(case_file, output_dir=tmp_path / "passport")
    passport = result["outputs"]["passport"]
    hints = result["outputs"]["fluent_hints"]

    assert result["status"] == "success"
    assert case["schema_version"] == SOLID_LIQUID_CASE_SCHEMA_VERSION
    assert passport["schema_version"] == SOLID_LIQUID_PASSPORT_SCHEMA_VERSION
    assert hints["schema_version"] == SOLID_LIQUID_HINTS_SCHEMA_VERSION
    assert passport["status"] in {"pass", "warn"}
    assert (tmp_path / "passport" / "solid_liquid_suspension_report.md").exists()


def test_invalid_negative_particle_diameter_fails_closed():
    case = demo_solid_liquid_suspension_case()
    case["particle_diameter_m"] = -1.0

    passport = build_solid_liquid_suspension_passport(case)

    assert passport["status"] == "block"
    assert any("particle_diameter_m" in error for error in passport["blocking_errors"])


def test_invalid_solid_volume_fraction_fails_closed():
    case = demo_solid_liquid_suspension_case()
    case["solid_volume_fraction"] = 0.7

    passport = build_solid_liquid_suspension_passport(case)

    assert passport["status"] == "block"
    assert any("solid_volume_fraction" in error for error in passport["blocking_errors"])


def test_core_physical_calculations_are_verified():
    case = demo_solid_liquid_suspension_case()

    passport = build_solid_liquid_suspension_passport(case)
    computed = passport["computed_quantities"]
    rho_f = case["fluid_density_kg_m3"]
    mu_f = case["fluid_dynamic_viscosity_Pa_s"]
    rho_p = case["particle_density_kg_m3"]
    d_p = case["particle_diameter_m"]
    velocity = case["reference_velocity_m_s"]
    length = case["length_scale_m"]
    settling = (rho_p - rho_f) * case["gravity_m_s2"] * d_p**2 / (18.0 * mu_f)
    tau_p = rho_p * d_p**2 / (18.0 * mu_f)
    mass_loading = case["solid_volume_fraction"] * rho_p / ((1.0 - case["solid_volume_fraction"]) * rho_f)

    assert computed["particle_reynolds_number"] == pytest.approx(rho_f * max(velocity, abs(settling)) * d_p / mu_f)
    assert computed["particle_relaxation_time_s"] == pytest.approx(tau_p)
    assert computed["stokes_number"] == pytest.approx(tau_p * velocity / length)
    assert computed["settling_velocity_m_s"] == pytest.approx(settling)
    assert computed["particle_mass_loading"] == pytest.approx(mass_loading)
    assert computed["cell_particle_ratio"] == pytest.approx(case["cell_size_m"] / d_p)
    assert computed["particle_time_step_ratio"] == pytest.approx(case["time_step_s"] / tau_p)


def test_dilute_low_loading_case_recommends_dpm_one_way_or_review():
    passport = build_solid_liquid_suspension_passport(demo_solid_liquid_suspension_case())

    assert passport["computed_quantities"]["recommended_model"] in {"dpm_one_way", "review_required"}


def test_dilute_moderate_loading_case_recommends_dpm_two_way_or_review():
    case = demo_solid_liquid_suspension_case()
    case["particle_density_kg_m3"] = 40000.0

    passport = build_solid_liquid_suspension_passport(case)

    assert passport["computed_quantities"]["particle_mass_loading"] >= 0.1
    assert passport["computed_quantities"]["recommended_model"] in {"dpm_two_way", "review_required"}


def test_moderate_volume_fraction_case_recommends_mixture_or_review():
    case = demo_solid_liquid_suspension_case()
    case["solid_volume_fraction"] = 0.03
    case["relative_velocity_m_s"] = 0.01

    passport = build_solid_liquid_suspension_passport(case)

    assert passport["computed_quantities"]["solid_volume_fraction_regime"] == "moderate"
    assert passport["computed_quantities"]["recommended_model"] in {"mixture_model", "review_required"}


def test_dense_case_recommends_eulerian_multiphase_review():
    case = demo_solid_liquid_suspension_case()
    case["solid_volume_fraction"] = 0.15

    passport = build_solid_liquid_suspension_passport(case)

    assert passport["computed_quantities"]["recommended_model"] == "eulerian_multiphase_review"


def test_very_dense_case_recommends_eulerian_granular_review():
    case = demo_solid_liquid_suspension_case()
    case["solid_volume_fraction"] = 0.35

    passport = build_solid_liquid_suspension_passport(case)

    assert passport["computed_quantities"]["recommended_model"] == "eulerian_granular_review"


def test_inconsistent_cell_particle_ratio_blocks():
    case = demo_solid_liquid_suspension_case()
    case["cell_size_m"] = 10.0e-6

    passport = build_solid_liquid_suspension_passport(case)

    assert passport["status"] == "block"
    assert any("cell_particle_ratio" in error for error in passport["blocking_errors"])


def test_large_time_step_produces_warning():
    case = demo_solid_liquid_suspension_case()
    case["time_step_s"] = 0.01

    passport = build_solid_liquid_suspension_passport(case)

    assert passport["status"] in {"warn", "block"}
    assert passport["computed_quantities"]["particle_time_step_risk"] == "under_resolved"


def test_solid_liquid_passport_compiles_to_valid_solver_plan_patch_without_executable_code():
    passport = build_solid_liquid_suspension_passport(demo_solid_liquid_suspension_case())

    patch = compile_solver_plan_patch_from_passport(passport)
    validation = validate_solver_plan_patch(patch)
    text = json.dumps(patch, sort_keys=True)

    assert validation.passed
    assert _operation(patch, "/physics/multiphase/enabled")["value"] is True
    assert _operation(patch, "/physics/multiphase/model")["evidence_refs"]
    assert any(op["path"] == "/monitors/global" and op["value"]["name"] == "particle_mass_balance" for op in patch["patches"])
    assert any(op["path"] == "/monitors/global" and op["value"]["name"] == "settling_indicator" for op in patch["patches"])
    assert "udf_code" not in text
    assert "raw_pyfluent" not in text


def test_solid_liquid_hints_compile_as_review_warnings():
    passport = build_solid_liquid_suspension_passport(demo_solid_liquid_suspension_case())
    hints = build_solid_liquid_fluent_hints(passport)

    patch = compile_solver_plan_patch_from_passport(hints)

    assert validate_solver_plan_patch(patch).passed
    assert patch["status"] == "warn"
    assert all(operation["op"] == "warn" for operation in patch["patches"])


def test_solid_liquid_handoff_demo_writes_expected_tree(tmp_path):
    output_dir = tmp_path / "solid_liquid_demo"

    result = run_solid_liquid_handoff_demo(output_dir=output_dir)

    assert result["status"] in {"success", "partial"}
    for relative in [
        "solid_liquid_suspension_case.json",
        "passport/solid_liquid_suspension_passport.json",
        "passport/solid_liquid_suspension_fluent_hints.json",
        "passport/solid_liquid_suspension_report.md",
        "solver_plan_patch.json",
        "solver_plan_patch_report.md",
    ]:
        assert (output_dir / relative).exists(), relative


def test_solid_liquid_cli_write_validate_demo_and_compile(tmp_path, capsys):
    output_dir = tmp_path / "cli_demo"

    exit_code = root_main(["fastcfd", "write-solid-liquid-demo", "--output-dir", str(output_dir)])
    payload = json.loads(capsys.readouterr().out)
    case_file = output_dir / "solid_liquid_suspension_case.json"
    assert exit_code == 0
    assert payload["status"] == "success"
    assert case_file.exists()

    passport_dir = output_dir / "passport"
    exit_code = root_main(["fastcfd", "validate-solid-liquid-suspension", "--case", str(case_file), "--output-dir", str(passport_dir)])
    payload = json.loads(capsys.readouterr().out)
    passport_file = passport_dir / "solid_liquid_suspension_passport.json"
    assert exit_code == 0
    assert payload["status"] == "success"
    assert passport_file.exists()

    patch_file = output_dir / "compiled_patch.json"
    exit_code = root_main(["fastcfd", "compile-fluent-patch", "--input", str(passport_file), "--output", str(patch_file)])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert patch_file.exists()

    full_demo_dir = tmp_path / "full_cli_demo"
    exit_code = root_main(["fastcfd", "solid-liquid-handoff-demo", "--output-dir", str(full_demo_dir)])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] in {"success", "partial"}
    assert (full_demo_dir / "solver_plan_patch.json").exists()


def _operation(patch: dict, path: str) -> dict:
    for operation in patch["patches"]:
        if operation["path"] == path:
            return operation
    raise AssertionError(f"Missing operation path: {path}")

