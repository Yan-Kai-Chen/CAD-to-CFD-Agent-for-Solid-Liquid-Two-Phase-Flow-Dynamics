"""Public-safe validation for dewaxing Agent result packs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEWAXING_RESULT_PACK_SCHEMA_VERSION = "dewaxing_agent_result_pack_v1"
DEWAXING_RESULT_PACK_VALIDATION_SCHEMA_VERSION = "dewaxing_agent_result_pack_validation_v1"


def validate_dewaxing_result_pack(pack: str | Path) -> dict[str, Any]:
    """Validate a dewaxing Agent Result Pack without reading private case/data files."""

    pack_path = _resolve_pack_path(pack)
    errors: list[str] = []
    warnings: list[str] = []
    if not pack_path.exists():
        return _failed([f"Result Pack does not exist: {pack_path}"])
    try:
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _failed([f"Result Pack is invalid JSON: {exc}"])

    if payload.get("schema_version") != DEWAXING_RESULT_PACK_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {payload.get('schema_version')!r}")
    if payload.get("status") != "dewaxing_bridge_complete":
        warnings.append(f"Unexpected pack status: {payload.get('status')!r}")
    if payload.get("evidence_level") != "reviewed_private_fluent_result_pack":
        warnings.append(f"Unexpected evidence_level: {payload.get('evidence_level')!r}")

    usage = payload.get("usage_boundary") if isinstance(payload.get("usage_boundary"), dict) else {}
    if usage.get("valid_for_final_crack_probability") is not False:
        errors.append("Dewaxing packs must not claim calibrated crack probability.")
    if usage.get("valid_for_two_way_fsi_claims") is not False:
        errors.append("Dewaxing packs must not claim two-way FSI validation.")
    if usage.get("valid_for_agent_workflow_control") is not True:
        errors.append("Dewaxing packs must be valid for agent workflow control.")

    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    if decision.get("can_support_final_crack_probability") is not False:
        errors.append("Decision must not support final crack probability.")
    if decision.get("can_support_two_way_fsi_validation") is not False:
        errors.append("Decision must not support two-way FSI validation.")

    qoi = payload.get("qoi") if isinstance(payload.get("qoi"), dict) else {}
    early = qoi.get("early_steam_shock") if isinstance(qoi.get("early_steam_shock"), dict) else {}
    full = qoi.get("full_cycle_wax") if isinstance(qoi.get("full_cycle_wax"), dict) else {}
    key_metrics = _key_metrics(early, full)
    _require_numeric(key_metrics, errors)

    if key_metrics.get("early_max_crack_index_over_3p6mpa", 1.0) >= 1.0:
        warnings.append("Early crack-driving index reaches or exceeds the 3.6 MPa reference.")
    if key_metrics.get("full_cycle_stress_drop_fraction", 0.0) < 0.5:
        warnings.append("Drainage-relief stress drop is below the expected screening threshold.")

    claim_ledger = payload.get("claim_ledger")
    if isinstance(claim_ledger, str):
        claim_path = pack_path.parent / claim_ledger
        if not claim_path.exists():
            warnings.append(f"Referenced claim ledger is missing: {claim_ledger}")
    else:
        warnings.append("Result Pack does not reference a claim_ledger artifact.")

    status = "failed" if errors else "passed"
    return {
        "schema_version": DEWAXING_RESULT_PACK_VALIDATION_SCHEMA_VERSION,
        "status": status,
        "passed": status == "passed",
        "pack_path": str(pack_path),
        "case_id": payload.get("case_id"),
        "evidence_level": payload.get("evidence_level"),
        "recommended_next_action": decision.get("recommended_next_action"),
        "key_metrics": key_metrics,
        "errors": errors,
        "warnings": warnings,
    }


def dewaxing_result_pack_validation_markdown(validation: dict[str, Any]) -> str:
    """Render dewaxing pack validation as Markdown."""

    metrics = validation.get("key_metrics", {}) if isinstance(validation.get("key_metrics"), dict) else {}
    lines = [
        "# Dewaxing Agent Result Pack Validation",
        "",
        f"- Status: `{validation.get('status')}`",
        f"- Case ID: `{validation.get('case_id')}`",
        f"- Evidence level: `{validation.get('evidence_level')}`",
        f"- Recommended next action: `{validation.get('recommended_next_action')}`",
        "",
        "## Key Metrics",
        "",
    ]
    for key, value in metrics.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Warnings", ""])
    warnings = validation.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.extend(["", "## Errors", ""])
    errors = validation.get("errors", [])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _key_metrics(early: dict[str, Any], full: dict[str, Any]) -> dict[str, float | str | None]:
    melt = full.get("melt_completion") if isinstance(full.get("melt_completion"), dict) else {}
    risk = full.get("dominant_risk_window") if isinstance(full.get("dominant_risk_window"), dict) else {}
    relief = full.get("drainage_relief") if isinstance(full.get("drainage_relief"), dict) else {}
    return {
        "early_max_crack_index_over_3p6mpa": _as_float(early.get("max_crack_driving_index_over_3p6mpa")),
        "full_melt_time_s": _as_float(melt.get("first_full_melt_time_s")),
        "latest_avg_liquid_fraction": _as_float(melt.get("latest_avg_liquid_fraction")),
        "dominant_risk_time_s": _as_float(risk.get("time_s")),
        "peak_effective_pressure_mpa": _as_float(risk.get("peak_effective_pressure_mpa")),
        "peak_wall_vm_p995_mpa": _as_float(risk.get("peak_wall_vm_p995_mpa")),
        "full_cycle_stress_drop_fraction": _as_float(relief.get("stress_drop_fraction_peak_to_latest_p995")),
    }


def _require_numeric(metrics: dict[str, Any], errors: list[str]) -> None:
    for key, value in metrics.items():
        if value is None:
            errors.append(f"Missing required numeric key metric: {key}")


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_pack_path(pack: str | Path) -> Path:
    path = Path(pack)
    return path / "result_pack.json" if path.is_dir() else path


def _failed(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": DEWAXING_RESULT_PACK_VALIDATION_SCHEMA_VERSION,
        "status": "failed",
        "passed": False,
        "errors": errors,
        "warnings": [],
    }
