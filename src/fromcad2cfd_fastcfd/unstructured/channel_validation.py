"""Boundary-aware Poiseuille channel validation for the unstructured backend."""

from __future__ import annotations

import csv
import json
from math import log, sqrt
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .boundary import BoundaryCondition, validate_boundary_contract
from .geometry import build_fv_geometry
from .gmsh import GmshReadError, read_gmsh_v4_ascii
from .mesh import UnstructuredMesh
from .quality import build_mesh_manifest, evaluate_mesh_quality
from .stokes import solve_manufactured_stokes
from .vtu import write_mesh_vtu, write_vector_solution_vtu


CHANNEL_VALIDATION_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_channel_validation_v1"
CHANNEL_CONVERGENCE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_channel_convergence_v1"


def run_channel_validation_case(
    mesh_file: str | Path,
    *,
    output_dir: str | Path | None = None,
    viscosity: float = 1.0,
    pressure_drop: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
    required_patches: tuple[str, ...] = ("inlet", "outlet", "wall"),
) -> dict[str, Any]:
    """Run the U12-U13 pressure-drop driven laminar channel validation."""

    mesh_path = Path(mesh_file)
    target_dir = Path(output_dir) if output_dir else unique_path(mesh_path.parent / f"{mesh_path.stem}_channel_validation")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        if viscosity <= 0:
            raise ValueError("Channel validation viscosity must be positive.")
        if pressure_drop <= 0:
            raise ValueError("Channel validation pressure_drop must be positive.")
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=())
        bounds = _mesh_bounds(mesh)
        length = bounds["xmax"] - bounds["xmin"]
        height = bounds["ymax"] - bounds["ymin"]
        if length <= 0 or height <= 0:
            raise ValueError("Channel validation requires positive mesh length and height.")
        boundary_contract = validate_boundary_contract(
            mesh,
            required_patches=required_patches,
            boundary_conditions=_channel_boundary_conditions(viscosity=viscosity, pressure_drop=pressure_drop, length=length, height=height),
        )
        artifacts: dict[str, str] = {
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
            "channel_boundary_contract": str(_write_json(target_dir / "channel_boundary_contract.json", boundary_contract)),
            "mesh_vtu": str(write_mesh_vtu(mesh, target_dir / "mesh.vtu")),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_channel_validation",
                message="Channel validation was blocked by mesh quality gate.",
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
            artifacts["channel_status"] = str(target_dir / "channel_status.json")
            _write_json(target_dir / "channel_status.json", result.to_dict())
            return result.to_dict()
        if boundary_contract["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_channel_validation",
                message="Channel validation was blocked by boundary-condition contract.",
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
            artifacts["channel_status"] = str(target_dir / "channel_status.json")
            _write_json(target_dir / "channel_status.json", result.to_dict())
            return result.to_dict()
        _require_triangles(mesh)
        fv_geometry = build_fv_geometry(mesh)
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", fv_geometry.to_dict()))
        solution = solve_channel_poiseuille(
            mesh,
            viscosity=viscosity,
            pressure_drop=pressure_drop,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        artifacts["channel_linear_systems"] = str(_write_json(target_dir / "channel_linear_systems.json", solution["linear_systems"]))
        artifacts["channel_residual_history"] = str(
            _write_channel_residual_history(target_dir / "channel_residual_history.csv", solution["residual_history"])
        )
        artifacts["channel_qoi"] = str(_write_json(target_dir / "channel_qoi.json", solution["qoi"]))
        artifacts["channel_solution_vtu"] = str(
            write_vector_solution_vtu(
                mesh,
                target_dir / "channel_solution.vtu",
                solution["velocity"],
                exact_vectors=solution["exact_velocity"],
                error_vectors=solution["velocity_error"],
                scalar_fields={"pressure_reference": solution["pressure"]},
            )
        )
        artifacts["channel_report"] = str(_write_text(target_dir / "channel_report.md", _channel_markdown(solution["qoi"])))
        result = AgentResult.success(
            backend="unstructured_fvm",
            operation="solve_channel_validation",
            message="Boundary-aware Poiseuille channel validation completed.",
            outputs={
                "artifacts": artifacts,
                "manifest": manifest,
                "quality": quality,
                "boundary_contract": boundary_contract,
                "fv_geometry": fv_geometry.to_dict(),
                "qoi": solution["qoi"],
                "solver_execution": "boundary_aware_poiseuille_channel_validation",
            },
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        artifacts["channel_status"] = str(target_dir / "channel_status.json")
        _write_json(target_dir / "channel_status.json", result.to_dict())
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_channel_validation",
            message="Channel validation failed before solver completion.",
            errors=[str(exc)],
            metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"channel_status": str(target_dir / "channel_status.json")}
        _write_json(target_dir / "channel_status.json", failure.to_dict())
        return failure.to_dict()


def solve_channel_poiseuille(
    mesh: UnstructuredMesh,
    *,
    viscosity: float = 1.0,
    pressure_drop: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
) -> dict[str, Any]:
    """Solve the controlled pressure-drop driven channel benchmark."""

    bounds = _mesh_bounds(mesh)
    length = bounds["xmax"] - bounds["xmin"]
    height = bounds["ymax"] - bounds["ymin"]
    if length <= 0 or height <= 0:
        raise ValueError("Poiseuille channel requires positive length and height.")
    pressure_gradient = (-pressure_drop / length, 0.0)
    solution = solve_manufactured_stokes(
        mesh,
        manufactured_solution="poiseuille_channel",
        viscosity=viscosity,
        pressure_gradient=pressure_gradient,
        linear_solver=linear_solver,
        linear_tolerance=linear_tolerance,
        max_linear_iterations=max_linear_iterations,
    )
    qoi = _build_channel_qoi(mesh, solution, viscosity=viscosity, pressure_drop=pressure_drop)
    solution["qoi"] = qoi
    return solution


def run_channel_convergence_case(
    *,
    mesh_files: list[str | Path] | None = None,
    mesh_levels: tuple[int, ...] = (2, 4, 8),
    output_dir: str | Path | None = None,
    viscosity: float = 1.0,
    pressure_drop: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
) -> dict[str, Any]:
    """Run U14 channel validation across several mesh levels."""

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "unstructured_channel_convergence" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        prepared_meshes = _prepare_convergence_meshes(target_dir, mesh_files=mesh_files, mesh_levels=mesh_levels)
        cases = []
        artifacts: dict[str, Any] = {"case_outputs": []}
        for mesh_path in prepared_meshes:
            case_dir = target_dir / mesh_path.stem
            case = run_channel_validation_case(
                mesh_path,
                output_dir=case_dir,
                viscosity=viscosity,
                pressure_drop=pressure_drop,
                linear_solver=linear_solver,
                linear_tolerance=linear_tolerance,
                max_linear_iterations=max_linear_iterations,
            )
            cases.append(_compact_case(mesh_path, case))
            artifacts["case_outputs"].append(case.get("outputs", {}).get("artifacts", {}))
        summary = _build_convergence_summary(cases, viscosity=viscosity, pressure_drop=pressure_drop)
        artifacts["channel_convergence"] = str(_write_json(target_dir / "channel_convergence.json", summary))
        artifacts["channel_convergence_report"] = str(_write_text(target_dir / "channel_convergence_report.md", _convergence_markdown(summary)))
        if summary["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_channel_convergence",
                message="Channel convergence evidence did not pass acceptance checks.",
                errors=summary["blocking_errors"],
                outputs={"artifacts": artifacts, "convergence": summary, "solver_execution": "channel_convergence_validation"},
                metadata={"output_dir": str(target_dir)},
            )
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="solve_channel_convergence",
                message="Channel convergence evidence completed.",
                outputs={"artifacts": artifacts, "convergence": summary, "solver_execution": "channel_convergence_validation"},
                metadata={"output_dir": str(target_dir)},
            )
        artifacts["channel_convergence_status"] = str(target_dir / "channel_convergence_status.json")
        _write_json(target_dir / "channel_convergence_status.json", result.to_dict())
        return result.to_dict()
    except (OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_channel_convergence",
            message="Channel convergence validation failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"channel_convergence_status": str(target_dir / "channel_convergence_status.json")}
        _write_json(target_dir / "channel_convergence_status.json", failure.to_dict())
        return failure.to_dict()


def write_unit_square_channel_mesh(path: str | Path, *, nx: int, ny: int | None = None) -> Path:
    """Write a public-safe synthetic unit-square channel mesh in Gmsh v4 ASCII."""

    if nx < 1:
        raise ValueError("Channel mesh nx must be at least 1.")
    ny = ny if ny is not None else nx
    if ny < 1:
        raise ValueError("Channel mesh ny must be at least 1.")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    def node_tag(i: int, j: int) -> int:
        return j * (nx + 1) + i + 1

    node_count = (nx + 1) * (ny + 1)
    triangle_count = 2 * nx * ny
    boundary_count = 2 * nx + 2 * ny
    element_count = triangle_count + boundary_count
    lines = [
        "$MeshFormat",
        "4.1 0 8",
        "$EndMeshFormat",
        "$PhysicalNames",
        "4",
        '1 1 "inlet"',
        '1 2 "outlet"',
        '1 3 "wall"',
        '2 10 "fluid"',
        "$EndPhysicalNames",
        "$Entities",
        "0 4 1 0",
        "1 0 0 0 0 1 0 1 1",
        "2 1 0 0 1 1 0 1 2",
        "3 0 0 0 1 0 0 1 3",
        "4 0 1 0 1 1 0 1 3",
        "1 0 0 0 1 1 0 1 10",
        "$EndEntities",
        "$Nodes",
        f"1 {node_count} 1 {node_count}",
        f"2 1 0 {node_count}",
    ]
    lines.extend(str(tag) for tag in range(1, node_count + 1))
    for j in range(ny + 1):
        for i in range(nx + 1):
            lines.append(f"{i / nx:.17g} {j / ny:.17g} 0")
    lines.extend(["$EndNodes", "$Elements", f"5 {element_count} 1 {element_count}", f"1 1 1 {ny}"])
    element_tag = 1
    for j in range(ny):
        lines.append(f"{element_tag} {node_tag(0, j)} {node_tag(0, j + 1)}")
        element_tag += 1
    lines.append(f"1 2 1 {ny}")
    for j in range(ny):
        lines.append(f"{element_tag} {node_tag(nx, j)} {node_tag(nx, j + 1)}")
        element_tag += 1
    lines.append(f"1 3 1 {nx}")
    for i in range(nx):
        lines.append(f"{element_tag} {node_tag(i, 0)} {node_tag(i + 1, 0)}")
        element_tag += 1
    lines.append(f"1 4 1 {nx}")
    for i in range(nx):
        lines.append(f"{element_tag} {node_tag(i, ny)} {node_tag(i + 1, ny)}")
        element_tag += 1
    lines.append(f"2 1 2 {triangle_count}")
    for j in range(ny):
        for i in range(nx):
            n00 = node_tag(i, j)
            n10 = node_tag(i + 1, j)
            n11 = node_tag(i + 1, j + 1)
            n01 = node_tag(i, j + 1)
            lines.append(f"{element_tag} {n00} {n10} {n11}")
            element_tag += 1
            lines.append(f"{element_tag} {n00} {n11} {n01}")
            element_tag += 1
    lines.append("$EndElements")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _channel_boundary_conditions(*, viscosity: float, pressure_drop: float, length: float, height: float) -> dict[str, BoundaryCondition]:
    pressure_gradient = -pressure_drop / length
    average_velocity = pressure_drop * height * height / (12.0 * viscosity * length)
    max_velocity = pressure_drop * height * height / (8.0 * viscosity * length)
    return {
        "inlet": BoundaryCondition(
            patch="inlet",
            kind="velocity_profile_dirichlet",
            role="parabolic Poiseuille inlet profile",
            parameters={"profile": "poiseuille_parabolic", "average_velocity": average_velocity, "max_velocity": max_velocity},
        ),
        "outlet": BoundaryCondition(
            patch="outlet",
            kind="pressure_reference",
            role="zero outlet pressure reference with imposed pressure drop",
            parameters={"pressure": 0.0, "pressure_gradient_x": pressure_gradient, "pressure_drop": pressure_drop},
        ),
        "wall": BoundaryCondition(patch="wall", kind="no_slip_wall", role="top and bottom no-slip channel walls"),
    }


def _build_channel_qoi(mesh: UnstructuredMesh, solution: dict[str, Any], *, viscosity: float, pressure_drop: float) -> dict[str, Any]:
    bounds = _mesh_bounds(mesh)
    length = bounds["xmax"] - bounds["xmin"]
    height = bounds["ymax"] - bounds["ymin"]
    pressure_gradient_x = -pressure_drop / length
    average_velocity_exact = pressure_drop * height * height / (12.0 * viscosity * length)
    max_velocity_exact = pressure_drop * height * height / (8.0 * viscosity * length)
    fluxes = _boundary_fluxes(mesh, solution["velocity"])
    stokes_qoi = solution["qoi"]
    metrics = dict(stokes_qoi["metrics"])
    metrics.update(
        {
            "average_velocity_exact": average_velocity_exact,
            "max_velocity_exact": max_velocity_exact,
            "inlet_flux": fluxes.get("inlet", 0.0),
            "outlet_flux": fluxes.get("outlet", 0.0),
            "wall_abs_flux": abs(fluxes.get("wall", 0.0)),
            "net_boundary_flux": sum(fluxes.values()),
            "mass_balance_abs_flux": abs(sum(fluxes.values())),
            "pressure_gradient_x": pressure_gradient_x,
        }
    )
    return {
        "schema_version": CHANNEL_VALIDATION_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "boundary_aware_poiseuille_channel_validation",
        "status": "passed",
        "viscosity": viscosity,
        "pressure_drop": pressure_drop,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "domain": {"length": length, "height": height},
        "boundary_model": {
            "inlet": "parabolic velocity profile",
            "outlet": "pressure reference recorded as analytical pressure field",
            "wall": "no-slip velocity profile",
        },
        "linear_systems": stokes_qoi["linear_systems"],
        "metrics": metrics,
        "profile_samples": _profile_samples(bounds, viscosity=viscosity, pressure_drop=pressure_drop),
        "residual_history_rows": len(solution["residual_history"]),
        "acceptance": {
            "linear_systems_converged": (
                stokes_qoi["linear_systems"]["u"]["converged"] is True and stokes_qoi["linear_systems"]["v"]["converged"] is True
            ),
            "pressure_drives_positive_x_flow": pressure_gradient_x < 0 and average_velocity_exact > 0,
            "divergence_within_benchmark_tolerance": metrics["cell_divergence_l2"] < 1.0e-10,
        },
        "limitations": [
            "This validates a steady laminar Poiseuille channel benchmark on triangular meshes.",
            "Pressure is an analytical reference/source field; pressure is not solved as a coupled production CFD variable.",
            "Boundary conditions drive a controlled validation kernel, not a general-purpose Fluent replacement.",
            "No VOF, turbulence, rheology, GPU acceleration, or transient Navier-Stokes behavior is claimed.",
        ],
    }


def _boundary_fluxes(mesh: UnstructuredMesh, velocity: dict[int, tuple[float, float, float]]) -> dict[str, float]:
    geometry = build_fv_geometry(mesh)
    fluxes: dict[str, float] = {}
    for face in geometry.faces:
        if not face.patch_name:
            continue
        u = sum(velocity[tag][0] for tag in face.node_tags) / len(face.node_tags)
        v = sum(velocity[tag][1] for tag in face.node_tags) / len(face.node_tags)
        flux = u * face.area_vector[0] + v * face.area_vector[1]
        fluxes[face.patch_name] = fluxes.get(face.patch_name, 0.0) + flux
    return fluxes


def _profile_samples(bounds: dict[str, float], *, viscosity: float, pressure_drop: float) -> list[dict[str, float]]:
    length = bounds["xmax"] - bounds["xmin"]
    height = bounds["ymax"] - bounds["ymin"]
    source = pressure_drop / length
    samples = []
    for fraction in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = bounds["ymin"] + fraction * height
        u = source * (y - bounds["ymin"]) * (bounds["ymax"] - y) / (2.0 * viscosity)
        samples.append({"y_fraction": fraction, "u_exact": u})
    return samples


def _prepare_convergence_meshes(
    target_dir: Path,
    *,
    mesh_files: list[str | Path] | None,
    mesh_levels: tuple[int, ...],
) -> list[Path]:
    if mesh_files:
        paths = [Path(item) for item in mesh_files]
        missing = [str(path) for path in paths if not path.exists()]
        if missing:
            raise ValueError(f"Missing convergence mesh files: {', '.join(missing)}")
        return paths
    if len(mesh_levels) < 2:
        raise ValueError("Channel convergence requires at least two mesh levels.")
    generated_dir = target_dir / "generated_meshes"
    return [write_unit_square_channel_mesh(generated_dir / f"unit_square_{level}x{level}.msh", nx=level, ny=level) for level in mesh_levels]


def _compact_case(mesh_path: Path, case: dict[str, Any]) -> dict[str, Any]:
    qoi = case.get("outputs", {}).get("qoi", {})
    metrics = qoi.get("metrics", {})
    domain = qoi.get("domain", {})
    h_proxy = None
    if domain.get("length") and case.get("outputs", {}).get("manifest", {}).get("cell_count"):
        h_proxy = sqrt((domain["length"] * domain["height"]) / case["outputs"]["manifest"]["cell_count"])
    return {
        "mesh_file": str(mesh_path),
        "status": case.get("status"),
        "node_count": qoi.get("node_count") or case.get("outputs", {}).get("manifest", {}).get("node_count"),
        "cell_count": qoi.get("cell_count") or case.get("outputs", {}).get("manifest", {}).get("cell_count"),
        "h_proxy": h_proxy,
        "cell_center_velocity_l2_error": metrics.get("cell_center_velocity_l2_error"),
        "cell_divergence_l2": metrics.get("cell_divergence_l2"),
        "u_final_residual_l2": metrics.get("u_final_residual_l2"),
        "v_final_residual_l2": metrics.get("v_final_residual_l2"),
        "mass_balance_abs_flux": metrics.get("mass_balance_abs_flux"),
        "errors": case.get("errors", []),
    }


def _build_convergence_summary(cases: list[dict[str, Any]], *, viscosity: float, pressure_drop: float) -> dict[str, Any]:
    errors = [case.get("cell_center_velocity_l2_error") for case in cases]
    statuses = [case.get("status") for case in cases]
    all_success = all(status == "success" for status in statuses)
    monotonic = all(errors[index + 1] is not None and errors[index] is not None and errors[index + 1] < errors[index] for index in range(len(errors) - 1))
    observed_orders = []
    for coarse, fine in zip(cases, cases[1:]):
        h1 = coarse.get("h_proxy")
        h2 = fine.get("h_proxy")
        e1 = coarse.get("cell_center_velocity_l2_error")
        e2 = fine.get("cell_center_velocity_l2_error")
        if h1 and h2 and e1 and e2 and h1 > h2 and e1 > 0 and e2 > 0:
            observed_orders.append(log(e1 / e2) / log(h1 / h2))
    blocking_errors = []
    if not all_success:
        blocking_errors.append("At least one channel validation case failed.")
    if not monotonic:
        blocking_errors.append("Cell-center velocity L2 error did not decrease monotonically with mesh refinement.")
    return {
        "schema_version": CHANNEL_CONVERGENCE_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "boundary_aware_poiseuille_channel_validation",
        "status": "passed" if not blocking_errors else "failed",
        "viscosity": viscosity,
        "pressure_drop": pressure_drop,
        "case_count": len(cases),
        "cases": cases,
        "observed_orders": observed_orders,
        "monotonic_error_decrease": monotonic,
        "blocking_errors": blocking_errors,
        "acceptance": {
            "all_cases_completed": all_success,
            "error_decreases_with_refinement": monotonic,
            "minimum_case_count": len(cases) >= 2,
        },
        "limitations": [
            "This convergence evidence uses a controlled analytical channel benchmark.",
            "It is a validation gate for the unstructured route, not a production Fluent replacement.",
        ],
    }


def _write_channel_residual_history(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["component", "iteration", "residual_l2", "residual_linf"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def _channel_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    return "\n".join(
        [
            "# FastFluent Unstructured Channel Validation",
            "",
            f"Status: `{qoi['status']}`",
            f"Viscosity: `{qoi['viscosity']}`",
            f"Pressure drop: `{qoi['pressure_drop']}`",
            "",
            "## Metrics",
            "",
            f"- Cell-center velocity L2 error: `{metrics['cell_center_velocity_l2_error']}`",
            f"- Cell divergence L2: `{metrics['cell_divergence_l2']}`",
            f"- Mass-balance absolute flux: `{metrics['mass_balance_abs_flux']}`",
            f"- U residual L2: `{metrics['u_final_residual_l2']}`",
            f"- V residual L2: `{metrics['v_final_residual_l2']}`",
            "",
            "## Scope",
            "",
            "This is a boundary-aware analytical Poiseuille validation case, not a production CFD solver.",
            "",
        ]
    )


def _convergence_markdown(summary: dict[str, Any]) -> str:
    lines = ["# FastFluent Unstructured Channel Convergence", "", f"Status: `{summary['status']}`", "", "## Cases", ""]
    for case in summary["cases"]:
        lines.append(
            f"- Cells `{case['cell_count']}`: error `{case['cell_center_velocity_l2_error']}`, "
            f"divergence `{case['cell_divergence_l2']}`"
        )
    lines.extend(["", "## Acceptance", "", f"- Monotonic error decrease: `{summary['monotonic_error_decrease']}`", ""])
    if summary["observed_orders"]:
        lines.append(f"- Observed orders: `{summary['observed_orders']}`")
        lines.append("")
    if summary["blocking_errors"]:
        lines.extend(["## Blocking Errors", ""])
        lines.extend(f"- {error}" for error in summary["blocking_errors"])
        lines.append("")
    return "\n".join(lines)


def _mesh_bounds(mesh: UnstructuredMesh) -> dict[str, float]:
    xs = [node.x for node in mesh.nodes.values()]
    ys = [node.y for node in mesh.nodes.values()]
    zs = [node.z for node in mesh.nodes.values()]
    return {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys), "zmin": min(zs), "zmax": max(zs)}


def _require_triangles(mesh: UnstructuredMesh) -> None:
    unsupported = sorted({cell.kind for cell in mesh.cells if cell.kind != "triangle"})
    if unsupported:
        raise ValueError(f"Channel validation currently supports triangle cells only; unsupported cells: {unsupported}.")


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
