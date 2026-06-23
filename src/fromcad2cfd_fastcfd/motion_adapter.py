"""Mesh-aware adapter for safe FastFluent motion contracts."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from .motion import MOTION_CONTRACT_SCHEMA_VERSION, MOTION_EVIDENCE_LEVEL, motion_report_markdown, sample_motion_contract
from .unstructured.gmsh import read_gmsh_v4_ascii
from .unstructured.mesh import MeshElement, UnstructuredMesh
from .unstructured.quality import evaluate_mesh_quality


MOTION_ADAPTER_SCHEMA_VERSION = "fastfluent_motion_mesh_adapter_v1"


def adapt_motion_to_mesh(
    motion_payload: dict[str, Any],
    mesh_file: str | Path,
    output_dir: str | Path,
    *,
    time_step_s: float = 0.1,
    total_time_s: float = 1.0,
    characteristic_length_m: float | None = None,
    cfl_warn: float = 0.5,
    cfl_fail: float = 1.0,
) -> dict[str, Any]:
    """Bind a motion contract to mesh boundary patches and write adapter evidence."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    mesh = read_gmsh_v4_ascii(mesh_file)
    mesh_length = characteristic_length_m or _mesh_characteristic_length(mesh)
    if mesh_length <= 0.0:
        raise ValueError("A positive characteristic length is required for motion CFL checks.")

    sampled = sample_motion_contract(motion_payload, root, time_step_s=time_step_s, total_time_s=total_time_s)
    normalized = sampled.get("validation", {}).get("normalized_motions", [])
    required_patches = tuple(sorted({str(item.get("target_patch_name") or item.get("target_name")) for item in normalized}))
    mesh_quality = evaluate_mesh_quality(mesh, required_patches=required_patches)
    samples = _read_motion_samples(root / "motion_samples.csv") if sampled.get("status") == "success" else []
    sample_metrics = _sample_metrics_by_motion(samples)
    bindings = [_bind_motion(mesh, item, sample_metrics.get(item["id"], {}), time_step_s, mesh_length, cfl_warn, cfl_fail) for item in normalized]

    blocking_errors = list(sampled.get("validation", {}).get("errors", []))
    blocking_errors.extend(mesh_quality.get("blocking_errors", []))
    blocking_errors.extend(error for binding in bindings for error in binding.get("blocking_errors", []))
    warnings = list(mesh_quality.get("warnings", []))
    warnings.extend(warning for binding in bindings for warning in binding.get("warnings", []))

    adapter_status = "failed" if blocking_errors else "warning" if warnings else "passed"
    result = {
        "schema_version": MOTION_ADAPTER_SCHEMA_VERSION,
        "status": adapter_status,
        "evidence_level": MOTION_EVIDENCE_LEVEL,
        "motion_schema_version": MOTION_CONTRACT_SCHEMA_VERSION,
        "mesh_source": str(mesh_file),
        "mesh_name": mesh.source_name(),
        "time_window": {
            "time_step_s": time_step_s,
            "total_time_s": total_time_s,
            "time_count": sampled.get("sampling", {}).get("time_count", 0),
        },
        "mesh_motion_scale": {
            "characteristic_length_m": mesh_length,
            "cfl_warn": cfl_warn,
            "cfl_fail": cfl_fail,
        },
        "motion_summary": sampled,
        "mesh_quality": mesh_quality,
        "bindings": bindings,
        "solver_adapter": _solver_adapter_payload(root, mesh, bindings, sampled),
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "limitations": [
            "This adapter binds kinematic motion data to named mesh boundary patches.",
            "It does not deform the mesh.",
            "It does not solve moving-boundary CFD.",
            "It does not replace Fluent dynamic mesh, immersed boundary, or FSI validation.",
        ],
        "artifacts": {
            "motion_summary": str(root / "motion_summary.json"),
            "motion_samples": str(root / "motion_samples.csv"),
            "motion_report": str(root / "motion_report.md"),
            "motion_mesh_adapter": str(root / "motion_adapter.json"),
            "motion_mesh_adapter_report": str(root / "motion_adapter.md"),
        },
    }
    _write_json(root / "motion_adapter.json", result)
    _write_text(root / "motion_adapter.md", motion_adapter_markdown(result))
    return result


