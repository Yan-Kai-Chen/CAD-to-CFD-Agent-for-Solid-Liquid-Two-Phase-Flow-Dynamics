"""Validation pack for FastFluent-native dewaxing evidence.

The validation pack runs a bounded grid/time-step perturbation matrix around
the baseline native dewaxing case and the best study candidate from the local
dewaxing study. It is intended to make the FastFluent-native calculation
auditable as agent guidance without launching Fluent.
"""

from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
from typing import Any

from fromcad2cfd_postprocessing.dewaxing_result_pack import validate_dewaxing_result_pack

from .dewaxing_native_solver import demo_dewaxing_native_case, run_dewaxing_native_solver
from .file_io import ensure_dir, write_json_file, write_text_file
from .practical_native_artifacts import write_csv
from .result_pack import compile_native_result_pack, validate_result_pack


DEWAXING_NATIVE_VALIDATION_PACK_SCHEMA_VERSION = "fastfluent_dewaxing_native_validation_pack_v1"
DEWAXING_NATIVE_VALIDATION_DECISION_SCHEMA_VERSION = "fastfluent_dewaxing_native_validation_decision_v1"


LIMITATIONS = [
    "This pack uses the FastFluent-native reduced-order dewaxing solver only.",
    "Fluent execution, PyFluent execution, UDF compilation, and case/data editing are outside this validation pack.",
    "Grid and time-step checks quantify the FastFluent-native reduced-order model used by the Agent.",
    "The shell_thin candidate is an effective thermal-resistance correction unless geometry/material evidence is added.",
    "Pressure-risk and shell-stress outputs are application screening proxies.",
]


QOI_METRICS = [
    "predicted_full_melt_time_s",
    "dominant_risk_time_s",
    "early_max_shell_stress_proxy_MPa",
    "peak_pressure_risk_proxy",
    "energy_balance_relative_error",
]


STABILITY_THRESHOLDS = {
    "predicted_full_melt_time_s": 0.12,
    "dominant_risk_time_s": 0.30,
    "early_max_shell_stress_proxy_MPa": 0.40,
    "peak_pressure_risk_proxy": 0.35,
    "energy_balance_relative_error": 0.08,
}


def default_dewaxing_native_validation_plan(profile: str = "standard") -> list[dict[str, Any]]:
    """Return validation cases for baseline and best-study dewaxing candidates."""

    if profile not in {"smoke", "standard"}:
        raise ValueError(f"Unsupported validation profile: {profile}")
    base_plan = [
        _case_spec("current", "Current native grid/time step", []),
        _case_spec(
            "coarse_grid",
            "Coarser grid at current time step",
            [
                {"path": "domain.nx", "operation": "set", "value": 15},
                {"path": "domain.ny", "operation": "set", "value": 11},
            ],
        ),
        _case_spec(
            "fine_grid",
            "Finer grid with smaller stable time step",
            [
                {"path": "domain.nx", "operation": "set", "value": 25},
                {"path": "domain.ny", "operation": "set", "value": 19},
                {"path": "time.time_step_s", "operation": "set", "value": 0.04},
            ],
        ),
        _case_spec(
            "dt_large",
            "Larger time step at current grid",
            [{"path": "time.time_step_s", "operation": "set", "value": 0.10}],
        ),
        _case_spec(
            "dt_small",
            "Smaller time step at current grid",
            [{"path": "time.time_step_s", "operation": "set", "value": 0.04}],
        ),
    ]
    if profile == "smoke":
        base_plan = [item for item in base_plan if item["case_variant"] in {"current", "coarse_grid"}]

    targets = [
        _target_spec("baseline", "Baseline native case", []),
        _target_spec(
            "shell_thin",
            "Best study candidate: effective thinner shell",
            [{"path": "domain.shell_thickness_m", "operation": "scale", "value": 0.80}],
        ),
    ]
    matrix: list[dict[str, Any]] = []
    for target in targets:
        for case in base_plan:
            matrix.append(
                {
                    "validation_case_id": f"{target['target_id']}_{case['case_variant']}",
                    "target_id": target["target_id"],
                    "target_name": target["target_name"],
                    "case_variant": case["case_variant"],
                    "case_name": case["case_name"],
                    "description": case["description"],
                    "edits": list(target["edits"]) + list(case["edits"]),
                    "target_edits": target["edits"],
                    "perturbation_edits": case["edits"],
                }
            )
    return matrix


