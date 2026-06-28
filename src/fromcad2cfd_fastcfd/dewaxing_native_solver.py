"""FastFluent-native reduced-order dewaxing solver.

The solver is a bounded, public-safe native computation for dewaxing case-study
evidence. It solves a 2D transient heat-conduction problem with an effective
heat-capacity enthalpy treatment for wax melting. It does not launch Fluent or
edit Fluent case/data files.
"""

from __future__ import annotations

from collections import deque
import math
from pathlib import Path
from typing import Any

from fromcad2cfd_postprocessing.dewaxing_result_pack import validate_dewaxing_result_pack

from .file_io import ensure_dir, write_json_file, write_text_file
from .practical_native_artifacts import write_csv


DEWAXING_NATIVE_RESULT_SCHEMA_VERSION = "fastfluent_dewaxing_native_result_v1"
DEWAXING_NATIVE_QOI_SCHEMA_VERSION = "fastfluent_dewaxing_native_qoi_v1"
DEWAXING_NATIVE_HARDENING_SCHEMA_VERSION = "fastfluent_dewaxing_native_hardening_v1"

LIMITATIONS = [
    "This is a FastFluent-native reduced-order dewaxing computation.",
    "It solves 2D heat conduction with effective heat-capacity phase change only.",
    "It does not solve Navier-Stokes momentum, turbulence, VOF interface reconstruction, or Fluent pressure fields.",
    "Drainage and pressure-risk outputs are reduced-order screening proxies.",
    "It does not launch Fluent, call PyFluent, emit UDF source, or edit Fluent case/data files.",
    "It is valid for agent screening and comparison against reviewed Fluent evidence, not final CFD validation.",
]


def demo_dewaxing_native_case() -> dict[str, Any]:
    """Return the default public-safe native dewaxing reduced-order case."""

    return {
        "case_id": "dewaxing_native_reduced_order_demo",
        "case_name": "FastFluent Native Dewaxing Reduced-Order Demo",
        "domain": {
            "thickness_m": 0.011,
            "height_m": 0.09,
            "shell_thickness_m": 0.0015,
            "nx": 17,
            "ny": 13,
        },
        "time": {
            "time_step_s": 0.08,
            "final_time_s": 420.0,
            "output_interval_s": 2.0,
            "snapshot_times_s": [0.0, 4.0, 100.7, 409.0, 420.0],
        },
        "initial": {
            "temperature_K": 293.15,
        },
        "steam_boundary": {
            "temperature_K": 443.15,
            "heat_transfer_coefficient_W_m2K": 900.0,
        },
        "shell": {
            "density_kg_m3": 2500.0,
            "specific_heat_J_kgK": 850.0,
            "thermal_conductivity_W_mK": 1.3,
            "young_modulus_Pa": 1.0e10,
            "thermal_expansion_1_K": 6.0e-6,
            "poisson_ratio": 0.25,
        },
        "wax": {
            "density_solid_kg_m3": 900.0,
            "density_liquid_kg_m3": 780.0,
            "specific_heat_J_kgK": 2200.0,
            "thermal_conductivity_solid_W_mK": 0.25,
            "thermal_conductivity_liquid_W_mK": 0.18,
            "latent_heat_J_kg": 60000.0,
            "melting_temperature_min_K": 330.15,
            "melting_temperature_max_K": 345.15,
            "liquid_fraction_threshold": 0.995,
            "drainage_liquid_threshold": 0.5,
        },
        "acceptance": {
            "max_energy_balance_relative_error": 0.08,
            "full_melt_time_reference_s": 409.0,
            "full_melt_time_warning_relative_error": 0.35,
            "full_melt_time_pass_relative_error": 0.20,
            "early_reference_time_s": 4.0,
            "dominant_risk_reference_time_s": 100.7,
            "dominant_risk_warning_relative_error": 0.60,
        },
        "metadata": {
            "public_safe": True,
            "fluent_launched": False,
            "purpose": "FastFluent-native reduced-order dewaxing evidence for agent screening.",
        },
    }


