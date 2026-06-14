"""Algebraic eddy-viscosity turbulent channel benchmark."""

from __future__ import annotations

import csv
import json
from math import sqrt
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .boundary import BoundaryCondition, validate_boundary_contract
from .channel_validation import write_unit_square_channel_mesh
from .geometry import build_fv_geometry, node_scalar_cell_gradients
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .linear import SparseMatrixCSR, solve_linear_system
from .mesh import MeshElement, UnstructuredMesh, triangle_signed_area_xy
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .vtu import write_mesh_vtu, write_vector_solution_vtu


TURBULENT_CHANNEL_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_turbulent_channel_v1"


def run_turbulent_channel_case(
    mesh_file: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    density: float = 1.0,
    molecular_viscosity: float = 1.0e-3,
    pressure_drop: float = 0.05,
    iterations: int = 12,
    relaxation: float = 0.55,
    kappa: float = 0.41,
    max_mixing_length_fraction: float = 0.09,
    turbulent_viscosity_cap_ratio: float = 1000.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Run a simplified RANS-like turbulent channel benchmark.

    The gate solves a pressure-driven channel with a Prandtl mixing-length
    eddy-viscosity closure. It is a real iterative turbulence-closure solve, but
    it remains a benchmark and setup-evidence route rather than a production
    turbulence CFD solver.
    """

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "unstructured_turbulent_channel" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        _validate_inputs(
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            relaxation=relaxation,
            kappa=kappa,
            max_mixing_length_fraction=max_mixing_length_fraction,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
        )
        mesh_path = Path(mesh_file) if mesh_file else write_unit_square_channel_mesh(target_dir / "public_turbulent_channel.msh", nx=10, ny=10)
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=())
        boundary_contract = validate_boundary_contract(
            mesh,
            required_patches=required_patches,
            boundary_conditions=_turbulent_boundary_conditions(),
        )
        artifacts: dict[str, str] = {
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
            "turbulent_boundary_contract": str(_write_json(target_dir / "turbulent_boundary_contract.json", boundary_contract)),
            "mesh_vtu": str(write_mesh_vtu(mesh, target_dir / "mesh.vtu")),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_turbulent_channel",
                message="Turbulent channel solve was blocked by mesh quality.",
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
            artifacts["turbulent_channel_status"] = str(_write_json(target_dir / "turbulent_channel_status.json", result.to_dict()))
            return result.to_dict()
        if boundary_contract["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_turbulent_channel",
                message="Turbulent channel solve was blocked by boundary-condition contract.",
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
            artifacts["turbulent_channel_status"] = str(_write_json(target_dir / "turbulent_channel_status.json", result.to_dict()))
            return result.to_dict()
        _require_triangles(mesh)
        fv_geometry = build_fv_geometry(mesh)
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry.to_dict()))
        solution = solve_algebraic_eddy_viscosity_channel(
            mesh,
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            relaxation=relaxation,
            kappa=kappa,
            max_mixing_length_fraction=max_mixing_length_fraction,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["turbulent_channel_qoi"] = str(_write_json(target_dir / "turbulent_channel_qoi.json", solution["qoi"]))
        artifacts["turbulent_channel_iterations"] = str(
            _write_iteration_history(target_dir / "turbulent_channel_iterations.csv", solution["iteration_history"])
        )
        artifacts["turbulent_channel_solution_vtu"] = str(
            write_vector_solution_vtu(
                mesh,
                target_dir / "turbulent_channel_solution.vtu",
                solution["velocity"],
                scalar_fields={
                    "turbulent_viscosity_ratio": solution["node_turbulent_viscosity_ratio"],
                    "effective_viscosity": solution["node_effective_viscosity"],
                },
            )
        )
        artifacts["turbulent_channel_report"] = str(_write_text(target_dir / "turbulent_channel_report.md", _turbulent_markdown(solution["qoi"])))
        if solution["qoi"]["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_turbulent_channel",
                message="Turbulent channel solve completed but did not pass acceptance checks.",
                errors=solution["qoi"]["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="solve_turbulent_channel",
                message="Algebraic eddy-viscosity turbulent channel solve completed.",
                outputs={
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "fv_geometry": fv_geometry.to_dict(),
                    "qoi": solution["qoi"],
                    "solver_execution": "algebraic_eddy_viscosity_turbulent_channel",
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
                    "qoi": solution["qoi"],
                    "solver_execution": "algebraic_eddy_viscosity_turbulent_channel_failed_acceptance",
                }
            )
        artifacts["turbulent_channel_status"] = str(_write_json(target_dir / "turbulent_channel_status.json", result.to_dict()))
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_turbulent_channel",
            message="Turbulent channel solve failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"turbulent_channel_status": str(target_dir / "turbulent_channel_status.json")}
        _write_json(target_dir / "turbulent_channel_status.json", failure.to_dict())
        return failure.to_dict()


def solve_algebraic_eddy_viscosity_channel(
    mesh: UnstructuredMesh,
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    iterations: int,
    relaxation: float,
    kappa: float,
    max_mixing_length_fraction: float,
    turbulent_viscosity_cap_ratio: float,
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
) -> dict[str, Any]:
    bounds = _mesh_bounds(mesh)
    length = bounds["xmax"] - bounds["xmin"]
    height = bounds["ymax"] - bounds["ymin"]
    if length <= 0 or height <= 0:
        raise ValueError("Turbulent channel requires positive length and height.")
    driving_source = pressure_drop / length
    node_tags = sorted(mesh.nodes)
    cell_count = len(mesh.cells)
    velocity_u = {tag: _laminar_profile(mesh.nodes[tag].y, bounds, driving_source=driving_source, viscosity=molecular_viscosity) for tag in node_tags}
    effective_viscosity = {index: molecular_viscosity for index in range(cell_count)}
    turbulent_viscosity = {index: 0.0 for index in range(cell_count)}
    history: list[dict[str, Any]] = []
    linear_metadata: dict[str, Any] = {}
    for iteration in range(1, iterations + 1):
        old_velocity = dict(velocity_u)
        old_effective = dict(effective_viscosity)
        turbulent_viscosity = _compute_mixing_length_turbulent_viscosity(
            mesh,
            velocity_u,
            bounds,
            density=density,
            molecular_viscosity=molecular_viscosity,
            kappa=kappa,
            max_mixing_length_fraction=max_mixing_length_fraction,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
        )
        raw_effective = {index: molecular_viscosity + turbulent_viscosity[index] for index in range(cell_count)}
        effective_viscosity = {
            index: (1.0 - relaxation) * old_effective[index] + relaxation * raw_effective[index] for index in range(cell_count)
        }
        solve = _solve_variable_viscosity_u(
            mesh,
            effective_viscosity=effective_viscosity,
            driving_source=driving_source,
            bounds=bounds,
            molecular_viscosity=molecular_viscosity,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        raw_u = solve["values"]
        velocity_u = {tag: (1.0 - relaxation) * old_velocity[tag] + relaxation * raw_u[tag] for tag in node_tags}
        linear_metadata = solve["linear_system"]
        velocity_update = _node_l2_delta(velocity_u, old_velocity)
        effective_update = _cell_l2_delta(effective_viscosity, old_effective)
        ratios = [turbulent_viscosity[index] / molecular_viscosity for index in range(cell_count)]
        history.append(
            {
                "iteration": iteration,
                "velocity_update_l2": velocity_update,
                "effective_viscosity_update_l2": effective_update,
                "max_turbulent_viscosity_ratio": max(ratios) if ratios else 0.0,
                "mean_turbulent_viscosity_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
                "linear_iterations": linear_metadata["iterations"],
                "linear_final_residual_l2": linear_metadata["final_residual_l2"],
            }
        )
    velocity = {tag: (velocity_u[tag], 0.0, 0.0) for tag in node_tags}
    node_turbulent_viscosity_ratio = _cell_field_to_node_field(
        mesh,
        {index: turbulent_viscosity[index] / molecular_viscosity for index in range(cell_count)},
    )
    node_effective_viscosity = _cell_field_to_node_field(mesh, effective_viscosity)
    qoi = _build_qoi(
        mesh,
        velocity_u,
        effective_viscosity,
        turbulent_viscosity,
        history,
        density=density,
        molecular_viscosity=molecular_viscosity,
        pressure_drop=pressure_drop,
        driving_source=driving_source,
        closure={
            "model": "prandtl_mixing_length_zero_equation",
            "kappa": kappa,
            "max_mixing_length_fraction": max_mixing_length_fraction,
            "turbulent_viscosity_cap_ratio": turbulent_viscosity_cap_ratio,
        },
        linear_system=linear_metadata,
    )
    return {
        "velocity": velocity,
        "node_turbulent_viscosity_ratio": node_turbulent_viscosity_ratio,
        "node_effective_viscosity": node_effective_viscosity,
        "iteration_history": history,
        "qoi": qoi,
    }


def _solve_variable_viscosity_u(
    mesh: UnstructuredMesh,
    *,
    effective_viscosity: dict[int, float],
    driving_source: float,
    bounds: dict[str, float],
    molecular_viscosity: float,
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    rows: list[dict[int, float]] = [dict() for _ in node_tags]
    rhs = [0.0 for _ in node_tags]
    for cell_index, cell in enumerate(mesh.cells):
        _assemble_triangle(rows, rhs, mesh, cell, node_index, driving_source, effective_viscosity[cell_index])
    constrained = _boundary_values(mesh, bounds, driving_source=driving_source, molecular_viscosity=molecular_viscosity)
    _apply_dirichlet_sparse_rows(rows, rhs, node_index, constrained)
    matrix = SparseMatrixCSR.from_rows(rows, n_cols=len(node_tags), drop_tolerance=1.0e-15)
    solve_result = solve_linear_system(matrix, rhs, method=linear_solver, tolerance=linear_tolerance, max_iterations=max_linear_iterations)
    if not solve_result.converged:
        raise ValueError(
            "Turbulent channel linear solve did not converge: "
            f"method={solve_result.method}, iterations={solve_result.iterations}, "
            f"final_residual_l2={solve_result.final_residual_l2}."
        )
    values = {tag: solve_result.values[node_index[tag]] for tag in node_tags}
    metadata = solve_result.metadata(matrix)
    metadata.update(
        {
            "component": "u",
            "assembly": "p1_triangle_variable_viscosity_momentum",
            "boundary_condition": "no_slip_walls_and_channel_profile_inlet_outlet",
            "constrained_node_count": len(constrained),
            "rhs_l2": sqrt(sum(value * value for value in rhs)),
        }
    )
    return {"values": values, "linear_system": metadata}


def _assemble_triangle(
    rows: list[dict[int, float]],
    rhs: list[float],
    mesh: UnstructuredMesh,
    cell: MeshElement,
    node_index: dict[int, int],
    source: float,
    viscosity: float,
) -> None:
    points = [mesh.nodes[tag].to_tuple() for tag in cell.node_tags]
    area = abs(triangle_signed_area_xy(points[0], points[1], points[2]))
    if area <= 0:
        raise ValueError(f"Cannot assemble turbulent channel for non-positive triangle area in element {cell.tag}.")
    gradients = _triangle_basis_gradients(points, area)
    for local_i, tag_i in enumerate(cell.node_tags):
        global_i = node_index[tag_i]
        rhs[global_i] += source * area / 3.0
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


def _compute_mixing_length_turbulent_viscosity(
    mesh: UnstructuredMesh,
    velocity_u: dict[int, float],
    bounds: dict[str, float],
    *,
    density: float,
    molecular_viscosity: float,
    kappa: float,
    max_mixing_length_fraction: float,
    turbulent_viscosity_cap_ratio: float,
) -> dict[int, float]:
    gradients = node_scalar_cell_gradients(mesh, velocity_u)
    height = bounds["ymax"] - bounds["ymin"]
    cap = molecular_viscosity * turbulent_viscosity_cap_ratio
    values: dict[int, float] = {}
    for cell_index, cell in enumerate(mesh.cells):
        center = mesh.cell_center(cell)
        wall_distance = min(center[1] - bounds["ymin"], bounds["ymax"] - center[1])
        mixing_length = min(kappa * max(0.0, wall_distance), max_mixing_length_fraction * height)
        shear_rate = abs(gradients[cell_index][1])
        mu_t = density * mixing_length * mixing_length * shear_rate
        values[cell_index] = min(cap, max(0.0, mu_t))
    return values


def _boundary_values(
    mesh: UnstructuredMesh,
    bounds: dict[str, float],
    *,
    driving_source: float,
    molecular_viscosity: float,
) -> dict[int, float]:
    values: dict[int, float] = {}
    patch_for_node: dict[int, set[str]] = {}
    for element in mesh.boundary_elements:
        patch = element.primary_physical_name or "unassigned"
        for tag in element.node_tags:
            patch_for_node.setdefault(tag, set()).add(patch)
    for tag, patches in patch_for_node.items():
        node = mesh.nodes[tag]
        if "wall" in patches:
            values[tag] = 0.0
        elif "inlet" in patches or "outlet" in patches:
            values[tag] = _laminar_profile(node.y, bounds, driving_source=driving_source, viscosity=molecular_viscosity)
        else:
            values[tag] = 0.0
    return values


def _laminar_profile(y: float, bounds: dict[str, float], *, driving_source: float, viscosity: float) -> float:
    return driving_source * (y - bounds["ymin"]) * (bounds["ymax"] - y) / (2.0 * viscosity)


def _build_qoi(
    mesh: UnstructuredMesh,
    velocity_u: dict[int, float],
    effective_viscosity: dict[int, float],
    turbulent_viscosity: dict[int, float],
    history: list[dict[str, Any]],
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    driving_source: float,
    closure: dict[str, Any],
    linear_system: dict[str, Any],
) -> dict[str, Any]:
    bounds = _mesh_bounds(mesh)
    length = bounds["xmax"] - bounds["xmin"]
    height = bounds["ymax"] - bounds["ymin"]
    total_measure = 0.0
    weighted_u = 0.0
    weighted_u2 = 0.0
    weighted_wall_error = 0.0
    for cell in mesh.cells:
        measure = abs(mesh.cell_signed_measure(cell))
        u_cell = sum(velocity_u[tag] for tag in cell.node_tags) / len(cell.node_tags)
        weighted_u += u_cell * measure
        weighted_u2 += u_cell * u_cell * measure
        total_measure += measure
    average_velocity = weighted_u / total_measure if total_measure > 0 else 0.0
    rms_velocity = sqrt(weighted_u2 / total_measure) if total_measure > 0 else 0.0
    hydraulic_diameter = 2.0 * height
    reynolds_bulk = density * abs(average_velocity) * hydraulic_diameter / molecular_viscosity
    ratios = [turbulent_viscosity[index] / molecular_viscosity for index in turbulent_viscosity]
    max_ratio = max(ratios) if ratios else 0.0
    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    streamwise_gradient = _cell_streamwise_u_gradient(mesh, velocity_u)
    for element in mesh.boundary_elements:
        if element.primary_physical_name == "wall":
            for tag in element.node_tags:
                weighted_wall_error = max(weighted_wall_error, abs(velocity_u[tag]))
    final = history[-1] if history else {}
    blocking_errors = []
    if not linear_system.get("converged", False):
        blocking_errors.append("Final turbulent-channel linear system did not converge.")
    if max_ratio <= 1.0e-8:
        blocking_errors.append("Turbulent viscosity was not activated; the benchmark did not exercise the turbulence closure.")
    if weighted_wall_error > 1.0e-8:
        blocking_errors.append(f"No-slip wall velocity check failed: {weighted_wall_error}.")
    if final.get("velocity_update_l2", 1.0) > 1.0e-2:
        blocking_errors.append(f"Velocity update did not settle below benchmark tolerance: {final.get('velocity_update_l2')}.")
    hints = [
        {
            "category": "turbulence_model",
            "recommendation": "Use this result as a low-cost algebraic eddy-viscosity benchmark before selecting Fluent RANS settings.",
            "evidence": [f"closure={closure['model']}", f"max_mu_t_over_mu={max_ratio}", f"Re_bulk={reynolds_bulk}"],
        },
        {
            "category": "near_wall_mesh",
            "recommendation": "Retain explicit wall patches and refine near-wall cells before production RANS validation.",
            "evidence": [f"wall_no_slip_abs_max={weighted_wall_error}", f"hydraulic_diameter={hydraulic_diameter}"],
        },
        {
            "category": "solver_initialization",
            "recommendation": "Initialize Fluent turbulence with conservative relaxation and monitor turbulent viscosity ratio.",
            "evidence": [f"final_velocity_update_l2={final.get('velocity_update_l2')}", f"iterations={len(history)}"],
        },
    ]
    return {
        "schema_version": TURBULENT_CHANNEL_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "algebraic_eddy_viscosity_turbulent_channel",
        "status": "passed" if not blocking_errors else "failed",
        "closure_model": closure,
        "density": density,
        "molecular_viscosity": molecular_viscosity,
        "pressure_drop": pressure_drop,
        "driving_source": driving_source,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "domain": {"length": length, "height": height, "hydraulic_diameter": hydraulic_diameter},
        "linear_system": _compact_linear_system(linear_system),
        "metrics": {
            "average_velocity": average_velocity,
            "max_velocity": max(velocity_u.values()) if velocity_u else 0.0,
            "rms_velocity": rms_velocity,
            "bulk_reynolds_number": reynolds_bulk,
            "max_turbulent_viscosity_ratio": max_ratio,
            "mean_turbulent_viscosity_ratio": mean_ratio,
            "min_effective_viscosity": min(effective_viscosity.values()) if effective_viscosity else None,
            "max_effective_viscosity": max(effective_viscosity.values()) if effective_viscosity else None,
            "final_velocity_update_l2": final.get("velocity_update_l2"),
            "final_effective_viscosity_update_l2": final.get("effective_viscosity_update_l2"),
            "final_linear_residual_l2": final.get("linear_final_residual_l2"),
            "streamwise_u_gradient_l2": _cell_metric_l2(mesh, streamwise_gradient),
            "wall_no_slip_abs_max": weighted_wall_error,
        },
        "iteration_count": len(history),
        "acceptance": {
            "linear_system_converged": linear_system.get("converged", False),
            "turbulent_viscosity_activated": max_ratio > 1.0e-8,
            "wall_no_slip_preserved": weighted_wall_error <= 1.0e-8,
            "velocity_update_settled": final.get("velocity_update_l2", 1.0) <= 1.0e-2,
        },
        "fluent_setup_hints": hints,
        "blocking_errors": blocking_errors,
        "limitations": [
            "This is a zero-equation algebraic eddy-viscosity turbulent channel benchmark.",
            "It solves an iterative effective-viscosity momentum problem, but it is not a production k-epsilon, SST, DES, LES, or Fluent replacement solver.",
            "Only the streamwise momentum component is solved; streamwise velocity gradients are diagnostic and are not a full incompressible continuity proof.",
            "The benchmark is intended to keep turbulence solving present in the agent stack while preserving clear validation boundaries.",
        ],
    }


def _compact_linear_system(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "storage": payload.get("storage"),
        "method": payload.get("method"),
        "n_rows": payload.get("n_rows"),
        "n_cols": payload.get("n_cols"),
        "nnz": payload.get("nnz"),
        "converged": payload.get("converged"),
        "iterations": payload.get("iterations"),
        "tolerance": payload.get("tolerance"),
        "final_residual_l2": payload.get("final_residual_l2"),
        "constrained_node_count": payload.get("constrained_node_count"),
    }


def _cell_streamwise_u_gradient(mesh: UnstructuredMesh, u_values: dict[int, float]) -> dict[int, float]:
    u_gradients = node_scalar_cell_gradients(mesh, u_values)
    return {cell_index: u_gradients[cell_index][0] for cell_index in u_gradients}


def _cell_metric_l2(mesh: UnstructuredMesh, values: dict[int, float]) -> float:
    total = 0.0
    weighted = 0.0
    for index, cell in enumerate(mesh.cells):
        measure = abs(mesh.cell_signed_measure(cell))
        weighted += values[index] * values[index] * measure
        total += measure
    return sqrt(weighted / total) if total > 0 else 0.0


def _cell_field_to_node_field(mesh: UnstructuredMesh, values: dict[int, float]) -> dict[int, float]:
    sums = {tag: 0.0 for tag in mesh.nodes}
    counts = {tag: 0 for tag in mesh.nodes}
    for index, cell in enumerate(mesh.cells):
        value = values[index]
        for tag in cell.node_tags:
            sums[tag] += value
            counts[tag] += 1
    return {tag: sums[tag] / counts[tag] if counts[tag] else 0.0 for tag in mesh.nodes}


def _node_l2_delta(current: dict[int, float], previous: dict[int, float]) -> float:
    return sqrt(sum((current[tag] - previous[tag]) ** 2 for tag in current) / max(1, len(current)))


def _cell_l2_delta(current: dict[int, float], previous: dict[int, float]) -> float:
    return sqrt(sum((current[index] - previous[index]) ** 2 for index in current) / max(1, len(current)))


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


def _turbulent_boundary_conditions() -> dict[str, BoundaryCondition]:
    return {
        "inlet": BoundaryCondition(patch="inlet", kind="velocity_profile_dirichlet", role="benchmark inlet profile"),
        "outlet": BoundaryCondition(patch="outlet", kind="velocity_profile_dirichlet", role="fully developed outlet profile"),
        "wall": BoundaryCondition(patch="wall", kind="no_slip_wall", role="top and bottom no-slip walls"),
    }


def _validate_inputs(
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    iterations: int,
    relaxation: float,
    kappa: float,
    max_mixing_length_fraction: float,
    turbulent_viscosity_cap_ratio: float,
) -> None:
    if density <= 0:
        raise ValueError("Turbulent channel density must be positive.")
    if molecular_viscosity <= 0:
        raise ValueError("Turbulent channel molecular_viscosity must be positive.")
    if pressure_drop <= 0:
        raise ValueError("Turbulent channel pressure_drop must be positive.")
    if iterations < 2:
        raise ValueError("Turbulent channel iterations must be at least 2.")
    if not (0.0 < relaxation <= 1.0):
        raise ValueError("Turbulent channel relaxation must be in the interval (0, 1].")
    if kappa <= 0:
        raise ValueError("Turbulent channel kappa must be positive.")
    if not (0.0 < max_mixing_length_fraction <= 0.5):
        raise ValueError("Turbulent channel max_mixing_length_fraction must be in (0, 0.5].")
    if turbulent_viscosity_cap_ratio <= 0:
        raise ValueError("Turbulent channel turbulent_viscosity_cap_ratio must be positive.")


def _mesh_bounds(mesh: UnstructuredMesh) -> dict[str, float]:
    xs = [node.x for node in mesh.nodes.values()]
    ys = [node.y for node in mesh.nodes.values()]
    zs = [node.z for node in mesh.nodes.values()]
    return {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys), "zmin": min(zs), "zmax": max(zs)}


def _require_triangles(mesh: UnstructuredMesh) -> None:
    unsupported = sorted({cell.kind for cell in mesh.cells if cell.kind != "triangle"})
    if unsupported:
        raise ValueError(f"Turbulent channel currently supports triangle cells only; unsupported cells: {unsupported}.")


def _write_iteration_history(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "iteration",
                "velocity_update_l2",
                "effective_viscosity_update_l2",
                "max_turbulent_viscosity_ratio",
                "mean_turbulent_viscosity_ratio",
                "linear_iterations",
                "linear_final_residual_l2",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _turbulent_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    return "\n".join(
        [
            "# FastFluent Algebraic Eddy-Viscosity Turbulent Channel",
            "",
            f"Status: `{qoi['status']}`",
            f"Closure: `{qoi['closure_model']['model']}`",
            f"Iterations: `{qoi['iteration_count']}`",
            "",
            "## Metrics",
            "",
            f"- Bulk Reynolds number: `{metrics['bulk_reynolds_number']}`",
            f"- Average velocity: `{metrics['average_velocity']}`",
            f"- Max turbulent viscosity ratio: `{metrics['max_turbulent_viscosity_ratio']}`",
            f"- Final velocity update L2: `{metrics['final_velocity_update_l2']}`",
            f"- Final linear residual L2: `{metrics['final_linear_residual_l2']}`",
            "",
            "## Scope",
            "",
            "This is a real iterative algebraic eddy-viscosity benchmark. It is not a production Fluent turbulence solver.",
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
