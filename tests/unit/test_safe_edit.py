from pathlib import Path

import pytest

from fromcad2cfd_solidworks.errors import SolidWorksOperationError
from fromcad2cfd_solidworks.paths import WORKSPACE_ROOT, unique_path
from fromcad2cfd_solidworks.safe_edit import SAFE_EDIT_SCHEMA_VERSION, resolve_unique_dimension, validate_safe_edit_plan


def test_resolve_unique_dimension_accepts_single_parameter_match():
    dimensions = [
        {"parameter_name": "D1@Boss-Extrude1", "feature_name": "Boss-Extrude1", "name": "D1"},
        {"parameter_name": "D1@Boss-Extrude2", "feature_name": "Boss-Extrude2", "name": "D1"},
    ]

    match = resolve_unique_dimension(dimensions, {"parameter_name": "D1@Boss-Extrude1"})

    assert match["feature_name"] == "Boss-Extrude1"


def test_resolve_unique_dimension_rejects_ambiguous_selector():
    dimensions = [
        {"parameter_name": "D1@Boss-Extrude1", "feature_name": "Boss-Extrude1", "name": "D1"},
        {"parameter_name": "D1@Boss-Extrude2", "feature_name": "Boss-Extrude2", "name": "D1"},
    ]

    with pytest.raises(SolidWorksOperationError, match="exactly one"):
        resolve_unique_dimension(dimensions, {"name": "D1"})


def test_validate_safe_edit_plan_rejects_nonexistent_input():
    plan = {
        "schema_version": SAFE_EDIT_SCHEMA_VERSION,
        "project": "phase6_unit_test",
        "input_file": str(Path("05_projects") / "missing" / "missing.SLDPRT"),
        "edits": [{"type": "set_dimension", "selector": {"parameter_name": "D1@Boss-Extrude1"}, "value_mm": 20}],
    }

    with pytest.raises(SolidWorksOperationError, match="does not exist"):
        validate_safe_edit_plan(plan)


def test_validate_safe_edit_plan_rejects_unsupported_edit_type():
    source = unique_path(WORKSPACE_ROOT / "06_logs" / "unit_test_safe_edit_source.SLDPRT")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"not a real part")
    plan = {
        "schema_version": SAFE_EDIT_SCHEMA_VERSION,
        "project": "phase6_unit_test",
        "input_file": str(source),
        "edits": [{"type": "execute_python", "selector": {"parameter_name": "D1@Boss-Extrude1"}, "value_mm": 20}],
    }

    with pytest.raises(SolidWorksOperationError):
        validate_safe_edit_plan(plan)