def motion_adapter_markdown(result: dict[str, Any]) -> str:
    """Render a compact mesh-motion adapter report."""

    lines = [
        "# FastFluent Motion Mesh Adapter",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Evidence level: `{result.get('evidence_level')}`",
        f"- Mesh: `{result.get('mesh_name')}`",
        f"- Characteristic length: `{result.get('mesh_motion_scale', {}).get('characteristic_length_m')}` m",
        f"- Time step: `{result.get('time_window', {}).get('time_step_s')}` s",
        "",
        "## Bindings",
        "",
        "| Motion | Patch | Status | Nodes | Elements | Effective speed (m/s) | Motion CFL |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for binding in result.get("bindings", []):
        qoi = binding.get("motion_qoi", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{binding.get('motion_id')}`",
                    f"`{binding.get('patch_name')}`",
                    f"`{binding.get('status')}`",
                    str(binding.get("node_count")),
                    str(binding.get("boundary_element_count")),
                    str(qoi.get("max_effective_speed_m_s")),
                    str(qoi.get("motion_courant")),
                ]
            )
            + " |"
        )
    if result.get("blocking_errors"):
        lines.extend(["", "## Blocking Errors", ""])
        lines.extend(f"- {item}" for item in result["blocking_errors"])
    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in result["warnings"])
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in result.get("limitations", []))
    lines.append("")
    return "\n".join(lines)


def _bind_motion(
    mesh: UnstructuredMesh,
    motion: dict[str, Any],
    sample_metrics: dict[str, float],
    time_step_s: float,
    characteristic_length_m: float,
    cfl_warn: float,
    cfl_fail: float,
) -> dict[str, Any]:
    patch_name = str(motion.get("target_patch_name") or motion.get("target_name"))
    elements = [element for element in mesh.boundary_elements if element.primary_physical_name == patch_name]
    node_tags = sorted({tag for element in elements for tag in element.node_tags})
    blocking_errors: list[str] = []
    warnings: list[str] = []
    if not elements:
        blocking_errors.append(f"Motion {motion['id']} target patch {patch_name!r} was not found in the mesh.")
    max_radius = _max_node_radius(mesh, node_tags, motion.get("reference_point", [0.0, 0.0, 0.0])) if node_tags else 0.0
    max_translation_speed = float(sample_metrics.get("max_translation_speed_m_s", 0.0))
    max_angular_velocity = float(sample_metrics.get("max_abs_angular_velocity_rad_s", 0.0))
    max_rotation_surface_speed = max_angular_velocity * max_radius
    max_effective_speed = max(max_translation_speed, max_rotation_surface_speed)
    motion_courant = max_effective_speed * time_step_s / characteristic_length_m
    if motion_courant > cfl_fail:
        blocking_errors.append(
            f"Motion {motion['id']} motion Courant {motion_courant:.6g} exceeds fail threshold {cfl_fail:.6g}."
        )
    elif motion_courant > cfl_warn:
        warnings.append(f"Motion {motion['id']} motion Courant {motion_courant:.6g} exceeds warning threshold {cfl_warn:.6g}.")
    status = "failed" if blocking_errors else "warning" if warnings else "passed"
    return {
        "motion_id": motion["id"],
        "target_type": motion["target_type"],
        "target_name": motion["target_name"],
        "patch_name": patch_name,
        "motion_kind": motion["motion_kind"],
        "status": status,
        "node_count": len(node_tags),
        "boundary_element_count": len(elements),
        "node_tags_preview": node_tags[:20],
        "boundary_element_tags_preview": [element.tag for element in elements[:20]],
        "motion_qoi": {
            "max_translation_m": sample_metrics.get("max_translation_m", 0.0),
            "max_translation_speed_m_s": max_translation_speed,
            "max_abs_angle_rad": sample_metrics.get("max_abs_angle_rad", 0.0),
            "max_abs_angular_velocity_rad_s": max_angular_velocity,
            "max_patch_radius_m": max_radius,
            "max_rotation_surface_speed_m_s": max_rotation_surface_speed,
            "max_effective_speed_m_s": max_effective_speed,
            "motion_courant": motion_courant,
        },
        "blocking_errors": blocking_errors,
        "warnings": warnings,
    }


def _solver_adapter_payload(root: Path, mesh: UnstructuredMesh, bindings: list[dict[str, Any]], sampled: dict[str, Any]) -> dict[str, Any]:
    return {
        "adapter_version": MOTION_ADAPTER_SCHEMA_VERSION,
        "mesh_source": mesh.source_path,
        "motion_samples_csv": str(root / "motion_samples.csv"),
        "motion_summary_json": str(root / "motion_summary.json"),
        "sample_count": sampled.get("sampling", {}).get("sample_count", 0),
        "bindings": [
            {
                "motion_id": binding["motion_id"],
                "patch_name": binding["patch_name"],
                "motion_kind": binding["motion_kind"],
                "status": binding["status"],
                "node_count": binding["node_count"],
                "boundary_element_count": binding["boundary_element_count"],
                "motion_courant": binding["motion_qoi"]["motion_courant"],
            }
            for binding in bindings
        ],
    }


def _sample_metrics_by_motion(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for row in rows:
        motion_id = row["motion_id"]
        item = metrics.setdefault(
            motion_id,
            {
                "max_translation_m": 0.0,
                "max_translation_speed_m_s": 0.0,
                "max_abs_angle_rad": 0.0,
                "max_abs_angular_velocity_rad_s": 0.0,
            },
        )
        item["max_translation_m"] = max(item["max_translation_m"], _vector_norm(row, "d", "m"))
        item["max_translation_speed_m_s"] = max(item["max_translation_speed_m_s"], _vector_norm(row, "v", "m_s"))
        item["max_abs_angle_rad"] = max(item["max_abs_angle_rad"], abs(float(row["angle_rad"])))
        item["max_abs_angular_velocity_rad_s"] = max(
            item["max_abs_angular_velocity_rad_s"], abs(float(row["angular_velocity_rad_s"]))
        )
    return metrics


def _vector_norm(row: dict[str, str], prefix: str, suffix: str) -> float:
    if prefix == "d":
        values = (float(row["dx_m"]), float(row["dy_m"]), float(row["dz_m"]))
    else:
        values = (float(row["vx_m_s"]), float(row["vy_m_s"]), float(row["vz_m_s"]))
    return math.sqrt(sum(value * value for value in values))


def _max_node_radius(mesh: UnstructuredMesh, node_tags: list[int], reference_point: list[float]) -> float:
    ref = tuple(float(value) for value in reference_point)
    radii = []
    for tag in node_tags:
        node = mesh.nodes[tag]
        radii.append(math.sqrt((node.x - ref[0]) ** 2 + (node.y - ref[1]) ** 2 + (node.z - ref[2]) ** 2))
    return max(radii, default=0.0)


def _mesh_characteristic_length(mesh: UnstructuredMesh) -> float:
    lengths = []
    for cell in mesh.cells:
        lengths.extend(_element_edge_lengths(mesh, cell))
    positive = [value for value in lengths if value > 0.0 and math.isfinite(value)]
    return min(positive) if positive else 0.0


def _element_edge_lengths(mesh: UnstructuredMesh, element: MeshElement) -> list[float]:
    tags = list(element.node_tags)
    pairs: list[tuple[int, int]] = []
    for i, a in enumerate(tags):
        for b in tags[i + 1 :]:
            pairs.append((a, b))
    lengths = []
    for a, b in pairs:
        pa = mesh.nodes[a]
        pb = mesh.nodes[b]
        lengths.append(math.sqrt((pb.x - pa.x) ** 2 + (pb.y - pa.y) ** 2 + (pb.z - pa.z) ** 2))
    return lengths


def _read_motion_samples(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path
