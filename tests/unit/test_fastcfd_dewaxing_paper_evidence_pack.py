from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.dewaxing_native_validation_pack import run_dewaxing_native_validation_pack
from fromcad2cfd_fastcfd.dewaxing_paper_evidence_pack import compile_dewaxing_paper_evidence_pack


PUBLIC_PACK = "examples/postprocessing/dewaxing_result_pack"


def _write_iteration_manifest(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "fastfluent_dewaxing_agent_iteration_pack_v1",
        "status": "success",
        "quality_status": "passed",
        "case_id": "dewaxing_agent_iteration_pack",
        "round_count": 3,
        "candidate_count": 3,
        "validation_target_count": 2,
        "round_trace": [
            {
                "round_index": 0,
                "round_id": "single_factor_screen",
                "candidate_ids": ["baseline", "shell_thin"],
                "best_after_round": {"candidate_id": "shell_thin"},
            },
            {
                "round_index": 1,
                "round_id": "combined_response",
                "candidate_ids": ["path106_initial6"],
                "best_after_round": {"candidate_id": "path106_initial6"},
            },
        ],
        "candidates": [
            _iteration_candidate("baseline", 0, 0.078093, 359.36, 100.724744, 1.723578, 0.121369, 0.000246),
            _iteration_candidate("shell_thin", 0, 0.064131, 399.68, 115.668278, 1.547805, 0.022787, 0.148642),
            _iteration_candidate("path106_initial6", 1, 0.042093, 386.8, 102.209953, 1.670091, 0.054279, 0.014995),
        ],
        "validation_reviews": [
            {
                "schema_version": "fastfluent_dewaxing_agent_candidate_validation_v1",
                "candidate_id": "shell_thin",
                "quality_status": "warning",
                "validation_case_count": 5,
                "native_cell_time_steps": 1000,
                "qoi_stability": {
                    "metrics": [
                        _stability_metric("predicted_full_melt_time_s", "warning", 399.68, 399.68, 430.0, 0.15, 0.12),
                    ],
                    "warnings": ["predicted_full_melt_time_s exceeds threshold."],
                },
                "warnings": ["predicted_full_melt_time_s exceeds threshold."],
            },
            {
                "schema_version": "fastfluent_dewaxing_agent_candidate_validation_v1",
                "candidate_id": "path106_initial6",
                "quality_status": "passed",
                "validation_case_count": 5,
                "native_cell_time_steps": 2000,
                "qoi_stability": {
                    "metrics": [
                        _stability_metric("predicted_full_melt_time_s", "passed", 386.8, 386.8, 417.92, 0.080455, 0.12),
                        _stability_metric("dominant_risk_time_s", "passed", 102.209953, 102.106287, 121.381726, 0.188587, 0.30),
                        _stability_metric("early_max_shell_stress_proxy_MPa", "passed", 1.670091, 1.611176, 1.674918, 0.038167, 0.40),
                        _stability_metric("peak_pressure_risk_proxy", "passed", 0.060468, 0.059093, 0.06047, 0.022775, 0.35),
                        _stability_metric("energy_balance_relative_error", "passed", 0.050275, 0.049707, 0.054615, 0.054615, 0.08),
                    ],
                    "warnings": [],
                },
                "warnings": [],
            },
        ],
        "agent_decision": {
            "schema_version": "fastfluent_dewaxing_agent_iteration_decision_v1",
            "status": "passed",
            "best_unvalidated_candidate": {
                "candidate_id": "shell_thin",
                "agent_objective_score": 0.064131,
                "predicted_full_melt_time_s": 399.68,
                "dominant_risk_time_s": 115.668278,
                "early_max_shell_stress_proxy_MPa": 1.547805,
                "full_melt_time_relative_error": 0.022787,
                "dominant_risk_time_relative_error": 0.148642,
            },
            "accepted_candidate": {
                "candidate_id": "path106_initial6",
                "agent_objective_score": 0.042093,
                "predicted_full_melt_time_s": 386.8,
                "dominant_risk_time_s": 102.209953,
                "early_max_shell_stress_proxy_MPa": 1.670091,
                "full_melt_time_relative_error": 0.054279,
                "dominant_risk_time_relative_error": 0.014995,
            },
            "accepted_candidate_validation_status": "passed",
            "stability_rejected_candidates": [{"candidate_id": "shell_thin", "quality_status": "warning"}],
            "objective_improvement_vs_baseline": 0.460989,
            "objective_improvement_vs_shell_thin": 0.34364,
            "execution_summary": {
                "native_dewaxing_solver_runs": 13,
                "native_cell_time_steps": 123456,
                "new_fluent_calculation": False,
            },
        },
        "execution_boundary": {
            "new_fluent_calculation": False,
            "fluent_launched": False,
            "native_dewaxing_solver_runs": 13,
            "native_cell_time_steps": 123456,
        },
    }
    path = root / "agent_iteration_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _iteration_candidate(
    candidate_id: str,
    round_index: int,
    objective: float,
    full_melt_time: float,
    risk_time: float,
    stress: float,
    full_error: float,
    risk_error: float,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "round_index": round_index,
        "agent_objective_score": objective,
        "metrics": {
            "predicted_full_melt_time_s": full_melt_time,
            "dominant_risk_time_s": risk_time,
            "early_max_shell_stress_proxy_MPa": stress,
        },
        "comparison_metrics": {
            "full_melt_time_relative_error": full_error,
            "dominant_risk_time_relative_error": risk_error,
        },
    }


