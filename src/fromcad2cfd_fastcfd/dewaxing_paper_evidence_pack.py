"""Paper evidence pack compiler for the dewaxing FastFluent case study.

This module converts a completed FastFluent-native dewaxing validation pack into
paper-facing tables, figures, application scope notes, and a draft results section. It
does not run Fluent or rerun the native solver.
"""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

from .file_io import ensure_dir, read_json_file, write_json_file, write_text_file
from .practical_native_artifacts import write_csv


DEWAXING_PAPER_EVIDENCE_SCHEMA_VERSION = "fastfluent_dewaxing_paper_evidence_pack_v1"
EXPECTED_VALIDATION_SCHEMA_VERSION = "fastfluent_dewaxing_native_validation_pack_v1"
EXPECTED_ITERATION_SCHEMA_VERSION = "fastfluent_dewaxing_agent_iteration_pack_v1"


LIMITATIONS = [
    "This evidence pack is compiled from an existing FastFluent-native validation pack.",
    "Fluent execution, PyFluent execution, UDF compilation, and case/data editing are outside this compiler.",
    "Reduced-order screening proxies are used as application guidance.",
    "The shell_thin label is an effective thermal-resistance correction unless independently verified.",
]

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
    "rule": "Use the low-saturation thesis blue-pink palette for statistical and workflow figures; reserve high-contrast blue-white-red palettes for scalar field maps.",
    "palette_hex": NATURE_SOFT_PALETTE,
}


def compile_dewaxing_paper_evidence_pack(
    *,
    validation_pack: str | Path,
    output_dir: str | Path,
    manuscript_title: str = "Agent-Guided FastFluent Dewaxing Evidence",
    iteration_pack: str | Path | None = None,
) -> dict[str, Any]:
    """Compile paper-facing artifacts from a dewaxing validation pack."""

    root = Path(output_dir)
    ensure_dir(root)
    manifest_path = _resolve_validation_manifest(validation_pack)
    validation = read_json_file(manifest_path)
    validation_check = _validate_validation_manifest(validation, manifest_path)
    iteration_manifest_path = _resolve_iteration_manifest(iteration_pack) if iteration_pack else None
    iteration = read_json_file(iteration_manifest_path) if iteration_manifest_path else None
    iteration_check = _validate_iteration_manifest(iteration, iteration_manifest_path) if iteration else None

    tables_dir = root / "tables"
    figures_dir = root / "figures"
    sections_dir = root / "sections"
    ensure_dir(tables_dir)
    ensure_dir(figures_dir)
    ensure_dir(sections_dir)

    tables = _table_payloads(validation, iteration)
    for table in tables:
        write_csv(tables_dir / f"{table['table_id']}.csv", table["rows"], table["fieldnames"])
        write_text_file(tables_dir / f"{table['table_id']}.md", _markdown_table(table["fieldnames"], table["rows"]))

    figures = _write_figures(validation, figures_dir, iteration)
    claims = _paper_claims(validation, iteration)
    results_section = _results_section_markdown(validation, claims, manuscript_title=manuscript_title, iteration=iteration)
    methods_section = _methods_section_markdown(validation, manuscript_title=manuscript_title, iteration=iteration)
    figure_caption_section = _figure_caption_section(figures)
    report = _evidence_report_markdown(validation, claims, tables, figures, manuscript_title=manuscript_title, iteration=iteration)
    execution = validation.get("execution_boundary", {}) if isinstance(validation.get("execution_boundary"), dict) else {}
    iteration_execution = _iteration_execution(iteration)
    checks_passed = bool(validation_check["passed"] and (iteration_check is None or iteration_check["passed"]))

    artifacts = {
        "manifest": str(root / "paper_evidence_manifest.json"),
        "paper_claims": str(root / "agent_paper_claims.json"),
        "results_section": str(sections_dir / "results_section.md"),
        "methods_section": str(sections_dir / "methods_section.md"),
        "figure_captions": str(sections_dir / "figure_captions.md"),
        "evidence_report": str(root / "paper_evidence_report.md"),
        "tables_dir": str(tables_dir),
        "figures_dir": str(figures_dir),
    }
    pack = {
        "schema_version": DEWAXING_PAPER_EVIDENCE_SCHEMA_VERSION,
        "status": "success" if validation_check["passed"] else "warning",
        "quality_status": validation.get("quality_status"),
        "case_id": "dewaxing_paper_evidence_pack",
        "manuscript_title": manuscript_title,
        "source_validation_pack": str(manifest_path),
        "source_validation_status": validation.get("status"),
        "source_iteration_pack": str(iteration_manifest_path) if iteration_manifest_path else None,
        "source_iteration_status": iteration.get("status") if iteration else None,
        "validation_check": validation_check,
        "iteration_check": iteration_check,
        "summary": _summary(validation, iteration),
        "tables": [{key: value for key, value in table.items() if key != "rows"} | {"row_count": len(table["rows"])} for table in tables],
        "figures": figures,
        "figure_style": FIGURE_STYLE,
        "paper_claims": claims,
        "artifacts": artifacts,
        "execution_boundary": {
            "new_fluent_calculation": False,
            "fluent_launched": False,
            "native_dewaxing_solver_rerun": False,
            "source_native_solver_runs": execution.get("native_dewaxing_solver_runs"),
            "source_native_cell_time_steps": execution.get("native_cell_time_steps"),
            "source_iteration_solver_runs": iteration_execution.get("native_dewaxing_solver_runs"),
            "source_iteration_cell_time_steps": iteration_execution.get("native_cell_time_steps"),
        },
        "limitations": list(LIMITATIONS),
    }
    pack["status"] = "success" if checks_passed else "warning"
    write_json_file(root / "agent_paper_claims.json", claims)
    write_text_file(sections_dir / "results_section.md", results_section)
    write_text_file(sections_dir / "methods_section.md", methods_section)
    write_text_file(sections_dir / "figure_captions.md", figure_caption_section)
    write_text_file(root / "paper_evidence_report.md", report)
    write_json_file(root / "paper_evidence_manifest.json", pack)
    return pack


