"""FastFluent-native dewaxing study pack.

The study runner executes an ensemble of reduced-order native dewaxing solver
variants, compares them with a reviewed Fluent dewaxing Result Pack when
supplied, and writes agent guidance for parameter sensitivity and follow-up
focus. It does not launch Fluent.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .dewaxing_native_solver import demo_dewaxing_native_case, run_dewaxing_native_solver
from .file_io import ensure_dir, write_json_file, write_text_file
from .practical_native_artifacts import write_csv
from .result_pack import compile_native_result_pack, validate_result_pack


DEWAXING_NATIVE_STUDY_SCHEMA_VERSION = "fastfluent_dewaxing_native_study_v1"
DEWAXING_NATIVE_GUIDANCE_SCHEMA_VERSION = "fastfluent_dewaxing_native_guidance_v1"


LIMITATIONS = [
    "This study uses the FastFluent-native reduced-order dewaxing solver only.",
    "It does not launch Fluent, PyFluent, UDFs, or arbitrary solver scripts.",
    "It does not edit Fluent case/data files.",
    "Parameter sensitivity is local to the public reduced-order model and chosen sweep bounds.",
    "The guidance supports screening and study design, not final CFD validation.",
]


def default_dewaxing_native_study_plan() -> list[dict[str, Any]]:
    """Return the default one-at-a-time dewaxing study plan."""

    return [
        _variant("baseline", "Baseline native solver", "Reference reduced-order case.", []),
        _scale_variant("htc_low", "Lower heat-transfer coefficient", "steam_boundary.heat_transfer_coefficient_W_m2K", 0.80),
        _scale_variant("htc_high", "Higher heat-transfer coefficient", "steam_boundary.heat_transfer_coefficient_W_m2K", 1.20),
        _offset_variant("steam_temp_low", "Lower steam temperature", "steam_boundary.temperature_K", -10.0),
        _offset_variant("steam_temp_high", "Higher steam temperature", "steam_boundary.temperature_K", 10.0),
        _scale_variant("latent_low", "Lower wax latent heat", "wax.latent_heat_J_kg", 0.85),
        _scale_variant("latent_high", "Higher wax latent heat", "wax.latent_heat_J_kg", 1.15),
        _multi_scale_variant(
            "wax_k_low",
            "Lower wax thermal conductivity",
            ["wax.thermal_conductivity_solid_W_mK", "wax.thermal_conductivity_liquid_W_mK"],
            0.80,
        ),
        _multi_scale_variant(
            "wax_k_high",
            "Higher wax thermal conductivity",
            ["wax.thermal_conductivity_solid_W_mK", "wax.thermal_conductivity_liquid_W_mK"],
            1.20,
        ),
        _scale_variant("shell_thin", "Thinner shell", "domain.shell_thickness_m", 0.80),
        _scale_variant("shell_thick", "Thicker shell", "domain.shell_thickness_m", 1.20),
        _scale_variant("wax_layer_thin", "Thinner total thermal path", "domain.thickness_m", 0.92),
        _scale_variant("wax_layer_thick", "Thicker total thermal path", "domain.thickness_m", 1.08),
        _offset_variant("initial_temp_low", "Lower initial temperature", "initial.temperature_K", -5.0),
        _offset_variant("initial_temp_high", "Higher initial temperature", "initial.temperature_K", 5.0),
    ]


def run_dewaxing_native_study(
    *,
    output_dir: str | Path,
    comparison_pack: str | Path | None = None,
    max_variants: int | None = None,
    study_plan: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run a parameter study with the native dewaxing reduced-order solver."""

    root = Path(output_dir)
    ensure_dir(root)
    plan = list(study_plan or default_dewaxing_native_study_plan())
    if max_variants is not None:
        plan = plan[: max(1, int(max_variants))]
    artifacts = {
        "study_manifest": str(root / "study_manifest.json"),
        "variant_summary_csv": str(root / "variant_summary.csv"),
        "variant_summary_json": str(root / "variant_summary.json"),
        "sensitivity_summary": str(root / "sensitivity_summary.json"),
        "dewaxing_guidance": str(root / "dewaxing_guidance.json"),
        "study_report": str(root / "study_report.md"),
    }
    base_case = demo_dewaxing_native_case()
    variants: list[dict[str, Any]] = []
    for index, spec in enumerate(plan):
        variant = _run_variant(index, spec, base_case, root=root, comparison_pack=comparison_pack)
        variants.append(variant)
    baseline = _find_variant(variants, "baseline") or variants[0]
    sensitivity = _sensitivity_summary(variants, baseline)
    guidance = _guidance(variants, baseline, sensitivity, comparison_pack=comparison_pack)
    status = "failed" if any(item.get("status") == "failed" for item in variants) else "success"
    manifest = {
        "schema_version": DEWAXING_NATIVE_STUDY_SCHEMA_VERSION,
        "status": status,
        "case_id": "dewaxing_native_study",
        "variant_count": len(variants),
        "comparison_pack": str(comparison_pack) if comparison_pack else None,
        "baseline_variant_id": baseline.get("variant_id"),
        "variants": variants,
        "sensitivity_summary": sensitivity,
        "guidance": guidance,
        "artifacts": artifacts,
        "execution_boundary": {
            "new_fluent_calculation": False,
            "fluent_launched": False,
            "fluent_case_or_data_edited": False,
            "native_dewaxing_solver_runs": len(variants),
        },
        "limitations": list(LIMITATIONS),
    }
    write_json_file(root / "study_manifest.json", manifest)
    write_json_file(root / "variant_summary.json", variants)
    write_csv(root / "variant_summary.csv", [_variant_csv_row(item) for item in variants])
    write_json_file(root / "sensitivity_summary.json", sensitivity)
    write_json_file(root / "dewaxing_guidance.json", guidance)
    write_text_file(root / "study_report.md", dewaxing_native_study_markdown(manifest))
    return manifest


