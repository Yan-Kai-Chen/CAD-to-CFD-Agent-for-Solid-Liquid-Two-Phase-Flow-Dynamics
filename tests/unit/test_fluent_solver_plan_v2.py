from __future__ import annotations

from fromcad2cfd_fluent_solver.solver_plan_v2 import (
    SOLVER_PLAN_V2_SCHEMA_VERSION,
    create_minimal_solver_plan_v2,
    validate_solver_plan_v2,
    write_solver_plan_v2_report,
)


def test_create_minimal_solver_plan_v2_returns_valid_plan():
    plan = create_minimal_solver_plan_v2("unit_plan_v2")

    result = validate_solver_plan_v2(plan)

    assert plan["schema_version"] == SOLVER_PLAN_V2_SCHEMA_VERSION
    assert result.is_valid
    assert result.status == "passed"
    assert result.normalized_plan["status"] == "ready_for_review"
    assert result.normalized_plan["runtime"]["execution_policy"] == "preview_only"


def test_solver_plan_v2_rejects_unsupported_schema_version():
    plan = create_minimal_solver_plan_v2("unit_plan_v2")
    plan["schema_version"] = "wrong"

    result = validate_solver_plan_v2(plan)

    assert not result.is_valid
    assert any("schema_version" in error for error in result.blocking_errors)


def test_solver_plan_v2_rejects_dangerous_keys():
    plan = create_minimal_solver_plan_v2("unit_plan_v2")
    plan["metadata"]["raw_pyfluent"] = "solver.tui.solve.iterate(10)"

    result = validate_solver_plan_v2(plan)

    assert not result.is_valid
    assert any("Dangerous key names" in error for error in result.blocking_errors)


def test_solver_plan_v2_warns_when_transient_time_step_missing():
    plan = create_minimal_solver_plan_v2("unit_plan_v2")

    result = validate_solver_plan_v2(plan)

    assert result.is_valid
    assert any("initial_time_step_s" in warning for warning in result.warnings)


def test_solver_plan_v2_rejects_non_preview_execution_policy():
    plan = create_minimal_solver_plan_v2("unit_plan_v2")
    plan["runtime"]["execution_policy"] = "launch_fluent"

    result = validate_solver_plan_v2(plan)

    assert not result.is_valid
    assert any("preview_only" in error for error in result.blocking_errors)


def test_solver_plan_v2_report_writer_creates_markdown(tmp_path):
    plan = create_minimal_solver_plan_v2("unit_plan_v2")
    report_path = tmp_path / "base_solver_plan_v2_report.md"

    write_solver_plan_v2_report(plan, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "Fluent Solver Plan v2 Preview Report" in text
    assert "preview-only" in text
