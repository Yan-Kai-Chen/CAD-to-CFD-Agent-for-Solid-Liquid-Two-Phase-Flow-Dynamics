"""Practical 1D/2D heat diffusion mini solvers for FastFluent S2."""

from __future__ import annotations

import math
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


def demo_heat_diffusion_1d_case() -> dict[str, Any]:
    return {
        "case_id": "heat_diffusion_1d_demo",
        "case_name": "Public 1D Heat Diffusion Demo",
        "length_m": 0.02,
        "nx": 41,
        "thermal_diffusivity_m2_s": 1.25e-7,
        "time_step_s": 0.2,
        "steps": 80,
        "output_interval": 10,
        "initial_temperature_K": 293.15,
        "fixed_temperature_left_K": 373.15,
        "fixed_temperature_right_K": 293.15,
        "left_bc": "fixed_temperature",
        "right_bc": "fixed_temperature",
        "front_threshold_K": 333.15,
    }


def demo_heat_diffusion_2d_case() -> dict[str, Any]:
    return {
        "case_id": "heat_diffusion_2d_demo",
        "case_name": "Public 2D Heat Diffusion Demo",
        "length_x_m": 0.02,
        "length_y_m": 0.01,
        "nx": 31,
        "ny": 17,
        "thermal_diffusivity_m2_s": 1.25e-7,
        "time_step_s": 0.1,
        "steps": 60,
        "output_interval": 10,
        "initial_temperature_K": 293.15,
        "heated_wall_temperature_K": 353.15,
        "right_wall_temperature_K": 293.15,
    }


def run_heat_diffusion_1d_case(case: dict[str, Any] | None = None, output_dir: str | Path = "heat_diffusion_1d") -> dict[str, Any]:
    payload = dict(case or demo_heat_diffusion_1d_case())
    target = Path(output_dir)
    nx = int(payload["nx"])
    length = float(payload["length_m"])
    alpha = float(payload["thermal_diffusivity_m2_s"])
    dt = float(payload["time_step_s"])
    steps = int(payload["steps"])
    output_interval = max(1, int(payload.get("output_interval", 10)))
    dx = length / (nx - 1)
    fo = alpha * dt / (dx * dx)
    warnings: list[str] = []
    blocking_errors: list[str] = []
    status = "pass"
    if nx < 3:
        status = "block"
        blocking_errors.append("nx must be at least 3.")
    if fo > 0.5:
        status = "block"
        blocking_errors.append(f"Explicit 1D heat diffusion Fourier number is unstable: Fo={fo}.")

    x = [i * dx for i in range(nx)]
    field = [float(payload["initial_temperature_K"]) for _ in range(nx)]
    _apply_1d_boundary(field, payload)
    history = [_heat_history_row(0, 0.0, x, field, payload)]
    if status != "block":
        for step in range(1, steps + 1):
            old = list(field)
            for i in range(1, nx - 1):
                field[i] = old[i] + fo * (old[i + 1] - 2.0 * old[i] + old[i - 1])
            _apply_1d_boundary(field, payload)
            if step % output_interval == 0 or step == steps:
                history.append(_heat_history_row(step, step * dt, x, field, payload))
    summary = min_max_mean(field)
    qoi = {
        "min_temperature_K": summary["min"],
        "max_temperature_K": summary["max"],
        "mean_temperature_K": summary["mean"],
        "thermal_front_position_m": _front_position(x, field, float(payload.get("front_threshold_K", summary["mean"]))),
        "energy_proxy_K_m": sum(field) * dx,
        "nonfinite_count": nx - int(summary["finite_count"]),
    }
    stability = {
        "fourier_number": fo,
        "recommended_max_fourier_number": 0.5,
        "stability_flag": "stable" if fo <= 0.5 else "unstable",
        "scheme": "explicit_central_difference",
    }
    final_rows = [{"x_m": x_value, "temperature_K": temp} for x_value, temp in zip(x, field)]
    case_path = write_json(target / "input_case.json", payload)
    history_path = write_csv(target / "temperature_history.csv", history)
    field_path = write_csv(target / "temperature_field_final.csv", final_rows)
    qoi_path = write_json(target / "qoi_summary.json", qoi)
    stability_path = write_json(target / "stability_summary.json", stability)
    benchmark = _heat_1d_benchmark(x, field, payload)
    result = build_practical_native_result(
        case_id=str(payload["case_id"]),
        case_name=str(payload["case_name"]),
        module="practical_heat_diffusion",
        kernel="heat_diffusion_1d_explicit",
        status=status,
        input_summary={"case_file": str(case_path)},
        grid_summary={"dimension": 1, "nx": nx, "dx_m": dx, "length_m": length},
        time_summary={"time_step_s": dt, "steps": steps, "final_time_s": dt * steps},
        stability_summary=stability,
        qoi_summary=qoi,
        field_outputs=[{"path": str(field_path), "kind": "temperature_field_final_csv"}],
        history_outputs=[{"path": str(history_path), "kind": "temperature_history_csv"}],
        benchmark_comparison=benchmark,
        warnings=warnings,
        blocking_errors=blocking_errors,
        limitations=LIMITATIONS,
        metadata={"qoi_summary": str(qoi_path), "stability_summary": str(stability_path)},
    )
    write_practical_native_result(result, target)
    write_text(target / "simulation_summary.md", _heat_summary_markdown(result))
    return result


