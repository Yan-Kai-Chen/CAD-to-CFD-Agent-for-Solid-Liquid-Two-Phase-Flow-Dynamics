"""Bounded k-epsilon turbulent channel benchmark."""

from __future__ import annotations

import csv
import json
from math import isfinite, sqrt
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .boundary import BoundaryCondition, validate_boundary_contract
from .channel_validation import write_unit_square_channel_mesh
from .geometry import build_fv_geometry, node_scalar_cell_gradients
from .flow import (
    _cell_divergence as _velocity_cell_divergence,
    _cell_metric_l2 as _flow_cell_metric_l2,
    _recover_node_gradients,
    _solve_pressure_correction_from_divergence,
)
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .linear import SparseMatrixCSR, solve_linear_system
from .mesh import MeshElement, UnstructuredMesh, triangle_signed_area_xy
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .turbulent_channel import (
    _apply_dirichlet_sparse_rows,
    _cell_field_to_node_field,
    _cell_l2_delta,
    _mesh_bounds,
    _node_l2_delta,
    _require_triangles,
    _solve_variable_viscosity_u,
    _triangle_basis_gradients,
)
from .vtu import write_mesh_vtu, write_vector_solution_vtu


KEPSILON_CHANNEL_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_kepsilon_channel_v1"
PRESSURE_KEPSILON_CHANNEL_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_pressure_kepsilon_channel_v1"


