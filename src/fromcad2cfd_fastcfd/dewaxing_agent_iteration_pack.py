"""Agent-guided iterative FastFluent dewaxing campaign.

This module turns the dewaxing native solver into a closed-loop Agent campaign:
the Agent proposes candidates from prior native evidence, runs real FastFluent-
native calculations, rejects numerically fragile candidates, and accepts the
best stable reduced-order candidate. It never launches Fluent.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .dewaxing_native_solver import demo_dewaxing_native_case, run_dewaxing_native_solver
from .dewaxing_native_validation_pack import QOI_METRICS, STABILITY_THRESHOLDS
from .file_io import ensure_dir, write_json_file, write_text_file
from .practical_native_artifacts import write_csv
from .result_pack import compile_native_result_pack, validate_result_pack


DEWAXING_AGENT_ITERATION_SCHEMA_VERSION = "fastfluent_dewaxing_agent_iteration_pack_v1"
DEWAXING_AGENT_ITERATION_DECISION_SCHEMA_VERSION = "fastfluent_dewaxing_agent_iteration_decision_v1"

LIMITATIONS = [
    "This pack uses the FastFluent-native reduced-order dewaxing solver only.",
    "It does not launch Fluent, call PyFluent, compile UDFs, or edit Fluent case/data files.",
    "The Agent iterates reduced-order candidate assumptions before any new high-fidelity CFD is requested.",
    "Accepted candidates remain application-screening evidence, not final CFD validation.",
]


def default_dewaxing_agent_iteration_plan() -> list[dict[str, Any]]:
    """Return the deterministic Agent proposal plan used by the campaign."""

    return [
        _round(
            0,
            "single_factor_screen",
            "Establish baseline and one-factor directions for timing, risk-window, and stress behavior.",
            [
                _candidate("baseline", "Baseline native case", [], "Control case for objective and sensitivity comparison."),
                _candidate(
                    "shell_thin",
                    "Effective thinner shell",
                    [_scale("domain.shell_thickness_m", 0.80)],
                    "Existing study candidate that improves full-melt timing.",
                ),
                _candidate(
                    "latent_high",
                    "Higher wax latent heat",
                    [_scale("wax.latent_heat_J_kg", 1.15)],
                    "Check whether delaying melt through latent heat improves timing without changing geometry.",
                ),
                _candidate(
                    "path108",
                    "Thicker total thermal path",
                    [_scale("domain.thickness_m", 1.08)],
                    "Probe total thermal path because it directly controls full-melt timing.",
                ),
                _candidate(
                    "initial_high5",
                    "Warmer initial wax and shell",
                    [_offset("initial.temperature_K", 5.0)],
                    "Probe initial temperature because the smoothed risk-window is sensitive to thermal state.",
                ),
                _candidate(
                    "steam_low10",
                    "Lower steam temperature",
                    [_offset("steam_boundary.temperature_K", -10.0)],
                    "Probe the strongest full-melt sensitivity from the native study.",
                ),
            ],
        ),
        _round(
            1,
            "combined_response",
            "Combine the best timing and risk-window directions instead of sweeping one factor at a time.",
            [
                _candidate(
                    "path108_initial5",
                    "Thermal path 1.08 with initial +5 K",
                    [_scale("domain.thickness_m", 1.08), _offset("initial.temperature_K", 5.0)],
                    "Combine full-melt timing correction with risk-window correction.",
                ),
                _candidate(
                    "shell080_latent110_initial5",
                    "Shell 0.80, latent 1.10, initial +5 K",
                    [_scale("domain.shell_thickness_m", 0.80), _scale("wax.latent_heat_J_kg", 1.10), _offset("initial.temperature_K", 5.0)],
                    "Test whether the previous shell candidate can be stabilized by latent heat and initial state.",
                ),
                _candidate(
                    "shell080_path104_initial5",
                    "Shell 0.80, path 1.04, initial +5 K",
                    [_scale("domain.shell_thickness_m", 0.80), _scale("domain.thickness_m", 1.04), _offset("initial.temperature_K", 5.0)],
                    "Blend shell-thin timing improvement with a modest path correction.",
                ),
                _candidate(
                    "path106_initial6",
                    "Thermal path 1.06 with initial +6 K",
                    [_scale("domain.thickness_m", 1.06), _offset("initial.temperature_K", 6.0)],
                    "Moderate version of the combined path/initial correction for stability.",
                ),
            ],
        ),
        _round(
            2,
            "local_refinement",
            "Locally refine the combined path and initial-temperature direction and let validation reject fragile points.",
            [
                _candidate(
                    "path108_initial4",
                    "Thermal path 1.08 with initial +4 K",
                    [_scale("domain.thickness_m", 1.08), _offset("initial.temperature_K", 4.0)],
                    "Refine the combined correction toward lower risk-time bias.",
                ),
                _candidate(
                    "path108_initial6",
                    "Thermal path 1.08 with initial +6 K",
                    [_scale("domain.thickness_m", 1.08), _offset("initial.temperature_K", 6.0)],
                    "Refine the combined correction around the best current path.",
                ),
                _candidate(
                    "path108_initial8",
                    "Thermal path 1.08 with initial +8 K",
                    [_scale("domain.thickness_m", 1.08), _offset("initial.temperature_K", 8.0)],
                    "Test a stronger initial-state correction while keeping the path correction below the fragile 1.10 setting.",
                ),
                _candidate(
                    "path110_initial6",
                    "Thermal path 1.10 with initial +6 K",
                    [_scale("domain.thickness_m", 1.10), _offset("initial.temperature_K", 6.0)],
                    "Test stronger full-melt correction with moderate initial-state correction.",
                ),
                _candidate(
                    "path110_initial8",
                    "Thermal path 1.10 with initial +8 K",
                    [_scale("domain.thickness_m", 1.10), _offset("initial.temperature_K", 8.0)],
                    "Best-fit trial; it must still pass stability before acceptance.",
                ),
                _candidate(
                    "path104_initial5",
                    "Thermal path 1.04 with initial +5 K",
                    [_scale("domain.thickness_m", 1.04), _offset("initial.temperature_K", 5.0)],
                    "Conservative fallback if stronger path corrections fail grid/time-step checks.",
                ),
            ],
        ),
    ]


def run_dewaxing_agent_iteration_pack(
    *,
    output_dir: str | Path,
    comparison_pack: str | Path | None = None,
    max_rounds: int | None = None,
    max_candidates_per_round: int | None = None,
    max_validation_targets: int = 8,
    iteration_plan: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the Agent-guided iterative native dewaxing campaign."""

    root = Path(output_dir)
    ensure_dir(root)
    plan = list(iteration_plan or default_dewaxing_agent_iteration_plan())
    if max_rounds is not None:
        plan = plan[: max(1, int(max_rounds))]

    artifacts = {
        "manifest": str(root / "agent_iteration_manifest.json"),
        "candidate_summary_csv": str(root / "candidate_summary.csv"),
        "candidate_summary_json": str(root / "candidate_summary.json"),
        "round_trace": str(root / "round_trace.json"),
        "agent_decision": str(root / "agent_decision.json"),
        "iteration_report": str(root / "iteration_report.md"),
    }
    base_case = demo_dewaxing_native_case()
    candidates: list[dict[str, Any]] = []
    round_trace: list[dict[str, Any]] = []
    seen: set[str] = set()
    native_runs = 0
    native_cell_steps = 0
    for round_spec in plan:
        specs = list(round_spec.get("candidates", []))
        if max_candidates_per_round is not None:
            specs = specs[: max(1, int(max_candidates_per_round))]
        round_candidates: list[dict[str, Any]] = []
        for spec in specs:
            candidate_id = str(spec["candidate_id"])
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            candidate = _run_candidate(
                spec,
                base_case,
                root=root / "candidates",
                comparison_pack=comparison_pack,
                round_index=int(round_spec["round_index"]),
            )
            native_runs += 1
            native_cell_steps += _cell_time_steps(candidate)
            candidates.append(candidate)
            round_candidates.append(candidate)
        best_after_round = _compact_candidate(_rank_candidates(candidates)[0]) if candidates else {}
        round_trace.append(
            {
                "round_index": round_spec.get("round_index"),
                "round_id": round_spec.get("round_id"),
                "agent_hypothesis": round_spec.get("agent_hypothesis"),
                "candidate_ids": [item.get("candidate_id") for item in round_candidates],
                "best_after_round": best_after_round,
            }
        )

    ranked = _rank_candidates(candidates)
    validation_reviews: list[dict[str, Any]] = []
    accepted: dict[str, Any] | None = None
    validation_limit = max(0, int(max_validation_targets))
    if validation_limit:
        for candidate in ranked[:validation_limit]:
            review = _run_candidate_validation(candidate, base_case, root=root / "candidate_validation", comparison_pack=comparison_pack)
            native_runs += int(review.get("validation_case_count", 0))
            native_cell_steps += int(review.get("native_cell_time_steps", 0))
            validation_reviews.append(review)
            if review.get("quality_status") == "passed":
                accepted = candidate
                break

    baseline = _candidate_by_id(candidates, "baseline") or (ranked[-1] if ranked else {})
    shell_thin = _candidate_by_id(candidates, "shell_thin") or {}
    decision = _agent_decision(
        candidates,
        validation_reviews,
        accepted,
        baseline=baseline,
        shell_thin=shell_thin,
        native_runs=native_runs,
        native_cell_steps=native_cell_steps,
    )
    status = "success" if candidates and accepted is not None else "warning"
    quality_status = "passed" if decision.get("accepted_candidate_validation_status") == "passed" else "warning"
    manifest = {
        "schema_version": DEWAXING_AGENT_ITERATION_SCHEMA_VERSION,
        "status": status,
        "quality_status": quality_status,
        "case_id": "dewaxing_agent_iteration_pack",
        "comparison_pack": str(comparison_pack) if comparison_pack else None,
        "round_count": len(plan),
        "candidate_count": len(candidates),
        "validation_target_count": len(validation_reviews),
        "round_trace": round_trace,
        "candidates": candidates,
        "validation_reviews": validation_reviews,
        "agent_decision": decision,
        "artifacts": artifacts,
        "execution_boundary": {
            "new_fluent_calculation": False,
            "fluent_launched": False,
            "fluent_case_or_data_edited": False,
            "native_dewaxing_solver_runs": native_runs,
            "native_cell_time_steps": native_cell_steps,
        },
        "limitations": list(LIMITATIONS),
    }
    write_json_file(root / "agent_iteration_manifest.json", manifest)
    write_json_file(root / "candidate_summary.json", candidates)
    write_csv(root / "candidate_summary.csv", [_candidate_csv_row(item) for item in candidates])
    write_json_file(root / "round_trace.json", round_trace)
    write_json_file(root / "agent_decision.json", decision)
    write_text_file(root / "iteration_report.md", dewaxing_agent_iteration_pack_markdown(manifest))
    return manifest


