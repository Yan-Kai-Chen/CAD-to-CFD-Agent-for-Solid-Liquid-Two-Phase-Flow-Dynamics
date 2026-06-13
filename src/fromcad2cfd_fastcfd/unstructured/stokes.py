"""Manufactured Stokes benchmark for the unstructured FastFluent backend."""

from __future__ import annotations

import csv
import json
from math import sqrt
from pathlib import Path
from typing import Any, Callable

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .geometry import build_fv_geometry, node_scalar_cell_gradients
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .linear import SparseMatrixCSR, solve_linear_system
from .mesh import MeshElement, UnstructuredMesh, triangle_signed_area_xy
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .vtu import write_mesh_vtu, write_vector_solution_vtu


STOKES_BENCHMARK_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_stokes_benchmark_v1"


def run_stokes_benchmark_case(
    mesh_file: str | Path,
    *,
    output_dir: str | Path | None = None,
    manufactured_solution: str = "pressure_driven_shear",
    viscosity: float = 1.0,
    pressure_gradient: tuple[float, float] = (1.0, 0.0),
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Run the U6 manufactured Stokes momentum benchmark.

    U6 solves two velocity-component diffusion systems with a manufactured
    pressure gradient and exact Dirichlet velocity values. It validates the
    momentum-equation linear-system route before pressure-velocity coupling is
    attempted. It is not a production incompressible-flow solver.
    """

    mesh_path = Path(mesh_file)
    target_dir = Path(output_dir) if output_dir else unique_path(mesh_path.parent / f"{mesh_path.stem}_stokes")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        if viscosity <= 0:
            raise ValueError("Stokes benchmark viscosity must be positive.")
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
                operation="solve_stokes_benchmark",
                message="Stokes benchmark was blocked by mesh quality gate.",
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
            artifacts["stokes_status"] = str(target_dir / "stokes_status.json")
            _write_json(target_dir / "stokes_status.json", result.to_dict())
            return result.to_dict()
        _require_supported_cells(mesh)
        fv_geometry = build_fv_geometry(mesh).to_dict()
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry))
        solution = solve_manufactured_stokes(
            mesh,
            manufactured_solution=manufactured_solution,
            viscosity=viscosity,
            pressure_gradient=pressure_gradient,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["stokes_linear_systems"] = str(_write_json(target_dir / "stokes_linear_systems.json", solution["linear_systems"]))
        artifacts["stokes_residual_history"] = str(
            _write_stokes_residual_history(target_dir / "stokes_residual_history.csv", solution["residual_history"])
        )
        artifacts["stokes_qoi"] = str(_write_json(target_dir / "stokes_qoi.json", solution["qoi"]))
        artifacts["stokes_solution_vtu"] = str(
            write_vector_solution_vtu(
                mesh,
                target_dir / "stokes_solution.vtu",
                solution["velocity"],
                exact_vectors=solution["exact_velocity"],
                error_vectors=solution["velocity_error"],
                scalar_fields={"pressure_exact": solution["pressure"]},
            )
        )
        artifacts["stokes_report"] = str(_write_text(target_dir / "stokes_report.md", _stokes_markdown(solution["qoi"])))
        result = AgentResult.success(
            backend="unstructured_fvm",
            operation="solve_stokes_benchmark",
            message="Manufactured Stokes momentum benchmark completed.",
            outputs={
                "artifacts": artifacts,
                "manifest": manifest,
                "quality": quality,
                "fv_geometry": fv_geometry,
                "linear_systems": solution["linear_systems"],
                "qoi": solution["qoi"],
                "solver_execution": "stokes_momentum_linear_system",
            },
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        artifacts["stokes_status"] = str(target_dir / "stokes_status.json")
        _write_json(target_dir / "stokes_status.json", result.to_dict())
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_stokes_benchmark",
            message="Stokes benchmark failed before solver completion.",
            errors=[str(exc)],
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"stokes_status": str(target_dir / "stokes_status.json")}
        _write_json(target_dir / "stokes_status.json", failure.to_dict())
        return failure.to_dict()


def solve_manufactured_stokes(
    mesh: UnstructuredMesh,
    *,
    manufactured_solution: str = "pressure_driven_shear",
    viscosity: float = 1.0,
    pressure_gradient: tuple[float, float] = (1.0, 0.0),
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
) -> dict[str, Any]:
    exact = _manufactured_solution(mesh, manufactured_solution, viscosity=viscosity, pressure_gradient=pressure_gradient)
    u_solution = _solve_velocity_component(
        mesh,
        component="u",
        value_fn=exact["u"],
        effective_source_fn=exact["effective_source_u"],
        viscosity=viscosity,
        linear_solver=linear_solver,
        linear_tolerance=linear_tolerance,
        max_linear_iterations=max_linear_iterations,
    )
    v_solution = _solve_velocity_component(
        mesh,
        component="v",
        value_fn=exact["v"],
        effective_source_fn=exact["effective_source_v"],
        viscosity=viscosity,
        linear_solver=linear_solver,
        linear_tolerance=linear_tolerance,
        max_linear_iterations=max_linear_iterations,
    )
    node_tags = sorted(mesh.nodes)
    velocity = {tag: (u_solution["values"][tag], v_solution["values"][tag], 0.0) for tag in node_tags}
    exact_velocity = {tag: (exact["u"](*mesh.nodes[tag].to_tuple()), exact["v"](*mesh.nodes[tag].to_tuple()), 0.0) for tag in node_tags}
    velocity_error = {
        tag: (
            velocity[tag][0] - exact_velocity[tag][0],
            velocity[tag][1] - exact_velocity[tag][1],
            0.0,
        )
        for tag in node_tags
    }
    pressure = {tag: exact["pressure"](*mesh.nodes[tag].to_tuple()) for tag in node_tags}
    divergence = _cell_divergence(mesh, {tag: velocity[tag][0] for tag in node_tags}, {tag: velocity[tag][1] for tag in node_tags})
    qoi = _build_qoi(
        mesh,
        velocity,
        exact_velocity,
        velocity_error,
        divergence,
        exact,
        manufactured_solution,
        viscosity,
        pressure_gradient,
        u_solution["linear_system"],
        v_solution["linear_system"],
    )
    residual_history = []
    residual_history.extend(u_solution["residual_history"])
    residual_history.extend(v_solution["residual_history"])
    return {
        "velocity": velocity,
        "exact_velocity": exact_velocity,
        "velocity_error": velocity_error,
        "pressure": pressure,
        "divergence": divergence,
        "linear_systems": {"u": u_solution["linear_system"], "v": v_solution["linear_system"]},
        "residual_history": residual_history,
        "qoi": qoi,
    }


def _solve_velocity_component(
    mesh: UnstructuredMesh,
    *,
    component: str,
    value_fn: Callable[[float, float, float], float],
    effective_source_fn: Callable[[float, float, float], float],
    viscosity: float,
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
) -> dict[str, Any]:
    linear_system = _assemble_component_linear_system(mesh, value_fn, effective_source_fn, viscosity)
    matrix: SparseMatrixCSR = linear_system["matrix"]
    rhs: list[float] = linear_system["rhs"]
    solve_result = solve_linear_system(
        matrix,
        rhs,
        method=linear_solver,
        tolerance=linear_tolerance,
        max_iterations=max_linear_iterations,
    )
    if not solve_result.converged:
        raise ValueError(
            "Stokes component linear solver did not converge: "
            f"component={component}, method={solve_result.method}, iterations={solve_result.iterations}, "
            f"final_residual_l2={solve_result.final_residual_l2}."
        )
    node_tags: list[int] = linear_system["node_tags"]
    node_index: dict[int, int] = linear_system["node_index"]
    values = {tag: solve_result.values[node_index[tag]] for tag in node_tags}
    metadata = solve_result.metadata(matrix)
    metadata.update(
        {
            "component": component,
            "assembly": "p1_triangle_stokes_momentum_component",
            "boundary_condition": "exact_dirichlet_velocity_on_boundary_nodes",
            "constrained_node_count": len(linear_system["constrained_values"]),
            "rhs_l2": sqrt(sum(value * value for value in rhs)),
        }
    )
    residual_history = [dict(row, component=component) for row in solve_result.residual_history]
    return {"values": values, "linear_system": metadata, "residual_history": residual_history}


def _assemble_component_linear_system(
    mesh: UnstructuredMesh,
    value_fn: Callable[[float, float, float], float],
    effective_source_fn: Callable[[float, float, float], float],
    viscosity: float,
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    size = len(node_tags)
    rows: list[dict[int, float]] = [dict() for _ in range(size)]
    rhs = [0.0 for _ in range(size)]
    for cell in mesh.cells:
        _assemble_triangle(rows, rhs, mesh, cell, node_index, effective_source_fn, viscosity)
    boundary_nodes = _boundary_nodes(mesh)
    if not boundary_nodes:
        raise ValueError("Stokes benchmark requires Dirichlet boundary nodes from boundary elements.")
    constrained = {tag: value_fn(*mesh.nodes[tag].to_tuple()) for tag in boundary_nodes}
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
    source_fn: Callable[[float, float, float], float],
    viscosity: float,
) -> None:
    if cell.kind != "triangle":
        raise ValueError(f"Stokes U6 currently supports triangle cells only, got {cell.kind}.")
    points = [mesh.nodes[tag].to_tuple() for tag in cell.node_tags]
    area = abs(triangle_signed_area_xy(points[0], points[1], points[2]))
    if area <= 0:
        raise ValueError(f"Cannot assemble Stokes benchmark for non-positive triangle area in element {cell.tag}.")
    gradients = _triangle_basis_gradients(points, area)
    local_source = source_fn(*mesh.cell_center(cell))
    for local_i, tag_i in enumerate(cell.node_tags):
        global_i = node_index[tag_i]
        rhs[global_i] += local_source * area / 3.0
        for local_j, tag_j in enumerate(cell.node_tags):
            global_j = node_index[tag_j]
            rows[global_i][global_j] = rows[global_i].get(global_j, 0.0) + viscosity * area * (
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


def _manufactured_solution(
    mesh: UnstructuredMesh,
    name: str,
    *,
    viscosity: float,
    pressure_gradient: tuple[float, float],
) -> dict[str, Any]:
    bounds = _mesh_bounds(mesh)
    xmin = bounds["xmin"]
    xmax = bounds["xmax"]
    ymin = bounds["ymin"]
    ymax = bounds["ymax"]
    dpdx, dpdy = pressure_gradient
    if name == "pressure_driven_shear":
        return {
            "name": name,
            "u": lambda x, y, z: (y - ymin) ** 2,
            "v": lambda x, y, z: 0.0,
            "pressure": lambda x, y, z: dpdx * x + dpdy * y,
            "body_force_u": lambda x, y, z: dpdx - 2.0 * viscosity,
            "body_force_v": lambda x, y, z: dpdy,
            "effective_source_u": lambda x, y, z: -2.0 * viscosity,
            "effective_source_v": lambda x, y, z: 0.0,
        }
    if name == "linear_divergence_free":
        xc = 0.5 * (xmin + xmax)
        yc = 0.5 * (ymin + ymax)
        return {
            "name": name,
            "u": lambda x, y, z: x - xc,
            "v": lambda x, y, z: -(y - yc),
            "pressure": lambda x, y, z: dpdx * x + dpdy * y,
            "body_force_u": lambda x, y, z: dpdx,
            "body_force_v": lambda x, y, z: dpdy,
            "effective_source_u": lambda x, y, z: 0.0,
            "effective_source_v": lambda x, y, z: 0.0,
        }
    if name == "poiseuille_channel":
        height = ymax - ymin
        length = xmax - xmin
        if height <= 0 or length <= 0:
            raise ValueError("Poiseuille channel benchmark requires positive mesh length and height.")
        driving_source = -dpdx
        if driving_source <= 0:
            raise ValueError("Poiseuille channel benchmark requires a negative dpdx pressure gradient.")

        def u_profile(x, y, z):
            return driving_source * (y - ymin) * (ymax - y) / (2.0 * viscosity)

        return {
            "name": name,
            "u": u_profile,
            "v": lambda x, y, z: 0.0,
            "pressure": lambda x, y, z: dpdx * (x - xmax) + dpdy * y,
            "body_force_u": lambda x, y, z: dpdx + driving_source,
            "body_force_v": lambda x, y, z: dpdy,
            "effective_source_u": lambda x, y, z: driving_source,
            "effective_source_v": lambda x, y, z: 0.0,
        }
    raise ValueError(f"Unsupported manufactured Stokes solution: {name}")


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


def _cell_divergence(mesh: UnstructuredMesh, u_values: dict[int, float], v_values: dict[int, float]) -> dict[int, float]:
    u_gradients = node_scalar_cell_gradients(mesh, u_values)
    v_gradients = node_scalar_cell_gradients(mesh, v_values)
    return {cell_index: u_gradients[cell_index][0] + v_gradients[cell_index][1] for cell_index in u_gradients}


def _build_qoi(
    mesh: UnstructuredMesh,
    velocity: dict[int, tuple[float, float, float]],
    exact_velocity: dict[int, tuple[float, float, float]],
    velocity_error: dict[int, tuple[float, float, float]],
    divergence: dict[int, float],
    exact,
    manufactured_solution: str,
    viscosity: float,
    pressure_gradient: tuple[float, float],
    u_linear_system: dict[str, Any],
    v_linear_system: dict[str, Any],
) -> dict[str, Any]:
    node_velocity_l2 = sqrt(
        sum(error[0] * error[0] + error[1] * error[1] for error in velocity_error.values()) / max(1, len(velocity_error))
    )
    node_velocity_linf = max((sqrt(error[0] * error[0] + error[1] * error[1]) for error in velocity_error.values()), default=0.0)
    weighted_error = 0.0
    weighted_divergence = 0.0
    total_measure = 0.0
    for cell_index, cell in enumerate(mesh.cells):
        measure = abs(mesh.cell_signed_measure(cell))
        numerical_u = sum(velocity[tag][0] for tag in cell.node_tags) / len(cell.node_tags)
        numerical_v = sum(velocity[tag][1] for tag in cell.node_tags) / len(cell.node_tags)
        exact_u = exact["u"](*mesh.cell_center(cell))
        exact_v = exact["v"](*mesh.cell_center(cell))
        weighted_error += ((numerical_u - exact_u) ** 2 + (numerical_v - exact_v) ** 2) * measure
        weighted_divergence += divergence[cell_index] * divergence[cell_index] * measure
        total_measure += measure
    return {
        "schema_version": STOKES_BENCHMARK_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "stokes_momentum_benchmark",
        "status": "passed",
        "manufactured_solution": manufactured_solution,
        "viscosity": viscosity,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "boundary_node_count": len(_boundary_nodes(mesh)),
        "pressure": {
            "model": "manufactured_linear_pressure",
            "gradient": [pressure_gradient[0], pressure_gradient[1]],
            "role": "known pressure-gradient source in the momentum equations",
        },
        "linear_systems": {
            "u": _compact_linear_system(u_linear_system),
            "v": _compact_linear_system(v_linear_system),
        },
        "metrics": {
            "node_velocity_l2_error": node_velocity_l2,
            "node_velocity_linf_error": node_velocity_linf,
            "cell_center_velocity_l2_error": sqrt(weighted_error / total_measure) if total_measure > 0 else None,
            "cell_divergence_l2": sqrt(weighted_divergence / total_measure) if total_measure > 0 else None,
            "cell_divergence_linf": max((abs(value) for value in divergence.values()), default=0.0),
            "u_final_residual_l2": u_linear_system["final_residual_l2"],
            "v_final_residual_l2": v_linear_system["final_residual_l2"],
        },
        "limitations": [
            "U6 solves a manufactured Stokes momentum benchmark only.",
            "Pressure is a manufactured source field, not a solved pressure-Poisson correction yet.",
            "The current implementation supports 2D triangular meshes with exact velocity Dirichlet values on all boundary nodes.",
            "This is not VOF, turbulence, GPU acceleration, or Fluent replacement behavior.",
        ],
    }


def _compact_linear_system(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload["schema_version"],
        "storage": payload["storage"],
        "method": payload["method"],
        "n_rows": payload["n_rows"],
        "n_cols": payload["n_cols"],
        "nnz": payload["nnz"],
        "density": payload["density"],
        "converged": payload["converged"],
        "iterations": payload["iterations"],
        "tolerance": payload["tolerance"],
        "constrained_node_count": payload["constrained_node_count"],
    }


def _write_stokes_residual_history(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["component", "iteration", "residual_l2", "residual_linf"])
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


def _stokes_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    pressure = qoi["pressure"]
    return "\n".join(
        [
            "# FastFluent Unstructured Stokes Benchmark",
            "",
            f"Status: `{qoi['status']}`",
            f"Manufactured solution: `{qoi['manufactured_solution']}`",
            f"Cells: `{qoi['cell_count']}`",
            f"Pressure gradient: `{pressure['gradient']}`",
            "",
            "## Metrics",
            "",
            f"- Node velocity L2 error: `{metrics['node_velocity_l2_error']}`",
            f"- Cell-center velocity L2 error: `{metrics['cell_center_velocity_l2_error']}`",
            f"- Cell divergence L2: `{metrics['cell_divergence_l2']}`",
            f"- U residual L2: `{metrics['u_final_residual_l2']}`",
            f"- V residual L2: `{metrics['v_final_residual_l2']}`",
            "",
            "## Scope",
            "",
            "This gate validates a manufactured Stokes momentum benchmark. It does not solve a production incompressible-flow case.",
            "",
        ]
    )


def _require_supported_cells(mesh: UnstructuredMesh) -> None:
    unsupported = sorted({cell.kind for cell in mesh.cells if cell.kind != "triangle"})
    if unsupported:
        raise ValueError(f"Stokes U6 currently supports triangle cells only; unsupported cells: {unsupported}.")