def run_kepsilon_channel_case(
    mesh_file: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    density: float = 1.0,
    molecular_viscosity: float = 1.0e-3,
    pressure_drop: float = 0.05,
    iterations: int = 12,
    relaxation: float = 0.45,
    c_mu: float = 0.09,
    c_epsilon_1: float = 1.44,
    c_epsilon_2: float = 1.92,
    sigma_k: float = 1.0,
    sigma_epsilon: float = 1.3,
    turbulence_intensity: float = 0.05,
    turbulent_length_scale_fraction: float = 0.07,
    turbulent_viscosity_cap_ratio: float = 1000.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Run a controlled two-equation k-epsilon channel benchmark."""

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "unstructured_kepsilon_channel" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        _validate_inputs(
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            relaxation=relaxation,
            c_mu=c_mu,
            c_epsilon_1=c_epsilon_1,
            c_epsilon_2=c_epsilon_2,
            sigma_k=sigma_k,
            sigma_epsilon=sigma_epsilon,
            turbulence_intensity=turbulence_intensity,
            turbulent_length_scale_fraction=turbulent_length_scale_fraction,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
        )
        mesh_path = Path(mesh_file) if mesh_file else write_unit_square_channel_mesh(target_dir / "public_kepsilon_channel.msh", nx=10, ny=10)
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=())
        boundary_contract = validate_boundary_contract(
            mesh,
            required_patches=required_patches,
            boundary_conditions=_pressure_kepsilon_boundary_conditions(),
        )
        artifacts: dict[str, str] = {
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
            "kepsilon_boundary_contract": str(_write_json(target_dir / "kepsilon_boundary_contract.json", boundary_contract)),
            "mesh_vtu": str(write_mesh_vtu(mesh, target_dir / "mesh.vtu")),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_kepsilon_channel",
                message="k-epsilon channel solve was blocked by mesh quality.",
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
            artifacts["kepsilon_status"] = str(_write_json(target_dir / "kepsilon_status.json", result.to_dict()))
            return result.to_dict()
        if boundary_contract["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_kepsilon_channel",
                message="k-epsilon channel solve was blocked by boundary-condition contract.",
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
            artifacts["kepsilon_status"] = str(_write_json(target_dir / "kepsilon_status.json", result.to_dict()))
            return result.to_dict()
        _require_triangles(mesh)
        fv_geometry = build_fv_geometry(mesh)
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry.to_dict()))
        solution = solve_kepsilon_channel(
            mesh,
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            relaxation=relaxation,
            c_mu=c_mu,
            c_epsilon_1=c_epsilon_1,
            c_epsilon_2=c_epsilon_2,
            sigma_k=sigma_k,
            sigma_epsilon=sigma_epsilon,
            turbulence_intensity=turbulence_intensity,
            turbulent_length_scale_fraction=turbulent_length_scale_fraction,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["kepsilon_qoi"] = str(_write_json(target_dir / "kepsilon_qoi.json", solution["qoi"]))
        artifacts["kepsilon_iterations"] = str(_write_iteration_history(target_dir / "kepsilon_iterations.csv", solution["iteration_history"]))
        artifacts["kepsilon_solution_vtu"] = str(
            write_vector_solution_vtu(
                mesh,
                target_dir / "kepsilon_solution.vtu",
                solution["velocity"],
                scalar_fields={
                    "turbulent_kinetic_energy": solution["node_k"],
                    "epsilon": solution["node_epsilon"],
                    "turbulent_viscosity_ratio": solution["node_turbulent_viscosity_ratio"],
                    "effective_viscosity": solution["node_effective_viscosity"],
                    "production": solution["node_production"],
                },
            )
        )
        artifacts["kepsilon_report"] = str(_write_text(target_dir / "kepsilon_report.md", _kepsilon_markdown(solution["qoi"])))
        if solution["qoi"]["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_kepsilon_channel",
                message="k-epsilon channel solve completed but did not pass acceptance checks.",
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
                    "solver_execution": "kepsilon_turbulent_channel_failed_acceptance",
                }
            )
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="solve_kepsilon_channel",
                message="Two-equation k-epsilon turbulent channel benchmark completed.",
                outputs={
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "fv_geometry": fv_geometry.to_dict(),
                    "qoi": solution["qoi"],
                    "solver_execution": "kepsilon_turbulent_channel",
                },
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
        artifacts["kepsilon_status"] = str(_write_json(target_dir / "kepsilon_status.json", result.to_dict()))
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_kepsilon_channel",
            message="k-epsilon channel solve failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"kepsilon_status": str(target_dir / "kepsilon_status.json")}
        _write_json(target_dir / "kepsilon_status.json", failure.to_dict())
        return failure.to_dict()


def solve_kepsilon_channel(
    mesh: UnstructuredMesh,
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    iterations: int,
    relaxation: float,
    c_mu: float,
    c_epsilon_1: float,
    c_epsilon_2: float,
    sigma_k: float,
    sigma_epsilon: float,
    turbulence_intensity: float,
    turbulent_length_scale_fraction: float,
    turbulent_viscosity_cap_ratio: float,
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
) -> dict[str, Any]:
    bounds = _mesh_bounds(mesh)
    length = bounds["xmax"] - bounds["xmin"]
    height = bounds["ymax"] - bounds["ymin"]
    if length <= 0 or height <= 0:
        raise ValueError("k-epsilon channel requires positive length and height.")
    driving_source = pressure_drop / length
    node_tags = sorted(mesh.nodes)
    cell_count = len(mesh.cells)
    reference_velocity = max(
        1.0e-9,
        max(
            _laminar_profile(mesh.nodes[tag].y, bounds, driving_source=driving_source, viscosity=molecular_viscosity)
            for tag in node_tags
        ),
    )
    length_scale = max(1.0e-9, turbulent_length_scale_fraction * height)
    k_floor = 1.0e-10 * reference_velocity * reference_velocity
    epsilon_floor = 1.0e-12 * reference_velocity * reference_velocity * reference_velocity / length_scale
    k_inlet = max(k_floor, 1.5 * (reference_velocity * turbulence_intensity) ** 2)
    epsilon_inlet = max(epsilon_floor, (c_mu**0.75) * (k_inlet**1.5) / length_scale)
    velocity_u = {tag: _laminar_profile(mesh.nodes[tag].y, bounds, driving_source=driving_source, viscosity=molecular_viscosity) for tag in node_tags}
    k_values = {tag: _interior_seed(mesh.nodes[tag].y, bounds, k_floor, k_inlet) for tag in node_tags}
    epsilon_values = {tag: _interior_seed(mesh.nodes[tag].y, bounds, epsilon_floor, epsilon_inlet) for tag in node_tags}
    turbulent_viscosity = {index: molecular_viscosity * 0.1 for index in range(cell_count)}
    effective_viscosity = {index: molecular_viscosity + turbulent_viscosity[index] for index in range(cell_count)}
    production = {index: 0.0 for index in range(cell_count)}
    history: list[dict[str, Any]] = []
    linear_systems: dict[str, Any] = {}
    for iteration in range(1, iterations + 1):
        old_u = dict(velocity_u)
        old_k = dict(k_values)
        old_epsilon = dict(epsilon_values)
        old_effective = dict(effective_viscosity)
        cell_k = _node_to_cell_average(mesh, k_values)
        cell_epsilon = _node_to_cell_average(mesh, epsilon_values)
        turbulent_viscosity = _compute_kepsilon_turbulent_viscosity(
            cell_k,
            cell_epsilon,
            density=density,
            molecular_viscosity=molecular_viscosity,
            c_mu=c_mu,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
        )
        raw_effective = {index: molecular_viscosity + turbulent_viscosity[index] for index in range(cell_count)}
        effective_viscosity = {
            index: (1.0 - relaxation) * old_effective[index] + relaxation * raw_effective[index] for index in range(cell_count)
        }
        momentum = _solve_variable_viscosity_u(
            mesh,
            effective_viscosity=effective_viscosity,
            driving_source=driving_source,
            bounds=bounds,
            molecular_viscosity=molecular_viscosity,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        raw_u = momentum["values"]
        velocity_u = {tag: (1.0 - relaxation) * old_u[tag] + relaxation * raw_u[tag] for tag in node_tags}
        production = _compute_turbulence_production(mesh, velocity_u, turbulent_viscosity)
        k_system = _solve_reaction_diffusion_scalar(
            mesh,
            diffusion={index: molecular_viscosity + turbulent_viscosity[index] / sigma_k for index in range(cell_count)},
            reaction={index: max(epsilon_floor, cell_epsilon[index]) / max(k_floor, cell_k[index]) for index in range(cell_count)},
            source={index: max(0.0, production[index]) for index in range(cell_count)},
            constrained_values=_scalar_boundary_values(mesh, k_floor, k_inlet),
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
            component="k",
        )
        raw_k = {tag: max(k_floor, value) for tag, value in k_system["values"].items()}
        k_values = {tag: max(k_floor, (1.0 - relaxation) * old_k[tag] + relaxation * raw_k[tag]) for tag in node_tags}
        cell_k = _node_to_cell_average(mesh, k_values)
        epsilon_system = _solve_reaction_diffusion_scalar(
            mesh,
            diffusion={index: molecular_viscosity + turbulent_viscosity[index] / sigma_epsilon for index in range(cell_count)},
            reaction={
                index: c_epsilon_2 * max(epsilon_floor, cell_epsilon[index]) / max(k_floor, cell_k[index])
                for index in range(cell_count)
            },
            source={
                index: c_epsilon_1
                * max(epsilon_floor, cell_epsilon[index])
                / max(k_floor, cell_k[index])
                * max(0.0, production[index])
                for index in range(cell_count)
            },
            constrained_values=_scalar_boundary_values(mesh, epsilon_floor, epsilon_inlet),
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
            component="epsilon",
        )
        raw_epsilon = {tag: max(epsilon_floor, value) for tag, value in epsilon_system["values"].items()}
        epsilon_values = {
            tag: max(epsilon_floor, (1.0 - relaxation) * old_epsilon[tag] + relaxation * raw_epsilon[tag]) for tag in node_tags
        }
        linear_systems = {
            "momentum_u": momentum["linear_system"],
            "k": k_system["linear_system"],
            "epsilon": epsilon_system["linear_system"],
        }
        ratios = [turbulent_viscosity[index] / molecular_viscosity for index in range(cell_count)]
        history.append(
            {
                "iteration": iteration,
                "velocity_update_l2": _node_l2_delta(velocity_u, old_u),
                "k_update_l2": _node_relative_l2_delta(k_values, old_k, floor=k_floor),
                "epsilon_update_l2": _node_relative_l2_delta(epsilon_values, old_epsilon, floor=epsilon_floor),
                "effective_viscosity_update_l2": _cell_l2_delta(effective_viscosity, old_effective),
                "max_turbulent_viscosity_ratio": max(ratios) if ratios else 0.0,
                "mean_turbulent_viscosity_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
                "max_production": max(production.values()) if production else 0.0,
                "u_linear_residual_l2": linear_systems["momentum_u"]["final_residual_l2"],
                "k_linear_residual_l2": linear_systems["k"]["final_residual_l2"],
                "epsilon_linear_residual_l2": linear_systems["epsilon"]["final_residual_l2"],
            }
        )
    cell_k = _node_to_cell_average(mesh, k_values)
    cell_epsilon = _node_to_cell_average(mesh, epsilon_values)
    turbulent_viscosity = _compute_kepsilon_turbulent_viscosity(
        cell_k,
        cell_epsilon,
        density=density,
        molecular_viscosity=molecular_viscosity,
        c_mu=c_mu,
        turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
    )
    effective_viscosity = {index: molecular_viscosity + turbulent_viscosity[index] for index in range(cell_count)}
    production = _compute_turbulence_production(mesh, velocity_u, turbulent_viscosity)
    qoi = _build_kepsilon_qoi(
        mesh,
        velocity_u,
        k_values,
        epsilon_values,
        turbulent_viscosity,
        effective_viscosity,
        production,
        history,
        density=density,
        molecular_viscosity=molecular_viscosity,
        pressure_drop=pressure_drop,
        driving_source=driving_source,
        closure={
            "model": "standard_k_epsilon_two_equation_benchmark",
            "c_mu": c_mu,
            "c_epsilon_1": c_epsilon_1,
            "c_epsilon_2": c_epsilon_2,
            "sigma_k": sigma_k,
            "sigma_epsilon": sigma_epsilon,
            "turbulence_intensity": turbulence_intensity,
            "turbulent_length_scale_fraction": turbulent_length_scale_fraction,
            "turbulent_viscosity_cap_ratio": turbulent_viscosity_cap_ratio,
        },
        linear_systems=linear_systems,
    )
    return {
        "velocity": {tag: (velocity_u[tag], 0.0, 0.0) for tag in node_tags},
        "node_k": k_values,
        "node_epsilon": epsilon_values,
        "node_turbulent_viscosity_ratio": _cell_field_to_node_field(
            mesh,
            {index: turbulent_viscosity[index] / molecular_viscosity for index in range(cell_count)},
        ),
        "node_effective_viscosity": _cell_field_to_node_field(mesh, effective_viscosity),
        "node_production": _cell_field_to_node_field(mesh, production),
        "iteration_history": history,
        "qoi": qoi,
    }


def run_pressure_corrected_kepsilon_channel_case(
    mesh_file: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    density: float = 1.0,
    molecular_viscosity: float = 1.0e-3,
    pressure_drop: float = 0.05,
    iterations: int = 10,
    relaxation: float = 0.4,
    pressure_relaxation: float = 0.35,
    c_mu: float = 0.09,
    c_epsilon_1: float = 1.44,
    c_epsilon_2: float = 1.92,
    sigma_k: float = 1.0,
    sigma_epsilon: float = 1.3,
    turbulence_intensity: float = 0.05,
    turbulent_length_scale_fraction: float = 0.07,
    turbulent_viscosity_cap_ratio: float = 1000.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Run a bounded pressure-corrected k-epsilon channel benchmark."""

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "unstructured_pressure_kepsilon_channel" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        _validate_inputs(
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            relaxation=relaxation,
            c_mu=c_mu,
            c_epsilon_1=c_epsilon_1,
            c_epsilon_2=c_epsilon_2,
            sigma_k=sigma_k,
            sigma_epsilon=sigma_epsilon,
            turbulence_intensity=turbulence_intensity,
            turbulent_length_scale_fraction=turbulent_length_scale_fraction,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
        )
        if not (0.0 < pressure_relaxation <= 1.0):
            raise ValueError("pressure-corrected k-epsilon channel pressure_relaxation must be in (0, 1].")
        mesh_path = Path(mesh_file) if mesh_file else write_unit_square_channel_mesh(target_dir / "public_pressure_kepsilon_channel.msh", nx=10, ny=10)
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=())
        boundary_contract = validate_boundary_contract(
            mesh,
            required_patches=required_patches,
            boundary_conditions=_kepsilon_boundary_conditions(),
        )
        artifacts: dict[str, str] = {
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
            "pressure_kepsilon_boundary_contract": str(_write_json(target_dir / "pressure_kepsilon_boundary_contract.json", boundary_contract)),
            "mesh_vtu": str(write_mesh_vtu(mesh, target_dir / "mesh.vtu")),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_pressure_kepsilon_channel",
                message="Pressure-corrected k-epsilon channel solve was blocked by mesh quality.",
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
            artifacts["pressure_kepsilon_status"] = str(_write_json(target_dir / "pressure_kepsilon_status.json", result.to_dict()))
            return result.to_dict()
        if boundary_contract["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_pressure_kepsilon_channel",
                message="Pressure-corrected k-epsilon channel solve was blocked by boundary-condition contract.",
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
            artifacts["pressure_kepsilon_status"] = str(_write_json(target_dir / "pressure_kepsilon_status.json", result.to_dict()))
            return result.to_dict()
        _require_triangles(mesh)
        fv_geometry = build_fv_geometry(mesh)
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry.to_dict()))
        solution = solve_pressure_corrected_kepsilon_channel(
            mesh,
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            relaxation=relaxation,
            pressure_relaxation=pressure_relaxation,
            c_mu=c_mu,
            c_epsilon_1=c_epsilon_1,
            c_epsilon_2=c_epsilon_2,
            sigma_k=sigma_k,
            sigma_epsilon=sigma_epsilon,
            turbulence_intensity=turbulence_intensity,
            turbulent_length_scale_fraction=turbulent_length_scale_fraction,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["pressure_kepsilon_qoi"] = str(_write_json(target_dir / "pressure_kepsilon_qoi.json", solution["qoi"]))
        artifacts["pressure_kepsilon_iterations"] = str(
            _write_pressure_iteration_history(target_dir / "pressure_kepsilon_iterations.csv", solution["iteration_history"])
        )
        artifacts["pressure_kepsilon_solution_vtu"] = str(
            write_vector_solution_vtu(
                mesh,
                target_dir / "pressure_kepsilon_solution.vtu",
                solution["velocity"],
                scalar_fields={
                    "pressure_correction": solution["pressure_correction"],
                    "turbulent_kinetic_energy": solution["node_k"],
                    "epsilon": solution["node_epsilon"],
                    "turbulent_viscosity_ratio": solution["node_turbulent_viscosity_ratio"],
                    "effective_viscosity": solution["node_effective_viscosity"],
                    "production": solution["node_production"],
                },
            )
        )
        artifacts["pressure_kepsilon_report"] = str(_write_text(target_dir / "pressure_kepsilon_report.md", _pressure_kepsilon_markdown(solution["qoi"])))
        if solution["qoi"]["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_pressure_kepsilon_channel",
                message="Pressure-corrected k-epsilon channel solve completed but did not pass acceptance checks.",
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
                    "solver_execution": "pressure_corrected_kepsilon_channel_failed_acceptance",
                }
            )
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="solve_pressure_kepsilon_channel",
                message="Pressure-corrected k-epsilon turbulent channel benchmark completed.",
                outputs={
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "fv_geometry": fv_geometry.to_dict(),
                    "qoi": solution["qoi"],
                    "solver_execution": "pressure_corrected_kepsilon_channel",
                },
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
        artifacts["pressure_kepsilon_status"] = str(_write_json(target_dir / "pressure_kepsilon_status.json", result.to_dict()))
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_pressure_kepsilon_channel",
            message="Pressure-corrected k-epsilon channel solve failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"pressure_kepsilon_status": str(target_dir / "pressure_kepsilon_status.json")}
        _write_json(target_dir / "pressure_kepsilon_status.json", failure.to_dict())
        return failure.to_dict()


