"""Practical FastFluent-native artifact contract for S2 utilities.

The S2 practical-native layer records lightweight numerical evidence without
launching ANSYS Fluent, PyFluent, raw Fluent TUI, UDF generation, or private
case workflows.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

from .solver_plan_patch import find_dangerous_keys


PRACTICAL_NATIVE_RESULT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_practical_native_result_v1"
PRACTICAL_NATIVE_PACK_SCHEMA_VERSION = "fromcad2cfd_fastfluent_practical_native_pack_v1"

ALLOWED_PRACTICAL_STATUS = {"pass", "warn", "block", "failed", "unavailable"}

REQUIRED_RESULT_FIELDS = [
    "schema_version",
    "case_id",
    "case_name",
    "module",
    "kernel",
    "status",
    "input_summary",
    "grid_summary",
    "time_summary",
    "stability_summary",
    "qoi_summary",
    "field_outputs",
    "history_outputs",
    "benchmark_comparison",
    "warnings",
    "blocking_errors",
    "limitations",
    "metadata",
]

LIMITATIONS = [
    "This is a FastFluent-native practical mini computation.",
    "It does not launch Fluent or call PyFluent.",
    "It does not edit Fluent case/data files.",
    "It does not emit Fluent TUI or executable UDF source.",
    "It does not prove high-fidelity CFD accuracy.",
]


def build_practical_native_result(
    *,
    case_id: str,
    case_name: str,
    module: str,
    kernel: str,
    status: str,
    input_summary: dict[str, Any] | None = None,
    grid_summary: dict[str, Any] | None = None,
    time_summary: dict[str, Any] | None = None,
    stability_summary: dict[str, Any] | None = None,
    qoi_summary: dict[str, Any] | None = None,
    field_outputs: list[dict[str, Any]] | None = None,
    history_outputs: list[dict[str, Any]] | None = None,
    benchmark_comparison: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    blocking_errors: list[str] | None = None,
    limitations: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "schema_version": PRACTICAL_NATIVE_RESULT_SCHEMA_VERSION,
        "case_id": case_id,
        "case_name": case_name,
        "module": module,
        "kernel": kernel,
        "status": status,
        "input_summary": input_summary or {},
        "grid_summary": grid_summary or {},
        "time_summary": time_summary or {},
        "stability_summary": stability_summary or {},
        "qoi_summary": qoi_summary or {},
        "field_outputs": field_outputs or [],
        "history_outputs": history_outputs or [],
        "benchmark_comparison": benchmark_comparison or {},
        "warnings": warnings or [],
        "blocking_errors": blocking_errors or [],
        "limitations": list(limitations or LIMITATIONS),
        "metadata": {"fluent_launched": False, "pyfluent_called": False} | dict(metadata or {}),
    }
    validation = validate_practical_native_result(result)
    if not validation["passed"]:
        raise ValueError("Invalid practical native result: " + "; ".join(validation["errors"]))
    return result


def validate_practical_native_result(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(payload, dict):
        return {"status": "failed", "passed": False, "errors": ["Result must be a JSON object."], "warnings": []}
    for field_name in REQUIRED_RESULT_FIELDS:
        if field_name not in payload:
            errors.append(f"Missing required field: {field_name}")
    if payload.get("schema_version") != PRACTICAL_NATIVE_RESULT_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {payload.get('schema_version')!r}")
    if payload.get("status") not in ALLOWED_PRACTICAL_STATUS:
        errors.append(f"Unsupported status: {payload.get('status')!r}")
    for field_name in [
        "input_summary",
        "grid_summary",
        "time_summary",
        "stability_summary",
        "qoi_summary",
        "benchmark_comparison",
        "metadata",
    ]:
        if field_name in payload and not isinstance(payload[field_name], dict):
            errors.append(f"{field_name} must be an object.")
    for field_name in ["field_outputs", "history_outputs", "warnings", "blocking_errors", "limitations"]:
        if field_name in payload and not isinstance(payload[field_name], list):
            errors.append(f"{field_name} must be a list.")
    dangerous = find_dangerous_keys(payload)
    if dangerous:
        errors.append("Dangerous key names found: " + ", ".join(dangerous))
    if payload.get("metadata", {}).get("fluent_launched") is True:
        errors.append("Practical native artifacts must not launch Fluent.")
    return {"status": "failed" if errors else "passed", "passed": not errors, "errors": errors, "warnings": warnings}


def write_practical_native_result(payload: dict[str, Any], output_dir: str | Path) -> Path:
    validation = validate_practical_native_result(payload)
    if not validation["passed"]:
        raise ValueError("Invalid practical native result: " + "; ".join(validation["errors"]))
    return write_json(Path(output_dir) / "simulation_result.json", payload)


def write_json(path: str | Path, payload: dict[str, Any] | list[Any]) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    with open(win_path(target), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    return target


def write_text(path: str | Path, text: str) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    with open(win_path(target), "w", encoding="utf-8") as handle:
        handle.write(text)
    return target


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    names = fieldnames or sorted({key for row in rows for key in row})
    with open(win_path(target), "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in names})
    return target


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    os.makedirs(win_path(target), exist_ok=True)
    return target


def win_path(path: str | Path) -> str:
    resolved = str(Path(path).resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def finite_count(values: list[float]) -> int:
    return sum(1 for value in values if math.isfinite(float(value)))


def min_max_mean(values: list[float]) -> dict[str, float | int]:
    finite_values = [float(value) for value in values if math.isfinite(float(value))]
    if not finite_values:
        return {"min": math.nan, "max": math.nan, "mean": math.nan, "finite_count": 0}
    return {
        "min": min(finite_values),
        "max": max(finite_values),
        "mean": sum(finite_values) / len(finite_values),
        "finite_count": len(finite_values),
    }
