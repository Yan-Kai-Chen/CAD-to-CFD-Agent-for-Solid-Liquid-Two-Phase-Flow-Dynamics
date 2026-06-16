"""Pre-meshing gate from FastCFD pilot evidence to Fluent Meshing planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FLUENT_MESHING_GATE_SCHEMA_VERSION = "fromcad2cfd_fluent_meshing_preflight_gate_v1"


def evaluate_preflight_gate(
    fastcfd_output_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    model_name: str = "fluent_meshing_preflight_gate",
) -> dict[str, Any]:
    """Evaluate whether FastCFD evidence is ready for Fluent Meshing planning."""

    source = Path(fastcfd_output_dir)
    report_dir = Path(output_dir) if output_dir else source.parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    inputs = _read_inputs(source)
    gate = _build_gate(source, inputs)
    json_path = _unique_path(report_dir / f"{model_name}_preflight_gate.json")
    markdown_path = _unique_path(report_dir / f"{model_name}_preflight_gate.md")
    _write_json(json_path, gate)
    markdown_path.write_text(_markdown_report(gate), encoding="utf-8")
    return {
        "status": gate["status"],
        "decision": gate["decision"],
        "json_report": str(json_path),
        "markdown_report": str(markdown_path),
        "gate": gate,
    }


def _read_inputs(source: Path) -> dict[str, Any]:
    return {
        "qoi": _read_optional_json(source / "qoi.json"),
        "pilot_decision": _read_optional_json(source / "pilot_decision.json"),
        "lattice_domain_summary": _read_optional_json(source / "lattice_domain_summary.json"),
        "field_qoi": _read_optional_json(source / "field_qoi.json"),
        "result_manifest": _read_optional_json(source / "result_manifest.json"),
        "paths": {
            "fastcfd_output_dir": str(source),
            "qoi": str(source / "qoi.json"),
            "pilot_decision": str(source / "pilot_decision.json"),
            "lattice_domain_summary": str(source / "lattice_domain_summary.json"),
            "field_qoi": str(source / "field_qoi.json"),
            "result_manifest": str(source / "result_manifest.json"),
        },
    }


def _build_gate(source: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    qoi = _payload(inputs, "qoi")
    pilot = _payload(inputs, "pilot_decision")
    lattice = _payload(inputs, "lattice_domain_summary")
    field = _payload(inputs, "field_qoi")
    manifest = _payload(inputs, "result_manifest")
    metrics = qoi.get("metrics") if isinstance(qoi.get("metrics"), dict) else {}
    checks = _checks(inputs, metrics, pilot, lattice, field)
    status = _gate_status(checks)
    decision = _gate_decision(status, pilot)
    case_type = _case_type(qoi, pilot, lattice, manifest)
    required_actions = _required_actions(status, checks, pilot)
    hints = _fluent_meshing_hints(case_type, field, lattice, pilot)
    return {
        "schema_version": FLUENT_MESHING_GATE_SCHEMA_VERSION,
        "status": status,
        "decision": decision,
        "case_type": case_type,
        "source_fastcfd_output_dir": str(source),
        "input_artifacts": inputs["paths"],
        "evidence_summary": {
            "pilot_decision_status": pilot.get("status", "missing"),
            "pilot_decision_confidence": pilot.get("confidence", "missing"),
            "lattice_domain_status": lattice.get("status", "missing"),
            "lattice_trust_score": lattice.get("trust_score"),
            "field_parser_status": field.get("status", "missing"),
            "native_convergence_reduction_ratio": metrics.get("native_convergence_reduction_ratio"),
            "pilot_top_action": metrics.get("pilot_decision_top_action"),
        },
        "gate_checks": checks,
        "required_actions": required_actions,
        "fluent_meshing_hints": hints,
        "limitations": [
            "This public gate prepares Fluent Meshing handoff evidence; mesh generation belongs to a configured local Fluent adapter.",
            "FastCFD/FastFluent pilot evidence is advisory and must be checked against Fluent mesh-quality reports.",
            "The current gate supports bounded FastCFD recipe cases and does not parse arbitrary Fluent case/data files.",
        ],
    }


def _checks(
    inputs: dict[str, Any],
    metrics: dict[str, Any],
    pilot: dict[str, Any],
    lattice: dict[str, Any],
    field: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for key in ("qoi", "pilot_decision", "lattice_domain_summary"):
        item = inputs.get(key) or {}
        checks.append(
            {
                "name": f"{key}_available",
                "status": "passed" if item.get("status") == "available" else "blocked",
                "message": item.get("error") or f"{key} was found.",
                "evidence": inputs["paths"].get(key),
            }
        )
    pilot_status = str(pilot.get("status", "missing"))
    if pilot_status in {"revise_lattice_domain", "insufficient_evidence", "missing"}:
        checks.append(
            {
                "name": "pilot_decision_allows_meshing_prep",
                "status": "blocked",
                "message": f"Pilot decision status is {pilot_status}; Fluent Meshing preparation should not proceed automatically.",
                "evidence": inputs["paths"].get("pilot_decision"),
            }
        )
    elif pilot_status in {"extend_pilot_before_handoff", "review_domain_extent", "review_before_handoff"}:
        checks.append(
            {
                "name": "pilot_decision_allows_meshing_prep",
                "status": "warning",
                "message": f"Pilot decision status is {pilot_status}; create a meshing plan only after review.",
                "evidence": inputs["paths"].get("pilot_decision"),
            }
        )
    else:
        checks.append(
            {
                "name": "pilot_decision_allows_meshing_prep",
                "status": "passed",
                "message": "Pilot decision allows advisory Fluent Meshing preparation.",
                "evidence": inputs["paths"].get("pilot_decision"),
            }
        )
    lattice_status = str(lattice.get("status", "missing"))
    lattice_score = _safe_float(lattice.get("trust_score"))
    if lattice_status == "failed" or (lattice_score is not None and lattice_score < 0.75):
        checks.append(
            {
                "name": "lattice_domain_trust",
                "status": "blocked",
                "message": "Recipe lattice domain must be revised before Fluent Meshing planning.",
                "evidence": inputs["paths"].get("lattice_domain_summary"),
            }
        )
    elif lattice_status == "warning" or (lattice_score is not None and lattice_score < 0.9):
        checks.append(
            {
                "name": "lattice_domain_trust",
                "status": "warning",
                "message": "Recipe lattice domain has warnings; review resolution and clearance before meshing.",
                "evidence": inputs["paths"].get("lattice_domain_summary"),
            }
        )
    else:
        checks.append(
            {
                "name": "lattice_domain_trust",
                "status": "passed",
                "message": "Recipe lattice domain is acceptable for advisory meshing preparation.",
                "evidence": inputs["paths"].get("lattice_domain_summary"),
            }
        )
    if field.get("status") == "parsed":
        checks.append(
            {
                "name": "field_qoi_available",
                "status": "passed",
                "message": "Parsed pilot field QoI is available for meshing hints.",
                "evidence": inputs["paths"].get("field_qoi"),
            }
        )
    else:
        checks.append(
            {
                "name": "field_qoi_available",
                "status": "warning",
                "message": "Parsed field QoI is unavailable; meshing hints will be geometry-only.",
                "evidence": inputs["paths"].get("field_qoi"),
            }
        )
    if _safe_float(metrics.get("native_convergence_reduction_ratio")) is not None:
        checks.append(
            {
                "name": "native_convergence_trace_available",
                "status": "passed",
                "message": "Native residual trace is available for handoff confidence review.",
                "evidence": inputs["paths"].get("qoi"),
            }
        )
    else:
        checks.append(
            {
                "name": "native_convergence_trace_available",
                "status": "warning",
                "message": "Native residual trace is unavailable.",
                "evidence": inputs["paths"].get("qoi"),
            }
        )
    return checks


def _gate_status(checks: list[dict[str, Any]]) -> str:
    statuses = {str(item.get("status")) for item in checks}
    if "blocked" in statuses:
        return "blocked"
    if "warning" in statuses:
        return "warning"
    return "passed"


def _gate_decision(status: str, pilot: dict[str, Any]) -> str:
    if status == "blocked":
        return "do_not_prepare_fluent_meshing"
    if status == "warning":
        pilot_status = str(pilot.get("status", "unknown"))
        if pilot_status == "extend_pilot_before_handoff":
            return "prepare_plan_after_pilot_extension_review"
        if pilot_status == "review_domain_extent":
            return "prepare_plan_with_domain_extent_review"
        return "prepare_plan_with_manual_review"
    return "allow_fluent_meshing_preparation"


def _required_actions(status: str, checks: list[dict[str, Any]], pilot: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for check in checks:
        if check.get("status") == "blocked":
            actions.append(
                {
                    "priority": "critical",
                    "action": f"resolve_{check['name']}",
                    "reason": check["message"],
                    "evidence": [check["evidence"]],
                }
            )
        elif check.get("status") == "warning":
            actions.append(
                {
                    "priority": "medium",
                    "action": f"review_{check['name']}",
                    "reason": check["message"],
                    "evidence": [check["evidence"]],
                }
            )
    for action in pilot.get("recommended_actions") or []:
        if isinstance(action, dict):
            actions.append(
                {
                    "priority": action.get("priority", "medium"),
                    "action": f"pilot_{action.get('action', 'review')}",
                    "reason": action.get("reason", "Pilot decision requested review."),
                    "evidence": action.get("evidence", []),
                }
            )
    if status == "passed":
        actions.append(
            {
                "priority": "medium",
                "action": "prepare_fluent_meshing_plan",
                "reason": "All pre-meshing gate checks passed.",
                "evidence": [],
            }
        )
    return actions


def _fluent_meshing_hints(case_type: str, field: dict[str, Any], lattice: dict[str, Any], pilot: dict[str, Any]) -> list[dict[str, Any]]:
    hints = [
        {
            "category": "named_selections",
            "hint": "Create explicit Fluent named selections before meshing.",
            "items": _named_selections(case_type),
            "evidence": ["case_type", "FastCFD semantic zones"],
            "confidence": "medium",
        },
        {
            "category": "global_mesh",
            "hint": "Use the lattice cell length and trust summary only as an initial scale reference, not as final mesh sizing.",
            "evidence": ["lattice_domain_summary.grid.cell_length_mm", "lattice_domain_summary.trust_score"],
            "confidence": "medium",
        },
    ]
    field_metrics = field.get("metrics") if isinstance(field.get("metrics"), dict) else {}
    wake = field_metrics.get("wake_bbox_proxy") if isinstance(field_metrics.get("wake_bbox_proxy"), dict) else {}
    if wake.get("status") == "detected":
        hints.append(
            {
                "category": "local_sizing",
                "hint": "Use the pilot wake bounding box as a candidate local refinement region.",
                "bbox_mm": wake.get("bbox_mm"),
                "evidence": ["field_qoi.metrics.wake_bbox_proxy.bbox_mm"],
                "confidence": "medium",
            }
        )
    if pilot.get("status") == "review_domain_extent":
        hints.append(
            {
                "category": "domain_extent",
                "hint": "Review downstream length and outlet placement before Fluent meshing.",
                "evidence": ["pilot_decision.status", "field_qoi.fluent_hint_inputs.outlet_spread_ratio"],
                "confidence": "medium",
            }
        )
    if lattice.get("status") == "warning":
        hints.append(
            {
                "category": "geometry",
                "hint": "Review recipe lattice warnings before using them to seed Fluent mesh controls.",
                "evidence": ["lattice_domain_summary.warnings"],
                "confidence": "medium",
            }
        )
    return hints


def _named_selections(case_type: str) -> list[str]:
    if case_type == "cavity2d":
        return ["fluid", "moving_wall", "stationary_walls"]
    if case_type == "channel2d":
        return ["fluid", "inlet", "outlet", "walls"]
    if case_type == "obstacle2d":
        return ["fluid", "inlet", "outlet", "walls", "obstacle_walls"]
    return ["fluid", "inlet", "outlet", "walls"]


def _case_type(qoi: dict[str, Any], pilot: dict[str, Any], lattice: dict[str, Any], manifest: dict[str, Any]) -> str:
    for payload in (pilot, lattice, manifest):
        value = payload.get("case_type")
        if value:
            return str(value)
    metrics = qoi.get("metrics") if isinstance(qoi.get("metrics"), dict) else {}
    return str(metrics.get("case_type") or "unknown")


def _payload(inputs: dict[str, Any], key: str) -> dict[str, Any]:
    item = inputs.get(key)
    if not isinstance(item, dict) or item.get("status") != "available":
        return {}
    payload = item.get("payload")
    return payload if isinstance(payload, dict) else {}


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "path": str(path), "error": f"Missing artifact: {path.name}"}
    try:
        return {"status": "available", "path": str(path), "payload": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"status": "failed", "path": str(path), "error": f"Failed to read {path.name}: {exc}"}


def _markdown_report(gate: dict[str, Any]) -> str:
    lines = [
        "# Fluent Meshing Preflight Gate",
        "",
        f"Status: `{gate['status']}`",
        f"Decision: `{gate['decision']}`",
        f"Case type: `{gate['case_type']}`",
        "",
        "## Evidence Summary",
        "",
    ]
    for key, value in gate["evidence_summary"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Gate Checks", ""])
    for check in gate["gate_checks"]:
        lines.append(f"- `{check['name']}`: `{check['status']}` - {check['message']}")
    lines.extend(["", "## Required Actions", ""])
    for action in gate["required_actions"]:
        lines.append(f"- `{action['priority']}` `{action['action']}`: {action['reason']}")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in gate["limitations"])
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 1
    while True:
        candidate = parent / f"{stem}_{index:02d}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
