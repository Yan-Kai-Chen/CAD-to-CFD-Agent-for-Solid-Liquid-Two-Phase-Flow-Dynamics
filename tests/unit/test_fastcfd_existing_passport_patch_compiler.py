from __future__ import annotations

import json

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fastcfd.fluent_patch_compiler import (
    compile_rheology_patch_from_artifact,
    compile_solver_plan_patch_from_passport,
    compile_turbulence_patch_from_artifact,
    compile_vof_patch_from_artifact,
    merge_solver_plan_patches,
)
from fromcad2cfd_fastcfd.rheology import build_rheology_passport, demo_rheology_case
from fromcad2cfd_fastcfd.solver_plan_patch import validate_solver_plan_patch
from fromcad2cfd_fastcfd.turbulence import TurbulenceCase, build_turbulence_passport, demo_turbulence_case
from fromcad2cfd_fastcfd.vof import build_vof_physics_passport, demo_vof_case


def test_vof_passport_compiles_to_valid_solver_plan_patch():
    passport = build_vof_physics_passport(demo_vof_case())

    patch = compile_vof_patch_from_artifact(passport, source_artifact="vof_passport.json")
    validation = validate_solver_plan_patch(patch)

    assert validation.passed
    assert patch["status"] == "pass"
    assert _operation(patch, "/physics/multiphase/model")["value"] == "vof"
    assert _operation(patch, "/physics/multiphase/model")["evidence_refs"]
    assert any(op["op"] == "append_unique" and op["path"] == "/monitors/global" for op in patch["patches"])


def test_turbulence_passport_compiles_to_valid_solver_plan_patch():
    passport = build_turbulence_passport(demo_turbulence_case())

    patch = compile_turbulence_patch_from_artifact(passport, source_artifact="turbulence_passport.json")
    validation = validate_solver_plan_patch(patch)

    assert validation.passed
    assert _operation(patch, "/physics/turbulence/model")["value"] == "k-omega-sst"
    assert _operation(patch, "/physics/turbulence/model")["evidence_refs"]
    assert any(op["path"] == "/monitors/global" and op["value"]["name"] == "wall_y_plus" for op in patch["patches"])


def test_transitional_turbulence_uses_review_required_instead_of_overclaim():
    case = TurbulenceCase(
        case_name="transitional_unit",
        domain={"geometry_kind": "pipe", "length_scale_mm": 10.0, "hydraulic_diameter_mm": 10.0},
        fluid={"name": "water", "density_kg_m3": 1000.0, "dynamic_viscosity_pa_s": 1.0e-3},
        reference_velocity_m_s=0.3,
        model_intent="rans_sst",
        turbulence_intensity_percent=5.0,
        first_cell_height_mm=0.02,
    )
    passport = build_turbulence_passport(case)

    patch = compile_turbulence_patch_from_artifact(passport)

    assert validate_solver_plan_patch(patch).passed
    assert patch["status"] == "warn"
    assert _operation(patch, "/physics/turbulence/model")["value"] == "review-required"
    assert any("transitional" in warning.lower() for warning in patch["warnings"])


def test_rheology_passport_compiles_to_valid_solver_plan_patch_without_udf_code():
    passport = build_rheology_passport(demo_rheology_case())

    patch = compile_rheology_patch_from_artifact(passport, source_artifact="rheology_passport.json")
    validation = validate_solver_plan_patch(patch)
    text = json.dumps(patch, sort_keys=True)

    assert validation.passed
    assert _operation(patch, "/physics/material_model")["value"] == "non-newtonian-review-required"
    assert any(op["path"] == "/monitors/global" and op["value"]["name"] == "viscosity_min_max" for op in patch["patches"])
    assert "udf_code" not in text
    assert "raw_pyfluent" not in text


def test_compile_solver_plan_patch_auto_detects_existing_passport_schemas():
    passports = [
        build_vof_physics_passport(demo_vof_case()),
        build_turbulence_passport(demo_turbulence_case()),
        build_rheology_passport(demo_rheology_case()),
    ]

    patches = [compile_solver_plan_patch_from_passport(passport) for passport in passports]

    assert all(validate_solver_plan_patch(patch).passed for patch in patches)


