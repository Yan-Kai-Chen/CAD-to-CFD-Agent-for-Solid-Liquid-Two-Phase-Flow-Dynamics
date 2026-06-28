"""Route Selector for choosing the next controlled FastFluent workflow step."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .file_io import ensure_dir, read_json_file, write_json_file, write_text_file
from .flow_pack import build_flow_pack, validate_flow_pack


ROUTE_SELECTION_SCHEMA_VERSION = "fastfluent_route_selection_v1"
ROUTE_CATALOG_SCHEMA_VERSION = "fastfluent_route_catalog_v1"


ROUTE_CATALOG: dict[str, dict[str, Any]] = {
    "fix_setup_contracts": {
        "route_type": "setup_repair",
        "goal": "Repair failed setup contracts before any solver route is considered.",
        "allowed_to_execute_solver": False,
        "commands": [
            "python -m fromcad2cfd fastcfd validate-case <case.json>",
            "python -m fromcad2cfd fastcfd flow-pack build <case.json> --output-dir <flow_pack_dir>",
        ],
    },
    "complete_mesh_gateway": {
        "route_type": "setup_completion",
        "goal": "Attach mesh-gateway evidence before choosing a solver or handoff route.",
        "allowed_to_execute_solver": False,
        "commands": [
            "python -m fromcad2cfd fastcfd mesh inspect <mesh.msh> --output-dir <mesh_evidence_dir>",
            "python -m fromcad2cfd fastcfd flow-pack build <case.json> --mesh-file <mesh.msh> --output-dir <flow_pack_dir>",
        ],
    },
    "native_fastfluent_structured": {
        "route_type": "native_fastfluent",
        "goal": "Run a bounded structured FastFluent route for preliminary native evidence.",
        "allowed_to_execute_solver": True,
        "commands": [
            "python -m fromcad2cfd fastcfd write-channel2d-job --project <project> --model-name <model>",
            "python -m fromcad2cfd fastcfd validate-job --job-file <job.json>",
            "python -m fromcad2cfd fastcfd run-fastfluent-job --job-file <job.json>",
        ],
    },
    "unstructured_fvm_evidence": {
        "route_type": "native_unstructured_fvm",
        "goal": "Run a controlled unstructured finite-volume evidence route after mesh and boundary gates pass.",
        "allowed_to_execute_solver": True,
        "commands": [
            "python -m fromcad2cfd fastcfd unstructured run-case <unstructured_case.json> --output-dir <output_dir>",
            "python -m fromcad2cfd fastcfd unstructured solve-steady-incompressible <mesh.msh> --output-dir <output_dir>",
        ],
    },
    "physics_passport_review": {
        "route_type": "physics_passport",
        "goal": "Generate or review physics-passport evidence before selecting a native or Fluent setup route.",
        "allowed_to_execute_solver": False,
        "commands": [
            "python -m fromcad2cfd fastcfd validate-vof --case-file <vof_case.json>",
            "python -m fromcad2cfd fastcfd validate-turbulence --case-file <turbulence_case.json>",
            "python -m fromcad2cfd fastcfd run-rheology-benchmark --case-file <rheology_case.json>",
        ],
    },
    "dewaxing_native_application": {
        "route_type": "application_native_dewaxing",
        "goal": "Run the dewaxing application chain with native dewaxing evidence, study/validation packs, and paper evidence outputs.",
        "allowed_to_execute_solver": True,
        "commands": [
            "python -m fromcad2cfd fastcfd dewaxing-application-demo --output-dir <application_dir> --dewaxing-pack <result_pack_dir>",
            "python -m fromcad2cfd fastcfd run-dewaxing-native-study --output-dir <study_dir> --comparison-pack <result_pack_dir>",
            "python -m fromcad2cfd fastcfd run-dewaxing-agent-iteration-pack --output-dir <iteration_dir> --comparison-pack <result_pack_dir>",
            "python -m fromcad2cfd fastcfd run-dewaxing-native-validation-pack --output-dir <validation_dir> --comparison-pack <result_pack_dir>",
            "python -m fromcad2cfd fastcfd compile-dewaxing-paper-evidence-pack --validation-pack <validation_dir> --iteration-pack <iteration_dir> --output-dir <paper_pack_dir>",
        ],
    },
    "fluent_planning_preview": {
        "route_type": "fluent_preview",
        "goal": "Compile reviewable Fluent setup or solver-plan evidence without launching Fluent.",
        "allowed_to_execute_solver": False,
        "commands": [
            "python -m fromcad2cfd fastcfd compile-fluent-hints --evidence-files <evidence.json>",
            "python -m fromcad2cfd fastcfd compile-fluent-patch --input <passport.json> --output <solver_plan_patch.json>",
        ],
    },
    "manual_review": {
        "route_type": "manual_review",
        "goal": "Escalate to human review because the current case is outside the bounded route catalog.",
        "allowed_to_execute_solver": False,
        "commands": [
            "Review flow_pack_report.md, readiness_gate.json, and case_summary.md before adding a new controlled route."
        ],
    },
}


def route_catalog() -> dict[str, Any]:
    """Return the route catalog used by M5."""

    return {
        "schema_version": ROUTE_CATALOG_SCHEMA_VERSION,
        "routes": ROUTE_CATALOG,
        "disabled_routes": [
            "raw_fluent_launch",
            "raw_pyfluent_execution",
            "arbitrary_python",
            "arbitrary_shell",
            "unbounded_parameter_sweep",
            "solver_without_setup_gates",
        ],
    }


def select_route(
    flow_pack_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Select the next controlled workflow route from a Flow Pack."""

    root = Path(flow_pack_dir)
    output_root = Path(output_dir) if output_dir else root
    ensure_dir(output_root)
    flow_pack = _read_json(root / "flow_pack.json")
    case_payload = _read_json(root / "case.json")
    validation = validate_flow_pack(root)
    evaluation = _evaluate_routes(flow_pack, case_payload, validation)
    selection = {
        "schema_version": ROUTE_SELECTION_SCHEMA_VERSION,
        "status": "success" if validation.get("passed") else "blocked",
        "source_flow_pack_dir": str(root),
        "case_id": flow_pack.get("case_id") or case_payload.get("case_id"),
        "case_type": flow_pack.get("case_type") or case_payload.get("case_type"),
        "recommended_route": evaluation["recommended_route"],
        "confidence": evaluation["confidence"],
        "rationale": evaluation["rationale"],
        "recommended_commands": ROUTE_CATALOG[evaluation["recommended_route"]]["commands"],
        "alternatives": evaluation["alternatives"],
        "rejected_routes": evaluation["rejected_routes"],
        "route_catalog_version": ROUTE_CATALOG_SCHEMA_VERSION,
        "input_validation": validation,
        "evidence_summary": _evidence_summary(flow_pack, case_payload),
        "agent_next_actions": evaluation["agent_next_actions"],
        "execution_boundary": {
            "selector_executes_solver": False,
            "selector_edits_fluent_case": False,
            "selector_runs_arbitrary_code": False,
            "note": "Route Selector selects the next controlled route only; it does not execute it.",
        },
        "artifacts": {
            "route_selection": str(output_root / "route_selection.json"),
            "route_selection_report": str(output_root / "route_selection_report.md"),
            "route_catalog": str(output_root / "route_catalog.json"),
        },
    }
    _write_json(output_root / "route_selection.json", selection)
    _write_json(output_root / "route_catalog.json", route_catalog())
    write_text_file(output_root / "route_selection_report.md", route_selection_markdown(selection))
    return selection


