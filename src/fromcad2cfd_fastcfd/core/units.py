"""Unit and dimension checks for FastFluent CaseSpec-style inputs."""

from __future__ import annotations

from math import isfinite
from typing import Any


UNIT_CHECK_SCHEMA_VERSION = "fastfluent_unit_check_v1"

UNIT_SUFFIXES = {
    "_m": "m",
    "_mm": "mm",
    "_s": "s",
    "_kg_m3": "kg/m^3",
    "_pa_s": "Pa*s",
    "_pa": "Pa",
    "_m_s": "m/s",
    "_w_m_k": "W/(m*K)",
    "_j_kg_k": "J/(kg*K)",
    "_k": "K",
}
POSITIVE_SUFFIXES = {
    "_m",
    "_mm",
    "_s",
    "_kg_m3",
    "_pa_s",
    "_w_m_k",
    "_j_kg_k",
    "_k",
}


def validate_unit_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate unit-bearing scalar and vector values in a nested payload."""

    errors: list[str] = []
    warnings: list[str] = []
    checked: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return {
            "schema_version": UNIT_CHECK_SCHEMA_VERSION,
            "status": "failed",
            "checked_quantities": [],
            "errors": ["Unit contract payload must be a JSON object."],
            "warnings": [],
        }
    _walk(payload, "$", checked, errors, warnings)
    if not checked:
        warnings.append("No recognized unit-suffixed quantities were found.")
    return {
        "schema_version": UNIT_CHECK_SCHEMA_VERSION,
        "status": "failed" if errors else "passed",
        "checked_quantities": checked,
        "errors": errors,
        "warnings": warnings,
    }


def unit_contract_markdown(report: dict[str, Any]) -> str:
    """Render a unit-contract report."""

    lines = [
        "# FastFluent Unit Contract Report",
        "",
        f"Status: `{report.get('status')}`",
        "",
        "## Checked Quantities",
        "",
        "| Path | Unit | Value Kind |",
        "| --- | --- | --- |",
    ]
    for item in report.get("checked_quantities", []):
        lines.append(f"| `{item.get('path')}` | `{item.get('unit')}` | `{item.get('value_kind')}` |")
    if not report.get("checked_quantities"):
        lines.append("| none | none | none |")
    lines.extend(["", "## Warnings", ""])
    warnings = report.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Errors", ""])
    errors = report.get("errors", [])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _walk(value: Any, path: str, checked: list[dict[str, Any]], errors: list[str], warnings: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            unit = _unit_for_key(str(key))
            if unit:
                _check_quantity(item, child_path, unit, checked, errors)
            _walk(item, child_path, checked, errors, warnings)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk(item, f"{path}[{index}]", checked, errors, warnings)


def _unit_for_key(key: str) -> str | None:
    for suffix, unit in sorted(UNIT_SUFFIXES.items(), key=lambda item: len(item[0]), reverse=True):
        if key.endswith(suffix):
            return unit
    return None


def _check_quantity(value: Any, path: str, unit: str, checked: list[dict[str, Any]], errors: list[str]) -> None:
    numbers = _numbers(value)
    checked.append({"path": path, "unit": unit, "value_kind": "vector" if isinstance(value, list) else "scalar"})
    if not numbers:
        errors.append(f"{path} must be numeric or a numeric vector.")
        return
    if not all(isfinite(number) for number in numbers):
        errors.append(f"{path} contains non-finite values.")
    if _requires_positive(path) and any(number <= 0 for number in numbers):
        errors.append(f"{path} must be positive.")


def _numbers(value: Any) -> list[float]:
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, list) and all(isinstance(item, (int, float)) for item in value):
        return [float(item) for item in value]
    return []


def _requires_positive(path: str) -> bool:
    suffix = _suffix_for_path(path)
    return suffix in POSITIVE_SUFFIXES if suffix else False


def _suffix_for_path(path: str) -> str | None:
    for suffix in sorted(UNIT_SUFFIXES, key=len, reverse=True):
        if path.endswith(suffix):
            return suffix
    return None