def dewaxing_agent_iteration_pack_markdown(pack: dict[str, Any]) -> str:
    """Render a concise Markdown report for CLI output and artifacts."""

    decision = pack.get("agent_decision", {}) if isinstance(pack.get("agent_decision"), dict) else {}
    accepted = decision.get("accepted_candidate", {}) if isinstance(decision.get("accepted_candidate"), dict) else {}
    best = decision.get("best_unvalidated_candidate", {}) if isinstance(decision.get("best_unvalidated_candidate"), dict) else {}
    lines = [
        "# FastFluent Dewaxing Agent Iteration Pack",
        "",
        f"- Status: `{pack.get('status')}`",
        f"- Quality status: `{pack.get('quality_status')}`",
        f"- Rounds: `{pack.get('round_count')}`",
        f"- Candidates: `{pack.get('candidate_count')}`",
        f"- Validation targets checked: `{pack.get('validation_target_count')}`",
        f"- Native solver runs: `{pack.get('execution_boundary', {}).get('native_dewaxing_solver_runs')}`",
        f"- Native cell-time steps: `{pack.get('execution_boundary', {}).get('native_cell_time_steps')}`",
        f"- New Fluent calculation: `{pack.get('execution_boundary', {}).get('new_fluent_calculation')}`",
        "",
        "## Agent Decision",
        "",
        f"- Best unvalidated candidate: `{best.get('candidate_id')}` objective `{best.get('agent_objective_score')}`",
        f"- Accepted stable candidate: `{accepted.get('candidate_id')}` objective `{accepted.get('agent_objective_score')}`",
        f"- Accepted validation status: `{decision.get('accepted_candidate_validation_status')}`",
        f"- Improvement vs baseline objective: `{decision.get('objective_improvement_vs_baseline')}`",
        f"- Improvement vs shell_thin objective: `{decision.get('objective_improvement_vs_shell_thin')}`",
        "",
        "## Rejected During Stability Review",
        "",
    ]
    rejected = decision.get("stability_rejected_candidates", []) if isinstance(decision.get("stability_rejected_candidates"), list) else []
    if rejected:
        for item in rejected:
            lines.append(f"- `{item.get('candidate_id')}`: {', '.join(item.get('warnings', []))}")
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    for item in decision.get("recommendations", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Application Scope", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _run_candidate(
    spec: dict[str, Any],
    base_case: dict[str, Any],
    *,
    root: Path,
    comparison_pack: str | Path | None,
    round_index: int,
) -> dict[str, Any]:
    candidate_id = str(spec["candidate_id"])
    case = deepcopy(base_case)
    case["case_id"] = f"dewaxing_agent_iteration_{candidate_id}"
    case["case_name"] = str(spec.get("name") or candidate_id)
    for edit in spec.get("edits", []):
        _apply_edit(case, edit)
    candidate_root = root / f"{round_index:02d}_{candidate_id}"
    native = run_dewaxing_native_solver(case, output_dir=candidate_root / "native_result", comparison_pack=comparison_pack)
    result_pack = compile_native_result_pack(candidate_root / "native_result" / "dewaxing_native_status.json", output_dir=candidate_root / "result_pack")
    pack_validation = validate_result_pack(candidate_root / "result_pack")
    metrics = native.get("outputs", {}).get("qoi", {}).get("metrics", {})
    comparison = native.get("outputs", {}).get("comparison", {})
    comparison_metrics = comparison.get("metrics", {}) if isinstance(comparison.get("metrics"), dict) else {}
    return {
        "candidate_id": candidate_id,
        "name": spec.get("name"),
        "round_index": round_index,
        "rationale": spec.get("rationale"),
        "edits": spec.get("edits", []),
        "status": native.get("status"),
        "quality_status": native.get("quality_status"),
        "result_pack_status": result_pack.get("status"),
        "result_pack_validation_status": pack_validation.get("status"),
        "agent_objective_score": _agent_objective(metrics, comparison_metrics),
        "metrics": metrics,
        "comparison_metrics": comparison_metrics,
        "warnings": native.get("warnings", []) + pack_validation.get("warnings", []),
        "blocking_errors": native.get("blocking_errors", []) + pack_validation.get("errors", []),
        "artifacts": {
            "native_result": str(candidate_root / "native_result" / "dewaxing_native_status.json"),
            "native_report": str(candidate_root / "native_result" / "dewaxing_native_report.md"),
            "history": str(candidate_root / "native_result" / "dewaxing_native_history.csv"),
            "final_field": str(candidate_root / "native_result" / "dewaxing_native_final_field.csv"),
            "result_pack": str(candidate_root / "result_pack" / "result_pack.json"),
        },
    }