def run_dewaxing_native_solver(
    case: dict[str, Any] | None = None,
    *,
    output_dir: str | Path,
    comparison_pack: str | Path | None = None,
) -> dict[str, Any]:
    """Run the native reduced-order dewaxing solver and write artifacts."""

    payload = _normalize_case(case or demo_dewaxing_native_case())
    root = Path(output_dir)
    ensure_dir(root)
    artifacts: dict[str, str] = {
        "case": str(root / "dewaxing_native_case.json"),
        "history": str(root / "dewaxing_native_history.csv"),
        "final_field": str(root / "dewaxing_native_final_field.csv"),
        "snapshot_field": str(root / "dewaxing_native_snapshots.csv"),
        "qoi": str(root / "dewaxing_native_qoi.json"),
        "hardening_summary": str(root / "hardening_summary.json"),
        "comparison": str(root / "dewaxing_native_comparison.json"),
        "report": str(root / "dewaxing_native_report.md"),
        "status": str(root / "dewaxing_native_status.json"),
    }

    validation = _validate_case(payload)
    if validation["blocking_errors"]:
        result = _blocked_result(payload, root=root, artifacts=artifacts, validation=validation, comparison_pack=comparison_pack)
        _write_outputs(root, result, artifacts=artifacts, case=payload, history=[], final_rows=[], snapshot_rows=[])
        return result

    solution = _solve(payload)
    comparison = _compare_with_pack(solution["qoi"]["metrics"], comparison_pack, payload)
    hardening = _hardening_summary(solution["qoi"]["metrics"], validation, comparison, payload)
    qoi = dict(solution["qoi"])
    qoi["status"] = hardening["status"]
    qoi["comparison"] = comparison
    decision = _agent_decision(hardening, qoi, comparison)
    result_status = "success" if hardening["status"] in {"passed", "warning"} else "failed"
    result = {
        "schema_version": DEWAXING_NATIVE_RESULT_SCHEMA_VERSION,
        "status": result_status,
        "backend": "fastfluent_native",
        "operation": "run_dewaxing_native_solver",
        "case_id": payload["case_id"],
        "case_type": "thermal.dewaxing_native_reduced_order",
        "quality_status": hardening["status"],
        "outputs": {
            "solver_execution": "fastfluent_dewaxing_native_reduced_order_solver",
            "artifacts": artifacts,
            "qoi": qoi,
            "hardening_summary": hardening,
            "comparison": comparison,
        },
        "agent_decision": decision,
        "warnings": hardening.get("warnings", []),
        "blocking_errors": hardening.get("blocking_errors", []),
        "limitations": list(LIMITATIONS),
        "metadata": {
            "output_dir": str(root),
            "comparison_pack": str(comparison_pack) if comparison_pack else None,
            "fluent_launched": False,
            "new_fluent_calculation": False,
        },
    }
    _write_outputs(
        root,
        result,
        artifacts=artifacts,
        case=payload,
        history=solution["history"],
        final_rows=solution["final_rows"],
        snapshot_rows=solution["snapshot_rows"],
    )
    return result


def dewaxing_native_solver_markdown(result: dict[str, Any]) -> str:
    """Render a native dewaxing result report."""

    outputs = result.get("outputs", {}) if isinstance(result.get("outputs"), dict) else {}
    qoi = outputs.get("qoi", {}) if isinstance(outputs.get("qoi"), dict) else {}
    metrics = qoi.get("metrics", {}) if isinstance(qoi.get("metrics"), dict) else {}
    comparison = outputs.get("comparison", {}) if isinstance(outputs.get("comparison"), dict) else {}
    lines = [
        "# FastFluent Native Dewaxing Reduced-Order Solver",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Quality status: `{result.get('quality_status')}`",
        f"- Case ID: `{result.get('case_id')}`",
        f"- Fluent launched: `{result.get('metadata', {}).get('fluent_launched')}`",
        f"- New Fluent calculation: `{result.get('metadata', {}).get('new_fluent_calculation')}`",
        "",
        "## Native QoI",
        "",
        f"- Final average liquid fraction: `{metrics.get('final_avg_liquid_fraction')}`",
        f"- Predicted full melt time s: `{metrics.get('predicted_full_melt_time_s')}`",
        f"- Dominant native risk time s: `{metrics.get('dominant_risk_time_s')}`",
        f"- Peak pressure risk proxy: `{metrics.get('peak_pressure_risk_proxy')}`",
        f"- Early shell stress proxy MPa: `{metrics.get('early_max_shell_stress_proxy_MPa')}`",
        f"- Energy balance relative error: `{metrics.get('energy_balance_relative_error')}`",
        "",
        "## Fluent Pack Comparison",
        "",
    ]
    if comparison.get("status") == "skipped":
        lines.append("- No comparison pack was supplied.")
    else:
        for key, value in sorted(comparison.get("metrics", {}).items()):
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Application Scope", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _normalize_case(case: dict[str, Any]) -> dict[str, Any]:
    payload = dict(case)
    payload.setdefault("case_id", "dewaxing_native_reduced_order_demo")
    payload.setdefault("case_name", "FastFluent Native Dewaxing Reduced-Order Demo")
    return payload


