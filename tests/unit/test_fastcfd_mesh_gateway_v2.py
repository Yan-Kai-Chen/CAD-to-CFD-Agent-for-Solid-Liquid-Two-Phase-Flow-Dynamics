from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.mesh.mesh_gateway import generate_structured_mesh_demo, inspect_mesh_gateway
from fromcad2cfd_fastcfd.mesh.structured_grid import build_structured_grid_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
CHANNEL_MESH = REPO_ROOT / "examples" / "unstructured" / "channel2d.msh"


def test_mesh_gateway_inspect_wraps_existing_unstructured_route(tmp_path):
    result = inspect_mesh_gateway(CHANNEL_MESH, output_dir=tmp_path / "inspect")

    assert result["status"] == "success"
    assert result["outputs"]["mesh_gateway_schema_version"] == "fastfluent_mesh_gateway_v2"
    assert Path(result["outputs"]["artifacts"]["mesh_manifest"]).exists()
    assert Path(result["outputs"]["artifacts"]["mesh_quality"]).exists()
    assert Path(result["outputs"]["artifacts"]["fv_geometry"]).exists()


def test_mesh_gateway_structured_manifest_counts():
    manifest = build_structured_grid_manifest(nx=10, ny=4, length_m=1.0, height_m=0.2)

    assert manifest["schema_version"] == "fastfluent_structured_grid_v1"
    assert manifest["node_count"] == 55
    assert manifest["cell_count"] == 40
    assert manifest["boundary_zone_counts"]["inlet"] == 4
    assert manifest["boundary_zone_counts"]["top_wall"] == 10


def test_mesh_gateway_generate_structured_demo_writes_artifacts(tmp_path):
    result = generate_structured_mesh_demo(tmp_path / "structured", nx=10, ny=4, length_m=1.0, height_m=0.2)

    assert result["status"] == "success"
    artifacts = result["outputs"]["artifacts"]
    for key in ["mesh_manifest", "mesh_quality", "fv_geometry", "mesh_quality_report", "mesh_vtu", "mesh_gateway_status"]:
        assert Path(artifacts[key]).exists()
    manifest = json.loads(Path(artifacts["mesh_manifest"]).read_text(encoding="utf-8"))
    quality = json.loads(Path(artifacts["mesh_quality"]).read_text(encoding="utf-8"))
    assert manifest["cell_count"] == 40
    assert quality["status"] == "passed"


def test_mesh_gateway_cli_inspect(tmp_path, capsys):
    exit_code = fastcfd_main(
        [
            "mesh",
            "inspect",
            str(CHANNEL_MESH),
            "--output-dir",
            str(tmp_path / "inspect"),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["outputs"]["mesh_gateway_schema_version"] == "fastfluent_mesh_gateway_v2"


def test_mesh_gateway_cli_generate_structured_demo(tmp_path, capsys):
    exit_code = fastcfd_main(
        [
            "mesh",
            "generate-structured-demo",
            "--output-dir",
            str(tmp_path / "structured"),
            "--nx",
            "10",
            "--ny",
            "4",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["mesh_vtu"]).exists()
