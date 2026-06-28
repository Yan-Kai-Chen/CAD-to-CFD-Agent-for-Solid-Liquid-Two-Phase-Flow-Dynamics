"""Dewaxing application bridge for FastFluent agent workflows.

This module is intentionally public-safe. It can run bounded FastFluent/S6
proxy calculations and validate an existing dewaxing result pack, but it does
not launch Fluent, edit Fluent case/data files, or create a new Fluent result.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fromcad2cfd_postprocessing.dewaxing_result_pack import validate_dewaxing_result_pack

from .core.case_spec import CASE_SPEC_SCHEMA_VERSION
from .file_io import ensure_dir, write_json_file, write_text_file
from .flow_pack import build_flow_pack, validate_flow_pack
from .result_pack import compile_native_result_pack, validate_result_pack
from .route_plan import compile_route_plan, validate_route_plan
from .route_selector import select_route
from .dewaxing_native_solver import run_dewaxing_native_solver
from .transport_core import run_transport_coupling_demo
from .wax_rheology_phase_change import run_wax_rheology_handoff_demo


DEWAXING_APPLICATION_SCHEMA_VERSION = "fastfluent_dewaxing_application_bridge_v1"
DEWAXING_APPLICATION_STAGE_SCHEMA_VERSION = "fastfluent_dewaxing_application_stage_status_v1"
DEWAXING_APPLICATION_DECISION_SCHEMA_VERSION = "fastfluent_dewaxing_application_agent_decision_v1"


def create_dewaxing_application_case() -> dict[str, Any]:
    """Return a public-safe CaseSpec for the dewaxing application bridge."""

    return {
        "schema_version": CASE_SPEC_SCHEMA_VERSION,
        "case_id": "dewaxing_application_bridge_demo",
        "case_type": "thermal.dewaxing",
        "claim_level": "fluent_aligned",
        "geometry": {
            "source": "analytic",
            "dimension": "2d",
            "parameters": {
                "length_m": 1.0,
                "height_m": 0.12,
            },
            "zones": [
                "steam_inlet",
                "pressure_outlet",
                "heated_wall",
                "model_shell",
                "wax_region",
                "fluid_region",
            ],
        },
        "mesh": {
            "source": "structured",
            "nx": 80,
            "ny": 16,
            "quality_gates": {
                "max_skewness": 0.85,
                "min_orthogonal_quality": 0.15,
            },
        },
        "materials": {
            "steam_air": {
                "name": "steam_air_public_surrogate",
                "type": "ideal_gas_lite",
                "density_kg_m3": 1.0,
                "viscosity_pa_s": 1.3e-5,
                "thermal_conductivity_w_m_k": 0.03,
                "specific_heat_j_kg_k": 2000.0,
                "gas_constant_j_kg_k": 461.5,
            },
            "wax": {
                "name": "wax_public_surrogate",
                "type": "temperature_dependent_fluid",
                "density_kg_m3": 900.0,
                "thermal_conductivity_w_m_k": 0.25,
                "specific_heat_j_kg_k": 2200.0,
                "temperature_points_k": [330.15, 345.15, 373.15],
                "viscosity_points_pa_s": [1000.0, 10.0, 0.01],
            },
            "model_shell": {
                "name": "shell_public_surrogate",
                "type": "solid_thermal",
                "density_kg_m3": 2500.0,
                "thermal_conductivity_w_m_k": 1.3,
                "specific_heat_j_kg_k": 850.0,
            },
        },
        "boundary_conditions": {
            "steam_inlet": {
                "type": "mass_flow_inlet",
                "mass_flow_kg_s": 0.01,
                "temperature_k": 443.15,
            },
            "pressure_outlet": {
                "type": "pressure_outlet",
                "gauge_pressure_pa": 0.0,
            },
            "heated_wall": {
                "type": "convective_wall",
                "heat_transfer_coefficient_w_m2_k": 200.0,
                "free_stream_temperature_k": 443.15,
            },
            "model_shell": {
                "type": "wall_no_slip",
            },
            "wax_region": {
                "type": "source_zone",
            },
            "fluid_region": {
                "type": "interface",
            },
        },
        "numerics": {
            "time_mode": "transient",
            "solver": "fastfluent_application_bridge_review",
            "time_step_s": 0.01,
            "max_iterations": 4100,
        },
        "qoi_targets": [
            "early_steam_shock_crack_index",
            "full_melt_time_s",
            "dominant_risk_time_s",
            "peak_effective_pressure_mpa",
            "peak_wall_vm_p995_mpa",
            "drainage_relief_stress_drop_fraction",
            "fastfluent_temperature_transport_balance",
            "fastfluent_wax_fraction_bounds",
        ],
        "handoff": {
            "generate_fluent_hints": True,
            "generate_solver_plan_patch": True,
        },
        "metadata": {
            "public_safe": True,
            "purpose": "Public dewaxing application bridge from setup evidence to existing result-pack review.",
            "new_fluent_calculation": False,
            "fastfluent_proxy_calculation": True,
        },
    }


def run_dewaxing_application_demo(
    output_dir: str | Path,
    *,
    dewaxing_pack: str | Path | None = None,
    include_native_transport: bool = True,
) -> dict[str, Any]:
    """Run the dewaxing application bridge.

    The bridge supplements the application stage with bounded FastFluent/S6
    proxy calculations. A supplied dewaxing pack is treated as existing external
    Fluent evidence and is validated, not recomputed.
    """

    root = Path(output_dir)
    ensure_dir(root)
    case_dir = root / "01_case"
    stages: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {
        "application_manifest": str(root / "application_manifest.json"),
        "stage_status": str(root / "stage_status.json"),
        "agent_decision": str(root / "agent_decision.json"),
        "agent_flow_report": str(root / "agent_flow_report.md"),
        "application_status": str(root / "application_status.json"),
    }
    blocking_errors: list[str] = []

    try:
        case = create_dewaxing_application_case()
        case_path = write_json_file(case_dir / "dewaxing_application_case.json", case)
        artifacts["case_spec"] = str(case_path)
        stages.append(_stage("case_spec", "written", artifacts={"case_spec": str(case_path)}))

        flow_pack = build_flow_pack(case_path, output_dir=root / "02_flow_pack", mesh_mode="structured-demo")
        flow_validation = validate_flow_pack(root / "02_flow_pack")
        artifacts["flow_pack"] = str(root / "02_flow_pack" / "flow_pack.json")
        stages.append(
            _stage(
                "flow_pack",
                str(flow_pack.get("status")),
                artifacts={"flow_pack": artifacts["flow_pack"]},
                validation=flow_validation,
                warnings=flow_validation.get("warnings", []),
                errors=flow_validation.get("errors", []),
            )
        )
        if not flow_validation.get("passed") or flow_pack.get("status") == "failed":
            blocking_errors.extend(_prefixed_errors("flow_pack", flow_validation.get("errors", [])))

        selection = select_route(root / "02_flow_pack", output_dir=root / "03_route_selection")
        artifacts["route_selection"] = str(root / "03_route_selection" / "route_selection.json")
        stages.append(
            _stage(
                "route_selection",
                str(selection.get("status")),
                artifacts={"route_selection": artifacts["route_selection"]},
                summary={"recommended_route": selection.get("recommended_route"), "confidence": selection.get("confidence")},
            )
        )
        if selection.get("status") == "blocked":
            blocking_errors.append("route_selection blocked")

        plan = compile_route_plan(root / "03_route_selection", output_dir=root / "04_route_plan")
        plan_validation = validate_route_plan(root / "04_route_plan")
        artifacts["route_plan"] = str(root / "04_route_plan" / "route_plan.json")
        stages.append(
            _stage(
                "route_plan",
                str(plan.get("status")),
                artifacts={"route_plan": artifacts["route_plan"]},
                validation=plan_validation,
                warnings=plan.get("warnings", []) + plan_validation.get("warnings", []),
                errors=plan.get("errors", []) + plan_validation.get("errors", []),
            )
        )
        if not plan_validation.get("passed"):
            blocking_errors.extend(_prefixed_errors("route_plan", plan_validation.get("errors", [])))

        wax = run_wax_rheology_handoff_demo(output_dir=root / "05_wax_h4_handoff")
        wax_artifacts = _string_artifacts(wax.get("outputs", {}).get("artifacts"))
        artifacts["wax_h4_handoff"] = str(root / "05_wax_h4_handoff" / "solver_plan_patch.json")
        stages.append(
            _stage(
                "wax_h4_handoff",
                str(wax.get("status")),
                artifacts=wax_artifacts,
                summary={
                    "passport_status": wax.get("outputs", {}).get("passport", {}).get("status"),
                    "patch_status": wax.get("outputs", {}).get("patch", {}).get("status"),
                },
                warnings=wax.get("warnings", []),
                errors=wax.get("errors", []),
            )
        )
        if wax.get("status") not in {"success", "partial"}:
            blocking_errors.extend(_prefixed_errors("wax_h4_handoff", wax.get("errors", [])))

        native_dewaxing = _run_native_dewaxing_stage(root / "06_fastfluent_native_dewaxing", comparison_pack=dewaxing_pack)
        stages.append(native_dewaxing["stage"])
        artifacts["native_dewaxing_result"] = native_dewaxing["artifacts"]["native_result"]
        artifacts["native_dewaxing_result_pack"] = native_dewaxing["artifacts"]["result_pack"]
        if not native_dewaxing["validation"].get("passed"):
            blocking_errors.extend(_prefixed_errors("native_dewaxing_result_pack", native_dewaxing["validation"].get("errors", [])))
        if native_dewaxing["native"].get("status") != "success":
            blocking_errors.extend(_prefixed_errors("native_dewaxing_solver", native_dewaxing["native"].get("blocking_errors", [])))

        native_results: dict[str, Any] = {}
        if include_native_transport:
            for quantity in ("temperature", "wax_fraction"):
                native_stage = _run_native_transport_stage(root / "07_fastfluent_native_proxy" / quantity, quantity=quantity)
                native_results[quantity] = native_stage
                stages.append(native_stage["stage"])
                artifacts[f"native_{quantity}_result"] = native_stage["artifacts"]["native_result"]
                artifacts[f"native_{quantity}_result_pack"] = native_stage["artifacts"]["result_pack"]
                if not native_stage["validation"].get("passed"):
                    blocking_errors.extend(_prefixed_errors(f"native_{quantity}_result_pack", native_stage["validation"].get("errors", [])))

        pack_validation = _validate_optional_dewaxing_pack(dewaxing_pack)
        if pack_validation.get("status") == "skipped":
            stages.append(_stage("dewaxing_result_pack_validation", "skipped", warnings=pack_validation.get("warnings", [])))
        else:
            artifacts["dewaxing_result_pack"] = str(pack_validation.get("pack_path", dewaxing_pack))
            stages.append(
                _stage(
                    "dewaxing_result_pack_validation",
                    str(pack_validation.get("status")),
                    artifacts={"dewaxing_result_pack": artifacts["dewaxing_result_pack"]},
                    validation=pack_validation,
                    warnings=pack_validation.get("warnings", []),
                    errors=pack_validation.get("errors", []),
                )
            )
            if not pack_validation.get("passed"):
                blocking_errors.extend(_prefixed_errors("dewaxing_result_pack", pack_validation.get("errors", [])))

        status = "blocked" if blocking_errors else ("partial" if pack_validation.get("status") == "skipped" else "success")
        decision = _agent_decision(
            status=status,
            selection=selection,
            plan=plan,
            wax=wax,
            native_dewaxing=native_dewaxing,
            native_results=native_results,
            pack_validation=pack_validation,
            blocking_errors=blocking_errors,
        )
        manifest = {
            "schema_version": DEWAXING_APPLICATION_SCHEMA_VERSION,
            "status": status,
            "case_id": case["case_id"],
            "application": "dewaxing",
            "source_case_file": str(case_path),
            "stages": stages,
            "flow_pack": {
                "status": flow_pack.get("status"),
                "validation": flow_validation,
            },
            "route_selection": {
                "status": selection.get("status"),
                "recommended_route": selection.get("recommended_route"),
                "confidence": selection.get("confidence"),
            },
            "route_plan": {
                "status": plan.get("status"),
                "validation": plan_validation,
            },
            "wax_h4_handoff": {
                "status": wax.get("status"),
                "passport_status": wax.get("outputs", {}).get("passport", {}).get("status"),
                "patch_status": wax.get("outputs", {}).get("patch", {}).get("status"),
            },
            "fastfluent_native_dewaxing": _native_dewaxing_manifest(native_dewaxing),
            "fastfluent_native_proxy": _native_manifest(native_results),
            "dewaxing_result_pack_validation": pack_validation,
            "agent_decision": decision,
            "artifacts": artifacts,
            "execution_boundary": {
                "new_fluent_calculation": False,
                "fluent_launched": False,
                "fluent_case_or_data_edited": False,
                "fastfluent_native_dewaxing_calculation": True,
                "fastfluent_native_proxy_calculation": bool(include_native_transport),
                "existing_dewaxing_pack_role": "external_evidence_validation_only",
            },
            "blocking_errors": blocking_errors,
            "warnings": _collect_stage_warnings(stages) + list(pack_validation.get("warnings", [])),
        }
        stages.append(_stage("application_decision", status, artifacts={"agent_decision": artifacts["agent_decision"]}))
        manifest["stages"] = stages
        write_json_file(root / "application_manifest.json", manifest)
        write_json_file(root / "stage_status.json", {"schema_version": DEWAXING_APPLICATION_STAGE_SCHEMA_VERSION, "stages": stages})
        write_json_file(root / "agent_decision.json", decision)
        write_json_file(root / "application_status.json", {"schema_version": DEWAXING_APPLICATION_SCHEMA_VERSION, "status": status, "artifacts": artifacts})
        write_text_file(root / "agent_flow_report.md", dewaxing_application_markdown(manifest))
        return manifest
    except (OSError, ValueError) as exc:
        failure = _failure_manifest(root, artifacts=artifacts, stages=stages, error=str(exc))
        write_json_file(root / "application_manifest.json", failure)
        write_json_file(root / "stage_status.json", {"schema_version": DEWAXING_APPLICATION_STAGE_SCHEMA_VERSION, "stages": stages})
        write_json_file(root / "agent_decision.json", failure["agent_decision"])
        write_json_file(root / "application_status.json", {"schema_version": DEWAXING_APPLICATION_SCHEMA_VERSION, "status": "failed", "artifacts": artifacts})
        write_text_file(root / "agent_flow_report.md", dewaxing_application_markdown(failure))
        return failure


def run_dewaxing_application_public_demo(output_dir: str | Path) -> dict[str, Any]:
    """Run the bridge against the public-safe synthetic dewaxing result pack."""

    return run_dewaxing_application_demo(output_dir, dewaxing_pack=_default_public_dewaxing_pack())


def dewaxing_application_markdown(manifest: dict[str, Any]) -> str:
    """Render a concise report for the dewaxing application bridge."""

    decision = manifest.get("agent_decision", {}) if isinstance(manifest.get("agent_decision"), dict) else {}
    lines = [
        "# FastFluent Dewaxing Application Bridge",
        "",
        f"- Status: `{manifest.get('status')}`",
        f"- Case ID: `{manifest.get('case_id')}`",
        f"- Route: `{manifest.get('route_selection', {}).get('recommended_route')}`",
        f"- New Fluent calculation: `{manifest.get('execution_boundary', {}).get('new_fluent_calculation')}`",
        f"- FastFluent native dewaxing calculation: `{manifest.get('execution_boundary', {}).get('fastfluent_native_dewaxing_calculation')}`",
        f"- FastFluent native proxy calculation: `{manifest.get('execution_boundary', {}).get('fastfluent_native_proxy_calculation')}`",
        f"- Recommended next action: `{decision.get('recommended_next_action')}`",
        "",
        "## Continuity Chain",
        "",
    ]
    for stage in manifest.get("stages", []):
        if isinstance(stage, dict):
            lines.append(f"- `{stage.get('stage')}`: `{stage.get('status')}`")
    native_dewaxing = manifest.get("fastfluent_native_dewaxing", {}) if isinstance(manifest.get("fastfluent_native_dewaxing"), dict) else {}
    native_qoi = native_dewaxing.get("qoi", {}) if isinstance(native_dewaxing.get("qoi"), dict) else {}
    native_metrics = native_qoi.get("metrics", {}) if isinstance(native_qoi.get("metrics"), dict) else {}
    lines.extend(
        [
            "",
            "## FastFluent Native Dewaxing Solver",
            "",
            f"- Quality: `{native_dewaxing.get('quality_status')}`",
            f"- Result pack: `{native_dewaxing.get('result_pack_status')}`",
            f"- Predicted full melt time s: `{native_metrics.get('predicted_full_melt_time_s')}`",
            f"- Dominant native risk time s: `{native_metrics.get('dominant_risk_time_s')}`",
            f"- Final average liquid fraction: `{native_metrics.get('final_avg_liquid_fraction')}`",
            f"- Energy balance relative error: `{native_metrics.get('energy_balance_relative_error')}`",
        ]
    )
    lines.extend(
        [
            "",
            "## FastFluent Native Proxy",
            "",
        ]
    )
    native = manifest.get("fastfluent_native_proxy", {}) if isinstance(manifest.get("fastfluent_native_proxy"), dict) else {}
    if native:
        for quantity, payload in sorted(native.items()):
            qoi = payload.get("qoi", {}) if isinstance(payload, dict) else {}
            metrics = qoi.get("metrics", {}) if isinstance(qoi.get("metrics"), dict) else qoi
            lines.append(
                f"- `{quantity}`: quality `{payload.get('quality_status')}`, "
                f"result pack `{payload.get('result_pack_status')}`, "
                f"max Courant `{metrics.get('max_courant_number')}`"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Dewaxing Result Pack Metrics", ""])
    validation = manifest.get("dewaxing_result_pack_validation", {})
    metrics = validation.get("key_metrics", {}) if isinstance(validation, dict) and isinstance(validation.get("key_metrics"), dict) else {}
    if metrics:
        for key, value in metrics.items():
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- Not supplied")
    lines.extend(
        [
            "",
            "## Application Scope",
            "",
            "- The bridge connects setup evidence, native dewaxing calculation, proxy transport evidence, and the reviewed Fluent result pack.",
            "- The native dewaxing solver is used for reduced-order candidate screening and timing comparison.",
            "- FastFluent/S6 proxy calculations support auxiliary screening and workflow control.",
            "- Existing dewaxing Fluent results remain the high-fidelity reference for final timing and stress interpretation.",
            "- Crack-probability and two-way FSI language should be added only when a dedicated evidence source is available.",
            "",
        ]
    )
    return "\n".join(lines)


def _run_native_dewaxing_stage(root: Path, *, comparison_pack: str | Path | None) -> dict[str, Any]:
    ensure_dir(root)
    native = run_dewaxing_native_solver(output_dir=root / "native_result", comparison_pack=comparison_pack)
    native_result_path = root / "native_result" / "dewaxing_native_status.json"
    result_pack = compile_native_result_pack(native_result_path, output_dir=root / "result_pack")
    validation = validate_result_pack(root / "result_pack")
    qoi = native.get("outputs", {}).get("qoi", {}) if isinstance(native.get("outputs"), dict) else {}
    artifacts = {
        "native_result": str(native_result_path),
        "result_pack": str(root / "result_pack" / "result_pack.json"),
        "native_result_summary": str(root / "result_pack" / "native_result_summary.json"),
    }
    metrics = qoi.get("metrics", {}) if isinstance(qoi.get("metrics"), dict) else {}
    stage = _stage(
        "fastfluent_dewaxing_native_solver",
        str(native.get("quality_status") or native.get("status")),
        artifacts=artifacts,
        validation=validation,
        summary={
            "case_id": native.get("case_id"),
            "result_pack_status": result_pack.get("status"),
            "evidence_level": result_pack.get("evidence_level"),
            "predicted_full_melt_time_s": metrics.get("predicted_full_melt_time_s"),
            "dominant_risk_time_s": metrics.get("dominant_risk_time_s"),
            "can_support_screening_decision": result_pack.get("decision", {}).get("can_support_screening_decision"),
        },
        warnings=native.get("warnings", []) + validation.get("warnings", []),
        errors=native.get("blocking_errors", []) + validation.get("errors", []),
    )
    return {
        "stage": stage,
        "native": native,
        "result_pack": result_pack,
        "validation": validation,
        "artifacts": artifacts,
        "qoi": qoi,
    }


def _run_native_transport_stage(root: Path, *, quantity: str) -> dict[str, Any]:
    ensure_dir(root)
    native = run_transport_coupling_demo(root / "native_result", quantity=quantity)
    native_result_path = root / "native_result" / "status.json"
    result_pack = compile_native_result_pack(native_result_path, output_dir=root / "result_pack")
    validation = validate_result_pack(root / "result_pack")
    qoi = native.get("outputs", {}).get("qoi", {}) if isinstance(native.get("outputs"), dict) else {}
    artifacts = {
        "native_result": str(native_result_path),
        "result_pack": str(root / "result_pack" / "result_pack.json"),
        "native_result_summary": str(root / "result_pack" / "native_result_summary.json"),
    }
    stage = _stage(
        f"fastfluent_{quantity}_transport",
        str(native.get("quality_status") or native.get("status")),
        artifacts=artifacts,
        validation=validation,
        summary={
            "case_id": native.get("case_id"),
            "result_pack_status": result_pack.get("status"),
            "evidence_level": result_pack.get("evidence_level"),
            "can_support_screening_decision": result_pack.get("decision", {}).get("can_support_screening_decision"),
        },
        warnings=native.get("warnings", []) + validation.get("warnings", []),
        errors=native.get("blocking_errors", []) + native.get("errors", []) + validation.get("errors", []),
    )
    return {
        "stage": stage,
        "native": native,
        "result_pack": result_pack,
        "validation": validation,
        "artifacts": artifacts,
        "qoi": qoi,
    }


def _validate_optional_dewaxing_pack(dewaxing_pack: str | Path | None) -> dict[str, Any]:
    if dewaxing_pack is None or str(dewaxing_pack).strip() == "":
        return {
            "schema_version": "dewaxing_agent_result_pack_validation_v1",
            "status": "skipped",
            "passed": False,
            "warnings": ["No existing dewaxing result pack was supplied."],
            "errors": [],
        }
    return validate_dewaxing_result_pack(dewaxing_pack)


def _agent_decision(
    *,
    status: str,
    selection: dict[str, Any],
    plan: dict[str, Any],
    wax: dict[str, Any],
    native_dewaxing: dict[str, Any],
    native_results: dict[str, Any],
    pack_validation: dict[str, Any],
    blocking_errors: list[str],
) -> dict[str, Any]:
    native_dewaxing_ready = (
        native_dewaxing.get("validation", {}).get("passed") is True
        and native_dewaxing.get("result_pack", {}).get("decision", {}).get("can_support_screening_decision") is True
    )
    native_screening_ready = bool(native_results) and all(
        item.get("validation", {}).get("passed") and item.get("result_pack", {}).get("decision", {}).get("can_support_screening_decision")
        for item in native_results.values()
    )
    pack_ready = pack_validation.get("passed") is True
    return {
        "schema_version": DEWAXING_APPLICATION_DECISION_SCHEMA_VERSION,
        "status": status,
        "fastfluent_application_continuity": status != "blocked",
        "recommended_next_action": "use_fastfluent_bridge_and_existing_dewaxing_pack_for_agent_case_study"
        if status == "success"
        else "repair_dewaxing_application_bridge_before_case_study",
        "can_support_agent_workflow_control": status != "blocked",
        "can_support_fastfluent_screening_decision": native_dewaxing_ready and (native_screening_ready or not native_results),
        "can_support_native_dewaxing_reduced_order_decision": native_dewaxing_ready,
        "can_support_existing_fluent_result_review": pack_ready,
        "can_support_new_fluent_calculation": False,
        "can_support_final_cfd_validation": False,
        "can_support_final_crack_probability": False,
        "can_support_two_way_fsi_validation": False,
        "route": {
            "recommended_route": selection.get("recommended_route"),
            "route_status": selection.get("status"),
            "route_plan_status": plan.get("status"),
        },
        "wax_h4": {
            "status": wax.get("status"),
            "passport_status": wax.get("outputs", {}).get("passport", {}).get("status"),
            "patch_status": wax.get("outputs", {}).get("patch", {}).get("status"),
        },
        "native_dewaxing": {
            "quality_status": native_dewaxing.get("native", {}).get("quality_status"),
            "result_pack_status": native_dewaxing.get("result_pack", {}).get("status"),
            "key_metrics": native_dewaxing.get("qoi", {}).get("metrics", {}),
        },
        "native_proxy_quantities": sorted(native_results),
        "dewaxing_pack_metrics": pack_validation.get("key_metrics", {}),
        "blocking_errors": blocking_errors,
        "rationale": [
            "CaseSpec, Flow Pack, Route Selector, and Route Plan make the application input auditable.",
            "H4 wax rheology and phase-change passport provides model-review and solver-plan handoff evidence.",
            "The native dewaxing reduced-order solver computes transient heat conduction, enthalpy melting, early thermal-shock proxies, and drainage-risk proxies.",
            "S6 temperature and wax-fraction proxy calculations add auxiliary reproducible FastFluent screening evidence.",
            "The existing dewaxing Fluent pack is validated as external evidence and is not recomputed.",
        ],
    }


def _native_dewaxing_manifest(native_dewaxing: dict[str, Any]) -> dict[str, Any]:
    native = native_dewaxing.get("native", {})
    result_pack = native_dewaxing.get("result_pack", {})
    qoi = native_dewaxing.get("qoi", {})
    return {
        "quality_status": native.get("quality_status"),
        "case_id": native.get("case_id"),
        "result_pack_status": result_pack.get("status"),
        "evidence_level": result_pack.get("evidence_level"),
        "qoi": qoi,
        "comparison": native.get("outputs", {}).get("comparison", {}),
        "artifacts": native_dewaxing.get("artifacts", {}),
    }


def _native_manifest(native_results: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for quantity, payload in sorted(native_results.items()):
        native = payload.get("native", {})
        result_pack = payload.get("result_pack", {})
        qoi = payload.get("qoi", {})
        result[quantity] = {
            "quality_status": native.get("quality_status"),
            "case_id": native.get("case_id"),
            "result_pack_status": result_pack.get("status"),
            "evidence_level": result_pack.get("evidence_level"),
            "qoi": qoi,
            "artifacts": payload.get("artifacts", {}),
        }
    return result


def _stage(
    name: str,
    status: str,
    *,
    artifacts: dict[str, str] | None = None,
    validation: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": DEWAXING_APPLICATION_STAGE_SCHEMA_VERSION,
        "stage": name,
        "status": status,
        "artifacts": artifacts or {},
        "warnings": warnings or [],
        "errors": errors or [],
    }
    if validation is not None:
        payload["validation"] = validation
    if summary is not None:
        payload["summary"] = summary
    return payload


def _failure_manifest(root: Path, *, artifacts: dict[str, str], stages: list[dict[str, Any]], error: str) -> dict[str, Any]:
    decision = {
        "schema_version": DEWAXING_APPLICATION_DECISION_SCHEMA_VERSION,
        "status": "failed",
        "fastfluent_application_continuity": False,
        "recommended_next_action": "repair_dewaxing_application_exception",
        "can_support_agent_workflow_control": False,
        "can_support_fastfluent_screening_decision": False,
        "can_support_existing_fluent_result_review": False,
        "can_support_new_fluent_calculation": False,
        "can_support_final_cfd_validation": False,
        "can_support_final_crack_probability": False,
        "can_support_two_way_fsi_validation": False,
        "blocking_errors": [error],
    }
    return {
        "schema_version": DEWAXING_APPLICATION_SCHEMA_VERSION,
        "status": "failed",
        "case_id": "dewaxing_application_bridge_demo",
        "application": "dewaxing",
        "stages": stages,
        "agent_decision": decision,
        "artifacts": artifacts,
        "execution_boundary": {
            "new_fluent_calculation": False,
            "fluent_launched": False,
            "fluent_case_or_data_edited": False,
            "fastfluent_native_proxy_calculation": False,
            "existing_dewaxing_pack_role": "not_validated_due_to_failure",
        },
        "blocking_errors": [error],
        "warnings": [],
        "metadata": {"output_dir": str(root)},
    }


def _default_public_dewaxing_pack() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "examples" / "postprocessing" / "dewaxing_result_pack"
    return candidate if candidate.exists() else Path("examples") / "postprocessing" / "dewaxing_result_pack"


def _string_artifacts(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if isinstance(item, str)}


def _collect_stage_warnings(stages: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for stage in stages:
        for warning in stage.get("warnings", []):
            warnings.append(f"{stage.get('stage')}: {warning}")
    return warnings


def _prefixed_errors(prefix: str, errors: Any) -> list[str]:
    if not isinstance(errors, list):
        return []
    return [f"{prefix}: {item}" for item in errors]
