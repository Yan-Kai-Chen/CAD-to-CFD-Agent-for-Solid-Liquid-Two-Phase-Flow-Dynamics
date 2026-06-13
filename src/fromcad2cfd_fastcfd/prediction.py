"""Preliminary CFD prediction and physics-screening reports for FastCFD."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .native_summary import read_native_convergence, read_native_summary
from .schemas import FastCFDJob, read_job


PREDICTION_SCHEMA_VERSION = "fromcad2cfd_fastcfd_prediction_v1"


def build_prediction_report(
    *,
    job: FastCFDJob,
    physics_contract: dict[str, Any],
    qoi: dict[str, Any],
    field_analysis: dict[str, Any],
    lattice_summary: dict[str, Any],
    native_summary: dict[str, Any],
    native_convergence: dict[str, Any],
    pilot_decision: dict[str, Any],
    artifact_refs: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a first-class preliminary CFD prediction from bounded evidence."""

    refs = artifact_refs or {}
    metrics = _metrics(qoi)
    physics_checks = _checks(physics_contract)
    field_metrics = _field_metrics(field_analysis)
    status = _prediction_status(physics_contract, field_analysis, native_convergence, lattice_summary)
    confidence = _confidence(status, field_analysis, native_convergence, lattice_summary)
    physics_screening = _physics_screening(job, physics_contract)
    expected_behavior = _expected_flow_behavior(job, field_analysis, metrics)
    numerical_quality = _numerical_quality(native_summary, native_convergence, field_analysis, lattice_summary)
    design_implications = _design_implications(job, physics_checks, field_metrics, pilot_decision, lattice_summary)
    parameter_suggestions = _parameter_suggestions(job, physics_checks, field_metrics, pilot_decision)
    return {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "status": status,
        "confidence": confidence,
        "case_type": job.case_type,
        "backend": job.backend,
        "model_name": job.model_name,
        "role": "preliminary CFD prediction and physics screening before high-fidelity Fluent validation",
        "executive_summary": _executive_summary(status, confidence, physics_screening, expected_behavior, design_implications),
        "physics_screening": physics_screening,
        "expected_flow_behavior": expected_behavior,
        "numerical_quality": numerical_quality,
        "design_implications": design_implications,
        "parameter_screening_suggestions": parameter_suggestions,
        "evidence": _evidence(refs),
        "limitations": [
            "FastFluent is used here as a low-cost preliminary CFD predictor, not as final high-fidelity validation.",
            "Predictions are only as reliable as the bounded case template, field parser coverage, and convergence evidence.",
            "Three-dimensional CAD-specific Fluent validation is still required for final engineering decisions.",
        ],
    }


def write_prediction_artifacts(
    *,
    report: dict[str, Any],
    output_dir: str | Path,
    reports_dir: str | Path,
    model_name: str,
    unique_path,
) -> dict[str, str]:
    """Write JSON and Markdown prediction artifacts and return their paths."""

    output = Path(output_dir)
    reports = Path(reports_dir)
    output.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    json_path = unique_path(output / "fastcfd_prediction.json")
    json_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    markdown_path = unique_path(reports / f"{model_name}_fastcfd_prediction.md")
    markdown_path.write_text(prediction_markdown(report), encoding="utf-8")
    return {"fastcfd_prediction_json": str(json_path), "fastcfd_prediction_markdown": str(markdown_path)}


def build_prediction_from_output(
    fastcfd_output_dir: str | Path,
    *,
    job_file: str | Path | None = None,
) -> dict[str, Any]:
    """Rebuild a prediction report from an existing FastCFD output directory."""

    output = Path(fastcfd_output_dir)
    manifest = _read_json(output / "result_manifest.json")
    inferred_job = job_file or manifest.get("job_path")
    if not inferred_job:
        raise ValueError("A job file is required when result_manifest.json does not provide job_path.")
    job = read_job(inferred_job)
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    return build_prediction_report(
        job=job,
        physics_contract=_read_json(_artifact_or_default(artifacts, output, "physics_contract", "physics_contract.json")),
        qoi=_read_json(_artifact_or_default(artifacts, output, "qoi", "qoi.json")),
        field_analysis=_read_json(_artifact_or_default(artifacts, output, "field_qoi", "field_qoi.json")),
        lattice_summary=_read_json(_artifact_or_default(artifacts, output, "lattice_domain_summary", "lattice_domain_summary.json")),
        native_summary=read_native_summary(output),
        native_convergence=read_native_convergence(output),
        pilot_decision=_read_json(_artifact_or_default(artifacts, output, "pilot_decision", "pilot_decision.json")),
        artifact_refs={key: str(value) for key, value in artifacts.items() if isinstance(value, str)},
    )


