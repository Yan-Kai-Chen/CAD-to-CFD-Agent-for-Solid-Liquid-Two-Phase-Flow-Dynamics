from __future__ import annotations

import json

from fromcad2cfd_fastcfd.fluent_patch_compiler import compile_solver_plan_patch_from_passport
from fromcad2cfd_fastcfd.solver_plan_patch import validate_solver_plan_patch
from fromcad2cfd_fastcfd.wax_rheology_phase_change import (
    build_wax_rheology_phase_change_fluent_hints,
    build_wax_rheology_phase_change_passport,
    compile_wax_rheology_phase_change_patch,
    create_demo_wax_rheology_case,
)


def test_wax_passport_compiles_to_valid_solver_plan_patch_without_executable_code():
    passport = build_wax_rheology_phase_change_passport(create_demo_wax_rheology_case())

    patch = compile_wax_rheology_phase_change_patch(passport, source_artifact="wax_passport.json")
    validation = validate_solver_plan_patch(patch)
    text = json.dumps(patch, sort_keys=True)

    assert validation.passed
    assert patch["status"] in {"pass", "warn"}
    assert _operation(patch, "/physics/energy/enabled")["value"] is True
    assert _operation(patch, "/physics/material_model")["value"] in {
        "arrhenius_viscosity",
        "temperature_dependent_viscosity",
        "softening_transition_review",
        "phase_change_review_required",
    }
    assert _operation(patch, "/source_terms/phase_change/model")["value"] == "review-required"
    assert _operation(patch, "/numerics/source_term_controls/ramping")["value"] is True
    assert _operation(patch, "/numerics/source_term_controls/clamp")["value"] is True
    assert _operation(patch, "/transient/initial_time_step_s")["value"] > 0
    assert any(op["path"] == "/monitors/global" and op["value"]["name"] == "temperature_min_max" for op in patch["patches"])
    assert any(op["path"] == "/monitors/global" and op["value"]["name"] == "phase_change_source_integral_if_available" for op in patch["patches"])
    assert any(item["evidence_id"] == "wax_arrhenius_viscosity" for item in patch["evidence"])
    assert "udf_code" not in text
    assert "source_code" not in text
    assert "raw_pyfluent" not in text


def test_generic_patch_compiler_auto_detects_wax_passport():
    passport = build_wax_rheology_phase_change_passport(create_demo_wax_rheology_case())

    patch = compile_solver_plan_patch_from_passport(passport)

    assert validate_solver_plan_patch(patch).passed
    assert _operation(patch, "/physics/energy/enabled")["value"] is True
    assert patch["metadata"]["compiler"] == "wax_rheology_phase_change"


def test_wax_hints_compile_as_review_warnings():
    passport = build_wax_rheology_phase_change_passport(create_demo_wax_rheology_case())
    hints = build_wax_rheology_phase_change_fluent_hints(passport)

    patch = compile_solver_plan_patch_from_passport(hints)

    assert validate_solver_plan_patch(patch).passed
    assert patch["status"] == "warn"
    assert all(operation["op"] == "warn" for operation in patch["patches"])


def test_blocked_wax_passport_compiles_to_block_patch():
    case = create_demo_wax_rheology_case()
    case["time_step_s"] = -1.0
    passport = build_wax_rheology_phase_change_passport(case)

    patch = compile_solver_plan_patch_from_passport(passport)

    assert validate_solver_plan_patch(patch).passed
    assert patch["status"] == "block"
    assert patch["blocking_errors"]
    assert _operation(patch, "/runtime/fluent_execution_allowed")["value"] is False


def _operation(patch: dict, path: str) -> dict:
    for operation in patch["patches"]:
        if operation["path"] == path:
            return operation
    raise AssertionError(f"Missing operation path: {path}")
