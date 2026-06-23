"""Practical material-property field utilities for FastFluent S2."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .practical_native_artifacts import (
    LIMITATIONS,
    build_practical_native_result,
    write_csv,
    write_json,
    write_practical_native_result,
    write_text,
)


def demo_arrhenius_viscosity_field_case() -> dict[str, Any]:
    return {
        "case_id": "arrhenius_viscosity_field_demo",
        "case_name": "Public Arrhenius Viscosity Field Demo",
        "property_name": "dynamic_viscosity",
        "property_model": "arrhenius",
        "arrhenius_A": -46.7601,
        "arrhenius_B_K": 16488.4,
        "temperature_min_K": 353.15,
        "temperature_max_K": 373.15,
        "fit_temperature_min_K": 330.0,
        "fit_temperature_max_K": 390.0,
        "nx": 41,
        "length_m": 0.02,
    }


def run_arrhenius_viscosity_field_demo(output_dir: str | Path = "arrhenius_viscosity_field", case: dict[str, Any] | None = None) -> dict[str, Any]:
    return run_property_field_case(case or demo_arrhenius_viscosity_field_case(), output_dir)


def run_property_field_case(case: dict[str, Any], output_dir: str | Path = "property_field") -> dict[str, Any]:
    payload = dict(case)
    target = Path(output_dir)
    nx = int(payload.get("nx", 41))
    length = float(payload.get("length_m", 1.0))
    x = [i * length / (nx - 1) for i in range(nx)]
    temperatures = _temperature_field(payload, nx)
    values = [evaluate_property_value(temp, payload) for temp in temperatures]
    summary = property_field_summary(values, temperatures, payload)
    rows = [
        {"x_m": x_value, "temperature_K": temp, "property_value": value}
        for x_value, temp, value in zip(x, temperatures, values)
    ]
    status = "pass"
    warnings: list[str] = []
    blocking_errors: list[str] = []
    if summary["nonfinite_count"] or summary["negative_value_count"]:
        status = "block"
        blocking_errors.append("Property field contains nonfinite or negative values.")
    elif summary["outside_fit_range_count"]:
        status = "warn"
        warnings.append("Some temperature samples are outside the declared property fit range.")
    case_path = write_json(target / "input_case.json", payload)
    field_path = write_csv(target / "viscosity_field.csv" if payload.get("property_name") == "dynamic_viscosity" else "property_field.csv", rows)
    summary_path = write_json(target / "property_field_summary.json", summary)
    result = build_practical_native_result(
        case_id=str(payload.get("case_id", "property_field_case")),
        case_name=str(payload.get("case_name", "Property Field Case")),
        module="practical_material_properties",
        kernel=str(payload.get("property_model", "unknown")),
        status=status,
        input_summary={"case_file": str(case_path), "property_name": payload.get("property_name")},
        grid_summary={"dimension": 1, "nx": nx, "length_m": length},
        time_summary={"steady_field_evaluation": True},
        stability_summary={"stability_flag": "not_applicable_property_evaluation"},
        qoi_summary=summary,
        field_outputs=[{"path": str(field_path), "kind": "property_field_csv"}],
        history_outputs=[],
        benchmark_comparison={"reference_type": "direct_formula_evaluation", "l2_error": 0.0, "max_error": 0.0},
        warnings=warnings,
        blocking_errors=blocking_errors,
        limitations=LIMITATIONS + ["Property fields are native evaluators, not Fluent material cards."],
        metadata={"property_field_summary": str(summary_path)},
    )
    write_practical_native_result(result, target)
    write_text(target / "simulation_summary.md", _property_summary_markdown(result))
    return result


def evaluate_property_value(temperature_K: float, case: dict[str, Any]) -> float:
    model = str(case.get("property_model", "constant"))
    if model == "constant":
        return float(case["constant_value"])
    if model == "linear":
        reference_temperature = float(case.get("reference_temperature_K", case.get("temperature_min_K", temperature_K)))
        reference_value = float(case["reference_value"])
        slope = float(case.get("slope_per_K", 0.0))
        return reference_value + slope * (temperature_K - reference_temperature)
    if model == "piecewise_linear":
        points = sorted((float(item["temperature_K"]), float(item["value"])) for item in case.get("points", []))
        if not points:
            raise ValueError("piecewise_linear requires points.")
        if temperature_K <= points[0][0]:
            return points[0][1]
        if temperature_K >= points[-1][0]:
            return points[-1][1]
        for (t0, v0), (t1, v1) in zip(points[:-1], points[1:]):
            if t0 <= temperature_K <= t1:
                weight = (temperature_K - t0) / (t1 - t0)
                return v0 + weight * (v1 - v0)
    if model == "arrhenius":
        value = math.exp(float(case["arrhenius_A"]) + float(case["arrhenius_B_K"]) / float(temperature_K))
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("Arrhenius property value must be finite and positive.")
        return value
    raise ValueError(f"Unsupported property_model: {model}")


def property_field_summary(values: list[float], temperatures: list[float], case: dict[str, Any]) -> dict[str, Any]:
    finite_values = [value for value in values if math.isfinite(value)]
    nonfinite_count = len(values) - len(finite_values)
    negative_value_count = sum(1 for value in finite_values if value < 0.0)
    prop_min = min(finite_values) if finite_values else math.nan
    prop_max = max(finite_values) if finite_values else math.nan
    ratio = math.inf if prop_min == 0 else prop_max / prop_min
    fit_min = case.get("fit_temperature_min_K")
    fit_max = case.get("fit_temperature_max_K")
    outside_fit = 0
    if fit_min is not None and fit_max is not None:
        outside_fit = sum(1 for temp in temperatures if temp < float(fit_min) or temp > float(fit_max))
    gradient_proxy = max(abs(values[i + 1] - values[i]) for i in range(len(values) - 1)) if len(values) > 1 else 0.0
    return {
        "property_name": case.get("property_name", "property"),
        "property_model": case.get("property_model", "unknown"),
        "property_min": prop_min,
        "property_max": prop_max,
        "property_ratio": ratio,
        "property_gradient_proxy": gradient_proxy,
        "nonfinite_count": nonfinite_count,
        "negative_value_count": negative_value_count,
        "outside_fit_range_count": outside_fit,
        "sample_count": len(values),
    }


def _temperature_field(case: dict[str, Any], nx: int) -> list[float]:
    if isinstance(case.get("temperature_field_K"), list):
        return [float(value) for value in case["temperature_field_K"]]
    t_min = float(case.get("temperature_min_K", 300.0))
    t_max = float(case.get("temperature_max_K", 350.0))
    return [t_min + (t_max - t_min) * i / (nx - 1) for i in range(nx)]


def _property_summary_markdown(result: dict[str, Any]) -> str:
    qoi = result["qoi_summary"]
    return "\n".join(
        [
            f"# {result['case_name']}",
            "",
            f"- Status: `{result['status']}`",
            f"- Property model: `{qoi.get('property_model')}`",
            f"- Property min/max: `{qoi.get('property_min')}` / `{qoi.get('property_max')}`",
            f"- Property ratio: `{qoi.get('property_ratio')}`",
            f"- Outside fit range count: `{qoi.get('outside_fit_range_count')}`",
            "",
            "This is a native property-field evaluator. It does not generate Fluent material code.",
            "",
        ]
    )
