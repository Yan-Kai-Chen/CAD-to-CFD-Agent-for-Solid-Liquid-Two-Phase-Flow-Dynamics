from __future__ import annotations

from pathlib import Path

from fromcad2cfd_hypermesh_meshing.runtime import locate_hypermesh_runtime
from fromcad2cfd_hypermesh_meshing.schemas import (
    MESHING_PLAN_SCHEMA_VERSION,
    hypermesh_python_template,
    hypermesh_tcl_template,
    validate_meshing_plan,
)
from fromcad2cfd_mcp_hypermesh_meshing.server import server_descriptor


def _valid_plan() -> dict[str, object]:
    return {
        "schema_version": MESHING_PLAN_SCHEMA_VERSION,
        "plan_name": "unit_hypermesh_plan",
        "geometry_input": "sandbox/input/unit.step",
        "hypermesh_model_output": "sandbox/output/unit.hm",
        "fluent_mesh_output": "sandbox/output/unit.msh",
        "units": {"length_unit": "mm", "scale_to_m": 0.001},
        "boundaries": {
            "inlet": {"type": "inlet", "description": "inlet face"},
            "outlet": {"type": "outlet", "description": "outlet face"},
            "outer_wall": {"type": "wall", "description": "outer wall"},
            "model_wall": {"type": "wall", "description": "model wall"},
        },
        "surface_mesh": {"target_size_mm": 5.0, "min_size_mm": 1.0},
        "boundary_layer": {"enabled": True, "first_height_mm": 0.1, "layers": 5, "growth_rate": 1.2},
        "volume_mesh": {"method": "hybrid_prism_tetra", "target_size_mm": 8.0},
        "quality": {"max_skewness": 0.9, "max_aspect_ratio": 20.0},
        "export": {"format": "fluent_msh"},
    }


def test_validate_hypermesh_meshing_plan_passes() -> None:
    result = validate_meshing_plan(_valid_plan())

    assert result["status"] == "passed"
    assert result["boundary_count"] == 4


def test_validate_hypermesh_meshing_plan_rejects_absolute_public_path() -> None:
    plan = _valid_plan()
    plan["geometry_input"] = str(Path.cwd() / "sandbox" / "input" / "unit.step")

    result = validate_meshing_plan(plan)

    assert result["status"] == "failed"
    assert any("geometry_input" in item for item in result["errors"])


def test_hypermesh_templates_include_plan_name() -> None:
    plan = _valid_plan()

    python_text = hypermesh_python_template(plan)
    tcl_text = hypermesh_tcl_template(plan)

    assert "unit_hypermesh_plan" in python_text
    assert "unit_hypermesh_plan" in tcl_text
    assert "template_only" in python_text
    assert "template_only" in tcl_text


def test_runtime_discovery_accepts_missing_extra_root() -> None:
    result = locate_hypermesh_runtime(["sandbox/missing_altair_root"])

    assert result["status"] in {"found", "not_found"}
    assert "candidates" in result


def test_mcp_descriptor_lists_safe_hypermesh_tools() -> None:
    descriptor = server_descriptor()

    assert descriptor["name"] == "fromcad2cfd-hypermesh-meshing"
    assert "fromcad2cfd_hypermesh_meshing_validate_plan" in descriptor["allowed_tools"]
    assert "execute_tcl" in descriptor["disabled_tools"]