def _run_candidate_validation(
    candidate: dict[str, Any],
    base_case: dict[str, Any],
    *,
    root: Path,
    comparison_pack: str | Path | None,
) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id"))
    validation_root = root / candidate_id
    cases: list[dict[str, Any]] = []
    native_cell_steps = 0
    for index, perturbation in enumerate(_validation_perturbations()):
        case = deepcopy(base_case)
        case["case_id"] = f"dewaxing_agent_validation_{candidate_id}_{perturbation['case_variant']}"
        case["case_name"] = f"{candidate.get('name')} validation {perturbation['case_variant']}"
        for edit in list(candidate.get("edits", [])) + list(perturbation.get("edits", [])):
            _apply_edit(case, edit)
        case_root = validation_root / f"{index:02d}_{perturbation['case_variant']}"
        native = run_dewaxing_native_solver(case, output_dir=case_root / "native_result", comparison_pack=comparison_pack)
        result_pack = compile_native_result_pack(case_root / "native_result" / "dewaxing_native_status.json", output_dir=case_root / "result_pack")
        pack_validation = validate_result_pack(case_root / "result_pack")
        metrics = native.get("outputs", {}).get("qoi", {}).get("metrics", {})
        comparison = native.get("outputs", {}).get("comparison", {})
        comparison_metrics = comparison.get("metrics", {}) if isinstance(comparison.get("metrics"), dict) else {}
        row = {
            "validation_case_id": f"{candidate_id}_{perturbation['case_variant']}",
            "candidate_id": candidate_id,
            "case_variant": perturbation["case_variant"],
            "edits": list(candidate.get("edits", [])) + list(perturbation.get("edits", [])),
            "status": native.get("status"),
            "quality_status": native.get("quality_status"),
            "result_pack_status": result_pack.get("status"),
            "result_pack_validation_status": pack_validation.get("status"),
            "metrics": metrics,
            "comparison_metrics": comparison_metrics,
            "warnings": native.get("warnings", []) + pack_validation.get("warnings", []),
            "blocking_errors": native.get("blocking_errors", []) + pack_validation.get("errors", []),
            "artifacts": {
                "native_result": str(case_root / "native_result" / "dewaxing_native_status.json"),
                "result_pack": str(case_root / "result_pack" / "result_pack.json"),
            },
        }
        native_cell_steps += _cell_time_steps(row)
        cases.append(row)
    stability = _candidate_stability(cases)
    warnings = list(stability.get("warnings", []))
    quality_status = "warning" if warnings else "passed"
    review = {
        "schema_version": "fastfluent_dewaxing_agent_candidate_validation_v1",
        "candidate_id": candidate_id,
        "quality_status": quality_status,
        "validation_case_count": len(cases),
        "native_cell_time_steps": native_cell_steps,
        "cases": cases,
        "qoi_stability": stability,
        "warnings": warnings,
        "artifacts": {
            "validation_dir": str(validation_root),
            "validation_review": str(validation_root / "candidate_validation_review.json"),
        },
    }
    write_json_file(validation_root / "candidate_validation_review.json", review)
    write_csv(validation_root / "candidate_validation_summary.csv", [_validation_csv_row(item) for item in cases])
    return review