def prediction_markdown(report: dict[str, Any]) -> str:
    """Render a compact Markdown report for researchers and agents."""

    lines = [
        "# FastCFD Preliminary CFD Prediction",
        "",
        f"Status: `{report.get('status')}`",
        f"Confidence: `{report.get('confidence')}`",
        f"Case type: `{report.get('case_type')}`",
        f"Backend: `{report.get('backend')}`",
        "",
        "## Executive Summary",
        "",
    ]
    for item in report.get("executive_summary") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Physics Screening", ""])
    screening = report.get("physics_screening") or {}
    for key in ("verdict", "flow_regime", "reynolds_number", "lattice_mach_estimate", "tau", "stability_band"):
        if key in screening:
            lines.append(f"- `{key}`: `{screening.get(key)}`")
    if screening.get("concerns"):
        lines.extend(["", "### Concerns", ""])
        lines.extend(f"- {item}" for item in screening["concerns"])
    lines.extend(["", "## Expected Flow Behavior", ""])
    for item in report.get("expected_flow_behavior") or []:
        lines.append(f"- **{item.get('feature')}** ({item.get('confidence')}): {item.get('prediction')}")
    lines.extend(["", "## Design Implications", ""])
    for item in report.get("design_implications") or []:
        lines.append(f"- **{item.get('priority')}** `{item.get('action')}`: {item.get('reason')}")
    lines.extend(["", "## Parameter Screening Suggestions", ""])
    for item in report.get("parameter_screening_suggestions") or []:
        lines.append(f"- `{item.get('parameter')}`: {item.get('reason')}")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.get("limitations") or [])
    lines.append("")
    return "\n".join(lines)


def _prediction_status(
    physics_contract: dict[str, Any],
    field_analysis: dict[str, Any],
    native_convergence: dict[str, Any],
    lattice_summary: dict[str, Any],
) -> str:
    if physics_contract.get("status") == "failed" or lattice_summary.get("status") == "failed":
        return "blocked"
    if field_analysis.get("status") == "parsed" and native_convergence.get("status") in {"parsed", "partial"}:
        return "prediction_ready"
    if field_analysis.get("status") == "parsed":
        return "field_based_prediction_limited"
    return "physics_screening_only"


def _confidence(
    status: str,
    field_analysis: dict[str, Any],
    native_convergence: dict[str, Any],
    lattice_summary: dict[str, Any],
) -> str:
    if status == "blocked":
        return "low"
    parsed = field_analysis.get("status") == "parsed"
    convergence = native_convergence.get("status") in {"parsed", "partial"}
    lattice_ok = lattice_summary.get("status") in {"passed", "warning"}
    if parsed and convergence and lattice_ok:
        return "medium"
    if parsed or convergence:
        return "low_medium"
    return "low"


def _physics_screening(job: FastCFDJob, physics_contract: dict[str, Any]) -> dict[str, Any]:
    checks = _checks(physics_contract)
    reynolds = _safe_float(checks.get("reynolds_number"))
    mach = _safe_float(checks.get("mach_lattice_estimate"))
    tau = _safe_float(checks.get("tau"))
    concerns = list(checks.get("warnings") or []) + list(checks.get("errors") or [])
    verdict = "acceptable_for_preliminary_screening"
    if physics_contract.get("status") == "failed":
        verdict = "blocked_before_prediction"
    elif physics_contract.get("status") == "warning":
        verdict = "usable_with_physics_warnings"
    return {
        "verdict": verdict,
        "case_type": job.case_type,
        "flow_regime": _flow_regime(reynolds),
        "reynolds_number": reynolds,
        "reference_velocity_mm_s": _safe_float(checks.get("reference_velocity_mm_s")),
        "kinematic_viscosity_mm2_s": _safe_float(checks.get("kinematic_viscosity_mm2_s")),
        "lattice_mach_estimate": mach,
        "tau": tau,
        "omega": _safe_float(checks.get("omega")),
        "cell_count": checks.get("cell_count"),
        "total_steps": checks.get("total_steps"),
        "stability_band": checks.get("stability_band"),
        "concerns": concerns,
        "remediation_suggestions": physics_contract.get("remediation_suggestions") or [],
    }


