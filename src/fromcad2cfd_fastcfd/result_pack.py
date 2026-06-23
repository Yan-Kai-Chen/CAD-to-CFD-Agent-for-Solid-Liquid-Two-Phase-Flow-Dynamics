"""Result Pack compiler for Controlled Runner outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_runner import run_controlled_runner_demo, validate_controlled_runner
from .file_io import ensure_dir, path_is_file, read_json_file, write_json_file, write_text_file


RESULT_PACK_SCHEMA_VERSION = "fastfluent_result_pack_v1"
RESULT_PACK_VALIDATION_SCHEMA_VERSION = "fastfluent_result_pack_validation_v1"
NATIVE_RESULT_SUMMARY_SCHEMA_VERSION = "fastfluent_native_result_summary_v1"


def compile_result_pack(
    controlled_run: str | Path,
    *,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Compile Controlled Runner output into an agent-facing result package."""

    run_path = _resolve_controlled_run_path(controlled_run)
    run = _read_json(run_path)
    root = Path(output_dir)
    ensure_dir(root)
    validation = validate_controlled_runner(run_path)
    run_result = run.get("run_result") if isinstance(run.get("run_result"), dict) else {}
    result_artifacts = run_result.get("artifacts") if isinstance(run_result.get("artifacts"), dict) else {}
    artifact_index = _artifact_index(run, result_artifacts)
    decision = _decision(run, validation, result_artifacts)
    artifacts = {
        "result_pack": str(root / "result_pack.json"),
        "decision_brief": str(root / "decision_brief.md"),
        "artifact_index": str(root / "artifact_index.json"),
        "agent_handoff": str(root / "agent_handoff.json"),
    }
    pack = {
        "schema_version": RESULT_PACK_SCHEMA_VERSION,
        "status": decision["status"],
        "source_controlled_run": str(run_path),
        "controlled_run_validation": validation,
        "case_id": run.get("case_id"),
        "case_type": run.get("case_type"),
        "recommended_route": run.get("recommended_route"),
        "runner_status": run.get("status"),
        "runner_mode": run.get("mode"),
        "solver_execution": run_result.get("solver_execution"),
        "evidence_level": decision["evidence_level"],
        "decision": decision,
        "artifact_index": artifact_index,
        "artifacts": artifacts,
        "usage_boundary": {
            "valid_for_agent_workflow_control": True,
            "valid_for_final_cfd_validation": False,
            "requires_fluent_or_reviewed_fastfluent_for_final_decision": True,
        },
    }
    handoff = {
        "schema_version": "fastfluent_agent_handoff_v1",
        "status": pack["status"],
        "evidence_level": pack["evidence_level"],
        "recommended_next_action": decision["recommended_next_action"],
        "do_not_claim_final_physics_validation": True,
        "source_result_pack": artifacts["result_pack"],
        "key_artifacts": decision["key_artifacts"],
    }
    _write_json(root / "result_pack.json", pack)
    _write_json(root / "artifact_index.json", {"schema_version": "fastfluent_artifact_index_v1", "artifacts": artifact_index})
    _write_json(root / "agent_handoff.json", handoff)
    write_text_file(root / "decision_brief.md", result_pack_markdown(pack))
    return pack