def run_dewaxing_native_validation_pack(
    *,
    output_dir: str | Path,
    comparison_pack: str | Path | None = None,
    profile: str = "standard",
    max_cases: int | None = None,
    validation_plan: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run dewaxing validation cases and write a paper-facing evidence pack."""

    root = Path(output_dir)
    ensure_dir(root)
    plan = list(validation_plan or default_dewaxing_native_validation_plan(profile))
    if max_cases is not None:
        plan = plan[: max(1, int(max_cases))]

    artifacts = {
        "manifest": str(root / "validation_pack_manifest.json"),
        "convergence_summary_csv": str(root / "convergence_summary.csv"),
        "convergence_summary_json": str(root / "convergence_summary.json"),
        "qoi_stability": str(root / "qoi_stability.json"),
        "paper_tables": str(root / "paper_tables.md"),
        "study_interpretation": str(root / "study_interpretation.md"),
        "agent_validation_decision": str(root / "agent_validation_decision.json"),
        "validation_report": str(root / "validation_report.md"),
    }
    fluent_validation = _validate_reference_pack(comparison_pack)
    base_case = demo_dewaxing_native_case()
    cases: list[dict[str, Any]] = []
    for index, spec in enumerate(plan):
        cases.append(_run_validation_case(index, spec, base_case, root=root, comparison_pack=comparison_pack))

    stability = _qoi_stability(cases)
    decision = _agent_validation_decision(cases, stability, fluent_validation)
    status = "failed" if any(item.get("status") == "failed" for item in cases) else "success"
    quality_status = "warning" if stability.get("warnings") or decision.get("warnings") else "passed"
    native_cell_steps = sum(int(_float_or(item.get("metrics", {}).get("grid_cells"), 0.0)) * int(_float_or(item.get("metrics", {}).get("time_steps"), 0.0)) for item in cases)
    manifest = {
        "schema_version": DEWAXING_NATIVE_VALIDATION_PACK_SCHEMA_VERSION,
        "status": status,
        "quality_status": quality_status if status == "success" else "failed",
        "case_id": "dewaxing_native_validation_pack",
        "profile": profile,
        "validation_case_count": len(cases),
        "comparison_pack": str(comparison_pack) if comparison_pack else None,
        "fluent_pack_validation": fluent_validation,
        "cases": cases,
        "qoi_stability": stability,
        "agent_validation_decision": decision,
        "artifacts": artifacts,
        "execution_boundary": {
            "new_fluent_calculation": False,
            "fluent_launched": False,
            "fluent_case_or_data_edited": False,
            "native_dewaxing_solver_runs": len(cases),
            "native_cell_time_steps": native_cell_steps,
        },
        "limitations": list(LIMITATIONS),
    }

    write_json_file(root / "validation_pack_manifest.json", manifest)
    write_json_file(root / "convergence_summary.json", cases)
    write_csv(root / "convergence_summary.csv", [_case_csv_row(item) for item in cases])
    write_json_file(root / "qoi_stability.json", stability)
    write_json_file(root / "agent_validation_decision.json", decision)
    write_text_file(root / "paper_tables.md", _paper_tables_markdown(manifest))
    write_text_file(root / "study_interpretation.md", _study_interpretation_markdown(manifest))
    write_text_file(root / "validation_report.md", dewaxing_native_validation_pack_markdown(manifest))
    return manifest


def dewaxing_native_validation_pack_markdown(pack: dict[str, Any]) -> str:
    """Render a concise validation-pack report."""

    decision = pack.get("agent_validation_decision", {}) if isinstance(pack.get("agent_validation_decision"), dict) else {}
    lines = [
        "# FastFluent Dewaxing Native Validation Pack",
        "",
        f"- Status: `{pack.get('status')}`",
        f"- Quality status: `{pack.get('quality_status')}`",
        f"- Profile: `{pack.get('profile')}`",
        f"- Validation cases: `{pack.get('validation_case_count')}`",
        f"- Native cell-time steps: `{pack.get('execution_boundary', {}).get('native_cell_time_steps')}`",
        f"- New Fluent calculation: `{pack.get('execution_boundary', {}).get('new_fluent_calculation')}`",
        f"- Recommended target: `{decision.get('recommended_target_id')}`",
        f"- Recommended next action: `{decision.get('recommended_next_action')}`",
        "",
        "## Reference Agreement",
        "",
    ]
    for item in decision.get("target_comparison", []):
        lines.append(
            f"- `{item.get('target_id')}`: full-melt error `{item.get('full_melt_time_relative_error')}`, "
            f"risk-time error `{item.get('dominant_risk_time_relative_error')}`"
        )
    lines.extend(["", "## Stability Summary", ""])
    stability = pack.get("qoi_stability", {}) if isinstance(pack.get("qoi_stability"), dict) else {}
    for target in stability.get("targets", []):
        lines.append(f"- `{target.get('target_id')}` quality `{target.get('quality_status')}`")
        for metric in target.get("metrics", []):
            lines.append(
                f"  - `{metric.get('metric')}` rel spread `{metric.get('relative_spread_vs_current')}`, "
                f"current `{metric.get('current_value')}`"
            )
    warnings = list(pack.get("qoi_stability", {}).get("warnings", [])) + list(decision.get("warnings", []))
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in warnings)
    lines.extend(["", "## Application Scope", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _run_validation_case(
    index: int,
    spec: dict[str, Any],
    base_case: dict[str, Any],
    *,
    root: Path,
    comparison_pack: str | Path | None,
) -> dict[str, Any]:
    case = deepcopy(base_case)
    validation_case_id = str(spec["validation_case_id"])
    case["case_id"] = f"dewaxing_native_validation_{validation_case_id}"
    case["case_name"] = str(spec.get("case_name") or validation_case_id)
    for edit in spec.get("edits", []):
        _apply_edit(case, edit)
    discretization = _case_discretization(case)
    case_root = root / "cases" / f"{index:02d}_{validation_case_id}"
    native = run_dewaxing_native_solver(case, output_dir=case_root / "native_result", comparison_pack=comparison_pack)
    result_pack = compile_native_result_pack(case_root / "native_result" / "dewaxing_native_status.json", output_dir=case_root / "result_pack")
    pack_validation = validate_result_pack(case_root / "result_pack")
    metrics = native.get("outputs", {}).get("qoi", {}).get("metrics", {})
    comparison = native.get("outputs", {}).get("comparison", {})
    comparison_metrics = comparison.get("metrics", {}) if isinstance(comparison.get("metrics"), dict) else {}
    return {
        "validation_case_id": validation_case_id,
        "target_id": spec.get("target_id"),
        "target_name": spec.get("target_name"),
        "case_variant": spec.get("case_variant"),
        "case_name": spec.get("case_name"),
        "description": spec.get("description"),
        "edits": spec.get("edits", []),
        "discretization": discretization,
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
            "native_report": str(case_root / "native_result" / "dewaxing_native_report.md"),
            "history": str(case_root / "native_result" / "dewaxing_native_history.csv"),
            "final_field": str(case_root / "native_result" / "dewaxing_native_final_field.csv"),
            "result_pack": str(case_root / "result_pack" / "result_pack.json"),
            "decision_brief": str(case_root / "result_pack" / "decision_brief.md"),
        },
    }


def _qoi_stability(cases: list[dict[str, Any]]) -> dict[str, Any]:
    targets = sorted({str(item.get("target_id")) for item in cases if item.get("target_id")})
    target_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for target_id in targets:
        members = [item for item in cases if item.get("target_id") == target_id and item.get("status") == "success"]
        current = _case_by_variant(members, "current") or (members[0] if members else {})
        metric_rows: list[dict[str, Any]] = []
        target_quality = "passed"
        for metric_name in QOI_METRICS:
            row = _metric_stability(metric_name, members, current)
            metric_rows.append(row)
            if row.get("quality_status") == "warning":
                target_quality = "warning"
                warnings.append(f"{target_id}.{metric_name} relative spread {row.get('relative_spread_vs_current')} exceeds threshold {row.get('threshold')}.")
        target_rows.append(
            {
                "target_id": target_id,
                "quality_status": target_quality,
                "case_count": len(members),
                "reference_case_id": current.get("validation_case_id"),
                "metrics": metric_rows,
            }
        )
    return {
        "schema_version": "fastfluent_dewaxing_native_qoi_stability_v1",
        "status": "warning" if warnings else "passed",
        "targets": target_rows,
        "warnings": warnings,
    }


def _metric_stability(metric_name: str, members: list[dict[str, Any]], current: dict[str, Any]) -> dict[str, Any]:
    values = [
        {
            "validation_case_id": item.get("validation_case_id"),
            "case_variant": item.get("case_variant"),
            "value": _maybe_float(item.get("metrics", {}).get(metric_name)),
        }
        for item in members
    ]
    values = [item for item in values if item.get("value") is not None]
    current_value = _maybe_float(current.get("metrics", {}).get(metric_name)) if current else None
    if not values:
        return {
            "metric": metric_name,
            "quality_status": "warning",
            "current_value": current_value,
            "min_value": None,
            "max_value": None,
            "relative_spread_vs_current": None,
            "threshold": STABILITY_THRESHOLDS.get(metric_name),
            "values": [],
        }
    numeric = [float(item["value"]) for item in values]
    min_value = min(numeric)
    max_value = max(numeric)
    spread = max_value - min_value
    threshold = STABILITY_THRESHOLDS.get(metric_name)
    if metric_name == "energy_balance_relative_error":
        relative_spread = max_value
        quality = "warning" if threshold is not None and max_value > threshold else "passed"
    else:
        denom = abs(current_value) if current_value not in {None, 0.0} else max(abs(max_value), 1.0e-12)
        relative_spread = spread / denom
        quality = "warning" if threshold is not None and relative_spread > threshold else "passed"
    return {
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


def _agent_validation_decision(
    cases: list[dict[str, Any]],
    stability: dict[str, Any],
    fluent_validation: dict[str, Any],
) -> dict[str, Any]:
    current_cases = [item for item in cases if item.get("case_variant") == "current"]
    comparisons = sorted([_target_comparison(item) for item in current_cases], key=lambda item: item.get("objective_score", 999.0))
    recommended = comparisons[0] if comparisons else {}
    baseline = next((item for item in comparisons if item.get("target_id") == "baseline"), {})
    warnings: list[str] = []
    if stability.get("status") != "passed":
        warnings.append("At least one reduced-order QoI has larger grid/time-step spread than the current validation threshold.")
    if not fluent_validation.get("passed"):
        warnings.append("The reviewed Fluent comparison pack did not pass validation; use native-only interpretation.")
    improved = False
    if baseline and recommended:
        improved = _float_or(recommended.get("objective_score"), 999.0) < _float_or(baseline.get("objective_score"), 999.0)
    recommendations = [
        "Use the validation pack as FastFluent-native screening evidence before writing Agent claims.",
        f"Use `{recommended.get('target_id')}` as the current FastFluent-guided candidate for dewaxing if its application scope is retained.",
        "Cite grid/time-step stability and comparison errors together; do not cite a single fitted run alone.",
        "Treat shell_thin as an effective thermal-resistance correction until geometry/material evidence justifies a physical shell-thickness claim.",
    ]
    if improved:
        recommendations.append("Report that the FastFluent-native study improved agreement against the reviewed Fluent pack relative to baseline.")
    if stability.get("status") != "passed":
        recommendations.append("Frame full-melt timing as the strongest stable native QoI; keep risk-window and shell-stress proxy claims as screening guidance.")
    return {
        "schema_version": DEWAXING_NATIVE_VALIDATION_DECISION_SCHEMA_VERSION,
        "status": "warning" if warnings else "passed",
        "recommended_target_id": recommended.get("target_id"),
        "recommended_next_action": "use_validation_pack_for_agent_paper_evidence",
        "target_comparison": comparisons,
        "improves_over_baseline": improved,
        "recommendations": recommendations,
        "warnings": warnings,
        "claim_boundary": {
            "can_support_agent_workflow_control": True,
            "can_support_fastfluent_screening_decision": True,
            "can_support_fluent_parameter_prioritization": bool(fluent_validation.get("passed")),
            "can_support_final_cfd_validation": False,
            "can_support_new_fluent_calculation": False,
        },
    }


def _target_comparison(item: dict[str, Any]) -> dict[str, Any]:
    comparison = item.get("comparison_metrics", {}) if isinstance(item.get("comparison_metrics"), dict) else {}
    metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
    full_error = _float_or(comparison.get("full_melt_time_relative_error"), 2.0)
    risk_error = _float_or(comparison.get("dominant_risk_time_relative_error"), 1.0)
    energy_error = _float_or(metrics.get("energy_balance_relative_error"), 0.5)
    objective = round(0.60 * full_error + 0.30 * risk_error + 0.10 * energy_error, 6)
    return {
        "target_id": item.get("target_id"),
        "validation_case_id": item.get("validation_case_id"),
        "objective_score": objective,
        "predicted_full_melt_time_s": metrics.get("predicted_full_melt_time_s"),
        "dominant_risk_time_s": metrics.get("dominant_risk_time_s"),
        "early_max_shell_stress_proxy_MPa": metrics.get("early_max_shell_stress_proxy_MPa"),
        "energy_balance_relative_error": metrics.get("energy_balance_relative_error"),
        "full_melt_time_relative_error": comparison.get("full_melt_time_relative_error"),
        "dominant_risk_time_relative_error": comparison.get("dominant_risk_time_relative_error"),
    }


def _paper_tables_markdown(pack: dict[str, Any]) -> str:
    cases = pack.get("cases", []) if isinstance(pack.get("cases"), list) else []
    decision = pack.get("agent_validation_decision", {}) if isinstance(pack.get("agent_validation_decision"), dict) else {}
    stability = pack.get("qoi_stability", {}) if isinstance(pack.get("qoi_stability"), dict) else {}
    current_rows = [item for item in cases if item.get("case_variant") == "current"]
    lines = [
        "# Paper Tables: FastFluent Dewaxing Native Validation",
        "",
        "## Table 1. Current Native Candidates Against Reviewed Fluent Pack",
        "",
        _markdown_table(
            [
                "target",
                "full melt s",
                "full melt rel error",
                "risk time s",
                "risk rel error",
                "energy error",
                "early stress proxy MPa",
            ],
            [
                [
                    item.get("target_id"),
                    _format_value(item.get("metrics", {}).get("predicted_full_melt_time_s")),
                    _format_value(item.get("comparison_metrics", {}).get("full_melt_time_relative_error")),
                    _format_value(item.get("metrics", {}).get("dominant_risk_time_s")),
                    _format_value(item.get("comparison_metrics", {}).get("dominant_risk_time_relative_error")),
                    _format_value(item.get("metrics", {}).get("energy_balance_relative_error")),
                    _format_value(item.get("metrics", {}).get("early_max_shell_stress_proxy_MPa")),
                ]
                for item in current_rows
            ],
        ),
        "",
        "## Table 2. Validation Matrix",
        "",
        _markdown_table(
            ["case", "target", "variant", "nx", "ny", "dt s", "shell columns", "cell-time steps"],
            [
                [
                    item.get("validation_case_id"),
                    item.get("target_id"),
                    item.get("case_variant"),
                    item.get("discretization", {}).get("nx"),
                    item.get("discretization", {}).get("ny"),
                    _format_value(item.get("discretization", {}).get("time_step_s")),
                    item.get("discretization", {}).get("shell_columns"),
                    int(_float_or(item.get("metrics", {}).get("grid_cells"), 0.0))
                    * int(_float_or(item.get("metrics", {}).get("time_steps"), 0.0)),
                ]
                for item in cases
            ],
        ),
        "",
        "## Table 3. Grid/Time-Step Stability",
        "",
    ]
    stability_rows: list[list[Any]] = []
    for target in stability.get("targets", []):
        for metric in target.get("metrics", []):
            stability_rows.append(
                [
                    target.get("target_id"),
                    metric.get("metric"),
                    metric.get("quality_status"),
                    _format_value(metric.get("current_value")),
                    _format_value(metric.get("min_value")),
                    _format_value(metric.get("max_value")),
                    _format_value(metric.get("relative_spread_vs_current")),
                ]
            )
    lines.extend(
        [
            _markdown_table(
                ["target", "metric", "quality", "current", "min", "max", "rel spread"],
                stability_rows,
            ),
            "",
            "## Table 4. Agent Application Claim Map",
            "",
            _markdown_table(
                ["claim", "value"],
                [
                    ["recommended target", decision.get("recommended_target_id")],
                    ["new Fluent calculation", pack.get("execution_boundary", {}).get("new_fluent_calculation")],
                    ["native solver runs", pack.get("execution_boundary", {}).get("native_dewaxing_solver_runs")],
                    ["native cell-time steps", pack.get("execution_boundary", {}).get("native_cell_time_steps")],
                    ["supports screening decision", decision.get("claim_boundary", {}).get("can_support_fastfluent_screening_decision")],
                    ["supports final CFD validation", decision.get("claim_boundary", {}).get("can_support_final_cfd_validation")],
                ],
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _study_interpretation_markdown(pack: dict[str, Any]) -> str:
    decision = pack.get("agent_validation_decision", {}) if isinstance(pack.get("agent_validation_decision"), dict) else {}
    lines = [
        "# Study Interpretation",
        "",
        "The validation pack turns the FastFluent-native dewaxing solver into an agent-facing computational gate. "
        "The Agent is no longer only reading reviewed Fluent postprocessing artifacts; it can run a reduced-order thermal phase-change model, "
        "compare candidate assumptions against the reviewed Fluent Result Pack, and require grid/time-step stability before accepting a candidate.",
        "",
        f"The current recommended target is `{decision.get('recommended_target_id')}`. "
        "This target should be described as an effective thermal-resistance correction produced by the FastFluent-native study. "
        "It should not be described as a measured shell-thickness change unless independent geometry or material evidence is added.",
        "",
        "For the paper, the defensible claim is that FastFluent supplies a hard intermediate computation for agent guidance: "
        "it screens dewaxing assumptions, identifies the candidate that best matches reviewed Fluent timing evidence, "
        "checks numerical stability of the reduced-order result, and writes a bounded handoff for later high-fidelity CFD or experiment.",
        "",
        "The pack intentionally keeps the final CFD application scope explicit. It does not replace Fluent pressure fields, VOF reconstruction, or final CFD validation. "
        "Its role is to make the Agent's dewaxing decision auditable and computational rather than prompt-only.",
        "",
        "## Recommended Paper Use",
        "",
    ]
    lines.extend(f"- {item}" for item in decision.get("recommendations", []))
    lines.extend(["", "## Application Scope", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _case_csv_row(item: dict[str, Any]) -> dict[str, Any]:
    metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
    comparison = item.get("comparison_metrics", {}) if isinstance(item.get("comparison_metrics"), dict) else {}
    discretization = item.get("discretization", {}) if isinstance(item.get("discretization"), dict) else {}
    return {
        "validation_case_id": item.get("validation_case_id"),
        "target_id": item.get("target_id"),
        "case_variant": item.get("case_variant"),
        "status": item.get("status"),
        "quality_status": item.get("quality_status"),
        "nx": discretization.get("nx"),
        "ny": discretization.get("ny"),
        "time_step_s": discretization.get("time_step_s"),
        "shell_columns": discretization.get("shell_columns"),
        "shell_thickness_m": discretization.get("shell_thickness_m"),
        "grid_cells": metrics.get("grid_cells"),
        "time_steps": metrics.get("time_steps"),
        "predicted_full_melt_time_s": metrics.get("predicted_full_melt_time_s"),
        "dominant_risk_time_s": metrics.get("dominant_risk_time_s"),
        "early_max_shell_stress_proxy_MPa": metrics.get("early_max_shell_stress_proxy_MPa"),
        "peak_pressure_risk_proxy": metrics.get("peak_pressure_risk_proxy"),
        "energy_balance_relative_error": metrics.get("energy_balance_relative_error"),
        "full_melt_time_relative_error": comparison.get("full_melt_time_relative_error"),
        "dominant_risk_time_relative_error": comparison.get("dominant_risk_time_relative_error"),
    }


def _validate_reference_pack(comparison_pack: str | Path | None) -> dict[str, Any]:
    if comparison_pack is None or str(comparison_pack).strip() == "":
        return {"status": "skipped", "passed": False, "warnings": ["No Fluent comparison pack supplied."], "errors": []}
    return validate_dewaxing_result_pack(comparison_pack)


def _case_spec(case_variant: str, description: str, edits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "case_variant": case_variant,
        "case_name": description,
        "description": description,
        "edits": edits,
    }


def _target_spec(target_id: str, target_name: str, edits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "target_id": target_id,
        "target_name": target_name,
        "edits": edits,
    }


def _apply_edit(case: dict[str, Any], edit: dict[str, Any]) -> None:
    target = case
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
        raise ValueError(f"Unsupported validation edit operation: {operation}")


def _case_discretization(case: dict[str, Any]) -> dict[str, Any]:
    domain = case.get("domain", {}) if isinstance(case.get("domain"), dict) else {}
    time = case.get("time", {}) if isinstance(case.get("time"), dict) else {}
    nx = int(domain.get("nx", 0))
    ny = int(domain.get("ny", 0))
    thickness = _float_or(domain.get("thickness_m"), 0.0)
    shell_thickness = _float_or(domain.get("shell_thickness_m"), 0.0)
    dx = thickness / nx if nx else None
    shell_columns = int(math.ceil(shell_thickness / dx)) if dx else None
    return {
        "nx": nx,
        "ny": ny,
        "grid_cells": nx * ny,
        "time_step_s": time.get("time_step_s"),
        "final_time_s": time.get("final_time_s"),
        "thickness_m": thickness,
        "shell_thickness_m": shell_thickness,
        "dx_m": dx,
        "shell_columns": shell_columns,
    }


def _case_by_variant(cases: list[dict[str, Any]], case_variant: str) -> dict[str, Any] | None:
    for item in cases:
        if item.get("case_variant") == case_variant:
            return item
    return None


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_format_cell(item) for item in row) + " |" for row in rows]
    if not body:
        body = ["| " + " | ".join("" for _ in headers) + " |"]
    return "\n".join([header, divider] + body)


def _format_cell(value: Any) -> str:
    text = _format_value(value)
    return str(text).replace("|", "\\|")


def _format_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    parsed = _maybe_float(value)
    if parsed is None or not math.isfinite(parsed):
        return value
    if abs(parsed) >= 100.0:
        return f"{parsed:.3f}"
    if abs(parsed) >= 1.0:
        return f"{parsed:.6f}"
    return f"{parsed:.6g}"


def _maybe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_or(value: Any, fallback: float = 0.0) -> float:
    parsed = _maybe_float(value)
    return fallback if parsed is None else parsed
