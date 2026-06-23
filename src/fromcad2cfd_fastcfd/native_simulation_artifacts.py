"""Artifact contract for FastFluent-native simulation validation.

This module defines a small, non-Fluent result schema used by the S1 validation
pack. It records native FastFluent/FastCFD simulation evidence without launching
ANSYS Fluent, PyFluent, raw Fluent TUI, or UDF workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any

from .solver_plan_patch import find_dangerous_keys


NATIVE_SIMULATION_RESULT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_native_simulation_result_v1"
NATIVE_SIMULATION_PACK_SCHEMA_VERSION = "fromcad2cfd_fastfluent_native_simulation_pack_v1"
ALLOWED_SIMULATION_STATUS = {"pass", "warn", "block", "unavailable"}
ALLOWED_BACKEND_STATUS = {"available", "unavailable", "failed", "skipped"}
REQUIRED_RESULT_FIELDS = [
    "schema_version",
    "case_id",
    "case_name",
    "module",
    "backend",
    "backend_status",
    "status",
    "input_summary",
    "runtime_summary",
    "mesh_summary",
    "numerics_summary",
    "convergence_summary",
    "qoi_summary",
    "field_outputs",
    "warnings",
    "blocking_errors",
    "limitations",
    "metadata",
]
RUNTIME_FIELDS = [
    "start_time",
    "end_time",
    "elapsed_s",
    "iteration_count",
    "time_step_count",
    "final_residual",
    "residual_drop",
    "exit_reason",
]
MESH_FIELDS = [
    "mesh_type",
    "dimension",
    "cell_count",
    "node_count",
    "face_count",
    "min_cell_size",
    "max_cell_size",
    "mesh_quality_summary",
    "boundary_zone_summary",
]
CONVERGENCE_FIELDS = [
    "residual_history_path",
    "final_residuals",
    "residual_drop_orders",
    "steady_or_transient",
    "converged",
    "convergence_warnings",
]


@dataclass(frozen=True)
class NativeSimulationValidation:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "passed": self.passed, "errors": list(self.errors), "warnings": list(self.warnings)}


def empty_runtime_summary(**updates: Any) -> dict[str, Any]:
    payload = {field_name: "not_available" for field_name in RUNTIME_FIELDS}
    payload.update(updates)
    return payload


def empty_mesh_summary(**updates: Any) -> dict[str, Any]:
    payload = {field_name: "not_available" for field_name in MESH_FIELDS}
    payload.update(updates)
    return payload


def empty_convergence_summary(**updates: Any) -> dict[str, Any]:
    payload = {field_name: "not_available" for field_name in CONVERGENCE_FIELDS}
    payload.update(updates)
    return payload


def build_native_simulation_result(
    *,
    case_id: str,
    case_name: str,
    module: str,
    backend: str,
    backend_status: str,
    status: str,
    input_summary: dict[str, Any] | None = None,
    runtime_summary: dict[str, Any] | None = None,
    mesh_summary: dict[str, Any] | None = None,
    numerics_summary: dict[str, Any] | None = None,
    convergence_summary: dict[str, Any] | None = None,
    qoi_summary: dict[str, Any] | None = None,
    field_outputs: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    blocking_errors: list[str] | None = None,
    limitations: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a native simulation result with all required top-level fields."""

    result = {
        "schema_version": NATIVE_SIMULATION_RESULT_SCHEMA_VERSION,
        "case_id": case_id,
        "case_name": case_name,
        "module": module,
        "backend": backend,
        "backend_status": backend_status,
        "status": status,
        "input_summary": input_summary or {},
        "runtime_summary": runtime_summary or empty_runtime_summary(),
        "mesh_summary": mesh_summary or empty_mesh_summary(),
        "numerics_summary": numerics_summary or {},
        "convergence_summary": convergence_summary or empty_convergence_summary(),
        "qoi_summary": qoi_summary or {},
        "field_outputs": field_outputs or [],
        "warnings": warnings or [],
        "blocking_errors": blocking_errors or [],
        "limitations": limitations or [],
        "metadata": metadata or {},
    }
    validation = validate_native_simulation_result(result)
    if not validation.passed:
        raise ValueError("Invalid native simulation result: " + "; ".join(validation.errors))
    return result


def validate_native_simulation_result(payload: dict[str, Any]) -> NativeSimulationValidation:
    """Validate S1 simulation_result.json using fail-closed checks."""

    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(payload, dict):
        return NativeSimulationValidation(status="failed", errors=["Native simulation result must be a JSON object."])
    for field_name in REQUIRED_RESULT_FIELDS:
        if field_name not in payload:
            errors.append(f"Missing required field: {field_name}")
    if payload.get("schema_version") != NATIVE_SIMULATION_RESULT_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {payload.get('schema_version')!r}")
    if payload.get("status") not in ALLOWED_SIMULATION_STATUS:
        errors.append(f"Unsupported status: {payload.get('status')!r}")
    if payload.get("backend_status") not in ALLOWED_BACKEND_STATUS:
        errors.append(f"Unsupported backend_status: {payload.get('backend_status')!r}")
    for field_name in ["input_summary", "runtime_summary", "mesh_summary", "numerics_summary", "convergence_summary", "qoi_summary", "metadata"]:
        if field_name in payload and not isinstance(payload[field_name], dict):
            errors.append(f"{field_name} must be an object.")
    for field_name in ["field_outputs", "warnings", "blocking_errors", "limitations"]:
        if field_name in payload and not isinstance(payload[field_name], list):
            errors.append(f"{field_name} must be a list.")
    runtime = payload.get("runtime_summary", {}) if isinstance(payload.get("runtime_summary"), dict) else {}
    for field_name in RUNTIME_FIELDS:
        if field_name not in runtime:
            warnings.append(f"runtime_summary is missing {field_name}; use not_available when unsupported.")
    mesh = payload.get("mesh_summary", {}) if isinstance(payload.get("mesh_summary"), dict) else {}
    for field_name in MESH_FIELDS:
        if field_name not in mesh:
            warnings.append(f"mesh_summary is missing {field_name}; use not_available when unsupported.")
    convergence = payload.get("convergence_summary", {}) if isinstance(payload.get("convergence_summary"), dict) else {}
    for field_name in CONVERGENCE_FIELDS:
        if field_name not in convergence:
            warnings.append(f"convergence_summary is missing {field_name}; use not_available when unsupported.")
    if payload.get("status") == "unavailable" and payload.get("backend_status") != "unavailable":
        errors.append("Unavailable simulation status must use backend_status='unavailable'.")
    if payload.get("status") in {"pass", "warn"} and payload.get("backend_status") != "available":
        errors.append("Pass/warn simulation status must use backend_status='available'.")
    dangerous = find_dangerous_keys(payload)
    if dangerous:
        errors.append("Dangerous key names found: " + ", ".join(dangerous))
    return NativeSimulationValidation(status="failed" if errors else "passed", errors=errors, warnings=warnings)


def write_native_simulation_result(payload: dict[str, Any], path: str | Path) -> Path:
    validation = validate_native_simulation_result(payload)
    if not validation.passed:
        raise ValueError("Invalid native simulation result: " + "; ".join(validation.errors))
    output = Path(path)
    os.makedirs(_win_path(output.parent), exist_ok=True)
    with open(_win_path(output), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    return output


def _win_path(path: Path) -> str:
    absolute = str(Path(path).resolve())
    if os.name == "nt" and not absolute.startswith("\\\\?\\"):
        return "\\\\?\\" + absolute
    return absolute