def run_heat_diffusion_2d_case(case: dict[str, Any] | None = None, output_dir: str | Path = "heat_diffusion_2d") -> dict[str, Any]:
    payload = dict(case or demo_heat_diffusion_2d_case())
    target = Path(output_dir)
    nx = int(payload["nx"])
    ny = int(payload["ny"])
    lx = float(payload["length_x_m"])
    ly = float(payload["length_y_m"])
    alpha = float(payload["thermal_diffusivity_m2_s"])
    dt = float(payload["time_step_s"])
    steps = int(payload["steps"])
    output_interval = max(1, int(payload.get("output_interval", 10)))
    dx = lx / (nx - 1)
    dy = ly / (ny - 1)
    fox = alpha * dt / (dx * dx)
    foy = alpha * dt / (dy * dy)
    status = "pass"
    blocking_errors: list[str] = []
    if nx < 3 or ny < 3:
        status = "block"
        blocking_errors.append("nx and ny must be at least 3.")
    if fox + foy > 0.5:
        status = "block"
        blocking_errors.append(f"Explicit 2D heat diffusion stability limit exceeded: Fo_x+Fo_y={fox + foy}.")
    field = [[float(payload["initial_temperature_K"]) for _ in range(nx)] for _ in range(ny)]
    _apply_2d_boundary(field, payload)
    history = [_heat2d_history_row(0, 0.0, field)]
    if status != "block":
        for step in range(1, steps + 1):
            old = [row[:] for row in field]
            for j in range(1, ny - 1):
                for i in range(1, nx - 1):
                    field[j][i] = old[j][i] + fox * (old[j][i + 1] - 2.0 * old[j][i] + old[j][i - 1]) + foy * (old[j + 1][i] - 2.0 * old[j][i] + old[j - 1][i])
            _apply_2d_boundary(field, payload)
            if step % output_interval == 0 or step == steps:
                history.append(_heat2d_history_row(step, step * dt, field))
    flat = [value for row in field for value in row]
    summary = min_max_mean(flat)
    qoi = {
        "min_temperature_K": summary["min"],
        "max_temperature_K": summary["max"],
        "mean_temperature_K": summary["mean"],
        "energy_proxy_K_m2": sum(flat) * dx * dy,
        "nonfinite_count": len(flat) - int(summary["finite_count"]),
    }
    stability = {
        "fourier_number_x": fox,
        "fourier_number_y": foy,
        "fourier_number_sum": fox + foy,
        "recommended_max_sum": 0.5,
        "stability_flag": "stable" if fox + foy <= 0.5 else "unstable",
        "scheme": "explicit_central_difference_2d",
    }
    rows = []
    for j, row in enumerate(field):
        for i, value in enumerate(row):
            rows.append({"x_m": i * dx, "y_m": j * dy, "temperature_K": value})
    case_path = write_json(target / "input_case.json", payload)
    field_path = write_csv(target / "temperature_field.csv", rows)
    history_path = write_csv(target / "temperature_history.csv", history)
    qoi_path = write_json(target / "qoi_summary.json", qoi)
    stability_path = write_json(target / "stability_summary.json", stability)
    result = build_practical_native_result(
        case_id=str(payload["case_id"]),
        case_name=str(payload["case_name"]),
        module="practical_heat_diffusion",
        kernel="heat_diffusion_2d_explicit",
        status=status,
        input_summary={"case_file": str(case_path)},
        grid_summary={"dimension": 2, "nx": nx, "ny": ny, "dx_m": dx, "dy_m": dy},
        time_summary={"time_step_s": dt, "steps": steps, "final_time_s": dt * steps},
        stability_summary=stability,
        qoi_summary=qoi,
        field_outputs=[{"path": str(field_path), "kind": "temperature_field_csv"}],
        history_outputs=[{"path": str(history_path), "kind": "temperature_history_csv"}],
        benchmark_comparison={"reference_type": "trend_only", "l2_error": None, "max_error": None},
        warnings=[],
        blocking_errors=blocking_errors,
        limitations=LIMITATIONS,
        metadata={"qoi_summary": str(qoi_path), "stability_summary": str(stability_path)},
    )
    write_practical_native_result(result, target)
    write_text(target / "simulation_summary.md", _heat_summary_markdown(result))
    return result