def _candidate_stability(cases: list[dict[str, Any]]) -> dict[str, Any]:
    current = next((item for item in cases if item.get("case_variant") == "current"), cases[0] if cases else {})
    metric_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for metric_name in QOI_METRICS:
        values = [
            {
                "validation_case_id": item.get("validation_case_id"),
                "case_variant": item.get("case_variant"),
                "value": _maybe_float(item.get("metrics", {}).get(metric_name)),
            }
            for item in cases
        ]
        missing = [str(item.get("case_variant")) for item in values if item.get("value") is None]
        present = [float(item["value"]) for item in values if item.get("value") is not None]
        current_value = _maybe_float(current.get("metrics", {}).get(metric_name)) if current else None
        threshold = STABILITY_THRESHOLDS.get(metric_name)
        if not present or current_value in {None, 0.0}:
            quality = "warning"
            relative_spread = None
            min_value = None
            max_value = None
            spread = None
        else:
            min_value = min(present)
            max_value = max(present)
            spread = max_value - min_value
            if metric_name == "energy_balance_relative_error":
                relative_spread = max_value
            else:
                relative_spread = spread / max(abs(float(current_value)), 1.0e-12)
            quality = "warning" if threshold is not None and relative_spread > threshold else "passed"
        if missing and metric_name == "predicted_full_melt_time_s":
            quality = "warning"
            warnings.append(f"{metric_name} missing for variants: {', '.join(missing)}.")
        if quality == "warning" and not (missing and metric_name == "predicted_full_melt_time_s"):
            warnings.append(f"{metric_name} relative spread {relative_spread} exceeds threshold {threshold}.")
        metric_rows.append(
            {
                "metric": metric_name,
                "quality_status": quality,
                "current_value": current_value,
                "min_value": min_value,
                "max_value": max_value,
                "spread": spread,
                "relative_spread_vs_current": relative_spread,
                "threshold": threshold,
                "values": values,
            }
        )
    return {
        "schema_version": "fastfluent_dewaxing_agent_candidate_stability_v1",
        "status": "warning" if warnings else "passed",
        "metrics": metric_rows,
        "warnings": warnings,
    }


