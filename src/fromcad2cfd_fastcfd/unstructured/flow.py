"""Iterative unstructured flow benchmark built from the projection gate."""

from __future__ import annotations

import csv
import json
from math import sqrt
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .boundary import validate_boundary_contract
from .geometry import build_fv_geometry, node_scalar_cell_gradients
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .linear import SparseMatrixCSR, solve_linear_system
from .mesh import MeshElement, UnstructuredMesh, triangle_signed_area_xy
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .vtu import write_mesh_vtu, write_vector_solution_vtu


FLOW_BENCHMARK_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_flow_benchmark_v1"


def run_flow_benchmark_case(
    mesh_file: str | Path,
    *,
    output_dir: str | Path | None = None,
    iterations: int = 5,
    correction_strength: float = 1.0,
    relaxation: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Run the U8/U10 iterative pressure-projection flow benchmark."""

    mesh_path = Path(mesh_file)
    target_dir = Path(output_dir) if output_dir else unique_path(mesh_path.parent / f"{mesh_path.stem}_flow")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        if iterations < 1:
            raise ValueError("Flow benchmark iterations must be at least 1.")
        if not (0.0 < relaxation <= 1.0):
            raise ValueError("Flow benchmark relaxation must be in the interval (0, 1].")
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=())
        boundary_contract = validate_boundary_contract(mesh, required_patches=required_patches)
        artifacts: dict[str, str] = {
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
            "flow_boundary_contract": str(_write_json(target_dir / "flow_boundary_contract.json", boundary_contract)),
            "mesh_vtu": str(write_mesh_vtu(mesh, target_dir / "mesh.vtu")),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_flow_benchmark",
                message="Flow benchmark was blocked by mesh quality gate.",
                errors=quality["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "solver_execution": "blocked_by_mesh_quality",
                }
            )
            artifacts["flow_status"] = str(target_dir / "flow_status.json")
            _write_json(target_dir / "flow_status.json", result.to_dict())
            return result.to_dict()
        if boundary_contract["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_flow_benchmark",
                message="Flow benchmark was blocked by boundary-condition contract.",
                errors=boundary_contract["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "solver_execution": "blocked_by_boundary_contract",
                }
            )
            artifacts["flow_status"] = str(target_dir / "flow_status.json")
            _write_json(target_dir / "flow_status.json", result.to_dict())
            return result.to_dict()
        _require_supported_cells(mesh)
        fv_geometry = build_fv_geometry(mesh).to_dict()
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry))
        solution = solve_iterative_projection_flow(
            mesh,
            iterations=iterations,
            correction_strength=correction_strength,
            relaxation=relaxation,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["flow_residual_history"] = str(_write_flow_residual_history(target_dir / "flow_residual_history.csv", solution["residual_history"]))
        artifacts["flow_qoi"] = str(_write_json(target_dir / "flow_qoi.json", solution["qoi"]))
        artifacts["flow_solution_vtu"] = str(
            write_vector_solution_vtu(
                mesh,
                target_dir / "flow_solution.vtu",
                solution["velocity"],
                exact_vectors=solution["target_velocity"],
                error_vectors=solution["velocity_error"],
                scalar_fields={"last_pressure_correction": solution["last_pressure_correction"]},
            )
        )
        artifacts["flow_report"] = str(_write_text(target_dir / "flow_report.md", _flow_markdown(solution["qoi"])))
        result = AgentResult.success(
            backend="unstructured_fvm",
            operation="solve_flow_benchmark",
            message="Iterative pressure-projection flow benchmark completed.",
            outputs={
                "artifacts": artifacts,
                "manifest": manifest,
                "quality": quality,
                "boundary_contract": boundary_contract,
                "fv_geometry": fv_geometry,
                "qoi": solution["qoi"],
                "solver_execution": "iterative_projection_flow_benchmark",
            },
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        artifacts["flow_status"] = str(target_dir / "flow_status.json")
        _write_json(target_dir / "flow_status.json", result.to_dict())
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_flow_benchmark",
            message="Flow benchmark failed before solver completion.",
            errors=[str(exc)],
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"flow_status": str(target_dir / "flow_status.json")}
        _write_json(target_dir / "flow_status.json", failure.to_dict())
        return failure.to_dict()


def solve_iterative_projection_flow(
    mesh: UnstructuredMesh,
    *,
    iterations: int = 5,
    correction_strength: float = 1.0,
    relaxation: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    exact = _manufactured_flow_fields(mesh, correction_strength=correction_strength)
    target_velocity = {tag: exact["target_velocity"](*mesh.nodes[tag].to_tuple()) for tag in node_tags}
    velocity = {tag: exact["initial_velocity"](*mesh.nodes[tag].to_tuple()) for tag in node_tags}
    residual_history: list[dict[str, Any]] = []
    last_pressure_correction = {tag: 0.0 for tag in node_tags}
    initial_divergence_l2: float | None = None
    final_divergence_l2: float | None = None
    final_linear_system: dict[str, Any] | None = None
    for iteration in range(1, iterations + 1):
        before_divergence = _cell_divergence(
            mesh,
            {tag: velocity[tag][0] for tag in node_tags},
            {tag: velocity[tag][1] for tag in node_tags},
        )
        before_l2 = _cell_metric_l2(mesh, before_divergence)
        if initial_divergence_l2 is None:
            initial_divergence_l2 = before_l2
        pressure = _solve_pressure_correction_from_divergence(
            mesh,
            before_divergence,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        last_pressure_correction = pressure["values"]
        gradients = _recover_node_gradients(mesh, last_pressure_correction)
        update_l2 = _velocity_update_l2(mesh, gradients, relaxation=relaxation)
        velocity = {
            tag: (
                velocity[tag][0] - relaxation * gradients[tag][0],
                velocity[tag][1] - relaxation * gradients[tag][1],
                0.0,
            )
            for tag in node_tags
        }
        after_divergence = _cell_divergence(
            mesh,
            {tag: velocity[tag][0] for tag in node_tags},
            {tag: velocity[tag][1] for tag in node_tags},
        )
        after_l2 = _cell_metric_l2(mesh, after_divergence)
        final_divergence_l2 = after_l2
        final_linear_system = pressure["linear_system"]
        residual_history.append(
            {
                "iteration": iteration,
                "predicted_divergence_l2": before_l2,
                "corrected_divergence_l2": after_l2,
                "divergence_reduction_ratio": after_l2 / before_l2 if before_l2 > 0 else 0.0,
                "pressure_residual_l2": pressure["linear_system"]["final_residual_l2"],
                "linear_iterations": pressure["linear_system"]["iterations"],
                "velocity_update_l2": update_l2,
            }
        )
    velocity_error = {
        tag: (
            velocity[tag][0] - target_velocity[tag][0],
            velocity[tag][1] - target_velocity[tag][1],
            0.0,
        )
        for tag in node_tags
    }
    qoi = _build_qoi(
        mesh,
        iterations,
        correction_strength,
        relaxation,
        velocity,
        target_velocity,
        velocity_error,
        residual_history,
        final_linear_system or {},
        initial_divergence_l2 or 0.0,
        final_divergence_l2 or 0.0,
    )
    return {
        "velocity": velocity,
        "target_velocity": target_velocity,
        "velocity_error": velocity_error,
        "last_pressure_correction": last_pressure_correction,
        "residual_history": residual_history,
        "qoi": qoi,
    }


def _solve_pressure_correction_from_divergence(
    mesh: UnstructuredMesh,
    divergence: dict[int, float],
    *,
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    rows: list[dict[int, float]] = [dict() for _ in node_tags]
    rhs = [0.0 for _ in node_tags]
    for cell_index, cell in enumerate(mesh.cells):
        _assemble_triangle(rows, rhs, mesh, cell, node_index, -divergence[cell_index])
    boundary_nodes = _boundary_nodes(mesh)
    constrained = {tag: 0.0 for tag in boundary_nodes}
    _apply_dirichlet_sparse_rows(rows, rhs, node_index, constrained)
    matrix = SparseMatrixCSR.from_rows(rows, n_cols=len(node_tags), drop_tolerance=1.0e-15)
    solve_result = solve_linear_system(
        matrix,
        rhs,
        method=linear_solver,
        tolerance=linear_tolerance,
        max_iterations=max_linear_iterations,
    )
    if not solve_result.converged:
        raise ValueError(
            "Flow pressure-correction solve did not converge: "
            f"method={solve_result.method}, iterations={solve_result.iterations}, "
            f"final_residual_l2={solve_result.final_residual_l2}."
        )
    metadata = solve_result.metadata(matrix)
    metadata.update(
        {
            "assembly": "p1_triangle_iterative_pressure_correction",
            "boundary_condition": "zero_dirichlet_pressure_correction_on_boundary_nodes",
            "constrained_node_count": len(constrained),
            "rhs_l2": sqrt(sum(value * value for value in rhs)),
        }
    )
    return {
        "values": {tag: solve_result.values[node_index[tag]] for tag in node_tags},
        "linear_system": metadata,
    }


def _assemble_triangle(
    rows: list[dict[int, float]],
    rhs: list[float],
    mesh: UnstructuredMesh,
    cell: MeshElement,
    node_index: dict[int, int],
    source: float,
) -> None:
    if cell.kind != "triangle":
        raise ValueError(f"Flow benchmark currently supports triangle cells only, got {cell.kind}.")
    points = [mesh.nodes[tag].to_tuple() for tag in cell.node_tags]
    area = abs(triangle_signed_area_xy(points[0], points[1], points[2]))
    if area <= 0:
        raise ValueError(f"Cannot assemble flow benchmark for non-positive triangle area in element {cell.tag}.")
    gradients = _triangle_basis_gradients(points, area)
    for local_i, tag_i in enumerate(cell.node_tags):
        global_i = node_index[tag_i]
        rhs[global_i] += source * area / 3.0
        for local_j, tag_j in enumerate(cell.node_tags):
            global_j = node_index[tag_j]
            rows[global_i][global_j] = rows[global_i].get(global_j, 0.0) + area * (
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


def _manufactured_flow_fields(mesh: UnstructuredMesh, *, correction_strength: float):
    bounds = _mesh_bounds(mesh)
    xmin = bounds["xmin"]
    xc = 0.5 * (bounds["xmin"] + bounds["xmax"])
    yc = 0.5 * (bounds["ymin"] + bounds["ymax"])

    def target_velocity(x, y, z):
        return (x - xc, -(y - yc), 0.0)

    def initial_velocity(x, y, z):
        return (target_velocity(x, y, z)[0] + correction_strength * (x - xmin), target_velocity(x, y, z)[1], 0.0)

    return {"target_velocity": target_velocity, "initial_velocity": initial_velocity}


def _recover_node_gradients(mesh: UnstructuredMesh, scalar_values: dict[int, float]) -> dict[int, tuple[float, float, float]]:
    cell_gradients = node_scalar_cell_gradients(mesh, scalar_values)
    accum = {tag: [0.0, 0.0, 0.0, 0.0] for tag in mesh.nodes}
    for cell_index, cell in enumerate(mesh.cells):
        weight = abs(mesh.cell_signed_measure(cell))
        gradient = cell_gradients[cell_index]
        for tag in cell.node_tags:
            accum[tag][0] += gradient[0] * weight
            accum[tag][1] += gradient[1] * weight
            accum[tag][2] += gradient[2] * weight
            accum[tag][3] += weight
    return {
        tag: (values[0] / values[3], values[1] / values[3], values[2] / values[3]) if values[3] > 0 else (0.0, 0.0, 0.0)
        for tag, values in accum.items()
    }


def _cell_divergence(mesh: UnstructuredMesh, u_values: dict[int, float], v_values: dict[int, float]) -> dict[int, float]:
    u_gradients = node_scalar_cell_gradients(mesh, u_values)
    v_gradients = node_scalar_cell_gradients(mesh, v_values)
    return {cell_index: u_gradients[cell_index][0] + v_gradients[cell_index][1] for cell_index in u_gradients}


def _cell_metric_l2(mesh: UnstructuredMesh, values: dict[int, float]) -> float:
    total = 0.0
    weighted = 0.0
    for cell_index, cell in enumerate(mesh.cells):
        measure = abs(mesh.cell_signed_measure(cell))
        total += measure
        weighted += values[cell_index] * values[cell_index] * measure
    return sqrt(weighted / total) if total > 0 else 0.0


def _velocity_update_l2(mesh: UnstructuredMesh, gradients: dict[int, tuple[float, float, float]], *, relaxation: float) -> float:
    if not gradients:
        return 0.0
    return sqrt(
        sum((relaxation * gradient[0]) ** 2 + (relaxation * gradient[1]) ** 2 for gradient in gradients.values()) / len(gradients)
    )


def _build_qoi(
    mesh: UnstructuredMesh,
    iterations: int,
    correction_strength: float,
    relaxation: float,
    velocity: dict[int, tuple[float, float, float]],
    target_velocity: dict[int, tuple[float, float, float]],
    velocity_error: dict[int, tuple[float, float, float]],
    residual_history: list[dict[str, Any]],
    final_linear_system: dict[str, Any],
    initial_divergence_l2: float,
    final_divergence_l2: float,
) -> dict[str, Any]:
    node_velocity_l2 = sqrt(
        sum(error[0] * error[0] + error[1] * error[1] for error in velocity_error.values()) / max(1, len(velocity_error))
    )
    node_velocity_linf = max((sqrt(error[0] * error[0] + error[1] * error[1]) for error in velocity_error.values()), default=0.0)
    return {
        "schema_version": FLOW_BENCHMARK_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "iterative_projection_flow_benchmark",
        "status": "passed",
        "iterations": iterations,
        "correction_strength": correction_strength,
        "relaxation": relaxation,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "boundary_node_count": len(_boundary_nodes(mesh)),
        "linear_system": _compact_linear_system(final_linear_system) if final_linear_system else None,
        "metrics": {
            "initial_divergence_l2": initial_divergence_l2,
            "final_divergence_l2": final_divergence_l2,
            "global_divergence_reduction_ratio": final_divergence_l2 / initial_divergence_l2 if initial_divergence_l2 > 0 else 0.0,
            "final_step_divergence_reduction_ratio": residual_history[-1]["divergence_reduction_ratio"] if residual_history else None,
            "node_velocity_l2_error": node_velocity_l2,
            "node_velocity_linf_error": node_velocity_linf,
            "final_pressure_residual_l2": residual_history[-1]["pressure_residual_l2"] if residual_history else None,
            "final_velocity_update_l2": residual_history[-1]["velocity_update_l2"] if residual_history else None,
        },
        "residual_history_rows": len(residual_history),
        "limitations": [
            "U8-U10 run a benchmark projection loop, not a production transient Navier-Stokes solver.",
            "Pressure correction uses zero Dirichlet correction on boundary nodes.",
            "The benchmark verifies iterative mass-balance reduction and agent-facing artifact contracts only.",
            "This is not VOF, rheology, turbulence, GPU acceleration, or Fluent replacement behavior.",
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


def _write_flow_residual_history(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "iteration",
                "predicted_divergence_l2",
                "corrected_divergence_l2",
                "divergence_reduction_ratio",
                "pressure_residual_l2",
                "linear_iterations",
                "velocity_update_l2",
            ],
        )
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


def _flow_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    return "\n".join(
        [
            "# FastFluent Unstructured Flow Benchmark",
            "",
            f"Status: `{qoi['status']}`",
            f"Iterations: `{qoi['iterations']}`",
            f"Cells: `{qoi['cell_count']}`",
            "",
            "## Metrics",
            "",
            f"- Initial divergence L2: `{metrics['initial_divergence_l2']}`",
            f"- Final divergence L2: `{metrics['final_divergence_l2']}`",
            f"- Global divergence reduction ratio: `{metrics['global_divergence_reduction_ratio']}`",
            f"- Final pressure residual L2: `{metrics['final_pressure_residual_l2']}`",
            f"- Final velocity update L2: `{metrics['final_velocity_update_l2']}`",
            "",
            "## Scope",
            "",
            "This is a benchmark projection loop with a boundary-condition contract. It is not a production CFD solver.",
            "",
        ]
    )


def _require_supported_cells(mesh: UnstructuredMesh) -> None:
    unsupported = sorted({cell.kind for cell in mesh.cells if cell.kind != "triangle"})
    if unsupported:
        raise ValueError(f"Flow benchmark currently supports triangle cells only; unsupported cells: {unsupported}.")
