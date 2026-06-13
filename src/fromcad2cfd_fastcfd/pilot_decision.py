"""Bounded pilot-run decision policy for FastCFD/FastFluent evidence."""

from __future__ import annotations

from typing import Any

from .schemas import FastCFDJob


PILOT_DECISION_SCHEMA_VERSION = "fromcad2cfd_pilot_decision_v1"


def build_pilot_decision(
    *,
    job: FastCFDJob,
    lattice_summary: dict[str, Any],
    field_analysis: dict[str, Any],
    native_convergence: dict[str, Any],
    artifact_refs: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return a conservative next-action decision from bounded pilot evidence."""

    refs = artifact_refs or {}
    metrics = _metrics_used(job, lattice_summary, field_analysis, native_convergence)
    actions: list[dict[str, Any]] = []
    _add_lattice_actions(actions, metrics, refs)
    _add_convergence_actions(actions, metrics, refs)
    _add_field_actions(actions, metrics, refs)
    if not actions:
        actions.append(
            {
                "priority": "medium",
                "action": "proceed_with_advisory_handoff",
                "reason": "The bounded pilot has no automatic blocking or review triggers.",
                "evidence": _evidence(refs, "qoi", "lattice_domain_summary", "native_convergence", "field_qoi"),
            }
        )
    status = _decision_status(actions)
    return {
        "schema_version": PILOT_DECISION_SCHEMA_VERSION,
        "status": status,
        "case_type": job.case_type,
        "confidence": _confidence(status, metrics),
        "metrics_used": metrics,
        "recommended_actions": actions,
        "limitations": [
            "This policy ranks next actions for agent workflow control; it is not a final CFD acceptance criterion.",
            "FastCFD/FastFluent pilot evidence must be reviewed before carrying assumptions into Fluent.",
            "Final decisions still require Fluent mesh quality, residuals, and engineering QoI checks.",
        ],
    }


def pilot_decision_qoi_updates(decision: dict[str, Any]) -> dict[str, Any]:
    """Return compact QoI fields from the pilot decision."""

    actions = decision.get("recommended_actions") if isinstance(decision.get("recommended_actions"), list) else []
    return {
        "pilot_decision_status": decision.get("status", "unknown"),
        "pilot_decision_confidence": decision.get("confidence", "unknown"),
        "pilot_decision_action_count": len(actions),
        "pilot_decision_top_action": actions[0].get("action") if actions and isinstance(actions[0], dict) else None,
    }


def _metrics_used(
    job: FastCFDJob,
    lattice_summary: dict[str, Any],
    field_analysis: dict[str, Any],
    native_convergence: dict[str, Any],
) -> dict[str, Any]:
    lattice_resolution = lattice_summary.get("resolution") if isinstance(lattice_summary.get("resolution"), dict) else {}
    obstacle_resolution = lattice_resolution.get("obstacle_resolution") if isinstance(lattice_resolution.get("obstacle_resolution"), dict) else {}
    obstacle_clearance = lattice_resolution.get("obstacle_clearance") if isinstance(lattice_resolution.get("obstacle_clearance"), dict) else {}
    convergence_metrics = native_convergence.get("metrics") if isinstance(native_convergence.get("metrics"), dict) else {}
    field_inputs = field_analysis.get("fluent_hint_inputs") if isinstance(field_analysis.get("fluent_hint_inputs"), dict) else {}
    return {
        "case_type": job.case_type,
        "lattice_status": lattice_summary.get("status", "unknown"),
        "lattice_trust_score": _safe_float(lattice_summary.get("trust_score")),
        "lattice_warning_count": len(lattice_summary.get("warnings") or []),
        "lattice_error_count": len(lattice_summary.get("errors") or []),
        "min_obstacle_resolution_cells": _safe_float(obstacle_resolution.get("min_size_cells")),
        "min_obstacle_clearance_cells": _safe_float(obstacle_clearance.get("min_clearance_cells")),
        "native_convergence_status": native_convergence.get("status", "unknown"),
        "native_reduction_ratio": _safe_float(convergence_metrics.get("reduction_ratio")),
        "native_nonincreasing_fraction": _safe_float(convergence_metrics.get("nonincreasing_fraction")),
        "field_parser_status": field_analysis.get("status", "unknown"),
        "outlet_spread_ratio": _safe_float(field_inputs.get("outlet_spread_ratio")),
        "outlet_reverse_flow_fraction": _safe_float(field_inputs.get("outlet_reverse_flow_fraction")),
        "wake_status": field_inputs.get("wake_status"),
    }


def _add_lattice_actions(actions: list[dict[str, Any]], metrics: dict[str, Any], refs: dict[str, str]) -> None:
    status = metrics.get("lattice_status")
    score = _safe_float(metrics.get("lattice_trust_score"))
    if status == "failed":
        actions.append(
            {
                "priority": "critical",
                "action": "revise_lattice_domain_before_fluent",
                "reason": "The recipe-to-lattice summary has blocking geometry or zoning errors.",
                "evidence": _evidence(refs, "lattice_domain_summary"),
            }
        )
        return
    if score is not None and score < 0.75:
        actions.append(
            {
                "priority": "high",
                "action": "increase_recipe_resolution_or_clearance",
                "reason": "The lattice trust score is below the bounded pilot handoff threshold.",
                "evidence": _evidence(refs, "lattice_domain_summary"),
            }
        )
    min_obstacle = _safe_float(metrics.get("min_obstacle_resolution_cells"))
    if min_obstacle is not None and min_obstacle < 6:
        actions.append(
            {
                "priority": "high",
                "action": "refine_obstacle_lattice_resolution",
                "reason": "The smallest obstacle size has fewer than 6 cells in the recipe lattice.",
                "evidence": _evidence(refs, "lattice_domain_summary"),
            }
        )
    min_clearance = _safe_float(metrics.get("min_obstacle_clearance_cells"))
    if min_clearance is not None and min_clearance < 3:
        actions.append(
            {
                "priority": "high",
                "action": "move_obstacle_or_enlarge_domain",
                "reason": "The obstacle has less than 3 cells of clearance to a domain boundary.",
                "evidence": _evidence(refs, "lattice_domain_summary"),
            }
        )


def _add_convergence_actions(actions: list[dict[str, Any]], metrics: dict[str, Any], refs: dict[str, str]) -> None:
    status = metrics.get("native_convergence_status")
    reduction = _safe_float(metrics.get("native_reduction_ratio"))
    nonincreasing = _safe_float(metrics.get("native_nonincreasing_fraction"))
    if status not in {"parsed", "partial"}:
        actions.append(
            {
                "priority": "medium",
                "action": "collect_native_residual_history",
                "reason": "Native residual history was not available, so convergence-aware handoff confidence is limited.",
                "evidence": _evidence(refs, "native_convergence", "stdout"),
            }
        )
        return
    if reduction is not None and reduction > 1.0:
        actions.append(
            {
                "priority": "high",
                "action": "extend_or_recondition_pilot_run",
                "reason": "Native residual increased during the short pilot run.",
                "evidence": _evidence(refs, "native_convergence"),
            }
        )
    elif reduction is not None and reduction > 0.8:
        actions.append(
            {
                "priority": "medium",
                "action": "extend_pilot_steps_before_handoff",
                "reason": "Native residual reduction is weak for an automatic Fluent handoff.",
                "evidence": _evidence(refs, "native_convergence"),
            }
        )
    if nonincreasing is not None and nonincreasing < 0.5:
        actions.append(
            {
                "priority": "medium",
                "action": "review_solver_stability_trace",
                "reason": "Less than half of residual samples are non-increasing.",
                "evidence": _evidence(refs, "native_convergence"),
            }
        )


def _add_field_actions(actions: list[dict[str, Any]], metrics: dict[str, Any], refs: dict[str, str]) -> None:
    if metrics.get("field_parser_status") != "parsed":
        actions.append(
            {
                "priority": "medium",
                "action": "collect_parseable_field_outputs",
                "reason": "No parseable field QoI was available for field-aware Fluent hints.",
                "evidence": _evidence(refs, "field_qoi", "result_manifest"),
            }
        )
        return
    outlet_spread = _safe_float(metrics.get("outlet_spread_ratio"))
    reverse = _safe_float(metrics.get("outlet_reverse_flow_fraction"))
    if (outlet_spread is not None and outlet_spread > 0.25) or (reverse is not None and reverse > 0.0):
        actions.append(
            {
                "priority": "medium",
                "action": "review_downstream_domain_extent",
                "reason": "The pilot field shows elevated outlet spread or reverse-flow fraction.",
                "evidence": _evidence(refs, "field_qoi"),
            }
        )
    if metrics.get("wake_status") == "detected":
        actions.append(
            {
                "priority": "medium",
                "action": "use_wake_bbox_for_fluent_refinement",
                "reason": "The pilot field detected a wake bounding box that can seed Fluent local sizing.",
                "evidence": _evidence(refs, "field_qoi"),
            }
        )


def _decision_status(actions: list[dict[str, Any]]) -> str:
    names = {str(action.get("action")) for action in actions}
    priorities = {str(action.get("priority")) for action in actions}
    if "revise_lattice_domain_before_fluent" in names:
        return "revise_lattice_domain"
    if "extend_or_recondition_pilot_run" in names or "extend_pilot_steps_before_handoff" in names:
        return "extend_pilot_before_handoff"
    if "review_downstream_domain_extent" in names:
        return "review_domain_extent"
    if "collect_parseable_field_outputs" in names and "collect_native_residual_history" in names:
        return "insufficient_evidence"
    if "high" in priorities:
        return "review_before_handoff"
    return "proceed_with_advisory_handoff"


def _confidence(status: str, metrics: dict[str, Any]) -> str:
    if status in {"revise_lattice_domain", "insufficient_evidence"}:
        return "low"
    parsed_count = sum(
        [
            metrics.get("lattice_status") in {"passed", "warning"},
            metrics.get("native_convergence_status") in {"parsed", "partial"},
            metrics.get("field_parser_status") == "parsed",
        ]
    )
    if status == "proceed_with_advisory_handoff" and parsed_count == 3:
        return "medium"
    if parsed_count >= 2:
        return "medium"
    return "low"


def _evidence(refs: dict[str, str], *keys: str) -> list[str]:
    evidence = [refs[key] for key in keys if refs.get(key)]
    return evidence or [key for key in keys]


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