def _agent_decision(
    candidates: list[dict[str, Any]],
    validation_reviews: list[dict[str, Any]],
    accepted: dict[str, Any] | None,
    *,
    baseline: dict[str, Any],
    shell_thin: dict[str, Any],
    native_runs: int,
    native_cell_steps: int,
) -> dict[str, Any]:
    ranked = _rank_candidates(candidates)
    best = ranked[0] if ranked else {}
    accepted_compact = _compact_candidate(accepted or {})
    rejected = [
        {
            "candidate_id": item.get("candidate_id"),
            "quality_status": item.get("quality_status"),
            "warnings": item.get("warnings", []),
        }
        for item in validation_reviews
        if item.get("quality_status") != "passed"
    ]
    if accepted:
        recommendations = [
            "Use the accepted candidate for the next reduced-order paper evidence comparison if its application scope is retained.",
            "Report both the best unvalidated candidate and the stability-rejected candidates to show Agent self-checking.",
            "Use the accepted candidate validation pack before requesting any new high-fidelity Fluent calculation.",
        ]
        recommendations.append(
            f"The accepted candidate `{accepted.get('candidate_id')}` improves the combined native objective relative to `shell_thin` while passing grid/time-step checks."
        )
    else:
        recommendations = [
            "Increase max_validation_targets or add a conservative refinement round before selecting a final reduced-order candidate.",
            "Report the rejected top candidates as evidence that the Agent does not accept fitted points that fail stability review.",
            "Keep the previous validated candidate until an iterative candidate passes stability review.",
        ]
    return {
        "schema_version": DEWAXING_AGENT_ITERATION_DECISION_SCHEMA_VERSION,
        "status": "passed" if accepted else "warning",
        "best_unvalidated_candidate": _compact_candidate(best),
        "accepted_candidate": accepted_compact,
        "accepted_candidate_validation_status": _validation_status_for(validation_reviews, accepted.get("candidate_id") if accepted else None),
        "stability_rejected_candidates": rejected,
        "objective_improvement_vs_baseline": _objective_improvement(accepted or {}, baseline),
        "objective_improvement_vs_shell_thin": _objective_improvement(accepted or {}, shell_thin),
        "recommendations": recommendations,
        "execution_summary": {
            "native_dewaxing_solver_runs": native_runs,
            "native_cell_time_steps": native_cell_steps,
            "new_fluent_calculation": False,
        },
        "application_scope": {
            "can_support_agent_workflow_control": True,
            "can_support_fastfluent_screening_decision": bool(accepted),
            "can_support_fluent_parameter_prioritization": bool(accepted),
            "can_support_final_cfd_validation": False,
            "can_support_new_fluent_calculation": False,
        },
    }


