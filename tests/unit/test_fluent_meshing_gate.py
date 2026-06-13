from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fluent_meshing.gate import evaluate_preflight_gate


def _write_fastcfd_artifacts(
    output_dir: Path,
    *,
    case_type: str = "obstacle2d",
    pilot_status: str = "proceed_with_advisory_handoff",
    lattice_status: str = "passed",
    lattice_score: float = 1.0,
    field_status: str = "parsed",
    residual_ratio: float | None = 0.5,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    qoi_metrics = {
        "field_parser_status": field_status,
        "lattice_domain_status": lattice_status,
        "lattice_trust_score": lattice_score,
        "pilot_decision_status": pilot_status,
        "pilot_decision_top_action": "proceed_with_advisory_handoff",
    }
    if residual_ratio is not None:
        qoi_metrics["native_convergence_reduction_ratio"] = residual_ratio
    (output_dir / "qoi.json").write_text(json.dumps({"run_id": "unit", "metrics": qoi_metrics}), encoding="utf-8")
    (output_dir / "pilot_decision.json").write_text(
        json.dumps(
            {
                "schema_version": "fromcad2cfd_pilot_decision_v1",
                "status": pilot_status,
                "case_type": case_type,
                "confidence": "medium",
                "recommended_actions": [
                    {
                        "priority": "medium",
                        "action": "proceed_with_advisory_handoff",
                        "reason": "Unit test action.",
                        "evidence": ["qoi.json"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "lattice_domain_summary.json").write_text(
        json.dumps(
            {
                "schema_version": "fromcad2cfd_lattice_domain_summary_v1",
                "status": lattice_status,
                "case_type": case_type,
                "trust_score": lattice_score,
                "grid": {"nx": 120, "ny": 40, "cell_length_mm": 1.0, "total_cells": 4800},
                "warnings": [],
                "errors": [] if lattice_status != "failed" else ["Unit test failure."],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "field_qoi.json").write_text(
        json.dumps(
            {
                "status": field_status,
                "metrics": {
                    "wake_bbox_proxy": {
                        "status": "detected",
                        "bbox_mm": {"x_min": 50.0, "x_max": 80.0, "y_min": 12.0, "y_max": 28.0},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "result_manifest.json").write_text(json.dumps({"status": "success", "case_type": case_type}), encoding="utf-8")


def test_fluent_meshing_gate_allows_clean_fastcfd_evidence(tmp_path):
    fastcfd_output = tmp_path / "fastcfd" / "output"
    _write_fastcfd_artifacts(fastcfd_output)

    result = evaluate_preflight_gate(fastcfd_output, output_dir=tmp_path / "reports", model_name="unit_gate")

    assert result["status"] == "passed"
    assert result["decision"] == "allow_fluent_meshing_preparation"
    assert Path(result["json_report"]).exists()
    gate = result["gate"]
    assert gate["case_type"] == "obstacle2d"
    assert any(hint["category"] == "local_sizing" for hint in gate["fluent_meshing_hints"])


def test_fluent_meshing_gate_warns_for_domain_extent_review(tmp_path):
    fastcfd_output = tmp_path / "fastcfd" / "output"
    _write_fastcfd_artifacts(fastcfd_output, case_type="channel2d", pilot_status="review_domain_extent", residual_ratio=0.76)

    result = evaluate_preflight_gate(fastcfd_output, output_dir=tmp_path / "reports", model_name="unit_gate")

    assert result["status"] == "warning"
    assert result["decision"] == "prepare_plan_with_domain_extent_review"
    assert any(action["action"] == "review_pilot_decision_allows_meshing_prep" for action in result["gate"]["required_actions"])


def test_fluent_meshing_gate_blocks_failed_lattice(tmp_path):
    fastcfd_output = tmp_path / "fastcfd" / "output"
    _write_fastcfd_artifacts(
        fastcfd_output,
        pilot_status="revise_lattice_domain",
        lattice_status="failed",
        lattice_score=0.25,
        field_status="not_available",
        residual_ratio=None,
    )

    result = evaluate_preflight_gate(fastcfd_output, output_dir=tmp_path / "reports", model_name="unit_gate")

    assert result["status"] == "blocked"
    assert result["decision"] == "do_not_prepare_fluent_meshing"


def test_root_cli_routes_fluent_meshing_preflight_gate(tmp_path, capsys):
    fastcfd_output = tmp_path / "fastcfd" / "output"
    _write_fastcfd_artifacts(fastcfd_output)

    exit_code = root_main(
        [
            "fluent-meshing",
            "preflight-gate",
            "--fastcfd-output-dir",
            str(fastcfd_output),
            "--output-dir",
            str(tmp_path / "reports"),
            "--model-name",
            "unit_gate_cli",
        ]
    )

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["status"] == "passed"
    assert Path(captured["json_report"]).exists()
