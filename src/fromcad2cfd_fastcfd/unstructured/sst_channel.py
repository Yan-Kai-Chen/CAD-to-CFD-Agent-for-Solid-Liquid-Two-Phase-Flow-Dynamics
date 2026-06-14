"""Bounded k-omega SST turbulent channel benchmark."""

from __future__ import annotations

import csv
import json
from math import isfinite, sqrt, tanh
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .boundary import BoundaryCondition, validate_boundary_contract
from .channel_validation import write_unit_square_channel_mesh
from .geometry import build_fv_geometry, node_scalar_cell_gradients
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .kepsilon_channel import (
    _compute_turbulence_production,
    _node_relative_l2_delta,
    _node_to_cell_average,
    _solve_reaction_diffusion_scalar,
)
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .turbulent_channel import (
    _cell_field_to_node_field,
    _cell_l2_delta,
    _mesh_bounds,
    _node_l2_delta,
    _require_triangles,
    _solve_variable_viscosity_u,
)
from .vtu import write_mesh_vtu, write_vector_solution_vtu


SST_CHANNEL_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_sst_channel_v1"


def run_sst_channel_case(
    mesh_file: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    density: float = 1.0,
    molecular_viscosity: float = 1.0e-3,
    pressure_drop: float = 0.05,
    iterations: int = 10,
    relaxation: float = 0.35,
    beta_star: float = 0.09,
    sigma_k1: float = 0.85,
    sigma_omega1: float = 0.5,
    beta1: float = 0.075,
    sigma_k2: float = 1.0,
    sigma_omega2: float = 0.856,
    beta2: float = 0.0828,
    kappa: float = 0.41,
    a1: float = 0.31,
    turbulence_intensity: float = 0.05,
    turbulent_length_scale_fraction: float = 0.07,
    turbulent_viscosity_cap_ratio: float = 1000.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Run a controlled Menter k-omega SST channel benchmark."""

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "unstructured_sst_channel" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        _validate_inputs(
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            relaxation=relaxation,
            beta_star=beta_star,
            sigma_k1=sigma_k1,
            sigma_omega1=sigma_omega1,
            beta1=beta1,
            sigma_k2=sigma_k2,
            sigma_omega2=sigma_omega2,
            beta2=beta2,
            kappa=kappa,
            a1=a1,
            turbulence_intensity=turbulence_intensity,
            turbulent_length_scale_fraction=turbulent_length_scale_fraction,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
        )
        mesh_path = Path(mesh_file) if mesh_file else write_unit_square_channel_mesh(target_dir / "public_sst_channel.msh", nx=10, ny=10)
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=())
        boundary_contract = validate_boundary_contract(
            mesh,
            required_patches=required_patches,
            boundary_conditions=_sst_boundary_conditions(),
        )
        artifacts: dict[str, str] = {
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
            "sst_boundary_contract": str(_write_json(target_dir / "sst_boundary_contract.json", boundary_contract)),
            "mesh_vtu": str(write_mesh_vtu(mesh, target_dir / "mesh.vtu")),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_sst_channel",
                message="SST channel solve was blocked by mesh quality.",
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
            artifacts["sst_status"] = str(_write_json(target_dir / "sst_status.json", result.to_dict()))
            return result.to_dict()
        if boundary_contract["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_sst_channel",
                message="SST channel solve was blocked by boundary-condition contract.",
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
            artifacts["sst_status"] = str(_write_json(target_dir / "sst_status.json", result.to_dict()))
            return result.to_dict()
        _require_triangles(mesh)
        fv_geometry = build_fv_geometry(mesh)
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry.to_dict()))
        solution = solve_sst_channel(
            mesh,
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            relaxation=relaxation,
            beta_star=beta_star,
            sigma_k1=sigma_k1,
            sigma_omega1=sigma_omega1,
            beta1=beta1,
            sigma_k2=sigma_k2,
            sigma_omega2=sigma_omega2,
            beta2=beta2,
            kappa=kappa,
            a1=a1,
            turbulence_intensity=turbulence_intensity,
            turbulent_length_scale_fraction=turbulent_length_scale_fraction,
            turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["sst_qoi"] = str(_write_json(target_dir / "sst_qoi.json", solution["qoi"]))
        artifacts["sst_iterations"] = str(_write_sst_iteration_history(target_dir / "sst_iterations.csv", solution["iteration_history"]))
        artifacts["sst_solution_vtu"] = str(
            write_vector_solution_vtu(
                mesh,
                target_dir / "sst_solution.vtu",
                solution["velocity"],
                scalar_fields={
                    "turbulent_kinetic_energy": solution["node_k"],
                    "omega": solution["node_omega"],
                    "turbulent_viscosity_ratio": solution["node_turbulent_viscosity_ratio"],
                    "effective_viscosity": solution["node_effective_viscosity"],
                    "production": solution["node_production"],
                    "f1": solution["node_f1"],
                    "f2": solution["node_f2"],
                },
            )
        )
        artifacts["sst_report"] = str(_write_text(target_dir / "sst_report.md", _sst_markdown(solution["qoi"])))
        if solution["qoi"]["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_sst_channel",
                message="SST channel solve completed but did not pass acceptance checks.",
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
                    "solver_execution": "sst_turbulent_channel_failed_acceptance",
                }
            )
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="solve_sst_channel",
                message="Menter k-omega SST turbulent channel benchmark completed.",
                outputs={
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "boundary_contract": boundary_contract,
                    "fv_geometry": fv_geometry.to_dict(),
                    "qoi": solution["qoi"],
                    "solver_execution": "sst_turbulent_channel",
                },
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
        artifacts["sst_status"] = str(_write_json(target_dir / "sst_status.json", result.to_dict()))
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_sst_channel",
            message="SST channel solve failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"sst_status": str(target_dir / "sst_status.json")}
        _write_json(target_dir / "sst_status.json", failure.to_dict())
        return failure.to_dict()


def solve_sst_channel(
    mesh,
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    iterations: int,
    relaxation: float,
    beta_star: float,
    sigma_k1: float,
    sigma_omega1: float,
    beta1: float,
    sigma_k2: float,
    sigma_omega2: float,
    beta2: float,
    kappa: float,
    a1: float,
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
        raise ValueError("SST channel requires positive length and height.")
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
    omega_floor = 1.0e-10 * reference_velocity / length_scale
    k_inlet = max(k_floor, 1.5 * (reference_velocity * turbulence_intensity) ** 2)
    omega_inlet = max(omega_floor, sqrt(k_inlet) / ((beta_star**0.25) * length_scale))
    omega_wall = max(omega_inlet, _wall_omega(mesh, bounds, molecular_viscosity=molecular_viscosity, density=density, beta1=beta1))
    gamma1 = beta1 / beta_star - sigma_omega1 * kappa * kappa / sqrt(beta_star)
    gamma2 = beta2 / beta_star - sigma_omega2 * kappa * kappa / sqrt(beta_star)
    velocity_u = {tag: _laminar_profile(mesh.nodes[tag].y, bounds, driving_source=driving_source, viscosity=molecular_viscosity) for tag in node_tags}
    k_values = {tag: _interior_seed(mesh.nodes[tag].y, bounds, k_floor, k_inlet) for tag in node_tags}
    omega_values = {
        tag: _omega_seed(mesh.nodes[tag].y, bounds, omega_floor=omega_floor, omega_inlet=omega_inlet, omega_wall=omega_wall)
        for tag in node_tags
    }
    turbulent_viscosity = {index: molecular_viscosity * 0.1 for index in range(cell_count)}
    effective_viscosity = {index: molecular_viscosity + turbulent_viscosity[index] for index in range(cell_count)}
    production = {index: 0.0 for index in range(cell_count)}
    f1_values = {index: 0.0 for index in range(cell_count)}
    f2_values = {index: 0.0 for index in range(cell_count)}
    history: list[dict[str, Any]] = []
    linear_systems: dict[str, Any] = {}
    for iteration in range(1, iterations + 1):
        old_u = dict(velocity_u)
        old_k = dict(k_values)
        old_omega = dict(omega_values)
        old_effective = dict(effective_viscosity)
        cell_k = _node_to_cell_average(mesh, k_values)
        cell_omega = _node_to_cell_average(mesh, omega_values)
        blending = _compute_sst_blending(
            mesh,
            k_values,
            omega_values,
            bounds,
            density=density,
            molecular_viscosity=molecular_viscosity,
            beta_star=beta_star,
            sigma_omega2=sigma_omega2,
        )
        f1_values = blending["f1"]
        f2_values = blending["f2"]
        turbulent_viscosity = _compute_sst_turbulent_viscosity(
            mesh,
            velocity_u,
            cell_k,
            cell_omega,
            f2_values,
            density=density,
            molecular_viscosity=molecular_viscosity,
            a1=a1,
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
        limited_production = {
            index: min(max(0.0, production[index]), 20.0 * beta_star * max(omega_floor, cell_omega[index]) * max(k_floor, cell_k[index]))
            for index in range(cell_count)
        }
        sigma_k = {index: _blend(f1_values[index], sigma_k1, sigma_k2) for index in range(cell_count)}
        sigma_omega = {index: _blend(f1_values[index], sigma_omega1, sigma_omega2) for index in range(cell_count)}
        beta = {index: _blend(f1_values[index], beta1, beta2) for index in range(cell_count)}
        gamma = {index: _blend(f1_values[index], gamma1, gamma2) for index in range(cell_count)}
        k_system = _solve_reaction_diffusion_scalar(
            mesh,
            diffusion={index: molecular_viscosity + sigma_k[index] * turbulent_viscosity[index] for index in range(cell_count)},
            reaction={index: beta_star * max(omega_floor, cell_omega[index]) for index in range(cell_count)},
            source=limited_production,
            constrained_values=_sst_k_boundary_values(mesh, k_floor, k_inlet),
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
            component="k_sst",
        )
        raw_k = {tag: max(k_floor, value) for tag, value in k_system["values"].items()}
        k_values = {tag: max(k_floor, (1.0 - relaxation) * old_k[tag] + relaxation * raw_k[tag]) for tag in node_tags}
        cell_k = _node_to_cell_average(mesh, k_values)
        cross_diffusion = _sst_cross_diffusion_source(
            mesh,
            k_values,
            omega_values,
            f1_values,
            density=density,
            sigma_omega2=sigma_omega2,
            omega_floor=omega_floor,
        )
        omega_system = _solve_reaction_diffusion_scalar(
            mesh,
            diffusion={index: molecular_viscosity + sigma_omega[index] * turbulent_viscosity[index] for index in range(cell_count)},
            reaction={index: beta[index] * max(omega_floor, cell_omega[index]) for index in range(cell_count)},
            source={
                index: gamma[index]
                * max(0.0, limited_production[index])
                / max(molecular_viscosity / density, turbulent_viscosity[index] / density, 1.0e-12)
                + cross_diffusion[index]
                for index in range(cell_count)
            },
            constrained_values=_sst_omega_boundary_values(mesh, omega_inlet=omega_inlet, omega_wall=omega_wall),
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
            component="omega_sst",
        )
        raw_omega = {tag: max(omega_floor, value) for tag, value in omega_system["values"].items()}
        omega_values = {
            tag: max(omega_floor, (1.0 - relaxation) * old_omega[tag] + relaxation * raw_omega[tag]) for tag in node_tags
        }
        linear_systems = {
            "momentum_u": momentum["linear_system"],
            "k": k_system["linear_system"],
            "omega": omega_system["linear_system"],
        }
        ratios = [turbulent_viscosity[index] / molecular_viscosity for index in range(cell_count)]
        history.append(
            {
                "iteration": iteration,
                "velocity_update_l2": _node_l2_delta(velocity_u, old_u),
                "k_update_l2": _node_relative_l2_delta(k_values, old_k, floor=k_floor),
                "omega_update_l2": _node_relative_l2_delta(omega_values, old_omega, floor=omega_floor),
                "effective_viscosity_update_l2": _cell_l2_delta(effective_viscosity, old_effective),
                "max_turbulent_viscosity_ratio": max(ratios) if ratios else 0.0,
                "mean_turbulent_viscosity_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
                "max_production": max(production.values()) if production else 0.0,
                "mean_f1": sum(f1_values.values()) / len(f1_values) if f1_values else 0.0,
                "mean_f2": sum(f2_values.values()) / len(f2_values) if f2_values else 0.0,
                "u_linear_residual_l2": linear_systems["momentum_u"]["final_residual_l2"],
                "k_linear_residual_l2": linear_systems["k"]["final_residual_l2"],
                "omega_linear_residual_l2": linear_systems["omega"]["final_residual_l2"],
            }
        )
    cell_k = _node_to_cell_average(mesh, k_values)
    cell_omega = _node_to_cell_average(mesh, omega_values)
    blending = _compute_sst_blending(
        mesh,
        k_values,
        omega_values,
        bounds,
        density=density,
        molecular_viscosity=molecular_viscosity,
        beta_star=beta_star,
        sigma_omega2=sigma_omega2,
    )
    f1_values = blending["f1"]
    f2_values = blending["f2"]
    turbulent_viscosity = _compute_sst_turbulent_viscosity(
        mesh,
        velocity_u,
        cell_k,
        cell_omega,
        f2_values,
        density=density,
        molecular_viscosity=molecular_viscosity,
        a1=a1,
        turbulent_viscosity_cap_ratio=turbulent_viscosity_cap_ratio,
    )
    effective_viscosity = {index: molecular_viscosity + turbulent_viscosity[index] for index in range(cell_count)}
    production = _compute_turbulence_production(mesh, velocity_u, turbulent_viscosity)
    qoi = _build_sst_qoi(
        mesh,
        velocity_u,
        k_values,
        omega_values,
        turbulent_viscosity,
        effective_viscosity,
        production,
        f1_values,
        f2_values,
        history,
        density=density,
        molecular_viscosity=molecular_viscosity,
        pressure_drop=pressure_drop,
        driving_source=driving_source,
        closure={
            "model": "menter_k_omega_sst_benchmark",
            "source": "NASA Turbulence Modeling Resource / Menter SST standard constants",
            "beta_star": beta_star,
            "sigma_k1": sigma_k1,
            "sigma_omega1": sigma_omega1,
            "beta1": beta1,
            "sigma_k2": sigma_k2,
            "sigma_omega2": sigma_omega2,
            "beta2": beta2,
            "kappa": kappa,
            "a1": a1,
            "gamma1": gamma1,
            "gamma2": gamma2,
            "turbulence_intensity": turbulence_intensity,
            "turbulent_length_scale_fraction": turbulent_length_scale_fraction,
            "turbulent_viscosity_cap_ratio": turbulent_viscosity_cap_ratio,
            "omega_wall": omega_wall,
        },
        linear_systems=linear_systems,
    )
    return {
        "velocity": {tag: (velocity_u[tag], 0.0, 0.0) for tag in node_tags},
        "node_k": k_values,
        "node_omega": omega_values,
        "node_turbulent_viscosity_ratio": _cell_field_to_node_field(
            mesh,
            {index: turbulent_viscosity[index] / molecular_viscosity for index in range(cell_count)},
        ),
        "node_effective_viscosity": _cell_field_to_node_field(mesh, effective_viscosity),
        "node_production": _cell_field_to_node_field(mesh, production),
        "node_f1": _cell_field_to_node_field(mesh, f1_values),
        "node_f2": _cell_field_to_node_field(mesh, f2_values),
        "iteration_history": history,
        "qoi": qoi,
    }


def _compute_sst_blending(
    mesh,
    k_values: dict[int, float],
    omega_values: dict[int, float],
    bounds: dict[str, float],
    *,
    density: float,
    molecular_viscosity: float,
    beta_star: float,
    sigma_omega2: float,
) -> dict[str, dict[int, float]]:
    k_gradients = node_scalar_cell_gradients(mesh, k_values)
    omega_gradients = node_scalar_cell_gradients(mesh, omega_values)
    nu = molecular_viscosity / density
    f1_values: dict[int, float] = {}
    f2_values: dict[int, float] = {}
    for index, cell in enumerate(mesh.cells):
        center = mesh.cell_center(cell)
        wall_distance = max(1.0e-9, min(center[1] - bounds["ymin"], bounds["ymax"] - center[1]))
        k_cell = max(1.0e-20, sum(k_values[tag] for tag in cell.node_tags) / len(cell.node_tags))
        omega_cell = max(1.0e-20, sum(omega_values[tag] for tag in cell.node_tags) / len(cell.node_tags))
        grad_dot = k_gradients[index][0] * omega_gradients[index][0] + k_gradients[index][1] * omega_gradients[index][1]
        cd_kw = max(2.0 * density * sigma_omega2 * grad_dot / omega_cell, 1.0e-20)
        arg1_a = sqrt(k_cell) / (beta_star * omega_cell * wall_distance)
        arg1_b = 500.0 * nu / (wall_distance * wall_distance * omega_cell)
        arg1_c = 4.0 * density * sigma_omega2 * k_cell / (cd_kw * wall_distance * wall_distance)
        arg1 = min(max(arg1_a, arg1_b), arg1_c)
        arg2 = max(2.0 * sqrt(k_cell) / (beta_star * omega_cell * wall_distance), arg1_b)
        f1_values[index] = tanh(max(0.0, arg1) ** 4)
        f2_values[index] = tanh(max(0.0, arg2) ** 2)
    return {"f1": f1_values, "f2": f2_values}


def _compute_sst_turbulent_viscosity(
    mesh,
    velocity_u: dict[int, float],
    cell_k: dict[int, float],
    cell_omega: dict[int, float],
    f2_values: dict[int, float],
    *,
    density: float,
    molecular_viscosity: float,
    a1: float,
    turbulent_viscosity_cap_ratio: float,
) -> dict[int, float]:
    gradients = node_scalar_cell_gradients(mesh, velocity_u)
    cap = molecular_viscosity * turbulent_viscosity_cap_ratio
    values: dict[int, float] = {}
    for index in cell_k:
        shear = abs(gradients[index][1])
        denominator = max(a1 * max(cell_omega[index], 1.0e-20), shear * f2_values[index], 1.0e-20)
        mu_t = density * a1 * max(cell_k[index], 0.0) / denominator
        values[index] = min(cap, max(0.0, mu_t))
    return values


def _sst_cross_diffusion_source(
    mesh,
    k_values: dict[int, float],
    omega_values: dict[int, float],
    f1_values: dict[int, float],
    *,
    density: float,
    sigma_omega2: float,
    omega_floor: float,
) -> dict[int, float]:
    k_gradients = node_scalar_cell_gradients(mesh, k_values)
    omega_gradients = node_scalar_cell_gradients(mesh, omega_values)
    values: dict[int, float] = {}
    for index in range(len(mesh.cells)):
        omega_cell = max(omega_floor, sum(omega_values[tag] for tag in mesh.cells[index].node_tags) / len(mesh.cells[index].node_tags))
        grad_dot = k_gradients[index][0] * omega_gradients[index][0] + k_gradients[index][1] * omega_gradients[index][1]
        values[index] = max(0.0, 2.0 * (1.0 - f1_values[index]) * density * sigma_omega2 * grad_dot / omega_cell)
    return values


def _build_sst_qoi(
    mesh,
    velocity_u: dict[int, float],
    k_values: dict[int, float],
    omega_values: dict[int, float],
    turbulent_viscosity: dict[int, float],
    effective_viscosity: dict[int, float],
    production: dict[int, float],
    f1_values: dict[int, float],
    f2_values: dict[int, float],
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
    weighted_omega = 0.0
    weighted_production = 0.0
    weighted_f1 = 0.0
    weighted_f2 = 0.0
    for index, cell in enumerate(mesh.cells):
        measure = abs(mesh.cell_signed_measure(cell))
        u_cell = sum(velocity_u[tag] for tag in cell.node_tags) / len(cell.node_tags)
        k_cell = sum(k_values[tag] for tag in cell.node_tags) / len(cell.node_tags)
        omega_cell = sum(omega_values[tag] for tag in cell.node_tags) / len(cell.node_tags)
        weighted_u += u_cell * measure
        weighted_u2 += u_cell * u_cell * measure
        weighted_k += k_cell * measure
        weighted_omega += omega_cell * measure
        weighted_production += production[index] * measure
        weighted_f1 += f1_values[index] * measure
        weighted_f2 += f2_values[index] * measure
        total_measure += measure
    average_velocity = weighted_u / total_measure if total_measure > 0 else 0.0
    rms_velocity = sqrt(weighted_u2 / total_measure) if total_measure > 0 else 0.0
    mean_k = weighted_k / total_measure if total_measure > 0 else 0.0
    mean_omega = weighted_omega / total_measure if total_measure > 0 else 0.0
    mean_production = weighted_production / total_measure if total_measure > 0 else 0.0
    mean_f1 = weighted_f1 / total_measure if total_measure > 0 else 0.0
    mean_f2 = weighted_f2 / total_measure if total_measure > 0 else 0.0
    hydraulic_diameter = 2.0 * height
    reynolds_bulk = density * abs(average_velocity) * hydraulic_diameter / molecular_viscosity
    ratios = [turbulent_viscosity[index] / molecular_viscosity for index in turbulent_viscosity]
    max_ratio = max(ratios) if ratios else 0.0
    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    wall_error = _wall_no_slip_error(mesh, velocity_u)
    final = history[-1] if history else {}
    systems_converged = all(payload.get("converged", False) for payload in linear_systems.values())
    all_positive_finite_k = all(value > 0.0 and isfinite(value) for value in k_values.values())
    all_positive_finite_omega = all(value > 0.0 and isfinite(value) for value in omega_values.values())
    blocking_errors = []
    if not systems_converged:
        blocking_errors.append("At least one SST linear system did not converge.")
    if max_ratio <= 1.0:
        blocking_errors.append("SST eddy viscosity did not rise above molecular viscosity.")
    if not all_positive_finite_k:
        blocking_errors.append("k field contains non-positive or non-finite values.")
    if not all_positive_finite_omega:
        blocking_errors.append("omega field contains non-positive or non-finite values.")
    if mean_production <= 0.0:
        blocking_errors.append("Mean SST turbulence production is non-positive.")
    if wall_error > 1.0e-8:
        blocking_errors.append(f"No-slip wall velocity check failed: {wall_error}.")
    if final.get("velocity_update_l2", 1.0) > 8.0e-2:
        blocking_errors.append(f"Velocity update did not settle below SST benchmark tolerance: {final.get('velocity_update_l2')}.")
    if final.get("k_update_l2", 1.0) > 6.0e-1:
        blocking_errors.append(f"k update did not settle below SST benchmark tolerance: {final.get('k_update_l2')}.")
    if final.get("omega_update_l2", 1.0) > 6.0e-1:
        blocking_errors.append(f"omega update did not settle below SST benchmark tolerance: {final.get('omega_update_l2')}.")
    hints = [
        {
            "category": "turbulence_model",
            "recommendation": "Use this SST result when the agent needs a stronger near-wall two-equation RANS pre-check than k-epsilon alone.",
            "evidence": [
                f"closure={closure['model']}",
                f"max_mu_t_over_mu={max_ratio}",
                f"mean_f1={mean_f1}",
                f"mean_f2={mean_f2}",
            ],
        },
        {
            "category": "near_wall_mesh",
            "recommendation": "Preserve wall patches and inspect near-wall spacing before transferring SST assumptions to Fluent.",
            "evidence": [
                f"omega_wall={closure['omega_wall']}",
                f"wall_no_slip_abs_max={wall_error}",
            ],
        },
        {
            "category": "solver_initialization",
            "recommendation": "Use conservative relaxation and monitor u, k, omega, and turbulent-viscosity ratio.",
            "evidence": [
                f"final_velocity_update_l2={final.get('velocity_update_l2')}",
                f"final_k_update_l2={final.get('k_update_l2')}",
                f"final_omega_update_l2={final.get('omega_update_l2')}",
            ],
        },
    ]
    return {
        "schema_version": SST_CHANNEL_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "menter_k_omega_sst_channel_benchmark",
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
            "mean_omega": mean_omega,
            "mean_production": mean_production,
            "max_turbulent_viscosity_ratio": max_ratio,
            "mean_turbulent_viscosity_ratio": mean_ratio,
            "min_effective_viscosity": min(effective_viscosity.values()) if effective_viscosity else None,
            "max_effective_viscosity": max(effective_viscosity.values()) if effective_viscosity else None,
            "mean_f1": mean_f1,
            "mean_f2": mean_f2,
            "final_velocity_update_l2": final.get("velocity_update_l2"),
            "final_k_update_l2": final.get("k_update_l2"),
            "final_omega_update_l2": final.get("omega_update_l2"),
            "wall_no_slip_abs_max": wall_error,
        },
        "iteration_count": len(history),
        "acceptance": {
            "transport_linear_systems_converged": systems_converged,
            "eddy_viscosity_above_molecular": max_ratio > 1.0,
            "positive_finite_k_field": all_positive_finite_k,
            "positive_finite_omega_field": all_positive_finite_omega,
            "positive_turbulence_production": mean_production > 0.0,
            "wall_no_slip_preserved": wall_error <= 1.0e-8,
            "velocity_update_settled": final.get("velocity_update_l2", 1.0) <= 8.0e-2,
            "k_update_settled": final.get("k_update_l2", 1.0) <= 6.0e-1,
            "omega_update_settled": final.get("omega_update_l2", 1.0) <= 6.0e-1,
            "blending_functions_recorded": mean_f1 >= 0.0 and mean_f2 >= 0.0,
        },
        "fluent_setup_hints": hints,
        "blocking_errors": blocking_errors,
        "limitations": [
            "This is a bounded Menter k-omega SST channel benchmark.",
            "It solves u momentum, k transport, omega transport, SST blending functions, and the SST eddy-viscosity limiter.",
            "It is not a production arbitrary-geometry RANS solver, DES, LES, wall-function validation route, or Fluent replacement.",
            "The benchmark is intended as local agent evidence for turbulence setup decisions before high-fidelity validation.",
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


def _omega_seed(y: float, bounds: dict[str, float], *, omega_floor: float, omega_inlet: float, omega_wall: float) -> float:
    height = bounds["ymax"] - bounds["ymin"]
    eta = (y - bounds["ymin"]) / height if height > 0 else 0.0
    shape = max(0.0, 4.0 * eta * (1.0 - eta))
    return max(omega_floor, shape * omega_inlet + (1.0 - shape) * omega_wall)


def _wall_omega(mesh, bounds: dict[str, float], *, molecular_viscosity: float, density: float, beta1: float) -> float:
    nu = molecular_viscosity / density
    distances = []
    for cell in mesh.cells:
        center = mesh.cell_center(cell)
        distances.append(max(1.0e-9, min(center[1] - bounds["ymin"], bounds["ymax"] - center[1])))
    delta_d1 = min(distances) if distances else max(1.0e-9, (bounds["ymax"] - bounds["ymin"]) * 0.05)
    return 10.0 * 6.0 * nu / (beta1 * delta_d1 * delta_d1)


def _sst_k_boundary_values(mesh, wall_value: float, inlet_outlet_value: float) -> dict[int, float]:
    values: dict[int, float] = {}
    patch_for_node: dict[int, set[str]] = {}
    for element in mesh.boundary_elements:
        patch = element.primary_physical_name or "unassigned"
        for tag in element.node_tags:
            patch_for_node.setdefault(tag, set()).add(patch)
    for tag, patches in patch_for_node.items():
        values[tag] = wall_value if "wall" in patches else inlet_outlet_value
    return values


def _sst_omega_boundary_values(mesh, *, omega_inlet: float, omega_wall: float) -> dict[int, float]:
    values: dict[int, float] = {}
    patch_for_node: dict[int, set[str]] = {}
    for element in mesh.boundary_elements:
        patch = element.primary_physical_name or "unassigned"
        for tag in element.node_tags:
            patch_for_node.setdefault(tag, set()).add(patch)
    for tag, patches in patch_for_node.items():
        values[tag] = omega_wall if "wall" in patches else omega_inlet
    return values


def _wall_no_slip_error(mesh, velocity_u: dict[int, float]) -> float:
    error = 0.0
    for element in mesh.boundary_elements:
        if element.primary_physical_name == "wall":
            for tag in element.node_tags:
                error = max(error, abs(velocity_u[tag]))
    return error


def _blend(f1: float, inner: float, outer: float) -> float:
    return f1 * inner + (1.0 - f1) * outer


def _sst_boundary_conditions() -> dict[str, BoundaryCondition]:
    return {
        "inlet": BoundaryCondition(patch="inlet", kind="velocity_profile_dirichlet", role="benchmark inlet velocity, k, and omega"),
        "outlet": BoundaryCondition(patch="outlet", kind="velocity_profile_dirichlet", role="fully developed outlet velocity, k, and omega"),
        "wall": BoundaryCondition(patch="wall", kind="no_slip_wall", role="top and bottom no-slip walls with low k and high omega"),
    }


def _validate_inputs(
    *,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
    iterations: int,
    relaxation: float,
    beta_star: float,
    sigma_k1: float,
    sigma_omega1: float,
    beta1: float,
    sigma_k2: float,
    sigma_omega2: float,
    beta2: float,
    kappa: float,
    a1: float,
    turbulence_intensity: float,
    turbulent_length_scale_fraction: float,
    turbulent_viscosity_cap_ratio: float,
) -> None:
    if density <= 0:
        raise ValueError("SST channel density must be positive.")
    if molecular_viscosity <= 0:
        raise ValueError("SST channel molecular_viscosity must be positive.")
    if pressure_drop <= 0:
        raise ValueError("SST channel pressure_drop must be positive.")
    if iterations < 3:
        raise ValueError("SST channel iterations must be at least 3.")
    if not (0.0 < relaxation <= 1.0):
        raise ValueError("SST channel relaxation must be in the interval (0, 1].")
    if beta_star <= 0 or beta1 <= 0 or beta2 <= 0:
        raise ValueError("SST beta coefficients must be positive.")
    if sigma_k1 <= 0 or sigma_omega1 <= 0 or sigma_k2 <= 0 or sigma_omega2 <= 0:
        raise ValueError("SST turbulent Prandtl coefficients must be positive.")
    if kappa <= 0 or a1 <= 0:
        raise ValueError("SST kappa and a1 must be positive.")
    if not (0.0 < turbulence_intensity < 1.0):
        raise ValueError("SST turbulence_intensity must be in (0, 1).")
    if not (0.0 < turbulent_length_scale_fraction <= 0.5):
        raise ValueError("SST turbulent_length_scale_fraction must be in (0, 0.5].")
    if turbulent_viscosity_cap_ratio <= 0:
        raise ValueError("SST turbulent_viscosity_cap_ratio must be positive.")


def _write_sst_iteration_history(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "iteration",
                "velocity_update_l2",
                "k_update_l2",
                "omega_update_l2",
                "effective_viscosity_update_l2",
                "max_turbulent_viscosity_ratio",
                "mean_turbulent_viscosity_ratio",
                "max_production",
                "mean_f1",
                "mean_f2",
                "u_linear_residual_l2",
                "k_linear_residual_l2",
                "omega_linear_residual_l2",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _sst_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    return "\n".join(
        [
            "# FastFluent Menter k-omega SST Channel",
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
            f"- Mean omega: `{metrics['mean_omega']}`",
            f"- Max turbulent viscosity ratio: `{metrics['max_turbulent_viscosity_ratio']}`",
            f"- Mean F1: `{metrics['mean_f1']}`",
            f"- Mean F2: `{metrics['mean_f2']}`",
            f"- Final velocity update L2: `{metrics['final_velocity_update_l2']}`",
            "",
            "## Scope",
            "",
            "This is a bounded Menter k-omega SST benchmark. It is not a production Fluent replacement.",
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