def _validation_perturbations() -> list[dict[str, Any]]:
    return [
        {"case_variant": "current", "edits": []},
        {"case_variant": "coarse_grid", "edits": [_set("domain.nx", 15), _set("domain.ny", 11)]},
        {"case_variant": "fine_grid", "edits": [_set("domain.nx", 25), _set("domain.ny", 19), _set("time.time_step_s", 0.04)]},
        {"case_variant": "dt_large", "edits": [_set("time.time_step_s", 0.10)]},
        {"case_variant": "dt_small", "edits": [_set("time.time_step_s", 0.04)]},
    ]


def _rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(candidates, key=lambda item: _float_or(item.get("agent_objective_score"), 999.0))


def _agent_objective(metrics: dict[str, Any], comparison_metrics: dict[str, Any]) -> float:
    full_error = _float_or(comparison_metrics.get("full_melt_time_relative_error"), 2.0)
    risk_error = _float_or(comparison_metrics.get("dominant_risk_time_relative_error"), 1.0)
    energy_error = _float_or(metrics.get("energy_balance_relative_error"), 0.5)
    no_melt_penalty = 1.0 if metrics.get("full_melt_reached") is not True else 0.0
    return round(0.60 * full_error + 0.30 * risk_error + 0.10 * energy_error + 0.05 * no_melt_penalty, 6)


def _cell_time_steps(item: dict[str, Any]) -> int:
    metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
    return int(_float_or(metrics.get("grid_cells"), 0.0)) * int(_float_or(metrics.get("time_steps"), 0.0))


def _compact_candidate(item: dict[str, Any]) -> dict[str, Any]:
    metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
    comparison = item.get("comparison_metrics", {}) if isinstance(item.get("comparison_metrics"), dict) else {}
    return {
        "candidate_id": item.get("candidate_id"),
        "name": item.get("name"),
        "round_index": item.get("round_index"),
        "agent_objective_score": item.get("agent_objective_score"),
        "predicted_full_melt_time_s": metrics.get("predicted_full_melt_time_s"),
        "dominant_risk_time_s": metrics.get("dominant_risk_time_s"),
        "early_max_shell_stress_proxy_MPa": metrics.get("early_max_shell_stress_proxy_MPa"),
        "full_melt_time_relative_error": comparison.get("full_melt_time_relative_error"),
        "dominant_risk_time_relative_error": comparison.get("dominant_risk_time_relative_error"),
    }


