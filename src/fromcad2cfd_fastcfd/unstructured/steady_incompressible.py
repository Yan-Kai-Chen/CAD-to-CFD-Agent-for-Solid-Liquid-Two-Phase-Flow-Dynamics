"""Controlled steady incompressible unstructured-flow case route."""

from __future__ import annotations

import csv
import json
from math import sqrt
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .boundary import BoundaryCondition, validate_boundary_contract
from .flow import _cell_divergence, _cell_metric_l2, _recover_node_gradients
from .geometry import FVGeometry, build_fv_geometry
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .linear import SparseMatrixCSR, solve_linear_system
from .mesh import MeshElement, UnstructuredMesh, triangle_signed_area_xy
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .turbulent_channel import _apply_dirichlet_sparse_rows, _triangle_basis_gradients
from .vtu import write_mesh_vtu, write_vector_solution_vtu


STEADY_INCOMPRESSIBLE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_steady_incompressible_v1"

SOLVER_SUPPORTED_BOUNDARY_KINDS = {
    "velocity_inlet",
    "velocity_dirichlet",
    "pressure_outlet",
    "pressure_reference",
    "outflow",
    "no_slip_wall",
}


def run_steady_incompressible_case(
    mesh_file: str | Path,
    *,
    output_dir: str | Path | None = None,
    boundary_conditions: dict[str, BoundaryCondition] | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
    density: float = 1.0,
    viscosity: float = 1.0e-3,
    body_force: tuple[float, float] = (0.0, 0.0),
    iterations: int = 8,
    pressure_relaxation: float = 0.45,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
) -> dict[str, Any]:
    """Run a bounded steady incompressible pressure-correction route."""

    mesh_path = Path(mesh_file)
    target_dir = Path(output_dir) if output_dir else unique_path(mesh_path.parent / f"{mesh_path.stem}_steady_incompressible")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        _validate_inputs(density=density, viscosity=viscosity, iterations=iterations, pressure_relaxation=pressure_relaxation)
        conditions = boundary_conditions or _default_boundary_conditions()
        unsupported_for_solver = sorted({condition.kind for condition in conditions.values() if condition.kind not in SOLVER_SUPPORTED_BOUNDARY_KINDS})
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=())
        boundary_contract = validate_boundary_contract(mesh, required_patches=required_patches, boundary_conditions=conditions)
        artifacts: dict[str, str] = {
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
            "steady_boundary_contract": str(_write_json(target_dir / "steady_boundary_contract.json", boundary_contract)),
            "mesh_vtu": str(write_mesh_vtu(mesh, target_dir / "mesh.vtu")),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_steady_incompressible",
                message="Steady incompressible solve was blocked by mesh quality.",
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
            artifacts["steady_status"] = str(_write_json(target_dir / "steady_status.json", result.to_dict()))
            return result.to_dict()
        if boundary_contract["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_steady_incompressible",
                message="Steady incompressible solve was blocked by boundary-condition contract.",
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
            artifacts["steady_status"] = str(_write_json(target_dir / "steady_status.json", result.to_dict()))
            return result.to_dict()
        if unsupported_for_solver:
            errors = [f"Steady incompressible solver does not implement boundary kinds: {', '.join(unsupported_for_solver)}"]
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_steady_incompressible",
                message="Steady incompressible solve was blocked by unsupported solver boundary kinds.",
                errors=errors,
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "unsupported_solver_boundary_kinds": unsupported_for_solver,
                    "solver_execution": "blocked_by_solver_boundary_kind",
                }
            )
            artifacts["steady_status"] = str(_write_json(target_dir / "steady_status.json", result.to_dict()))
            return result.to_dict()
        _require_triangles(mesh)
        fv_geometry = build_fv_geometry(mesh)
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry.to_dict()))
        solution = solve_steady_incompressible(
            mesh,
            fv_geometry=fv_geometry,
            boundary_conditions=conditions,
            density=density,
            viscosity=viscosity,
            body_force=body_force,
            iterations=iterations,
            pressure_relaxation=pressure_relaxation,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["steady_linear_systems"] = str(_write_json(target_dir / "steady_linear_systems.json", solution["linear_systems"]))
        artifacts["steady_residual_history"] = str(_write_residual_history(target_dir / "steady_residual_history.csv", solution["residual_history"]))
        artifacts["steady_qoi"] = str(_write_json(target_dir / "steady_qoi.json", solution["qoi"]))
        artifacts["steady_solution_vtu"] = str(
            write_vector_solution_vtu(
                mesh,
                target_dir / "steady_solution.vtu",
                solution["velocity"],
                scalar_fields={
                    "pressure_correction": solution["pressure_correction"],
                    "cell_divergence_at_nodes": _cell_to_node_field(mesh, solution["cell_divergence"]),
                },
            )
        )
        artifacts["steady_report"] = str(_write_text(target_dir / "steady_report.md", _steady_markdown(solution["qoi"])))
        if solution["qoi"]["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_steady_incompressible",
                message="Steady incompressible solve completed but did not pass acceptance checks.",
                errors=solution["qoi"]["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "qoi": solution["qoi"],
                    "solver_execution": "steady_incompressible_failed_acceptance",
                }
            )
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="solve_steady_incompressible",
                message="Steady incompressible pressure-correction solve completed.",
                outputs={
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "fv_geometry": fv_geometry.to_dict(),
                    "qoi": solution["qoi"],
                    "solver_execution": "steady_incompressible_pressure_correction",
                },
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
        artifacts["steady_status"] = str(_write_json(target_dir / "steady_status.json", result.to_dict()))
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_steady_incompressible",
            message="Steady incompressible solve failed before completion.",
            errors=[str(exc)],
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"steady_status": str(target_dir / "steady_status.json")}
        _write_json(target_dir / "steady_status.json", failure.to_dict())
        return failure.to_dict()


