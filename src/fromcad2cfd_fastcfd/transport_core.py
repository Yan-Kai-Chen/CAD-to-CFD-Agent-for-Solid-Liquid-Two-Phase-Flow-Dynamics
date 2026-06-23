"""Unified scalar transport coupling core for FastFluent S6."""

from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .file_io import ensure_dir, read_json_file, write_json_file, write_text_file
from .paths import unique_path
from .unstructured.channel_validation import write_unit_square_channel_mesh
from .unstructured.geometry import build_fv_geometry
from .unstructured.gmsh import GmshReadError, read_gmsh_v4_ascii
from .unstructured.quality import build_mesh_manifest, evaluate_mesh_quality
from .unstructured.vtu import write_scalar_solution_vtu


TRANSPORT_CASE_SCHEMA_VERSION = "fastfluent_transport_case_v1"
TRANSPORT_QOI_SCHEMA_VERSION = "fastfluent_transport_qoi_v1"
TRANSPORT_RESULT_SCHEMA_VERSION = "fastfluent_transport_result_v1"


@dataclass(frozen=True)
class TransportFieldSpec:
    """Agent-facing scalar transport field declaration."""

    name: str
    quantity: str
    units: str
    bounded_min: float | None = None
    bounded_max: float | None = None

    @property
    def bounded(self) -> bool:
        return self.bounded_min is not None and self.bounded_max is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "units": self.units,
            "bounded": self.bounded,
            "bounded_min": self.bounded_min,
            "bounded_max": self.bounded_max,
        }


def demo_transport_case(*, quantity: str = "alpha") -> dict[str, Any]:
    """Return a public S6 transport case for a supported scalar quantity."""

    quantity = quantity.lower().strip()
    base = {
        "schema_version": TRANSPORT_CASE_SCHEMA_VERSION,
        "case_id": f"s6_{quantity}_transport_demo",
        "case_name": f"S6 {quantity} transport coupling demo",
        "steps": 16,
        "time_step_s": 0.01,
        "velocity_m_s": [0.12, 0.0],
        "diffusivity_m2_s": 0.0,
        "required_patches": ["inlet", "outlet", "wall"],
        "initial_condition": {
            "type": "left_column",
            "fraction": 0.35,
            "value": 1.0,
            "background": 0.0,
        },
        "boundary_conditions": {
            "inlet": {"type": "fixed_value", "value": 1.0},
            "outlet": {"type": "zero_gradient"},
            "wall": {"type": "zero_gradient"},
        },
        "source": {"type": "none"},
        "material_couplings": [
            {
                "property": "density_kg_m3",
                "model": "linear",
                "field_min": 0.0,
                "field_max": 1.0,
                "value_at_min": 998.2,
                "value_at_max": 1200.0,
            },
            {
                "property": "dynamic_viscosity_Pa_s",
                "model": "linear",
                "field_min": 0.0,
                "field_max": 1.0,
                "value_at_min": 0.001,
                "value_at_max": 0.006,
            },
        ],
        "acceptance": {
            "max_courant_number": 0.5,
            "max_diffusion_number": 0.5,
            "max_relative_balance_error": 1.0e-8,
            "max_clipped_integral_warning": 1.0e-10,
        },
        "limitations": [
            "S6 solves a bounded scalar transport proxy only.",
            "S6 does not solve pressure, momentum, turbulence, phase interface reconstruction, or Fluent validation.",
        ],
    }
    if quantity == "alpha":
        base["field"] = {"name": "alpha", "quantity": "volume_fraction", "units": "1", "bounded_min": 0.0, "bounded_max": 1.0}
    elif quantity == "temperature":
        base.update(
            {
                "case_id": "s6_temperature_transport_demo",
                "case_name": "S6 temperature transport coupling demo",
                "diffusivity_m2_s": 1.0e-4,
                "velocity_m_s": [0.04, 0.0],
                "initial_condition": {"type": "linear_x", "left_value": 310.0, "right_value": 290.0},
                "boundary_conditions": {
                    "inlet": {"type": "fixed_value", "value": 315.0},
                    "outlet": {"type": "zero_gradient"},
                    "wall": {"type": "zero_gradient"},
                },
                "source": {"type": "constant", "value_per_s": 0.4},
                "material_couplings": [
                    {
                        "property": "dynamic_viscosity_Pa_s",
                        "model": "arrhenius_temperature",
                        "A": 2.5e-6,
                        "B_K": 1800.0,
                    }
                ],
            }
        )
        base["field"] = {"name": "temperature", "quantity": "temperature", "units": "K"}
    elif quantity in {"species", "particle_concentration", "wax_fraction"}:
        bounded_name = {"species": "species_mass_fraction", "particle_concentration": "particle_concentration", "wax_fraction": "wax_fraction"}[quantity]
        base["field"] = {"name": bounded_name, "quantity": quantity, "units": "1", "bounded_min": 0.0, "bounded_max": 1.0}
        if quantity == "wax_fraction":
            base["source"] = {"type": "linear_relaxation", "target": 0.2, "rate_per_s": 0.2}
    else:
        raise ValueError(f"Unsupported S6 demo quantity: {quantity}")
    return base


