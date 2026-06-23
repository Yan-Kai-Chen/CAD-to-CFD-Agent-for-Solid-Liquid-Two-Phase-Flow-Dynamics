"""Execution Gate for auditing Route Plans before any controlled solver run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .file_io import ensure_dir, path_is_file, read_json_file, write_json_file, write_text_file
from .physics_validator import contract_has_blocking_errors, validate_physics
from .preflight import detect_fastcfd_environment
from .route_plan import run_route_plan_demo, validate_route_plan
from .schemas import read_job


EXECUTION_GATE_SCHEMA_VERSION = "fastfluent_execution_gate_v1"
EXECUTION_GATE_VALIDATION_SCHEMA_VERSION = "fastfluent_execution_gate_validation_v1"


def audit_execution_gate(
    route_plan: str | Path,
    *,
    output_dir: str | Path,
    source_root: str | None = None,
    execution_mode: str = "dry_run",
) -> dict[str, Any]:
    """Audit a Route Plan and write an execution package without running solvers."""

    if execution_mode != "dry_run":
        raise ValueError("Execution Gate v1 only supports execution_mode='dry_run'.")
    plan_path = _resolve_route_plan_path(route_plan)
    plan = _read_json(plan_path)
    root = Path(output_dir)
    ensure_dir(root)
    plan_validation = validate_route_plan(plan_path)
    approval_gate = plan.get("approval_gate") if isinstance(plan.get("approval_gate"), dict) else {}
    materialized = plan.get("materialized_job") if isinstance(plan.get("materialized_job"), dict) else {}
    job_audit = _audit_job(materialized.get("job_path"))
    preflight = detect_fastcfd_environment(source_root).to_dict()
    decisions = _gate_decision(
        plan=plan,
        plan_validation=plan_validation,
        approval_gate=approval_gate,
        job_audit=job_audit,
        preflight=preflight,
    )
    artifacts = {
        "execution_gate": str(root / "execution_gate.json"),
        "dry_run_ledger": str(root / "dry_run_ledger.json"),
        "runbook": str(root / "runbook.md"),
        "preflight": str(root / "preflight.json"),
    }
    gate = {
        "schema_version": EXECUTION_GATE_SCHEMA_VERSION,
        "status": decisions["status"],
        "execution_mode": execution_mode,
        "solver_execution": "not_attempted",
        "source_route_plan": str(plan_path),
        "recommended_route": plan.get("recommended_route"),
        "case_id": plan.get("case_id"),
        "case_type": plan.get("case_type"),
        "plan_validation": plan_validation,
        "approval_gate": approval_gate,
        "job_audit": job_audit,
        "environment_preflight": preflight,
        "decision": decisions,
        "commands_after_approval": approval_gate.get("commands_after_approval", []),
        "artifacts": artifacts,
        "execution_boundary": {
            "gate_executes_solver": False,
            "gate_launches_fluent": False,
            "gate_runs_arbitrary_code": False,
            "explicit_user_approval_required_for_commands": True,
        },
    }
    ledger = {
        "schema_version": "fastfluent_dry_run_ledger_v1",
        "status": gate["status"],
        "execution_mode": execution_mode,
        "solver_execution": "not_attempted",
        "checked_artifacts": _checked_artifacts(plan, materialized),
        "blocking_errors": decisions["blocking_errors"],
        "warnings": decisions["warnings"],
        "commands_after_approval": gate["commands_after_approval"],
    }
    _write_json(root / "execution_gate.json", gate)
    _write_json(root / "dry_run_ledger.json", ledger)
    _write_json(root / "preflight.json", preflight)
    write_text_file(root / "runbook.md", execution_gate_markdown(gate))
    return gate


def validate_execution_gate(execution_gate: str | Path) -> dict[str, Any]:
    """Validate an execution gate output file or directory."""

    path = _resolve_execution_gate_path(execution_gate)
    if not path_is_file(path):
        return _validation_failed(["execution_gate.json is missing."])
    try:
        gate = read_json_file(path)
    except json.JSONDecodeError as exc:
        return _validation_failed([f"execution_gate.json is invalid JSON: {exc}"])

    errors: list[str] = []
    warnings: list[str] = []
    if gate.get("schema_version") != EXECUTION_GATE_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {gate.get('schema_version')!r}")
    if gate.get("execution_mode") != "dry_run":
        errors.append("Execution Gate v1 must be dry_run.")
    if gate.get("solver_execution") != "not_attempted":
        errors.append("Execution Gate must not claim solver execution.")
    boundary = gate.get("execution_boundary") if isinstance(gate.get("execution_boundary"), dict) else {}
    if boundary.get("gate_executes_solver") is not False:
        errors.append("execution_boundary.gate_executes_solver must be false.")
    artifacts = gate.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be an object.")
    else:
        for key in ("execution_gate", "dry_run_ledger", "runbook", "preflight"):
            artifact_path = artifacts.get(key)
            if not isinstance(artifact_path, str) or not path_is_file(artifact_path):
                errors.append(f"Required execution artifact is missing: {key}")
    if gate.get("status") == "blocked":
        warnings.append("Execution Gate is blocked; do not run commands_after_approval.")

    status = "failed" if errors else "passed"
    return {
        "schema_version": EXECUTION_GATE_VALIDATION_SCHEMA_VERSION,
        "status": status,
        "passed": status == "passed",
        "gate_status": gate.get("status"),
        "recommended_route": gate.get("recommended_route"),
        "errors": errors,
        "warnings": warnings,
    }


def run_execution_gate_demo(output_dir: str | Path) -> dict[str, Any]:
    """Run the public route-plan demo and audit it with Execution Gate."""

    root = Path(output_dir)
    plan_demo = run_route_plan_demo(root)
    plan_path = Path(plan_demo["outputs"]["artifacts"]["route_plan"])
    gate = audit_execution_gate(plan_path, output_dir=root / "g")
    result = {
        "status": gate["status"],
        "operation": "execution_gate_demo",
        "outputs": {
            "route_plan_demo": str(root),
            "execution_gate_dir": str(root / "g"),
            "recommended_route": gate.get("recommended_route"),
            "solver_execution": gate.get("solver_execution"),
            "artifacts": {
                "route_plan": str(plan_path),
                "execution_gate": str(root / "g" / "execution_gate.json"),
                "dry_run_ledger": str(root / "g" / "dry_run_ledger.json"),
                "runbook": str(root / "g" / "runbook.md"),
            },
        },
        "errors": gate.get("decision", {}).get("blocking_errors", []),
    }
    _write_json(root / "demo_status.json", result)
    return result


def execution_gate_markdown(gate: dict[str, Any]) -> str:
    """Render a dry-run execution gate report."""

    decision = gate.get("decision", {})
    lines = [
        "# FastFluent Execution Gate",
        "",
        f"- Status: `{gate.get('status')}`",
        f"- Execution mode: `{gate.get('execution_mode')}`",
        f"- Solver execution: `{gate.get('solver_execution')}`",
        f"- Recommended route: `{gate.get('recommended_route')}`",
        f"- Case ID: `{gate.get('case_id')}`",
        "",
        "## Decision",
        "",
        f"- Ready after approval: `{decision.get('ready_after_approval')}`",
        f"- Environment status: `{decision.get('environment_status')}`",
        "",
        "## Required Reviews",
        "",
    ]
    reviews = gate.get("approval_gate", {}).get("required_reviews", [])
    lines.extend(f"- {item}" for item in reviews) if reviews else lines.append("- None")
    lines.extend(["", "## Commands After Explicit Approval", ""])
    commands = gate.get("commands_after_approval", [])
    lines.extend(f"- `{item}`" for item in commands) if commands else lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    warnings = decision.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Blocking Errors", ""])
    errors = decision.get("blocking_errors", [])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Execution Gate v1 is a dry-run audit layer.",
            "- It does not run FastFluent or Fluent.",
            "- Commands in this runbook require explicit user approval before execution.",
            "",
        ]
    )
    return "\n".join(lines)


def execution_gate_validation_markdown(validation: dict[str, Any]) -> str:
    """Render an execution gate validation result."""

    lines = [
        "# FastFluent Execution Gate Validation",
        "",
        f"- Status: `{validation.get('status')}`",
        f"- Gate status: `{validation.get('gate_status')}`",
        f"- Recommended route: `{validation.get('recommended_route')}`",
        "",
        "## Warnings",
        "",
    ]
    warnings = validation.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Errors", ""])
    errors = validation.get("errors", [])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _gate_decision(
    *,
    plan: dict[str, Any],
    plan_validation: dict[str, Any],
    approval_gate: dict[str, Any],
    job_audit: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    blocking_errors: list[str] = []
    warnings: list[str] = []
    if not plan_validation.get("passed"):
        blocking_errors.extend(f"Route plan: {item}" for item in plan_validation.get("errors", []))
    if approval_gate.get("status") == "blocked":
        blocking_errors.extend(f"Approval gate: {item}" for item in approval_gate.get("blocking_errors", []))
    if job_audit.get("status") == "failed":
        blocking_errors.extend(f"Job audit: {item}" for item in job_audit.get("errors", []))
    elif job_audit.get("status") == "warning":
        warnings.extend(f"Job audit: {item}" for item in job_audit.get("warnings", []))
    if preflight.get("status") == "skipped":
        warnings.append("FastFluent source preflight was skipped or source root is unavailable.")
    elif preflight.get("status") == "partial":
        warnings.extend(f"Preflight: {item}" for item in preflight.get("known_blockers", []))
        warnings.append("FastFluent environment preflight is partial.")
    ready = not blocking_errors and approval_gate.get("status") == "ready_for_approval"
    return {
        "schema_version": "fastfluent_execution_gate_decision_v1",
        "status": "blocked" if blocking_errors else ("ready_for_approval" if ready else "review_only"),
        "ready_after_approval": ready,
        "environment_status": preflight.get("status"),
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "notes": [
            "Execution Gate performs validation and environment preflight only.",
            "Commands are copied for review and are not executed by this command.",
        ],
    }


def _audit_job(job_path_text: Any) -> dict[str, Any]:
    if not isinstance(job_path_text, str) or not job_path_text:
        return {"schema_version": "fastfluent_execution_job_audit_v1", "status": "skipped", "errors": [], "warnings": ["No materialized job_path is available."]}
    path = Path(job_path_text)
    if not path_is_file(path):
        return {"schema_version": "fastfluent_execution_job_audit_v1", "status": "failed", "errors": [f"job_path does not exist: {path}"], "warnings": []}
    try:
        job = read_job(path)
        physics = validate_physics(job)
    except Exception as exc:
        return {"schema_version": "fastfluent_execution_job_audit_v1", "status": "failed", "errors": [str(exc)], "warnings": []}
    warnings = list(physics.checks.get("warnings", []))
    errors = list(physics.checks.get("errors", []))
    status = "failed" if contract_has_blocking_errors(physics) else ("warning" if warnings else "passed")
    return {
        "schema_version": "fastfluent_execution_job_audit_v1",
        "status": status,
        "job_path": str(path),
        "case_type": job.case_type,
        "backend": job.backend,
        "physics_status": physics.status,
        "physics_contract": physics.to_dict(),
        "errors": errors,
        "warnings": warnings,
    }


def _checked_artifacts(plan: dict[str, Any], materialized: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key, value in (plan.get("artifacts") or {}).items():
        if isinstance(value, str):
            entries.append({"name": key, "path": value, "exists": Path(value).exists()})
    for key in ("job_path", "physics_passport_path", "job_mapping_path"):
        value = materialized.get(key)
        if isinstance(value, str):
            entries.append({"name": key, "path": value, "exists": Path(value).exists()})
    return entries


def _resolve_route_plan_path(route_plan: str | Path) -> Path:
    path = Path(route_plan)
    if path.is_dir():
        return path / "route_plan.json"
    return path


def _resolve_execution_gate_path(execution_gate: str | Path) -> Path:
    path = Path(execution_gate)
    if path.is_dir():
        return path / "execution_gate.json"
    return path


def _validation_failed(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": EXECUTION_GATE_VALIDATION_SCHEMA_VERSION,
        "status": "failed",
        "passed": False,
        "errors": errors,
        "warnings": [],
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = read_json_file(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return write_json_file(path, payload)
