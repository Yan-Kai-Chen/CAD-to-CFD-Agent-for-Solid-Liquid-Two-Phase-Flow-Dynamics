"""Bounded source-term toy models for FastFluent S2."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .practical_native_artifacts import (
    LIMITATIONS,
    build_practical_native_result,
    write_csv,
    write_json,
    write_practical_native_result,
    write_text,
)


def demo_source_term_case(*, ramp_enabled: bool = True, clamp_enabled: bool = True) -> dict[str, Any]:
    return {
        "case_id": "source_term_ramp_clamp_demo",
        "case_name": "Public Source-Term Ramp Clamp Demo",
        "source_mode": "phase_change_interval_source",
        "initial_temperature_K": 332.0,
        "density_kg_m3": 900.0,
        "specific_heat_J_kgK": 2200.0,
        "time_step_s": 0.05,
        "steps": 120,
        "source_strength_W_m3": 8.0e7,
        "melting_temperature_min_K": 330.0,
        "melting_temperature_max_K": 345.0,
        "ramp_enabled": ramp_enabled,
        "ramp_time_s": 2.0,
        "clamp_enabled": clamp_enabled,
        "source_min_W_m3": 0.0,
        "source_max_W_m3": 2.5e7,
        "temperature_min_K": 250.0,
        "temperature_max_K": 380.0,
        "nan_guard": True,
    }


def run_source_term_cell_model(case: dict[str, Any] | None = None, output_dir: str | Path = "source_term_cell_model") -> dict[str, Any]:
    payload = dict(case or demo_source_term_case())
    target = Path(output_dir)
    dt = float(payload["time_step_s"])
    steps = int(payload["steps"])
    rho_cp = float(payload["density_kg_m3"]) * float(payload["specific_heat_J_kgK"])
    temperature = float(payload["initial_temperature_K"])
    history: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocking_errors: list[str] = []
    source_integral = 0.0
    max_source_jump = 0.0
    previous_source = 0.0
    nonfinite_count = 0
    max_temperature = temperature
    for step in range(steps + 1):
        time_s = step * dt
        raw_source = source_value(temperature, time_s, payload)
        controlled_source = apply_source_controls(raw_source, time_s, payload)
        if not math.isfinite(temperature) or not math.isfinite(controlled_source):
            nonfinite_count += 1
            if payload.get("nan_guard"):
                controlled_source = 0.0
                warnings.append("NaN guard suppressed a nonfinite source or temperature.")
        if step > 0:
            source_integral += controlled_source * dt
            max_source_jump = max(max_source_jump, abs(controlled_source - previous_source))
        history.append({"step": step, "time_s": time_s, "temperature_K": temperature, "raw_source_W_m3": raw_source, "controlled_source_W_m3": controlled_source})
        previous_source = controlled_source
        if step == steps:
            break
        temperature += dt * controlled_source / rho_cp
        if payload.get("clamp_enabled"):
            temperature = min(max(temperature, float(payload["temperature_min_K"])), float(payload["temperature_max_K"]))
        max_temperature = max(max_temperature, temperature)
    overshoot = max(0.0, max_temperature - float(payload["temperature_max_K"]))
    if nonfinite_count:
        blocking_errors.append("Nonfinite source-term values were detected.")
    status = "block" if blocking_errors else ("warn" if warnings or overshoot > 0.0 else "pass")
    qoi = {
        "max_temperature_K": max_temperature,
        "final_temperature_K": temperature,
        "overshoot_K": overshoot,
        "source_integral_J_m3": source_integral,
        "source_jump_max_W_m3": max_source_jump,
        "nonfinite_count": nonfinite_count,
        "stability_flag": "guarded" if payload.get("ramp_enabled") or payload.get("clamp_enabled") else "unguarded",
    }
    stability = {
        "rho_cp_J_m3K": rho_cp,
        "temperature_increment_per_step_at_source_strength_K": float(payload["source_strength_W_m3"]) * dt / rho_cp,
        "ramp_enabled": bool(payload.get("ramp_enabled")),
        "clamp_enabled": bool(payload.get("clamp_enabled")),
        "nan_guard": bool(payload.get("nan_guard")),
    }
    case_path = write_json(target / "input_case.json", payload)
    history_path = write_csv(target / "source_history.csv", history)
    temperature_history_path = write_csv(target / "temperature_history.csv", [{"step": row["step"], "time_s": row["time_s"], "temperature_K": row["temperature_K"]} for row in history])
    qoi_path = write_json(target / "qoi_summary.json", qoi)
    stability_path = write_json(target / "stability_summary.json", stability)
    result = build_practical_native_result(
        case_id=str(payload["case_id"]),
        case_name=str(payload["case_name"]),
        module="practical_source_terms",
        kernel=str(payload["source_mode"]),
        status=status,
        input_summary={"case_file": str(case_path)},
        grid_summary={"dimension": 0, "cell_model": True},
        time_summary={"time_step_s": dt, "steps": steps, "final_time_s": steps * dt},
        stability_summary=stability,
        qoi_summary=qoi,
        field_outputs=[],
        history_outputs=[{"path": str(history_path), "kind": "source_history_csv"}, {"path": str(temperature_history_path), "kind": "temperature_history_csv"}],
        benchmark_comparison={"reference_type": "ramp_clamp_control_comparison", "l2_error": None, "max_error": None},
        warnings=warnings,
        blocking_errors=blocking_errors,
        limitations=LIMITATIONS + ["This is a source-term toy model, not Fluent source code or a physical phase-change solver."],
        metadata={"qoi_summary": str(qoi_path), "stability_summary": str(stability_path)},
    )
    write_practical_native_result(result, target)
    write_text(target / "simulation_summary.md", _source_summary_markdown(result))
    return result


def run_source_ramp_clamp_comparison(output_dir: str | Path = "source_term_ramp_clamp") -> dict[str, Any]:
    target = Path(output_dir)
    no_control = demo_source_term_case(ramp_enabled=False, clamp_enabled=False)
    no_control["case_id"] = "source_no_ramp_no_clamp"
    guarded = demo_source_term_case(ramp_enabled=True, clamp_enabled=True)
    guarded["case_id"] = "source_with_ramp_and_clamp"
    result_no_control = run_source_term_cell_model(no_control, target / "no_ramp_no_clamp")
    result_guarded = run_source_term_cell_model(guarded, target / "with_ramp_and_clamp")
    comparison = {
        "schema_version": "fromcad2cfd_fastfluent_source_ramp_clamp_comparison_v1",
        "no_ramp_no_clamp_status": result_no_control["status"],
        "with_ramp_and_clamp_status": result_guarded["status"],
        "source_jump_no_ramp_no_clamp_W_m3": result_no_control["qoi_summary"]["source_jump_max_W_m3"],
        "source_jump_with_ramp_and_clamp_W_m3": result_guarded["qoi_summary"]["source_jump_max_W_m3"],
        "max_temperature_no_ramp_no_clamp_K": result_no_control["qoi_summary"]["max_temperature_K"],
        "max_temperature_with_ramp_and_clamp_K": result_guarded["qoi_summary"]["max_temperature_K"],
        "fluent_launched": False,
    }
    write_json(target / "comparison_summary.json", comparison)
    write_text(target / "simulation_summary.md", "# Source-Term Ramp Clamp Comparison\n\nThis compares native guarded and unguarded source updates. It is not Fluent UDF code.\n")
    return comparison


def source_value(temperature_K: float, time_s: float, case: dict[str, Any]) -> float:
    del time_s
    mode = str(case.get("source_mode", "constant_source"))
    source = float(case.get("source_strength_W_m3", 0.0))
    if mode == "constant_source":
        return source
    if mode == "temperature_window_source":
        return source if float(case["temperature_min_K"]) <= temperature_K <= float(case["temperature_max_K"]) else 0.0
    if mode == "phase_change_interval_source":
        return source if float(case["melting_temperature_min_K"]) <= temperature_K <= float(case["melting_temperature_max_K"]) else 0.0
    raise ValueError(f"Unsupported source_mode: {mode}")


def apply_source_controls(source: float, time_s: float, case: dict[str, Any]) -> float:
    value = source
    if case.get("ramp_enabled"):
        ramp_time = max(float(case.get("ramp_time_s", 0.0)), 1.0e-30)
        value *= min(1.0, max(0.0, time_s / ramp_time))
    if case.get("clamp_enabled"):
        value = min(max(value, float(case.get("source_min_W_m3", value))), float(case.get("source_max_W_m3", value)))
    return value


def _source_summary_markdown(result: dict[str, Any]) -> str:
    qoi = result["qoi_summary"]
    return "\n".join(
        [
            f"# {result['case_name']}",
            "",
            f"- Status: `{result['status']}`",
            f"- Max temperature K: `{qoi.get('max_temperature_K')}`",
            f"- Source integral J/m3: `{qoi.get('source_integral_J_m3')}`",
            f"- Max source jump W/m3: `{qoi.get('source_jump_max_W_m3')}`",
            "",
            "This is a native source-term toy model. It does not generate UDF source or Fluent commands.",
            "",
        ]
    )
