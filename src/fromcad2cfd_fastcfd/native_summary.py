"""Native FastFluent summary contract helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import statistics
from typing import Any


NATIVE_SUMMARY_SCHEMA_VERSION = "fromcad2cfd_fastfluent_native_summary_v1"
NATIVE_SUMMARY_FILENAME = "fastfluent_native_summary.json"
NATIVE_CONVERGENCE_FILENAME = "fastfluent_native_convergence.csv"


def native_summary_path(output_dir: str | Path) -> Path:
    """Return the expected native FastFluent summary path for a run directory."""

    return Path(output_dir) / NATIVE_SUMMARY_FILENAME


def native_convergence_path(output_dir: str | Path) -> Path:
    """Return the expected native FastFluent convergence CSV path."""

    return Path(output_dir) / NATIVE_CONVERGENCE_FILENAME


def read_native_summary(output_dir: str | Path) -> dict[str, Any]:
    """Read and lightly validate a native FastFluent run summary when present."""

    path = native_summary_path(output_dir)
    if not path.exists():
        return {
            "status": "not_available",
            "path": str(path),
            "warnings": ["Native FastFluent summary was not emitted by this executable."],
            "metrics": {},
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "failed",
            "path": str(path),
            "warnings": [f"Failed to read native FastFluent summary: {exc}"],
            "metrics": {},
        }
    warnings: list[str] = []
    if payload.get("schema_version") != NATIVE_SUMMARY_SCHEMA_VERSION:
        warnings.append(f"Unexpected native summary schema: {payload.get('schema_version')!r}.")
    metrics = {key: value for key, value in payload.items() if key != "schema_version"}
    return {
        "status": "parsed" if not warnings else "partial",
        "path": str(path),
        "warnings": warnings,
        "metrics": metrics,
    }


def read_native_convergence(output_dir: str | Path) -> dict[str, Any]:
    """Read native FastFluent residual history when emitted by the executable."""

    path = native_convergence_path(output_dir)
    if not path.exists():
        return {
            "status": "not_available",
            "path": str(path),
            "warnings": ["Native FastFluent convergence CSV was not emitted by this executable."],
            "rows": [],
            "metrics": {},
        }
    rows: list[dict[str, float | int]] = []
    warnings: list[str] = []
    try:
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for raw in reader:
                if not raw:
                    continue
                step_text = raw.get("step")
                residual_text = raw.get("residual")
                if step_text is None or residual_text is None:
                    warnings.append("Native convergence CSV must contain step and residual columns.")
                    break
                rows.append({"step": int(float(step_text)), "residual": float(residual_text)})
    except Exception as exc:
        return {
            "status": "failed",
            "path": str(path),
            "warnings": [f"Failed to read native FastFluent convergence CSV: {exc}"],
            "rows": rows,
            "metrics": {},
        }
    if not rows:
        warnings.append("Native convergence CSV contains no residual samples.")
    return {
        "status": "parsed" if rows and not warnings else ("partial" if rows else "failed"),
        "path": str(path),
        "warnings": warnings,
        "rows": rows,
        "metrics": _native_convergence_metrics(rows),
    }


def _native_convergence_metrics(rows: list[dict[str, float | int]]) -> dict[str, Any]:
    if not rows:
        return {}
    residuals = [float(row["residual"]) for row in rows]
    first = residuals[0]
    final = residuals[-1]
    nonincreasing_pairs = 0
    total_pairs = max(0, len(residuals) - 1)
    for left, right in zip(residuals, residuals[1:]):
        if right <= left:
            nonincreasing_pairs += 1
    return {
        "sample_count": len(rows),
        "first_step": int(rows[0]["step"]),
        "last_step": int(rows[-1]["step"]),
        "first_residual": first,
        "final_residual": final,
        "min_residual": min(residuals),
        "max_residual": max(residuals),
        "mean_residual": statistics.fmean(residuals),
        "reduction_ratio": final / first if first != 0 else None,
        "nonincreasing_fraction": nonincreasing_pairs / total_pairs if total_pairs else None,
    }


def native_summary_qoi_updates(summary: dict[str, Any]) -> dict[str, Any]:
    """Return compact QoI metrics derived from a native summary."""

    metrics = summary.get("metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}
    grid = metrics.get("grid") if isinstance(metrics.get("grid"), dict) else {}
    physical_properties = metrics.get("physical_properties") if isinstance(metrics.get("physical_properties"), dict) else {}
    boundary_conditions = metrics.get("boundary_conditions") if isinstance(metrics.get("boundary_conditions"), dict) else {}
    return {
        "native_summary_status": summary.get("status", "unknown"),
        "native_completed_steps": metrics.get("completed_steps"),
        "native_requested_total_steps": metrics.get("requested_total_steps"),
        "native_output_interval": metrics.get("output_interval"),
        "native_final_residual": metrics.get("final_residual"),
        "native_physical_time_s": metrics.get("physical_time_s"),
        "native_field_prefix": metrics.get("field_prefix"),
        "native_grid_nx": grid.get("nx"),
        "native_grid_ny": grid.get("ny"),
        "native_cell_length_mm": grid.get("cell_length_mm"),
        "native_kinematic_viscosity_mm2_s": physical_properties.get("kinematic_viscosity_mm2_s"),
        "native_reference_velocity_mm_s": boundary_conditions.get("reference_velocity_mm_s"),
    }


def native_convergence_qoi_updates(convergence: dict[str, Any]) -> dict[str, Any]:
    """Return compact QoI metrics derived from native residual history."""

    metrics = convergence.get("metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}
    return {
        "native_convergence_status": convergence.get("status", "unknown"),
        "native_convergence_sample_count": metrics.get("sample_count"),
        "native_convergence_first_step": metrics.get("first_step"),
        "native_convergence_last_step": metrics.get("last_step"),
        "native_convergence_first_residual": metrics.get("first_residual"),
        "native_convergence_final_residual": metrics.get("final_residual"),
        "native_convergence_reduction_ratio": metrics.get("reduction_ratio"),
        "native_convergence_nonincreasing_fraction": metrics.get("nonincreasing_fraction"),
    }