def solve_steady_incompressible(
    mesh: UnstructuredMesh,
    *,
    fv_geometry: FVGeometry | None,
    boundary_conditions: dict[str, BoundaryCondition],
    density: float,
    viscosity: float,
    body_force: tuple[float, float],
    iterations: int,
    pressure_relaxation: float,
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    dirichlet = _velocity_dirichlet_values(mesh, boundary_conditions)
    if not dirichlet:
        raise ValueError("Steady incompressible solve requires at least one velocity Dirichlet boundary.")
    u_solution = _solve_velocity_component(
        mesh,
        component="u",
        viscosity=viscosity,
        source=density * body_force[0],
        constrained_values={tag: value[0] for tag, value in dirichlet.items()},
        linear_solver=linear_solver,
        linear_tolerance=linear_tolerance,
        max_linear_iterations=max_linear_iterations,
    )
    v_solution = _solve_velocity_component(
        mesh,
        component="v",
        viscosity=viscosity,
        source=density * body_force[1],
        constrained_values={tag: value[1] for tag, value in dirichlet.items()},
        linear_solver=linear_solver,
        linear_tolerance=linear_tolerance,
        max_linear_iterations=max_linear_iterations,
    )
    u_values = u_solution["values"]
    v_values = v_solution["values"]
    pressure_correction = {tag: 0.0 for tag in node_tags}
    residual_history: list[dict[str, Any]] = []
    initial_divergence_l2: float | None = None
    final_divergence = _cell_divergence(mesh, u_values, v_values)
    pressure_linear_system: dict[str, Any] = {}
    for iteration in range(1, iterations + 1):
        predicted = _cell_divergence(mesh, u_values, v_values)
        predicted_l2 = _cell_metric_l2(mesh, predicted)
        if initial_divergence_l2 is None:
            initial_divergence_l2 = predicted_l2
        pressure = _solve_pressure_correction_from_divergence(
            mesh,
            predicted,
            boundary_conditions=boundary_conditions,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        pressure_correction = pressure["values"]
        pressure_linear_system = pressure["linear_system"]
        gradients = _recover_node_gradients(mesh, pressure_correction)
        old_u = dict(u_values)
        old_v = dict(v_values)
        for tag in node_tags:
            u_values[tag] -= pressure_relaxation * gradients[tag][0] / density
            v_values[tag] -= pressure_relaxation * gradients[tag][1] / density
        _apply_velocity_constraints(u_values, v_values, dirichlet)
        corrected = _cell_divergence(mesh, u_values, v_values)
        corrected_l2 = _cell_metric_l2(mesh, corrected)
        final_divergence = corrected
        residual_history.append(
            {
                "iteration": iteration,
                "predicted_divergence_l2": predicted_l2,
                "corrected_divergence_l2": corrected_l2,
                "divergence_reduction_ratio": corrected_l2 / predicted_l2 if predicted_l2 > 0 else 0.0,
                "pressure_residual_l2": pressure_linear_system.get("final_residual_l2"),
                "linear_iterations": pressure_linear_system.get("iterations"),
                "velocity_update_l2": _velocity_delta_l2(u_values, v_values, old_u, old_v),
            }
        )
    velocity = {tag: (u_values[tag], v_values[tag], 0.0) for tag in node_tags}
    fv = fv_geometry or build_fv_geometry(mesh)
    mass_flux = _boundary_mass_flux(mesh, fv, velocity, density=density)
    boundary_error = _velocity_boundary_error(mesh, velocity, dirichlet)
    qoi = _build_qoi(
        mesh,
        velocity,
        final_divergence,
        residual_history,
        mass_flux,
        boundary_error,
        density=density,
        viscosity=viscosity,
        body_force=body_force,
        iterations=iterations,
        pressure_relaxation=pressure_relaxation,
        linear_systems={"u": u_solution["linear_system"], "v": v_solution["linear_system"], "pressure_correction": pressure_linear_system},
        initial_divergence_l2=initial_divergence_l2 or 0.0,
    )
    return {
        "velocity": velocity,
        "pressure_correction": pressure_correction,
        "cell_divergence": final_divergence,
        "mass_flux": mass_flux,
        "linear_systems": {
            "u": u_solution["linear_system"],
            "v": v_solution["linear_system"],
            "pressure_correction": pressure_linear_system,
        },
        "residual_history": residual_history,
        "qoi": qoi,
    }


def _solve_velocity_component(
    mesh: UnstructuredMesh,
    *,
    component: str,
    viscosity: float,
    source: float,
    constrained_values: dict[int, float],
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    rows: list[dict[int, float]] = [dict() for _ in node_tags]
    rhs = [0.0 for _ in node_tags]
    for cell in mesh.cells:
        _assemble_triangle(rows, rhs, mesh, cell, node_index, source, viscosity)
    _apply_dirichlet_sparse_rows(rows, rhs, node_index, constrained_values)
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
            "Steady incompressible velocity solve did not converge: "
            f"component={component}, method={solve_result.method}, iterations={solve_result.iterations}, "
            f"final_residual_l2={solve_result.final_residual_l2}."
        )
    values = {tag: solve_result.values[node_index[tag]] for tag in node_tags}
    metadata = solve_result.metadata(matrix)
    metadata.update(
        {
            "component": component,
            "assembly": "p1_triangle_steady_incompressible_velocity_component",
            "boundary_condition": "json_case_velocity_dirichlet_subset",
            "constrained_node_count": len(constrained_values),
            "rhs_l2": sqrt(sum(value * value for value in rhs)),
        }
    )
    return {"values": values, "linear_system": metadata}


def _solve_pressure_correction_from_divergence(
    mesh: UnstructuredMesh,
    divergence: dict[int, float],
    *,
    boundary_conditions: dict[str, BoundaryCondition],
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    rows: list[dict[int, float]] = [dict() for _ in node_tags]
    rhs = [0.0 for _ in node_tags]
    for cell_index, cell in enumerate(mesh.cells):
        _assemble_pressure_triangle(rows, rhs, mesh, cell, node_index, -divergence[cell_index])
    constrained = _pressure_reference_nodes(mesh, boundary_conditions)
    if not constrained:
        constrained = {node_tags[0]: 0.0}
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
            "Steady incompressible pressure-correction solve did not converge: "
            f"method={solve_result.method}, iterations={solve_result.iterations}, "
            f"final_residual_l2={solve_result.final_residual_l2}."
        )
    metadata = solve_result.metadata(matrix)
    metadata.update(
        {
            "assembly": "p1_triangle_steady_pressure_correction",
            "boundary_condition": "pressure_reference_patches_with_natural_other_boundaries",
            "constrained_node_count": len(constrained),
            "rhs_l2": sqrt(sum(value * value for value in rhs)),
        }
    )
    return {"values": {tag: solve_result.values[node_index[tag]] for tag in node_tags}, "linear_system": metadata}


def _assemble_pressure_triangle(
    rows: list[dict[int, float]],
    rhs: list[float],
    mesh: UnstructuredMesh,
    cell: MeshElement,
    node_index: dict[int, int],
    source: float,
) -> None:
    if cell.kind != "triangle":
        raise ValueError(f"Steady pressure correction currently supports triangle cells only, got {cell.kind}.")
    points = [mesh.nodes[tag].to_tuple() for tag in cell.node_tags]
    area = abs(triangle_signed_area_xy(points[0], points[1], points[2]))
    if area <= 0:
        raise ValueError(f"Cannot assemble pressure correction for non-positive triangle area in element {cell.tag}.")
    gradients = _triangle_basis_gradients(points, area)
    for local_i, tag_i in enumerate(cell.node_tags):
        global_i = node_index[tag_i]
        rhs[global_i] += source * area / 3.0
        for local_j, tag_j in enumerate(cell.node_tags):
            global_j = node_index[tag_j]
            rows[global_i][global_j] = rows[global_i].get(global_j, 0.0) + area * (
                gradients[local_i][0] * gradients[local_j][0] + gradients[local_i][1] * gradients[local_j][1]
            )


def _pressure_reference_nodes(mesh: UnstructuredMesh, conditions: dict[str, BoundaryCondition]) -> dict[int, float]:
    constrained: dict[int, float] = {}
    for element in mesh.boundary_elements:
        patch = element.primary_physical_name or "unassigned"
        condition = conditions.get(patch)
        if not condition or condition.kind not in {"pressure_reference", "pressure_outlet"}:
            continue
        pressure = float((condition.parameters or {}).get("pressure", 0.0))
        for tag in element.node_tags:
            constrained[tag] = pressure
    return constrained


def _assemble_triangle(
    rows: list[dict[int, float]],
    rhs: list[float],
    mesh: UnstructuredMesh,
    cell: MeshElement,
    node_index: dict[int, int],
    source: float,
    viscosity: float,
) -> None:
    if cell.kind != "triangle":
        raise ValueError(f"Steady incompressible solve currently supports triangle cells only, got {cell.kind}.")
    points = [mesh.nodes[tag].to_tuple() for tag in cell.node_tags]
    area = abs(triangle_signed_area_xy(points[0], points[1], points[2]))
    if area <= 0:
        raise ValueError(f"Cannot assemble steady incompressible solve for non-positive triangle area in element {cell.tag}.")
    gradients = _triangle_basis_gradients(points, area)
    for local_i, tag_i in enumerate(cell.node_tags):
        global_i = node_index[tag_i]
        rhs[global_i] += source * area / 3.0
        for local_j, tag_j in enumerate(cell.node_tags):
            global_j = node_index[tag_j]
            rows[global_i][global_j] = rows[global_i].get(global_j, 0.0) + viscosity * area * (
                gradients[local_i][0] * gradients[local_j][0] + gradients[local_i][1] * gradients[local_j][1]
            )


def _velocity_dirichlet_values(mesh: UnstructuredMesh, conditions: dict[str, BoundaryCondition]) -> dict[int, tuple[float, float]]:
    patch_for_node: dict[int, set[str]] = {}
    for element in mesh.boundary_elements:
        patch = element.primary_physical_name or "unassigned"
        for tag in element.node_tags:
            patch_for_node.setdefault(tag, set()).add(patch)
    values: dict[int, tuple[float, float]] = {}
    for tag, patches in patch_for_node.items():
        if any(conditions.get(patch) and conditions[patch].kind == "no_slip_wall" for patch in patches):
            values[tag] = (0.0, 0.0)
            continue
        for patch in sorted(patches):
            condition = conditions.get(patch)
            if not condition or condition.kind not in {"velocity_inlet", "velocity_dirichlet"}:
                continue
            vector = (condition.parameters or {}).get("velocity", (0.0, 0.0))
            values[tag] = (float(vector[0]), float(vector[1]))
            break
    return values


def _apply_velocity_constraints(
    u_values: dict[int, float],
    v_values: dict[int, float],
    dirichlet: dict[int, tuple[float, float]],
) -> None:
    for tag, value in dirichlet.items():
        u_values[tag] = value[0]
        v_values[tag] = value[1]


def _boundary_mass_flux(mesh: UnstructuredMesh, fv_geometry: FVGeometry, velocity: dict[int, tuple[float, float, float]], *, density: float) -> dict[str, Any]:
    by_patch: dict[str, float] = {}
    for face in fv_geometry.faces:
        if not face.is_boundary:
            continue
        patch = face.patch_name or "unassigned"
        count = len(face.node_tags)
        average = (
            sum(velocity[tag][0] for tag in face.node_tags) / count,
            sum(velocity[tag][1] for tag in face.node_tags) / count,
            0.0,
        )
        flux = density * (
            average[0] * face.area_vector[0]
            + average[1] * face.area_vector[1]
            + average[2] * face.area_vector[2]
        )
        by_patch[patch] = by_patch.get(patch, 0.0) + flux
    positive_outflow = sum(value for value in by_patch.values() if value > 0.0)
    negative_inflow = -sum(value for value in by_patch.values() if value < 0.0)
    net = sum(by_patch.values())
    reference = max(positive_outflow, negative_inflow, 1.0e-30)
    return {
        "by_patch": dict(sorted(by_patch.items())),
        "positive_outflow": positive_outflow,
        "negative_inflow": negative_inflow,
        "net_flux": net,
        "relative_imbalance": abs(net) / reference,
    }


def _velocity_boundary_error(
    mesh: UnstructuredMesh,
    velocity: dict[int, tuple[float, float, float]],
    dirichlet: dict[int, tuple[float, float]],
) -> float:
    return max(
        (
            sqrt((velocity[tag][0] - value[0]) ** 2 + (velocity[tag][1] - value[1]) ** 2)
            for tag, value in dirichlet.items()
        ),
        default=0.0,
    )


def _velocity_delta_l2(
    u_values: dict[int, float],
    v_values: dict[int, float],
    old_u: dict[int, float],
    old_v: dict[int, float],
) -> float:
    return sqrt(
        sum((u_values[tag] - old_u[tag]) ** 2 + (v_values[tag] - old_v[tag]) ** 2 for tag in u_values) / max(1, len(u_values))
    )


def _build_qoi(
    mesh: UnstructuredMesh,
    velocity: dict[int, tuple[float, float, float]],
    cell_divergence: dict[int, float],
    residual_history: list[dict[str, Any]],
    mass_flux: dict[str, Any],
    boundary_error: float,
    *,
    density: float,
    viscosity: float,
    body_force: tuple[float, float],
    iterations: int,
    pressure_relaxation: float,
    linear_systems: dict[str, dict[str, Any]],
    initial_divergence_l2: float,
) -> dict[str, Any]:
    final_divergence_l2 = _cell_metric_l2(mesh, cell_divergence)
    speeds = [sqrt(value[0] * value[0] + value[1] * value[1]) for value in velocity.values()]
    max_speed = max(speeds) if speeds else 0.0
    mean_speed = sum(speeds) / len(speeds) if speeds else 0.0
    systems_converged = all(payload.get("converged", False) for payload in linear_systems.values())
    final = residual_history[-1] if residual_history else {}
    blocking_errors = []
    if not systems_converged:
        blocking_errors.append("At least one steady incompressible linear system did not converge.")
    if boundary_error > 1.0e-8:
        blocking_errors.append(f"Velocity Dirichlet boundary was not preserved: {boundary_error}.")
    if final_divergence_l2 > max(5.0e-1, 1.25 * initial_divergence_l2):
        blocking_errors.append(f"Final divergence is outside the controlled benchmark tolerance: {final_divergence_l2}.")
    if mass_flux["relative_imbalance"] > 0.75:
        blocking_errors.append(f"Mass-flux imbalance is outside the controlled benchmark tolerance: {mass_flux['relative_imbalance']}.")
    return {
        "schema_version": STEADY_INCOMPRESSIBLE_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "steady_incompressible_pressure_correction",
        "status": "passed" if not blocking_errors else "failed",
        "density": density,
        "viscosity": viscosity,
        "body_force": list(body_force),
        "iterations": iterations,
        "pressure_relaxation": pressure_relaxation,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "linear_systems": {name: _compact_linear_system(payload) for name, payload in linear_systems.items()},
        "metrics": {
            "mean_speed": mean_speed,
            "max_speed": max_speed,
            "initial_divergence_l2": initial_divergence_l2,
            "final_divergence_l2": final_divergence_l2,
            "final_divergence_ratio": final_divergence_l2 / initial_divergence_l2 if initial_divergence_l2 > 0 else 0.0,
            "final_velocity_update_l2": final.get("velocity_update_l2"),
            "velocity_boundary_error": boundary_error,
            "mass_flux": mass_flux,
        },
        "acceptance": {
            "linear_systems_converged": systems_converged,
            "velocity_boundary_preserved": boundary_error <= 1.0e-8,
            "divergence_within_controlled_tolerance": final_divergence_l2 <= max(5.0e-1, 1.25 * initial_divergence_l2),
            "mass_flux_imbalance_within_controlled_tolerance": mass_flux["relative_imbalance"] <= 0.75,
        },
        "fluent_setup_hints": [
            {
                "category": "boundary_conditions",
                "recommendation": "Check that named inlet, outlet, and wall patches preserve the intended engineering boundary roles before Fluent setup.",
                "evidence": [f"mass_flux_relative_imbalance={mass_flux['relative_imbalance']}", f"boundary_error={boundary_error}"],
            },
            {
                "category": "solver_initialization",
                "recommendation": "Use conservative pressure-velocity coupling controls and monitor continuity residuals for the corresponding Fluent case.",
                "evidence": [
                    f"initial_divergence_l2={initial_divergence_l2}",
                    f"final_divergence_l2={final_divergence_l2}",
                    f"pressure_relaxation={pressure_relaxation}",
                ],
            },
        ],
        "blocking_errors": blocking_errors,
        "limitations": [
            "This is a controlled steady incompressible pressure-correction route for public unstructured cases.",
            "It is not a production arbitrary-geometry SIMPLE/PISO solver and does not replace Fluent validation.",
            "Mass-flux and divergence checks are acceptance evidence for this bounded route, not a universal CFD validation proof.",
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


def _cell_to_node_field(mesh: UnstructuredMesh, cell_values: dict[int, float]) -> dict[int, float]:
    sums = {tag: 0.0 for tag in mesh.nodes}
    counts = {tag: 0 for tag in mesh.nodes}
    for index, cell in enumerate(mesh.cells):
        for tag in cell.node_tags:
            sums[tag] += cell_values[index]
            counts[tag] += 1
    return {tag: sums[tag] / counts[tag] if counts[tag] else 0.0 for tag in mesh.nodes}


def _default_boundary_conditions() -> dict[str, BoundaryCondition]:
    return {
        "inlet": BoundaryCondition(
            patch="inlet",
            kind="velocity_inlet",
            role="controlled uniform inlet",
            parameters={"velocity": [1.0, 0.0]},
        ),
        "outlet": BoundaryCondition(
            patch="outlet",
            kind="pressure_outlet",
            role="controlled pressure outlet",
            parameters={"pressure": 0.0},
        ),
        "wall": BoundaryCondition(patch="wall", kind="no_slip_wall", role="controlled no-slip wall"),
    }


def _require_triangles(mesh: UnstructuredMesh) -> None:
    unsupported = sorted({cell.kind for cell in mesh.cells if cell.kind != "triangle"})
    if unsupported:
        raise ValueError(f"Steady incompressible solve currently supports triangle cells only; unsupported cells: {unsupported}.")


def _validate_inputs(*, density: float, viscosity: float, iterations: int, pressure_relaxation: float) -> None:
    if density <= 0:
        raise ValueError("Steady incompressible density must be positive.")
    if viscosity <= 0:
        raise ValueError("Steady incompressible viscosity must be positive.")
    if iterations < 1:
        raise ValueError("Steady incompressible iterations must be at least 1.")
    if not (0.0 < pressure_relaxation <= 1.0):
        raise ValueError("Steady incompressible pressure_relaxation must be in (0, 1].")


def _write_residual_history(path: Path, rows: list[dict[str, Any]]) -> Path:
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


def _steady_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    return "\n".join(
        [
            "# FastFluent Steady Incompressible Case",
            "",
            f"Status: `{qoi['status']}`",
            f"Solver: `{qoi['solver_family']}`",
            f"Iterations: `{qoi['iterations']}`",
            "",
            "## Metrics",
            "",
            f"- Mean speed: `{metrics['mean_speed']}`",
            f"- Max speed: `{metrics['max_speed']}`",
            f"- Initial divergence L2: `{metrics['initial_divergence_l2']}`",
            f"- Final divergence L2: `{metrics['final_divergence_l2']}`",
            f"- Mass-flux relative imbalance: `{metrics['mass_flux']['relative_imbalance']}`",
            f"- Velocity boundary error: `{metrics['velocity_boundary_error']}`",
            "",
            "## Scope",
            "",
            "This is a controlled steady incompressible route for public unstructured cases. It is not a production Fluent replacement.",
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