def _validate_case(case: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    domain = _object(case, "domain", errors)
    time = _object(case, "time", errors)
    shell = _object(case, "shell", errors)
    wax = _object(case, "wax", errors)
    steam = _object(case, "steam_boundary", errors)
    initial = _object(case, "initial", errors)
    if not isinstance(case.get("case_id"), str) or not case.get("case_id"):
        errors.append("case_id must be a non-empty string.")
    if domain:
        nx = _int(domain.get("nx"), "domain.nx", errors)
        ny = _int(domain.get("ny"), "domain.ny", errors)
        thickness = _positive(domain.get("thickness_m"), "domain.thickness_m", errors)
        height = _positive(domain.get("height_m"), "domain.height_m", errors)
        shell_thickness = _positive(domain.get("shell_thickness_m"), "domain.shell_thickness_m", errors)
        if nx is not None and nx < 4:
            errors.append("domain.nx must be at least 4.")
        if ny is not None and ny < 4:
            errors.append("domain.ny must be at least 4.")
        if thickness is not None and shell_thickness is not None and shell_thickness >= thickness:
            errors.append("domain.shell_thickness_m must be smaller than domain.thickness_m.")
        if thickness and height and thickness / height > 1.0:
            warnings.append("domain.thickness_m is large relative to height_m; check public surrogate geometry.")
    if time:
        _positive(time.get("time_step_s"), "time.time_step_s", errors)
        _positive(time.get("final_time_s"), "time.final_time_s", errors)
        _positive(time.get("output_interval_s"), "time.output_interval_s", errors)
    for label, material in (("shell", shell), ("wax", wax), ("steam_boundary", steam), ("initial", initial)):
        if material:
            for key, value in material.items():
                if key.endswith(("_kg_m3", "_J_kgK", "_W_mK", "_W_m2K", "_K", "_Pa", "_1_K", "_J_kg")):
                    _positive(value, f"{label}.{key}", errors)
    if wax:
        t_min = wax.get("melting_temperature_min_K")
        t_max = wax.get("melting_temperature_max_K")
        if t_min is not None and t_max is not None and float(t_max) <= float(t_min):
            errors.append("wax.melting_temperature_max_K must exceed wax.melting_temperature_min_K.")
    if not errors:
        stability = _stability(case)
        if stability["stable"] is not True:
            errors.append(stability["message"])
    return {"status": "failed" if errors else "passed", "passed": not errors, "warnings": warnings, "blocking_errors": errors}


def _solve(case: dict[str, Any]) -> dict[str, Any]:
    domain = case["domain"]
    time = case["time"]
    wax = case["wax"]
    nx = int(domain["nx"])
    ny = int(domain["ny"])
    thickness = float(domain["thickness_m"])
    height = float(domain["height_m"])
    shell_thickness = float(domain["shell_thickness_m"])
    dx = thickness / nx
    dy = height / ny
    dt = float(time["time_step_s"])
    steps = int(round(float(time["final_time_s"]) / dt))
    output_every = max(1, int(round(float(time["output_interval_s"]) / dt)))
    snapshot_steps = {int(round(float(item) / dt)): float(item) for item in time.get("snapshot_times_s", [])}
    initial_temperature = float(case["initial"]["temperature_K"])
    shell_columns = max(1, min(nx - 1, int(math.ceil(shell_thickness / dx))))

    field = [[initial_temperature for _ in range(nx)] for _ in range(ny)]
    heat_input_J_m = 0.0
    previous_enthalpy = 0.0
    history: list[dict[str, Any]] = []
    snapshot_rows: list[dict[str, Any]] = []
    full_melt_time: float | None = None
    risk_series: list[dict[str, float]] = []
    raw_dominant_risk = {"time_s": 0.0, "pressure_risk_proxy": -1.0, "drainage_accessibility": 0.0}
    early = {
        "max_shell_stress_proxy_MPa": 0.0,
        "max_shell_delta_T_K": 0.0,
        "max_wall_heat_flux_W_m2": 0.0,
        "max_thermal_gradient_K_m": 0.0,
    }
    threshold_full = float(wax.get("liquid_fraction_threshold", 0.995))
    early_time = float(case.get("acceptance", {}).get("early_reference_time_s", 4.0))

    for step in range(steps + 1):
        time_s = step * dt
        state = _state_summary(
            field,
            case,
            dx=dx,
            dy=dy,
            shell_columns=shell_columns,
            heat_input_J_m=heat_input_J_m,
            initial_enthalpy=previous_enthalpy,
            time_s=time_s,
        )
        if full_melt_time is None and state["avg_liquid_fraction"] >= threshold_full:
            full_melt_time = time_s
        risk_series.append(
            {
                "time_s": time_s,
                "pressure_risk_proxy": state["pressure_risk_proxy"],
                "drainage_accessibility": state["drainage_accessibility"],
            }
        )
        if state["pressure_risk_proxy"] > raw_dominant_risk["pressure_risk_proxy"]:
            raw_dominant_risk = {
                "time_s": time_s,
                "pressure_risk_proxy": state["pressure_risk_proxy"],
                "drainage_accessibility": state["drainage_accessibility"],
            }
        if time_s <= early_time + 0.5 * dt:
            early["max_shell_stress_proxy_MPa"] = max(early["max_shell_stress_proxy_MPa"], state["shell_stress_proxy_MPa"])
            early["max_shell_delta_T_K"] = max(early["max_shell_delta_T_K"], state["shell_delta_T_K"])
            early["max_wall_heat_flux_W_m2"] = max(early["max_wall_heat_flux_W_m2"], state["mean_wall_heat_flux_W_m2"])
            early["max_thermal_gradient_K_m"] = max(early["max_thermal_gradient_K_m"], state["max_thermal_gradient_K_m"])
        if step % output_every == 0 or step in snapshot_steps or step == steps:
            history.append(_history_row(step, time_s, state))
        if step in snapshot_steps or step == steps:
            snapshot_rows.extend(_field_rows(field, case, dx=dx, dy=dy, shell_columns=shell_columns, time_s=snapshot_steps.get(step, time_s)))
        if step == steps:
            previous_enthalpy = state["total_enthalpy_J_m"]
            break
        heat_input_J_m += _advance(field, case, dx=dx, dy=dy, dt=dt, shell_columns=shell_columns)
        previous_enthalpy = state["total_enthalpy_J_m"]

    final_state = _state_summary(
        field,
        case,
        dx=dx,
        dy=dy,
        shell_columns=shell_columns,
        heat_input_J_m=heat_input_J_m,
        initial_enthalpy=0.0,
        time_s=steps * dt,
    )
    final_rows = _field_rows(field, case, dx=dx, dy=dy, shell_columns=shell_columns, time_s=steps * dt)
    energy_error = abs(final_state["total_enthalpy_J_m"] - heat_input_J_m) / max(abs(heat_input_J_m), 1.0e-12)
    dominant_risk = _dominant_risk_from_series(
        risk_series,
        smoothing_window_s=float(case.get("acceptance", {}).get("risk_time_smoothing_window_s", 18.0)),
    )
    metrics = {
        "final_time_s": steps * dt,
        "grid_cells": nx * ny,
        "time_steps": steps,
        "final_avg_liquid_fraction": final_state["avg_liquid_fraction"],
        "final_liquid_fraction_p95": final_state["liquid_fraction_p95"],
        "predicted_full_melt_time_s": full_melt_time,
        "full_melt_reached": full_melt_time is not None,
        "dominant_risk_time_s": dominant_risk["time_s"],
        "peak_pressure_risk_proxy": dominant_risk["pressure_risk_proxy"],
        "drainage_accessibility_at_peak": dominant_risk["drainage_accessibility"],
        "raw_dominant_risk_time_s": raw_dominant_risk["time_s"],
        "raw_peak_pressure_risk_proxy": raw_dominant_risk["pressure_risk_proxy"],
        "risk_time_smoothing_window_s": dominant_risk["smoothing_window_s"],
        "final_drainage_accessibility": final_state["drainage_accessibility"],
        "final_melt_front_depth_m": final_state["melt_front_depth_m"],
        "early_max_shell_stress_proxy_MPa": early["max_shell_stress_proxy_MPa"],
        "early_max_shell_delta_T_K": early["max_shell_delta_T_K"],
        "early_max_wall_heat_flux_W_m2": early["max_wall_heat_flux_W_m2"],
        "early_max_thermal_gradient_K_m": early["max_thermal_gradient_K_m"],
        "energy_input_J_per_m": heat_input_J_m,
        "final_enthalpy_J_per_m": final_state["total_enthalpy_J_m"],
        "energy_balance_relative_error": energy_error,
    }
    qoi = {
        "schema_version": DEWAXING_NATIVE_QOI_SCHEMA_VERSION,
        "status": "passed",
        "case_id": case["case_id"],
        "metrics": metrics,
        "acceptance": case.get("acceptance", {}),
        "limitations": list(LIMITATIONS),
    }
    return {"qoi": qoi, "history": history, "final_rows": final_rows, "snapshot_rows": snapshot_rows}


def _advance(field: list[list[float]], case: dict[str, Any], *, dx: float, dy: float, dt: float, shell_columns: int) -> float:
    ny = len(field)
    nx = len(field[0])
    old = [row[:] for row in field]
    props_grid = [[_cell_properties(old[j][i], i, shell_columns, case) for i in range(nx)] for j in range(ny)]
    steam = case["steam_boundary"]
    h = float(steam["heat_transfer_coefficient_W_m2K"])
    t_steam = float(steam["temperature_K"])
    heat_input = 0.0
    for j in range(ny):
        for i in range(nx):
            props = props_grid[j][i]
            rho_cp = props["rho_cp_eff"]
            k_c = props["k"]
            west = h * (t_steam - old[j][i]) / dx if i == 0 else _k_face(k_c, props_grid[j][i - 1]["k"]) * (old[j][i - 1] - old[j][i]) / (dx * dx)
            east = 0.0 if i == nx - 1 else _k_face(k_c, props_grid[j][i + 1]["k"]) * (old[j][i + 1] - old[j][i]) / (dx * dx)
            south = 0.0 if j == 0 else _k_face(k_c, props_grid[j - 1][i]["k"]) * (old[j - 1][i] - old[j][i]) / (dy * dy)
            north = 0.0 if j == ny - 1 else _k_face(k_c, props_grid[j + 1][i]["k"]) * (old[j + 1][i] - old[j][i]) / (dy * dy)
            field[j][i] = old[j][i] + dt * (west + east + south + north) / rho_cp
            if i == 0:
                heat_input += h * (t_steam - old[j][i]) * dt * dy
    return heat_input


def _state_summary(
    field: list[list[float]],
    case: dict[str, Any],
    *,
    dx: float,
    dy: float,
    shell_columns: int,
    heat_input_J_m: float,
    initial_enthalpy: float,
    time_s: float,
) -> dict[str, float]:
    del initial_enthalpy
    ny = len(field)
    nx = len(field[0])
    wax_cells = 0
    liquid_values: list[float] = []
    total_enthalpy = 0.0
    max_gradient = 0.0
    wall_flux_values: list[float] = []
    initial_temperature = float(case["initial"]["temperature_K"])
    for j in range(ny):
        for i in range(nx):
            temp = field[j][i]
            props = _cell_properties(temp, i, shell_columns, case)
            total_enthalpy += props["rho"] * (props["cp"] * (temp - initial_temperature) + props["latent_heat"] * props["liquid_fraction"]) * dx * dy
            if i >= shell_columns:
                wax_cells += 1
                liquid_values.append(props["liquid_fraction"])
            if i == 0:
                wall_flux_values.append(float(case["steam_boundary"]["heat_transfer_coefficient_W_m2K"]) * (float(case["steam_boundary"]["temperature_K"]) - temp))
            if i + 1 < nx:
                max_gradient = max(max_gradient, abs(field[j][i + 1] - temp) / dx)
            if j + 1 < ny:
                max_gradient = max(max_gradient, abs(field[j + 1][i] - temp) / dy)
    avg_lf = sum(liquid_values) / max(len(liquid_values), 1)
    p95 = _percentile(liquid_values, 0.95)
    drainage = _drainage_accessibility(field, case, shell_columns=shell_columns)
    mean_wall_flux = sum(wall_flux_values) / max(len(wall_flux_values), 1)
    initial_flux = float(case["steam_boundary"]["heat_transfer_coefficient_W_m2K"]) * (
        float(case["steam_boundary"]["temperature_K"]) - float(case["initial"]["temperature_K"])
    )
    thermal_drive = max(mean_wall_flux, 0.0) / max(initial_flux, 1.0e-30)
    pressure_risk = avg_lf * (1.0 - drainage) * (thermal_drive**0.45) * (1.0 + 0.25 * _mushy_fraction(liquid_values))
    gauge_fraction = float(case.get("acceptance", {}).get("shell_stress_gauge_fraction", 0.55))
    gauge_x = max(0.5 * dx, min(float(case["domain"]["shell_thickness_m"]) * gauge_fraction, float(case["domain"]["thickness_m"]) - 0.5 * dx))
    shell = case["shell"]
    shell_k = float(shell["thermal_conductivity_W_mK"])
    shell_alpha = shell_k / max(float(shell["density_kg_m3"]) * float(shell["specific_heat_J_kgK"]), 1.0e-30)
    diffusion_ramp = 1.0 - math.exp(-max(time_s, 0.0) * shell_alpha / max(gauge_x * gauge_x, 1.0e-30))
    heat_flux_shape = float(case.get("acceptance", {}).get("shell_stress_heat_flux_shape_factor", 0.55))
    shell_delta = max(0.0, heat_flux_shape * diffusion_ramp * max(mean_wall_flux, 0.0) * gauge_x / max(shell_k, 1.0e-30))
    shell_stress = float(shell["young_modulus_Pa"]) * float(shell["thermal_expansion_1_K"]) * shell_delta / max(1.0 - float(shell["poisson_ratio"]), 1.0e-12) / 1.0e6
    front_depth = _melt_front_depth(field, case, shell_columns=shell_columns, dx=dx)
    return {
        "avg_liquid_fraction": avg_lf,
        "liquid_fraction_p95": p95,
        "drainage_accessibility": drainage,
        "pressure_risk_proxy": pressure_risk,
        "melt_front_depth_m": front_depth,
        "total_enthalpy_J_m": total_enthalpy,
        "energy_input_J_m": heat_input_J_m,
        "shell_delta_T_K": shell_delta,
        "shell_stress_proxy_MPa": shell_stress,
        "mean_wall_heat_flux_W_m2": mean_wall_flux,
        "max_thermal_gradient_K_m": max_gradient,
    }


def _cell_properties(temp: float, i: int, shell_columns: int, case: dict[str, Any]) -> dict[str, float]:
    if i < shell_columns:
        shell = case["shell"]
        rho = float(shell["density_kg_m3"])
        cp = float(shell["specific_heat_J_kgK"])
        return {
            "rho": rho,
            "cp": cp,
            "rho_cp_eff": rho * cp,
            "k": float(shell["thermal_conductivity_W_mK"]),
            "liquid_fraction": 0.0,
            "latent_heat": 0.0,
        }
    wax = case["wax"]
    lf = _liquid_fraction(temp, wax)
    rho = (1.0 - lf) * float(wax["density_solid_kg_m3"]) + lf * float(wax["density_liquid_kg_m3"])
    cp = float(wax["specific_heat_J_kgK"])
    latent = float(wax["latent_heat_J_kg"])
    t_min = float(wax["melting_temperature_min_K"])
    t_max = float(wax["melting_temperature_max_K"])
    cp_eff = cp + (latent / (t_max - t_min) if t_min <= temp <= t_max else 0.0)
    k = (1.0 - lf) * float(wax["thermal_conductivity_solid_W_mK"]) + lf * float(wax["thermal_conductivity_liquid_W_mK"])
    return {"rho": rho, "cp": cp, "rho_cp_eff": rho * cp_eff, "k": k, "liquid_fraction": lf, "latent_heat": latent}


def _liquid_fraction(temp: float, wax: dict[str, Any]) -> float:
    t_min = float(wax["melting_temperature_min_K"])
    t_max = float(wax["melting_temperature_max_K"])
    if temp <= t_min:
        return 0.0
    if temp >= t_max:
        return 1.0
    return (temp - t_min) / (t_max - t_min)


def _drainage_accessibility(field: list[list[float]], case: dict[str, Any], *, shell_columns: int) -> float:
    threshold = float(case["wax"].get("drainage_liquid_threshold", 0.5))
    ny = len(field)
    nx = len(field[0])
    wax_total = max((nx - shell_columns) * ny, 1)
    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    for j in range(ny):
        i = shell_columns
        if i < nx and _cell_properties(field[j][i], i, shell_columns, case)["liquid_fraction"] >= threshold:
            queue.append((j, i))
            visited.add((j, i))
    while queue:
        j, i = queue.popleft()
        for jj, ii in ((j - 1, i), (j + 1, i), (j, i - 1), (j, i + 1)):
            if jj < 0 or jj >= ny or ii < shell_columns or ii >= nx or (jj, ii) in visited:
                continue
            if _cell_properties(field[jj][ii], ii, shell_columns, case)["liquid_fraction"] >= threshold:
                visited.add((jj, ii))
                queue.append((jj, ii))
    return len(visited) / wax_total


def _melt_front_depth(field: list[list[float]], case: dict[str, Any], *, shell_columns: int, dx: float) -> float:
    threshold = float(case["wax"].get("drainage_liquid_threshold", 0.5))
    nx = len(field[0])
    deepest = 0
    for i in range(shell_columns, nx):
        values = [_cell_properties(row[i], i, shell_columns, case)["liquid_fraction"] for row in field]
        if sum(values) / len(values) >= threshold:
            deepest = i - shell_columns + 1
    return deepest * dx


def _mushy_fraction(liquid_values: list[float]) -> float:
    if not liquid_values:
        return 0.0
    return sum(1 for value in liquid_values if 0.05 < value < 0.95) / len(liquid_values)


def _dominant_risk_from_series(series: list[dict[str, float]], *, smoothing_window_s: float) -> dict[str, float]:
    if not series:
        return {"time_s": 0.0, "pressure_risk_proxy": 0.0, "drainage_accessibility": 0.0, "smoothing_window_s": smoothing_window_s}
    if len(series) == 1 or smoothing_window_s <= 0.0:
        item = max(series, key=lambda row: row["pressure_risk_proxy"])
        return {
            "time_s": item["time_s"],
            "pressure_risk_proxy": item["pressure_risk_proxy"],
            "drainage_accessibility": item["drainage_accessibility"],
            "smoothing_window_s": 0.0,
        }
    times = [row["time_s"] for row in series]
    values = [row["pressure_risk_proxy"] for row in series]
    dt_values = [times[i + 1] - times[i] for i in range(len(times) - 1) if times[i + 1] > times[i]]
    dt = sum(dt_values) / len(dt_values) if dt_values else smoothing_window_s
    half_count = max(1, int(round(0.5 * smoothing_window_s / max(dt, 1.0e-12))))
    prefix = [0.0]
    for value in values:
        prefix.append(prefix[-1] + value)
    smoothed: list[float] = []
    for index in range(len(values)):
        lo = max(0, index - half_count)
        hi = min(len(values), index + half_count + 1)
        smoothed.append((prefix[hi] - prefix[lo]) / max(hi - lo, 1))
    peak_index = max(range(len(smoothed)), key=lambda index: smoothed[index])
    peak_value = smoothed[peak_index]
    threshold = 0.997 * peak_value
    plateau = [index for index, value in enumerate(smoothed) if value >= threshold]
    if plateau:
        weights = [max(smoothed[index] - threshold * 0.98, 1.0e-18) for index in plateau]
        time_s = sum(times[index] * weight for index, weight in zip(plateau, weights)) / sum(weights)
        nearest = min(plateau, key=lambda index: abs(times[index] - time_s))
    else:
        time_s = times[peak_index]
        nearest = peak_index
    return {
        "time_s": time_s,
        "pressure_risk_proxy": peak_value,
        "drainage_accessibility": series[nearest]["drainage_accessibility"],
        "smoothing_window_s": smoothing_window_s,
    }


def _field_rows(
    field: list[list[float]],
    case: dict[str, Any],
    *,
    dx: float,
    dy: float,
    shell_columns: int,
    time_s: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for j, row in enumerate(field):
        for i, temp in enumerate(row):
            props = _cell_properties(temp, i, shell_columns, case)
            rows.append(
                {
                    "time_s": time_s,
                    "x_m": (i + 0.5) * dx,
                    "y_m": (j + 0.5) * dy,
                    "temperature_K": temp,
                    "liquid_fraction": props["liquid_fraction"],
                    "material": "shell" if i < shell_columns else "wax",
                }
            )
    return rows


def _history_row(step: int, time_s: float, state: dict[str, float]) -> dict[str, Any]:
    return {
        "step": step,
        "time_s": time_s,
        "avg_liquid_fraction": state["avg_liquid_fraction"],
        "liquid_fraction_p95": state["liquid_fraction_p95"],
        "drainage_accessibility": state["drainage_accessibility"],
        "pressure_risk_proxy": state["pressure_risk_proxy"],
        "melt_front_depth_m": state["melt_front_depth_m"],
        "total_enthalpy_J_m": state["total_enthalpy_J_m"],
        "energy_input_J_m": state["energy_input_J_m"],
        "shell_stress_proxy_MPa": state["shell_stress_proxy_MPa"],
        "mean_wall_heat_flux_W_m2": state["mean_wall_heat_flux_W_m2"],
        "max_thermal_gradient_K_m": state["max_thermal_gradient_K_m"],
    }


def _compare_with_pack(metrics: dict[str, Any], comparison_pack: str | Path | None, case: dict[str, Any]) -> dict[str, Any]:
    if comparison_pack is None or str(comparison_pack).strip() == "":
        return {"schema_version": "fastfluent_dewaxing_native_comparison_v1", "status": "skipped", "metrics": {}, "warnings": ["No comparison pack supplied."]}
    validation = validate_dewaxing_result_pack(comparison_pack)
    if not validation.get("passed"):
        return {
            "schema_version": "fastfluent_dewaxing_native_comparison_v1",
            "status": "failed",
            "validation": validation,
            "metrics": {},
            "warnings": validation.get("warnings", []),
            "blocking_errors": validation.get("errors", []),
        }
    reference = validation.get("key_metrics", {})
    native_full = metrics.get("predicted_full_melt_time_s")
    native_risk = metrics.get("dominant_risk_time_s")
    full_ref = reference.get("full_melt_time_s")
    risk_ref = reference.get("dominant_risk_time_s")
    comparison_metrics = {
        "native_full_melt_time_s": native_full,
        "fluent_full_melt_time_s": full_ref,
        "full_melt_time_abs_error_s": _abs_error(native_full, full_ref),
        "full_melt_time_relative_error": _rel_error(native_full, full_ref),
        "native_dominant_risk_time_s": native_risk,
        "fluent_dominant_risk_time_s": risk_ref,
        "dominant_risk_time_abs_error_s": _abs_error(native_risk, risk_ref),
        "dominant_risk_time_relative_error": _rel_error(native_risk, risk_ref),
        "fluent_peak_effective_pressure_mpa": reference.get("peak_effective_pressure_mpa"),
        "native_peak_pressure_risk_proxy": metrics.get("peak_pressure_risk_proxy"),
    }
    warnings: list[str] = []
    acceptance = case.get("acceptance", {})
    rel = comparison_metrics["full_melt_time_relative_error"]
    if rel is None:
        warnings.append("Native reduced-order solver did not reach full melt within final_time_s.")
    elif rel > float(acceptance.get("full_melt_time_warning_relative_error", 0.35)):
        warnings.append(f"Native full-melt timing differs substantially from Fluent pack: relative error {rel}.")
    risk_rel = comparison_metrics["dominant_risk_time_relative_error"]
    if risk_rel is not None and risk_rel > float(acceptance.get("dominant_risk_warning_relative_error", 0.60)):
        warnings.append(f"Native dominant-risk timing differs substantially from Fluent pack: relative error {risk_rel}.")
    return {
        "schema_version": "fastfluent_dewaxing_native_comparison_v1",
        "status": "warning" if warnings else "passed",
        "validation": validation,
        "metrics": comparison_metrics,
        "warnings": warnings,
        "blocking_errors": [],
    }


def _hardening_summary(
    metrics: dict[str, Any],
    validation: dict[str, Any],
    comparison: dict[str, Any],
    case: dict[str, Any],
) -> dict[str, Any]:
    warnings = list(validation.get("warnings", [])) + list(comparison.get("warnings", []))
    blocking_errors = list(validation.get("blocking_errors", [])) + list(comparison.get("blocking_errors", []))
    acceptance = case.get("acceptance", {})
    if metrics.get("energy_balance_relative_error", 1.0) > float(acceptance.get("max_energy_balance_relative_error", 0.08)):
        warnings.append(f"Energy balance relative error is high: {metrics.get('energy_balance_relative_error')}.")
    if not metrics.get("full_melt_reached"):
        warnings.append("Native reduced-order solver did not reach the full-melt threshold within final_time_s.")
    rel = comparison.get("metrics", {}).get("full_melt_time_relative_error") if isinstance(comparison.get("metrics"), dict) else None
    if rel is not None and rel <= float(acceptance.get("full_melt_time_pass_relative_error", 0.20)):
        timing_gate = "passed"
    elif rel is None:
        timing_gate = "not_available"
    else:
        timing_gate = "warning"
    status = "failed" if blocking_errors else ("warning" if warnings else "passed")
    decision = {
        "usable_as_native_advisory_seed": status in {"passed", "warning"},
        "usable_for_screening_evidence": status in {"passed", "warning"},
        "usable_for_final_cfd_validation": False,
        "recommended_next_action": "compare_native_dewaxing_qoi_against_reviewed_fluent_pack",
    }
    return {
        "schema_version": DEWAXING_NATIVE_HARDENING_SCHEMA_VERSION,
        "status": status,
        "evidence_level": "native_dewaxing_reduced_order_advisory",
        "gate_results": {
            "case_validation_passed": validation.get("passed") is True,
            "energy_balance_within_advisory_tolerance": metrics.get("energy_balance_relative_error", 1.0) <= float(acceptance.get("max_energy_balance_relative_error", 0.08)),
            "full_melt_reached": metrics.get("full_melt_reached") is True,
            "full_melt_timing_gate": timing_gate,
            "comparison_pack_validation_passed": comparison.get("validation", {}).get("passed") is True if isinstance(comparison.get("validation"), dict) else None,
        },
        "metrics": metrics,
        "decision": decision,
        "warnings": warnings,
        "blocking_errors": blocking_errors,
        "limitations": list(LIMITATIONS),
    }


def _agent_decision(hardening: dict[str, Any], qoi: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "fastfluent_dewaxing_native_agent_decision_v1",
        "status": hardening.get("status"),
        "can_support_agent_workflow_control": hardening.get("status") in {"passed", "warning"},
        "can_support_fastfluent_screening_decision": hardening.get("status") in {"passed", "warning"},
        "can_support_existing_fluent_result_review": comparison.get("status") in {"passed", "warning"},
        "can_support_new_fluent_calculation": False,
        "can_support_final_cfd_validation": False,
        "can_support_final_crack_probability": False,
        "recommended_next_action": hardening.get("decision", {}).get("recommended_next_action"),
        "key_metrics": qoi.get("metrics", {}),
        "comparison_metrics": comparison.get("metrics", {}),
        "rationale": [
            "Native reduced-order dewaxing solved transient heat conduction and enthalpy phase change.",
            "The result is independent FastFluent evidence and is compared against reviewed Fluent pack metrics when supplied.",
            "Final CFD validation remains outside this native reduced-order solver boundary.",
        ],
    }


def _blocked_result(
    case: dict[str, Any],
    *,
    root: Path,
    artifacts: dict[str, str],
    validation: dict[str, Any],
    comparison_pack: str | Path | None,
) -> dict[str, Any]:
    hardening = {
        "schema_version": DEWAXING_NATIVE_HARDENING_SCHEMA_VERSION,
        "status": "failed",
        "evidence_level": "blocked_native_dewaxing_reduced_order",
        "gate_results": {"case_validation_passed": False},
        "metrics": {},
        "decision": {
            "usable_as_native_advisory_seed": False,
            "usable_for_screening_evidence": False,
            "usable_for_final_cfd_validation": False,
            "recommended_next_action": "repair_native_dewaxing_case",
        },
        "warnings": validation.get("warnings", []),
        "blocking_errors": validation.get("blocking_errors", []),
        "limitations": list(LIMITATIONS),
    }
    qoi = {
        "schema_version": DEWAXING_NATIVE_QOI_SCHEMA_VERSION,
        "status": "failed",
        "case_id": case.get("case_id"),
        "metrics": {},
        "acceptance": case.get("acceptance", {}),
        "limitations": list(LIMITATIONS),
    }
    comparison = {"schema_version": "fastfluent_dewaxing_native_comparison_v1", "status": "skipped", "metrics": {}, "warnings": []}
    return {
        "schema_version": DEWAXING_NATIVE_RESULT_SCHEMA_VERSION,
        "status": "failed",
        "backend": "fastfluent_native",
        "operation": "run_dewaxing_native_solver",
        "case_id": case.get("case_id"),
        "case_type": "thermal.dewaxing_native_reduced_order",
        "quality_status": "failed",
        "outputs": {
            "solver_execution": "blocked_by_native_case_validation",
            "artifacts": artifacts,
            "qoi": qoi,
            "hardening_summary": hardening,
            "comparison": comparison,
        },
        "agent_decision": _agent_decision(hardening, qoi, comparison),
        "warnings": validation.get("warnings", []),
        "blocking_errors": validation.get("blocking_errors", []),
        "limitations": list(LIMITATIONS),
        "metadata": {
            "output_dir": str(root),
            "comparison_pack": str(comparison_pack) if comparison_pack else None,
            "fluent_launched": False,
            "new_fluent_calculation": False,
        },
    }


def _write_outputs(
    root: Path,
    result: dict[str, Any],
    *,
    artifacts: dict[str, str],
    case: dict[str, Any],
    history: list[dict[str, Any]],
    final_rows: list[dict[str, Any]],
    snapshot_rows: list[dict[str, Any]],
) -> None:
    write_json_file(root / "dewaxing_native_case.json", case)
    if history:
        write_csv(root / "dewaxing_native_history.csv", history)
    else:
        write_text_file(root / "dewaxing_native_history.csv", "step,time_s\n")
    if final_rows:
        write_csv(root / "dewaxing_native_final_field.csv", final_rows)
    else:
        write_text_file(root / "dewaxing_native_final_field.csv", "time_s,x_m,y_m,temperature_K,liquid_fraction,material\n")
    if snapshot_rows:
        write_csv(root / "dewaxing_native_snapshots.csv", snapshot_rows)
    else:
        write_text_file(root / "dewaxing_native_snapshots.csv", "time_s,x_m,y_m,temperature_K,liquid_fraction,material\n")
    outputs = result.get("outputs", {}) if isinstance(result.get("outputs"), dict) else {}
    write_json_file(root / "dewaxing_native_qoi.json", outputs.get("qoi", {}))
    write_json_file(root / "hardening_summary.json", outputs.get("hardening_summary", {}))
    write_json_file(root / "dewaxing_native_comparison.json", outputs.get("comparison", {}))
    write_json_file(root / "dewaxing_native_status.json", result)
    write_text_file(root / "dewaxing_native_report.md", dewaxing_native_solver_markdown(result))
    for path_text in artifacts.values():
        ensure_dir(Path(path_text).parent)


def _stability(case: dict[str, Any]) -> dict[str, Any]:
    domain = case["domain"]
    dt = float(case["time"]["time_step_s"])
    nx = int(domain["nx"])
    ny = int(domain["ny"])
    dx = float(domain["thickness_m"]) / nx
    dy = float(domain["height_m"]) / ny
    shell = case["shell"]
    wax = case["wax"]
    alpha_shell = float(shell["thermal_conductivity_W_mK"]) / (float(shell["density_kg_m3"]) * float(shell["specific_heat_J_kgK"]))
    alpha_wax = max(float(wax["thermal_conductivity_solid_W_mK"]), float(wax["thermal_conductivity_liquid_W_mK"])) / (
        min(float(wax["density_solid_kg_m3"]), float(wax["density_liquid_kg_m3"])) * float(wax["specific_heat_J_kgK"])
    )
    alpha = max(alpha_shell, alpha_wax)
    limit = 1.0 / (2.0 * alpha * (1.0 / (dx * dx) + 1.0 / (dy * dy)))
    stable = dt <= 0.85 * limit
    return {
        "stable": stable,
        "time_step_s": dt,
        "explicit_stability_limit_s": limit,
        "message": f"Explicit heat-conduction time step exceeds stable limit: dt={dt}, limit={limit}.",
    }


def _object(payload: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict) or not value:
        errors.append(f"{key} must be a non-empty object.")
        return {}
    return value


def _positive(value: Any, label: str, errors: list[str]) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be numeric.")
        return None
    if number <= 0.0:
        errors.append(f"{label} must be positive.")
    return number


def _int(value: Any, label: str, errors: list[str]) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be an integer.")
        return None
    return number


def _k_face(left: float, right: float) -> float:
    return 2.0 * left * right / max(left + right, 1.0e-30)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def _abs_error(native: Any, reference: Any) -> float | None:
    if native is None or reference is None:
        return None
    return abs(float(native) - float(reference))


def _rel_error(native: Any, reference: Any) -> float | None:
    if native is None or reference in {None, 0.0}:
        return None
    return abs(float(native) - float(reference)) / abs(float(reference))