def run_route_selector_demo(
    output_dir: str | Path,
    *,
    case_file: str | Path = "examples/fastcfd/casespec_v3/channel_flow_case.json",
) -> dict[str, Any]:
    """Build a public Flow Pack demo and select the next route."""

    root = Path(output_dir)
    flow_pack_dir = root / "f"
    route_dir = root / "s"
    flow_pack = build_flow_pack(case_file, output_dir=flow_pack_dir, mesh_mode="structured-demo")
    selection = select_route(flow_pack_dir, output_dir=route_dir)
    result = {
        "status": selection["status"],
        "operation": "route_selector_demo",
        "outputs": {
            "flow_pack_dir": str(flow_pack_dir),
            "route_selection_dir": str(route_dir),
            "flow_pack_status": flow_pack.get("status"),
            "recommended_route": selection.get("recommended_route"),
            "artifacts": {
                "flow_pack": str(flow_pack_dir / "flow_pack.json"),
                "route_selection": str(route_dir / "route_selection.json"),
                "route_selection_report": str(route_dir / "route_selection_report.md"),
                "route_catalog": str(route_dir / "route_catalog.json"),
            },
        },
        "errors": [] if selection["status"] == "success" else selection.get("input_validation", {}).get("errors", []),
    }
    _write_json(root / "demo_status.json", result)
    return result