def _expected_flow_behavior(job: FastCFDJob, field_analysis: dict[str, Any], qoi_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    field_parsed = field_analysis.get("status") == "parsed"
    field_metrics = _field_metrics(field_analysis)
    behavior: list[dict[str, Any]] = []
    if job.case_type == "cavity2d":
        behavior.append(
            {
                "feature": "recirculating cavity flow",
                "prediction": "A lid-driven recirculation structure is expected; use centerline velocity samples to check whether the preliminary flow trend is plausible.",
                "confidence": "medium" if field_parsed else "low",
                "evidence": ["field_qoi.centerline_velocity_samples" if field_parsed else "case_template.cavity2d"],
            }
        )
    if job.case_type == "channel2d":
        outlet = field_metrics.get("outlet_velocity_spread") or {}
        behavior.append(
            {
                "feature": "through-flow channel response",
                "prediction": _channel_prediction(outlet),
                "confidence": "medium" if field_parsed else "low",
                "evidence": ["field_qoi.outlet_velocity_spread" if field_parsed else "case_template.channel2d"],
            }
        )
    if job.case_type == "obstacle2d":
        wake = field_metrics.get("wake_bbox_proxy") or {}
        behavior.append(
            {
                "feature": "obstacle wake",
                "prediction": _wake_prediction(wake),
                "confidence": "medium" if wake.get("status") == "detected" else ("low_medium" if field_parsed else "low"),
                "evidence": ["field_qoi.wake_bbox_proxy" if field_parsed else "case_template.obstacle2d"],
            }
        )
    speed = (field_metrics.get("speed_summary") or {}).get("max") or qoi_metrics.get("max_velocity_mm_s")
    if speed is not None:
        behavior.append(
            {
                "feature": "velocity scale",
                "prediction": f"The preliminary maximum speed proxy is {speed}; compare this with the intended reference velocity before promoting the setup.",
                "confidence": "medium" if field_parsed else "low",
                "evidence": ["field_qoi.speed_summary.max" if field_parsed else "qoi.max_velocity_mm_s"],
            }
        )
    return behavior


def _numerical_quality(
    native_summary: dict[str, Any],
    native_convergence: dict[str, Any],
    field_analysis: dict[str, Any],
    lattice_summary: dict[str, Any],
) -> dict[str, Any]:
    convergence_metrics = native_convergence.get("metrics") if isinstance(native_convergence.get("metrics"), dict) else {}
    reduction = _safe_float(convergence_metrics.get("reduction_ratio"))
    verdict = "limited"
    concerns: list[str] = []
    if native_convergence.get("status") in {"parsed", "partial"}:
        if reduction is not None and reduction <= 0.8:
            verdict = "acceptable_preliminary_trace"
        elif reduction is not None and reduction <= 1.0:
            verdict = "weak_preliminary_trace"
            concerns.append("Residual reduction is weak; extend the run before strong physical conclusions.")
        else:
            verdict = "poor_preliminary_trace"
            concerns.append("Residual increased; treat flow predictions as exploratory only.")
    else:
        concerns.append("Native residual history is unavailable.")
    if field_analysis.get("status") != "parsed":
        concerns.append("No parseable field output is available.")
    if lattice_summary.get("status") == "warning":
        concerns.extend(str(item) for item in lattice_summary.get("warnings") or [])
    if lattice_summary.get("status") == "failed":
        concerns.extend(str(item) for item in lattice_summary.get("errors") or [])
    return {
        "verdict": verdict,
        "native_summary_status": native_summary.get("status", "unknown"),
        "native_convergence_status": native_convergence.get("status", "unknown"),
        "native_reduction_ratio": reduction,
        "field_parser_status": field_analysis.get("status", "unknown"),
        "lattice_status": lattice_summary.get("status", "unknown"),
        "lattice_trust_score": lattice_summary.get("trust_score"),
        "concerns": concerns,
    }


def _design_implications(
    job: FastCFDJob,
    physics_checks: dict[str, Any],
    field_metrics: dict[str, Any],
    pilot_decision: dict[str, Any],
    lattice_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    implications: list[dict[str, Any]] = []
    for action in pilot_decision.get("recommended_actions") or []:
        if isinstance(action, dict):
            implications.append(
                {
                    "priority": action.get("priority", "medium"),
                    "action": action.get("action", "review"),
                    "reason": action.get("reason", "Pilot decision requested review."),
                    "evidence": action.get("evidence", []),
                }
            )
    outlet = field_metrics.get("outlet_velocity_spread") or {}
    if _safe_float(outlet.get("reverse_flow_fraction")) and _safe_float(outlet.get("reverse_flow_fraction")) > 0:
        implications.append(
            {
                "priority": "high",
                "action": "increase_downstream_length_or_review_outlet_boundary",
                "reason": "Preliminary field evidence indicates reverse flow near the outlet.",
                "evidence": ["field_qoi.outlet_velocity_spread.reverse_flow_fraction"],
            }
        )
    wake = field_metrics.get("wake_bbox_proxy") or {}
    if job.case_type == "obstacle2d" and wake.get("status") == "detected":
        implications.append(
            {
                "priority": "medium",
                "action": "evaluate_obstacle_shape_or_spacing",
                "reason": "A wake region was detected; use it to decide where geometry optimization or later Fluent refinement should focus.",
                "evidence": ["field_qoi.wake_bbox_proxy.bbox_mm"],
            }
        )
    if lattice_summary.get("status") == "failed":
        implications.append(
            {
                "priority": "critical",
                "action": "revise_simplified_fastcfd_domain",
                "reason": "The simplified FastCFD recipe domain is not trustworthy enough for physical screening.",
                "evidence": ["lattice_domain_summary.errors"],
            }
        )
    mach = _safe_float(physics_checks.get("mach_lattice_estimate"))
    if mach is not None and mach >= 0.08:
        implications.append(
            {
                "priority": "high",
                "action": "reduce_reference_velocity_or_adjust_lattice_scaling",
                "reason": "The lattice Mach estimate is high for a low-Mach preliminary CFD screen.",
                "evidence": ["physics_contract.checks.mach_lattice_estimate"],
            }
        )
    if not implications:
        implications.append(
            {
                "priority": "medium",
                "action": "use_as_baseline_for_next_parameter_screening",
                "reason": "No blocking preliminary CFD issue was detected.",
                "evidence": ["physics_contract", "qoi", "pilot_decision"],
            }
        )
    return implications


def _parameter_suggestions(
    job: FastCFDJob,
    physics_checks: dict[str, Any],
    field_metrics: dict[str, Any],
    pilot_decision: dict[str, Any],
) -> list[dict[str, Any]]:
    suggestions = [
        {
            "parameter": "reference_velocity",
            "reason": "Screen velocity sensitivity because Reynolds number and lattice Mach both depend on the chosen velocity scale.",
            "candidate_multipliers": [0.5, 1.0, 2.0],
        },
        {
            "parameter": "cell_length_mm",
            "reason": "Screen grid sensitivity before expensive Fluent setup; keep physical domain size fixed when changing cell length.",
            "candidate_multipliers": [1.0, 0.5],
        },
    ]
    if job.case_type == "obstacle2d":
        suggestions.append(
            {
                "parameter": "obstacle_size",
                "reason": "Obstacle size controls blockage, wake length, and expected local refinement demand.",
                "candidate_multipliers": [0.75, 1.0, 1.25],
            }
        )
    if any((action or {}).get("action") == "review_downstream_domain_extent" for action in pilot_decision.get("recommended_actions") or [] if isinstance(action, dict)):
        suggestions.append(
            {
                "parameter": "domain_length",
                "reason": "Outlet spread or reverse flow suggests a downstream length sensitivity check.",
                "candidate_multipliers": [1.0, 1.5, 2.0],
            }
        )
    if _safe_float(physics_checks.get("reynolds_number")) and _safe_float(physics_checks.get("reynolds_number")) > 1000:
        suggestions.append(
            {
                "parameter": "kinematic_viscosity_or_velocity",
                "reason": "The preliminary Reynolds number is high for the current simple 2D screen; check whether the physical regime intent is correct.",
                "candidate_multipliers": [0.5, 1.0, 2.0],
            }
        )
    if (field_metrics.get("refinement_hints") or {}).get("suggested_fluent_focus"):
        suggestions.append(
            {
                "parameter": "local_refinement_focus",
                "reason": "Field-gradient proxies identify regions worth testing with finer simplified grids before Fluent.",
                "candidate_multipliers": [],
            }
        )
    return suggestions


def _executive_summary(
    status: str,
    confidence: str,
    physics_screening: dict[str, Any],
    expected_behavior: list[dict[str, Any]],
    design_implications: list[dict[str, Any]],
) -> list[str]:
    lines = [
        f"The preliminary CFD prediction status is {status} with {confidence} confidence.",
        f"Physics screening verdict: {physics_screening.get('verdict')} with flow regime `{physics_screening.get('flow_regime')}`.",
    ]
    if expected_behavior:
        first = expected_behavior[0]
        lines.append(f"Expected main flow feature: {first.get('feature')} - {first.get('prediction')}")
    critical = [item for item in design_implications if item.get("priority") in {"critical", "high"}]
    if critical:
        lines.append(f"Immediate review item: {critical[0].get('action')} because {critical[0].get('reason')}")
    else:
        lines.append("No high-priority preliminary CFD blocker was detected; use this case as a baseline for controlled parameter screening.")
    return lines


def _channel_prediction(outlet: dict[str, Any]) -> str:
    spread = _safe_float(outlet.get("spread_ratio"))
    reverse = _safe_float(outlet.get("reverse_flow_fraction"))
    if reverse is not None and reverse > 0:
        return "The outlet shows reverse-flow evidence; the current domain or outlet boundary may influence the result."
    if spread is not None and spread > 0.25:
        return "The outlet velocity spread is elevated; downstream length or outlet placement should be checked."
    if spread is not None:
        return "The outlet profile does not show an automatic high-spread warning in the current preliminary field."
    return "A through-flow channel response is expected, but no parsed outlet field is available yet."


def _wake_prediction(wake: dict[str, Any]) -> str:
    if wake.get("status") == "detected":
        bbox = wake.get("bbox_mm")
        return f"A downstream wake proxy was detected with bounding box {bbox}; this is a candidate refinement and optimization region."
    if wake.get("status") == "not_detected":
        return "No wake proxy was detected by the current simple threshold; check run length, obstacle resolution, and velocity scale before concluding wake absence."
    return "Obstacle wake behavior is expected, but current field evidence is insufficient for a bounded wake estimate."


def _flow_regime(reynolds: float | None) -> str:
    if reynolds is None:
        return "unknown"
    if reynolds < 1:
        return "creeping_or_stokes_like"
    if reynolds < 100:
        return "laminar_low_reynolds"
    if reynolds < 2300:
        return "laminar_to_transitional_screening_range"
    return "high_reynolds_screening_range"


def _metrics(qoi: dict[str, Any]) -> dict[str, Any]:
    metrics = qoi.get("metrics")
    return metrics if isinstance(metrics, dict) else {}


def _checks(physics_contract: dict[str, Any]) -> dict[str, Any]:
    checks = physics_contract.get("checks")
    return checks if isinstance(checks, dict) else {}


def _field_metrics(field_analysis: dict[str, Any]) -> dict[str, Any]:
    metrics = field_analysis.get("metrics")
    return metrics if isinstance(metrics, dict) else {}


def _evidence(refs: dict[str, str]) -> dict[str, str]:
    keys = (
        "physics_contract",
        "qoi",
        "field_qoi",
        "lattice_domain_summary",
        "native_summary",
        "native_convergence",
        "pilot_decision",
        "flow_fingerprint",
    )
    return {key: refs[key] for key in keys if refs.get(key)}


def _artifact_or_default(artifacts: dict[str, Any], output: Path, key: str, default_name: str) -> Path:
    value = artifacts.get(key)
    if isinstance(value, str) and value:
        return Path(value)
    return output / default_name


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {"status": "not_available", "path": str(file_path), "warnings": [f"Missing artifact: {file_path.name}"]}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "failed", "path": str(file_path), "warnings": [f"Failed to read {file_path.name}: {exc}"]}
    if isinstance(payload, dict):
        payload.setdefault("path", str(file_path))
        return payload
    return {"status": "failed", "path": str(file_path), "warnings": [f"Artifact is not a JSON object: {file_path.name}"]}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