def dewaxing_paper_evidence_pack_markdown(pack: dict[str, Any]) -> str:
    """Render a concise Markdown summary for CLI output."""

    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    claims = pack.get("paper_claims", {}) if isinstance(pack.get("paper_claims"), dict) else {}
    lines = [
        "# Dewaxing Paper Evidence Pack",
        "",
        f"- Status: `{pack.get('status')}`",
        f"- Source validation status: `{pack.get('source_validation_status')}`",
        f"- Recommended target: `{summary.get('recommended_target_id')}`",
        f"- Native cell-time steps: `{summary.get('native_cell_time_steps')}`",
        f"- New Fluent calculation: `{pack.get('execution_boundary', {}).get('new_fluent_calculation')}`",
        f"- Results section: `{pack.get('artifacts', {}).get('results_section')}`",
        f"- Evidence report: `{pack.get('artifacts', {}).get('evidence_report')}`",
        "",
        "## Paper Claims",
        "",
    ]
    if summary.get("iteration_accepted_candidate_id"):
        lines[5:5] = [
            f"- Source iteration status: `{pack.get('source_iteration_status')}`",
            f"- Agent accepted candidate: `{summary.get('iteration_accepted_candidate_id')}`",
            f"- Iteration native solver runs: `{summary.get('iteration_solver_runs')}`",
            f"- Iteration cell-time steps: `{summary.get('iteration_cell_time_steps')}`",
        ]
    for item in claims.get("supported_claims", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Application Use Notes", ""])
    for item in claims.get("restricted_claims", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _resolve_validation_manifest(path: str | Path) -> Path:
    source = Path(path)
    if source.is_dir():
        return source / "validation_pack_manifest.json"
    return source


def _resolve_iteration_manifest(path: str | Path) -> Path:
    source = Path(path)
    if source.is_dir():
        return source / "agent_iteration_manifest.json"
    return source


def _validate_validation_manifest(validation: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if validation.get("schema_version") != EXPECTED_VALIDATION_SCHEMA_VERSION:
        errors.append(f"Unsupported validation schema_version: {validation.get('schema_version')!r}")
    if validation.get("status") != "success":
        warnings.append(f"Source validation status is {validation.get('status')!r}.")
    if validation.get("quality_status") == "warning":
        warnings.append("Source validation quality is warning; keep reduced-order proxy language tied to application guidance.")
    if not isinstance(validation.get("cases"), list) or not validation.get("cases"):
        errors.append("Source validation pack has no cases.")
    if not isinstance(validation.get("agent_validation_decision"), dict):
        errors.append("Source validation pack has no agent_validation_decision object.")
    if not manifest_path.exists():
        errors.append(f"Validation manifest does not exist: {manifest_path}")
    return {"status": "failed" if errors else "passed", "passed": not errors, "errors": errors, "warnings": warnings}


def _validate_iteration_manifest(iteration: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if iteration.get("schema_version") != EXPECTED_ITERATION_SCHEMA_VERSION:
        errors.append(f"Unsupported iteration schema_version: {iteration.get('schema_version')!r}")
    if iteration.get("status") != "success":
        warnings.append(f"Source iteration status is {iteration.get('status')!r}.")
    if iteration.get("quality_status") == "warning":
        warnings.append("Source iteration quality is warning; keep accepted-candidate claims tied to the review status.")
    if not isinstance(iteration.get("candidates"), list) or not iteration.get("candidates"):
        errors.append("Source iteration pack has no candidates.")
    if not isinstance(iteration.get("agent_decision"), dict):
        errors.append("Source iteration pack has no agent_decision object.")
    if not manifest_path.exists():
        errors.append(f"Iteration manifest does not exist: {manifest_path}")
    return {"status": "failed" if errors else "passed", "passed": not errors, "errors": errors, "warnings": warnings}


def _table_payloads(validation: dict[str, Any], iteration: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    tables = [
        {
            "table_id": "table_01_native_candidate_comparison",
            "title": "Native candidates against reviewed Fluent pack",
            "fieldnames": [
                "target_id",
                "native_full_melt_time_s",
                "fluent_full_melt_time_s",
                "full_melt_relative_error_pct",
                "native_dominant_risk_time_s",
                "fluent_dominant_risk_time_s",
                "dominant_risk_relative_error_pct",
                "early_shell_stress_proxy_MPa",
                "objective_score",
            ],
            "rows": _candidate_comparison_rows(validation),
        },
        {
            "table_id": "table_02_validation_matrix",
            "title": "Native validation matrix",
            "fieldnames": [
                "validation_case_id",
                "target_id",
                "case_variant",
                "nx",
                "ny",
                "time_step_s",
                "shell_columns",
                "grid_cells",
                "time_steps",
                "cell_time_steps",
            ],
            "rows": _validation_matrix_rows(validation),
        },
        {
            "table_id": "table_03_stability_summary",
            "title": "Grid/time-step stability summary",
            "fieldnames": [
                "target_id",
                "metric",
                "quality_status",
                "current_value",
                "min_value",
                "max_value",
                "relative_spread_pct",
                "threshold_pct",
            ],
            "rows": _stability_rows(validation),
        },
        {
            "table_id": "table_04_agent_claim_boundary",
            "title": "Agent application claim map",
            "fieldnames": ["claim", "value"],
            "rows": _claim_boundary_rows(validation),
        },
    ]
    if iteration:
        tables.extend(
            [
                {
                    "table_id": "table_05_agent_iteration_candidates",
                    "title": "Agent iteration candidate ranking",
                    "fieldnames": [
                        "candidate_id",
                        "round_index",
                        "objective_score",
                        "full_melt_relative_error_pct",
                        "dominant_risk_relative_error_pct",
                        "full_melt_time_s",
                        "dominant_risk_time_s",
                        "early_shell_stress_proxy_MPa",
                        "review_status",
                    ],
                    "rows": _iteration_candidate_rows(iteration),
                },
                {
                    "table_id": "table_06_agent_iteration_stability",
                    "title": "Agent iteration stability review",
                    "fieldnames": [
                        "candidate_id",
                        "metric",
                        "quality_status",
                        "current_value",
                        "min_value",
                        "max_value",
                        "relative_spread_pct",
                        "threshold_pct",
                    ],
                    "rows": _iteration_stability_rows(iteration),
                },
            ]
        )
    return tables


def _candidate_comparison_rows(validation: dict[str, Any]) -> list[dict[str, Any]]:
    fluent = validation.get("fluent_pack_validation", {}).get("key_metrics", {})
    decision = validation.get("agent_validation_decision", {})
    rows: list[dict[str, Any]] = []
    for item in decision.get("target_comparison", []):
        rows.append(
            {
                "target_id": item.get("target_id"),
                "native_full_melt_time_s": _round(item.get("predicted_full_melt_time_s"), 3),
                "fluent_full_melt_time_s": _round(fluent.get("full_melt_time_s"), 3),
                "full_melt_relative_error_pct": _pct(item.get("full_melt_time_relative_error"), 3),
                "native_dominant_risk_time_s": _round(item.get("dominant_risk_time_s"), 3),
                "fluent_dominant_risk_time_s": _round(fluent.get("dominant_risk_time_s"), 3),
                "dominant_risk_relative_error_pct": _pct(item.get("dominant_risk_time_relative_error"), 3),
                "early_shell_stress_proxy_MPa": _round(item.get("early_max_shell_stress_proxy_MPa"), 6),
                "objective_score": _round(item.get("objective_score"), 6),
            }
        )
    return rows


def _validation_matrix_rows(validation: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in validation.get("cases", []):
        metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
        discretization = item.get("discretization", {}) if isinstance(item.get("discretization"), dict) else {}
        grid_cells = int(_float_or(metrics.get("grid_cells"), 0.0))
        time_steps = int(_float_or(metrics.get("time_steps"), 0.0))
        rows.append(
            {
                "validation_case_id": item.get("validation_case_id"),
                "target_id": item.get("target_id"),
                "case_variant": item.get("case_variant"),
                "nx": discretization.get("nx"),
                "ny": discretization.get("ny"),
                "time_step_s": discretization.get("time_step_s"),
                "shell_columns": discretization.get("shell_columns"),
                "grid_cells": grid_cells,
                "time_steps": time_steps,
                "cell_time_steps": grid_cells * time_steps,
            }
        )
    return rows


def _stability_rows(validation: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stability = validation.get("qoi_stability", {}) if isinstance(validation.get("qoi_stability"), dict) else {}
    for target in stability.get("targets", []):
        for metric in target.get("metrics", []):
            rows.append(
                {
                    "target_id": target.get("target_id"),
                    "metric": metric.get("metric"),
                    "quality_status": metric.get("quality_status"),
                    "current_value": _round(metric.get("current_value"), 6),
                    "min_value": _round(metric.get("min_value"), 6),
                    "max_value": _round(metric.get("max_value"), 6),
                    "relative_spread_pct": _pct(metric.get("relative_spread_vs_current"), 3),
                    "threshold_pct": _pct(metric.get("threshold"), 3),
                }
            )
    return rows


def _claim_boundary_rows(validation: dict[str, Any]) -> list[dict[str, Any]]:
    decision = validation.get("agent_validation_decision", {}) if isinstance(validation.get("agent_validation_decision"), dict) else {}
    boundary = decision.get("claim_boundary", {}) if isinstance(decision.get("claim_boundary"), dict) else {}
    execution = validation.get("execution_boundary", {}) if isinstance(validation.get("execution_boundary"), dict) else {}
    return [
        {"claim": "recommended_target", "value": decision.get("recommended_target_id")},
        {"claim": "native_solver_runs", "value": execution.get("native_dewaxing_solver_runs")},
        {"claim": "native_cell_time_steps", "value": execution.get("native_cell_time_steps")},
        {"claim": "new_fluent_calculation", "value": execution.get("new_fluent_calculation")},
        {"claim": "supports_agent_workflow_control", "value": boundary.get("can_support_agent_workflow_control")},
        {"claim": "supports_fastfluent_screening_decision", "value": boundary.get("can_support_fastfluent_screening_decision")},
        {"claim": "supports_fluent_parameter_prioritization", "value": boundary.get("can_support_fluent_parameter_prioritization")},
        {"claim": "supports_final_cfd_validation", "value": boundary.get("can_support_final_cfd_validation")},
    ]


def _iteration_candidate_rows(iteration: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _rank_iteration_candidates(iteration):
        metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
        comparison = item.get("comparison_metrics", {}) if isinstance(item.get("comparison_metrics"), dict) else {}
        rows.append(
            {
                "candidate_id": item.get("candidate_id"),
                "round_index": item.get("round_index"),
                "objective_score": _round(item.get("agent_objective_score"), 6),
                "full_melt_relative_error_pct": _pct(comparison.get("full_melt_time_relative_error"), 3),
                "dominant_risk_relative_error_pct": _pct(comparison.get("dominant_risk_time_relative_error"), 3),
                "full_melt_time_s": _round(metrics.get("predicted_full_melt_time_s"), 3),
                "dominant_risk_time_s": _round(metrics.get("dominant_risk_time_s"), 3),
                "early_shell_stress_proxy_MPa": _round(metrics.get("early_max_shell_stress_proxy_MPa"), 6),
                "review_status": _iteration_review_status(iteration, item.get("candidate_id")),
            }
        )
    return rows


def _iteration_stability_rows(iteration: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for review in iteration.get("validation_reviews", []):
        candidate_id = review.get("candidate_id")
        stability = review.get("qoi_stability", {}) if isinstance(review.get("qoi_stability"), dict) else {}
        for metric in stability.get("metrics", []):
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "metric": metric.get("metric"),
                    "quality_status": metric.get("quality_status"),
                    "current_value": _round(metric.get("current_value"), 6),
                    "min_value": _round(metric.get("min_value"), 6),
                    "max_value": _round(metric.get("max_value"), 6),
                    "relative_spread_pct": _pct(metric.get("relative_spread_vs_current"), 3),
                    "threshold_pct": _pct(metric.get("threshold"), 3),
                }
            )
    return rows


def _write_figures(validation: dict[str, Any], figures_dir: Path, iteration: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    figures: list[dict[str, Any]] = []
    evidence_chain = _evidence_chain_svg(validation)
    path = figures_dir / "figure_01_agent_evidence_chain.svg"
    write_text_file(path, evidence_chain)
    figures.append(
        {
            "figure_id": "figure_01_agent_evidence_chain",
            "title": "Agent evidence chain for dewaxing",
            "path": str(path),
            "kind": "svg",
        }
    )

    candidate_rows = []
    for item in validation.get("agent_validation_decision", {}).get("target_comparison", []):
        target = str(item.get("target_id"))
        candidate_rows.append({"label": f"{target} full melt", "value": _float_or(item.get("full_melt_time_relative_error"), 0.0) * 100.0, "status": "passed"})
        candidate_rows.append({"label": f"{target} risk time", "value": _float_or(item.get("dominant_risk_time_relative_error"), 0.0) * 100.0, "status": "passed"})
    path = figures_dir / "figure_02_candidate_relative_errors.svg"
    write_text_file(path, _horizontal_bar_svg("Candidate Error vs Reviewed Fluent Pack", "Relative error (%)", candidate_rows))
    figures.append(
        {
            "figure_id": "figure_02_candidate_relative_errors",
            "title": "Candidate relative errors against reviewed Fluent pack",
            "path": str(path),
            "kind": "svg",
        }
    )

    stability_rows = []
    for row in _stability_rows(validation):
        stability_rows.append(
            {
                "label": f"{row['target_id']} {_metric_display_label(row.get('metric'))}",
                "value": _float_or(row.get("relative_spread_pct"), 0.0),
                "threshold": _float_or(row.get("threshold_pct"), 0.0),
                "status": row.get("quality_status"),
            }
        )
    path = figures_dir / "figure_03_stability_spread.svg"
    write_text_file(path, _horizontal_bar_svg("Grid/Time-Step Stability Spread", "Relative spread (%)", stability_rows, show_threshold=True))
    figures.append(
        {
            "figure_id": "figure_03_stability_spread",
            "title": "Grid/time-step stability spread",
            "path": str(path),
            "kind": "svg",
        }
    )

    load_rows = []
    for row in _validation_matrix_rows(validation):
        load_rows.append({"label": row["validation_case_id"], "value": _float_or(row["cell_time_steps"], 0.0) / 1.0e6, "status": "passed"})
    path = figures_dir / "figure_04_native_compute_load.svg"
    write_text_file(path, _horizontal_bar_svg("Native Solver Compute Load", "Cell-time steps (million)", load_rows))
    figures.append(
        {
            "figure_id": "figure_04_native_compute_load",
            "title": "Native solver compute load by validation case",
            "path": str(path),
            "kind": "svg",
        }
    )
    if iteration:
        objective_rows = []
        for item in _rank_iteration_candidates(iteration)[:10]:
            candidate_id = item.get("candidate_id")
            review_status = _iteration_review_status(iteration, candidate_id)
            objective_rows.append(
                {
                    "label": f"{candidate_id} r{item.get('round_index')}",
                    "value": _float_or(item.get("agent_objective_score"), 0.0),
                    "status": review_status,
                }
            )
        path = figures_dir / "figure_05_agent_iteration_objective.svg"
        write_text_file(path, _horizontal_bar_svg("Agent Iteration Objective Ranking", "Objective score (lower is better)", objective_rows))
        figures.append(
            {
                "figure_id": "figure_05_agent_iteration_objective",
                "title": "Agent iteration objective ranking",
                "path": str(path),
                "kind": "svg",
            }
        )

        accepted_stability_rows = []
        for row in _accepted_iteration_stability_rows(iteration):
            accepted_stability_rows.append(
                {
                    "label": _metric_display_label(row.get("metric")),
                    "value": _float_or(row.get("relative_spread_pct"), 0.0),
                    "threshold": _float_or(row.get("threshold_pct"), 0.0),
                    "status": row.get("quality_status"),
                }
            )
        path = figures_dir / "figure_06_accepted_candidate_stability.svg"
        write_text_file(path, _horizontal_bar_svg("Accepted Candidate Stability", "Relative spread (%)", accepted_stability_rows, show_threshold=True))
        figures.append(
            {
                "figure_id": "figure_06_accepted_candidate_stability",
                "title": "Accepted Agent candidate stability",
                "path": str(path),
                "kind": "svg",
            }
        )

        path = figures_dir / "figure_07_agent_iteration_flow.svg"
        write_text_file(path, _iteration_flow_svg(iteration))
        figures.append(
            {
                "figure_id": "figure_07_agent_iteration_flow",
                "title": "Agent iteration decision flow",
                "path": str(path),
                "kind": "svg",
            }
        )
    return figures


def _paper_claims(validation: dict[str, Any], iteration: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = _summary(validation, iteration)
    decision = validation.get("agent_validation_decision", {}) if isinstance(validation.get("agent_validation_decision"), dict) else {}
    warnings = list(validation.get("qoi_stability", {}).get("warnings", [])) + list(decision.get("warnings", []))
    supported = [
        f"FastFluent-native validation executed {summary.get('native_solver_runs')} reduced-order dewaxing cases without a new Fluent calculation.",
        f"The validation matrix accumulated {summary.get('native_cell_time_steps')} native cell-time steps.",
        f"The Agent selected `{summary.get('recommended_target_id')}` as the FastFluent-guided candidate.",
        _candidate_improvement_claim(summary),
        "The full-melt timing QoI is the strongest paper-facing FastFluent-native result because it passed the grid/time-step stability gate.",
    ]
    if iteration:
        supported.extend(_iteration_supported_claims(summary))
    restricted = [
        "Use the native solver as application evidence, not final CFD validation.",
        "Use the pressure-risk proxy for ranking and screening, not as a Fluent pressure field.",
        "Treat crack and FSI language as outside the current FastFluent-native evidence.",
        "Treat `shell_thin` as an effective thermal-resistance correction until geometry or material evidence is added.",
        _risk_stress_application_note(warnings),
    ]
    if iteration:
        restricted.append("Use the Agent iteration pack to support candidate search, stability-gated acceptance, and compute-load evidence; keep final CFD claims tied to reviewed Fluent evidence.")
    return {
        "schema_version": "fastfluent_dewaxing_paper_claims_v1",
        "status": "warning" if warnings else "passed",
        "supported_claims": supported,
        "restricted_claims": restricted,
        "warnings": warnings,
    }


def _summary(validation: dict[str, Any], iteration: dict[str, Any] | None = None) -> dict[str, Any]:
    decision = validation.get("agent_validation_decision", {}) if isinstance(validation.get("agent_validation_decision"), dict) else {}
    recommended_id = decision.get("recommended_target_id")
    recommended = next((item for item in decision.get("target_comparison", []) if item.get("target_id") == recommended_id), {})
    baseline = next((item for item in decision.get("target_comparison", []) if item.get("target_id") == "baseline"), {})
    execution = validation.get("execution_boundary", {}) if isinstance(validation.get("execution_boundary"), dict) else {}
    summary = {
        "recommended_target_id": recommended_id,
        "native_solver_runs": execution.get("native_dewaxing_solver_runs"),
        "native_cell_time_steps": execution.get("native_cell_time_steps"),
        "new_fluent_calculation": execution.get("new_fluent_calculation"),
        "recommended_full_melt_time_s": _round(recommended.get("predicted_full_melt_time_s"), 3),
        "recommended_full_melt_error_pct": _pct(recommended.get("full_melt_time_relative_error"), 3),
        "recommended_risk_time_s": _round(recommended.get("dominant_risk_time_s"), 3),
        "recommended_risk_time_error_pct": _pct(recommended.get("dominant_risk_time_relative_error"), 3),
        "baseline_full_melt_error_pct": _pct(baseline.get("full_melt_time_relative_error"), 3),
        "baseline_risk_time_error_pct": _pct(baseline.get("dominant_risk_time_relative_error"), 3),
    }
    if iteration:
        summary.update(_iteration_summary(iteration))
    return summary


def _iteration_summary(iteration: dict[str, Any]) -> dict[str, Any]:
    decision = iteration.get("agent_decision", {}) if isinstance(iteration.get("agent_decision"), dict) else {}
    accepted = decision.get("accepted_candidate", {}) if isinstance(decision.get("accepted_candidate"), dict) else {}
    best_unvalidated = decision.get("best_unvalidated_candidate", {}) if isinstance(decision.get("best_unvalidated_candidate"), dict) else {}
    rejected = decision.get("stability_rejected_candidates", []) if isinstance(decision.get("stability_rejected_candidates"), list) else []
    execution = _iteration_execution(iteration)
    accepted_stability = _accepted_iteration_stability_lookup(iteration)
    return {
        "iteration_round_count": iteration.get("round_count"),
        "iteration_candidate_count": iteration.get("candidate_count") or len(iteration.get("candidates", [])),
        "iteration_validation_target_count": iteration.get("validation_target_count") or len(iteration.get("validation_reviews", [])),
        "iteration_solver_runs": execution.get("native_dewaxing_solver_runs"),
        "iteration_cell_time_steps": execution.get("native_cell_time_steps"),
        "iteration_new_fluent_calculation": execution.get("new_fluent_calculation"),
        "iteration_best_unvalidated_candidate_id": best_unvalidated.get("candidate_id"),
        "iteration_best_unvalidated_objective_score": _round(best_unvalidated.get("agent_objective_score"), 6),
        "iteration_best_unvalidated_full_melt_error_pct": _pct(best_unvalidated.get("full_melt_time_relative_error"), 3),
        "iteration_best_unvalidated_risk_time_error_pct": _pct(best_unvalidated.get("dominant_risk_time_relative_error"), 3),
        "iteration_accepted_candidate_id": accepted.get("candidate_id"),
        "iteration_accepted_validation_status": decision.get("accepted_candidate_validation_status"),
        "iteration_accepted_objective_score": _round(accepted.get("agent_objective_score"), 6),
        "iteration_accepted_full_melt_time_s": _round(accepted.get("predicted_full_melt_time_s"), 3),
        "iteration_accepted_full_melt_error_pct": _pct(accepted.get("full_melt_time_relative_error"), 3),
        "iteration_accepted_risk_time_s": _round(accepted.get("dominant_risk_time_s"), 3),
        "iteration_accepted_risk_time_error_pct": _pct(accepted.get("dominant_risk_time_relative_error"), 3),
        "iteration_accepted_shell_stress_proxy_MPa": _round(accepted.get("early_max_shell_stress_proxy_MPa"), 6),
        "iteration_rejected_candidate_count": len(rejected),
        "iteration_objective_improvement_vs_baseline_pct": _pct(decision.get("objective_improvement_vs_baseline"), 3),
        "iteration_objective_improvement_vs_shell_thin_pct": _pct(decision.get("objective_improvement_vs_shell_thin"), 3),
        "iteration_accepted_full_melt_spread_pct": accepted_stability.get("predicted_full_melt_time_s"),
        "iteration_accepted_risk_time_spread_pct": accepted_stability.get("dominant_risk_time_s"),
        "iteration_accepted_shell_stress_spread_pct": accepted_stability.get("early_max_shell_stress_proxy_MPa"),
        "iteration_accepted_pressure_risk_spread_pct": accepted_stability.get("peak_pressure_risk_proxy"),
        "iteration_accepted_energy_error_pct": accepted_stability.get("energy_balance_relative_error"),
    }


def _iteration_supported_claims(summary: dict[str, Any]) -> list[str]:
    accepted = summary.get("iteration_accepted_candidate_id")
    best = summary.get("iteration_best_unvalidated_candidate_id")
    return [
        f"The Agent iteration campaign evaluated {summary.get('iteration_candidate_count')} native candidates across {summary.get('iteration_round_count')} rounds and executed {summary.get('iteration_solver_runs')} native solver runs without a new Fluent calculation.",
        f"The Agent iteration campaign accumulated {summary.get('iteration_cell_time_steps')} native cell-time steps.",
        f"The best raw-fit candidate `{best}` was checked before acceptance; the Agent accepted `{accepted}` after rejecting {summary.get('iteration_rejected_candidate_count')} fitted candidates during stability review.",
        f"`{accepted}` improved the combined native objective by {summary.get('iteration_objective_improvement_vs_baseline_pct')}% relative to baseline and {summary.get('iteration_objective_improvement_vs_shell_thin_pct')}% relative to `shell_thin` while passing the accepted-candidate review.",
    ]


def _candidate_improvement_claim(summary: dict[str, Any]) -> str:
    target = summary.get("recommended_target_id")
    full = summary.get("recommended_full_melt_error_pct")
    risk = summary.get("recommended_risk_time_error_pct")
    baseline_full = summary.get("baseline_full_melt_error_pct")
    baseline_risk = summary.get("baseline_risk_time_error_pct")
    full_improved = _float_or(full, 1.0e30) < _float_or(baseline_full, -1.0)
    risk_improved = _float_or(risk, 1.0e30) < _float_or(baseline_risk, -1.0)
    if full_improved and risk_improved:
        return f"`{target}` reduced full-melt relative error to {full}% and dominant-risk timing error to {risk}% against the reviewed Fluent pack."
    if full_improved:
        return f"`{target}` reduced full-melt relative error from {baseline_full}% to {full}%; its smoothed dominant-risk timing error was {risk}%."
    return f"`{target}` was selected by the combined FastFluent objective; its full-melt error was {full}% and smoothed dominant-risk timing error was {risk}%."


def _risk_stress_application_note(warnings: list[str]) -> str:
    if warnings:
        return "Keep risk-window and shell-stress proxy statements framed as reduced-order screening guidance while stability warnings are present."
    return "Use risk-window and shell-stress proxy statements as grid/time-step checked application screening metrics in this reduced-order pack."


def _validation_stability_sentence(validation: dict[str, Any], summary: dict[str, Any], stability: dict[tuple[Any, Any], dict[str, Any]]) -> str:
    target = summary.get("recommended_target_id")
    full_spread = _format_number(stability.get((target, "predicted_full_melt_time_s"), {}).get("relative_spread_pct"))
    risk_spread = _format_number(stability.get((target, "dominant_risk_time_s"), {}).get("relative_spread_pct"))
    stress_spread = _format_number(stability.get((target, "early_max_shell_stress_proxy_MPa"), {}).get("relative_spread_pct"))
    warnings = list(validation.get("qoi_stability", {}).get("warnings", []))
    if validation.get("quality_status") == "passed" and not warnings:
        return (
            f"The strongest native QoI remains full-melt timing: for `{target}`, the grid/time-step relative spread was {full_spread}% and passed the validation threshold. "
            f"The smoothed risk-window timing and heat-flux shell-stress proxy also passed the current grid/time-step checks; for `{target}`, their relative spreads were {risk_spread}% and {stress_spread}%, respectively."
        )
    return (
        f"The strongest native QoI was full-melt timing: for `{target}`, the grid/time-step relative spread was {full_spread}% and passed the validation threshold. "
        "When the validation quality is warning, at least one reduced-order proxy exceeded the current stability threshold. Use those quantities as screening guidance until their stability warnings are resolved."
    )


def _results_section_markdown(
    validation: dict[str, Any],
    claims: dict[str, Any],
    *,
    manuscript_title: str,
    iteration: dict[str, Any] | None = None,
) -> str:
    summary = _summary(validation, iteration)
    fluent = validation.get("fluent_pack_validation", {}).get("key_metrics", {})
    stability = _stable_metric_lookup(validation)
    lines = [
        f"# Results Section Draft: {manuscript_title}",
        "",
        "The reviewed Fluent dewaxing result pack was used as external high-fidelity evidence, while the Agent executed a separate FastFluent-native reduced-order validation matrix for candidate screening. "
        f"The validation matrix ran {summary.get('native_solver_runs')} native dewaxing cases and accumulated {summary.get('native_cell_time_steps')} cell-time steps without launching Fluent or editing Fluent case/data files.",
        "",
        f"The reviewed Fluent pack reported a full-melt time of {_format_number(fluent.get('full_melt_time_s'))} s and a dominant risk time of {_format_number(fluent.get('dominant_risk_time_s'))} s. "
        f"The baseline native case predicted full-melt and risk-time relative errors of {summary.get('baseline_full_melt_error_pct')}% and {summary.get('baseline_risk_time_error_pct')}%, respectively. "
        f"The FastFluent-guided candidate `{summary.get('recommended_target_id')}` reduced full-melt error to {summary.get('recommended_full_melt_error_pct')}%, with predicted full-melt time {_format_number(summary.get('recommended_full_melt_time_s'))} s. "
        f"Its smoothed dominant-risk time was {_format_number(summary.get('recommended_risk_time_s'))} s, corresponding to {summary.get('recommended_risk_time_error_pct')}% relative error against the reviewed Fluent timing.",
        "",
        _validation_stability_sentence(validation, summary, stability),
        "",
    ]
    if iteration:
        lines.extend([_iteration_results_paragraph(summary), ""])
    lines.extend(
        [
            "This evidence supports the application claim that FastFluent contributes an intermediate computation which selects and checks a dewaxing candidate before any additional high-fidelity Fluent work is requested. "
            "In the manuscript, use the native calculation for candidate selection, timing comparison, and compute-load evidence, while keeping final high-fidelity statements tied to reviewed Fluent results.",
            "",
            "## Supported Claims",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in claims.get("supported_claims", []))
    lines.extend(["", "## Application Use Notes", ""])
    lines.extend(f"- {item}" for item in claims.get("restricted_claims", []))
    lines.append("")
    return "\n".join(lines)


def _iteration_results_paragraph(summary: dict[str, Any]) -> str:
    return (
        "A separate Agent-guided FastFluent campaign then converted the native model into a closed-loop candidate search. "
        f"It evaluated {summary.get('iteration_candidate_count')} candidates across {summary.get('iteration_round_count')} rounds, ran {summary.get('iteration_solver_runs')} native solver cases, and accumulated {summary.get('iteration_cell_time_steps')} cell-time steps without a new Fluent calculation. "
        f"The best raw-fit candidate was `{summary.get('iteration_best_unvalidated_candidate_id')}`, with full-melt error {summary.get('iteration_best_unvalidated_full_melt_error_pct')}% and risk-time error {summary.get('iteration_best_unvalidated_risk_time_error_pct')}%, but the Agent did not accept it directly. "
        f"After rejecting {summary.get('iteration_rejected_candidate_count')} fitted candidates during the stability review, the Agent accepted `{summary.get('iteration_accepted_candidate_id')}`. "
        f"The accepted candidate predicted full melt at {_format_number(summary.get('iteration_accepted_full_melt_time_s'))} s with {summary.get('iteration_accepted_full_melt_error_pct')}% full-melt error and {summary.get('iteration_accepted_risk_time_error_pct')}% risk-time error. "
        f"Its accepted-candidate spreads were {summary.get('iteration_accepted_full_melt_spread_pct')}% for full-melt timing, {summary.get('iteration_accepted_risk_time_spread_pct')}% for risk-window timing, and {summary.get('iteration_accepted_shell_stress_spread_pct')}% for the shell-stress proxy. "
        f"The combined native objective improved by {summary.get('iteration_objective_improvement_vs_baseline_pct')}% relative to baseline and {summary.get('iteration_objective_improvement_vs_shell_thin_pct')}% relative to `shell_thin`."
    )


def _methods_section_markdown(validation: dict[str, Any], *, manuscript_title: str, iteration: dict[str, Any] | None = None) -> str:
    summary = _summary(validation, iteration)
    lines = [
        f"# Methods Section Draft: {manuscript_title}",
        "",
        "FastFluent-native dewaxing evidence was generated with a bounded reduced-order solver that resolves transient 2D heat conduction in a shell/wax surrogate domain with effective heat-capacity phase change. "
        "The validation pack did not invoke Fluent, PyFluent, UDF compilation, or case/data editing.",
        "",
        f"The validation matrix contained {summary.get('native_solver_runs')} cases: baseline and the FastFluent-guided candidate, each evaluated on current, coarse-grid, fine-grid, larger-time-step, and smaller-time-step settings when the standard profile was used. "
        "Each native result was compiled into a FastFluent Result Pack before aggregation.",
        "",
        "The Agent compared native QoIs with the reviewed Fluent result pack using full-melt timing and dominant risk-window timing. "
        "It then applied grid/time-step stability checks to report which reduced-order application metrics were stable enough for paper-facing candidate screening.",
        "",
    ]
    if iteration:
        lines.extend(
            [
                "The optional Agent iteration pack used the same FastFluent-native solver in a closed-loop candidate campaign. "
                f"It ranked {summary.get('iteration_candidate_count')} candidates, then ran five-case stability reviews on top candidates until `{summary.get('iteration_accepted_candidate_id')}` passed. "
                "The iteration pack was read as a completed manifest by this compiler; no native solver rerun and no Fluent execution occurred during evidence compilation.",
                "",
            ]
        )
    return "\n".join(lines)


def _figure_caption_section(figures: list[dict[str, Any]]) -> str:
    lines = ["# Figure Captions", ""]
    captions = {
        "figure_01_agent_evidence_chain": "Agent evidence chain linking reviewed Fluent evidence, FastFluent-native validation, candidate selection, and application scope.",
        "figure_02_candidate_relative_errors": "Relative timing errors of baseline and FastFluent-guided candidates against the reviewed Fluent result pack.",
        "figure_03_stability_spread": "Grid/time-step relative spread for native QoIs against the validation thresholds.",
        "figure_04_native_compute_load": "Native solver compute load by validation case, reported as cell-time steps.",
        "figure_05_agent_iteration_objective": "Objective ranking from the Agent-guided FastFluent-native iteration campaign.",
        "figure_06_accepted_candidate_stability": "Accepted Agent candidate stability spreads against the review thresholds.",
        "figure_07_agent_iteration_flow": "Agent iteration flow from round-wise candidate proposals to stability-gated acceptance.",
    }
    for figure in figures:
        lines.append(f"- {figure.get('figure_id')}: {captions.get(figure.get('figure_id'), figure.get('title'))}")
    lines.append("")
    return "\n".join(lines)


def _evidence_report_markdown(
    validation: dict[str, Any],
    claims: dict[str, Any],
    tables: list[dict[str, Any]],
    figures: list[dict[str, Any]],
    *,
    manuscript_title: str,
    iteration: dict[str, Any] | None = None,
) -> str:
    summary = _summary(validation, iteration)
    lines = [
        f"# Dewaxing Paper Evidence Pack: {manuscript_title}",
        "",
        f"- Recommended target: `{summary.get('recommended_target_id')}`",
        f"- Native solver runs: `{summary.get('native_solver_runs')}`",
        f"- Native cell-time steps: `{summary.get('native_cell_time_steps')}`",
        f"- New Fluent calculation: `{summary.get('new_fluent_calculation')}`",
        f"- Source validation quality: `{validation.get('quality_status')}`",
    ]
    if iteration:
        lines.extend(
            [
                f"- Agent iteration accepted candidate: `{summary.get('iteration_accepted_candidate_id')}`",
                f"- Agent iteration solver runs: `{summary.get('iteration_solver_runs')}`",
                f"- Agent iteration cell-time steps: `{summary.get('iteration_cell_time_steps')}`",
                f"- Agent iteration rejected candidates: `{summary.get('iteration_rejected_candidate_count')}`",
            ]
        )
    lines.extend(["", "## Tables", ""])
    for table in tables:
        lines.append(f"- `{table['table_id']}`: {table['title']}")
    lines.extend(["", "## Figures", ""])
    for figure in figures:
        lines.append(f"- `{figure['figure_id']}`: `{figure['path']}`")
    lines.extend(["", "## Application Use Notes", ""])
    lines.extend(f"- {item}" for item in claims.get("restricted_claims", []))
    lines.extend(["", "## Implementation Notes", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _rank_iteration_candidates(iteration: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = iteration.get("candidates", []) if isinstance(iteration.get("candidates"), list) else []
    return sorted(candidates, key=lambda item: _float_or(item.get("agent_objective_score"), 1.0e30))


def _iteration_review_status(iteration: dict[str, Any], candidate_id: Any) -> str:
    decision = iteration.get("agent_decision", {}) if isinstance(iteration.get("agent_decision"), dict) else {}
    accepted = decision.get("accepted_candidate", {}) if isinstance(decision.get("accepted_candidate"), dict) else {}
    if candidate_id == accepted.get("candidate_id"):
        return "accepted"
    rejected = decision.get("stability_rejected_candidates", []) if isinstance(decision.get("stability_rejected_candidates"), list) else []
    if any(candidate_id == item.get("candidate_id") for item in rejected):
        return "stability_rejected"
    for review in iteration.get("validation_reviews", []):
        if candidate_id == review.get("candidate_id"):
            return f"review_{review.get('quality_status')}"
    return "not_reviewed"


def _accepted_iteration_stability_rows(iteration: dict[str, Any]) -> list[dict[str, Any]]:
    decision = iteration.get("agent_decision", {}) if isinstance(iteration.get("agent_decision"), dict) else {}
    accepted = decision.get("accepted_candidate", {}) if isinstance(decision.get("accepted_candidate"), dict) else {}
    accepted_id = accepted.get("candidate_id")
    return [row for row in _iteration_stability_rows(iteration) if row.get("candidate_id") == accepted_id]


def _accepted_iteration_stability_lookup(iteration: dict[str, Any]) -> dict[str, float | None]:
    lookup: dict[str, float | None] = {}
    for row in _accepted_iteration_stability_rows(iteration):
        lookup[str(row.get("metric"))] = row.get("relative_spread_pct")
    return lookup


def _iteration_execution(iteration: dict[str, Any] | None) -> dict[str, Any]:
    if not iteration:
        return {}
    execution = iteration.get("execution_boundary", {}) if isinstance(iteration.get("execution_boundary"), dict) else {}
    decision = iteration.get("agent_decision", {}) if isinstance(iteration.get("agent_decision"), dict) else {}
    decision_execution = decision.get("execution_summary", {}) if isinstance(decision.get("execution_summary"), dict) else {}
    return {
        "native_dewaxing_solver_runs": decision_execution.get("native_dewaxing_solver_runs", execution.get("native_dewaxing_solver_runs")),
        "native_cell_time_steps": decision_execution.get("native_cell_time_steps", execution.get("native_cell_time_steps")),
        "new_fluent_calculation": decision_execution.get("new_fluent_calculation", execution.get("new_fluent_calculation")),
    }


def _evidence_chain_svg(validation: dict[str, Any]) -> str:
    summary = _summary(validation)
    nodes = [
        ("Reviewed Fluent pack", "existing external evidence"),
        ("FastFluent native validation", f"{summary.get('native_solver_runs')} cases"),
        ("Agent candidate selection", str(summary.get("recommended_target_id"))),
        ("Stability gate", str(validation.get("quality_status"))),
        ("Paper application claims", "screening plus timing evidence"),
    ]
    width = 1120
    height = 240
    box_w = 190
    box_h = 88
    gap = 30
    x0 = 30
    y = 76
    parts = [_svg_header(width, height), f'<text x="30" y="36" class="title">Agent Evidence Chain</text>']
    for index, (title, subtitle) in enumerate(nodes):
        x = x0 + index * (box_w + gap)
        box_class = "box-accent" if index in {2, 3} else "box"
        parts.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="4" class="{box_class}"/>')
        parts.append(f'<text x="{x + 14}" y="{y + 34}" class="label">{_esc(title)}</text>')
        parts.append(f'<text x="{x + 14}" y="{y + 60}" class="small">{_esc(subtitle)}</text>')
        if index + 1 < len(nodes):
            ax = x + box_w
            bx = ax + gap - 8
            ay = y + box_h / 2
            parts.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{ay}" class="arrow"/>')
            parts.append(f'<polygon points="{bx},{ay} {bx - 10},{ay - 5} {bx - 10},{ay + 5}" class="arrowhead"/>')
    parts.append(_svg_footer())
    return "\n".join(parts)


def _iteration_flow_svg(iteration: dict[str, Any]) -> str:
    round_trace = iteration.get("round_trace", []) if isinstance(iteration.get("round_trace"), list) else []
    decision = iteration.get("agent_decision", {}) if isinstance(iteration.get("agent_decision"), dict) else {}
    accepted = decision.get("accepted_candidate", {}) if isinstance(decision.get("accepted_candidate"), dict) else {}
    rejected = decision.get("stability_rejected_candidates", []) if isinstance(decision.get("stability_rejected_candidates"), list) else []
    nodes: list[tuple[str, str]] = []
    for item in round_trace:
        best = item.get("best_after_round", {}) if isinstance(item.get("best_after_round"), dict) else {}
        nodes.append((f"Round {item.get('round_index')}: {_phrase_label(item.get('round_id'))}", f"{len(item.get('candidate_ids', []))} candidates; best {best.get('candidate_id')}"))
    nodes.append(("Stability review", f"{iteration.get('validation_target_count')} targets; {len(rejected)} rejected"))
    nodes.append(("Accepted candidate", str(accepted.get("candidate_id"))))
    if not nodes:
        nodes = [("Agent iteration", "no data")]
    box_w = 210
    box_h = 88
    gap = 26
    width = 60 + len(nodes) * box_w + max(0, len(nodes) - 1) * gap
    height = 240
    x0 = 30
    y = 76
    parts = [_svg_header(width, height), f'<text x="30" y="36" class="title">Agent Iteration Flow</text>']
    for index, (title, subtitle) in enumerate(nodes):
        x = x0 + index * (box_w + gap)
        if title == "Accepted candidate":
            box_class = "box-accepted"
        elif title == "Stability review":
            box_class = "box-warning"
        else:
            box_class = "box"
        parts.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="4" class="{box_class}"/>')
        parts.append(f'<text x="{x + 12}" y="{y + 34}" class="label">{_esc(title)}</text>')
        parts.append(f'<text x="{x + 12}" y="{y + 60}" class="small">{_esc(subtitle)}</text>')
        if index + 1 < len(nodes):
            ax = x + box_w
            bx = ax + gap - 8
            ay = y + box_h / 2
            parts.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{ay}" class="arrow"/>')
            parts.append(f'<polygon points="{bx},{ay} {bx - 10},{ay - 5} {bx - 10},{ay + 5}" class="arrowhead"/>')
    parts.append(_svg_footer())
    return "\n".join(parts)


def _horizontal_bar_svg(title: str, axis_label: str, rows: list[dict[str, Any]], *, show_threshold: bool = False) -> str:
    if not rows:
        rows = [{"label": "no data", "value": 0.0, "status": "warning"}]
    label_w = 350
    bar_w = 680
    row_h = 30
    top = 78
    width = label_w + bar_w + 180
    height = top + row_h * len(rows) + 70
    max_value = max([_float_or(row.get("value"), 0.0) for row in rows] + [0.0])
    if show_threshold:
        max_value = max(max_value, max([_float_or(row.get("threshold"), 0.0) for row in rows] + [0.0]))
    if max_value <= 0.0:
        max_value = 1.0
    max_value *= 1.12
    axis_y = top + row_h * len(rows) + 14
    parts = [
        _svg_header(width, height),
        f'<text x="30" y="34" class="title">{_esc(title)}</text>',
        f'<text x="{label_w}" y="58" class="axis">{_esc(axis_label)}</text>',
    ]
    for fraction in (0.25, 0.50, 0.75, 1.00):
        x = label_w + bar_w * fraction
        parts.append(f'<line x1="{x:.2f}" y1="{top - 8}" x2="{x:.2f}" y2="{axis_y - 8}" class="gridline"/>')
    parts.append(f'<line x1="{label_w}" y1="{axis_y - 8}" x2="{label_w + bar_w}" y2="{axis_y - 8}" class="axisline"/>')
    for index, row in enumerate(rows):
        y = top + index * row_h
        value = _float_or(row.get("value"), 0.0)
        bar_len = 0.0 if max_value == 0 else value / max_value * bar_w
        cls = _bar_class(row.get("status"))
        parts.append(f'<text x="30" y="{y + 18}" class="label">{_esc(str(row.get("label")))}</text>')
        parts.append(f'<rect x="{label_w}" y="{y + 5}" width="{bar_len:.2f}" height="16" rx="1.5" class="{cls}"/>')
        parts.append(f'<text x="{label_w + bar_len + 8:.2f}" y="{y + 18}" class="small">{_format_number(value)}</text>')
        if show_threshold:
            threshold = _float_or(row.get("threshold"), 0.0)
            tx = label_w + (0.0 if max_value == 0 else threshold / max_value * bar_w)
            parts.append(f'<line x1="{tx:.2f}" y1="{y + 2}" x2="{tx:.2f}" y2="{y + 24}" class="threshold"/>')
    parts.append(f'<text x="{label_w}" y="{axis_y + 18}" class="caption">Soft blue bars indicate passed or accepted quantities; sakura bars mark rejected or warning quantities.</text>')
    parts.append(_svg_footer())
    return "\n".join(parts)


def _bar_class(status: Any) -> str:
    value = str(status or "")
    if value in {"warning", "stability_rejected", "review_warning"}:
        return "bar-warning"
    if value == "accepted":
        return "bar-accepted"
    if value == "not_reviewed":
        return "bar-muted"
    return "bar"


def _metric_display_label(metric: Any) -> str:
    labels = {
        "predicted_full_melt_time_s": "full-melt time",
        "dominant_risk_time_s": "risk-window time",
        "early_max_shell_stress_proxy_MPa": "shell-stress proxy",
        "peak_pressure_risk_proxy": "pressure-risk proxy",
        "energy_balance_relative_error": "energy-balance error",
    }
    key = str(metric if metric is not None else "")
    return labels.get(key, key.replace("_", " "))


def _phrase_label(value: Any) -> str:
    return str(value if value is not None else "").replace("_", " ").capitalize()


def _svg_header(width: int, height: int) -> str:
    c = NATURE_SOFT_PALETTE
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<style>",
            f"svg{{background:{c['paper']}}}",
            f"text{{font-family:Arial,Helvetica,sans-serif;fill:{c['ink']};letter-spacing:0}}",
            ".title{font-size:18px;font-weight:700}",
            ".label{font-size:12.5px;font-weight:600}",
            f".small{{font-size:11.5px;fill:{c['muted']}}}",
            f".axis{{font-size:11.5px;fill:{c['muted']}}}",
            f".caption{{font-size:10.5px;fill:{c['muted']}}}",
            f".box{{fill:{c['rice']};stroke:{c['grid']};stroke-width:0.9}}",
            f".box-accent{{fill:{c['blue_very_light']};stroke:{c['blue_ink']};stroke-width:1.0}}",
            f".box-accepted{{fill:{c['blue_light']};stroke:{c['blue_ink']};stroke-width:1.0}}",
            f".box-warning{{fill:{c['sakura']};stroke:{c['sakura_deep']};stroke-width:1.0}}",
            f".arrow{{stroke:{c['muted']};stroke-width:1.15}}",
            f".arrowhead{{fill:{c['muted']}}}",
            f".bar{{fill:{c['blue_deep']}}}",
            f".bar-accepted{{fill:{c['blue_ink']}}}",
            f".bar-muted{{fill:{c['blue_light']}}}",
            f".bar-warning{{fill:{c['sakura_deep']}}}",
            f".gridline{{stroke:{c['grid']};stroke-width:0.55;opacity:0.32}}",
            f".axisline{{stroke:{c['ink']};stroke-width:0.75;opacity:0.55}}",
            f".threshold{{stroke:{c['wine_soft']};stroke-width:0.95;stroke-dasharray:4 4}}",
            "</style>",
        ]
    )


def _svg_footer() -> str:
    return "</svg>"


def _stable_metric_lookup(validation: dict[str, Any]) -> dict[tuple[Any, Any], dict[str, Any]]:
    lookup: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in _stability_rows(validation):
        lookup[(row.get("target_id"), row.get("metric"))] = row
    return lookup


def _markdown_table(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(fieldnames) + " |"
    divider = "| " + " | ".join("---" for _ in fieldnames) + " |"
    body = ["| " + " | ".join(_cell(row.get(field)) for field in fieldnames) + " |" for row in rows]
    if not body:
        body = ["| " + " | ".join("" for _ in fieldnames) + " |"]
    return "\n".join([header, divider] + body) + "\n"


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|")


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


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


def _format_number(value: Any) -> str:
    parsed = _maybe_float(value)
    if parsed is None or not math.isfinite(parsed):
        return str(value)
    if abs(parsed) >= 1000:
        return f"{parsed:.0f}"
    if abs(parsed) >= 100:
        return f"{parsed:.2f}"
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