def run_transport_coupling_demo(output_dir: str | Path, *, quantity: str = "alpha") -> dict[str, Any]:
    """Run a public S6 demo and write a native result packable status file."""

    return run_transport_coupling_case(demo_transport_case(quantity=quantity), output_dir=output_dir)


def run_transport_coupling_case(
    case: dict[str, Any] | str | Path | None = None,
    *,
    mesh_file: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run a unified scalar transport case on a public or provided mesh."""

    payload = _read_case(case)
    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "transport_coupling" / "output")
    ensure_dir(target_dir)
    try:
        validation = validate_transport_case(payload)
        if validation["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="run_transport_coupling",
                message="S6 transport case validation failed.",
                errors=validation["errors"],
                metadata={"output_dir": str(target_dir)},
            ).to_dict()
            result.update({"schema_version": TRANSPORT_RESULT_SCHEMA_VERSION, "quality_status": "failed"})
            result["outputs"]["artifacts"] = {"transport_status": str(target_dir / "status.json")}
            _write_json(target_dir / "status.json", result)
            return result
        mesh_path = Path(mesh_file) if mesh_file else write_unit_square_channel_mesh(target_dir / "public_s6_channel.msh", nx=6, ny=4)
        mesh = read_gmsh_v4_ascii(mesh_path)
        required_patches = tuple(str(item) for item in payload.get("required_patches", ["inlet", "outlet", "wall"]))
        manifest = build_mesh_manifest(mesh)
        quality = evaluate_mesh_quality(mesh, required_patches=required_patches)
        artifacts: dict[str, str] = {
            "transport_case": str(_write_json(target_dir / "transport_case.json", payload)),
            "mesh_manifest": str(_write_json(target_dir / "mesh_manifest.json", manifest)),
            "mesh_quality": str(_write_json(target_dir / "mesh_quality.json", quality)),
        }
        if quality["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="run_transport_coupling",
                message="S6 transport coupling was blocked by mesh quality.",
                errors=quality["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            ).to_dict()
            result.update({"schema_version": TRANSPORT_RESULT_SCHEMA_VERSION, "quality_status": "failed"})
            result["outputs"].update({"artifacts": artifacts, "manifest": manifest, "quality": quality, "solver_execution": "blocked_by_mesh_quality"})
            artifacts["transport_status"] = str(_write_json(target_dir / "status.json", result))
            return result
        geometry = build_fv_geometry(mesh)
        artifacts["fv_geometry"] = str(_write_json(target_dir / "fv_geometry.json", geometry.to_dict()))
        solution = solve_transport_coupling(mesh, payload)
        artifacts.update(
            {
                "transport_history": str(_write_history_csv(target_dir / "transport_history.csv", solution["history"])),
                "transport_qoi": str(_write_json(target_dir / "transport_qoi.json", solution["qoi"])),
                "material_properties": str(_write_json(target_dir / "material_properties.json", solution["material_properties"])),
                "transport_solution_vtu": str(
                    write_scalar_solution_vtu(mesh, target_dir / "transport_solution.vtu", solution["node_values"])
                ),
                "transport_report": str(_write_text(target_dir / "transport_report.md", transport_markdown(solution["qoi"]))),
            }
        )
        status = "success" if solution["qoi"]["status"] in {"passed", "warning"} else "failed"
        if status == "success":
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="run_transport_coupling",
                message="S6 unified transport coupling case completed.",
                outputs={
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "qoi": solution["qoi"],
                    "quality_status": solution["qoi"]["status"],
                    "solver_execution": "unified_transport_coupling_core",
                },
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            ).to_dict()
        else:
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="run_transport_coupling",
                message="S6 unified transport coupling case failed acceptance.",
                errors=solution["qoi"]["blocking_errors"],
                metadata={"mesh_file": str(mesh_path), "output_dir": str(target_dir)},
            ).to_dict()
            result["outputs"].update(
                {
                    "artifacts": artifacts,
                    "manifest": manifest,
                    "quality": quality,
                    "qoi": solution["qoi"],
                    "quality_status": "failed",
                    "solver_execution": "unified_transport_coupling_core_failed_acceptance",
                }
            )
        result.update(
            {
                "schema_version": TRANSPORT_RESULT_SCHEMA_VERSION,
                "case_id": payload.get("case_id"),
                "case_type": "transport_coupling",
                "quality_status": solution["qoi"]["status"],
                "warnings": solution["qoi"]["warnings"],
                "blocking_errors": solution["qoi"]["blocking_errors"],
            }
        )
        artifacts["transport_status"] = str(_write_json(target_dir / "status.json", result))
        return result
    except (GmshReadError, OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="run_transport_coupling",
            message="S6 transport coupling failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        ).to_dict()
        failure.update({"schema_version": TRANSPORT_RESULT_SCHEMA_VERSION, "quality_status": "failed"})
        failure["outputs"]["artifacts"] = {"transport_status": str(target_dir / "status.json")}
        _write_json(target_dir / "status.json", failure)
        return failure


def validate_transport_case(case: dict[str, Any]) -> dict[str, Any]:
    """Validate a S6 transport case without running a solver."""

    errors: list[str] = []
    warnings: list[str] = []
    if case.get("schema_version") != TRANSPORT_CASE_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {case.get('schema_version')!r}")
    field = case.get("field") if isinstance(case.get("field"), dict) else {}
    if not field.get("name"):
        errors.append("field.name is required.")
    if not field.get("quantity"):
        errors.append("field.quantity is required.")
    if float(case.get("time_step_s", 0.0)) <= 0:
        errors.append("time_step_s must be positive.")
    if int(case.get("steps", 0)) < 1:
        errors.append("steps must be at least 1.")
    if float(case.get("diffusivity_m2_s", 0.0)) < 0:
        errors.append("diffusivity_m2_s must be non-negative.")
    velocity = case.get("velocity_m_s", [])
    if not isinstance(velocity, list | tuple) or len(velocity) not in {2, 3}:
        errors.append("velocity_m_s must contain two or three numbers.")
    if field.get("bounded_min") is not None and field.get("bounded_max") is not None:
        if float(field["bounded_min"]) >= float(field["bounded_max"]):
            errors.append("field.bounded_min must be smaller than field.bounded_max.")
    source = case.get("source") if isinstance(case.get("source"), dict) else {"type": "none"}
    if source.get("type", "none") not in {"none", "constant", "linear_relaxation"}:
        errors.append(f"Unsupported source.type: {source.get('type')!r}")
    for coupling in case.get("material_couplings", []):
        if not isinstance(coupling, dict):
            errors.append("material_couplings entries must be objects.")
        elif coupling.get("model") not in {"linear", "arrhenius_temperature"}:
            errors.append(f"Unsupported material coupling model: {coupling.get('model')!r}")
    return {
        "schema_version": "fastfluent_transport_case_validation_v1",
        "status": "failed" if errors else "passed",
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def solve_transport_coupling(mesh, case: dict[str, Any]) -> dict[str, Any]:
    """Solve the bounded explicit scalar transport update on FV cells."""

    field = _field_spec(case)
    geometry = build_fv_geometry(mesh)
    steps = int(case["steps"])
    dt = float(case["time_step_s"])
    velocity = _velocity(case)
    diffusivity = float(case.get("diffusivity_m2_s", 0.0))
    acceptance = case.get("acceptance", {}) if isinstance(case.get("acceptance"), dict) else {}
    phi = _initial_cell_values(geometry, case)
    initial_integral = _cell_integral(geometry, phi)
    cumulative_advective_flux = 0.0
    cumulative_diffusive_flux = 0.0
    cumulative_source = 0.0
    total_clipping = 0.0
    max_courant = _max_courant_number(geometry, velocity, dt)
    max_diffusion = _max_diffusion_number(geometry, diffusivity, dt)
    history = [_history_row(0, 0.0, geometry, phi, initial_integral, 0.0, 0.0, 0.0, 0.0)]
    for step in range(1, steps + 1):
        delta = {cell.cell_index: 0.0 for cell in geometry.cells}
        boundary_advective_flux = 0.0
        boundary_diffusive_flux = 0.0
        source_integral = 0.0
        for face in geometry.faces:
            flux = velocity[0] * face.area_vector[0] + velocity[1] * face.area_vector[1] + velocity[2] * face.area_vector[2]
            if face.neighbor is not None:
                donor = face.owner if flux >= 0.0 else face.neighbor
                face_value = phi[donor]
                delta[face.owner] -= dt * flux * face_value
                delta[face.neighbor] += dt * flux * face_value
                if diffusivity > 0.0:
                    coeff = _diffusion_coeff(geometry, face, diffusivity)
                    exchange = dt * coeff * (phi[face.neighbor] - phi[face.owner])
                    delta[face.owner] += exchange
                    delta[face.neighbor] -= exchange
            else:
                face_value = _boundary_face_value(case, face.patch_name, phi[face.owner], inflow=flux < 0.0)
                delta[face.owner] -= dt * flux * face_value
                boundary_advective_flux += flux * face_value
                if diffusivity > 0.0:
                    bc_value = _dirichlet_boundary_value(case, face.patch_name)
                    if bc_value is not None:
                        coeff = _boundary_diffusion_coeff(geometry, face, diffusivity)
                        exchange = dt * coeff * (bc_value - phi[face.owner])
                        delta[face.owner] += exchange
                        boundary_diffusive_flux += -coeff * (bc_value - phi[face.owner])
        for cell in geometry.cells:
            source_value = _source_value(case, phi[cell.cell_index])
            source_delta = dt * source_value * cell.measure
            delta[cell.cell_index] += source_delta
            source_integral += source_delta
        new_phi: dict[int, float] = {}
        step_clipping = 0.0
        for cell in geometry.cells:
            raw = phi[cell.cell_index] + delta[cell.cell_index] / cell.measure
            clipped = _clip_if_bounded(raw, field)
            step_clipping += abs(clipped - raw) * cell.measure
            new_phi[cell.cell_index] = clipped
        phi = new_phi
        total_clipping += step_clipping
        cumulative_advective_flux += dt * boundary_advective_flux
        cumulative_diffusive_flux += dt * boundary_diffusive_flux
        cumulative_source += source_integral
        history.append(
            _history_row(
                step,
                step * dt,
                geometry,
                phi,
                initial_integral,
                cumulative_advective_flux,
                cumulative_diffusive_flux,
                cumulative_source,
                step_clipping,
            )
        )
    final_integral = _cell_integral(geometry, phi)
    balance_error = abs(final_integral - initial_integral + cumulative_advective_flux + cumulative_diffusive_flux - cumulative_source)
    material_properties = evaluate_material_couplings(case, phi)
    qoi = _transport_qoi(
        mesh,
        field,
        case,
        phi,
        initial_integral=initial_integral,
        final_integral=final_integral,
        cumulative_advective_flux=cumulative_advective_flux,
        cumulative_diffusive_flux=cumulative_diffusive_flux,
        cumulative_source=cumulative_source,
        balance_error=balance_error,
        total_clipping=total_clipping,
        max_courant=max_courant,
        max_diffusion=max_diffusion,
        material_properties=material_properties,
        history=history,
        acceptance=acceptance,
    )
    return {
        "cell_values": phi,
        "node_values": _cell_values_to_node_values(mesh, phi),
        "history": history,
        "material_properties": material_properties,
        "qoi": qoi,
    }


def evaluate_material_couplings(case: dict[str, Any], cell_values: dict[int, float]) -> dict[str, Any]:
    """Evaluate scalar-to-property coupling ranges for agent screening."""

    properties = []
    values = list(cell_values.values())
    for coupling in case.get("material_couplings", []):
        if not isinstance(coupling, dict):
            continue
        model = coupling.get("model")
        if model == "linear":
            fmin = float(coupling.get("field_min", min(values)))
            fmax = float(coupling.get("field_max", max(values)))
            vmin = float(coupling["value_at_min"])
            vmax = float(coupling["value_at_max"])
            denom = fmax - fmin if abs(fmax - fmin) > 1.0e-30 else 1.0
            prop_values = [vmin + (value - fmin) * (vmax - vmin) / denom for value in values]
        elif model == "arrhenius_temperature":
            a = float(coupling["A"])
            b = float(coupling["B_K"])
            prop_values = [a * math.exp(b / max(value, 1.0e-12)) for value in values]
        else:
            continue
        properties.append(
            {
                "property": coupling.get("property"),
                "model": model,
                "min": min(prop_values),
                "max": max(prop_values),
                "mean": sum(prop_values) / len(prop_values),
            }
        )
    return {
        "schema_version": "fastfluent_transport_material_couplings_v1",
        "property_count": len(properties),
        "properties": properties,
        "limitations": ["Material coupling is evaluated from scalar fields for screening; it is not a coupled momentum solve."],
    }


def transport_markdown(qoi: dict[str, Any]) -> str:
    metrics = qoi.get("metrics", {})
    return "\n".join(
        [
            "# FastFluent S6 Unified Transport Coupling",
            "",
            f"- Status: `{qoi.get('status')}`",
            f"- Field: `{qoi.get('field', {}).get('name')}`",
            f"- Quantity: `{qoi.get('field', {}).get('quantity')}`",
            f"- Max Courant number: `{metrics.get('max_courant_number')}`",
            f"- Max diffusion number: `{metrics.get('max_diffusion_number')}`",
            f"- Relative balance error: `{metrics.get('relative_balance_error')}`",
            f"- Field range: `{metrics.get('min_value')}` to `{metrics.get('max_value')}`",
            f"- Material property count: `{qoi.get('material_couplings', {}).get('property_count')}`",
            "",
            "## Boundary",
            "",
            "This is a unified scalar transport evidence route. It is valid for screening and workflow control only.",
            "",
        ]
    )


def _transport_qoi(
    mesh,
    field: TransportFieldSpec,
    case: dict[str, Any],
    values: dict[int, float],
    *,
    initial_integral: float,
    final_integral: float,
    cumulative_advective_flux: float,
    cumulative_diffusive_flux: float,
    cumulative_source: float,
    balance_error: float,
    total_clipping: float,
    max_courant: float,
    max_diffusion: float,
    material_properties: dict[str, Any],
    history: list[dict[str, Any]],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    reference = max(abs(initial_integral), 1.0e-12)
    relative_balance_error = balance_error / reference
    min_value = min(values.values())
    max_value = max(values.values())
    warnings: list[str] = []
    blocking_errors: list[str] = []
    if max_courant > float(acceptance.get("max_courant_number", 0.5)):
        blocking_errors.append(f"Courant number exceeds S6 acceptance limit: {max_courant}.")
    if max_diffusion > float(acceptance.get("max_diffusion_number", 0.5)):
        blocking_errors.append(f"Diffusion number exceeds S6 acceptance limit: {max_diffusion}.")
    if field.bounded and (min_value < field.bounded_min - 1.0e-12 or max_value > field.bounded_max + 1.0e-12):
        blocking_errors.append("Bounded scalar field left its declared bounds.")
    if total_clipping > float(acceptance.get("max_clipped_integral_warning", 1.0e-10)):
        warnings.append(f"Transport required bounded clipping integral {total_clipping}.")
    if relative_balance_error > float(acceptance.get("max_relative_balance_error", 1.0e-8)):
        warnings.append(f"Transport balance residual is above advisory limit: {relative_balance_error}.")
    status = "failed" if blocking_errors else ("warning" if warnings else "passed")
    return {
        "schema_version": TRANSPORT_QOI_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "unified_scalar_transport",
        "status": status,
        "field": field.to_dict(),
        "case_id": case.get("case_id"),
        "mesh_name": mesh.source_name(),
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "steps": int(case["steps"]),
        "time_step_s": float(case["time_step_s"]),
        "metrics": {
            "initial_integral": initial_integral,
            "final_integral": final_integral,
            "cumulative_advective_boundary_flux": cumulative_advective_flux,
            "cumulative_diffusive_boundary_flux": cumulative_diffusive_flux,
            "cumulative_source_integral": cumulative_source,
            "absolute_balance_error": balance_error,
            "relative_balance_error": relative_balance_error,
            "total_clipped_integral": total_clipping,
            "max_courant_number": max_courant,
            "max_diffusion_number": max_diffusion,
            "min_value": min_value,
            "max_value": max_value,
            "history_rows": len(history),
        },
        "acceptance": {
            "courant_within_limit": max_courant <= float(acceptance.get("max_courant_number", 0.5)),
            "diffusion_within_limit": max_diffusion <= float(acceptance.get("max_diffusion_number", 0.5)),
            "declared_bounds_respected": not field.bounded
            or (min_value >= field.bounded_min - 1.0e-12 and max_value <= field.bounded_max + 1.0e-12),
            "no_hard_blocking_errors": not blocking_errors,
        },
        "material_couplings": material_properties,
        "fluent_setup_hints": [
            {
                "category": "transport_scalar",
                "recommendation": "Use the same scalar bounds, source intent, and transport QoI as pre-Fluent setup checks.",
                "evidence": [f"field={field.name}", f"quantity={field.quantity}", f"status={status}"],
            },
            {
                "category": "time_step_screening",
                "recommendation": "Keep Fluent transient time steps below the S6 Courant and diffusion screening limits before production tuning.",
                "evidence": [f"max_courant={max_courant}", f"max_diffusion={max_diffusion}"],
            },
        ],
        "warnings": warnings,
        "blocking_errors": blocking_errors,
        "limitations": case.get("limitations", []),
    }


def _read_case(case: dict[str, Any] | str | Path | None) -> dict[str, Any]:
    if case is None:
        return demo_transport_case(quantity="alpha")
    if isinstance(case, dict):
        return dict(case)
    return read_json_file(case)


def _field_spec(case: dict[str, Any]) -> TransportFieldSpec:
    field = case.get("field") if isinstance(case.get("field"), dict) else {}
    return TransportFieldSpec(
        name=str(field.get("name")),
        quantity=str(field.get("quantity")),
        units=str(field.get("units", "1")),
        bounded_min=float(field["bounded_min"]) if field.get("bounded_min") is not None else None,
        bounded_max=float(field["bounded_max"]) if field.get("bounded_max") is not None else None,
    )


def _velocity(case: dict[str, Any]) -> tuple[float, float, float]:
    values = [float(item) for item in case.get("velocity_m_s", [0.0, 0.0])]
    if len(values) == 2:
        values.append(0.0)
    return (values[0], values[1], values[2])


def _initial_cell_values(geometry, case: dict[str, Any]) -> dict[int, float]:
    initial = case.get("initial_condition") if isinstance(case.get("initial_condition"), dict) else {"type": "uniform", "value": 0.0}
    xs = [cell.center[0] for cell in geometry.cells]
    xmin = min(xs)
    xmax = max(xs)
    kind = initial.get("type", "uniform")
    if kind == "uniform":
        value = float(initial.get("value", 0.0))
        return {cell.cell_index: value for cell in geometry.cells}
    if kind == "left_column":
        fraction = float(initial.get("fraction", 0.35))
        threshold = xmin + fraction * (xmax - xmin)
        value = float(initial.get("value", 1.0))
        background = float(initial.get("background", 0.0))
        return {cell.cell_index: value if cell.center[0] <= threshold else background for cell in geometry.cells}
    if kind == "linear_x":
        left = float(initial.get("left_value", 1.0))
        right = float(initial.get("right_value", 0.0))
        denom = xmax - xmin if xmax > xmin else 1.0
        return {cell.cell_index: left + (cell.center[0] - xmin) * (right - left) / denom for cell in geometry.cells}
    raise ValueError(f"Unsupported initial_condition.type: {kind!r}")


def _boundary_face_value(case: dict[str, Any], patch_name: str | None, owner_value: float, *, inflow: bool) -> float:
    if not inflow:
        return owner_value
    bc = _boundary_condition(case, patch_name)
    if bc.get("type") == "fixed_value":
        return float(bc["value"])
    return owner_value


def _dirichlet_boundary_value(case: dict[str, Any], patch_name: str | None) -> float | None:
    bc = _boundary_condition(case, patch_name)
    if bc.get("type") == "fixed_value":
        return float(bc["value"])
    return None


def _boundary_condition(case: dict[str, Any], patch_name: str | None) -> dict[str, Any]:
    bcs = case.get("boundary_conditions") if isinstance(case.get("boundary_conditions"), dict) else {}
    return bcs.get(str(patch_name), {"type": "zero_gradient"}) if isinstance(bcs.get(str(patch_name), {}), dict) else {"type": "zero_gradient"}


def _source_value(case: dict[str, Any], current_value: float) -> float:
    source = case.get("source") if isinstance(case.get("source"), dict) else {"type": "none"}
    kind = source.get("type", "none")
    if kind == "constant":
        return float(source.get("value_per_s", 0.0))
    if kind == "linear_relaxation":
        return float(source.get("rate_per_s", 0.0)) * (float(source.get("target", 0.0)) - current_value)
    return 0.0


def _clip_if_bounded(value: float, field: TransportFieldSpec) -> float:
    if not field.bounded:
        return value
    return min(field.bounded_max, max(field.bounded_min, value))


def _max_courant_number(geometry, velocity: tuple[float, float, float], dt: float) -> float:
    max_value = 0.0
    for face in geometry.faces:
        flux = abs(velocity[0] * face.area_vector[0] + velocity[1] * face.area_vector[1] + velocity[2] * face.area_vector[2])
        for cell_index in (face.owner, face.neighbor):
            if cell_index is not None and geometry.cells[cell_index].measure > 0:
                max_value = max(max_value, flux * dt / geometry.cells[cell_index].measure)
    return max_value


def _max_diffusion_number(geometry, diffusivity: float, dt: float) -> float:
    if diffusivity <= 0:
        return 0.0
    max_value = 0.0
    for face in geometry.faces:
        coeff = _diffusion_coeff(geometry, face, diffusivity) if face.neighbor is not None else _boundary_diffusion_coeff(geometry, face, diffusivity)
        for cell_index in (face.owner, face.neighbor):
            if cell_index is not None and geometry.cells[cell_index].measure > 0:
                max_value = max(max_value, coeff * dt / geometry.cells[cell_index].measure)
    return max_value


def _diffusion_coeff(geometry, face, diffusivity: float) -> float:
    owner_center = geometry.cells[face.owner].center
    if face.neighbor is None:
        return _boundary_diffusion_coeff(geometry, face, diffusivity)
    neighbor_center = geometry.cells[face.neighbor].center
    distance = _distance(owner_center, neighbor_center)
    return diffusivity * face.area / max(distance, 1.0e-12)


def _boundary_diffusion_coeff(geometry, face, diffusivity: float) -> float:
    owner_center = geometry.cells[face.owner].center
    distance = _distance(owner_center, face.center)
    return diffusivity * face.area / max(distance, 1.0e-12)


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _cell_integral(geometry, values: dict[int, float]) -> float:
    return sum(values[cell.cell_index] * cell.measure for cell in geometry.cells)


def _cell_values_to_node_values(mesh, values: dict[int, float]) -> dict[int, float]:
    sums = {tag: 0.0 for tag in mesh.nodes}
    counts = {tag: 0 for tag in mesh.nodes}
    for index, cell in enumerate(mesh.cells):
        value = values[index]
        for tag in cell.node_tags:
            sums[tag] += value
            counts[tag] += 1
    return {tag: sums[tag] / counts[tag] if counts[tag] else 0.0 for tag in mesh.nodes}


def _history_row(
    step: int,
    time_s: float,
    geometry,
    values: dict[int, float],
    initial_integral: float,
    cumulative_advective_flux: float,
    cumulative_diffusive_flux: float,
    cumulative_source: float,
    clipped_integral: float,
) -> dict[str, Any]:
    integral = _cell_integral(geometry, values)
    residual = integral - initial_integral + cumulative_advective_flux + cumulative_diffusive_flux - cumulative_source
    return {
        "step": step,
        "time_s": time_s,
        "integral": integral,
        "min_value": min(values.values()),
        "max_value": max(values.values()),
        "cumulative_advective_boundary_flux": cumulative_advective_flux,
        "cumulative_diffusive_boundary_flux": cumulative_diffusive_flux,
        "cumulative_source_integral": cumulative_source,
        "balance_residual": residual,
        "clipped_integral": clipped_integral,
    }


def _write_history_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return write_text_file(path, buffer.getvalue())


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return write_json_file(path, payload)


def _write_text(path: Path, text: str) -> Path:
    return write_text_file(path, text)
