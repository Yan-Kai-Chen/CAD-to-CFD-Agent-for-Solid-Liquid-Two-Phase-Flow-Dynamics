"""Controlled Runner for post-gate FastFluent execution bookkeeping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .execution_gate import run_execution_gate_demo, validate_execution_gate
from .file_io import ensure_dir, path_is_file, read_json_file, write_json_file, write_text_file
from .mock_runner import run_mock_job


CONTROLLED_RUNNER_SCHEMA_VERSION = "fastfluent_controlled_runner_v1"
CONTROLLED_RUNNER_VALIDATION_SCHEMA_VERSION = "fastfluent_controlled_runner_validation_v1"


def run_controlled_runner(
    execution_gate: str | Path,
    *,
    output_dir: str | Path,
    mode: str = "dry_run",
    approval_id: str | None = None,
) -> dict[str, Any]:
    """Create a controlled execution ledger and optionally run an allowed mock backend."""

    if mode not in {"dry_run", "mock"}:
        raise ValueError("Controlled Runner v1 supports mode='dry_run' or mode='mock'.")

    gate_path = _resolve_execution_gate_path(execution_gate)
    gate = _read_json(gate_path)
    root = Path(output_dir)
    ensure_dir(root)
    validation = validate_execution_gate(gate_path)
    job = gate.get("job_audit") if isinstance(gate.get("job_audit"), dict) else {}
    commands = gate.get("commands_after_approval") if isinstance(gate.get("commands_after_approval"), list) else []
    artifacts = {
        "controlled_run": str(root / "controlled_run.json"),
        "command_ledger": str(root / "command_ledger.json"),
        "execution_transcript": str(root / "execution_transcript.md"),
    }
    blocking_errors: list[str] = []
    warnings: list[str] = []
    run_result: dict[str, Any] = {
        "schema_version": "fastfluent_controlled_run_result_v1",
        "status": "not_executed",
        "solver_execution": "not_attempted",
        "backend": job.get("backend"),
        "artifacts": {},
        "message": "Controlled Runner v1 recorded the execution plan without running a solver.",
    }

    if not validation.get("passed"):
        blocking_errors.extend(f"Execution gate: {item}" for item in validation.get("errors", []))
    if gate.get("status") != "ready_for_approval":
        warnings.append(f"Execution gate status is {gate.get('status')}; do not run solver commands automatically.")

    if mode == "mock":
        if not approval_id:
            blocking_errors.append("Mock execution mode requires an explicit approval_id.")
        elif job.get("backend") != "mock":
            blocking_errors.append(f"Mock execution mode requires backend='mock'; found {job.get('backend')!r}.")
        elif blocking_errors:
            pass
        else:
            result = run_mock_job(str(job.get("job_path")))
            run_result = {
                "schema_version": "fastfluent_controlled_run_result_v1",
                "status": result.get("status"),
                "solver_execution": "mock_backend_executed",
                "backend": "mock",
                "result": result,
                "artifacts": result.get("outputs", {}).get("artifacts", {}),
                "message": "Deterministic mock backend executed under Controlled Runner.",
            }
            if result.get("status") != "success":
                blocking_errors.append("Mock backend did not complete successfully.")

    status = "blocked" if blocking_errors else ("success" if mode == "mock" and run_result.get("status") == "success" else "ready_not_executed")
    runner = {
        "schema_version": CONTROLLED_RUNNER_SCHEMA_VERSION,
        "status": status,
        "mode": mode,
        "source_execution_gate": str(gate_path),
        "case_id": gate.get("case_id"),
        "case_type": gate.get("case_type"),
        "recommended_route": gate.get("recommended_route"),
        "gate_validation": validation,
        "job": {
            "status": job.get("status"),
            "job_path": job.get("job_path"),
            "backend": job.get("backend"),
            "case_type": job.get("case_type"),
            "physics_status": job.get("physics_status"),
        },
        "approval": {
            "approval_id": approval_id,
            "approval_required_for_real_solver": True,
            "real_solver_execution_supported_by_m8": False,
            "mock_or_dry_run_only": True,
        },
        "command_policy": {
            "commands_recorded": len(commands),
            "commands_executed": 0,
            "real_solver_commands_executed": 0,
            "arbitrary_code_execution_allowed": False,
        },
        "run_result": run_result,
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "artifacts": artifacts,
        "execution_boundary": {
            "runner_launches_fluent": False,
            "runner_executes_real_fastfluent": False,
            "runner_executes_mock_backend": mode == "mock" and status == "success",
            "real_solver_execution_requires_future_explicit_adapter": True,
        },
    }
    ledger = {
        "schema_version": "fastfluent_controlled_command_ledger_v1",
        "status": status,
        "mode": mode,
        "commands_after_approval": commands,
        "commands_executed": [],
        "blocked_real_solver_execution": True,
        "blocking_errors": blocking_errors,
        "warnings": warnings,
    }
    _write_json(root / "controlled_run.json", runner)
    _write_json(root / "command_ledger.json", ledger)
    write_text_file(root / "execution_transcript.md", controlled_runner_markdown(runner))
    return runner


def validate_controlled_runner(controlled_run: str | Path) -> dict[str, Any]:
    """Validate a Controlled Runner output file or directory."""

    path = _resolve_controlled_run_path(controlled_run)
    if not path_is_file(path):
        return _validation_failed(["controlled_run.json is missing."])
    try:
        payload = read_json_file(path)
    except json.JSONDecodeError as exc:
        return _validation_failed([f"controlled_run.json is invalid JSON: {exc}"])

    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("schema_version") != CONTROLLED_RUNNER_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {payload.get('schema_version')!r}")
    boundary = payload.get("execution_boundary") if isinstance(payload.get("execution_boundary"), dict) else {}
    if boundary.get("runner_launches_fluent") is not False:
        errors.append("Controlled Runner v1 must not launch Fluent.")
    if boundary.get("runner_executes_real_fastfluent") is not False:
        errors.append("Controlled Runner v1 must not claim real FastFluent execution.")
    policy = payload.get("command_policy") if isinstance(payload.get("command_policy"), dict) else {}
    if policy.get("real_solver_commands_executed") not in {0, None}:
        errors.append("Controlled Runner v1 must not execute real solver commands.")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be an object.")
    else:
        for key in ("controlled_run", "command_ledger", "execution_transcript"):
            artifact_path = artifacts.get(key)
            if not isinstance(artifact_path, str) or not path_is_file(artifact_path):
                errors.append(f"Required controlled-run artifact is missing: {key}")
    if payload.get("status") == "blocked":
        warnings.append("Controlled Runner is blocked; do not use as solver evidence.")

    status = "failed" if errors else "passed"
    return {
        "schema_version": CONTROLLED_RUNNER_VALIDATION_SCHEMA_VERSION,
        "status": status,
        "passed": status == "passed",
        "controlled_run_status": payload.get("status"),
        "mode": payload.get("mode"),
        "errors": errors,
        "warnings": warnings,
    }


def run_controlled_runner_demo(output_dir: str | Path) -> dict[str, Any]:
    """Run the public M7 demo and record an M8 dry-run execution ledger."""

    root = Path(output_dir)
    gate_demo = run_execution_gate_demo(root)
    gate_path = Path(gate_demo["outputs"]["artifacts"]["execution_gate"])
    runner = run_controlled_runner(gate_path, output_dir=root / "x", mode="dry_run")
    result = {
        "status": runner["status"],
        "operation": "controlled_runner_demo",
        "outputs": {
            "execution_gate_demo": str(root),
            "controlled_run_dir": str(root / "x"),
            "solver_execution": runner["run_result"].get("solver_execution"),
            "artifacts": {
                "execution_gate": str(gate_path),
                "controlled_run": str(root / "x" / "controlled_run.json"),
                "command_ledger": str(root / "x" / "command_ledger.json"),
                "execution_transcript": str(root / "x" / "execution_transcript.md"),
            },
        },
        "errors": runner.get("blocking_errors", []),
    }
    _write_json(root / "demo_status.json", result)
    return result


def controlled_runner_markdown(runner: dict[str, Any]) -> str:
    """Render a controlled-run transcript."""

    run_result = runner.get("run_result", {}) if isinstance(runner.get("run_result"), dict) else {}
    lines = [
        "# FastFluent Controlled Runner",
        "",
        f"- Status: `{runner.get('status')}`",
        f"- Mode: `{runner.get('mode')}`",
        f"- Recommended route: `{runner.get('recommended_route')}`",
        f"- Solver execution: `{run_result.get('solver_execution')}`",
        f"- Backend: `{runner.get('job', {}).get('backend')}`",
        "",
        "## Boundary",
        "",
        "- Controlled Runner v1 does not launch Fluent.",
        "- Controlled Runner v1 does not execute real FastFluent.",
        "- Real solver execution requires a future explicit adapter and user approval.",
        "",
        "## Warnings",
        "",
    ]
    warnings = runner.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Blocking Errors", ""])
    errors = runner.get("blocking_errors", [])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def controlled_runner_validation_markdown(validation: dict[str, Any]) -> str:
    """Render Controlled Runner validation."""

    lines = [
        "# FastFluent Controlled Runner Validation",
        "",
        f"- Status: `{validation.get('status')}`",
        f"- Controlled run status: `{validation.get('controlled_run_status')}`",
        f"- Mode: `{validation.get('mode')}`",
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


def _resolve_execution_gate_path(execution_gate: str | Path) -> Path:
    path = Path(execution_gate)
    if path.is_dir():
        return path / "execution_gate.json"
    return path


def _resolve_controlled_run_path(controlled_run: str | Path) -> Path:
    path = Path(controlled_run)
    if path.is_dir():
        return path / "controlled_run.json"
    return path


def _validation_failed(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": CONTROLLED_RUNNER_VALIDATION_SCHEMA_VERSION,
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
