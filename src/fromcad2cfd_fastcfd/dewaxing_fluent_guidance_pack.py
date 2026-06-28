"""FastFluent-to-Fluent guidance compiler for the dewaxing case study.

This module reorganizes existing FastFluent-native dewaxing outputs and
completed Fluent result packs into a Fluent-facing guidance artifact. It does
not run Fluent, rerun the native solver, edit Fluent case/data files, or
generate Fluent TUI.
"""

from __future__ import annotations

import math
import html
from pathlib import Path
from typing import Any

from .file_io import ensure_dir, read_json_file, write_json_file, write_text_file
from .practical_native_artifacts import write_csv


DEWAXING_FLUENT_GUIDANCE_SCHEMA_VERSION = "fastfluent_to_fluent_dewaxing_guidance_pack_v1"

NATURE_SOFT_PALETTE = {
    "paper": "#FFFFFF",
    "ink": "#1E2327",
    "muted": "#6D7176",
    "grid": "#CBBCC7",
    "rice": "#F6F2EA",
    "blue_very_light": "#E5EDF3",
    "blue_light": "#D1DEE8",
    "blue_mid": "#B6CBDC",
    "blue_deep": "#9FB9CE",
    "blue_ink": "#6F91AA",
    "transition": "#CBBCC7",
    "sakura": "#DFAFC0",
    "sakura_deep": "#B8738E",
    "wine_soft": "#8F4A65",
}

FIGURE_STYLE = {
    "style_name": "nature_soft_statistical",
    "source_memory": "earlySteamShock distance-effect nature-style statistical plots",
    "rule": "Use the low-saturation thesis blue-pink palette for workflow figures; keep Fluent contour palettes separate.",
    "palette_hex": NATURE_SOFT_PALETTE,
}

LIMITATIONS = [
    "This guidance pack compiles existing FastFluent-native and completed Fluent evidence.",
    "It does not launch Fluent, call PyFluent, compile UDFs, or edit Fluent case/data files.",
    "FastFluent guidance identifies priorities for targeted Fluent validation; it is not final CFD validation.",
    "Completed Fluent packs are used as retrospective confirmation of the guidance chain.",
]


def compile_dewaxing_fluent_guidance_pack(
    *,
    output_dir: str | Path,
    study_pack: str | Path | None = None,
    validation_pack: str | Path | None = None,
    iteration_pack: str | Path | None = None,
    fluent_bridge_pack: str | Path | None = None,
    manuscript_title: str = "FastFluent-Guided Fluent Dewaxing Workflow",
) -> dict[str, Any]:
    """Compile a paper-facing FastFluent-to-Fluent guidance pack."""

    root = Path(output_dir)
    tables_dir = root / "tables"
    figures_dir = root / "figures"
    sections_dir = root / "sections"
    ensure_dir(tables_dir)
    ensure_dir(figures_dir)
    ensure_dir(sections_dir)

    sources = _load_sources(
        study_pack=study_pack,
        validation_pack=validation_pack,
        iteration_pack=iteration_pack,
        fluent_bridge_pack=fluent_bridge_pack,
    )
    summary = _summary(sources)
    process_rows = _process_partition_rows(sources, summary)
    target_rows = _fluent_validation_target_rows(sources, summary)
    parameter_rows = _parameter_priority_rows(sources)
    asset_rows = _asset_reuse_rows(sources)
    tables = [
        _table("table_01_process_partition_guidance", "Dewaxing process partitions and Fluent guidance", process_rows),
        _table("table_02_fluent_validation_targets", "Targeted Fluent validation recommendations", target_rows),
        _table("table_03_parameter_priority", "FastFluent parameter priorities for Fluent cases", parameter_rows),
        _table("table_04_existing_asset_reuse_map", "Existing assets reused in the guidance chain", asset_rows),
    ]
    for table in tables:
        write_csv(tables_dir / f"{table['table_id']}.csv", table["rows"], table["fieldnames"])
        write_text_file(tables_dir / f"{table['table_id']}.md", _markdown_table(table["fieldnames"], table["rows"]))

    paper_outline = _paper_outline_markdown(summary, manuscript_title=manuscript_title)
    methods_section = _methods_section_markdown(summary, manuscript_title=manuscript_title)
    results_section = _results_section_markdown(summary, process_rows, target_rows, parameter_rows, manuscript_title=manuscript_title)
    fluent_handoff = _fluent_handoff_markdown(summary, target_rows, parameter_rows)
    workflow_notes = _workflow_figure_notes_markdown(summary)
    workflow_figure_path = figures_dir / "figure_01_fastfluent_guided_fluent_workflow.svg"
    write_text_file(workflow_figure_path, _workflow_figure_svg(summary, process_rows, target_rows, parameter_rows))
    figures = [
        {
            "figure_id": "figure_01_fastfluent_guided_fluent_workflow",
            "title": "FastFluent-guided Fluent dewaxing workflow",
            "path": str(workflow_figure_path),
            "kind": "svg",
        }
    ]
    report = _guidance_report_markdown(summary, tables, manuscript_title=manuscript_title)

    artifacts = {
        "manifest": str(root / "guidance_manifest.json"),
        "guidance_report": str(root / "fluent_guidance_report.md"),
        "fluent_handoff_brief": str(root / "fluent_handoff_brief.md"),
        "paper_outline": str(sections_dir / "paper_outline.md"),
        "methods_section": str(sections_dir / "methods_guidance_section.md"),
        "results_section": str(sections_dir / "results_guidance_section.md"),
        "workflow_figure_notes": str(sections_dir / "workflow_figure_notes.md"),
        "tables_dir": str(tables_dir),
        "figures_dir": str(figures_dir),
    }
    pack = {
        "schema_version": DEWAXING_FLUENT_GUIDANCE_SCHEMA_VERSION,
        "status": "success" if not sources["warnings"] else "warning",
        "case_id": "dewaxing_fastfluent_to_fluent_guidance",
        "manuscript_title": manuscript_title,
        "summary": summary,
        "source_packs": sources["paths"],
        "tables": [{key: value for key, value in table.items() if key != "rows"} | {"row_count": len(table["rows"])} for table in tables],
        "figures": figures,
        "figure_style": FIGURE_STYLE,
        "artifacts": artifacts,
        "guidance_claims": _guidance_claims(summary),
        "warnings": sources["warnings"],
        "execution_boundary": {
            "new_fluent_calculation": False,
            "fluent_launched": False,
            "native_dewaxing_solver_rerun": False,
            "fluent_case_or_data_edited": False,
        },
        "limitations": list(LIMITATIONS),
    }
    write_text_file(sections_dir / "paper_outline.md", paper_outline)
    write_text_file(sections_dir / "methods_guidance_section.md", methods_section)
    write_text_file(sections_dir / "results_guidance_section.md", results_section)
    write_text_file(sections_dir / "workflow_figure_notes.md", workflow_notes)
    write_text_file(root / "fluent_handoff_brief.md", fluent_handoff)
    write_text_file(root / "fluent_guidance_report.md", report)
    write_json_file(root / "guidance_manifest.json", pack)
    return pack


