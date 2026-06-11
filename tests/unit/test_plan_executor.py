import pytest

from fromcad2cfd_solidworks.errors import SolidWorksOperationError
from fromcad2cfd_solidworks.plan_executor import PLAN_SCHEMA_VERSION, validate_plan


def test_validate_plan_accepts_supported_operation():
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "project": "phase5_unit_test",
        "model_name": "unit test model",
        "operations": [
            {
                "id": "base",
                "op": "create_rectangular_prism",
                "args": {"width_mm": 10, "height_mm": 8, "depth_mm": 6},
            }
        ],
    }

    normalized = validate_plan(plan)

    assert normalized["project"] == "phase5_unit_test"
    assert normalized["model_name"] == "unit_test_model"
    assert normalized["operations"][0]["op"] == "create_rectangular_prism"
    assert normalized["operations"][0]["rebuild"] is True


def test_validate_plan_rejects_unsupported_operation():
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "project": "phase5_unit_test",
        "operations": [{"op": "execute_python", "args": {"code": "print(1)"}}],
    }

    with pytest.raises(SolidWorksOperationError, match="unsupported op"):
        validate_plan(plan)


def test_validate_plan_rejects_project_path_traversal():
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "project": "..\\outside",
        "operations": [{"op": "create_rectangular_prism", "args": {"width_mm": 10, "height_mm": 8, "depth_mm": 6}}],
    }

    with pytest.raises(SolidWorksOperationError, match="workspace project name"):
        validate_plan(plan)

