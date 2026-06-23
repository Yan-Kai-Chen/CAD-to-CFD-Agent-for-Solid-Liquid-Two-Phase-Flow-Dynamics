"""Practical 1D scalar advection-diffusion utilities for FastFluent S2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .practical_native_artifacts import (
    LIMITATIONS,
    build_practical_native_result,
    min_max_mean,
    write_csv,
    write_json,
    write_practical_native_result,
    write_text,
)


def demo_scalar_transport_case(*, bounded: bool = False, clamp_enabled: bool = False) -> dict[str, Any]:
    return {
        "case_id": "bounded_scalar_transport_demo" if bounded else "scalar_advection_diffusion_1d_demo",
        "case_name": "Public Bounded Scalar Transport Demo" if bounded else "Public 1D Scalar Advection-Diffusion Demo",
        "length_m": 1.0,
        "nx": 101,
        "velocity_m_s": 0.2,
        "diffusivity_m2_s": 0.001,
        "time_step_s": 0.01,
        "steps": 80,
        "output_interval": 10,
        "initial_patch_min_m": 0.15,
        "initial_patch_max_m": 0.35,
        "initial_patch_value": 1.0,
        "inlet_value": 0.0,
        "bounded": bounded,
        "clamp_enabled": clamp_enabled,
        "bounded_min": 0.0,
        "bounded_max": 1.0,
        "front_threshold": 0.5,
    }


def run_scalar_advection_diffusion_1d_case(case: dict[str, Any] | None = None, output_dir: str | Path = "scalar_advection_diffusion_1d") -> dict[str, Any]:
    payload = dict(case or demo_scalar_transport_case())
    target = Path(output_dir)
    nx = int(payload["nx"])
    length = float(payload["length_m"])
    dx = length / (nx - 1)
    u = float(payload["velocity_m_s"])
    diffusivity = float(payload["diffusivity_m2_s"])
    dt = float(payload["time_step_s"])
    steps = int(payload["steps"])
    output_interval = max(1, int(payload.get("output_interval", 10)))
    cfl = abs(u) * dt / dx
    diffnum = diffusivity * dt / (dx * dx)
    status = "pass"
    warnings: list[str] = []
    blocking_errors: list[str] = []
    if cfl > 1.0 or diffnum > 0.5:
        status = "block"
        blocking_errors.append(f"Scalar transport explicit stability limit exceeded: CFL={cfl}, diffusion_number={diffnum}.")
    x = [i * dx for i in range(nx)]
    phi = [
        float(payload["initial_patch_value"]) if float(payload["initial_patch_min_m"]) <= value <= float(payload["initial_patch_max_m"]) else 0.0
        for value in x
    ]
    initial_mass = _scalar_mass(phi, dx)
    history = [_history_row(0, 0.0, x, phi, initial_mass, payload)]
    if status != "block":
        for step in range(1, steps + 1):
            old = list(phi)
            for i in range(1, nx - 1):
                if u >= 0:
                    adv = -cfl * (old[i] - old[i - 1])
                else:
                    adv = cfl * (old[i + 1] - old[i])
                diff = diffnum * (old[i + 1] - 2.0 * old[i] + old[i - 1])
                phi[i] = old[i] + adv + diff
            phi[0] = float(payload.get("inlet_value", 0.0))
            phi[-1] = phi[-2]
            if payload.get("bounded") and payload.get("clamp_enabled"):
                lo = float(payload.get("bounded_min", 0.0))
                hi = float(payload.get("bounded_max", 1.0))
                phi = [min(max(value, lo), hi) for value in phi]
            if step % output_interval == 0 or step == steps:
                history.append(_history_row(step, step * dt, x, phi, initial_mass, payload))
    qoi = _qoi(x, phi, initial_mass, payload)
    stability = {
        "cfl": cfl,
        "diffusion_number": diffnum,
        "recommended_max_cfl": 1.0,
        "recommended_max_diffusion_number": 0.5,
        "stability_flag": "stable" if cfl <= 1.0 and diffnum <= 0.5 else "unstable",
        "scheme": "upwind_advection_explicit_diffusion",
    }
    boundedness = {
        "bounded": bool(payload.get("bounded")),
        "clamp_enabled": bool(payload.get("clamp_enabled")),
        "bounded_min": payload.get("bounded_min"),
        "bounded_max": payload.get("bounded_max"),
        "boundedness_violation_count": qoi["boundedness_violation_count"],
    }
    field_rows = [{"x_m": x_value, "phi": value} for x_value, value in zip(x, phi)]
    case_path = write_json(target / "input_case.json", payload)
    field_path = write_csv(target / "scalar_field_final.csv", field_rows)
    history_path = write_csv(target / "scalar_history.csv", history)
    qoi_path = write_json(target / "qoi_summary.json", qoi)
    bounded_path = write_json(target / "boundedness_summary.json", boundedness)
    stability_path = write_json(target / "stability_summary.json", stability)
    result = build_practical_native_result(
        case_id=str(payload["case_id"]),
        case_name=str(payload["case_name"]),
        module="practical_scalar_transport",
        kernel="scalar_advection_diffusion_1d",
        status=status,
        input_summary={"case_file": str(case_path)},
        grid_summary={"dimension": 1, "nx": nx, "dx_m": dx, "length_m": length},
        time_summary={"time_step_s": dt, "steps": steps, "final_time_s": steps * dt},
        stability_summary=stability | boundedness,
        qoi_summary=qoi,
        field_outputs=[{"path": str(field_path), "kind": "scalar_field_final_csv"}],
        history_outputs=[{"path": str(history_path), "kind": "scalar_history_csv"}],
        benchmark_comparison={"reference_type": "boundedness_and_mass_trend", "l2_error": None, "max_error": None},
        warnings=warnings,
        blocking_errors=blocking_errors,
        limitations=LIMITATIONS + ["This is a scalar transport proxy; it is not a full VOF, species, or momentum solver."],
        metadata={"qoi_summary": str(qoi_path), "boundedness_summary": str(bounded_path), "stability_summary": str(stability_path)},
    )
    write_practical_native_result(result, target)
    write_text(target / "simulation_summary.md", _summary_markdown(result))
    return result


def run_bounded_scalar_transport_comparison(output_dir: str | Path = "bounded_scalar_transport") -> dict[str, Any]:
    target = Path(output_dir)
    without_case = demo_scalar_transport_case(bounded=True, clamp_enabled=False)
    without_case["case_id"] = "bounded_scalar_without_clamp"
    with_case = demo_scalar_transport_case(bounded=True, clamp_enabled=True)
    with_case["case_id"] = "bounded_scalar_with_clamp"
    without_result = run_scalar_advection_diffusion_1d_case(without_case, target / "without_clamp")
    with_result = run_scalar_advection_diffusion_1d_case(with_case, target / "with_clamp")
    comparison = {
        "schema_version": "fromcad2cfd_fastfluent_bounded_scalar_comparison_v1",
        "without_clamp_status": without_result["status"],
        "with_clamp_status": with_result["status"],
        "without_clamp_violation_count": without_result["qoi_summary"]["boundedness_violation_count"],
        "with_clamp_violation_count": with_result["qoi_summary"]["boundedness_violation_count"],
        "mass_relative_change_without_clamp": without_result["qoi_summary"]["phi_mass_relative_change"],
        "mass_relative_change_with_clamp": with_result["qoi_summary"]["phi_mass_relative_change"],
        "fluent_launched": False,
    }
    write_json(target / "comparison_summary.json", comparison)
    write_text(target / "simulation_summary.md", "# Bounded Scalar Transport Comparison\n\nThis compares clamped and unclamped scalar proxy transport. It is not a full VOF solver.\n")
    return comparison


def _scalar_mass(phi: list[float], dx: float) -> float:
    return sum(phi) * dx


def _qoi(x: list[float], phi: list[float], initial_mass: float, case: dict[str, Any]) -> dict[str, Any]:
    dx = x[1] - x[0] if len(x) > 1 else 1.0
    mass = _scalar_mass(phi, dx)
    lo = float(case.get("bounded_min", 0.0))
    hi = float(case.get("bounded_max", 1.0))
    bounded = bool(case.get("bounded"))
    violations = sum(1 for value in phi if bounded and (value < lo or value > hi))
    summary = min_max_mean(phi)
    return {
        "phi_min": summary["min"],
        "phi_max": summary["max"],
        "phi_mass_initial": initial_mass,
        "phi_mass_final": mass,
        "phi_mass_relative_change": 0.0 if abs(initial_mass) < 1.0e-30 else (mass - initial_mass) / initial_mass,
        "boundedness_violation_count": violations,
        "front_position_m": _front_position(x, phi, float(case.get("front_threshold", 0.5))),
        "nonfinite_count": len(phi) - int(summary["finite_count"]),
    }


def _history_row(step: int, time_s: float, x: list[float], phi: list[float], initial_mass: float, case: dict[str, Any]) -> dict[str, Any]:
    qoi = _qoi(x, phi, initial_mass, case)
    return {"step": step, "time_s": time_s, **qoi}


def _front_position(x: list[float], phi: list[float], threshold: float) -> float:
    active = [x_value for x_value, value in zip(x, phi) if value >= threshold]
    return max(active) if active else 0.0


def _summary_markdown(result: dict[str, Any]) -> str:
    qoi = result["qoi_summary"]
    return "\n".join(
        [
            f"# {result['case_name']}",
            "",
            f"- Status: `{result['status']}`",
            f"- CFL: `{result['stability_summary'].get('cfl')}`",
            f"- Diffusion number: `{result['stability_summary'].get('diffusion_number')}`",
            f"- Phi min/max: `{qoi.get('phi_min')}` / `{qoi.get('phi_max')}`",
            f"- Mass relative change: `{qoi.get('phi_mass_relative_change')}`",
            "",
            "This is a FastFluent-native scalar proxy. It does not replace VOF, species transport, or Fluent.",
            "",
        ]
    )