def test_existing_patches_merge_preserves_evidence_and_deduplicates_append_unique():
    vof_patch = compile_vof_patch_from_artifact(build_vof_physics_passport(demo_vof_case()))
    duplicate_vof_patch = compile_vof_patch_from_artifact(build_vof_physics_passport(demo_vof_case()))
    turbulence_patch = compile_turbulence_patch_from_artifact(build_turbulence_passport(demo_turbulence_case()))
    rheology_patch = compile_rheology_patch_from_artifact(build_rheology_passport(demo_rheology_case()))

    merged = merge_solver_plan_patches([vof_patch, duplicate_vof_patch, turbulence_patch, rheology_patch])
    validation = validate_solver_plan_patch(merged)
    monitor_keys = [json.dumps([op["path"], op.get("value")], sort_keys=True) for op in merged["patches"] if op["op"] == "append_unique"]

    assert validation.passed
    assert len(merged["evidence"]) >= len(vof_patch["evidence"]) + len(turbulence_patch["evidence"]) + len(rheology_patch["evidence"])
    assert len(monitor_keys) == len(set(monitor_keys))


def test_conflicting_replace_patch_is_reported_by_merge():
    vof_patch = compile_vof_patch_from_artifact(build_vof_physics_passport(demo_vof_case()))
    conflict_patch = json.loads(json.dumps(vof_patch))
    for operation in conflict_patch["patches"]:
        if operation["op"] == "replace" and operation["path"] == "/physics/multiphase/model":
            operation["value"] = "eulerian"
            break

    merged = merge_solver_plan_patches([vof_patch, conflict_patch])

    assert validate_solver_plan_patch(merged).passed
    assert merged["status"] in {"warn", "block"}
    assert any("Conflicting replace patch" in warning for warning in merged["warnings"])


def test_existing_passport_patch_demo_cli_writes_expected_tree(tmp_path, capsys):
    output_dir = tmp_path / "h1_demo"

    exit_code = root_main(["fastcfd", "existing-passport-patch-demo", "--output-dir", str(output_dir)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] in {"success", "partial"}
    for relative in [
        "vof/vof_input_or_passport.json",
        "vof/solver_plan_patch.json",
        "vof/solver_plan_patch_report.md",
        "turbulence/turbulence_input_or_passport.json",
        "turbulence/solver_plan_patch.json",
        "turbulence/solver_plan_patch_report.md",
        "rheology/rheology_input_or_passport.json",
        "rheology/solver_plan_patch.json",
        "rheology/solver_plan_patch_report.md",
        "combined/combined_solver_plan_patch.json",
        "combined/combined_solver_plan_patch_report.md",
        "combined/conflict_summary.json",
    ]:
        assert (output_dir / relative).exists(), relative


def test_compile_fluent_patch_cli_auto_detects_vof_passport_and_fails_closed_for_unknown(tmp_path, capsys):
    passport_path = tmp_path / "vof_passport.json"
    output_path = tmp_path / "solver_plan_patch.json"
    passport_path.write_text(json.dumps(build_vof_physics_passport(demo_vof_case())), encoding="utf-8")

    exit_code = root_main(["fastcfd", "compile-fluent-patch", "--input", str(passport_path), "--output", str(output_path)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert output_path.exists()

    unsupported_path = tmp_path / "unsupported.json"
    unsupported_output = tmp_path / "unsupported_patch.json"
    unsupported_path.write_text(json.dumps({"schema_version": "unknown", "case_name": "bad"}), encoding="utf-8")

    exit_code = root_main(["fastcfd", "compile-fluent-patch", "--input", str(unsupported_path), "--output", str(unsupported_output)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["status"] == "failed"
    assert any("Unsupported evidence schema" in error for error in payload["errors"])


def _operation(patch: dict, path: str) -> dict:
    for operation in patch["patches"]:
        if operation["path"] == path:
            return operation
    raise AssertionError(f"Missing operation path: {path}")