def _stability_metric(
    metric: str,
    status: str,
    current: float,
    min_value: float,
    max_value: float,
    spread: float,
    threshold: float,
) -> dict[str, object]:
    return {
        "metric": metric,
        "quality_status": status,
        "current_value": current,
        "min_value": min_value,
        "max_value": max_value,
        "relative_spread_vs_current": spread,
        "threshold": threshold,
    }


def test_dewaxing_paper_evidence_pack_compiles_tables_figures_and_claims(tmp_path):
    validation = run_dewaxing_native_validation_pack(
        output_dir=tmp_path / "validation",
        comparison_pack=PUBLIC_PACK,
        profile="smoke",
        max_cases=2,
    )
    pack = compile_dewaxing_paper_evidence_pack(
        validation_pack=validation["artifacts"]["manifest"],
        output_dir=tmp_path / "paper",
        manuscript_title="Dewaxing Evidence Test",
    )

    assert pack["status"] == "success"
    assert pack["execution_boundary"]["new_fluent_calculation"] is False
    assert pack["execution_boundary"]["native_dewaxing_solver_rerun"] is False
    assert pack["summary"]["native_solver_runs"] == 2
    assert len(pack["tables"]) == 4
    assert len(pack["figures"]) == 4
    assert pack["figure_style"]["style_name"] == "nature_soft_statistical"
    assert Path(pack["artifacts"]["results_section"]).exists()
    assert Path(pack["artifacts"]["paper_claims"]).exists()
    assert "FastFluent-native validation executed" in Path(pack["artifacts"]["results_section"]).read_text(encoding="utf-8")
    for figure in pack["figures"]:
        text = Path(figure["path"]).read_text(encoding="utf-8")
        assert text.startswith("<svg")
        assert "</svg>" in text
        assert "#6F91AA" in text or "#B8738E" in text
    claims = pack["paper_claims"]
    assert any("final CFD validation" in item for item in claims["restricted_claims"])


def test_dewaxing_paper_evidence_pack_compiles_iteration_evidence(tmp_path):
    validation = run_dewaxing_native_validation_pack(
        output_dir=tmp_path / "validation",
        comparison_pack=PUBLIC_PACK,
        profile="smoke",
        max_cases=2,
    )
    iteration_manifest = _write_iteration_manifest(tmp_path / "iteration")
    pack = compile_dewaxing_paper_evidence_pack(
        validation_pack=validation["artifacts"]["manifest"],
        iteration_pack=iteration_manifest,
        output_dir=tmp_path / "paper",
        manuscript_title="Dewaxing Iteration Evidence Test",
    )

    assert pack["status"] == "success"
    assert pack["source_iteration_status"] == "success"
    assert pack["summary"]["iteration_accepted_candidate_id"] == "path106_initial6"
    assert pack["summary"]["iteration_solver_runs"] == 13
    assert pack["execution_boundary"]["source_iteration_cell_time_steps"] == 123456
    assert len(pack["tables"]) == 6
    assert len(pack["figures"]) == 7
    assert any("Agent iteration campaign" in item for item in pack["paper_claims"]["supported_claims"])
    assert "path106_initial6" in Path(pack["artifacts"]["results_section"]).read_text(encoding="utf-8")


def test_dewaxing_paper_evidence_pack_cli(tmp_path, capsys):
    validation = run_dewaxing_native_validation_pack(
        output_dir=tmp_path / "validation",
        comparison_pack=PUBLIC_PACK,
        profile="smoke",
        max_cases=2,
    )
    iteration_manifest = _write_iteration_manifest(tmp_path / "iteration")
    exit_code = fastcfd_main(
        [
            "compile-dewaxing-paper-evidence-pack",
            "--validation-pack",
            validation["artifacts"]["manifest"],
            "--iteration-pack",
            str(iteration_manifest),
            "--output-dir",
            str(tmp_path / "cli_paper"),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["execution_boundary"]["new_fluent_calculation"] is False
    assert payload["summary"]["native_solver_runs"] == 2
    assert payload["summary"]["iteration_accepted_candidate_id"] == "path106_initial6"
    assert len(payload["figures"]) == 7
    assert Path(payload["artifacts"]["evidence_report"]).exists()
