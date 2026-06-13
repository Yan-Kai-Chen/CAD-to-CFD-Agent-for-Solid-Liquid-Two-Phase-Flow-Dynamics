from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd.cli import main as root_main
import fromcad2cfd_mesh.paths as mesh_paths
from fromcad2cfd_mesh.freecad_solidify import (
    _execution_command,
    freecad_preflight,
    run_freecad_solidify_job,
    solidify_freecad_job,
    write_solidify_freecad_job,
)
from fromcad2cfd_mesh.job_schema import read_mesh_job
from fromcad2cfd_mesh.stl import inspect_stl


CUBE_STL = """solid cube
facet normal 0 0 -1
outer loop
vertex 0 0 0
vertex 1 1 0
vertex 1 0 0
endloop
endfacet
facet normal 0 0 -1
outer loop
vertex 0 0 0
vertex 0 1 0
vertex 1 1 0
endloop
endfacet
facet normal 0 0 1
outer loop
vertex 0 0 1
vertex 1 0 1
vertex 1 1 1
endloop
endfacet
facet normal 0 0 1
outer loop
vertex 0 0 1
vertex 1 1 1
vertex 0 1 1
endloop
endfacet
facet normal 0 -1 0
outer loop
vertex 0 0 0
vertex 1 0 0
vertex 1 0 1
endloop
endfacet
facet normal 0 -1 0
outer loop
vertex 0 0 0
vertex 1 0 1
vertex 0 0 1
endloop
endfacet
facet normal 0 1 0
outer loop
vertex 0 1 0
vertex 0 1 1
vertex 1 1 1
endloop
endfacet
facet normal 0 1 0
outer loop
vertex 0 1 0
vertex 1 1 1
vertex 1 1 0
endloop
endfacet
facet normal -1 0 0
outer loop
vertex 0 0 0
vertex 0 0 1
vertex 0 1 1
endloop
endfacet
facet normal -1 0 0
outer loop
vertex 0 0 0
vertex 0 1 1
vertex 0 1 0
endloop
endfacet
facet normal 1 0 0
outer loop
vertex 1 0 0
vertex 1 1 0
vertex 1 1 1
endloop
endfacet
facet normal 1 0 0
outer loop
vertex 1 0 0
vertex 1 1 1
vertex 1 0 1
endloop
endfacet
endsolid cube
"""


def _write_cube(path: Path) -> Path:
    path.write_text(CUBE_STL, encoding="utf-8")
    return path


def test_inspect_ascii_cube_stl(tmp_path):
    source = _write_cube(tmp_path / "cube.stl")

    result = inspect_stl(source)

    assert result.format == "ascii"
    assert result.triangle_count == 12
    assert result.unique_vertex_count == 8
    assert result.boundary_edge_count == 0
    assert result.is_probably_watertight is True


def test_solidify_freecad_job_builder_records_input_summary(tmp_path):
    source = _write_cube(tmp_path / "cube.stl")

    job = solidify_freecad_job(source, tmp_path / "output", model_name="cube_solid", sew_tolerance_mm=0.1)

    assert job.operation == "solidify_mesh_freecad"
    assert job.model_name == "cube_solid"
    assert job.parameters["sew_tolerance_mm"] == 0.1
    assert job.metadata["route"] == "freecad_opencascade_mesh_to_solid"
    assert job.metadata["input_summary"]["triangle_count"] == 12
    assert job.metadata["input_summary"]["is_probably_watertight"] is True


def test_write_solidify_freecad_job_copies_input(tmp_path, monkeypatch):
    monkeypatch.setattr(mesh_paths, "PROJECTS_ROOT", tmp_path)
    source = _write_cube(tmp_path / "source_cube.stl")

    result = write_solidify_freecad_job(source, project="unit_mesh", model_name="unit_cube")
    payload = json.loads(Path(result["job_path"]).read_text(encoding="utf-8"))

    assert result["status"] == "success"
    assert payload["input_file"] != str(source)
    assert Path(payload["input_file"]).exists()
    assert payload["metadata"]["original_source_file"] == str(source)
    assert payload["metadata"]["copied_input_file"] == payload["input_file"]
    assert read_mesh_job(result["job_path"]).operation == "solidify_mesh_freecad"


def test_run_solidify_job_blocks_when_freecad_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(mesh_paths, "PROJECTS_ROOT", tmp_path)
    source = _write_cube(tmp_path / "source_cube.stl")
    written = write_solidify_freecad_job(source, project="unit_mesh_blocked", model_name="blocked_cube")

    result = run_freecad_solidify_job(written["job_path"], freecadcmd=str(tmp_path / "missing_FreeCADCmd.exe"))

    assert result["status"] == "blocked"
    assert "FreeCADCmd" in result["message"]
    assert Path(result["reports"]["json"]).exists()
    assert Path(result["reports"]["markdown"]).exists()


def test_freecad_preflight_accepts_explicit_fake_executable(tmp_path):
    fake = tmp_path / "FreeCADCmd.exe"
    fake.write_text("placeholder", encoding="utf-8")

    result = freecad_preflight(str(fake))

    assert result.status == "success"
    assert result.freecadcmd == str(fake)


def test_execution_command_prefers_bundled_freecad_python(tmp_path):
    freecadcmd = tmp_path / "FreeCADCmd.exe"
    python_dir = tmp_path / "bin"
    python_dir.mkdir()
    python_exe = python_dir / "python.exe"
    freecadcmd.write_text("placeholder", encoding="utf-8")
    python_exe.write_text("placeholder", encoding="utf-8")

    command, env, mode = _execution_command(freecadcmd, tmp_path / "script.py", tmp_path / "job.json", tmp_path / "result.json")

    assert mode == "bundled_python"
    assert command[0] == str(python_exe)
    assert str(python_dir) in env["PATH"]


def test_root_cli_writes_mesh_solidify_job(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mesh_paths, "PROJECTS_ROOT", tmp_path)
    source = _write_cube(tmp_path / "source_cube.stl")

    exit_code = root_main(
        [
            "mesh",
            "solidify-freecad",
            "--input-file",
            str(source),
            "--project",
            "unit_cli_mesh",
            "--model-name",
            "cli_cube",
            "--no-execute",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["job"]["operation"] == "solidify_mesh_freecad"
    assert Path(payload["job_path"]).exists()