def solve_pressure_corrected_kepsilon_channel(
    mesh: UnstructuredMesh,
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    iterations: int,
    relaxation: float,
    pressure_relaxation: float,
    c_mu: float,
    c_epsilon_1: float,
    c_epsilon_2: float,
    sigma_k: float,
    sigma_epsilon: float,
    turbulence_intensity: float,
    turbulent_length_scale_fraction: float,
    turbulent_viscosity_cap_ratio: float,
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
) -> dict[str, Any]:
    bounds = _mesh_bounds(mesh)
    length = bounds["xmax"] - bounds["xmin"]
    height = bounds["ymax"] - bounds["ymin"]
    if length <= 0 or height <= 0:
        raise ValueError("Pressure-corrected k-epsilon channel requires positive length and height.")
    driving_source = pressure_drop / length
    node_tags = sorted(mesh.nodes)
    reference_velocity = max(
        1.0e-9,
        max(
            _laminar_profile(mesh.nodes[tag].y, bounds, driving_source=driving_source, viscosity=molecular_viscosity)
            for tag in node_tags
        ),
    )
    length_scale = max(1.0e-9, turbulent_length_scale_fraction * height)
    k_floor = 1.0e-10 * reference_velocity * reference_velocity
    epsilon_floor = 1.0e-12 * reference_velocity * reference_velocity * reference_velocity / length_scale
    k_inlet = max(k_floor, 1.5 * (reference_velocity * turbulence_intensity) ** 2)
    epsilon_inlet = max(epsilon_floor, (c_mu**0.75) * (k_inlet**1.5) / length_scale)
    velocity_u = {tag: _laminar_profile(mesh.nodes[tag].y, bounds, driving_source=driving_source, viscosity=molecular_viscosity) for tag in node_tags}
    velocity_v = {tag: 0.0 for tag in node_tags}
    k_values = {tag: _interior_seed(mesh.nodes[tag].y, bounds, k_floor, k_inlet) for tag in node_tags}
    epsilon_values = {tag: _interior_seed(mesh.nodes[tag].y, bounds, epsilon_floor, epsilon_inlet) for tag in node_tags}
    cell_count = len(mesh.cells)
    turbulent_viscosity = {index: molecular_viscosity * 0.1 for index in range(cell_count)}
    effective_viscosity = {index: molecular_viscosity + turbulent_viscosity[index] for index in range(cell_count)}
    production = {index: 0.0 for index in range(cell_count)}
    pressure_correction = {tag: 0.0 for tag in node_tags}
    history: list[dict[str, Any]] = []
    linear_systems: dict[str, Any] = {}
    initial_divergence_l2: float | None = None
    final_divergence_l2 = 0.0
    for iteration in range(1, iterations + 1):
        old_u = dict(velocity_u)
        old_v = dict(velocity_v)
        old_k = dict(k_values)
        old_epsilon = dict(epsilon_values)
        old_effective = dict(effective_viscosity)
        cell_k = _node_to_cell_average(mesh, k_values)
        cell_epsilon = _node_to_cell_average(mesh, epsilon_values)
        turbulent_viscosity = _compute_kepsilon_turbulent_viscosity(
            cell_k,
            cell_epsilon,
            density=density,
            molecular_viscosity=molecular_viscosity,
            c_mu=c_mu,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
        )
        raw_effective = {index: molecular_viscosity + turbulent_viscosity[index] for index in range(cell_count)}
        effective_viscosity = {
            index: (1.0 - relaxation) * old_effective[index] + relaxation * raw_effective[index] for index in range(cell_count)
        }
        momentum = _solve_variable_viscosity_u(
            mesh,
            effective_viscosity=effective_viscosity,
            driving_source=driving_source,
            bounds=bounds,
            molecular_viscosity=molecular_viscosity,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        predicted_u = {tag: (1.0 - relaxation) * old_u[tag] + relaxation * momentum["values"][tag] for tag in node_tags}
        predicted_v = {tag: 0.0 for tag in node_tags}
        predicted_divergence = _velocity_cell_divergence(mesh, predicted_u, predicted_v)
        predicted_divergence_l2 = _flow_cell_metric_l2(mesh, predicted_divergence)
        if initial_divergence_l2 is None:
            initial_divergence_l2 = predicted_divergence_l2
        pressure = _solve_pressure_correction_from_divergence(
            mesh,
            predicted_divergence,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        pressure_correction = pressure["values"]
        pressure_gradients = _recover_node_gradients(mesh, pressure_correction)
        velocity_u = {tag: predicted_u[tag] - pressure_relaxation * pressure_gradients[tag][0] for tag in node_tags}
        velocity_v = {tag: predicted_v[tag] - pressure_relaxation * pressure_gradients[tag][1] for tag in node_tags}
        _apply_channel_velocity_boundaries(
            mesh,
            velocity_u,
            velocity_v,
            bounds,
            driving_source=driving_source,
            molecular_viscosity=molecular_viscosity,
            enforce_outlet_profile=False,
        )
        corrected_divergence = _velocity_cell_divergence(mesh, velocity_u, velocity_v)
        corrected_divergence_l2 = _flow_cell_metric_l2(mesh, corrected_divergence)
        final_divergence_l2 = corrected_divergence_l2
        production = _compute_turbulence_production(mesh, velocity_u, turbulent_viscosity)
        k_system = _solve_reaction_diffusion_scalar(
            mesh,
            diffusion={index: molecular_viscosity + turbulent_viscosity[index] / sigma_k for index in range(cell_count)},
            reaction={index: max(epsilon_floor, cell_epsilon[index]) / max(k_floor, cell_k[index]) for index in range(cell_count)},
            source={index: max(0.0, production[index]) for index in range(cell_count)},
            constrained_values=_scalar_boundary_values(mesh, k_floor, k_inlet),
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
            component="k",
        )
        raw_k = {tag: max(k_floor, value) for tag, value in k_system["values"].items()}
        k_values = {tag: max(k_floor, (1.0 - relaxation) * old_k[tag] + relaxation * raw_k[tag]) for tag in node_tags}
        cell_k = _node_to_cell_average(mesh, k_values)
        epsilon_system = _solve_reaction_diffusion_scalar(
            mesh,
            diffusion={index: molecular_viscosity + turbulent_viscosity[index] / sigma_epsilon for index in range(cell_count)},
            reaction={
                index: c_epsilon_2 * max(epsilon_floor, cell_epsilon[index]) / max(k_floor, cell_k[index])
                for index in range(cell_count)
            },
            source={
                index: c_epsilon_1
                * max(epsilon_floor, cell_epsilon[index])
                / max(k_floor, cell_k[index])
                * max(0.0, production[index])
                for index in range(cell_count)
            },
            constrained_values=_scalar_boundary_values(mesh, epsilon_floor, epsilon_inlet),
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
            component="epsilon",
        )
        raw_epsilon = {tag: max(epsilon_floor, value) for tag, value in epsilon_system["values"].items()}
        epsilon_values = {
            tag: max(epsilon_floor, (1.0 - relaxation) * old_epsilon[tag] + relaxation * raw_epsilon[tag]) for tag in node_tags
        }
        linear_systems = {
            "momentum_u": momentum["linear_system"],
            "pressure_correction": pressure["linear_system"],
            "k": k_system["linear_system"],
            "epsilon": epsilon_system["linear_system"],
        }
        ratios = [turbulent_viscosity[index] / molecular_viscosity for index in range(cell_count)]
        velocity_update = sqrt(
            sum((velocity_u[tag] - old_u[tag]) ** 2 + (velocity_v[tag] - old_v[tag]) ** 2 for tag in node_tags) / max(1, len(node_tags))
        )
        history.append(
            {
                "iteration": iteration,
                "predicted_divergence_l2": predicted_divergence_l2,
                "corrected_divergence_l2": corrected_divergence_l2,
                "divergence_reduction_ratio": corrected_divergence_l2 / predicted_divergence_l2 if predicted_divergence_l2 > 0 else 0.0,
                "velocity_update_l2": velocity_update,
                "k_update_l2": _node_relative_l2_delta(k_values, old_k, floor=k_floor),
                "epsilon_update_l2": _node_relative_l2_delta(epsilon_values, old_epsilon, floor=epsilon_floor),
                "effective_viscosity_update_l2": _cell_l2_delta(effective_viscosity, old_effective),
                "max_turbulent_viscosity_ratio": max(ratios) if ratios else 0.0,
                "mean_turbulent_viscosity_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
                "max_production": max(production.values()) if production else 0.0,
                "u_linear_residual_l2": linear_systems["momentum_u"]["final_residual_l2"],
                "pressure_linear_residual_l2": linear_systems["pressure_correction"]["final_residual_l2"],
                "k_linear_residual_l2": linear_systems["k"]["final_residual_l2"],
                "epsilon_linear_residual_l2": linear_systems["epsilon"]["final_residual_l2"],
            }
        )
    cell_k = _node_to_cell_average(mesh, k_values)
    cell_epsilon = _node_to_cell_average(mesh, epsilon_values)
    turbulent_viscosity = _compute_kepsilon_turbulent_viscosity(
        cell_k,
        cell_epsilon,
        density=density,
        molecular_viscosity=molecular_viscosity,
        c_mu=c_mu,
        turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
    )
    effective_viscosity = {index: molecular_viscosity + turbulent_viscosity[index] for index in range(cell_count)}
    production = _compute_turbulence_production(mesh, velocity_u, turbulent_viscosity)
    qoi = _build_pressure_kepsilon_qoi(
        mesh,
        velocity_u,
        velocity_v,
        k_values,
        epsilon_values,
        turbulent_viscosity,
        effective_viscosity,
        production,
        history,
        density=density,
        molecular_viscosity=molecular_viscosity,
        pressure_drop=pressure_drop,
        pressure_relaxation=pressure_relaxation,
        driving_source=driving_source,
        closure={
            "model": "pressure_corrected_standard_k_epsilon_benchmark",
            "c_mu": c_mu,
            "c_epsilon_1": c_epsilon_1,
            "c_epsilon_2": c_epsilon_2,
            "sigma_k": sigma_k,
            "sigma_epsilon": sigma_epsilon,
            "turbulence_intensity": turbulence_intensity,
            "turbulent_length_scale_fraction": turbulent_length_scale_fraction,
            "turbulent_viscosity_cap_ratio": turbulent_viscosity_cap_ratio,
        },
        linear_systems=linear_systems,
        initial_divergence_l2=initial_divergence_l2 or 0.0,
        final_divergence_l2=final_divergence_l2,
    )
    return {
        "velocity": {tag: (velocity_u[tag], velocity_v[tag], 0.0) for tag in node_tags},
        "pressure_correction": pressure_correction,
        "node_k": k_values,
        "node_epsilon": epsilon_values,
        "node_turbulent_viscosity_ratio": _cell_field_to_node_field(
            mesh,
            {index: turbulent_viscosity[index] / molecular_viscosity for index in range(cell_count)},
        ),
        "node_effective_viscosity": _cell_field_to_node_field(mesh, effective_viscosity),
        "node_production": _cell_field_to_node_field(mesh, production),
        "iteration_history": history,
        "qoi": qoi,
    }


def _solve_reaction_diffusion_scalar(
    mesh: UnstructuredMesh,
    *,
    diffusion: dict[int, float],
    reaction: dict[int, float],
    source: dict[int, float],
    constrained_values: dict[int, float],
    linear_solver: str,
    linear_tolerance: float,
    max_linear_iterations: int | None,
    component: str,
) -> dict[str, Any]:
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    rows: list[dict[int, float]] = [dict() for _ in node_tags]
    rhs = [0.0 for _ in node_tags]
    for cell_index, cell in enumerate(mesh.cells):
        _assemble_reaction_diffusion_triangle(
            rows,
            rhs,
            mesh,
            cell,
            node_index,
            diffusion=diffusion[cell_index],
            reaction=reaction[cell_index],
            source=source[cell_index],
        )
    _apply_dirichlet_sparse_rows(rows, rhs, node_index, constrained_values)
    matrix = SparseMatrixCSR.from_rows(rows, n_cols=len(node_tags), drop_tolerance=1.0e-15)
    solve_result = solve_linear_system(matrix, rhs, method=linear_solver, tolerance=linear_tolerance, max_iterations=max_linear_iterations)
    if not solve_result.converged:
        raise ValueError(
            f"k-epsilon {component} linear solve did not converge: "
            f"method={solve_result.method}, iterations={solve_result.iterations}, "
            f"final_residual_l2={solve_result.final_residual_l2}."
        )
    values = {tag: solve_result.values[node_index[tag]] for tag in node_tags}
    metadata = solve_result.metadata(matrix)
    metadata.update(
        {
            "component": component,
            "assembly": "p1_triangle_reaction_diffusion_transport",
            "constrained_node_count": len(constrained_values),
            "rhs_l2": sqrt(sum(value * value for value in rhs)),
        }
    )
    return {"values": values, "linear_system": metadata}


def _assemble_reaction_diffusion_triangle(
    rows: list[dict[int, float]],
    rhs: list[float],
    mesh: UnstructuredMesh,
    cell: MeshElement,
    node_index: dict[int, int],
    *,
    diffusion: float,
    reaction: float,
    source: float,
) -> None:
    points = [mesh.nodes[tag].to_tuple() for tag in cell.node_tags]
    area = abs(triangle_signed_area_xy(points[0], points[1], points[2]))
    if area <= 0:
        raise ValueError(f"Cannot assemble k-epsilon transport for non-positive triangle area in element {cell.tag}.")
    gradients = _triangle_basis_gradients(points, area)
    mass_diag = area / 6.0
    mass_offdiag = area / 12.0
    for local_i, tag_i in enumerate(cell.node_tags):
        global_i = node_index[tag_i]
        rhs[global_i] += source * area / 3.0
        for local_j, tag_j in enumerate(cell.node_tags):
            global_j = node_index[tag_j]
            mass = mass_diag if local_i == local_j else mass_offdiag
            value = diffusion * area * (
                gradients[local_i][0] * gradients[local_j][0] + gradients[local_i][1] * gradients[local_j][1]
            )
            value += reaction * mass
            rows[global_i][global_j] = rows[global_i].get(global_j, 0.0) + value


def _compute_kepsilon_turbulent_viscosity(
    cell_k: dict[int, float],
    cell_epsilon: dict[int, float],
    *,
    density: float,
    molecular_viscosity: float,
    c_mu: float,
    turbulent_viscosity_cap_ratio: float,
) -> dict[int, float]:
    cap = molecular_viscosity * turbulent_viscosity_cap_ratio
    values: dict[int, float] = {}
    for index, k_value in cell_k.items():
        epsilon_value = max(cell_epsilon[index], 1.0e-30)
        mu_t = density * c_mu * max(0.0, k_value) * max(0.0, k_value) / epsilon_value
        values[index] = min(cap, max(0.0, mu_t))
    return values


def _compute_turbulence_production(
    mesh: UnstructuredMesh,
    velocity_u: dict[int, float],
    turbulent_viscosity: dict[int, float],
) -> dict[int, float]:
    gradients = node_scalar_cell_gradients(mesh, velocity_u)
    values: dict[int, float] = {}
    for index in turbulent_viscosity:
        shear_rate = abs(gradients[index][1])
        values[index] = turbulent_viscosity[index] * shear_rate * shear_rate
    return values


def _build_kepsilon_qoi(
    mesh: UnstructuredMesh,
    velocity_u: dict[int, float],
    k_values: dict[int, float],
    epsilon_values: dict[int, float],
    turbulent_viscosity: dict[int, float],
    effective_viscosity: dict[int, float],
    production: dict[int, float],
    history: list[dict[str, Any]],
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    driving_source: float,
    closure: dict[str, Any],
    linear_systems: dict[str, Any],
) -> dict[str, Any]:
    bounds = _mesh_bounds(mesh)
    length = bounds["xmax"] - bounds["xmin"]
    height = bounds["ymax"] - bounds["ymin"]
    total_measure = 0.0
    weighted_u = 0.0
    weighted_u2 = 0.0
    weighted_k = 0.0
    weighted_epsilon = 0.0
    weighted_production = 0.0
    for index, cell in enumerate(mesh.cells):
        measure = abs(mesh.cell_signed_measure(cell))
        u_cell = sum(velocity_u[tag] for tag in cell.node_tags) / len(cell.node_tags)
        k_cell = sum(k_values[tag] for tag in cell.node_tags) / len(cell.node_tags)
        epsilon_cell = sum(epsilon_values[tag] for tag in cell.node_tags) / len(cell.node_tags)
        weighted_u += u_cell * measure
        weighted_u2 += u_cell * u_cell * measure
        weighted_k += k_cell * measure
        weighted_epsilon += epsilon_cell * measure
        weighted_production += production[index] * measure
        total_measure += measure
    average_velocity = weighted_u / total_measure if total_measure > 0 else 0.0
    rms_velocity = sqrt(weighted_u2 / total_measure) if total_measure > 0 else 0.0
    mean_k = weighted_k / total_measure if total_measure > 0 else 0.0
    mean_epsilon = weighted_epsilon / total_measure if total_measure > 0 else 0.0
    mean_production = weighted_production / total_measure if total_measure > 0 else 0.0
    hydraulic_diameter = 2.0 * height
    reynolds_bulk = density * abs(average_velocity) * hydraulic_diameter / molecular_viscosity
    ratios = [turbulent_viscosity[index] / molecular_viscosity for index in turbulent_viscosity]
    max_ratio = max(ratios) if ratios else 0.0
    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    wall_error = _wall_no_slip_error(mesh, velocity_u)
    final = history[-1] if history else {}
    transport_converged = all(payload.get("converged", False) for payload in linear_systems.values())
    blocking_errors = []
    if not transport_converged:
        blocking_errors.append("At least one final k-epsilon transport linear system did not converge.")
    if max_ratio <= 1.0:
        blocking_errors.append("k-epsilon turbulent viscosity did not activate above molecular viscosity.")
    if mean_k <= 0.0:
        blocking_errors.append("Mean turbulent kinetic energy is non-positive.")
    if mean_epsilon <= 0.0:
        blocking_errors.append("Mean epsilon is non-positive.")
    if mean_production <= 0.0:
        blocking_errors.append("Mean turbulence production is non-positive.")
    if wall_error > 1.0e-8:
        blocking_errors.append(f"No-slip wall velocity check failed: {wall_error}.")
    if final.get("velocity_update_l2", 1.0) > 5.0e-2:
        blocking_errors.append(f"Velocity update did not settle below k-epsilon benchmark tolerance: {final.get('velocity_update_l2')}.")
    if final.get("k_update_l2", 1.0) > 5.0e-1:
        blocking_errors.append(f"k update did not settle below benchmark relative tolerance: {final.get('k_update_l2')}.")
    if final.get("epsilon_update_l2", 1.0) > 5.0e-1:
        blocking_errors.append(f"epsilon update did not settle below benchmark relative tolerance: {final.get('epsilon_update_l2')}.")
    hints = [
        {
            "category": "turbulence_model",
            "recommendation": "Use this local k-epsilon benchmark as evidence that two-equation turbulence variables are active before Fluent RANS setup.",
            "evidence": [
                f"closure={closure['model']}",
                f"max_mu_t_over_mu={max_ratio}",
                f"mean_k={mean_k}",
                f"mean_epsilon={mean_epsilon}",
            ],
        },
        {
            "category": "near_wall_mesh",
            "recommendation": "Keep explicit wall patches and validate y-plus in Fluent before relying on production wall functions.",
            "evidence": [f"wall_no_slip_abs_max={wall_error}", f"hydraulic_diameter={hydraulic_diameter}"],
        },
        {
            "category": "solver_initialization",
            "recommendation": "Use conservative turbulence under-relaxation and monitor mu_t/mu, k, epsilon, and residuals.",
            "evidence": [
                f"final_velocity_update_l2={final.get('velocity_update_l2')}",
                f"final_k_update_l2={final.get('k_update_l2')}",
                f"final_epsilon_update_l2={final.get('epsilon_update_l2')}",
            ],
        },
    ]
    return {
        "schema_version": KEPSILON_CHANNEL_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "standard_kepsilon_turbulent_channel_benchmark",
        "status": "passed" if not blocking_errors else "failed",
        "closure_model": closure,
        "density": density,
        "molecular_viscosity": molecular_viscosity,
        "pressure_drop": pressure_drop,
        "driving_source": driving_source,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "domain": {"length": length, "height": height, "hydraulic_diameter": hydraulic_diameter},
        "linear_systems": {name: _compact_linear_system(payload) for name, payload in linear_systems.items()},
        "metrics": {
            "average_velocity": average_velocity,
            "max_velocity": max(velocity_u.values()) if velocity_u else 0.0,
            "rms_velocity": rms_velocity,
            "bulk_reynolds_number": reynolds_bulk,
            "mean_turbulent_kinetic_energy": mean_k,
            "mean_epsilon": mean_epsilon,
            "mean_production": mean_production,
            "max_turbulent_viscosity_ratio": max_ratio,
            "mean_turbulent_viscosity_ratio": mean_ratio,
            "min_effective_viscosity": min(effective_viscosity.values()) if effective_viscosity else None,
            "max_effective_viscosity": max(effective_viscosity.values()) if effective_viscosity else None,
            "final_velocity_update_l2": final.get("velocity_update_l2"),
            "final_k_update_l2": final.get("k_update_l2"),
            "final_epsilon_update_l2": final.get("epsilon_update_l2"),
            "wall_no_slip_abs_max": wall_error,
        },
        "iteration_count": len(history),
        "acceptance": {
            "transport_linear_systems_converged": transport_converged,
            "eddy_viscosity_above_molecular": max_ratio > 1.0,
            "positive_k_field": min(k_values.values()) > 0.0 if k_values else False,
            "positive_epsilon_field": min(epsilon_values.values()) > 0.0 if epsilon_values else False,
            "positive_turbulence_production": mean_production > 0.0,
            "wall_no_slip_preserved": wall_error <= 1.0e-8,
            "velocity_update_settled": final.get("velocity_update_l2", 1.0) <= 5.0e-2,
            "k_update_settled": final.get("k_update_l2", 1.0) <= 5.0e-1,
            "epsilon_update_settled": final.get("epsilon_update_l2", 1.0) <= 5.0e-1,
        },
        "fluent_setup_hints": hints,
        "blocking_errors": blocking_errors,
        "limitations": [
            "This is a bounded standard k-epsilon two-equation turbulent channel benchmark.",
            "It solves streamwise momentum plus k and epsilon transport equations with explicit nonlinear source linearization.",
            "It is not a production SIMPLE/PISO Navier-Stokes solver, SST model, DES, LES, wall-function validation, or Fluent replacement.",
            "It is intended as a stronger local turbulence evidence gate before later Fluent setup and validation work.",
        ],
    }


def _build_pressure_kepsilon_qoi(
    mesh: UnstructuredMesh,
    velocity_u: dict[int, float],
    velocity_v: dict[int, float],
    k_values: dict[int, float],
    epsilon_values: dict[int, float],
    turbulent_viscosity: dict[int, float],
    effective_viscosity: dict[int, float],
    production: dict[int, float],
    history: list[dict[str, Any]],
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    pressure_relaxation: float,
    driving_source: float,
    closure: dict[str, Any],
    linear_systems: dict[str, Any],
    initial_divergence_l2: float,
    final_divergence_l2: float,
) -> dict[str, Any]:
    bounds = _mesh_bounds(mesh)
    length = bounds["xmax"] - bounds["xmin"]
    height = bounds["ymax"] - bounds["ymin"]
    total_measure = 0.0
    weighted_speed = 0.0
    weighted_speed2 = 0.0
    weighted_k = 0.0
    weighted_epsilon = 0.0
    weighted_production = 0.0
    for index, cell in enumerate(mesh.cells):
        measure = abs(mesh.cell_signed_measure(cell))
        u_cell = sum(velocity_u[tag] for tag in cell.node_tags) / len(cell.node_tags)
        v_cell = sum(velocity_v[tag] for tag in cell.node_tags) / len(cell.node_tags)
        speed_cell = sqrt(u_cell * u_cell + v_cell * v_cell)
        k_cell = sum(k_values[tag] for tag in cell.node_tags) / len(cell.node_tags)
        epsilon_cell = sum(epsilon_values[tag] for tag in cell.node_tags) / len(cell.node_tags)
        weighted_speed += speed_cell * measure
        weighted_speed2 += speed_cell * speed_cell * measure
        weighted_k += k_cell * measure
        weighted_epsilon += epsilon_cell * measure
        weighted_production += production[index] * measure
        total_measure += measure
    average_speed = weighted_speed / total_measure if total_measure > 0 else 0.0
    rms_speed = sqrt(weighted_speed2 / total_measure) if total_measure > 0 else 0.0
    mean_k = weighted_k / total_measure if total_measure > 0 else 0.0
    mean_epsilon = weighted_epsilon / total_measure if total_measure > 0 else 0.0
    mean_production = weighted_production / total_measure if total_measure > 0 else 0.0
    hydraulic_diameter = 2.0 * height
    reynolds_bulk = density * abs(average_speed) * hydraulic_diameter / molecular_viscosity
    ratios = [turbulent_viscosity[index] / molecular_viscosity for index in turbulent_viscosity]
    max_ratio = max(ratios) if ratios else 0.0
    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    wall_error = _wall_velocity_error(mesh, velocity_u, velocity_v)
    final = history[-1] if history else {}
    systems_converged = all(payload.get("converged", False) for payload in linear_systems.values())
    all_positive_finite_k = all(value > 0.0 and isfinite(value) for value in k_values.values())
    all_positive_finite_epsilon = all(value > 0.0 and isfinite(value) for value in epsilon_values.values())
    divergence_ratio = final_divergence_l2 / initial_divergence_l2 if initial_divergence_l2 > 0 else 0.0
    blocking_errors = []
    if not systems_converged:
        blocking_errors.append("At least one pressure-corrected k-epsilon linear system did not converge.")
    if max_ratio <= 1.0:
        blocking_errors.append("Pressure-corrected k-epsilon eddy viscosity did not rise above molecular viscosity.")
    if not all_positive_finite_k:
        blocking_errors.append("k field contains non-positive or non-finite values.")
    if not all_positive_finite_epsilon:
        blocking_errors.append("epsilon field contains non-positive or non-finite values.")
    if mean_production <= 0.0:
        blocking_errors.append("Mean turbulence production is non-positive.")
    if wall_error > 1.0e-8:
        blocking_errors.append(f"No-slip wall velocity check failed: {wall_error}.")
    if final.get("velocity_update_l2", 1.0) > 8.0e-2:
        blocking_errors.append(f"Velocity update did not settle below pressure-corrected benchmark tolerance: {final.get('velocity_update_l2')}.")
    if final.get("k_update_l2", 1.0) > 5.0e-1:
        blocking_errors.append(f"k update did not settle below pressure-corrected benchmark tolerance: {final.get('k_update_l2')}.")
    if final.get("epsilon_update_l2", 1.0) > 5.0e-1:
        blocking_errors.append(f"epsilon update did not settle below pressure-corrected benchmark tolerance: {final.get('epsilon_update_l2')}.")
    if final.get("divergence_reduction_ratio", 1.0) > 1.0:
        blocking_errors.append(f"Final pressure-correction step did not reduce predicted divergence: {final.get('divergence_reduction_ratio')}.")
    hints = [
        {
            "category": "pressure_velocity_coupling",
            "recommendation": "Use this pressure-corrected benchmark to confirm that turbulence setup decisions are not based only on a fixed velocity profile.",
            "evidence": [
                f"initial_divergence_l2={initial_divergence_l2}",
                f"final_divergence_l2={final_divergence_l2}",
                f"pressure_relaxation={pressure_relaxation}",
            ],
        },
        {
            "category": "turbulence_model",
            "recommendation": "Use this local k-epsilon pressure-correction result as bounded evidence before Fluent RANS setup.",
            "evidence": [
                f"closure={closure['model']}",
                f"max_mu_t_over_mu={max_ratio}",
                f"mean_k={mean_k}",
                f"mean_epsilon={mean_epsilon}",
            ],
        },
        {
            "category": "solver_initialization",
            "recommendation": "Use conservative pressure and turbulence relaxation and monitor velocity, k, epsilon, and pressure-correction residuals.",
            "evidence": [
                f"final_velocity_update_l2={final.get('velocity_update_l2')}",
                f"final_k_update_l2={final.get('k_update_l2')}",
                f"final_epsilon_update_l2={final.get('epsilon_update_l2')}",
            ],
        },
    ]
    return {
        "schema_version": PRESSURE_KEPSILON_CHANNEL_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "pressure_corrected_standard_kepsilon_channel_benchmark",
        "status": "passed" if not blocking_errors else "failed",
        "closure_model": closure,
        "density": density,
        "molecular_viscosity": molecular_viscosity,
        "pressure_drop": pressure_drop,
        "pressure_relaxation": pressure_relaxation,
        "driving_source": driving_source,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "domain": {"length": length, "height": height, "hydraulic_diameter": hydraulic_diameter},
        "linear_systems": {name: _compact_linear_system(payload) for name, payload in linear_systems.items()},
        "metrics": {
            "average_speed": average_speed,
            "max_speed": max((sqrt(velocity_u[tag] * velocity_u[tag] + velocity_v[tag] * velocity_v[tag]) for tag in velocity_u), default=0.0),
            "rms_speed": rms_speed,
            "bulk_reynolds_number": reynolds_bulk,
            "mean_turbulent_kinetic_energy": mean_k,
            "mean_epsilon": mean_epsilon,
            "mean_production": mean_production,
            "max_turbulent_viscosity_ratio": max_ratio,
            "mean_turbulent_viscosity_ratio": mean_ratio,
            "min_effective_viscosity": min(effective_viscosity.values()) if effective_viscosity else None,
            "max_effective_viscosity": max(effective_viscosity.values()) if effective_viscosity else None,
            "initial_divergence_l2": initial_divergence_l2,
            "final_divergence_l2": final_divergence_l2,
            "global_divergence_ratio": divergence_ratio,
            "final_step_divergence_reduction_ratio": final.get("divergence_reduction_ratio"),
            "final_velocity_update_l2": final.get("velocity_update_l2"),
            "final_k_update_l2": final.get("k_update_l2"),
            "final_epsilon_update_l2": final.get("epsilon_update_l2"),
            "wall_no_slip_abs_max": wall_error,
        },
        "iteration_count": len(history),
        "acceptance": {
            "all_linear_systems_converged": systems_converged,
            "pressure_correction_system_converged": linear_systems.get("pressure_correction", {}).get("converged", False),
            "eddy_viscosity_above_molecular": max_ratio > 1.0,
            "positive_finite_k_field": all_positive_finite_k,
            "positive_finite_epsilon_field": all_positive_finite_epsilon,
            "positive_turbulence_production": mean_production > 0.0,
            "wall_no_slip_preserved": wall_error <= 1.0e-8,
            "velocity_update_settled": final.get("velocity_update_l2", 1.0) <= 8.0e-2,
            "k_update_settled": final.get("k_update_l2", 1.0) <= 5.0e-1,
            "epsilon_update_settled": final.get("epsilon_update_l2", 1.0) <= 5.0e-1,
            "final_step_divergence_reduced": final.get("divergence_reduction_ratio", 1.0) <= 1.0,
            "divergence_monitor_recorded": initial_divergence_l2 >= 0.0 and final_divergence_l2 >= 0.0,
        },
        "fluent_setup_hints": hints,
        "blocking_errors": blocking_errors,
        "limitations": [
            "This is a bounded pressure-corrected standard k-epsilon channel benchmark.",
            "It couples streamwise momentum prediction, pressure correction, k transport, epsilon transport, and eddy-viscosity updates in one outer loop.",
            "It is not a production SIMPLE/PISO solver, SST model, DES, LES, validated wall-function route, arbitrary geometry solver, or Fluent replacement.",
            "The divergence metrics are pressure-correction monitors for this benchmark, not proof of global production continuity convergence.",
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


def _laminar_profile(y: float, bounds: dict[str, float], *, driving_source: float, viscosity: float) -> float:
    return driving_source * (y - bounds["ymin"]) * (bounds["ymax"] - y) / (2.0 * viscosity)


def _interior_seed(y: float, bounds: dict[str, float], floor: float, center_value: float) -> float:
    height = bounds["ymax"] - bounds["ymin"]
    eta = (y - bounds["ymin"]) / height if height > 0 else 0.0
    shape = max(0.0, 4.0 * eta * (1.0 - eta))
    return floor + center_value * shape


def _node_to_cell_average(mesh: UnstructuredMesh, values: dict[int, float]) -> dict[int, float]:
    return {index: sum(values[tag] for tag in cell.node_tags) / len(cell.node_tags) for index, cell in enumerate(mesh.cells)}


def _scalar_boundary_values(mesh: UnstructuredMesh, wall_value: float, inlet_outlet_value: float) -> dict[int, float]:
    values: dict[int, float] = {}
    patch_for_node: dict[int, set[str]] = {}
    for element in mesh.boundary_elements:
        patch = element.primary_physical_name or "unassigned"
        for tag in element.node_tags:
            patch_for_node.setdefault(tag, set()).add(patch)
    for tag, patches in patch_for_node.items():
        values[tag] = wall_value if "wall" in patches else inlet_outlet_value
    return values


def _apply_channel_velocity_boundaries(
    mesh: UnstructuredMesh,
    velocity_u: dict[int, float],
    velocity_v: dict[int, float],
    bounds: dict[str, float],
    *,
    driving_source: float,
    molecular_viscosity: float,
    enforce_outlet_profile: bool = True,
) -> None:
    patch_for_node: dict[int, set[str]] = {}
    for element in mesh.boundary_elements:
        patch = element.primary_physical_name or "unassigned"
        for tag in element.node_tags:
            patch_for_node.setdefault(tag, set()).add(patch)
    for tag, patches in patch_for_node.items():
        if "wall" in patches:
            velocity_u[tag] = 0.0
            velocity_v[tag] = 0.0
        elif "inlet" in patches or (enforce_outlet_profile and "outlet" in patches):
            velocity_u[tag] = _laminar_profile(mesh.nodes[tag].y, bounds, driving_source=driving_source, viscosity=molecular_viscosity)
            velocity_v[tag] = 0.0


def _wall_no_slip_error(mesh: UnstructuredMesh, velocity_u: dict[int, float]) -> float:
    error = 0.0
    for element in mesh.boundary_elements:
        if element.primary_physical_name == "wall":
            for tag in element.node_tags:
                error = max(error, abs(velocity_u[tag]))
    return error


def _wall_velocity_error(mesh: UnstructuredMesh, velocity_u: dict[int, float], velocity_v: dict[int, float]) -> float:
    error = 0.0
    for element in mesh.boundary_elements:
        if element.primary_physical_name == "wall":
            for tag in element.node_tags:
                error = max(error, sqrt(velocity_u[tag] * velocity_u[tag] + velocity_v[tag] * velocity_v[tag]))
    return error


def _node_relative_l2_delta(current: dict[int, float], previous: dict[int, float], *, floor: float) -> float:
    total = 0.0
    for tag in current:
        scale = max(floor, abs(previous[tag]), abs(current[tag]))
        total += ((current[tag] - previous[tag]) / scale) ** 2
    return sqrt(total / max(1, len(current)))


def _kepsilon_boundary_conditions() -> dict[str, BoundaryCondition]:
    return {
        "inlet": BoundaryCondition(patch="inlet", kind="velocity_profile_dirichlet", role="benchmark inlet velocity, k, and epsilon"),
        "outlet": BoundaryCondition(patch="outlet", kind="velocity_profile_dirichlet", role="fully developed outlet velocity, k, and epsilon"),
        "wall": BoundaryCondition(patch="wall", kind="no_slip_wall", role="top and bottom no-slip walls with low turbulence variable floors"),
    }


def _pressure_kepsilon_boundary_conditions() -> dict[str, BoundaryCondition]:
    return {
        "inlet": BoundaryCondition(patch="inlet", kind="velocity_profile_dirichlet", role="benchmark inlet velocity, k, and epsilon"),
        "outlet": BoundaryCondition(patch="outlet", kind="pressure_reference", role="pressure-correction reference outlet"),
        "wall": BoundaryCondition(patch="wall", kind="no_slip_wall", role="top and bottom no-slip walls with low turbulence variable floors"),
    }


def _validate_inputs(
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    iterations: int,
    relaxation: float,
    c_mu: float,
    c_epsilon_1: float,
    c_epsilon_2: float,
    sigma_k: float,
    sigma_epsilon: float,
    turbulence_intensity: float,
    turbulent_length_scale_fraction: float,
    turbulent_viscosity_cap_ratio: float,
) -> None:
    if density <= 0:
        raise ValueError("k-epsilon channel density must be positive.")
    if molecular_viscosity <= 0:
        raise ValueError("k-epsilon channel molecular_viscosity must be positive.")
    if pressure_drop <= 0:
        raise ValueError("k-epsilon channel pressure_drop must be positive.")
    if iterations < 3:
        raise ValueError("k-epsilon channel iterations must be at least 3.")
    if not (0.0 < relaxation <= 1.0):
        raise ValueError("k-epsilon channel relaxation must be in the interval (0, 1].")
    if c_mu <= 0 or c_epsilon_1 <= 0 or c_epsilon_2 <= 0:
        raise ValueError("k-epsilon closure coefficients must be positive.")
    if sigma_k <= 0 or sigma_epsilon <= 0:
        raise ValueError("k-epsilon turbulent Prandtl numbers must be positive.")
    if not (0.0 < turbulence_intensity < 1.0):
        raise ValueError("k-epsilon turbulence_intensity must be in (0, 1).")
    if not (0.0 < turbulent_length_scale_fraction <= 0.5):
        raise ValueError("k-epsilon turbulent_length_scale_fraction must be in (0, 0.5].")
    if turbulent_viscosity_cap_ratio <= 0:
        raise ValueError("k-epsilon turbulent_viscosity_cap_ratio must be positive.")


def _write_iteration_history(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "iteration",
                "velocity_update_l2",
                "k_update_l2",
                "epsilon_update_l2",
                "effective_viscosity_update_l2",
                "max_turbulent_viscosity_ratio",
                "mean_turbulent_viscosity_ratio",
                "max_production",
                "u_linear_residual_l2",
                "k_linear_residual_l2",
                "epsilon_linear_residual_l2",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_pressure_iteration_history(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "iteration",
                "predicted_divergence_l2",
                "corrected_divergence_l2",
                "divergence_reduction_ratio",
                "velocity_update_l2",
                "k_update_l2",
                "epsilon_update_l2",
                "effective_viscosity_update_l2",
                "max_turbulent_viscosity_ratio",
                "mean_turbulent_viscosity_ratio",
                "max_production",
                "u_linear_residual_l2",
                "pressure_linear_residual_l2",
                "k_linear_residual_l2",
                "epsilon_linear_residual_l2",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _kepsilon_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    return "\n".join(
        [
            "# FastFluent Standard k-epsilon Turbulent Channel",
            "",
            f"Status: `{qoi['status']}`",
            f"Closure: `{qoi['closure_model']['model']}`",
            f"Iterations: `{qoi['iteration_count']}`",
            "",
            "## Metrics",
            "",
            f"- Bulk Reynolds number: `{metrics['bulk_reynolds_number']}`",
            f"- Average velocity: `{metrics['average_velocity']}`",
            f"- Mean k: `{metrics['mean_turbulent_kinetic_energy']}`",
            f"- Mean epsilon: `{metrics['mean_epsilon']}`",
            f"- Max turbulent viscosity ratio: `{metrics['max_turbulent_viscosity_ratio']}`",
            f"- Final velocity update L2: `{metrics['final_velocity_update_l2']}`",
            f"- Final k update L2: `{metrics['final_k_update_l2']}`",
            f"- Final epsilon update L2: `{metrics['final_epsilon_update_l2']}`",
            "",
            "## Scope",
            "",
            "This is a real two-equation k-epsilon benchmark. It is not a production Fluent replacement.",
            "",
        ]
    )


def _pressure_kepsilon_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    return "\n".join(
        [
            "# FastFluent Pressure-Corrected k-epsilon Channel",
            "",
            f"Status: `{qoi['status']}`",
            f"Closure: `{qoi['closure_model']['model']}`",
            f"Iterations: `{qoi['iteration_count']}`",
            "",
            "## Metrics",
            "",
            f"- Bulk Reynolds number: `{metrics['bulk_reynolds_number']}`",
            f"- Average speed: `{metrics['average_speed']}`",
            f"- Mean k: `{metrics['mean_turbulent_kinetic_energy']}`",
            f"- Mean epsilon: `{metrics['mean_epsilon']}`",
            f"- Max turbulent viscosity ratio: `{metrics['max_turbulent_viscosity_ratio']}`",
            f"- Initial divergence L2: `{metrics['initial_divergence_l2']}`",
            f"- Final divergence L2: `{metrics['final_divergence_l2']}`",
            f"- Final velocity update L2: `{metrics['final_velocity_update_l2']}`",
            "",
            "## Scope",
            "",
            "This is a bounded pressure-corrected k-epsilon benchmark. It is not a production Fluent replacement.",
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
