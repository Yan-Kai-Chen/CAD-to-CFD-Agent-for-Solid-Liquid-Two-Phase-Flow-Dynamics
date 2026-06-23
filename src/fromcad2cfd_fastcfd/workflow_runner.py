"""S7 full FastFluent workflow runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_runner import run_controlled_runner
from .execution_gate import audit_execution_gate
from .file_io import ensure_dir, write_json_file, write_text_file
from .flow_pack import build_flow_pack, validate_flow_pack
from .result_pack import compile_native_result_pack, compile_result_pack, validate_result_pack
from .route_plan import compile_route_plan
from .route_selector import select_route
from .transport_core import run_transport_coupling_demo


WORKFLOW_RUNNER_SCHEMA_VERSION = "fastfluent_workflow_runner_v1"
WORKFLOW_STAGE_STATUS_SCHEMA_VERSION = "fastfluent_workflow_stage_status_v1"
WORKFLOW_AGENT_DECISION_SCHEMA_VERSION = "fastfluent_workflow_agent_decision_v1"


def run_workflow(
    case_file: str | Path,
    *,
    output_dir: str | Path,
    mode: str = "dry_run",
    mesh_file: str | Path | None = None,
    mesh_mode: str = "auto",
    required_patches: tuple[str, ...] | None = None,
    native_route: str = "transport",
    transport_quantity: str = "alpha",
    source_root: str | None = None,
) -> dict[str, Any]:
    """Run the S7 controlled agent workflow.

    The runner orchestrates existing gates and evidence modules. It does not
    launch Fluent, execute arbitrary code, or run unbounded native solvers.
    """

    if mode not in {"dry_run", "native_advisory"}:
        raise ValueError("S7 workflow mode must be 'dry_run' or 'native_advisory'.")
    if native_route != "transport":
        raise ValueError("S7 native_advisory currently supports native_route='transport' only.")

    root = Path(output_dir)
    ensure_dir(root)
    stages: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {
        "workflow_manifest": str(root / "workflow_manifest.json"),
        "stage_status": str(root / "stage_status.json"),
        "agent_decision": str(root / "agent_decision.json"),
        "workflow_report": str(root / "workflow_report.md"),
        "workflow_status": str(root / "workflow_status.json"),
    }

    try:
        flow_pack = build_flow_pack(
            case_file,
            output_dir=root / "01_flow_pack",
            mesh_file=mesh_file,
            mesh_mode=mesh_mode,
            required_patches=required_patches,
        )
        flow_validation = validate_flow_pack(root / "01_flow_pack")
        artifacts["flow_pack"] = str(root / "01_flow_pack" / "flow_pack.json")
        stages.append(_stage("flow_pack", flow_pack.get("status"), artifacts={"flow_pack": artifacts["flow_pack"]}, validation=flow_validation))
        if flow_pack.get("status") == "failed" or not flow_validation.get("passed"):
            return _finalize_workflow(
                root,
                status="blocked",
                mode=mode,
                stages=stages,
                artifacts=artifacts,
                result_pack={},
                blocking_errors=_prefixed_errors("flow_pack", flow_validation.get("errors", [])),
                warnings=flow_validation.get("warnings", []),
                recommended_next_action="repair_flow_pack_before_workflow_execution",
            )

        selection = select_route(root / "01_flow_pack", output_dir=root / "02_route_selection")
        artifacts["route_selection"] = str(root / "02_route_selection" / "route_selection.json")
        stages.append(_stage("route_selection", selection.get("status"), artifacts={"route_selection": artifacts["route_selection"]}))
        if selection.get("status") == "blocked":
            return _finalize_workflow(
                root,
                status="blocked",
                mode=mode,
                stages=stages,
                artifacts=artifacts,
                result_pack={},
                blocking_errors=["route_selection blocked"],
                warnings=[],
                recommended_next_action="repair_route_selection_inputs",
            )

        plan = compile_route_plan(root / "02_route_selection", output_dir=root / "03_route_plan")
        artifacts["route_plan"] = str(root / "03_route_plan" / "route_plan.json")
        stages.append(_stage("route_plan", plan.get("status"), artifacts={"route_plan": artifacts["route_plan"]}, warnings=plan.get("warnings", []), errors=plan.get("errors", [])))

        gate = audit_execution_gate(root / "03_route_plan", output_dir=root / "04_execution_gate", source_root=source_root)
        artifacts["execution_gate"] = str(root / "04_execution_gate" / "execution_gate.json")
        stages.append(
            _stage(
                "execution_gate",
                gate.get("status"),
                artifacts={"execution_gate": artifacts["execution_gate"]},
                warnings=gate.get("decision", {}).get("warnings", []),
                errors=gate.get("decision", {}).get("blocking_errors", []),
            )
        )

        controlled = run_controlled_runner(root / "04_execution_gate", output_dir=root / "05_controlled_runner", mode="dry_run")
        artifacts["controlled_run"] = str(root / "05_controlled_runner" / "controlled_run.json")
        stages.append(
            _stage(
                "controlled_runner",
                controlled.get("status"),
                artifacts={"controlled_run": artifacts["controlled_run"]},
                warnings=controlled.get("warnings", []),
                errors=controlled.get("blocking_errors", []),
            )
        )

        if mode == "native_advisory":
            native = run_transport_coupling_demo(root / "06_native_result", quantity=transport_quantity)
            artifacts["native_result"] = str(root / "06_native_result" / "status.json")
            stages.append(
                _stage(
                    "native_advisory",
                    native.get("quality_status") or native.get("status"),
                    artifacts={"native_result": artifacts["native_result"]},
                    warnings=native.get("warnings", []),
                    errors=native.get("blocking_errors", []) or native.get("errors", []),
                )
            )
            if native.get("quality_status") not in {"passed", "warning"}:
                return _finalize_workflow(
                    root,
                    status="blocked_native_evidence",
                    mode=mode,
                    stages=stages,
                    artifacts=artifacts,
                    result_pack={},
                    blocking_errors=native.get("blocking_errors", []) or native.get("errors", []),
                    warnings=native.get("warnings", []),
                    recommended_next_action="repair_native_evidence_before_result_pack",
                )
            result_pack = compile_native_result_pack(root / "06_native_result" / "status.json", output_dir=root / "07_result_pack")
        else:
            result_pack = compile_result_pack(root / "05_controlled_runner", output_dir=root / "07_result_pack")

        artifacts["result_pack"] = str(root / "07_result_pack" / "result_pack.json")
        result_validation = validate_result_pack(root / "07_result_pack")
        stages.append(
            _stage(
                "result_pack",
                result_pack.get("status"),
                artifacts={"result_pack": artifacts["result_pack"]},
                validation=result_validation,
                warnings=result_validation.get("warnings", []),
                errors=result_validation.get("errors", []),
            )
        )
        if not result_validation.get("passed"):
            return _finalize_workflow(
                root,
                status="blocked",
                mode=mode,
                stages=stages,
                artifacts=artifacts,
                result_pack=result_pack,
                blocking_errors=_prefixed_errors("result_pack", result_validation.get("errors", [])),
                warnings=result_validation.get("warnings", []),
                recommended_next_action="repair_result_pack",
            )

        return _finalize_workflow(
            root,
            status=_workflow_status_from_result_pack(result_pack),
            mode=mode,
            stages=stages,
            artifacts=artifacts,
            result_pack=result_pack,
            blocking_errors=[],
            warnings=_collect_stage_warnings(stages),
            recommended_next_action=result_pack.get("decision", {}).get("recommended_next_action", "review_workflow_outputs"),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _finalize_workflow(
            root,
            status="failed",
            mode=mode,
            stages=stages,
            artifacts=artifacts,
            result_pack={},
            blocking_errors=[str(exc)],
            warnings=[],
            recommended_next_action="repair_workflow_exception",
        )


def run_workflow_demo(output_dir: str | Path, *, mode: str = "native_advisory") -> dict[str, Any]:
    """Run the public S7 channel-flow workflow demo."""

    return run_workflow(
        "examples/fastcfd/casespec_v3/channel_flow_case.json",
        output_dir=output_dir,
        mode=mode,
        mesh_mode="structured-demo",
        transport_quantity="alpha",
    )


def workflow_markdown(workflow: dict[str, Any]) -> str:
    """Render the S7 workflow report."""

    lines = [
        "# FastFluent S7 Workflow Runner",
        "",
        f"- Status: `{workflow.get('status')}`",
        f"- Mode: `{workflow.get('mode')}`",
        f"- Case ID: `{workflow.get('case_id')}`",
        f"- Recommended next action: `{workflow.get('agent_decision', {}).get('recommended_next_action')}`",
        f"- Result Pack: `{workflow.get('artifacts', {}).get('result_pack')}`",
        "",
        "## Stages",
        "",
    ]
    for stage in workflow.get("stages", []):
        lines.append(f"- `{stage.get('stage')}`: `{stage.get('status')}`")
    lines.extend(["", "## Agent Decision", ""])
    decision = workflow.get("agent_decision", {})
    lines.append(f"- Can support workflow decision: `{decision.get('can_support_workflow_decision')}`")
    lines.append(f"- Can support screening decision: `{decision.get('can_support_screening_decision')}`")
    lines.append(f"- Can support final CFD validation: `{decision.get('can_support_final_cfd_validation')}`")
    lines.extend(["", "## Warnings", ""])
    warnings = workflow.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Blocking Errors", ""])
    errors = workflow.get("blocking_errors", [])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- S7 orchestrates bounded FastFluent workflow stages.",
            "- It does not launch Fluent.",
            "- `native_advisory` currently runs the S6 transport evidence route only.",
            "- Result Packs remain advisory and are not final CFD validation.",
            "",
        ]
    )
    return "\n".join(lines)


def _finalize_workflow(
    root: Path,
    *,
    status: str,
    mode: str,
    stages: list[dict[str, Any]],
    artifacts: dict[str, str],
    result_pack: dict[str, Any],
    blocking_errors: list[str],
    warnings: list[str],
    recommended_next_action: str,
) -> dict[str, Any]:
    case_id = _first_non_empty([_stage_case_id(stages), result_pack.get("case_id")])
    agent_decision = _agent_decision(
        status=status,
        mode=mode,
        result_pack=result_pack,
        recommended_next_action=recommended_next_action,
        blocking_errors=blocking_errors,
    )
    workflow = {
        "schema_version": WORKFLOW_RUNNER_SCHEMA_VERSION,
        "status": status,
        "mode": mode,
        "case_id": case_id,
        "stages": stages,
        "result_pack": _compact_result_pack(result_pack),
        "agent_decision": agent_decision,
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "artifacts": artifacts,
        "execution_boundary": {
            "workflow_launches_fluent": False,
            "workflow_runs_arbitrary_code": False,
            "native_advisory_is_bounded": mode == "native_advisory",
            "valid_for_final_cfd_validation": False,
        },
    }
    stage_status = {
        "schema_version": WORKFLOW_STAGE_STATUS_SCHEMA_VERSION,
        "status": status,
        "mode": mode,
        "stages": stages,
        "blocking_errors": blocking_errors,
        "warnings": warnings,
    }
    _write_json(root / "workflow_manifest.json", workflow)
    _write_json(root / "stage_status.json", stage_status)
    _write_json(root / "agent_decision.json", agent_decision)
    _write_json(root / "workflow_status.json", {"schema_version": "fastfluent_workflow_status_v1", "status": status, "artifacts": artifacts})
    write_text_file(root / "workflow_report.md", workflow_markdown(workflow))
    return workflow


def _stage(
    stage: str,
    status: Any,
    *,
    artifacts: dict[str, str] | None = None,
    validation: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": str(status or "unknown"),
        "artifacts": artifacts or {},
        "validation": validation or {},
        "warnings": warnings or [],
        "errors": errors or [],
    }


def _agent_decision(
    *,
    status: str,
    mode: str,
    result_pack: dict[str, Any],
    recommended_next_action: str,
    blocking_errors: list[str],
) -> dict[str, Any]:
    pack_decision = result_pack.get("decision") if isinstance(result_pack.get("decision"), dict) else {}
    return {
        "schema_version": WORKFLOW_AGENT_DECISION_SCHEMA_VERSION,
        "status": status,
        "mode": mode,
        "recommended_next_action": recommended_next_action,
        "can_support_workflow_decision": not blocking_errors,
        "can_support_screening_decision": bool(pack_decision.get("can_support_screening_decision", False)),
        "can_support_physics_decision": bool(pack_decision.get("can_support_physics_decision", False)),
        "can_support_final_cfd_validation": False,
        "result_pack_status": result_pack.get("status"),
        "result_pack_evidence_level": result_pack.get("evidence_level"),
        "required_human_review": True,
        "boundary": "Agent workflow control and FastFluent screening only; not final Fluent validation.",
    }


def _workflow_status_from_result_pack(result_pack: dict[str, Any]) -> str:
    pack_status = str(result_pack.get("status") or "")
    if pack_status == "advisory_native_evidence":
        return "native_advisory_complete"
    if pack_status == "native_evidence_warning":
        return "native_advisory_warning"
    if pack_status in {"review_only", "workflow_validated_only"}:
        return "review_only"
    if pack_status == "blocked_native_evidence":
        return "blocked"
    return pack_status or "unknown"


def _compact_result_pack(result_pack: dict[str, Any]) -> dict[str, Any]:
    if not result_pack:
        return {}
    return {
        "status": result_pack.get("status"),
        "evidence_level": result_pack.get("evidence_level"),
        "quality_status": result_pack.get("quality_status"),
        "solver_execution": result_pack.get("solver_execution"),
        "usage_boundary": result_pack.get("usage_boundary"),
        "artifacts": result_pack.get("artifacts"),
    }


def _collect_stage_warnings(stages: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for stage in stages:
        for item in stage.get("warnings", []):
            warnings.append(f"{stage.get('stage')}: {item}")
    return warnings


def _prefixed_errors(prefix: str, errors: list[str]) -> list[str]:
    return [f"{prefix}: {item}" for item in errors] if errors else [f"{prefix}: failed"]


def _stage_case_id(stages: list[dict[str, Any]]) -> str | None:
    for stage in stages:
        validation = stage.get("validation")
        if isinstance(validation, dict) and validation.get("case_id"):
            return str(validation["case_id"])
    return None


def _first_non_empty(values: list[Any]) -> str | None:
    for value in values:
        if value:
            return str(value)
    return None


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return write_json_file(path, payload)
