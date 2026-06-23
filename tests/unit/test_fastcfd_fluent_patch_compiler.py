from __future__ import annotations

from fromcad2cfd_fastcfd.fluent_patch_compiler import (
    compile_solver_plan_patch_from_passport,
    compile_solver_plan_patch_from_steam_air_passport,
    merge_solver_plan_patches,
)
from fromcad2cfd_fastcfd.solver_plan_patch import validate_solver_plan_patch
from fromcad2cfd_fastcfd.steam_air_condensation import build_steam_air_condensation_passport, demo_steam_air_condensation_case


def test_steam_air_passport_compiles_to_valid_solver_plan_patch(tmp_path):
    passport = build_steam_air_condensation_passport(demo_steam_air_condensation_case(), source_artifact="case.json")

    patch = compile_solver_plan_patch_from_steam_air_passport(passport, source_artifact="passport.json")
    validation = validate_solver_plan_patch(patch)

    assert validation.passed
    assert patch["schema_version"] == "fromcad2cfd_fastfluent_solver_plan_patch_v1"
    assert patch["patches"]


def test_physics_and_monitor_patches_include_evidence_refs():
    passport = build_steam_air_condensation_passport(demo_steam_air_condensation_case())

    patch = compile_solver_plan_patch_from_passport(passport)

    for operation in patch["patches"]:
        if operation["path"].startswith(("/physics", "/monitors", "/source_terms", "/transient", "/numerics")) and operation["op"] not in {
            "block",
            "warn",
        }:
            assert operation["evidence_refs"], operation


def test_high_source_stiffness_creates_warning_or_block_patch():
    case = demo_steam_air_condensation_case()
    case["time_step_s"] = 0.05
    passport = build_steam_air_condensation_passport(case)

    patch = compile_solver_plan_patch_from_passport(passport)

    assert patch["status"] in {"warn", "block"}
    assert patch["warnings"] or patch["blocking_errors"]


def test_conflicting_patch_merge_records_warning():
    passport = build_steam_air_condensation_passport(demo_steam_air_condensation_case())
    patch_a = compile_solver_plan_patch_from_passport(passport)
    patch_b = compile_solver_plan_patch_from_passport(passport)
    for operation in patch_b["patches"]:
        if operation["path"] == "/physics/time":
            operation["value"] = "steady"
            break

    merged = merge_solver_plan_patches([patch_a, patch_b])
    validation = validate_solver_plan_patch(merged)

    assert validation.passed
    assert merged["status"] in {"warn", "block"}
    assert any("Conflicting replace patch" in warning for warning in merged["warnings"])