def dewaxing_fluent_guidance_pack_markdown(pack: dict[str, Any]) -> str:
    """Render a concise Markdown summary for CLI output."""

    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    lines = [
        "# FastFluent-to-Fluent Dewaxing Guidance Pack",
        "",
        f"- Status: `{pack.get('status')}`",
        f"- Process partitions: `{summary.get('process_partition_count')}`",
        f"- Fluent validation targets: `{summary.get('fluent_validation_target_count')}`",
        f"- Accepted FastFluent candidate: `{summary.get('accepted_candidate_id')}`",
        f"- Native iteration runs: `{summary.get('iteration_solver_runs')}`",
        f"- New Fluent calculation: `{pack.get('execution_boundary', {}).get('new_fluent_calculation')}`",
        f"- Guidance report: `{pack.get('artifacts', {}).get('guidance_report')}`",
        f"- Fluent handoff brief: `{pack.get('artifacts', {}).get('fluent_handoff_brief')}`",
        "",
        "## Guidance Claims",
        "",
    ]
    for item in pack.get("guidance_claims", {}).get("supported_claims", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Application Limits", ""])
    for item in pack.get("guidance_claims", {}).get("application_limits", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _load_sources(
    *,
    study_pack: str | Path | None,
    validation_pack: str | Path | None,
    iteration_pack: str | Path | None,
    fluent_bridge_pack: str | Path | None,
) -> dict[str, Any]:
    warnings: list[str] = []
    study_guidance_path = _resolve_optional_file(study_pack, ["dewaxing_guidance.json"])
    sensitivity_path = _resolve_optional_file(study_pack, ["sensitivity_summary.json"])
    study_manifest_path = _resolve_optional_file(study_pack, ["study_manifest.json"])
    validation_path = _resolve_optional_file(validation_pack, ["validation_pack_manifest.json"])
    iteration_path = _resolve_optional_file(iteration_pack, ["agent_iteration_manifest.json"])
    bridge_path = _resolve_fluent_bridge_status(fluent_bridge_pack)

    payloads: dict[str, Any] = {}
    paths = {
        "study_guidance": str(study_guidance_path) if study_guidance_path else None,
        "sensitivity_summary": str(sensitivity_path) if sensitivity_path else None,
        "study_manifest": str(study_manifest_path) if study_manifest_path else None,
        "validation_pack": str(validation_path) if validation_path else None,
        "iteration_pack": str(iteration_path) if iteration_path else None,
        "fluent_bridge_pack": str(bridge_path) if bridge_path else None,
    }
    for key, path in [
        ("study_guidance", study_guidance_path),
        ("sensitivity", sensitivity_path),
        ("study_manifest", study_manifest_path),
        ("validation", validation_path),
        ("iteration", iteration_path),
        ("fluent_bridge", bridge_path),
    ]:
        if path and path.exists():
            payloads[key] = read_json_file(path)
        else:
            payloads[key] = {}
            warnings.append(f"Missing optional source: {key}.")
    return {"payloads": payloads, "paths": paths, "warnings": warnings}


def _resolve_optional_file(path: str | Path | None, names: list[str]) -> Path | None:
    if not path:
        return None
    source = Path(path)
    if source.is_file():
        return source
    for name in names:
        candidate = source / name
        if candidate.exists():
            return candidate
    return source / names[0]


def _resolve_fluent_bridge_status(path: str | Path | None) -> Path | None:
    if not path:
        return None
    source = Path(path)
    if source.is_file():
        return source
    candidates = [
        source / "dewaxing_result_status.json",
        source / "01_agent_result_pack" / "dewaxing_result_status.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _summary(sources: dict[str, Any]) -> dict[str, Any]:
    payloads = sources["payloads"]
    study = payloads.get("study_guidance", {})
    sensitivity = payloads.get("sensitivity", {})
    study_manifest = payloads.get("study_manifest", {})
    validation = payloads.get("validation", {})
    iteration = payloads.get("iteration", {})
    bridge = payloads.get("fluent_bridge", {})

    early = bridge.get("early_steam_shock_qoi", {}) if isinstance(bridge.get("early_steam_shock_qoi"), dict) else {}
    full = bridge.get("full_cycle_wax_qoi", {}) if isinstance(bridge.get("full_cycle_wax_qoi"), dict) else {}
    melt = full.get("melt_completion", {}) if isinstance(full.get("melt_completion"), dict) else {}
    risk = full.get("dominant_risk_window", {}) if isinstance(full.get("dominant_risk_window"), dict) else {}
    drainage = full.get("drainage_relief", {}) if isinstance(full.get("drainage_relief"), dict) else {}
    accepted = _accepted_candidate(iteration)
    accepted_metrics = accepted.get("metrics", {}) if isinstance(accepted.get("metrics"), dict) else {}
    accepted_cmp = accepted.get("comparison_metrics", {}) if isinstance(accepted.get("comparison_metrics"), dict) else {}
    decision = iteration.get("agent_decision", {}) if isinstance(iteration.get("agent_decision"), dict) else {}
    rejected = decision.get("stability_rejected_candidates", []) if isinstance(decision.get("stability_rejected_candidates"), list) else []
    execution = iteration.get("execution_boundary", {}) if isinstance(iteration.get("execution_boundary"), dict) else {}
    study_execution = study_manifest.get("execution_boundary", {}) if isinstance(study_manifest.get("execution_boundary"), dict) else {}
    validation_execution = validation.get("execution_boundary", {}) if isinstance(validation.get("execution_boundary"), dict) else {}
    top_metrics = sensitivity.get("top_by_metric", {}) if isinstance(sensitivity.get("top_by_metric"), dict) else {}
    process_count = 5
    target_count = 7
    return {
        "process_partition_count": process_count,
        "fluent_validation_target_count": target_count,
        "early_stage_window_s": early.get("stage", "0-4.1 s"),
        "early_case_count": early.get("case_count"),
        "early_max_crack_index": _round(early.get("max_crack_driving_index_over_3p6mpa"), 6),
        "early_max_heat_dose_kj_m2": _round(_nested(early, "max_mean_heat_dose", "heat_dose_kj_m2"), 3),
        "early_max_shell_mean_rise_c": _round(_nested(early, "max_shell_mean_rise", "shell_mean_rise_c"), 3),
        "early_max_impact_impulse_n_s": _round(_nested(early, "max_impact_impulse", "impact_impulse_n_s"), 3),
        "full_melt_time_s": _round(melt.get("first_full_melt_time_s"), 3),
        "latest_avg_liquid_fraction": _round(melt.get("latest_avg_liquid_fraction"), 6),
        "dominant_risk_time_s": _round(risk.get("time_s"), 3),
        "peak_effective_pressure_mpa": _round(risk.get("peak_effective_pressure_mpa"), 6),
        "peak_wall_vm_p995_mpa": _round(risk.get("peak_wall_vm_p995_mpa"), 6),
        "stress_drop_fraction_pct": _pct(drainage.get("stress_drop_fraction_peak_to_latest_p995"), 3),
        "study_solver_runs": study_execution.get("native_dewaxing_solver_runs"),
        "validation_solver_runs": validation_execution.get("native_dewaxing_solver_runs"),
        "validation_cell_time_steps": validation_execution.get("native_cell_time_steps"),
        "iteration_solver_runs": execution.get("native_dewaxing_solver_runs"),
        "iteration_cell_time_steps": execution.get("native_cell_time_steps"),
        "iteration_candidate_count": iteration.get("candidate_count"),
        "iteration_rejected_candidate_count": len(rejected),
        "accepted_candidate_id": accepted.get("candidate_id"),
        "accepted_candidate_name": accepted.get("name"),
        "accepted_candidate_edits": accepted.get("edits", []),
        "accepted_full_melt_time_s": _round(accepted_metrics.get("predicted_full_melt_time_s"), 3),
        "accepted_risk_time_s": _round(accepted_metrics.get("dominant_risk_time_s"), 3),
        "accepted_full_melt_error_pct": _pct(accepted_cmp.get("full_melt_time_relative_error"), 3),
        "accepted_risk_time_error_pct": _pct(accepted_cmp.get("dominant_risk_time_relative_error"), 3),
        "objective_improvement_vs_baseline_pct": _pct(decision.get("objective_improvement_vs_baseline"), 3),
        "objective_improvement_vs_shell_thin_pct": _pct(decision.get("objective_improvement_vs_shell_thin"), 3),
        "study_best_match_variant": _nested(study, "best_match_variant", "variant_id"),
        "study_closest_full_melt_variant": _nested(study, "closest_full_melt_variant", "variant_id"),
        "study_closest_risk_window_variant": _nested(study, "closest_risk_window_variant", "variant_id"),
        "top_full_melt_parameter": _top_parameter(top_metrics, "predicted_full_melt_time_s"),
        "top_risk_time_parameter": _top_parameter(top_metrics, "dominant_risk_time_s"),
        "top_shell_stress_parameter": _top_parameter(top_metrics, "early_max_shell_stress_proxy_MPa"),
        "top_pressure_risk_parameter": _top_parameter(top_metrics, "peak_pressure_risk_proxy"),
    }


def _process_partition_rows(sources: dict[str, Any], summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "partition_id": "P1_early_steam_shock",
            "time_window_s": "0-4.1",
            "fastfluent_screening_role": "identify early thermal-impact screening window and inlet/surface priority",
            "fluent_validation_target": "steam filling, jet path, surface heat dose, normal-impact proxy",
            "priority": "high for boundary-condition and local-load validation",
            "existing_fluent_confirmation": f"early crack index {_fmt(summary.get('early_max_crack_index'))}; max heat dose {_fmt(summary.get('early_max_heat_dose_kj_m2'))} kJ/m2; max impact impulse {_fmt(summary.get('early_max_impact_impulse_n_s'))} N s",
            "paper_use": "show that FastFluent partitions the short early shock stage before full-cycle melting",
        },
        {
            "partition_id": "P2_dominant_risk_window",
            "time_window_s": "~100.7",
            "fastfluent_screening_role": "rank pressure-risk and shell-stress proxy window",
            "fluent_validation_target": "effective pressure, liquid fraction, release ratio, wall VM proxy",
            "priority": "highest full-cycle validation priority",
            "existing_fluent_confirmation": f"peak effective pressure {_fmt(summary.get('peak_effective_pressure_mpa'))} MPa and wall VM P99.5 {_fmt(summary.get('peak_wall_vm_p995_mpa'))} MPa",
            "paper_use": "central example that FastFluent identifies where Fluent should be dense in time and monitors",
        },
        {
            "partition_id": "P3_melt_front_drainage",
            "time_window_s": "120-420",
            "fastfluent_screening_role": "track phase-change progress, melt-front depth, and drainage accessibility",
            "fluent_validation_target": "liquid fraction fields, outlet discharge, unreleased wax fraction",
            "priority": "high for full-cycle melt/drainage interpretation",
            "existing_fluent_confirmation": f"late pressure/stress drop {_fmt(summary.get('stress_drop_fraction_pct'))}%",
            "paper_use": "connect melt progression to drainage relief rather than only final liquid fraction",
        },
        {
            "partition_id": "P4_full_melt_completion",
            "time_window_s": "~409-420",
            "fastfluent_screening_role": "predict completion timing and final melt state",
            "fluent_validation_target": "full-melt threshold crossing and final liquid fraction",
            "priority": "medium-high for end-state validation",
            "existing_fluent_confirmation": f"first full-melt time {_fmt(summary.get('full_melt_time_s'))} s; final LF {_fmt(summary.get('latest_avg_liquid_fraction'))}",
            "paper_use": "show that guidance covers both risk window and completion endpoint",
        },
        {
            "partition_id": "P5_candidate_handoff",
            "time_window_s": "case-level",
            "fastfluent_screening_role": "accept a stable reduced-order candidate after rejecting fitted but unstable points",
            "fluent_validation_target": "targeted Fluent case using accepted candidate assumptions",
            "priority": "high for future high-fidelity case selection",
            "existing_fluent_confirmation": f"accepted {summary.get('accepted_candidate_id')} with full-melt error {_fmt(summary.get('accepted_full_melt_error_pct'))}% and risk-time error {_fmt(summary.get('accepted_risk_time_error_pct'))}%",
            "paper_use": "demonstrate Agent decision-making before targeted Fluent validation",
        },
    ]


def _fluent_validation_target_rows(sources: dict[str, Any], summary: dict[str, Any]) -> list[dict[str, Any]]:
    edits = _edit_text(summary.get("accepted_candidate_edits", []))
    return [
        {
            "target_id": "F1_early_shock_sampling",
            "time_window_s": "0-4.1",
            "spatial_block": "steam inlet, jet path, shell inner surface",
            "why_fastfluent_selects_it": "short thermal-impact window is separated from the full-cycle melt problem",
            "recommended_fluent_action": "dense transient sampling of temperature, velocity, heat flux, pressure and surface dose",
            "existing_confirmation": "early-steam-shock packages 21-31 and 34-36 already cover this family",
            "status": "retrospectively_confirmed",
        },
        {
            "target_id": "F2_risk_window_refinement",
            "time_window_s": "80-130 centered near 100.7",
            "spatial_block": "pressure-retention and shell-stress monitoring regions",
            "why_fastfluent_selects_it": "native risk-window timing and pressure-risk proxy point to this interval",
            "recommended_fluent_action": "use tighter reporting and monitor outputs around the risk peak",
            "existing_confirmation": f"completed bridge pack reports peak pressure at {_fmt(summary.get('dominant_risk_time_s'))} s",
            "status": "retrospectively_confirmed",
        },
        {
            "target_id": "F3_melt_front_and_drainage",
            "time_window_s": "120-420",
            "spatial_block": "wax melt front, drainage paths, outlet region",
            "why_fastfluent_selects_it": "FastFluent tracks melt-front depth and drainage accessibility",
            "recommended_fluent_action": "monitor liquid fraction, outlet discharge, release ratio, trapped wax fraction",
            "existing_confirmation": "full-cycle W6 bridge confirms late drainage relief",
            "status": "retrospectively_confirmed",
        },
        {
            "target_id": "F4_completion_endpoint",
            "time_window_s": "390-420",
            "spatial_block": "whole wax domain and final residual pockets",
            "why_fastfluent_selects_it": "full-melt timing is a stable native QoI",
            "recommended_fluent_action": "verify first LF>=0.995 crossing and final residual wax pockets",
            "existing_confirmation": f"completed Fluent full melt at {_fmt(summary.get('full_melt_time_s'))} s",
            "status": "retrospectively_confirmed",
        },
        {
            "target_id": "F5_parameter_steam_temperature",
            "time_window_s": "full-cycle with early emphasis",
            "spatial_block": "steam boundary and shell inner surface",
            "why_fastfluent_selects_it": f"top full-melt sensitivity: {summary.get('top_full_melt_parameter')}",
            "recommended_fluent_action": "prioritize steam-temperature variants before broad parameter sweeps",
            "existing_confirmation": "not a new Fluent run in this pack; use as future targeted case recommendation",
            "status": "future_target",
        },
        {
            "target_id": "F6_parameter_initial_temperature",
            "time_window_s": "risk-window emphasis",
            "spatial_block": "wax/shell initial thermal state",
            "why_fastfluent_selects_it": f"top risk-window sensitivity: {summary.get('top_risk_time_parameter')}",
            "recommended_fluent_action": "prioritize initial-state variants for risk-window timing validation",
            "existing_confirmation": "not a new Fluent run in this pack; use as future targeted case recommendation",
            "status": "future_target",
        },
        {
            "target_id": "F7_accepted_candidate",
            "time_window_s": "0-420",
            "spatial_block": "accepted reduced-order candidate setup",
            "why_fastfluent_selects_it": f"{summary.get('accepted_candidate_id')} passed stability review after 5 fitted candidates were rejected",
            "recommended_fluent_action": f"use accepted candidate assumptions as one targeted Fluent validation case: {edits}",
            "existing_confirmation": "retrospective comparison shows close risk-time alignment with completed Fluent pack",
            "status": "future_target_with_retrospective_support",
        },
    ]


def _parameter_priority_rows(sources: dict[str, Any]) -> list[dict[str, Any]]:
    sensitivity = sources["payloads"].get("sensitivity", {})
    rows = sensitivity.get("rows", []) if isinstance(sensitivity.get("rows"), list) else []
    best_by_parameter: dict[str, dict[str, Any]] = {}
    for row in rows:
        parameter = str(row.get("parameter_group") or "")
        if not parameter:
            continue
        current = best_by_parameter.get(parameter)
        if current is None or _float_or(row.get("relative_sensitivity"), -1.0) > _float_or(current.get("relative_sensitivity"), -1.0):
            best_by_parameter[parameter] = row
    sorted_rows = sorted(best_by_parameter.values(), key=lambda row: _float_or(row.get("relative_sensitivity"), 0.0), reverse=True)
    output: list[dict[str, Any]] = []
    for index, row in enumerate(sorted_rows, start=1):
        metric = row.get("metric")
        output.append(
            {
                "rank": index,
                "parameter_group": row.get("parameter_group"),
                "primary_sensitive_metric": _metric_label(metric),
                "relative_sensitivity": _round(row.get("relative_sensitivity"), 6),
                "low_variant": row.get("low_variant"),
                "high_variant": row.get("high_variant"),
                "fastfluent_guidance": _parameter_guidance(row.get("parameter_group"), metric),
                "fluent_case_priority": "high" if index <= 3 else "medium",
            }
        )
    return output


def _asset_reuse_rows(sources: dict[str, Any]) -> list[dict[str, Any]]:
    paths = sources.get("paths", {})
    return [
        {
            "asset_group": "FastFluent native study",
            "source": paths.get("study_guidance"),
            "reuse_role": "parameter sensitivity and first-pass process screening",
            "paper_section": "Methods: FastFluent screening; Results: parameter priorities",
        },
        {
            "asset_group": "FastFluent validation pack",
            "source": paths.get("validation_pack"),
            "reuse_role": "grid/time-step checked native evidence",
            "paper_section": "Methods: stability gate; Results: stable QoIs",
        },
        {
            "asset_group": "FastFluent Agent iteration",
            "source": paths.get("iteration_pack"),
            "reuse_role": "multi-round candidate search and accepted candidate handoff",
            "paper_section": "Results: Agent-guided case selection",
        },
        {
            "asset_group": "Completed Fluent bridge pack",
            "source": paths.get("fluent_bridge_pack"),
            "reuse_role": "retrospective confirmation of FastFluent-selected windows and QoIs",
            "paper_section": "Results: targeted Fluent confirmation",
        },
        {
            "asset_group": "Early-steam-shock nature-style assets",
            "source": "D:/CYK2/Fluent/10_Results/21-31 and 34-36 earlySteamShock packages",
            "reuse_role": "existing Fluent evidence for early 0-4.1 s thermal-impact partition",
            "paper_section": "Results: early shock partition and validation",
        },
    ]


def _guidance_claims(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "fastfluent_to_fluent_dewaxing_guidance_claims_v1",
        "supported_claims": [
            "FastFluent partitions the dewaxing process into early shock, risk-window, melt/drainage, completion, and candidate-handoff blocks before targeted Fluent validation.",
            f"The Agent iteration campaign executed {summary.get('iteration_solver_runs')} native runs and {summary.get('iteration_cell_time_steps')} native cell-time steps to prioritize Fluent validation targets.",
            f"The completed Fluent bridge retrospectively confirms the main FastFluent-selected windows: early 0-4.1 s screening, risk window near {summary.get('dominant_risk_time_s')} s, and full melt near {summary.get('full_melt_time_s')} s.",
            f"The accepted FastFluent candidate `{summary.get('accepted_candidate_id')}` provides a stable reduced-order case for future targeted Fluent validation.",
        ],
        "application_limits": [
            "Do not present FastFluent as a replacement for final Fluent validation.",
            "Do not present completed Fluent packs as the reason FastFluent chose the partitions; use them as retrospective confirmation.",
            "Do not convert pressure-risk or shell-stress proxies into calibrated crack probability.",
            "Do not treat accepted reduced-order parameter edits as measured geometry or material changes without independent evidence.",
        ],
    }


def _paper_outline_markdown(summary: dict[str, Any], *, manuscript_title: str) -> str:
    return "\n".join(
        [
            f"# Paper Outline: {manuscript_title}",
            "",
            "## 1. Introduction",
            "",
            "Direct full-domain Fluent exploration of dewaxing is expensive because the process mixes short early steam shock, longer wax melting, drainage relief, and shell-risk windows. The paper should frame FastFluent as a process-partitioning and guidance layer that decides where high-fidelity Fluent validation should focus.",
            "",
            "## 2. Methods",
            "",
            "- Build FastFluent-native reduced-order dewaxing screening.",
            "- Partition the process into time windows and physics blocks.",
            "- Use Agent iteration to prioritize candidate assumptions and reject unstable fits.",
            "- Use completed Fluent packages as retrospective high-fidelity confirmation of the guidance.",
            "",
            "## 3. Results",
            "",
            f"- FastFluent identified the early shock block, risk window near {_fmt(summary.get('dominant_risk_time_s'))} s, melt/drainage block, full-melt endpoint near {_fmt(summary.get('full_melt_time_s'))} s, and accepted candidate `{summary.get('accepted_candidate_id')}`.",
            "- Fluent-facing tables specify target windows, spatial blocks, monitored QoIs, and parameter priorities.",
            "- Existing Fluent assets confirm that the selected windows correspond to real high-fidelity events.",
            "",
            "## 4. Discussion",
            "",
            "The key contribution is not replacing Fluent, but making Fluent use more directed: fewer blind sweeps, clearer monitor design, and explicit handoff from reduced-order evidence to high-fidelity validation.",
            "",
            "## 5. Limitations",
            "",
            "FastFluent outputs are screening and guidance evidence. Final CFD claims remain tied to Fluent or experiments.",
            "",
        ]
    )


def _methods_section_markdown(summary: dict[str, Any], *, manuscript_title: str) -> str:
    edits = _edit_text(summary.get("accepted_candidate_edits", []))
    return "\n".join(
        [
            f"# Methods Guidance Section Draft: {manuscript_title}",
            "",
            "The dewaxing workflow was organized as a FastFluent-guided, Fluent-validated process rather than a blind high-fidelity sweep. FastFluent first decomposed the process into early steam shock, dominant pressure-risk, melt/drainage, full-melt completion, and candidate-handoff blocks. Each block produced Fluent-facing recommendations for time-window resolution, spatial monitoring, and QoI selection.",
            "",
            f"The native study and Agent iteration provided the computational guidance layer. The Agent iteration evaluated {summary.get('iteration_candidate_count')} candidates, executed {summary.get('iteration_solver_runs')} native solver runs, and accepted `{summary.get('accepted_candidate_id')}` after stability review. The accepted candidate edits were: {edits}.",
            "",
            "Completed Fluent result packs were then used as retrospective confirmation that the FastFluent-selected windows and monitoring quantities corresponded to high-fidelity events. No new Fluent calculation was launched by this compiler.",
            "",
        ]
    )


def _results_section_markdown(
    summary: dict[str, Any],
    process_rows: list[dict[str, Any]],
    target_rows: list[dict[str, Any]],
    parameter_rows: list[dict[str, Any]],
    *,
    manuscript_title: str,
) -> str:
    top_parameters = ", ".join(str(row.get("parameter_group")) for row in parameter_rows[:3])
    return "\n".join(
        [
            f"# Results Guidance Section Draft: {manuscript_title}",
            "",
            f"FastFluent partitioned the dewaxing process into {len(process_rows)} Fluent-facing blocks. The most important high-fidelity validation windows were the early 0-4.1 s steam-shock stage, the dominant full-cycle risk window near {_fmt(summary.get('dominant_risk_time_s'))} s, the melt/drainage interval from 120-420 s, and the full-melt completion interval near {_fmt(summary.get('full_melt_time_s'))} s.",
            "",
            f"The completed Fluent bridge retrospectively confirmed these windows: early shock remained a screening stage with crack-driving index {_fmt(summary.get('early_max_crack_index'))}, while the full-cycle Fluent pack showed peak effective pressure {_fmt(summary.get('peak_effective_pressure_mpa'))} MPa and wall VM P99.5 {_fmt(summary.get('peak_wall_vm_p995_mpa'))} MPa near {_fmt(summary.get('dominant_risk_time_s'))} s. The first full-melt time was {_fmt(summary.get('full_melt_time_s'))} s and the late pressure/stress relief was {_fmt(summary.get('stress_drop_fraction_pct'))}%.",
            "",
            f"The Agent iteration converted this partitioning into a candidate handoff. It ran {summary.get('iteration_solver_runs')} native cases, rejected {summary.get('iteration_rejected_candidate_count')} fitted candidates during stability review, and accepted `{summary.get('accepted_candidate_id')}`. This accepted candidate improved the combined native objective by {_fmt(summary.get('objective_improvement_vs_baseline_pct'))}% relative to baseline and {_fmt(summary.get('objective_improvement_vs_shell_thin_pct'))}% relative to `shell_thin`.",
            "",
            f"FastFluent parameter screening indicates that the first Fluent parameter-validation set should prioritize {top_parameters}. These are not broad exploratory sweeps; they are reduced-order priorities for targeted high-fidelity validation.",
            "",
            f"The guidance pack therefore defines {len(target_rows)} Fluent validation targets and {len(parameter_rows)} parameter-priority rows for a paper-facing FastFluent-to-Fluent workflow.",
            "",
        ]
    )


def _fluent_handoff_markdown(summary: dict[str, Any], target_rows: list[dict[str, Any]], parameter_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Fluent Handoff Brief",
        "",
        "This brief states what FastFluent would ask Fluent to validate.",
        "",
        "## Target Windows",
        "",
    ]
    for row in target_rows:
        lines.append(f"- `{row['target_id']}` ({row['time_window_s']}): {row['recommended_fluent_action']}")
    lines.extend(["", "## Parameter Priorities", ""])
    for row in parameter_rows[:5]:
        lines.append(f"- Rank {row['rank']}: `{row['parameter_group']}` for {row['primary_sensitive_metric']} ({row['fluent_case_priority']} priority).")
    lines.extend(
        [
            "",
            "## Accepted Candidate",
            "",
            f"- Candidate: `{summary.get('accepted_candidate_id')}`",
            f"- Edits: {_edit_text(summary.get('accepted_candidate_edits', []))}",
            f"- Native full-melt error: {_fmt(summary.get('accepted_full_melt_error_pct'))}%",
            f"- Native risk-time error: {_fmt(summary.get('accepted_risk_time_error_pct'))}%",
            "",
            "## Execution Boundary",
            "",
            "- This handoff brief did not launch Fluent.",
            "- This handoff brief did not rerun the FastFluent-native solver.",
            "- It compiles existing evidence into Fluent-facing instructions.",
            "",
        ]
    )
    return "\n".join(lines)


def _guidance_report_markdown(summary: dict[str, Any], tables: list[dict[str, Any]], *, manuscript_title: str) -> str:
    lines = [
        f"# FastFluent-to-Fluent Guidance Report: {manuscript_title}",
        "",
        f"- Accepted FastFluent candidate: `{summary.get('accepted_candidate_id')}`",
        f"- Native iteration runs: `{summary.get('iteration_solver_runs')}`",
        f"- Native iteration cell-time steps: `{summary.get('iteration_cell_time_steps')}`",
        f"- Fluent risk window confirmed near: `{summary.get('dominant_risk_time_s')} s`",
        f"- Fluent full-melt endpoint confirmed near: `{summary.get('full_melt_time_s')} s`",
        "",
        "## Tables",
        "",
    ]
    for table in tables:
        lines.append(f"- `{table['table_id']}`: {table['title']}")
    lines.extend(
        [
            "",
            "## Figure",
            "",
            "- `figure_01_fastfluent_guided_fluent_workflow`: FastFluent-guided Fluent dewaxing workflow.",
        ]
    )
    lines.extend(["", "## Guidance Logic", ""])
    lines.append("FastFluent is the guidance layer: it partitions, ranks, and selects targets. Completed Fluent packs are the retrospective validation layer.")
    lines.extend(["", "## Limits", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _workflow_figure_notes_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Workflow Figure Notes",
            "",
            "This figure is intended to lock the direction of the dewaxing workflow before later paper polishing.",
            "",
            "## Direction Check",
            "",
            "- Solid arrows show the intended guidance direction: FastFluent computes, partitions, ranks, and hands targets to Fluent.",
            "- The existing Fluent bridge appears only as a retrospective confirmation layer.",
            "- The figure should not be read as completed Fluent results selecting the FastFluent partitions.",
            "",
            "## Main Evidence Blocks",
            "",
            f"- FastFluent native study: `{summary.get('study_solver_runs')}` runs.",
            f"- FastFluent validation pack: `{summary.get('validation_solver_runs')}` cases and `{summary.get('validation_cell_time_steps')}` cell-time steps.",
            f"- Agent iteration: `{summary.get('iteration_solver_runs')}` native runs and `{summary.get('iteration_cell_time_steps')}` cell-time steps.",
            f"- Accepted handoff candidate: `{summary.get('accepted_candidate_id')}`.",
            "",
            "## Fluent Confirmation Values",
            "",
            f"- Early shock window: `{summary.get('early_stage_window_s')}`.",
            f"- Dominant risk window: `{summary.get('dominant_risk_time_s')} s`.",
            f"- Full-melt endpoint: `{summary.get('full_melt_time_s')} s`.",
            f"- Peak effective pressure: `{summary.get('peak_effective_pressure_mpa')} MPa`.",
            f"- Wall VM P99.5: `{summary.get('peak_wall_vm_p995_mpa')} MPa`.",
            "",
        ]
    )


def _workflow_figure_svg(
    summary: dict[str, Any],
    process_rows: list[dict[str, Any]],
    target_rows: list[dict[str, Any]],
    parameter_rows: list[dict[str, Any]],
) -> str:
    width = 1520
    height = 860
    parts = [
        _svg_header(width, height),
        '<text x="50" y="42" class="title">FastFluent-guided Fluent dewaxing workflow</text>',
        '<text x="50" y="67" class="subtitle">Solid arrows: FastFluent guidance direction. Dashed confirmation lane: existing Fluent results are used only for retrospective confirmation.</text>',
    ]

    main_y = 105
    box_h = 166
    main_boxes = [
        (
            50,
            230,
            "Dewaxing CFD objective",
            [
                "Early steam shock plus full-cycle wax melting",
                "Question: where should expensive Fluent evidence focus?",
                "Boundary: no new Fluent run in this pack",
            ],
            "box",
        ),
        (
            328,
            290,
            "FastFluent computation layer",
            [
                f"Native study: {summary.get('study_solver_runs')} runs",
                f"Validation: {summary.get('validation_solver_runs')} cases / {_million(summary.get('validation_cell_time_steps'))}M cell-steps",
                f"Agent iteration: {summary.get('iteration_solver_runs')} runs / {_million(summary.get('iteration_cell_time_steps'))}M cell-steps",
            ],
            "box-blue",
        ),
        (
            666,
            278,
            "Guidance synthesis",
            [
                f"{len(process_rows)} process partitions P1-P5",
                f"Top parameters: {_top_parameter_text(parameter_rows)}",
                f"Accepted handoff: {summary.get('accepted_candidate_id')}",
            ],
            "box-blue-strong",
        ),
        (
            990,
            236,
            "Fluent-facing plan",
            [
                f"{len(target_rows)} validation targets F1-F7",
                "Time windows, spatial blocks, monitors",
                "Targeted cases before broad sweeps",
            ],
            "box",
        ),
        (
            1274,
            196,
            "Paper evidence",
            [
                "Workflow figure plus four tables",
                "Methods and results structure",
                "Claim boundaries kept explicit",
            ],
            "box-pink",
        ),
    ]
    for index, (x, w, title, lines, css_class) in enumerate(main_boxes):
        _svg_box(parts, x, main_y, w, box_h, title, lines, css_class)
        if index + 1 < len(main_boxes):
            x2 = main_boxes[index + 1][0] - 18
            _svg_arrow(parts, x + w + 8, main_y + box_h / 2, x2, main_y + box_h / 2)

    parts.append('<text x="50" y="318" class="section">Process partition layer from FastFluent</text>')
    partition_nodes = _partition_nodes(summary)
    part_y = 342
    part_w = 270
    part_gap = 18
    for index, (title, subtitle, note, css_class) in enumerate(partition_nodes):
        x = 50 + index * (part_w + part_gap)
        _svg_box(parts, x, part_y, part_w, 112, title, [subtitle, note], css_class)
        if index + 1 < len(partition_nodes):
            _svg_arrow(parts, x + part_w + 4, part_y + 56, x + part_w + part_gap - 6, part_y + 56)

    parts.append('<text x="50" y="500" class="section">Fluent validation targets selected by the guidance layer</text>')
    target_y = 525
    target_boxes = [
        (
            50,
            450,
            "Retrospectively confirmed targets F1-F4",
            [
                "F1 early sampling: 0-4.1 s",
                f"F2 risk refinement: 80-130 s centered near {_fmt(summary.get('dominant_risk_time_s'))} s",
                "F3 melt/drainage: 120-420 s",
                f"F4 completion endpoint: {_fmt(summary.get('full_melt_time_s'))} s",
            ],
            "box-blue",
        ),
        (
            535,
            420,
            "Future parameter targets F5-F6",
            [
                f"Full-melt timing: {summary.get('top_full_melt_parameter')}",
                f"Risk-window timing: {summary.get('top_risk_time_parameter')}",
                f"Shell-stress proxy: {summary.get('top_shell_stress_parameter')}",
                "Use targeted cases, not blind sweeps",
            ],
            "box",
        ),
        (
            990,
            480,
            "Accepted candidate target F7",
            [
                f"Candidate: {summary.get('accepted_candidate_id')}",
                f"Edits: {_edit_text(summary.get('accepted_candidate_edits', []))}",
                f"Risk-time error: {_fmt(summary.get('accepted_risk_time_error_pct'))}%; full-melt error: {_fmt(summary.get('accepted_full_melt_error_pct'))}%",
                "Stable reduced-order handoff for later Fluent validation",
            ],
            "box-blue-strong",
        ),
    ]
    for x, w, title, lines, css_class in target_boxes:
        _svg_box(parts, x, target_y, w, 150, title, lines, css_class)

    _svg_arrow(parts, 805, main_y + box_h + 8, 805, part_y - 12)
    _svg_arrow(parts, 805, part_y + 122, 805, target_y - 14)

    confirm_y = 725
    parts.append(f'<rect x="50" y="{confirm_y}" width="1420" height="92" rx="4" class="confirmation"/>')
    parts.append(f'<text x="72" y="{confirm_y + 28}" class="label">Existing Fluent bridge: retrospective confirmation layer, not the partition-selection source</text>')
    parts.append(
        f'<text x="72" y="{confirm_y + 56}" class="small">Confirms early {summary.get("early_stage_window_s")}; risk near {_fmt(summary.get("dominant_risk_time_s"))} s; full melt near {_fmt(summary.get("full_melt_time_s"))} s; peak pressure {_fmt(summary.get("peak_effective_pressure_mpa"))} MPa; wall VM P99.5 {_fmt(summary.get("peak_wall_vm_p995_mpa"))} MPa.</text>'
    )
    parts.append(
        f'<text x="72" y="{confirm_y + 78}" class="micro">This lane supports the paper narrative after FastFluent has already defined windows, monitors, and target cases.</text>'
    )
    _svg_arrow(parts, 1230, target_y + 150 + 10, 1230, confirm_y - 12, dashed=True)

    parts.append(_svg_footer())
    return "\n".join(parts)


def _partition_nodes(summary: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    return [
        ("P1 Early shock", "0-4.1 s", "inlet, jet path, shell dose", "box"),
        ("P2 Risk window", f"near {_fmt(summary.get('dominant_risk_time_s'))} s", "pressure plus wall VM monitors", "box-blue-strong"),
        ("P3 Melt/drainage", "120-420 s", "liquid fraction and outlet discharge", "box"),
        ("P4 Completion", f"near {_fmt(summary.get('full_melt_time_s'))} s", "full-melt threshold and residual wax", "box"),
        ("P5 Handoff case", "case level", str(summary.get("accepted_candidate_id")), "box-pink"),
    ]


def _svg_box(parts: list[str], x: float, y: float, w: float, h: float, title: str, lines: list[str], css_class: str) -> None:
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" class="{css_class}"/>')
    parts.append(f'<text x="{x + 16}" y="{y + 29}" class="label">{_esc(title)}</text>')
    current_y = y + 55
    for line in lines:
        wrapped = _wrap_words(str(line), max(22, int((w - 30) / 6.2)))
        for item in wrapped[:2]:
            parts.append(f'<text x="{x + 16}" y="{current_y}" class="small">{_esc(item)}</text>')
            current_y += 19
        if len(wrapped) > 2:
            parts.append(f'<text x="{x + 16}" y="{current_y}" class="small">{_esc(wrapped[2])}</text>')
            current_y += 19


def _svg_arrow(parts: list[str], x1: float, y1: float, x2: float, y2: float, *, dashed: bool = False) -> None:
    cls = "arrow dashed" if dashed else "arrow"
    parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}"/>')
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 >= x1 else -1
        points = f"{x2:.1f},{y2:.1f} {x2 - 10 * direction:.1f},{y2 - 5:.1f} {x2 - 10 * direction:.1f},{y2 + 5:.1f}"
    else:
        direction = 1 if y2 >= y1 else -1
        points = f"{x2:.1f},{y2:.1f} {x2 - 5:.1f},{y2 - 10 * direction:.1f} {x2 + 5:.1f},{y2 - 10 * direction:.1f}"
    parts.append(f'<polygon points="{points}" class="arrowhead"/>')


def _svg_header(width: int, height: int) -> str:
    c = NATURE_SOFT_PALETTE
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<style>",
            f"svg{{background:{c['paper']}}}",
            f"text{{font-family:Arial,Helvetica,sans-serif;fill:{c['ink']};letter-spacing:0}}",
            ".title{font-size:21px;font-weight:700}",
            f".subtitle{{font-size:12px;fill:{c['muted']}}}",
            ".section{font-size:13px;font-weight:700}",
            ".label{font-size:12.5px;font-weight:700}",
            f".small{{font-size:11.2px;fill:{c['muted']}}}",
            f".micro{{font-size:10.5px;fill:{c['muted']}}}",
            f".box{{fill:{c['rice']};stroke:{c['grid']};stroke-width:0.95}}",
            f".box-blue{{fill:{c['blue_very_light']};stroke:{c['blue_ink']};stroke-width:1.0}}",
            f".box-blue-strong{{fill:{c['blue_light']};stroke:{c['blue_ink']};stroke-width:1.15}}",
            f".box-pink{{fill:{c['sakura']};stroke:{c['sakura_deep']};stroke-width:1.0}}",
            f".confirmation{{fill:{c['paper']};stroke:{c['sakura_deep']};stroke-width:1.0;stroke-dasharray:6 5}}",
            f".arrow{{stroke:{c['muted']};stroke-width:1.2;fill:none}}",
            ".dashed{stroke-dasharray:6 5}",
            f".arrowhead{{fill:{c['muted']}}}",
            "</style>",
        ]
    )