def _candidate_csv_row(item: dict[str, Any]) -> dict[str, Any]:
    metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
    comparison = item.get("comparison_metrics", {}) if isinstance(item.get("comparison_metrics"), dict) else {}
    return {
        "candidate_id": item.get("candidate_id"),
        "round_index": item.get("round_index"),
        "agent_objective_score": item.get("agent_objective_score"),
        "predicted_full_melt_time_s": metrics.get("predicted_full_melt_time_s"),
        "dominant_risk_time_s": metrics.get("dominant_risk_time_s"),
        "early_max_shell_stress_proxy_MPa": metrics.get("early_max_shell_stress_proxy_MPa"),
        "energy_balance_relative_error": metrics.get("energy_balance_relative_error"),
        "full_melt_time_relative_error": comparison.get("full_melt_time_relative_error"),
        "dominant_risk_time_relative_error": comparison.get("dominant_risk_time_relative_error"),
    }


def _validation_csv_row(item: dict[str, Any]) -> dict[str, Any]:
    metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
    comparison = item.get("comparison_metrics", {}) if isinstance(item.get("comparison_metrics"), dict) else {}
    return {
        "validation_case_id": item.get("validation_case_id"),
        "candidate_id": item.get("candidate_id"),
        "case_variant": item.get("case_variant"),
        "predicted_full_melt_time_s": metrics.get("predicted_full_melt_time_s"),
        "dominant_risk_time_s": metrics.get("dominant_risk_time_s"),
        "early_max_shell_stress_proxy_MPa": metrics.get("early_max_shell_stress_proxy_MPa"),
        "energy_balance_relative_error": metrics.get("energy_balance_relative_error"),
        "full_melt_time_relative_error": comparison.get("full_melt_time_relative_error"),
        "dominant_risk_time_relative_error": comparison.get("dominant_risk_time_relative_error"),
    }


def _validation_status_for(reviews: list[dict[str, Any]], candidate_id: str | None) -> str | None:
    for item in reviews:
        if item.get("candidate_id") == candidate_id:
            return item.get("quality_status")
    return None


def _objective_improvement(candidate: dict[str, Any], reference: dict[str, Any]) -> float | None:
    c_score = _maybe_float(candidate.get("agent_objective_score"))
    r_score = _maybe_float(reference.get("agent_objective_score"))
    if c_score is None or r_score in {None, 0.0}:
        return None
    return (float(r_score) - float(c_score)) / abs(float(r_score))


def _candidate_by_id(candidates: list[dict[str, Any]], candidate_id: str) -> dict[str, Any] | None:
    for item in candidates:
        if item.get("candidate_id") == candidate_id:
            return item
    return None


def _apply_edit(case: dict[str, Any], edit: dict[str, Any]) -> None:
    target: Any = case
    path = str(edit["path"]).split(".")
    for key in path[:-1]:
        target = target[key]
    leaf = path[-1]
    operation = edit.get("operation")
    if operation == "scale":
        target[leaf] = float(target[leaf]) * float(edit["value"])
    elif operation == "offset":
        target[leaf] = float(target[leaf]) + float(edit["value"])
    elif operation == "set":
        target[leaf] = edit["value"]
    else:
        raise ValueError(f"Unsupported Agent iteration edit operation: {operation}")


def _round(round_index: int, round_id: str, agent_hypothesis: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "round_index": round_index,
        "round_id": round_id,
        "agent_hypothesis": agent_hypothesis,
        "candidates": candidates,
    }


def _candidate(candidate_id: str, name: str, edits: list[dict[str, Any]], rationale: str) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "name": name,
        "edits": edits,
        "rationale": rationale,
    }


def _scale(path: str, value: float) -> dict[str, Any]:
    return {"path": path, "operation": "scale", "value": value}


def _offset(path: str, value: float) -> dict[str, Any]:
    return {"path": path, "operation": "offset", "value": value}


def _set(path: str, value: Any) -> dict[str, Any]:
    return {"path": path, "operation": "set", "value": value}


def _maybe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_or(value: Any, fallback: float = 0.0) -> float:
    parsed = _maybe_float(value)
    return fallback if parsed is None else parsed
