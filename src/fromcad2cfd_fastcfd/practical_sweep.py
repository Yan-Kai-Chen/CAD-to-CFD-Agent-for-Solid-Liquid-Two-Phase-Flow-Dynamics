"""Lightweight practical parameter sweep utilities for FastFluent S2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .practical_native_artifacts import write_csv, write_json, write_text


def run_practical_parameter_sweep(output_dir: str | Path = "practical_parameter_sweep", base_case: dict[str, Any] | None = None) -> dict[str, Any]:
    target = Path(output_dir)
    case = {
        "case_id": "practical_parameter_sweep_demo",
        "cell_size_m": 5.0e-4,
        "thermal_diffusivity_m2_s": 1.25e-7,
        "velocity_m_s": 0.2,
        "diffusivity_m2_s": 0.001,
        "source_strength_W_m3": 8.0e7,
        "density_kg_m3": 900.0,
        "specific_heat_J_kgK": 2200.0,
    } | dict(base_case or {})
    rows: list[dict[str, Any]] = []
    case_index = 0
    for dt in [0.005, 0.01, 0.05, 0.2, 1.2]:
        case_index += 1
        rows.append(_sweep_row(case_index, "time_step_s", dt, case | {"time_step_s": dt}))
    for alpha in [5.0e-8, 1.25e-7, 5.0e-7]:
        case_index += 1
        rows.append(_sweep_row(case_index, "thermal_diffusivity_m2_s", alpha, case | {"thermal_diffusivity_m2_s": alpha, "time_step_s": 0.05}))
    for source in [1.0e7, 8.0e7, 2.0e8]:
        case_index += 1
        rows.append(_sweep_row(case_index, "source_strength_W_m3", source, case | {"source_strength_W_m3": source, "time_step_s": 0.05}))
    for velocity in [0.05, 0.2, 0.8]:
        case_index += 1
        rows.append(_sweep_row(case_index, "velocity_m_s", velocity, case | {"velocity_m_s": velocity, "time_step_s": 0.01}))
    status_counts = _count_status(rows)
    risk_map = {
        "schema_version": "fromcad2cfd_fastfluent_practical_risk_map_v1",
        "status_counts": status_counts,
        "unstable_case_ids": [row["case_id"] for row in rows if row["status"] in {"warn", "block"}],
        "dominant_risks": sorted({row["stability_flags"] for row in rows if row["stability_flags"]}),
        "fluent_launched": False,
    }
    recommended = [
        {
            "parameter": row["swept_parameter"],
            "parameter_value": row["parameter_value"],
            "recommended_dt_s": row["recommended_dt_s"],
            "status": row["status"],
        }
        for row in rows
    ]
    sweep_path = write_csv(target / "sweep_summary.csv", rows)
    manifest = {
        "schema_version": "fromcad2cfd_fastfluent_practical_parameter_sweep_v1",
        "case_count": len(rows),
        "status_counts": status_counts,
        "sweep_summary": str(sweep_path),
        "risk_map": str(target / "risk_map.json"),
        "recommended_dt_table": str(target / "recommended_dt_table.csv"),
        "fluent_launched": False,
    }
    write_json(target / "sweep_manifest.json", manifest)
    write_json(target / "risk_map.json", risk_map)
    write_csv(target / "recommended_dt_table.csv", recommended)
    write_text(target / "simulation_summary.md", _sweep_summary_markdown(manifest))
    return {"manifest": manifest, "rows": rows, "risk_map": risk_map}


def _sweep_row(index: int, parameter: str, parameter_value: float, case: dict[str, Any]) -> dict[str, Any]:
    dx = float(case["cell_size_m"])
    dt = float(case["time_step_s"])
    alpha = float(case["thermal_diffusivity_m2_s"])
    velocity = float(case["velocity_m_s"])
    diffusivity = float(case["diffusivity_m2_s"])
    rho_cp = float(case["density_kg_m3"]) * float(case["specific_heat_J_kgK"])
    source_strength = float(case["source_strength_W_m3"])
    fo = alpha * dt / (dx * dx)
    cfl = abs(velocity) * dt / dx
    diffusion_number = diffusivity * dt / (dx * dx)
    source_delta_t = source_strength * dt / rho_cp
    flags = []
    if fo > 0.5:
        flags.append("heat_fo_unstable")
    if cfl > 1.0:
        flags.append("scalar_cfl_unstable")
    if diffusion_number > 0.5:
        flags.append("scalar_diffusion_unstable")
    if source_delta_t > 10.0:
        flags.append("source_temperature_jump_large")
    status = "block" if any(flag.endswith("unstable") for flag in flags) else ("warn" if flags else "pass")
    recommended_dt = min(0.45 * dx * dx / max(alpha, 1.0e-30), 0.8 * dx / max(abs(velocity), 1.0e-30), 5.0 * rho_cp / max(source_strength, 1.0e-30))
    return {
        "case_id": f"sweep_case_{index:03d}",
        "swept_parameter": parameter,
        "parameter_value": parameter_value,
        "status": status,
        "fourier_number": fo,
        "cfl": cfl,
        "diffusion_number": diffusion_number,
        "source_delta_t_K_per_step": source_delta_t,
        "recommended_dt_s": recommended_dt,
        "key_qoi": source_delta_t,
        "stability_flags": ";".join(flags),
        "warnings": ";".join(flags) if status == "warn" else "",
        "blocking_errors": ";".join(flags) if status == "block" else "",
    }


def _count_status(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "block": 0}
    for row in rows:
        counts[str(row["status"])] = counts.get(str(row["status"]), 0) + 1
    return counts


def _sweep_summary_markdown(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Practical Parameter Sweep",
            "",
            f"- Case count: `{manifest['case_count']}`",
            f"- Status counts: `{manifest['status_counts']}`",
            "",
            "This sweep screens stability indicators for practical native mini computations. It does not launch Fluent.",
            "",
        ]
    )