def _svg_footer() -> str:
    return "</svg>"


def _wrap_words(text: str, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=False)


def _million(value: Any) -> str:
    parsed = _maybe_float(value)
    if parsed is None or not math.isfinite(parsed):
        return "NA"
    return f"{parsed / 1_000_000:.1f}"


def _top_parameter_text(parameter_rows: list[dict[str, Any]]) -> str:
    names = [str(row.get("parameter_group")) for row in parameter_rows[:3] if row.get("parameter_group")]
    return ", ".join(names) if names else "not available"


def _table(table_id: str, title: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    fieldnames = list(rows[0].keys()) if rows else ["item", "value"]
    return {"table_id": table_id, "title": title, "fieldnames": fieldnames, "rows": rows}


def _markdown_table(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(fieldnames) + " |"
    divider = "| " + " | ".join("---" for _ in fieldnames) + " |"
    body = ["| " + " | ".join(_cell(row.get(field)) for field in fieldnames) + " |" for row in rows]
    if not body:
        body = ["| " + " | ".join("" for _ in fieldnames) + " |"]
    return "\n".join([header, divider] + body) + "\n"


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|")


def _accepted_candidate(iteration: dict[str, Any]) -> dict[str, Any]:
    decision = iteration.get("agent_decision", {}) if isinstance(iteration.get("agent_decision"), dict) else {}
    accepted = decision.get("accepted_candidate", {}) if isinstance(decision.get("accepted_candidate"), dict) else {}
    accepted_id = accepted.get("candidate_id")
    for candidate in iteration.get("candidates", []) if isinstance(iteration.get("candidates"), list) else []:
        if candidate.get("candidate_id") == accepted_id:
            return candidate
    return accepted


def _top_parameter(top_metrics: dict[str, Any], metric: str) -> str | None:
    rows = top_metrics.get(metric, []) if isinstance(top_metrics.get(metric), list) else []
    if not rows:
        return None
    return rows[0].get("parameter_group")


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _parameter_guidance(parameter: Any, metric: Any) -> str:
    parameter_text = str(parameter or "")
    metric_text = _metric_label(metric)
    if parameter_text == "steam_boundary_temperature_K":
        return f"prioritize steam temperature variants because they strongly affect {metric_text}"
    if parameter_text == "initial_temperature_K":
        return f"prioritize initial thermal-state variants because they strongly affect {metric_text}"
    if parameter_text == "thickness_m":
        return f"validate thermal-path thickness as a full-cycle melt/risk control for {metric_text}"
    if parameter_text == "latent_heat_J_kg":
        return f"use latent heat as a phase-change uncertainty case for {metric_text}"
    if parameter_text == "wax_thermal_conductivity":
        return f"use wax conductivity to bracket melt-front and pressure-risk uncertainty for {metric_text}"
    if parameter_text == "shell_thickness_m":
        return f"treat shell thickness as effective thermal resistance before any physical geometry claim for {metric_text}"
    if parameter_text == "heat_transfer_coefficient_W_m2K":
        return f"use heat-transfer coefficient to bracket wall heat input for {metric_text}"
    return f"use as a targeted Fluent parameter for {metric_text}"


def _metric_label(metric: Any) -> str:
    labels = {
        "predicted_full_melt_time_s": "full-melt timing",
        "dominant_risk_time_s": "risk-window timing",
        "early_max_shell_stress_proxy_MPa": "shell-stress proxy",
        "peak_pressure_risk_proxy": "pressure-risk proxy",
        "energy_balance_relative_error": "energy balance",
    }
    text = str(metric or "")
    return labels.get(text, text.replace("_", " "))


def _edit_text(edits: Any) -> str:
    if not isinstance(edits, list) or not edits:
        return "no parameter edits recorded"
    pieces = []
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        pieces.append(f"{edit.get('path')} {edit.get('operation')} {edit.get('value')}")
    return "; ".join(pieces) if pieces else "no parameter edits recorded"


def _round(value: Any, digits: int) -> float | None:
    parsed = _maybe_float(value)
    if parsed is None or not math.isfinite(parsed):
        return None
    return round(parsed, digits)


def _pct(value: Any, digits: int) -> float | None:
    parsed = _maybe_float(value)
    if parsed is None or not math.isfinite(parsed):
        return None
    return round(100.0 * parsed, digits)


def _fmt(value: Any) -> str:
    parsed = _maybe_float(value)
    if parsed is None or not math.isfinite(parsed):
        return str(value)
    if abs(parsed) >= 100:
        return f"{parsed:.2f}"
    if abs(parsed) >= 10:
        return f"{parsed:.3f}"
    if abs(parsed) >= 1:
        return f"{parsed:.3f}"
    return f"{parsed:.4f}"


def _maybe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_or(value: Any, fallback: float = 0.0) -> float:
    parsed = _maybe_float(value)
    return fallback if parsed is None else parsed
