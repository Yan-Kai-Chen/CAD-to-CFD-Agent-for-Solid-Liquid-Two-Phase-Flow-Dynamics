"""Manufactured pressure-projection benchmark for the unstructured backend."""

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


PROJECTION_BENCHMARK_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_projection_benchmark_v1"


def run_projection_benchmark_case(
    mesh_file: str | Path,
    *,
    output_dir: str | Path | None = None,
    manufactured_solution: str = "quadratic_correction",
    correction_strength: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Run a manufactured pressure-correction projection benchmark."""

    mesh_path = Path(mesh_file)
    target_dir = Path(output_dir) if output_dir else unique_path(mesh_path.parent / f"{mesh_path.stem}_projection")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
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
                operation="solve_projection_benchmark",
                message="Projection benchmark was blocked by mesh quality gate.",
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
            artifacts["projection_status"] = str(target_dir / "projection_status.json")
            _write_json(target_dir / "projection_status.json", result.to_dict())
            return result.to_dict()
        _require_supported_cells(mesh)
        fv_geometry = build_fv_geometry(mesh).to_dict()
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry))
        solution = solve_manufactured_projection(
            mesh,
            manufactured_solution=manufactured_solution,
            correction_strength=correction_strength,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["projection_linear_system"] = str(_write_json(target_dir / "projection_linear_system.json", solution["linear_system"]))
        artifacts["projection_residual_history"] = str(
            _write_residual_history(target_dir / "projection_residual_history.csv", solution["residual_history"])
        )
        artifacts["projection_qoi"] = str(_write_json(target_dir / "projection_qoi.json", solution["qoi"]))
        artifacts["projection_solution_vtu"] = str(
            write_vector_solution_vtu(
                mesh,
                target_dir / "projection_solution.vtu",
                solution["corrected_velocity"],
                exact_vectors=solution["target_velocity"],
                error_vectors=solution["velocity_error"],
                scalar_fields={"pressure_correction": solution["pressure_correction"]},
            )
        )
        artifacts["projection_report"] = str(_write_text(target_dir / "projection_report.md", _projection_markdown(solution["qoi"])))
        result = AgentResult.success(
            backend="unstructured_fvm",
            operation="solve_projection_benchmark",
            message="Manufactured pressure-projection benchmark completed.",
            outputs={
                "artifacts": artifacts,
                "manifest": manifest,
                "quality": quality,
                "fv_geometry": fv_geometry,
                "linear_system": solution["linear_system"],
                "qoi": solution["qoi"],
                "solver_execution": "pressure_projection_linear_system",
            },
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        artifacts["projection_status"] = str(target_dir / "projection_status.json")
        _write_json(target_dir / "projection_status.json", result.to_dict())
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_projection_benchmark",
            message="Projection benchmark failed before solver completion.",
            errors=[str(exc)],
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"projection_status": str(target_dir / "projection_status.json")}
        _write_json(target_dir / "projection_status.json", failure.to_dict())
        return failure.to_dict()


def solve_manufactured_projection(
    mesh: UnstructuredMesh,
    *,
    manufactured_solution: str = "quadratic_correction",
    correction_strength: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
) -> dict[str, Any]:
    exact = _manufactured_solution(mesh, manufactured_solution, correction_strength=correction_strength)
    linear_system = _assemble_pressure_correction_system(mesh, exact["correction"], exact["poisson_source"])
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
            "Projection pressure-correction solve did not converge: "
            f"method={solve_result.method}, iterations={solve_result.iterations}, "
            f"final_residual_l2={solve_result.final_residual_l2}."
        )
    node_tags: list[int] = linear_system["node_tags"]
    node_index: dict[int, int] = linear_system["node_index"]
    pressure_correction = {tag: solve_result.values[node_index[tag]] for tag in node_tags}
    predicted_velocity = {tag: exact["predicted_velocity"](*mesh.nodes[tag].to_tuple()) for tag in node_tags}
    target_velocity = {tag: exact["target_velocity"](*mesh.nodes[tag].to_tuple()) for tag in node_tags}
    correction_gradients = _recover_node_gradients(mesh, pressure_correction)
    corrected_velocity = {
        tag: (
            predicted_velocity[tag][0] - correction_gradients[tag][0],
            predicted_velocity[tag][1] - correction_gradients[tag][1],
            0.0,
        )
        for tag in node_tags
    }
    velocity_error = {
        tag: (
            corrected_velocity[tag][0] - target_velocity[tag][0],
            corrected_velocity[tag][1] - target_velocity[tag][1],
            0.0,
        )
        for tag in node_tags
    }
    predicted_divergence = _cell_divergence(
        mesh,
        {tag: predicted_velocity[tag][0] for tag in node_tags},
        {tag: predicted_velocity[tag][1] for tag in node_tags},
    )
    corrected_divergence = _cell_divergence(
        mesh,
        {tag: corrected_velocity[tag][0] for tag in node_tags},
        {tag: corrected_velocity[tag][1] for tag in node_tags},
    )
    matrix_metadata = solve_result.metadata(matrix)
    matrix_metadata.update(
        {
            "assembly": "p1_triangle_pressure_correction_poisson",
            "boundary_condition": "exact_dirichlet_pressure_correction_on_boundary_nodes",
            "constrained_node_count": len(linear_system["constrained_values"]),
            "rhs_l2": sqrt(sum(value * value for value in rhs)),
        }
    )
    qoi = _build_qoi(
        mesh,
        manufactured_solution,
        correction_strength,
        pressure_correction,
        predicted_velocity,
        corrected_velocity,
        target_velocity,
        velocity_error,
        predicted_divergence,
        corrected_divergence,
        matrix_metadata,
    )
    return {
        "pressure_correction": pressure_correction,
        "predicted_velocity": predicted_velocity,
        "corrected_velocity": corrected_velocity,
        "target_velocity": target_velocity,
        "velocity_error": velocity_error,
        "predicted_divergence": predicted_divergence,
        "corrected_divergence": corrected_divergence,
        "linear_system": matrix_metadata,
        "residual_history": solve_result.residual_history,
        "qoi": qoi,
    }


def _assemble_pressure_correction_system(
    mesh: UnstructuredMesh,
    correction_fn: Callable[[float, float, float], float],
    source_fn: Callable[[float, float, float], float],
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    size = len(node_tags)
    rows: list[dict[int, float]] = [dict() for _ in range(size)]
    rhs = [0.0 for _ in range(size)]
    for cell in mesh.cells:
        _assemble_triangle(rows, rhs, mesh, cell, node_index, source_fn)
    boundary_nodes = _boundary_nodes(mesh)
    if not boundary_nodes:
        raise ValueError("Projection benchmark requires pressure-correction Dirichlet boundary nodes.")
    constrained = {tag: correction_fn(*mesh.nodes[tag].to_tuple()) for tag in boundary_nodes}
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
) -> None:
    if cell.kind != "triangle":
        raise ValueError(f"Projection U7 currently supports triangle cells only, got {cell.kind}.")
    points = [mesh.nodes[tag].to_tuple() for tag in cell.node_tags]
    area = abs(triangle_signed_area_xy(points[0], points[1], points[2]))
    if area <= 0:
        raise ValueError(f"Cannot assemble projection benchmark for non-positive triangle area in element {cell.tag}.")
    gradients = _triangle_basis_gradients(points, area)
    local_source = source_fn(*mesh.cell_center(cell))
    for local_i, tag_i in enumerate(cell.node_tags):
        global_i = node_index[tag_i]
        rhs[global_i] += local_source * area / 3.0
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


def _manufactured_solution(mesh: UnstructuredMesh, name: str, *, correction_strength: float) -> dict[str, Any]:
    bounds = _mesh_bounds(mesh)
    xmin = bounds["xmin"]
    ymin = bounds["ymin"]
    xc = 0.5 * (bounds["xmin"] + bounds["xmax"])
    yc = 0.5 * (bounds["ymin"] + bounds["ymax"])
    if name == "quadratic_correction":
        strength = correction_strength

        def correction(x, y, z):
            return 0.5 * strength * (x - xmin) * (x - xmin)

        def correction_gradient(x, y, z):
            return (strength * (x - xmin), 0.0, 0.0)

        def target_velocity(x, y, z):
            return (x - xc, -(y - yc), 0.0)

        def predicted_velocity(x, y, z):
            base = target_velocity(x, y, z)
            grad = correction_gradient(x, y, z)
            return (base[0] + grad[0], base[1] + grad[1], 0.0)

        return {
            "name": name,
            "correction": correction,
            "correction_gradient": correction_gradient,
            "target_velocity": target_velocity,
            "predicted_velocity": predicted_velocity,
            "poisson_source": lambda x, y, z: -strength,
            "expected_predicted_divergence": strength,
        }
    if name == "linear_correction":
        strength = correction_strength

        def correction(x, y, z):
            return strength * ((x - xmin) + 0.5 * (y - ymin))

        def correction_gradient(x, y, z):
            return (strength, 0.5 * strength, 0.0)

        def target_velocity(x, y, z):
            return (x - xc, -(y - yc), 0.0)

        def predicted_velocity(x, y, z):
            base = target_velocity(x, y, z)
            grad = correction_gradient(x, y, z)
            return (base[0] + grad[0], base[1] + grad[1], 0.0)

        return {
            "name": name,
            "correction": correction,
            "correction_gradient": correction_gradient,
            "target_velocity": target_velocity,
            "predicted_velocity": predicted_velocity,
            "poisson_source": lambda x, y, z: 0.0,
            "expected_predicted_divergence": 0.0,
        }
    raise ValueError(f"Unsupported manufactured projection solution: {name}")


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
    recovered = {}
    for tag, values in accum.items():
        if values[3] <= 0:
            recovered[tag] = (0.0, 0.0, 0.0)
        else:
            recovered[tag] = (values[0] / values[3], values[1] / values[3], values[2] / values[3])
    return recovered


def _cell_divergence(mesh: UnstructuredMesh, u_values: dict[int, float], v_values: dict[int, float]) -> dict[int, float]:
    u_gradients = node_scalar_cell_gradients(mesh, u_values)
    v_gradients = node_scalar_cell_gradients(mesh, v_values)
    return {cell_index: u_gradients[cell_index][0] + v_gradients[cell_index][1] for cell_index in u_gradients}


def _build_qoi(
    mesh: UnstructuredMesh,
    manufactured_solution: str,
    correction_strength: float,
    pressure_correction: dict[int, float],
    predicted_velocity: dict[int, tuple[float, float, float]],
    corrected_velocity: dict[int, tuple[float, float, float]],
    target_velocity: dict[int, tuple[float, float, float]],
    velocity_error: dict[int, tuple[float, float, float]],
    predicted_divergence: dict[int, float],
    corrected_divergence: dict[int, float],
    linear_system: dict[str, Any],
) -> dict[str, Any]:
    total_measure = 0.0
    predicted_divergence_l2 = 0.0
    corrected_divergence_l2 = 0.0
    velocity_l2 = 0.0
    for cell_index, cell in enumerate(mesh.cells):
        measure = abs(mesh.cell_signed_measure(cell))
        predicted_divergence_l2 += predicted_divergence[cell_index] * predicted_divergence[cell_index] * measure
        corrected_divergence_l2 += corrected_divergence[cell_index] * corrected_divergence[cell_index] * measure
        avg_error_u = sum(velocity_error[tag][0] for tag in cell.node_tags) / len(cell.node_tags)
        avg_error_v = sum(velocity_error[tag][1] for tag in cell.node_tags) / len(cell.node_tags)
        velocity_l2 += (avg_error_u * avg_error_u + avg_error_v * avg_error_v) * measure
        total_measure += measure
    node_velocity_l2 = sqrt(
        sum(error[0] * error[0] + error[1] * error[1] for error in velocity_error.values()) / max(1, len(velocity_error))
    )
    node_velocity_linf = max((sqrt(error[0] * error[0] + error[1] * error[1]) for error in velocity_error.values()), default=0.0)
    before_l2 = sqrt(predicted_divergence_l2 / total_measure) if total_measure > 0 else None
    after_l2 = sqrt(corrected_divergence_l2 / total_measure) if total_measure > 0 else None
    reduction = (after_l2 / before_l2) if before_l2 and before_l2 > 0 else None
    return {
        "schema_version": PROJECTION_BENCHMARK_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "pressure_projection_benchmark",
        "status": "passed",
        "manufactured_solution": manufactured_solution,
        "correction_strength": correction_strength,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "boundary_node_count": len(_boundary_nodes(mesh)),
        "pressure_correction": {
            "model": "manufactured_dirichlet_pressure_correction",
            "min": min(pressure_correction.values()) if pressure_correction else None,
            "max": max(pressure_correction.values()) if pressure_correction else None,
        },
        "linear_system": _compact_linear_system(linear_system),
        "metrics": {
            "predicted_divergence_l2": before_l2,
            "corrected_divergence_l2": after_l2,
            "divergence_reduction_ratio": reduction,
            "predicted_divergence_linf": max((abs(value) for value in predicted_divergence.values()), default=0.0),
            "corrected_divergence_linf": max((abs(value) for value in corrected_divergence.values()), default=0.0),
            "node_velocity_l2_error": node_velocity_l2,
            "node_velocity_linf_error": node_velocity_linf,
            "cell_velocity_l2_error": sqrt(velocity_l2 / total_measure) if total_measure > 0 else None,
            "pressure_correction_final_residual_l2": linear_system["final_residual_l2"],
        },
        "limitations": [
            "U7 solves a manufactured pressure-correction projection benchmark only.",
            "The pressure correction uses exact Dirichlet values, not production pressure boundary conditions.",
            "Velocity correction uses recovered nodal gradients from a P1 pressure-correction field.",
            "This is not transient Navier-Stokes, SIMPLE/PISO, VOF, turbulence, GPU acceleration, or Fluent replacement behavior.",
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


def _projection_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    return "\n".join(
        [
            "# FastFluent Unstructured Projection Benchmark",
            "",
            f"Status: `{qoi['status']}`",
            f"Manufactured solution: `{qoi['manufactured_solution']}`",
            f"Cells: `{qoi['cell_count']}`",
            "",
            "## Metrics",
            "",
            f"- Predicted divergence L2: `{metrics['predicted_divergence_l2']}`",
            f"- Corrected divergence L2: `{metrics['corrected_divergence_l2']}`",
            f"- Divergence reduction ratio: `{metrics['divergence_reduction_ratio']}`",
            f"- Velocity L2 error: `{metrics['node_velocity_l2_error']}`",
            f"- Pressure-correction residual L2: `{metrics['pressure_correction_final_residual_l2']}`",
            "",
            "## Scope",
            "",
            "This gate validates a manufactured pressure-correction projection route. It is not a production pressure solver.",
            "",
        ]
    )


def _require_supported_cells(mesh: UnstructuredMesh) -> None:
    unsupported = sorted({cell.kind for cell in mesh.cells if cell.kind != "triangle"})
    if unsupported:
        raise ValueError(f"Projection U7 currently supports triangle cells only; unsupported cells: {unsupported}.")
