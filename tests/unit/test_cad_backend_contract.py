from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_cad import (
    AgentResult,
    BackendRegistration,
    BackendRegistry,
    CADBackend,
    CADBackendCapabilities,
    ExportManifest,
    GeometryRecipe,
    ModelInspection,
    ParameterEditRequest,
)
from fromcad2cfd_cad.formats import is_cfd_preferred_format, normalize_export_format


class DummyBackend:
    name = "dummy"

    def preflight(self) -> AgentResult:
        return AgentResult.success(backend=self.name, operation="preflight")

    def create_test_geometry(self, recipe: GeometryRecipe) -> AgentResult:
        return AgentResult.success(
            backend=self.name,
            operation="create_test_geometry",
            metadata={"recipe": recipe.recipe_name},
        )

    def inspect_model(self, input_file: str | Path) -> AgentResult:
        return AgentResult.success(backend=self.name, operation="inspect_model", outputs={"input_file": str(input_file)})

    def copy_model_for_edit(self, input_file: str | Path, output_dir: str | Path) -> AgentResult:
        return AgentResult.success(
            backend=self.name,
            operation="copy_model_for_edit",
            outputs={"input_file": str(input_file), "output_dir": str(output_dir)},
        )

    def edit_parameter_by_exact_name(self, request: ParameterEditRequest) -> AgentResult:
        return AgentResult.success(
            backend=self.name,
            operation="edit_parameter_by_exact_name",
            metadata={"parameter_name": request.parameter_name, "value_mm": request.value_mm},
        )

    def rebuild_and_validate(self, model_file: str | Path) -> AgentResult:
        return AgentResult.success(backend=self.name, operation="rebuild_and_validate", outputs={"model_file": str(model_file)})

    def export_geometry(self, model_file: str | Path, fmt: str, output_dir: str | Path) -> AgentResult:
        return AgentResult.success(
            backend=self.name,
            operation="export_geometry",
            outputs={"model_file": str(model_file), "format": normalize_export_format(fmt), "output_dir": str(output_dir)},
        )

    def write_report(self, result: AgentResult) -> AgentResult:
        return AgentResult.success(backend=self.name, operation="write_report", metadata={"source_operation": result.operation})


def test_agent_result_serializes():
    result = AgentResult.success(
        backend="solidworks",
        operation="preflight",
        message="ready",
        outputs={"revision": "33.3.0"},
    )

    assert result.ok is True
    assert result.to_dict()["status"] == "success"
    assert json.dumps(result.to_dict())


def test_failed_agent_result_contains_error():
    result = AgentResult.failed(backend="nx", operation="preflight", message="NX is not available")

    assert result.ok is False
    assert result.errors == ["NX is not available"]


def test_geometry_recipe_requires_named_parameter():
    recipe = GeometryRecipe(
        recipe_name="cylinder",
        model_name="unit_cylinder",
        parameters_mm={"radius_mm": 10.0, "height_mm": 20.0},
    )

    assert recipe.require_parameter_mm("radius_mm") == 10.0


def test_geometry_recipe_rejects_missing_parameter():
    recipe = GeometryRecipe(recipe_name="cylinder", model_name="unit_cylinder")

    try:
        recipe.require_parameter_mm("radius_mm")
    except ValueError as exc:
        assert "radius_mm" in str(exc)
    else:
        raise AssertionError("Expected missing parameter to fail")


def test_export_format_normalization():
    assert normalize_export_format("step") == "STEP"
    assert normalize_export_format("x_t") == "PARASOLID"
    assert is_cfd_preferred_format("parasolid") is True
    assert is_cfd_preferred_format("stl") is False


def test_manifest_and_inspection_are_serializable():
    inspection = ModelInspection(
        backend="nx",
        input_file="input.prt",
        features=[{"name": "EXTRUDE_1"}],
        parameters=[{"name": "radius", "value_mm": 10.0}],
    )
    manifest = ExportManifest(
        backend="nx",
        source_model="model.prt",
        exported_file="model.step",
        format="STEP",
    )

    assert inspection.to_dict()["features"][0]["name"] == "EXTRUDE_1"
    assert manifest.to_dict()["format"] == "STEP"


def test_backend_protocol_and_registry():
    registry = BackendRegistry()
    capabilities = CADBackendCapabilities(
        backend="dummy",
        status="test",
        native_formats=("PRT",),
        export_formats=("STEP", "PARASOLID"),
    )
    registry.register(
        BackendRegistration(
            name="dummy",
            description="Dummy test backend.",
            capabilities=capabilities,
            factory=DummyBackend,
        )
    )

    backend = registry.create("dummy")
    assert isinstance(backend, CADBackend)
    assert registry.names() == ["dummy"]
    assert registry.describe()[0]["capabilities"]["export_formats"] == ["STEP", "PARASOLID"]


def test_root_cli_exposes_cad_contract(capsys):
    exit_code = root_main(["cad", "contract"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "fromcad2cfd_cad_backend_contract_v1" in captured.out
