"""Mesh Gateway v2 public workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fromcad2cfd_fastcfd.file_io import ensure_dir, write_json_file, write_text_file
from fromcad2cfd_fastcfd.unstructured.inspect import inspect_mesh_file

from .structured_grid import (
    build_structured_fv_geometry,
    build_structured_grid_manifest,
    build_structured_grid_quality,
    structured_grid_report,
    structured_grid_vtu,
)


MESH_GATEWAY_SCHEMA_VERSION = "fastfluent_mesh_gateway_v2"


def inspect_mesh_gateway(
    mesh_file: str | Path,
    *,
    output_dir: str | Path,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Inspect a mesh through the Mesh Gateway v2 facade."""

    result = inspect_mesh_file(mesh_file, output_dir=output_dir, required_patches=required_patches, write_vtu=True)
    result.setdefault("outputs", {})["mesh_gateway_schema_version"] = MESH_GATEWAY_SCHEMA_VERSION
    return result


def generate_structured_mesh_demo(
    output_dir: str | Path,
    *,
    nx: int = 20,
    ny: int = 8,
    length_m: float = 1.0,
    height_m: float = 0.1,
) -> dict[str, Any]:
    """Generate a public-safe structured mesh gateway demo."""

    root = Path(output_dir)
    ensure_dir(root)
    manifest = build_structured_grid_manifest(nx=nx, ny=ny, length_m=length_m, height_m=height_m)
    quality = build_structured_grid_quality(manifest)
    fv_geometry = build_structured_fv_geometry(manifest)
    artifacts = {
        "mesh_manifest": str(root / "mesh_manifest.json"),
        "mesh_quality": str(root / "mesh_quality.json"),
        "fv_geometry": str(root / "fv_geometry.json"),
        "mesh_quality_report": str(root / "mesh_quality_report.md"),
        "mesh_vtu": str(root / "mesh.vtu"),
        "mesh_gateway_status": str(root / "mesh_status.json"),
    }
    _write_json(root / "mesh_manifest.json", manifest)
    _write_json(root / "mesh_quality.json", quality)
    _write_json(root / "fv_geometry.json", fv_geometry)
    _write_text(root / "mesh_quality_report.md", structured_grid_report(manifest, quality))
    _write_text(root / "mesh.vtu", structured_grid_vtu(manifest))
    result = {
        "status": "success",
        "backend": "mesh_gateway_v2",
        "operation": "generate_structured_demo",
        "message": "Structured Mesh Gateway v2 demo generated.",
        "outputs": {
            "mesh_gateway_schema_version": MESH_GATEWAY_SCHEMA_VERSION,
            "artifacts": artifacts,
            "manifest": manifest,
            "quality": quality,
            "fv_geometry": fv_geometry,
            "solver_execution": "not_attempted",
        },
        "errors": [],
        "metadata": {"output_dir": str(root)},
    }
    _write_json(root / "mesh_status.json", result)
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return write_json_file(path, payload)


def _write_text(path: Path, text: str) -> Path:
    return write_text_file(path, text)
