"""Scalar diffusion benchmark for the unstructured FastFluent backend."""

from __future__ import annotations

import csv
import json
from math import sqrt
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .geometry import build_fv_geometry
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .linear import SparseMatrixCSR, solve_linear_system
from .mesh import MeshElement, UnstructuredMesh, triangle_signed_area_xy
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .vtu import write_mesh_vtu, write_scalar_solution_vtu


SCALAR_DIFFUSION_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_scalar_diffusion_v1"
RESIDUAL_HISTORY_SCHEMA_VERSION = "iteration,residual_l2,residual_linf"


def run_scalar_diffusion_case(
    mesh_file: str | Path,
    *,
    output_dir: str | Path | None = None,
    manufactured_solution: str = "linear",
    diffusivity: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Run a small manufactured scalar diffusion benchmark.

    The current implementation supports 2D triangular meshes and exact
    Dirichlet boundary values on all boundary nodes. It exists as a benchmark
    gate for geometry and matrix assembly, not as a production scalar solver.
    """

    mesh_path = Path(mesh_file)
    target_dir = Path(output_dir) if output_dir else unique_path(mesh_path.parent / f"{mesh_path.stem}_diffusion")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        if diffusivity <= 0:
            raise ValueError("Scalar diffusion diffusivity must be positive.")
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=required_patches)
        artifacts: dict[str, str] = {
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
            "mesh_vtu": str(write_mesh_vtu(mesh, target_dir / "mesh.vtu")),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_scalar_diffusion",
                message="Scalar diffusion was blocked by mesh quality gate.",
                errors=quality["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "solver_execution": "blocked_by_mesh_quality",
                }
            )
            artifacts["diffusion_status"] = str(target_dir / "diffusion_status.json")
            _write_json(target_dir / "diffusion_status.json", result.to_dict())
            return result.to_dict()
        _require_supported_cells(mesh)
        fv_geometry = build_fv_geometry(mesh).to_dict()
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry))
        solution = solve_manufactured_diffusion(
            mesh,
            manufactured_solution=manufactured_solution,
            diffusivity=diffusivity,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["linear_system"] = str(_write_json(target_dir / "linear_system.json", solution["linear_system"]))
        artifacts["residual_history"] = str(_write_residual_history(target_dir / "residual_history.csv", solution["residual_history"]))
        artifacts["qoi"] = str(_write_json(target_dir / "qoi.json", solution["qoi"]))
        artifacts["solution_vtu"] = str(
            write_scalar_solution_vtu(
                mesh,
                target_dir / "solution.vtu",
                solution["node_values"],
                exact_values=solution["exact_node_values"],
                error_values=solution["node_error_values"],
            )
        )
        artifacts["diffusion_report"] = str(_write_text(target_dir / "scalar_diffusion_report.md", _diffusion_markdown(solution["qoi"])))
        result = AgentResult.success(
            backend="unstructured_fvm",
            operation="solve_scalar_diffusion",
            message="Scalar diffusion manufactured-solution benchmark completed.",
            outputs={
                "artifacts": artifacts,
                "manifest": manifest,
                "quality": quality,
                "fv_geometry": fv_geometry,
                "linear_system": solution["linear_system"],
                "qoi": solution["qoi"],
                "solver_execution": "scalar_diffusion_linear_system",
            },
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        artifacts["diffusion_status"] = str(target_dir / "diffusion_status.json")
        _write_json(target_dir / "diffusion_status.json", result.to_dict())
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_scalar_diffusion",
            message="Scalar diffusion benchmark failed before solver completion.",
            errors=[str(exc)],
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"diffusion_status": str(target_dir / "diffusion_status.json")}
        _write_json(target_dir / "diffusion_status.json", failure.to_dict())
        return failure.to_dict()


def solve_manufactured_diffusion(
    mesh: UnstructuredMesh,
    *,
    manufactured_solution: str = "linear",
    diffusivity: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
) -> dict[str, Any]:
    exact = _manufactured_solution(mesh, manufactured_solution, diffusivity=diffusivity)
    linear_system = _assemble_scalar_diffusion_linear_system(mesh, exact, diffusivity)
    matrix: SparseMatrixCSR = linear_system["matrix"]
    rhs: list[float] = linear_system["rhs"]
    node_tags: list[int] = linear_system["node_tags"]
    node_index: dict[int, int] = linear_system["node_index"]
    solve_result = solve_linear_system(
        matrix,
        rhs,
        method=linear_solver,
        tolerance=linear_tolerance,
        max_iterations=max_linear_iterations,
    )
    if not solve_result.converged:
        raise ValueError(
            "Scalar diffusion linear solver did not converge: "
            f"method={solve_result.method}, iterations={solve_result.iterations}, "
            f"final_residual_l2={solve_result.final_residual_l2}."
        )
    solution_vector = solve_result.values
    final_residual = {"l2": solve_result.final_residual_l2, "linf": solve_result.final_residual_linf}
    node_values = {tag: solution_vector[node_index[tag]] for tag in node_tags}
    exact_node_values = {tag: exact["value"](*mesh.nodes[tag].to_tuple()) for tag in node_tags}
    node_error_values = {tag: node_values[tag] - exact_node_values[tag] for tag in node_tags}
    matrix_metadata = solve_result.metadata(matrix)
    matrix_metadata.update(
        {
            "assembly": "p1_triangle_scalar_diffusion",
            "boundary_condition": "exact_dirichlet_on_boundary_nodes",
            "constrained_node_count": len(linear_system["constrained_values"]),
            "rhs_l2": sqrt(sum(value * value for value in rhs)),
        }
    )
    qoi = _build_qoi(
        mesh,
        node_values,
        exact,
        node_error_values,
        final_residual,
        manufactured_solution,
        diffusivity,
        matrix_metadata,
    )
    residual_history = solve_result.residual_history
    qoi["residual_history_rows"] = len(residual_history)
    qoi["residual_reduction_ratio"] = (
        final_residual["l2"] / solve_result.initial_residual_l2 if solve_result.initial_residual_l2 > 0 else 0.0
    )
    return {
        "node_values": node_values,
        "exact_node_values": exact_node_values,
        "node_error_values": node_error_values,
        "residual_history": residual_history,
        "linear_system": matrix_metadata,
        "qoi": qoi,
    }


def _assemble_scalar_diffusion_linear_system(
    mesh: UnstructuredMesh,
    exact,
    diffusivity: float,
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    size = len(node_tags)
    rows: list[dict[int, float]] = [dict() for _ in range(size)]
    rhs = [0.0 for _ in range(size)]
    for cell in mesh.cells:
        _assemble_triangle(rows, rhs, mesh, cell, node_index, exact["source"], diffusivity)
    boundary_nodes = _boundary_nodes(mesh)
    if not boundary_nodes:
        raise ValueError("Scalar diffusion requires Dirichlet boundary nodes from boundary elements.")
    constrained = {tag: exact["value"](*mesh.nodes[tag].to_tuple()) for tag in boundary_nodes}
    _apply_dirichlet_sparse_rows(rows, rhs, node_index, constrained)
    matrix = SparseMatrixCSR.from_rows(rows, n_cols=size, drop_tolerance=1.0e-15)
    return {
        "matrix": matrix,
        "rhs": rhs,
        "node_tags": node_tags,
        "node_index": node_index,
        "constrained_values": constrained,
    }


def _assemble_triangle(
    rows: list[dict[int, float]],
    rhs: list[float],
    mesh: UnstructuredMesh,
    cell: MeshElement,
    node_index: dict[int, int],
    source_fn,
    diffusivity: float,
) -> None:
    if cell.kind != "triangle":
        raise ValueError(f"Scalar diffusion U4 currently supports triangle cells only, got {cell.kind}.")
    points = [mesh.nodes[tag].to_tuple() for tag in cell.node_tags]
    area = abs(triangle_signed_area_xy(points[0], points[1], points[2]))
    if area <= 0:
        raise ValueError(f"Cannot assemble diffusion for non-positive triangle area in element {cell.tag}.")
    gradients = _triangle_basis_gradients(points, area)
    local_source = source_fn(*mesh.cell_center(cell))
    for local_i, tag_i in enumerate(cell.node_tags):
        global_i = node_index[tag_i]
        rhs[global_i] += local_source * area / 3.0
        for local_j, tag_j in enumerate(cell.node_tags):
            global_j = node_index[tag_j]
            rows[global_i][global_j] = rows[global_i].get(global_j, 0.0) + diffusivity * area * (
                gradients[local_i][0] * gradients[local_j][0] + gradients[local_i][1] * gradients[local_j][1]
            )


def _triangle_basis_gradients(points: list[tuple[float, float, float]], area: float) -> list[tuple[float, float]]:
    gradients = []
    for i in range(3):
        j = (i + 1) % 3
        k = (i + 2) % 3
        b = points[j][1] - points[k][1]
        c = points[k][0] - points[j][0]
        gradients.append((b / (2.0 * area), c / (2.0 * area)))
    return gradients


def _manufactured_solution(mesh: UnstructuredMesh, name: str, *, diffusivity: float):
    bounds = _mesh_bounds(mesh)
    lx = bounds["xmax"] - bounds["xmin"]
    ly = bounds["ymax"] - bounds["ymin"]
    if lx <= 0 or ly <= 0:
        raise ValueError("Manufactured scalar diffusion requires non-zero x and y mesh extents.")
    if name == "linear":
        return {
            "name": name,
            "value": lambda x, y, z: 2.0 * x - 3.0 * y + 5.0,
            "source": lambda x, y, z: 0.0,
        }
    if name == "quadratic_bubble":
        xmin = bounds["xmin"]
        ymin = bounds["ymin"]

        def value(x, y, z):
            xi = (x - xmin) / lx
            eta = (y - ymin) / ly
            return xi * (1.0 - xi) * eta * (1.0 - eta)

        def source(x, y, z):
            xi = (x - xmin) / lx
            eta = (y - ymin) / ly
            return 2.0 * diffusivity * (eta * (1.0 - eta) / (lx * lx) + xi * (1.0 - xi) / (ly * ly))

        return {"name": name, "value": value, "source": source}
    raise ValueError(f"Unsupported manufactured scalar diffusion solution: {name}")


def _mesh_bounds(mesh: UnstructuredMesh) -> dict[str, float]:
    xs = [node.x for node in mesh.nodes.values()]
    ys = [node.y for node in mesh.nodes.values()]
    zs = [node.z for node in mesh.nodes.values()]
    return {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys), "zmin": min(zs), "zmax": max(zs)}


def _boundary_nodes(mesh: UnstructuredMesh) -> set[int]:
    nodes: set[int] = set()
    for element in mesh.boundary_elements:
        nodes.update(element.node_tags)
    return nodes


def _apply_dirichlet_sparse_rows(
    rows: list[dict[int, float]],
    rhs: list[float],
    node_index: dict[int, int],
    constrained_values: dict[int, float],
) -> None:
    for tag, value in constrained_values.items():
        index = node_index[tag]
        for row, coefficients in enumerate(rows):
            if row == index:
                continue
            column_value = coefficients.pop(index, 0.0)
            rhs[row] -= column_value * value
        rows[index].clear()
        rows[index][index] = 1.0
        rhs[index] = value


def _build_qoi(
    mesh: UnstructuredMesh,
    node_values: dict[int, float],
    exact,
    node_error_values: dict[int, float],
    final_residual: dict[str, float],
    manufactured_solution: str,
    diffusivity: float,
    linear_system: dict[str, Any],
) -> dict[str, Any]:
    node_error_l2 = sqrt(sum(value * value for value in node_error_values.values()) / max(1, len(node_error_values)))
    node_error_linf = max((abs(value) for value in node_error_values.values()), default=0.0)
    weighted_error = 0.0
    total_measure = 0.0
    for cell in mesh.cells:
        measure = abs(mesh.cell_signed_measure(cell))
        numerical = sum(node_values[tag] for tag in cell.node_tags) / len(cell.node_tags)
        exact_center = exact["value"](*mesh.cell_center(cell))
        weighted_error += (numerical - exact_center) ** 2 * measure
        total_measure += measure
    cell_center_l2 = sqrt(weighted_error / total_measure) if total_measure > 0 else None
    return {
        "schema_version": SCALAR_DIFFUSION_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "finite_volume_benchmark",
        "status": "passed",
        "manufactured_solution": manufactured_solution,
        "diffusivity": diffusivity,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "boundary_node_count": len(_boundary_nodes(mesh)),
        "linear_system": {
            "schema_version": linear_system["schema_version"],
            "storage": linear_system["storage"],
            "method": linear_system["method"],
            "n_rows": linear_system["n_rows"],
            "n_cols": linear_system["n_cols"],
            "nnz": linear_system["nnz"],
            "density": linear_system["density"],
            "converged": linear_system["converged"],
            "iterations": linear_system["iterations"],
            "tolerance": linear_system["tolerance"],
            "constrained_node_count": linear_system["constrained_node_count"],
        },
        "metrics": {
            "node_l2_error": node_error_l2,
            "node_linf_error": node_error_linf,
            "cell_center_l2_error": cell_center_l2,
            "final_residual_l2": final_residual["l2"],
            "final_residual_linf": final_residual["linf"],
        },
        "limitations": [
            "U5 solves a scalar manufactured diffusion benchmark with an explicit linear-system layer only.",
            "The current implementation supports 2D triangular meshes with Dirichlet values on all boundary nodes.",
            "This is not a momentum, pressure, VOF, rheology, turbulence, or Fluent solver.",
        ],
    }


def _write_residual_history(path: Path, rows: list[dict[str, float]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["iteration", "residual_l2", "residual_linf"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _diffusion_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    linear_system = qoi["linear_system"]
    return "\n".join(
        [
            "# FastFluent Unstructured Scalar Diffusion Benchmark",
            "",
            f"Status: `{qoi['status']}`",
            f"Manufactured solution: `{qoi['manufactured_solution']}`",
            f"Cells: `{qoi['cell_count']}`",
            f"Linear solver: `{linear_system['method']}`",
            f"Matrix: `{linear_system['storage']}`, nnz `{linear_system['nnz']}`",
            "",
            "## Metrics",
            "",
            f"- Node L2 error: `{metrics['node_l2_error']}`",
            f"- Cell-center L2 error: `{metrics['cell_center_l2_error']}`",
            f"- Final residual L2: `{metrics['final_residual_l2']}`",
            "",
            "## Scope",
            "",
            "This gate runs a scalar diffusion benchmark only. It does not run a flow solver.",
            "",
        ]
    )


def _require_supported_cells(mesh: UnstructuredMesh) -> None:
    unsupported = sorted({cell.kind for cell in mesh.cells if cell.kind != "triangle"})
    if unsupported:
        raise ValueError(f"Scalar diffusion U4 currently supports triangle cells only; unsupported cells: {unsupported}.")