def route_selection_markdown(selection: dict[str, Any]) -> str:
    """Render route selection as Markdown."""

    route_name = selection.get("recommended_route")
    route = ROUTE_CATALOG.get(str(route_name), {})
    lines = [
        "# FastFluent Route Selection",
        "",
        f"- Status: `{selection.get('status')}`",
        f"- Case ID: `{selection.get('case_id')}`",
        f"- Case type: `{selection.get('case_type')}`",
        f"- Recommended route: `{route_name}`",
        f"- Route type: `{route.get('route_type')}`",
        f"- Confidence: `{selection.get('confidence')}`",
        f"- Selector executes solver: `{selection.get('execution_boundary', {}).get('selector_executes_solver')}`",
        "",
        "## Rationale",
        "",
    ]
    lines.extend(f"- {item}" for item in selection.get("rationale", [])) if selection.get("rationale") else lines.append("- None")
    lines.extend(["", "## Recommended Commands", ""])
    lines.extend(f"- `{item}`" for item in selection.get("recommended_commands", [])) if selection.get("recommended_commands") else lines.append("- None")
    lines.extend(["", "## Alternatives", ""])
    alternatives = selection.get("alternatives", [])
    if alternatives:
        for item in alternatives:
            lines.append(f"- `{item.get('route')}`: {item.get('reason')}")
    else:
        lines.append("- None")
    lines.extend(["", "## Rejected Routes", ""])
    rejected = selection.get("rejected_routes", [])
    if rejected:
        for item in rejected:
            lines.append(f"- `{item.get('route')}`: {item.get('reason')}")
    else:
        lines.append("- None")
    lines.extend(["", "## Agent Next Actions", ""])
    lines.extend(f"- {item}" for item in selection.get("agent_next_actions", [])) if selection.get("agent_next_actions") else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _evaluate_routes(flow_pack: dict[str, Any], case_payload: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    flow_status = flow_pack.get("status")
    readiness = flow_pack.get("readiness_gate") if isinstance(flow_pack.get("readiness_gate"), dict) else {}
    case_type = str(case_payload.get("case_type") or flow_pack.get("case_type") or "")
    claim_level = str(case_payload.get("claim_level") or "")
    mesh = case_payload.get("mesh") if isinstance(case_payload.get("mesh"), dict) else {}
    mesh_source = str(mesh.get("source") or "")
    geometry = case_payload.get("geometry") if isinstance(case_payload.get("geometry"), dict) else {}
    dimension = str(geometry.get("dimension") or "")
    handoff = case_payload.get("handoff") if isinstance(case_payload.get("handoff"), dict) else {}

    if not validation.get("passed") or flow_status == "failed":
        return _decision(
            "fix_setup_contracts",
            confidence="high",
            rationale=["Flow Pack validation failed or setup readiness is failed."],
            alternatives=[],
            rejected_routes=[_reject("native_fastfluent_structured", "Setup contracts are not ready.")],
            next_actions=["Fix failed setup artifacts and rebuild the Flow Pack."],
        )
    if flow_status == "partial" or readiness.get("checks", {}).get("mesh_gateway_available") is False:
        return _decision(
            "complete_mesh_gateway",
            confidence="high",
            rationale=["The Flow Pack is partial or mesh-gateway evidence is missing."],
            alternatives=[_alternative("manual_review", "Manual review is possible but mesh evidence should be completed first.")],
            rejected_routes=[_reject("native_fastfluent_structured", "Native route requires mesh-gateway evidence.")],
            next_actions=["Attach mesh-gateway evidence and rerun route selection."],
        )

    if _is_structured_flow_case(case_type, mesh_source, dimension):
        alternatives = [
            _alternative("unstructured_fvm_evidence", "Use when a Gmsh or unstructured mesh becomes the source of truth."),
            _alternative("fluent_planning_preview", "Use after native evidence if a Fluent handoff is required."),
        ]
        return _decision(
            "native_fastfluent_structured",
            confidence="high",
            rationale=[
                "Case is a steady flow CaseSpec with structured or analytic mesh source.",
                "Flow Pack setup gates passed.",
                "A bounded structured FastFluent channel/obstacle route is already available.",
            ],
            alternatives=alternatives,
            rejected_routes=[_reject("raw_fluent_launch", "Direct Fluent launch is outside this selector boundary.")],
            next_actions=[
                "Generate a controlled FastFluent job from the case intent.",
                "Validate the job physics passport before any native run.",
                "Export resulting native evidence before any Fluent planning preview.",
            ],
        )

    if _is_unstructured_flow_case(case_type, mesh_source):
        return _decision(
            "unstructured_fvm_evidence",
            confidence="high",
            rationale=[
                "Case is a flow CaseSpec with unstructured or Gmsh mesh source.",
                "Mesh Gateway and setup gates passed.",
                "Controlled unstructured FVM evidence routes are available.",
            ],
            alternatives=[_alternative("fluent_planning_preview", "Use after native unstructured evidence is reviewed.")],
            rejected_routes=[_reject("native_fastfluent_structured", "Structured FastFluent route is not the best match for unstructured mesh source.")],
            next_actions=[
                "Convert the CaseSpec into an unstructured case-runner JSON if needed.",
                "Run a controlled unstructured evidence route with mesh and boundary gates enabled.",
            ],
        )

    if case_type == "thermal.dewaxing":
        return _decision(
            "dewaxing_native_application",
            confidence="high",
            rationale=[
                "Case is the dewaxing application CaseSpec.",
                "Flow Pack setup gates passed.",
                "A dedicated FastFluent-native dewaxing application chain is available.",
            ],
            alternatives=[
                _alternative("physics_passport_review", "Use only when the dewaxing application chain should be decomposed into individual model-review artifacts."),
                _alternative("fluent_planning_preview", "Use after native dewaxing evidence if a Fluent setup preview is needed."),
            ],
            rejected_routes=[_reject("native_fastfluent_structured", "Dewaxing requires the dedicated thermal phase-change application route.")],
            next_actions=[
                "Run the dewaxing application bridge to generate setup, native solver, proxy transport, and result-pack artifacts.",
                "Run the native study and validation pack to select and check the FastFluent-guided candidate.",
                "Run the Agent iteration pack when a closed-loop candidate search is needed before final paper evidence.",
                "Compile the paper evidence pack from the completed validation and Agent iteration packs.",
            ],
        )

    if _needs_physics_passport(case_type):
        return _decision(
            "physics_passport_review",
            confidence="medium",
            rationale=[
                "Case type requires specialized physics passport or model-selection evidence before a solver route.",
                "Route Selector does not invent missing physics-model evidence.",
            ],
            alternatives=[_alternative("fluent_planning_preview", "Use after passport evidence exists and needs non-executing Fluent setup preview.")],
            rejected_routes=[_reject("native_fastfluent_structured", "Specialized physics case is not a simple structured single-phase flow route.")],
            next_actions=[
                "Generate the relevant physics passport.",
                "Review Fluent hints or solver-plan patch preview before any high-fidelity setup.",
            ],
        )

    if claim_level in {"fluent_aligned", "engineering_candidate"} or handoff.get("generate_solver_plan_patch") is True:
        return _decision(
            "fluent_planning_preview",
            confidence="medium",
            rationale=[
                "The CaseSpec requests Fluent-aligned or solver-plan handoff artifacts.",
                "The safe current route is preview-only and does not launch Fluent.",
            ],
            alternatives=[_alternative("manual_review", "Review required if upstream native evidence is incomplete.")],
            rejected_routes=[_reject("raw_fluent_launch", "Direct Fluent execution is not enabled in this milestone.")],
            next_actions=["Compile reviewable Fluent hints or solver-plan patches from evidence artifacts."],
        )

    return _decision(
        "manual_review",
        confidence="low",
        rationale=["The case does not match a bounded M5 route rule."],
        alternatives=[],
        rejected_routes=[_reject("raw_solver_execution", "No validated route rule supports direct execution.")],
        next_actions=["Review the CaseSpec and add a new controlled route rule if the case is in scope."],
    )


def _is_structured_flow_case(case_type: str, mesh_source: str, dimension: str) -> bool:
    return case_type.startswith("flow.") and mesh_source in {"structured", "analytic"} and dimension in {"2d", "3d"}


def _is_unstructured_flow_case(case_type: str, mesh_source: str) -> bool:
    return case_type.startswith("flow.") and mesh_source in {"gmsh", "unstructured", "mesh"}


def _needs_physics_passport(case_type: str) -> bool:
    return case_type.startswith(
        (
            "multiphase_lite.",
            "turbulence.",
            "rheology.",
            "thermal.",
            "scalar.",
            "porous.",
            "particle.",
        )
    )


def _decision(
    route: str,
    *,
    confidence: str,
    rationale: list[str],
    alternatives: list[dict[str, str]],
    rejected_routes: list[dict[str, str]],
    next_actions: list[str],
) -> dict[str, Any]:
    return {
        "recommended_route": route,
        "confidence": confidence,
        "rationale": rationale,
        "alternatives": alternatives,
        "rejected_routes": rejected_routes,
        "agent_next_actions": next_actions,
    }


def _alternative(route: str, reason: str) -> dict[str, str]:
    return {"route": route, "reason": reason}


def _reject(route: str, reason: str) -> dict[str, str]:
    return {"route": route, "reason": reason}


def _evidence_summary(flow_pack: dict[str, Any], case_payload: dict[str, Any]) -> dict[str, Any]:
    readiness = flow_pack.get("readiness_gate") if isinstance(flow_pack.get("readiness_gate"), dict) else {}
    mesh = case_payload.get("mesh") if isinstance(case_payload.get("mesh"), dict) else {}
    geometry = case_payload.get("geometry") if isinstance(case_payload.get("geometry"), dict) else {}
    contracts = flow_pack.get("contracts") if isinstance(flow_pack.get("contracts"), dict) else {}
    return {
        "flow_pack_status": flow_pack.get("status"),
        "readiness_status": readiness.get("status"),
        "readiness_checks": readiness.get("checks", {}),
        "mesh_source": mesh.get("source"),
        "geometry_dimension": geometry.get("dimension"),
        "case_claim_level": case_payload.get("claim_level"),
        "boundary_status": _contract_status(contracts, "boundary_contract"),
        "material_status": _contract_status(contracts, "material_contract"),
        "mesh_gateway_status": _contract_status(contracts, "mesh_gateway"),
    }


def _contract_status(contracts: dict[str, Any], key: str) -> str | None:
    value = contracts.get(key)
    return value.get("status") if isinstance(value, dict) else None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = read_json_file(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return write_json_file(path, payload)