def compile_native_result_pack(
    native_result: str | Path,
    *,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Compile a native FastFluent result into the unified agent Result Pack."""

    source_path = _resolve_native_result_path(native_result)
    payload = _read_json(source_path)
    root = Path(output_dir)
    ensure_dir(root)
    summary = _native_result_summary(payload, source_path)
    decision = _native_decision(summary)
    artifact_index = _native_artifact_index(summary)
    artifacts = {
        "result_pack": str(root / "result_pack.json"),
        "decision_brief": str(root / "decision_brief.md"),
        "artifact_index": str(root / "artifact_index.json"),
        "agent_handoff": str(root / "agent_handoff.json"),
        "native_result_summary": str(root / "native_result_summary.json"),
    }
    pack = {
        "schema_version": RESULT_PACK_SCHEMA_VERSION,
        "status": decision["status"],
        "source_kind": "native_result",
        "source_native_result": str(source_path),
        "case_id": summary.get("case_id"),
        "case_type": summary.get("case_type"),
        "recommended_route": summary.get("result_kind"),
        "runner_status": summary.get("execution_status"),
        "runner_mode": "native_result_adapter",
        "solver_execution": summary.get("solver_execution"),
        "quality_status": summary.get("quality_status"),
        "evidence_level": decision["evidence_level"],
        "decision": decision,
        "native_result": summary,
        "artifact_index": artifact_index,
        "artifacts": artifacts,
        "usage_boundary": {
            "valid_for_agent_workflow_control": True,
            "valid_for_screening_decision": decision["can_support_screening_decision"],
            "valid_for_final_cfd_validation": False,
            "requires_fluent_or_reviewed_fastfluent_for_final_decision": True,
        },
    }
    handoff = {
        "schema_version": "fastfluent_agent_handoff_v1",
        "status": pack["status"],
        "quality_status": pack["quality_status"],
        "evidence_level": pack["evidence_level"],
        "recommended_next_action": decision["recommended_next_action"],
        "do_not_claim_final_physics_validation": True,
        "source_result_pack": artifacts["result_pack"],
        "source_native_result": str(source_path),
        "key_artifacts": decision["key_artifacts"],
        "agent_actions": decision.get("agent_actions", []),
    }
    _write_json(root / "result_pack.json", pack)
    _write_json(root / "native_result_summary.json", summary)
    _write_json(root / "artifact_index.json", {"schema_version": "fastfluent_artifact_index_v1", "artifacts": artifact_index})
    _write_json(root / "agent_handoff.json", handoff)
    write_text_file(root / "decision_brief.md", result_pack_markdown(pack))
    return pack


def validate_result_pack(result_pack: str | Path) -> dict[str, Any]:
    """Validate a Result Pack file or directory."""

    path = _resolve_result_pack_path(result_pack)
    if not path_is_file(path):
        return _validation_failed(["result_pack.json is missing."])
    try:
        payload = read_json_file(path)
    except json.JSONDecodeError as exc:
        return _validation_failed([f"result_pack.json is invalid JSON: {exc}"])

    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("schema_version") != RESULT_PACK_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {payload.get('schema_version')!r}")
    usage = payload.get("usage_boundary") if isinstance(payload.get("usage_boundary"), dict) else {}
    if usage.get("valid_for_final_cfd_validation") is not False:
        errors.append("Result Pack v1 must not claim final CFD validation.")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be an object.")
    else:
        for key in ("result_pack", "decision_brief", "artifact_index", "agent_handoff"):
            artifact_path = artifacts.get(key)
            if not isinstance(artifact_path, str) or not path_is_file(artifact_path):
                errors.append(f"Required result-pack artifact is missing: {key}")
    if payload.get("evidence_level") in {"no_solver_evidence", "workflow_fixture"}:
        warnings.append(f"Evidence level is {payload.get('evidence_level')}; use for workflow control only.")
    if payload.get("quality_status") == "warning":
        warnings.append("Native result quality is warning; use for screening only before repair or Fluent handoff.")
    if payload.get("quality_status") == "failed":
        warnings.append("Native result quality is failed; the pack is valid but blocked for downstream use.")

    status = "failed" if errors else "passed"
    return {
        "schema_version": RESULT_PACK_VALIDATION_SCHEMA_VERSION,
        "status": status,
        "passed": status == "passed",
        "result_pack_status": payload.get("status"),
        "quality_status": payload.get("quality_status"),
        "evidence_level": payload.get("evidence_level"),
        "errors": errors,
        "warnings": warnings,
    }


def run_result_pack_demo(output_dir: str | Path) -> dict[str, Any]:
    """Run the public M8 demo and compile an M9 Result Pack."""

    root = Path(output_dir)
    runner_demo = run_controlled_runner_demo(root)
    controlled_run_path = Path(runner_demo["outputs"]["artifacts"]["controlled_run"])
    pack = compile_result_pack(controlled_run_path, output_dir=root / "r")
    result = {
        "status": pack["status"],
        "operation": "result_pack_demo",
        "outputs": {
            "controlled_runner_demo": str(root),
            "result_pack_dir": str(root / "r"),
            "evidence_level": pack.get("evidence_level"),
            "solver_execution": pack.get("solver_execution"),
            "artifacts": {
                "controlled_run": str(controlled_run_path),
                "result_pack": str(root / "r" / "result_pack.json"),
                "decision_brief": str(root / "r" / "decision_brief.md"),
                "agent_handoff": str(root / "r" / "agent_handoff.json"),
            },
        },
        "errors": [],
    }
    _write_json(root / "demo_status.json", result)
    return result


def result_pack_markdown(pack: dict[str, Any]) -> str:
    """Render a concise agent decision brief."""

    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    lines = [
        "# FastFluent Result Pack",
        "",
        f"- Status: `{pack.get('status')}`",
        f"- Evidence level: `{pack.get('evidence_level')}`",
        f"- Quality status: `{pack.get('quality_status')}`",
        f"- Runner mode: `{pack.get('runner_mode')}`",
        f"- Solver execution: `{pack.get('solver_execution')}`",
        f"- Recommended route: `{pack.get('recommended_route')}`",
        "",
        "## Decision",
        "",
        f"- Recommended next action: `{decision.get('recommended_next_action')}`",
        f"- Can support physics decision: `{decision.get('can_support_physics_decision')}`",
        f"- Can support screening decision: `{decision.get('can_support_screening_decision')}`",
        f"- Can support workflow decision: `{decision.get('can_support_workflow_decision')}`",
        "",
        "## Rationale",
        "",
    ]
    rationale = decision.get("rationale", [])
    lines.extend(f"- {item}" for item in rationale) if rationale else lines.append("- None")
    lines.extend(["", "## Key Artifacts", ""])
    key_artifacts = decision.get("key_artifacts", [])
    lines.extend(f"- `{item}`" for item in key_artifacts) if key_artifacts else lines.append("- None")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This package is valid for agent workflow control.",
            "- It is not final CFD validation.",
            "- Final engineering decisions require Fluent or reviewed FastFluent evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def result_pack_validation_markdown(validation: dict[str, Any]) -> str:
    """Render Result Pack validation."""

    lines = [
        "# FastFluent Result Pack Validation",
        "",
        f"- Status: `{validation.get('status')}`",
        f"- Result pack status: `{validation.get('result_pack_status')}`",
        f"- Evidence level: `{validation.get('evidence_level')}`",
        f"- Quality status: `{validation.get('quality_status')}`",
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


def _decision(run: dict[str, Any], validation: dict[str, Any], result_artifacts: dict[str, Any]) -> dict[str, Any]:
    runner_status = str(run.get("status"))
    mode = str(run.get("mode"))
    run_result = run.get("run_result") if isinstance(run.get("run_result"), dict) else {}
    solver_execution = str(run_result.get("solver_execution"))
    key_artifacts = [str(value) for value in result_artifacts.values() if isinstance(value, str)]

    if not validation.get("passed"):
        return {
            "schema_version": "fastfluent_result_pack_decision_v1",
            "status": "blocked",
            "evidence_level": "invalid",
            "recommended_next_action": "repair_controlled_run",
            "can_support_workflow_decision": False,
            "can_support_physics_decision": False,
            "can_support_screening_decision": False,
            "key_artifacts": key_artifacts,
            "rationale": ["Controlled Runner validation failed."],
        }
    if solver_execution == "mock_backend_executed":
        return {
            "schema_version": "fastfluent_result_pack_decision_v1",
            "status": "workflow_validated_only",
            "evidence_level": "workflow_fixture",
            "recommended_next_action": "review_mock_artifacts_then_request_real_solver_or_fluent_run",
            "can_support_workflow_decision": True,
            "can_support_physics_decision": False,
            "can_support_screening_decision": False,
            "key_artifacts": key_artifacts,
            "rationale": [
                "A deterministic mock backend was executed.",
                "Mock outputs validate plumbing and reporting but are not numerical CFD evidence.",
            ],
        }
    if runner_status == "ready_not_executed" or mode == "dry_run":
        return {
            "schema_version": "fastfluent_result_pack_decision_v1",
            "status": "review_only",
            "evidence_level": "no_solver_evidence",
            "recommended_next_action": "request_explicit_solver_execution_approval_or_compile_fluent_plan",
            "can_support_workflow_decision": True,
            "can_support_physics_decision": False,
            "can_support_screening_decision": False,
            "key_artifacts": key_artifacts,
            "rationale": [
                "Execution was intentionally not attempted.",
                "The package can guide review, but it cannot support physics claims.",
            ],
        }
    return {
        "schema_version": "fastfluent_result_pack_decision_v1",
        "status": "advisory_native_evidence",
        "evidence_level": "native_advisory",
        "recommended_next_action": "review_qoi_pilot_decision_and_fluent_hints",
        "can_support_workflow_decision": True,
        "can_support_physics_decision": True,
        "can_support_screening_decision": True,
        "key_artifacts": key_artifacts,
        "rationale": [
            "A controlled native advisory run appears to be available.",
            "Final validation still requires Fluent or equivalent high-fidelity review.",
        ],
    }


def _native_result_summary(payload: dict[str, Any], source_path: Path) -> dict[str, Any]:
    kind = _native_result_kind(payload, source_path)
    artifacts = _collect_native_artifacts(payload)
    hardening = _find_hardening_summary(payload)
    agent_decision = _find_agent_decision(payload, hardening)
    qoi = _native_qoi(payload)
    warnings = _collect_list_values(payload, "warnings") + _collect_list_values(payload, "quality_warnings") + _collect_list_values(hardening, "warnings")
    blocking_errors = _collect_list_values(payload, "blocking_errors") + _collect_list_values(payload, "errors") + _collect_list_values(hardening, "blocking_errors")
    quality_status = _native_quality_status(payload, hardening)
    execution_status = str(payload.get("status") or "unknown")
    solver_execution = _native_solver_execution(payload, kind)
    return {
        "schema_version": NATIVE_RESULT_SUMMARY_SCHEMA_VERSION,
        "status": "success",
        "source_path": str(source_path),
        "result_kind": kind,
        "case_id": payload.get("case_id") or payload.get("case_name"),
        "case_type": payload.get("case_type") or kind,
        "execution_status": execution_status,
        "quality_status": quality_status,
        "solver_execution": solver_execution,
        "evidence_level": _native_evidence_level(quality_status, hardening),
        "qoi": qoi,
        "hardening_summary": hardening,
        "agent_decision": agent_decision,
        "warnings": warnings,
        "blocking_errors": blocking_errors,
        "artifacts": artifacts,
        "limitations": _collect_list_values(payload, "limitations"),
    }


def _native_decision(summary: dict[str, Any]) -> dict[str, Any]:
    execution_status = str(summary.get("execution_status"))
    quality_status = str(summary.get("quality_status"))
    existing = summary.get("agent_decision") if isinstance(summary.get("agent_decision"), dict) else {}
    key_artifacts = [str(value) for value in summary.get("artifacts", {}).values() if isinstance(value, str)]
    actions = list(existing.get("agent_actions", [])) if isinstance(existing.get("agent_actions"), list) else []
    if execution_status not in {"success", "passed"}:
        status = "blocked_native_evidence"
        evidence_level = "blocked_native_advisory"
        recommended = existing.get("recommended_next_action") or "repair_native_result_before_handoff"
        rationale = ["Native route did not complete successfully."]
        can_screen = False
        can_physics = False
        if not actions:
            actions = [{"action": "inspect_native_result_errors", "priority": "critical", "reason": "Execution did not complete successfully."}]
    elif quality_status == "passed":
        status = "advisory_native_evidence"
        evidence_level = summary.get("evidence_level") or "native_advisory"
        recommended = existing.get("recommended_next_action") or "package_as_advisory_fastfluent_evidence"
        rationale = ["Native route completed and passed S4 quality gates."]
        can_screen = True
        can_physics = True
    elif quality_status == "warning":
        status = "native_evidence_warning"
        evidence_level = summary.get("evidence_level") or "degraded_native_advisory"
        recommended = existing.get("recommended_next_action") or "use_for_screening_only_and_repair_before_fluent_handoff"
        rationale = ["Native route completed, but one or more S4 advisory quality gates were marginal."]
        can_screen = True
        can_physics = False
        if not actions:
            actions = [{"action": "repair_native_quality_before_fluent_handoff", "priority": "high", "reason": "Quality status is warning."}]
    else:
        status = "blocked_native_evidence"
        evidence_level = summary.get("evidence_level") or "blocked_native_advisory"
        recommended = existing.get("recommended_next_action") or "do_not_trust_native_evidence_repair_case"
        rationale = ["Native evidence failed or has unknown quality."]
        can_screen = False
        can_physics = False
        if not actions:
            actions = [{"action": "stop_and_repair_native_case", "priority": "critical", "reason": "Quality status is failed or unknown."}]
    return {
        "schema_version": "fastfluent_result_pack_decision_v1",
        "status": status,
        "evidence_level": evidence_level,
        "recommended_next_action": recommended,
        "can_support_workflow_decision": True,
        "can_support_screening_decision": can_screen,
        "can_support_physics_decision": can_physics,
        "can_support_final_cfd_validation": False,
        "key_artifacts": key_artifacts,
        "agent_actions": actions,
        "rationale": rationale,
    }


def _native_artifact_index(summary: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [{"scope": "native_result", "name": "source_path", "path": summary["source_path"], "exists": Path(summary["source_path"]).exists()}]
    for name, value in summary.get("artifacts", {}).items():
        if isinstance(value, str):
            entries.append({"scope": "native_result", "name": name, "path": value, "exists": Path(value).exists()})
    return entries


def _native_result_kind(payload: dict[str, Any], source_path: Path) -> str:
    schema = str(payload.get("schema_version") or "")
    operation = str(payload.get("operation") or "")
    if schema == "fastfluent_moving_obstacle_evidence_v1":
        return "moving_obstacle_motion_evidence"
    if schema == "fastfluent_quasi_steady_motion_v1":
        return "quasi_steady_motion_evidence"
    if schema == "fastfluent_transport_result_v1":
        return "unified_transport_coupling"
    if operation == "solve_steady_incompressible":
        return "steady_incompressible"
    if operation == "run_unstructured_case" or "case_status" in source_path.name:
        return "unstructured_case"
    return schema or operation or "native_result"


def _native_quality_status(payload: dict[str, Any], hardening: dict[str, Any]) -> str:
    if isinstance(payload.get("quality_status"), str):
        return str(payload["quality_status"])
    quasi = payload.get("quasi_steady") if isinstance(payload.get("quasi_steady"), dict) else {}
    if isinstance(quasi.get("quality_status"), str):
        return str(quasi["quality_status"])
    if isinstance(hardening.get("status"), str):
        return str(hardening["status"])
    qoi = payload.get("outputs", {}).get("qoi", {}) if isinstance(payload.get("outputs"), dict) else {}
    if isinstance(qoi, dict) and qoi.get("status") == "passed":
        return "passed"
    if payload.get("status") == "failed":
        return "failed"
    return "unknown"


def _native_evidence_level(quality_status: str, hardening: dict[str, Any]) -> str:
    if isinstance(hardening.get("evidence_level"), str):
        return str(hardening["evidence_level"])
    return {
        "passed": "native_advisory",
        "warning": "degraded_native_advisory",
        "failed": "blocked_native_advisory",
    }.get(quality_status, "native_advisory_unknown_quality")


def _native_solver_execution(payload: dict[str, Any], kind: str) -> str:
    outputs = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else {}
    if isinstance(outputs.get("solver_execution"), str):
        return str(outputs["solver_execution"])
    if kind == "quasi_steady_motion_evidence":
        return "quasi_steady_static_grid_sequence"
    if kind == "moving_obstacle_motion_evidence":
        return "moving_obstacle_static_grid_evidence"
    return str(payload.get("operation") or kind)


def _native_qoi(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("summary_qoi"), dict):
        return payload["summary_qoi"]
    quasi = payload.get("quasi_steady") if isinstance(payload.get("quasi_steady"), dict) else {}
    if isinstance(quasi.get("summary_qoi"), dict):
        return quasi["summary_qoi"]
    outputs = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else {}
    qoi = outputs.get("qoi") if isinstance(outputs.get("qoi"), dict) else {}
    if isinstance(qoi.get("metrics"), dict):
        return qoi["metrics"]
    return qoi


def _find_hardening_summary(payload: dict[str, Any]) -> dict[str, Any]:
    outputs = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else {}
    hardening = outputs.get("hardening_summary") if isinstance(outputs.get("hardening_summary"), dict) else {}
    if hardening:
        return hardening
    snapshots = payload.get("snapshots") if isinstance(payload.get("snapshots"), list) else []
    statuses = [item.get("solver_qoi", {}).get("hardening_status") for item in snapshots if isinstance(item, dict)]
    if statuses:
        return {"status": "failed" if "failed" in statuses else ("warning" if "warning" in statuses else "passed")}
    quasi = payload.get("quasi_steady") if isinstance(payload.get("quasi_steady"), dict) else {}
    if isinstance(quasi.get("quality_status"), str):
        return {"status": quasi["quality_status"]}
    return {}


def _find_agent_decision(payload: dict[str, Any], hardening: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("agent_decision"), dict):
        return payload["agent_decision"]
    if isinstance(hardening.get("decision"), dict):
        return hardening["decision"]
    quasi = payload.get("quasi_steady") if isinstance(payload.get("quasi_steady"), dict) else {}
    if isinstance(quasi.get("agent_decision"), dict):
        return quasi["agent_decision"]
    return {}


def _collect_native_artifacts(payload: dict[str, Any]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for mapping in _artifact_mappings(payload):
        for key, value in mapping.items():
            if isinstance(value, str):
                artifacts[str(key)] = value
    return dict(sorted(artifacts.items()))


def _artifact_mappings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    if isinstance(payload.get("artifacts"), dict):
        mappings.append(payload["artifacts"])
    outputs = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else {}
    if isinstance(outputs.get("artifacts"), dict):
        mappings.append(outputs["artifacts"])
    for key in ("obstacle_evidence", "quasi_steady"):
        item = payload.get(key)
        if isinstance(item, dict) and isinstance(item.get("artifacts"), dict):
            mappings.append(item["artifacts"])
    return mappings


def _collect_list_values(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _artifact_index(run: dict[str, Any], result_artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for scope, mapping in (("controlled_runner", run.get("artifacts")), ("run_result", result_artifacts)):
        if isinstance(mapping, dict):
            for name, value in mapping.items():
                if isinstance(value, str):
                    entries.append({"scope": scope, "name": name, "path": value, "exists": Path(value).exists()})
    return entries


def _resolve_controlled_run_path(controlled_run: str | Path) -> Path:
    path = Path(controlled_run)
    if path.is_dir():
        return path / "controlled_run.json"
    return path


def _resolve_result_pack_path(result_pack: str | Path) -> Path:
    path = Path(result_pack)
    if path.is_dir():
        return path / "result_pack.json"
    return path


def _resolve_native_result_path(native_result: str | Path) -> Path:
    path = Path(native_result)
    if path_is_file(path):
        return path
    if path.is_dir():
        for name in (
            "mo_summary.json",
            "qs_summary.json",
            "case_status.json",
            "status.json",
            "steady_status.json",
            "obstacle_status.json",
        ):
            candidate = path / name
            if path_is_file(candidate):
                return candidate
    return path


def _validation_failed(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": RESULT_PACK_VALIDATION_SCHEMA_VERSION,
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
