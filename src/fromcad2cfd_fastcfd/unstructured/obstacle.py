"""Public body-fitted obstacle-channel evidence for unstructured FastFluent."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .boundary import BoundaryCondition, validate_boundary_contract
from .geometry import build_fv_geometry
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .vtu import write_mesh_vtu


OBSTACLE_CHANNEL_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_obstacle_channel_evidence_v1"


@dataclass(frozen=True)
class BoundarySegment:
    entity_tag: int
    physical_tag: int
    node_a: int
    node_b: int


def write_rectangular_obstacle_channel_mesh(
    path: str | Path,
    *,
    nx: int = 16,
    ny: int = 8,
    obstacle_i_min: int | None = None,
    obstacle_i_max: int | None = None,
    obstacle_j_min: int | None = None,
    obstacle_j_max: int | None = None,
) -> Path:
    """Write a public-safe body-fitted rectangular-obstacle channel mesh."""

    if nx < 6 or ny < 4:
        raise ValueError("Obstacle-channel mesh requires nx >= 6 and ny >= 4.")
    obstacle_i_min = obstacle_i_min if obstacle_i_min is not None else max(2, nx // 2 - 1)
    obstacle_i_max = obstacle_i_max if obstacle_i_max is not None else min(nx - 2, nx // 2 + 1)
    obstacle_j_min = obstacle_j_min if obstacle_j_min is not None else max(1, ny // 2 - 1)
    obstacle_j_max = obstacle_j_max if obstacle_j_max is not None else min(ny - 1, ny // 2 + 1)
    if not (0 < obstacle_i_min < obstacle_i_max < nx):
        raise ValueError("Obstacle i-index range must be inside the channel.")
    if not (0 < obstacle_j_min < obstacle_j_max < ny):
        raise ValueError("Obstacle j-index range must be inside the channel.")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    def node_tag(i: int, j: int) -> int:
        return j * (nx + 1) + i + 1

    def is_blocked(i: int, j: int) -> bool:
        return obstacle_i_min <= i < obstacle_i_max and obstacle_j_min <= j < obstacle_j_max

    node_count = (nx + 1) * (ny + 1)
    triangles: list[tuple[int, int, int]] = []
    for j in range(ny):
        for i in range(nx):
            if is_blocked(i, j):
                continue
            n00 = node_tag(i, j)
            n10 = node_tag(i + 1, j)
            n11 = node_tag(i + 1, j + 1)
            n01 = node_tag(i, j + 1)
            triangles.append((n00, n10, n11))
            triangles.append((n00, n11, n01))
    boundaries: list[BoundarySegment] = []

    def add_boundary(physical_tag: int, a: int, b: int) -> None:
        boundaries.append(BoundarySegment(entity_tag=len(boundaries) + 1, physical_tag=physical_tag, node_a=a, node_b=b))

    for j in range(ny):
        add_boundary(1, node_tag(0, j), node_tag(0, j + 1))
        add_boundary(2, node_tag(nx, j), node_tag(nx, j + 1))
    for i in range(nx):
        add_boundary(3, node_tag(i, 0), node_tag(i + 1, 0))
        add_boundary(3, node_tag(i, ny), node_tag(i + 1, ny))
    for i in range(obstacle_i_min, obstacle_i_max):
        add_boundary(4, node_tag(i, obstacle_j_min), node_tag(i + 1, obstacle_j_min))
        add_boundary(4, node_tag(i, obstacle_j_max), node_tag(i + 1, obstacle_j_max))
    for j in range(obstacle_j_min, obstacle_j_max):
        add_boundary(4, node_tag(obstacle_i_min, j), node_tag(obstacle_i_min, j + 1))
        add_boundary(4, node_tag(obstacle_i_max, j), node_tag(obstacle_i_max, j + 1))

    element_count = len(boundaries) + len(triangles)
    lines = [
        "$MeshFormat",
        "4.1 0 8",
        "$EndMeshFormat",
        "$PhysicalNames",
        "5",
        '1 1 "inlet"',
        '1 2 "outlet"',
        '1 3 "wall"',
        '1 4 "obstacle_wall"',
        '2 10 "fluid"',
        "$EndPhysicalNames",
        "$Entities",
        f"0 {len(boundaries)} 1 0",
    ]
    for segment in boundaries:
        a = _node_coordinates(segment.node_a, nx=nx, ny=ny)
        b = _node_coordinates(segment.node_b, nx=nx, ny=ny)
        xmin = min(a[0], b[0])
        ymin = min(a[1], b[1])
        xmax = max(a[0], b[0])
        ymax = max(a[1], b[1])
        lines.append(f"{segment.entity_tag} {xmin:.17g} {ymin:.17g} 0 {xmax:.17g} {ymax:.17g} 0 1 {segment.physical_tag}")
    lines.append("1 0 0 0 1 1 0 1 10")
    lines.extend(["$EndEntities", "$Nodes", f"1 {node_count} 1 {node_count}", f"2 1 0 {node_count}"])
    lines.extend(str(tag) for tag in range(1, node_count + 1))
    for j in range(ny + 1):
        for i in range(nx + 1):
            lines.append(f"{i / nx:.17g} {j / ny:.17g} 0")
    lines.extend(["$EndNodes", "$Elements", f"{len(boundaries) + 1} {element_count} 1 {element_count}"])
    element_tag = 1
    for segment in boundaries:
        lines.append(f"1 {segment.entity_tag} 1 1")
        lines.append(f"{element_tag} {segment.node_a} {segment.node_b}")
        element_tag += 1
    lines.append(f"2 1 2 {len(triangles)}")
    for triangle in triangles:
        lines.append(f"{element_tag} {triangle[0]} {triangle[1]} {triangle[2]}")
        element_tag += 1
    lines.append("$EndElements")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def run_obstacle_channel_evidence(
    mesh_file: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    nx: int = 16,
    ny: int = 8,
) -> dict[str, Any]:
    """Generate or inspect a public body-fitted obstacle channel evidence case."""

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "unstructured_obstacle_channel" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        mesh_path = Path(mesh_file) if mesh_file else write_rectangular_obstacle_channel_mesh(target_dir / "public_obstacle_channel.msh", nx=nx, ny=ny)
        mesh = read_gmsh_v4_ascii(mesh_path)
        required_patches = ("inlet", "outlet", "wall", "obstacle_wall")
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=required_patches)
        boundary_contract = validate_boundary_contract(
            mesh,
            required_patches=required_patches,
            boundary_conditions=_obstacle_boundary_conditions(),
        )
        fv_geometry = build_fv_geometry(mesh) if quality["status"] == "passed" else None
        qoi = _build_obstacle_qoi(mesh, quality=quality, boundary_contract=boundary_contract)
        artifacts: dict[str, str] = {
            "obstacle_mesh": str(mesh_path),
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
            "obstacle_boundary_contract": str(_write_json(target_dir / "obstacle_boundary_contract.json", boundary_contract)),
            "mesh_vtu": str(write_mesh_vtu(mesh, target_dir / "mesh.vtu")),
            "obstacle_qoi": str(_write_json(target_dir / "obstacle_qoi.json", qoi)),
            "obstacle_report": str(_write_text(target_dir / "obstacle_report.md", _obstacle_markdown(qoi))),
        }
        if fv_geometry is not None:
            artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry.to_dict()))
        if qoi["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="build_obstacle_channel_evidence",
                message="Obstacle-channel evidence did not pass acceptance checks.",
                errors=qoi["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="build_obstacle_channel_evidence",
                message="Public body-fitted obstacle-channel evidence completed.",
                outputs={
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "qoi": qoi,
                    "solver_execution": "not_attempted_body_fitted_obstacle_evidence_only",
                },
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
        if result.status != "success":
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "qoi": qoi,
                    "solver_execution": "blocked_by_obstacle_channel_evidence",
                }
            )
        artifacts["obstacle_status"] = str(_write_json(target_dir / "obstacle_status.json", result.to_dict()))
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="build_obstacle_channel_evidence",
            message="Obstacle-channel evidence failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"obstacle_status": str(target_dir / "obstacle_status.json")}
        _write_json(target_dir / "obstacle_status.json", failure.to_dict())
        return failure.to_dict()


def _node_coordinates(tag: int, *, nx: int, ny: int) -> tuple[float, float]:
    zero = tag - 1
    i = zero % (nx + 1)
    j = zero // (nx + 1)
    return (float(i) / float(nx), float(j) / float(ny))


def _obstacle_boundary_conditions() -> dict[str, BoundaryCondition]:
    return {
        "inlet": BoundaryCondition(patch="inlet", kind="velocity_dirichlet", role="public obstacle-channel inlet"),
        "outlet": BoundaryCondition(patch="outlet", kind="pressure_reference", role="public obstacle-channel outlet"),
        "wall": BoundaryCondition(patch="wall", kind="no_slip_wall", role="outer channel walls"),
        "obstacle_wall": BoundaryCondition(patch="obstacle_wall", kind="no_slip_wall", role="body-fitted obstacle wall"),
    }


def _build_obstacle_qoi(mesh, *, quality: dict[str, Any], boundary_contract: dict[str, Any]) -> dict[str, Any]:
    xs = [node.x for node in mesh.nodes.values()]
    ys = [node.y for node in mesh.nodes.values()]
    bounds = {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys)}
    obstacle_nodes = sorted(
        {
            tag
            for element in mesh.boundary_elements
            if element.primary_physical_name == "obstacle_wall"
            for tag in element.node_tags
        }
    )
    obstacle_xs = [mesh.nodes[tag].x for tag in obstacle_nodes]
    obstacle_ys = [mesh.nodes[tag].y for tag in obstacle_nodes]
    obstacle_bounds = {
        "xmin": min(obstacle_xs) if obstacle_xs else None,
        "xmax": max(obstacle_xs) if obstacle_xs else None,
        "ymin": min(obstacle_ys) if obstacle_ys else None,
        "ymax": max(obstacle_ys) if obstacle_ys else None,
    }
    channel_height = bounds["ymax"] - bounds["ymin"]
    obstacle_height = (obstacle_bounds["ymax"] - obstacle_bounds["ymin"]) if obstacle_ys else 0.0
    top_clearance = bounds["ymax"] - obstacle_bounds["ymax"] if obstacle_ys else None
    bottom_clearance = obstacle_bounds["ymin"] - bounds["ymin"] if obstacle_ys else None
    hints = [
        {
            "category": "mesh_zones",
            "recommendation": "Preserve inlet, outlet, wall, obstacle_wall, and fluid zones when exporting to Fluent.",
            "evidence": [f"boundary_zone_counts={quality.get('boundary_zone_counts')}", f"region_zone_counts={quality.get('region_zone_counts')}"],
        },
        {
            "category": "boundary_conditions",
            "recommendation": "Apply no-slip to both outer wall and obstacle_wall patches in the first Fluent setup.",
            "evidence": [f"boundary_contract_status={boundary_contract.get('status')}", "obstacle_wall condition is no_slip_wall"],
        },
        {
            "category": "mesh_refinement",
            "recommendation": "Refine around the obstacle leading/trailing edges and near-wall wake region.",
            "evidence": [f"blockage_ratio={obstacle_height / channel_height if channel_height > 0 else None}", f"obstacle_bounds={obstacle_bounds}"],
        },
    ]
    blocking_errors = []
    if quality["status"] != "passed":
        blocking_errors.extend(quality["blocking_errors"])
    if boundary_contract["status"] != "passed":
        blocking_errors.extend(boundary_contract["blocking_errors"])
    if not obstacle_nodes:
        blocking_errors.append("No obstacle_wall patch was detected.")
    return {
        "schema_version": OBSTACLE_CHANNEL_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "status": "passed" if not blocking_errors else "failed",
        "mesh_name": mesh.source_name(),
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "domain_bounds": bounds,
        "obstacle_bounds": obstacle_bounds,
        "obstacle_wall_node_count": len(obstacle_nodes),
        "blockage_ratio": obstacle_height / channel_height if channel_height > 0 else None,
        "top_clearance": top_clearance,
        "bottom_clearance": bottom_clearance,
        "boundary_zone_counts": quality.get("boundary_zone_counts", {}),
        "region_zone_counts": quality.get("region_zone_counts", {}),
        "acceptance": {
            "quality_gate_passed": quality["status"] == "passed",
            "boundary_contract_passed": boundary_contract["status"] == "passed",
            "obstacle_wall_present": bool(obstacle_nodes),
            "public_synthetic_case": True,
        },
        "fluent_setup_hints": hints,
        "blocking_errors": blocking_errors,
        "limitations": [
            "This is a public synthetic body-fitted obstacle-channel mesh evidence case.",
            "No private device geometry is included.",
            "No production obstacle-flow CFD result is claimed by this evidence gate.",
        ],
    }


def _obstacle_markdown(qoi: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# FastFluent Public Obstacle-Channel Evidence",
            "",
            f"Status: `{qoi['status']}`",
            f"Cells: `{qoi['cell_count']}`",
            f"Blockage ratio: `{qoi['blockage_ratio']}`",
            "",
            "## Boundary Zones",
            "",
            f"`{qoi['boundary_zone_counts']}`",
            "",
            "## Scope",
            "",
            "This is a public synthetic body-fitted mesh evidence case, not a private geometry artifact.",
            "",
        ]
    )


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
