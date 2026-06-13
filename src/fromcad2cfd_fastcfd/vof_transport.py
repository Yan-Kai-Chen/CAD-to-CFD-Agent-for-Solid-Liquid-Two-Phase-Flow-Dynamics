"""VOF-lite bounded alpha transport benchmark on unstructured meshes."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .paths import unique_path
from .unstructured.channel_validation import write_unit_square_channel_mesh
from .unstructured.geometry import build_fv_geometry
from .unstructured.gmsh import GmshReadError, read_gmsh_v4_ascii
from .unstructured.quality import build_mesh_manifest, evaluate_mesh_quality
from .unstructured.vtu import write_scalar_solution_vtu


VOF_LITE_QOI_SCHEMA_VERSION = "fromcad2cfd_fastfluent_vof_lite_alpha_transport_v1"


def run_vof_lite_transport_benchmark(
    mesh_file: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    steps: int = 20,
    time_step_s: float = 0.02,
    velocity_m_s: tuple[float, float] = (0.1, 0.0),
    inlet_alpha: float = 1.0,
    initial_column_fraction: float = 0.35,
) -> dict[str, Any]:
    """Run a bounded finite-volume alpha transport benchmark.

    This is a VOF-lite transport gate: it exercises bounded alpha advection and
    evidence output, but does not solve pressure, momentum, surface tension, or
    interface reconstruction.
    """

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "vof_lite_alpha_transport" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        if steps < 1:
            raise ValueError("VOF-lite steps must be at least 1.")
        if time_step_s <= 0:
            raise ValueError("VOF-lite time_step_s must be positive.")
        if not (0.0 <= inlet_alpha <= 1.0):
            raise ValueError("VOF-lite inlet_alpha must be in [0, 1].")
        mesh_path = Path(mesh_file) if mesh_file else write_unit_square_channel_mesh(target_dir / "public_vof_lite_channel.msh", nx=4, ny=4)
        mesh = read_gmsh_v4_ascii(mesh_path)
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=("inlet", "outlet", "wall"))
        artifacts: dict[str, str] = {
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="run_vof_lite_alpha_transport",
                message="VOF-lite alpha transport was blocked by mesh quality.",
                errors=quality["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
            result.outputs.update({"artifacts": artifacts, "manifest": manifest, "quality": quality, "solver_execution": "blocked_by_mesh_quality"})
            artifacts["vof_lite_status"] = str(_write_json(target_dir / "vof_lite_status.json", result.to_dict()))
            return result.to_dict()
        solution = solve_vof_lite_alpha_transport(
            mesh,
            steps=steps,
            time_step_s=time_step_s,
            velocity_m_s=velocity_m_s,
            inlet_alpha=inlet_alpha,
            initial_column_fraction=initial_column_fraction,
        )
        artifacts.update(
            {
                "vof_lite_history": str(_write_history_csv(target_dir / "vof_lite_history.csv", solution["history"])),
                "vof_lite_qoi": str(_write_json(target_dir / "vof_lite_qoi.json", solution["qoi"])),
                "vof_lite_solution_vtu": str(
                    write_scalar_solution_vtu(mesh, target_dir / "vof_lite_alpha.vtu", solution["node_alpha"])
                ),
                "vof_lite_report": str(_write_text(target_dir / "vof_lite_report.md", _vof_lite_markdown(solution["qoi"]))),
            }
        )
        if solution["qoi"]["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="run_vof_lite_alpha_transport",
                message="VOF-lite alpha transport did not pass acceptance checks.",
                errors=solution["qoi"]["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="run_vof_lite_alpha_transport",
                message="VOF-lite bounded alpha transport benchmark completed.",
                outputs={
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "qoi": solution["qoi"],
                    "solver_execution": "vof_lite_bounded_alpha_transport",
                },
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            )
        if result.status != "success":
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "qoi": solution["qoi"],
                    "solver_execution": "vof_lite_bounded_alpha_transport_failed_acceptance",
                }
            )
        artifacts["vof_lite_status"] = str(_write_json(target_dir / "vof_lite_status.json", result.to_dict()))
        return result.to_dict()
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="run_vof_lite_alpha_transport",
            message="VOF-lite alpha transport failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"vof_lite_status": str(target_dir / "vof_lite_status.json")}
        _write_json(target_dir / "vof_lite_status.json", failure.to_dict())
        return failure.to_dict()


def solve_vof_lite_alpha_transport(
    mesh,
    *,
    steps: int,
    time_step_s: float,
    velocity_m_s: tuple[float, float],
    inlet_alpha: float,
    initial_column_fraction: float,
) -> dict[str, Any]:
    geometry = build_fv_geometry(mesh)
    bounds = _bounds(mesh)
    column_x = bounds["xmin"] + initial_column_fraction * (bounds["xmax"] - bounds["xmin"])
    alpha = {cell.cell_index: 1.0 if cell.center[0] <= column_x else 0.0 for cell in geometry.cells}
    initial_mass = _alpha_mass(geometry, alpha)
    history = []
    cumulative_boundary_alpha_flux = 0.0
    max_courant = _max_courant(geometry, velocity_m_s, time_step_s)
    total_clipping = 0.0
    for step in range(1, steps + 1):
        delta = {cell.cell_index: 0.0 for cell in geometry.cells}
        boundary_alpha_flux = 0.0
        for face in geometry.faces:
            flux = velocity_m_s[0] * face.area_vector[0] + velocity_m_s[1] * face.area_vector[1]
            if face.neighbor is not None:
                donor = face.owner if flux >= 0 else face.neighbor
                face_alpha = alpha[donor]
                delta[face.owner] -= time_step_s * flux * face_alpha
                delta[face.neighbor] += time_step_s * flux * face_alpha
            else:
                if flux >= 0:
                    face_alpha = alpha[face.owner]
                else:
                    face_alpha = inlet_alpha if face.patch_name == "inlet" else alpha[face.owner]
                delta[face.owner] -= time_step_s * flux * face_alpha
                boundary_alpha_flux += flux * face_alpha
        new_alpha = {}
        step_clipping = 0.0
        for cell in geometry.cells:
            value = alpha[cell.cell_index] + delta[cell.cell_index] / cell.measure
            clipped = min(1.0, max(0.0, value))
            step_clipping += abs(clipped - value) * cell.measure
            new_alpha[cell.cell_index] = clipped
        alpha = new_alpha
        total_clipping += step_clipping
        cumulative_boundary_alpha_flux += time_step_s * boundary_alpha_flux
        mass = _alpha_mass(geometry, alpha)
        history.append(
            {
                "step": step,
                "time_s": step * time_step_s,
                "alpha_mass": mass,
                "min_alpha": min(alpha.values()),
                "max_alpha": max(alpha.values()),
                "boundary_alpha_flux": boundary_alpha_flux,
                "cumulative_boundary_alpha_flux": cumulative_boundary_alpha_flux,
                "clipped_volume": step_clipping,
            }
        )
    final_mass = _alpha_mass(geometry, alpha)
    balance_error = abs(final_mass - initial_mass + cumulative_boundary_alpha_flux)
    qoi = _build_vof_lite_qoi(
        mesh,
        alpha=alpha,
        initial_mass=initial_mass,
        final_mass=final_mass,
        balance_error=balance_error,
        total_clipping=total_clipping,
        max_courant=max_courant,
        steps=steps,
        time_step_s=time_step_s,
        velocity_m_s=velocity_m_s,
        inlet_alpha=inlet_alpha,
        history=history,
    )
    return {"cell_alpha": alpha, "node_alpha": _cell_alpha_to_node_alpha(mesh, alpha), "history": history, "qoi": qoi}


def _build_vof_lite_qoi(
    mesh,
    *,
    alpha: dict[int, float],
    initial_mass: float,
    final_mass: float,
    balance_error: float,
    total_clipping: float,
    max_courant: float,
    steps: int,
    time_step_s: float,
    velocity_m_s: tuple[float, float],
    inlet_alpha: float,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    bounded = min(alpha.values()) >= -1.0e-12 and max(alpha.values()) <= 1.0 + 1.0e-12
    blocking_errors = []
    if max_courant > 0.5:
        blocking_errors.append(f"VOF-lite Courant number is above the accepted benchmark limit: {max_courant}.")
    if not bounded:
        blocking_errors.append("Alpha field is outside [0, 1].")
    if total_clipping > 1.0e-8:
        blocking_errors.append(f"Alpha transport required clipping volume {total_clipping}.")
    reference_mass = max(abs(initial_mass), 1.0e-12)
    relative_balance_error = balance_error / reference_mass
    hints = [
        {
            "category": "vof_time_step",
            "recommendation": "Keep Fluent VOF time step bounded by a conservative Courant target before production runs.",
            "evidence": [f"vof_lite_courant={max_courant}", f"time_step_s={time_step_s}"],
        },
        {
            "category": "volume_fraction_boundedness",
            "recommendation": "Monitor min/max volume fraction and phase-volume balance in Fluent.",
            "evidence": [f"min_alpha={min(alpha.values())}", f"max_alpha={max(alpha.values())}", f"relative_balance_error={relative_balance_error}"],
        },
        {
            "category": "interface_transport_scope",
            "recommendation": "Use this result only as an alpha-transport sanity check; Fluent must still solve momentum, pressure, and interface physics.",
            "evidence": ["solver_execution=vof_lite_bounded_alpha_transport", f"history_rows={len(history)}"],
        },
    ]
    return {
        "schema_version": VOF_LITE_QOI_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "status": "passed" if not blocking_errors else "failed",
        "mesh_name": mesh.source_name(),
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "steps": steps,
        "time_step_s": time_step_s,
        "velocity_m_s": list(velocity_m_s),
        "inlet_alpha": inlet_alpha,
        "metrics": {
            "initial_alpha_mass": initial_mass,
            "final_alpha_mass": final_mass,
            "cumulative_balance_error": balance_error,
            "relative_balance_error": relative_balance_error,
            "total_clipped_volume": total_clipping,
            "max_courant_number": max_courant,
            "min_alpha": min(alpha.values()),
            "max_alpha": max(alpha.values()),
        },
        "acceptance": {
            "bounded_alpha": bounded,
            "courant_within_limit": max_courant <= 0.5,
            "no_clipping_required": total_clipping <= 1.0e-8,
        },
        "fluent_setup_hints": hints,
        "blocking_errors": blocking_errors,
        "limitations": [
            "This is a VOF-lite scalar alpha transport benchmark only.",
            "No pressure, momentum, surface tension, interface reconstruction, turbulence, or Fluent solver result is claimed.",
        ],
    }


def _max_courant(geometry, velocity_m_s: tuple[float, float], time_step_s: float) -> float:
    max_value = 0.0
    for face in geometry.faces:
        flux = abs(velocity_m_s[0] * face.area_vector[0] + velocity_m_s[1] * face.area_vector[1])
        owner_measure = geometry.cells[face.owner].measure
        if owner_measure > 0:
            max_value = max(max_value, flux * time_step_s / owner_measure)
        if face.neighbor is not None:
            neighbor_measure = geometry.cells[face.neighbor].measure
            if neighbor_measure > 0:
                max_value = max(max_value, flux * time_step_s / neighbor_measure)
    return max_value


def _alpha_mass(geometry, alpha: dict[int, float]) -> float:
    return sum(alpha[cell.cell_index] * cell.measure for cell in geometry.cells)


def _cell_alpha_to_node_alpha(mesh, alpha: dict[int, float]) -> dict[int, float]:
    sums = {tag: 0.0 for tag in mesh.nodes}
    counts = {tag: 0 for tag in mesh.nodes}
    for index, cell in enumerate(mesh.cells):
        value = alpha[index]
        for tag in cell.node_tags:
            sums[tag] += value
            counts[tag] += 1
    return {tag: sums[tag] / counts[tag] if counts[tag] else 0.0 for tag in mesh.nodes}


def _bounds(mesh) -> dict[str, float]:
    xs = [node.x for node in mesh.nodes.values()]
    ys = [node.y for node in mesh.nodes.values()]
    return {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys)}


def _write_history_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "step",
                "time_s",
                "alpha_mass",
                "min_alpha",
                "max_alpha",
                "boundary_alpha_flux",
                "cumulative_boundary_alpha_flux",
                "clipped_volume",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _vof_lite_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi["metrics"]
    return "\n".join(
        [
            "# FastFluent VOF-Lite Alpha Transport",
            "",
            f"Status: `{qoi['status']}`",
            f"Steps: `{qoi['steps']}`",
            f"Max Courant number: `{metrics['max_courant_number']}`",
            f"Relative balance error: `{metrics['relative_balance_error']}`",
            f"Alpha range: `{metrics['min_alpha']}` to `{metrics['max_alpha']}`",
            "",
            "## Scope",
            "",
            "This benchmark validates bounded alpha transport only; it is not a Fluent VOF solver.",
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