def _apply_1d_boundary(field: list[float], case: dict[str, Any]) -> None:
    if case.get("left_bc") == "insulated":
        field[0] = field[1]
    else:
        field[0] = float(case["fixed_temperature_left_K"])
    if case.get("right_bc") == "insulated":
        field[-1] = field[-2]
    else:
        field[-1] = float(case["fixed_temperature_right_K"])


def _apply_2d_boundary(field: list[list[float]], case: dict[str, Any]) -> None:
    left = float(case["heated_wall_temperature_K"])
    right = float(case["right_wall_temperature_K"])
    ny = len(field)
    nx = len(field[0])
    for j in range(ny):
        field[j][0] = left
        field[j][nx - 1] = right
    for i in range(nx):
        field[0][i] = field[1][i]
        field[ny - 1][i] = field[ny - 2][i]
    field[0][0] = left
    field[ny - 1][0] = left
    field[0][nx - 1] = right
    field[ny - 1][nx - 1] = right


def _heat_history_row(step: int, time_s: float, x: list[float], field: list[float], case: dict[str, Any]) -> dict[str, Any]:
    summary = min_max_mean(field)
    dx = x[1] - x[0] if len(x) > 1 else 1.0
    threshold = float(case.get("front_threshold_K", summary["mean"]))
    return {
        "step": step,
        "time_s": time_s,
        "min_temperature_K": summary["min"],
        "max_temperature_K": summary["max"],
        "mean_temperature_K": summary["mean"],
        "energy_proxy_K_m": sum(field) * dx,
        "thermal_front_position_m": _front_position(x, field, threshold),
    }


def _heat2d_history_row(step: int, time_s: float, field: list[list[float]]) -> dict[str, Any]:
    flat = [value for row in field for value in row]
    summary = min_max_mean(flat)
    return {"step": step, "time_s": time_s, "min_temperature_K": summary["min"], "max_temperature_K": summary["max"], "mean_temperature_K": summary["mean"]}


def _front_position(x: list[float], field: list[float], threshold: float) -> float:
    active = [x_value for x_value, value in zip(x, field) if value >= threshold]
    return max(active) if active else 0.0


def _heat_1d_benchmark(x: list[float], field: list[float], case: dict[str, Any]) -> dict[str, Any]:
    if case.get("left_bc") != "fixed_temperature" or case.get("right_bc") != "fixed_temperature":
        return {"reference_type": "trend_only", "l2_error": None, "max_error": None}
    left = float(case["fixed_temperature_left_K"])
    right = float(case["fixed_temperature_right_K"])
    length = float(case["length_m"])
    reference = [left + (right - left) * value / length for value in x]
    errors = [field_value - ref_value for field_value, ref_value in zip(field, reference)]
    l2 = math.sqrt(sum(error * error for error in errors) / len(errors))
    return {"reference_type": "fixed_end_steady_linear_profile", "l2_error": l2, "max_error": max(abs(error) for error in errors)}


def _heat_summary_markdown(result: dict[str, Any]) -> str:
    qoi = result["qoi_summary"]
    stability = result["stability_summary"]
    return "\n".join(
        [
            f"# {result['case_name']}",
            "",
            f"- Status: `{result['status']}`",
            f"- Kernel: `{result['kernel']}`",
            f"- Min temperature K: `{qoi.get('min_temperature_K')}`",
            f"- Max temperature K: `{qoi.get('max_temperature_K')}`",
            f"- Mean temperature K: `{qoi.get('mean_temperature_K')}`",
            f"- Stability flag: `{stability.get('stability_flag')}`",
            "",
            "This is a FastFluent-native practical mini simulation. It does not launch Fluent or prove high-fidelity CFD accuracy.",
            "",
        ]
    )
