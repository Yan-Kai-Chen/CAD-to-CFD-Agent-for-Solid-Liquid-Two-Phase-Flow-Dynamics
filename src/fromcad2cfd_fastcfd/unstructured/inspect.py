"""Top-level unstructured mesh inspection workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .geometry import build_fv_geometry
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .vtu import write_mesh_vtu


def inspect_mesh_file(
    mesh_file: str | Path,
    *,
    output_dir: str | Path | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
    write_vtu: bool = True,
) -> dict[str, Any]:
    mesh_path = Path(mesh_file)
    target_dir = Path(output_dir) if output_dir else unique_path(mesh_path.parent / f"{mesh_path.stem}_inspect")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=required_patches)
        manifest_path = _write_json(target_dir / "mesh_manifest.json", manifest)
        quality_path = _write_json(target_dir / "mesh_quality.json", quality)
        report_path = _write_text(target_dir / "unstructured_mesh_report.md", _inspection_markdown(manifest, quality))
        artifacts = {
            "mesh_manifest": str(manifest_path),
            "mesh_quality": str(quality_path),
            "mesh_report": str(report_path),
        }
        if write_vtu:
            artifacts["mesh_vtu"] = str(write_mesh_vtu(mesh, target_dir / "mesh.vtu"))
        fv_geometry = None
        if quality["status"] == "passed":
            fv_geometry = build_fv_geometry(mesh).to_dict()
            artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry))
        status_path = target_dir / "inspection_status.json"
        artifacts["inspection_status"] = str(status_path)
        status = "success" if quality["status"] == "passed" else "failed"
        result = AgentResult(
            status=status,
            backend="unstructured_fvm",
            operation="inspect_mesh",
            message=(
                "Unstructured mesh inspection passed."
                if status == "success"
                else "Unstructured mesh inspection failed closed before solver execution."
            ),
            outputs={
                "artifacts": artifacts,
                "manifest": manifest,
                "quality": quality,
                "fv_geometry": fv_geometry,
                "solver_execution": "not_attempted",
            },
            errors=quality["blocking_errors"] if status == "failed" else [],
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        _write_json(status_path, result.to_dict())
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="inspect_mesh",
            message="Unstructured mesh import failed before solver execution.",
            errors=[str(exc)],
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        failure_path = target_dir / "inspection_status.json"
        failure.outputs["artifacts"] = {"inspection_status": str(failure_path)}
        _write_json(failure_path, failure.to_dict())
        return failure.to_dict()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _inspection_markdown(manifest: dict[str, Any], quality: dict[str, Any]) -> str:
    lines = [
        "# FastFluent Unstructured Mesh Inspection",
        "",
        f"Status: `{quality['status']}`",
        f"Backend: `{manifest['backend']}`",
        f"Mesh: `{manifest['mesh_name']}`",
        "",
        "## Mesh Summary",
        "",
        f"- Nodes: `{manifest['node_count']}`",
        f"- Cells: `{manifest['cell_count']}`",
        f"- Boundary faces: `{manifest['boundary_face_count']}`",
        f"- Internal faces: `{manifest['internal_face_count']}`",
        f"- Cell types: `{manifest['cell_type_counts']}`",
        "",
        "## Boundary Zones",
        "",
    ]
    for name, count in quality["boundary_zone_counts"].items():
        lines.append(f"- `{name}`: `{count}`")
    lines.extend(["", "## Region Zones", ""])
    for name, count in quality["region_zone_counts"].items():
        lines.append(f"- `{name}`: `{count}`")
    lines.extend(["", "## Blocking Errors", ""])
    if quality["blocking_errors"]:
        lines.extend(f"- {item}" for item in quality["blocking_errors"])
    else:
        lines.append("- None")
    lines.extend(["", "## Scope", "", "This gate inspects mesh topology only. No flow solver is executed."])
    lines.append("")
    return "\n".join(lines)
