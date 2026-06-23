from __future__ import annotations

import pytest

from fromcad2cfd_fastcfd.solver_plan_patch import (
    SOLVER_PLAN_PATCH_SCHEMA_VERSION,
    validate_solver_plan_patch,
    write_solver_plan_patch_report,
)


def _evidence(evidence_id: str = "e1") -> dict:
    return {
        "evidence_id": evidence_id,
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


def _patch() -> dict:
    return {
        "schema_version": SOLVER_PLAN_PATCH_SCHEMA_VERSION,
        "case_name": "unit_case",
        "created_by": "unit",
        "status": "pass",
        "summary": "unit patch",
        "evidence": [_evidence()],
        "patches": [
            {
                "op": "replace",
                "path": "/physics/energy/enabled",
                "value": True,
                "reason": "unit",
                "evidence_refs": ["e1"],
                "confidence": "high",
                "limitations": [],
            }
        ],
        "warnings": [],
        "blocking_errors": [],
        "limitations": [],
        "metadata": {},
    }


def test_valid_solver_plan_patch_passes():
    result = validate_solver_plan_patch(_patch())

    assert result.passed
    assert result.checked_patch_count == 1
    assert result.checked_evidence_count == 1


def test_unsupported_path_fails():
    patch = _patch()
    patch["patches"][0]["path"] = "/unsafe/raw_tui"

    result = validate_solver_plan_patch(patch)

    assert not result.passed
    assert any("outside allowlist" in error for error in result.errors)


def test_dangerous_key_fails():
    patch = _patch()
    patch["patches"][0]["value"] = {"raw_tui": "/solve/iterate 100"}

    result = validate_solver_plan_patch(patch)

    assert not result.passed
    assert any("Dangerous key names" in error for error in result.errors)


@pytest.mark.parametrize("path", ["/physics/energy/enabled", "/source_terms/condensation/model"])
def test_evidence_required_paths_fail_without_refs(path):
    patch = _patch()
    patch["patches"][0]["path"] = path
    patch["patches"][0]["evidence_refs"] = []

    result = validate_solver_plan_patch(patch)

    assert not result.passed
    assert any("requires evidence_refs" in error for error in result.errors)


def test_empty_pass_patch_fails_but_block_patch_can_pass():
    patch = _patch()
    patch["patches"] = []
    assert not validate_solver_plan_patch(patch).passed

    block_patch = _patch()
    block_patch["status"] = "block"
    block_patch["patches"] = []
    block_patch["blocking_errors"] = ["blocked by unit test"]
    assert validate_solver_plan_patch(block_patch).passed


def test_append_unique_monitor_patch_validates_and_report_writes(tmp_path):
    patch = _patch()
    patch["patches"][0] = {
        "op": "append_unique",
        "path": "/monitors/global",
        "value": {"name": "max_temperature", "required": True},
        "reason": "unit monitor",
        "evidence_refs": ["e1"],
        "confidence": "high",
        "limitations": [],
    }

    result = validate_solver_plan_patch(patch)
    report = write_solver_plan_patch_report(patch, tmp_path / "solver_plan_patch_report.md")

    assert result.passed
    assert report.exists()
    assert "Reviewer Checklist" in report.read_text(encoding="utf-8")