def dewaxing_native_study_markdown(study: dict[str, Any]) -> str:
    """Render a concise Markdown report for the study pack."""

    guidance = study.get("guidance", {}) if isinstance(study.get("guidance"), dict) else {}
    best = guidance.get("best_match_variant", {}) if isinstance(guidance.get("best_match_variant"), dict) else {}
    lines = [
        "# FastFluent Dewaxing Native Study",
        "",
        f"- Status: `{study.get('status')}`",
        f"- Variant count: `{study.get('variant_count')}`",
        f"- New Fluent calculation: `{study.get('execution_boundary', {}).get('new_fluent_calculation')}`",
        f"- Best match: `{best.get('variant_id')}`",
        f"- Best score: `{best.get('objective_score')}`",
        "",
        "## Agent Guidance",
        "",
    ]
    for item in guidance.get("recommendations", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Top Variants", ""])
    for item in guidance.get("top_ranked_variants", [])[:5]:
        lines.append(
            f"- `{item.get('variant_id')}` score `{item.get('objective_score')}`, "
            f"full melt `{item.get('predicted_full_melt_time_s')}`, "
            f"risk time `{item.get('dominant_risk_time_s')}`"
        )
    lines.extend(["", "## Dominant Sensitivities", ""])
    sens = study.get("sensitivity_summary", {}) if isinstance(study.get("sensitivity_summary"), dict) else {}
    for metric_name, entries in sorted(sens.get("top_by_metric", {}).items()):
        if entries:
            top = entries[0]
            lines.append(f"- `{metric_name}`: `{top.get('parameter_group')}` sensitivity `{top.get('relative_sensitivity')}`")
    lines.extend(["", "## Application Scope", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _run_variant(
    index: int,
    spec: dict[str, Any],
    base_case: dict[str, Any],
    *,
    root: Path,
    comparison_pack: str | Path | None,
) -> dict[str, Any]:
    case = deepcopy(base_case)
    variant_id = str(spec["variant_id"])
    case["case_id"] = f"dewaxing_native_{variant_id}"
    case["case_name"] = str(spec.get("name") or variant_id)
    for edit in spec.get("edits", []):
        _apply_edit(case, edit)
    variant_root = root / "variants" / f"{index:02d}_{variant_id}"
    native = run_dewaxing_native_solver(case, output_dir=variant_root / "native_result", comparison_pack=comparison_pack)
    result_pack = compile_native_result_pack(variant_root / "native_result" / "dewaxing_native_status.json", output_dir=variant_root / "result_pack")
    pack_validation = validate_result_pack(variant_root / "result_pack")
    metrics = native.get("outputs", {}).get("qoi", {}).get("metrics", {})
    comparison = native.get("outputs", {}).get("comparison", {})
    comparison_metrics = comparison.get("metrics", {}) if isinstance(comparison.get("metrics"), dict) else {}
    objective = _objective_score(metrics, comparison_metrics)
    return {
        "variant_id": variant_id,
        "name": spec.get("name"),
        "description": spec.get("description"),
        "parameter_group": spec.get("parameter_group"),
        "representative_factor": spec.get("representative_factor"),
        "edits": spec.get("edits", []),
        "status": native.get("status"),
        "quality_status": native.get("quality_status"),
        "result_pack_status": result_pack.get("status"),
        "result_pack_validation_status": pack_validation.get("status"),
        "objective_score": objective,
        "metrics": metrics,
        "comparison_metrics": comparison_metrics,
        "warnings": native.get("warnings", []) + pack_validation.get("warnings", []),
        "blocking_errors": native.get("blocking_errors", []) + pack_validation.get("errors", []),
        "artifacts": {
            "native_result": str(variant_root / "native_result" / "dewaxing_native_status.json"),
            "native_report": str(variant_root / "native_result" / "dewaxing_native_report.md"),
            "history": str(variant_root / "native_result" / "dewaxing_native_history.csv"),
            "final_field": str(variant_root / "native_result" / "dewaxing_native_final_field.csv"),
            "result_pack": str(variant_root / "result_pack" / "result_pack.json"),
        },
    }


def _objective_score(metrics: dict[str, Any], comparison_metrics: dict[str, Any]) -> float:
    full_error = _float_or(comparison_metrics.get("full_melt_time_relative_error"), 2.0)
    risk_error = _float_or(comparison_metrics.get("dominant_risk_time_relative_error"), 1.0)
    energy_error = _float_or(metrics.get("energy_balance_relative_error"), 0.5)
    final_lf_gap = abs(1.0 - _float_or(metrics.get("final_avg_liquid_fraction"), 0.0))
    no_melt_penalty = 1.0 if metrics.get("full_melt_reached") is not True else 0.0
    return round(0.55 * full_error + 0.25 * risk_error + 0.10 * energy_error + 0.05 * final_lf_gap + 0.05 * no_melt_penalty, 6)


def _sensitivity_summary(variants: list[dict[str, Any]], baseline: dict[str, Any]) -> dict[str, Any]:
    groups = sorted({str(item.get("parameter_group")) for item in variants if item.get("parameter_group") and item.get("variant_id") != "baseline"})
    metrics = [
        "predicted_full_melt_time_s",
        "dominant_risk_time_s",
        "early_max_shell_stress_proxy_MPa",
        "peak_pressure_risk_proxy",
    ]
    rows: list[dict[str, Any]] = []
    for group in groups:
        members = [item for item in variants if item.get("parameter_group") == group]
        low = _member_with_factor(members, prefer_low=True)
        high = _member_with_factor(members, prefer_low=False)
        if not low or not high:
            continue
        f_low = _float_or(low.get("representative_factor"), 1.0)
        f_high = _float_or(high.get("representative_factor"), 1.0)
        factor_span = abs(f_high - f_low)
        for metric_name in metrics:
            y_low = _maybe_float(low.get("metrics", {}).get(metric_name))
            y_high = _maybe_float(high.get("metrics", {}).get(metric_name))
            y_base = _maybe_float(baseline.get("metrics", {}).get(metric_name))
            if y_low is None or y_high is None or y_base in {None, 0.0} or factor_span == 0.0:
                continue
            sensitivity = abs(y_high - y_low) / abs(y_base) / factor_span
            rows.append(
                {
                    "parameter_group": group,
                    "metric": metric_name,
                    "low_variant": low.get("variant_id"),
                    "high_variant": high.get("variant_id"),
                    "low_value": y_low,
                    "high_value": y_high,
                    "baseline_value": y_base,
                    "relative_sensitivity": sensitivity,
                }
            )
    top_by_metric: dict[str, list[dict[str, Any]]] = {}
    for metric_name in metrics:
        top_by_metric[metric_name] = sorted([row for row in rows if row["metric"] == metric_name], key=lambda item: item["relative_sensitivity"], reverse=True)
    return {
        "schema_version": "fastfluent_dewaxing_native_sensitivity_v1",
        "rows": rows,
        "top_by_metric": top_by_metric,
    }


def _guidance(
    variants: list[dict[str, Any]],
    baseline: dict[str, Any],
    sensitivity: dict[str, Any],
    *,
    comparison_pack: str | Path | None,
) -> dict[str, Any]:
    ranked = sorted(variants, key=lambda item: item.get("objective_score", 999.0))
    best = ranked[0] if ranked else {}
    full_ranked = sorted(variants, key=lambda item: _float_or(item.get("comparison_metrics", {}).get("full_melt_time_relative_error"), 999.0))
    risk_ranked = sorted(variants, key=lambda item: _float_or(item.get("comparison_metrics", {}).get("dominant_risk_time_relative_error"), 999.0))
    stress_ranked = sorted(variants, key=lambda item: _float_or(item.get("metrics", {}).get("early_max_shell_stress_proxy_MPa"), 999.0))
    fastest = sorted(variants, key=lambda item: _float_or(item.get("metrics", {}).get("predicted_full_melt_time_s"), 999999.0))
    recommendations = _recommendations(best, baseline, sensitivity, comparison_pack=comparison_pack)
    rejected = [
        _compact_variant(item)
        for item in variants
        if item.get("status") != "success"
        or item.get("metrics", {}).get("full_melt_reached") is not True
        or _float_or(item.get("objective_score"), 0.0) > 0.55
    ]
    return {
        "schema_version": DEWAXING_NATIVE_GUIDANCE_SCHEMA_VERSION,
        "status": "success",
        "best_match_variant": _compact_variant(best),
        "closest_full_melt_variant": _compact_variant(full_ranked[0]) if full_ranked else {},
        "closest_risk_window_variant": _compact_variant(risk_ranked[0]) if risk_ranked else {},
        "lowest_early_stress_variant": _compact_variant(stress_ranked[0]) if stress_ranked else {},
        "fastest_full_melt_variant": _compact_variant(fastest[0]) if fastest else {},
        "top_ranked_variants": [_compact_variant(item) for item in ranked[:5]],
        "rejected_variants": rejected,
        "recommendations": recommendations,
        "claim_boundary": {
            "can_support_agent_workflow_control": True,
            "can_support_fastfluent_screening_decision": True,
            "can_support_fluent_parameter_prioritization": comparison_pack is not None,
            "can_support_final_cfd_validation": False,
            "can_support_new_fluent_calculation": False,
        },
    }


def _recommendations(
    best: dict[str, Any],
    baseline: dict[str, Any],
    sensitivity: dict[str, Any],
    *,
    comparison_pack: str | Path | None,
) -> list[str]:
    recommendations = [
        f"Use `{best.get('variant_id')}` as the best reduced-order agreement case for the current study pack.",
        "Use the native study to bracket reduced-order uncertainty before interpreting the reviewed Fluent result pack.",
    ]
    top = sensitivity.get("top_by_metric", {}) if isinstance(sensitivity.get("top_by_metric"), dict) else {}
    full_top = (top.get("predicted_full_melt_time_s") or [{}])[0]
    risk_top = (top.get("dominant_risk_time_s") or [{}])[0]
    stress_top = (top.get("early_max_shell_stress_proxy_MPa") or [{}])[0]
    if full_top.get("parameter_group"):
        recommendations.append(f"Full-melt timing is most sensitive to `{full_top.get('parameter_group')}` in this sweep.")
    if risk_top.get("parameter_group"):
        recommendations.append(f"The reduced-order risk-window timing is most sensitive to `{risk_top.get('parameter_group')}`.")
    if stress_top.get("parameter_group"):
        recommendations.append(f"Early thermal-shock stress proxy is most sensitive to `{stress_top.get('parameter_group')}`.")
    baseline_error = baseline.get("comparison_metrics", {}).get("full_melt_time_relative_error")
    best_error = best.get("comparison_metrics", {}).get("full_melt_time_relative_error")
    if baseline_error is not None and best_error is not None and best_error < baseline_error:
        recommendations.append(
            f"The study improves full-melt agreement from baseline relative error `{baseline_error}` to `{best_error}`."
        )
    if comparison_pack is None:
        recommendations.append("No Fluent comparison pack was supplied; rank variants by native QoI only before making Fluent-facing claims.")
    recommendations.append("Do not treat reduced-order pressure-risk proxy as Fluent pressure or calibrated crack probability.")
    return recommendations


def _variant_csv_row(item: dict[str, Any]) -> dict[str, Any]:
    metrics = item.get("metrics", {})
    comparison = item.get("comparison_metrics", {})
    return {
        "variant_id": item.get("variant_id"),
        "parameter_group": item.get("parameter_group"),
        "representative_factor": item.get("representative_factor"),
        "status": item.get("status"),
        "quality_status": item.get("quality_status"),
        "objective_score": item.get("objective_score"),
        "predicted_full_melt_time_s": metrics.get("predicted_full_melt_time_s"),
        "dominant_risk_time_s": metrics.get("dominant_risk_time_s"),
        "early_max_shell_stress_proxy_MPa": metrics.get("early_max_shell_stress_proxy_MPa"),
        "peak_pressure_risk_proxy": metrics.get("peak_pressure_risk_proxy"),
        "final_avg_liquid_fraction": metrics.get("final_avg_liquid_fraction"),
        "energy_balance_relative_error": metrics.get("energy_balance_relative_error"),
        "full_melt_time_relative_error": comparison.get("full_melt_time_relative_error"),
        "dominant_risk_time_relative_error": comparison.get("dominant_risk_time_relative_error"),
    }


def _compact_variant(item: dict[str, Any]) -> dict[str, Any]:
    metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
    comparison = item.get("comparison_metrics", {}) if isinstance(item.get("comparison_metrics"), dict) else {}
    return {
        "variant_id": item.get("variant_id"),
        "name": item.get("name"),
        "parameter_group": item.get("parameter_group"),
        "objective_score": item.get("objective_score"),
        "quality_status": item.get("quality_status"),
        "predicted_full_melt_time_s": metrics.get("predicted_full_melt_time_s"),
        "dominant_risk_time_s": metrics.get("dominant_risk_time_s"),
        "early_max_shell_stress_proxy_MPa": metrics.get("early_max_shell_stress_proxy_MPa"),
        "full_melt_time_relative_error": comparison.get("full_melt_time_relative_error"),
        "dominant_risk_time_relative_error": comparison.get("dominant_risk_time_relative_error"),
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
        raise ValueError(f"Unsupported study edit operation: {operation}")


def _variant(variant_id: str, name: str, description: str, edits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "variant_id": variant_id,
        "name": name,
        "description": description,
        "parameter_group": None,
        "representative_factor": 1.0,
        "edits": edits,
    }


def _scale_variant(variant_id: str, name: str, path: str, factor: float) -> dict[str, Any]:
    group = path.split(".")[-1]
    return {
        "variant_id": variant_id,
        "name": name,
        "description": f"Scale {path} by {factor}.",
        "parameter_group": group,
        "representative_factor": factor,
        "edits": [{"path": path, "operation": "scale", "value": factor}],
    }


def _multi_scale_variant(variant_id: str, name: str, paths: list[str], factor: float) -> dict[str, Any]:
    return {
        "variant_id": variant_id,
        "name": name,
        "description": f"Scale {', '.join(paths)} by {factor}.",
        "parameter_group": "wax_thermal_conductivity",
        "representative_factor": factor,
        "edits": [{"path": path, "operation": "scale", "value": factor} for path in paths],
    }


def _offset_variant(variant_id: str, name: str, path: str, offset: float) -> dict[str, Any]:
    group = path.replace(".", "_")
    base = _get_path(demo_dewaxing_native_case(), path)
    factor = (float(base) + offset) / float(base)
    return {
        "variant_id": variant_id,
        "name": name,
        "description": f"Offset {path} by {offset}.",
        "parameter_group": group,
        "representative_factor": factor,
        "edits": [{"path": path, "operation": "offset", "value": offset}],
    }


def _get_path(case: dict[str, Any], path: str) -> Any:
    target: Any = case
    for key in path.split("."):
        target = target[key]
    return target


def _find_variant(variants: list[dict[str, Any]], variant_id: str) -> dict[str, Any] | None:
    for item in variants:
        if item.get("variant_id") == variant_id:
            return item
    return None


def _member_with_factor(members: list[dict[str, Any]], *, prefer_low: bool) -> dict[str, Any] | None:
    if not members:
        return None
    return sorted(members, key=lambda item: _float_or(item.get("representative_factor"), 1.0), reverse=not prefer_low)[0]


def _maybe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_or(value: Any, fallback: float = 0.0) -> float:
    parsed = _maybe_float(value)
    return fallback if parsed is None else parsed
