from __future__ import annotations

from copy import deepcopy

from fromcad2cfd_fastcfd.fluent_patch_compiler import compile_solver_plan_patch_from_steam_air_passport
from fromcad2cfd_fastcfd.solver_plan_patch import SOLVER_PLAN_PATCH_SCHEMA_VERSION
from fromcad2cfd_fastcfd.steam_air_condensation import build_steam_air_condensation_passport, demo_steam_air_condensation_case
from fromcad2cfd_fluent_solver.patch_preview import apply_solver_plan_patch_preview, write_patch_preview_bundle
from fromcad2cfd_fluent_solver.solver_plan_v2 import create_minimal_solver_plan_v2, validate_solver_plan_v2


def _evidence() -> dict:
    return {
        "evidence_id": "e1",
        "source_module": "unit",
        "source_artifact": "unit.json",
        "source_schema_version": "unit_schema",
        "source_status": "pass",
        "quantity_name": "q",
        "quantity_value": 1.0,
        "quantity_units": "1",
        "threshold_or_rule": "q > 0",
        "interpretation": "unit evidence",
        "confidence": "high",
        "limitations": [],
    }


def _patch(operations: list[dict], *, status: str = "pass", blocking_errors: list[str] | None = None) -> dict:
    return {
        "schema_version": SOLVER_PLAN_PATCH_SCHEMA_VERSION,
        "case_name": "unit_case",
        "created_by": "unit",
        "status": status,
        "summary": "unit patch",
        "evidence": [_evidence()],
        "patches": operations,
        "warnings": [],
        "blocking_errors": blocking_errors or [],
        "limitations": [],
        "metadata": {},
    }


def _operation(op: str, path: str, value, *, evidence_refs: list[str] | None = None) -> dict:
    return {
        "op": op,
        "path": path,
        "value": value,
        "reason": f"unit {op}",
        "evidence_refs": ["e1"] if evidence_refs is None else evidence_refs,
        "confidence": "high",
        "limitations": [],
    }


def test_valid_fastfluent_steam_air_patch_applies_to_solver_plan_v2():
    passport = build_steam_air_condensation_passport(demo_steam_air_condensation_case(), source_artifact="case.json")
    patch = compile_solver_plan_patch_from_steam_air_passport(passport, source_artifact="passport.json")
    base_plan = create_minimal_solver_plan_v2("steam_air_receiver_unit")

    result = apply_solver_plan_patch_preview(base_plan, patch)
    validation = validate_solver_plan_v2(result.patched_plan)

    assert result.preview_status == "ready_for_review"
    assert validation.is_valid
    assert result.patched_plan["physics"]["energy"]["enabled"] is True
    assert result.patched_plan["physics"]["species_transport"]["enabled"] is True
    assert result.patched_plan["monitors"]["global"]
    assert not any("initial_time_step_s is not positive" in warning for warning in result.warnings)


def test_replace_operation_updates_value():
    patch = _patch([_operation("replace", "/physics/energy/enabled", True)])

    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    assert result.preview_status == "ready_for_review"
    assert result.patched_plan["physics"]["energy"]["enabled"] is True
    assert any(item["path"] == "/physics/energy/enabled" for item in result.changed_paths)


def test_add_operation_creates_missing_allowed_field():
    patch = _patch([_operation("add", "/mesh/fluent_named_zone_review_required", True, evidence_refs=[])])

    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    assert result.preview_status == "ready_for_review"
    assert result.patched_plan["mesh"]["fluent_named_zone_review_required"] is True


def test_append_unique_operation_deduplicates_monitor_entries():
    monitor = {"name": "max_temperature", "quantity": "temperature", "required": True}
    patch = _patch(
        [
            _operation("append_unique", "/monitors/global", monitor),
            _operation("append_unique", "/monitors/global", deepcopy(monitor)),
        ]
    )

    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    assert result.preview_status == "ready_for_review"
    assert result.patched_plan["monitors"]["global"].count(monitor) == 1


def test_warn_operation_adds_warning():
    patch = _patch([_operation("warn", "/physics/energy/enabled", "review this setup")], status="warn")

    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    assert result.preview_status == "ready_for_review"
    assert any("unit warn" in warning for warning in result.warnings)


def test_block_operation_marks_preview_blocked():
    patch = _patch(
        [_operation("block", "/runtime/fluent_execution_allowed", False, evidence_refs=[])],
        status="block",
        blocking_errors=["unit block"],
    )

    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    assert result.preview_status == "blocked"
    assert result.blocking_errors
    assert result.conflicts


def test_unsupported_path_blocks_preview():
    patch = _patch([_operation("replace", "/unsafe/raw_tui", "bad", evidence_refs=[])])

    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    assert result.preview_status == "blocked"
    assert any("validation" in error.lower() for error in result.blocking_errors)


def test_dangerous_patch_value_blocks_preview():
    patch = _patch([_operation("replace", "/metadata/unit", {"raw_pyfluent": "bad"}, evidence_refs=[])])

    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    assert result.preview_status == "blocked"
    assert any("Dangerous key names" in error for error in result.blocking_errors)


def test_conflicting_replace_operations_generate_conflict_report():
    patch = _patch(
        [
            _operation("replace", "/physics/time", "steady"),
            _operation("replace", "/physics/time", "transient"),
        ]
    )

    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    assert result.preview_status == "blocked"
    assert any("conflicting_replace" in conflict["conflict_id"] for conflict in result.conflicts)


def test_attempt_to_change_execution_policy_blocks():
    patch = _patch([_operation("replace", "/runtime/execution_policy", "launch_fluent", evidence_refs=[])])

    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    assert result.preview_status == "blocked"
    assert any("preview_only" in conflict["message"] for conflict in result.conflicts)


def test_patch_preview_bundle_writes_diff_and_checklist(tmp_path):
    patch = _patch([_operation("replace", "/physics/energy/enabled", True)])
    result = apply_solver_plan_patch_preview(create_minimal_solver_plan_v2("unit"), patch)

    write_patch_preview_bundle(result, tmp_path)

    assert (tmp_path / "patched_solver_plan_preview.json").exists()
    assert (tmp_path / "before_after_diff.md").exists()
    assert (tmp_path / "reviewer_checklist.md").exists()
    assert "preview-only" in (tmp_path / "reviewer_checklist.md").read_text(encoding="utf-8")
