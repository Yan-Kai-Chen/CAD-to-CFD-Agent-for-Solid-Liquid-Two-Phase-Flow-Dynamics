from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.dewaxing_agent_iteration_pack import run_dewaxing_agent_iteration_pack


PUBLIC_PACK = "examples/postprocessing/dewaxing_result_pack"


def test_dewaxing_agent_iteration_pack_runs_agent_trace_without_fluent(tmp_path):
    pack = run_dewaxing_agent_iteration_pack(
        output_dir=tmp_path / "iteration",
        comparison_pack=PUBLIC_PACK,
        max_rounds=1,
        max_candidates_per_round=2,
        max_validation_targets=0,
    )

    assert pack["status"] == "warning"
    assert pack["candidate_count"] == 2
    assert pack["execution_boundary"]["new_fluent_calculation"] is False
    assert pack["execution_boundary"]["native_dewaxing_solver_runs"] == 2
    assert pack["round_trace"][0]["round_id"] == "single_factor_screen"
    assert pack["agent_decision"]["best_unvalidated_candidate"]["candidate_id"] in {"baseline", "shell_thin"}
    assert Path(pack["artifacts"]["candidate_summary_csv"]).exists()
    assert Path(pack["artifacts"]["round_trace"]).exists()


def test_dewaxing_agent_iteration_pack_records_stability_rejection(tmp_path):
    quick_plan = [
        {
            "round_index": 0,
            "round_id": "quick_unmelted_candidate",
            "agent_hypothesis": "A short final time should be rejected by the stability review.",
            "candidates": [
                {
                    "candidate_id": "short_final_time",
                    "name": "Short final time",
                    "rationale": "Force a quick validation warning in test.",
                    "edits": [{"path": "time.final_time_s", "operation": "set", "value": 40.0}],
                }
            ],
        }
    ]
    pack = run_dewaxing_agent_iteration_pack(
        output_dir=tmp_path / "iteration",
        comparison_pack=PUBLIC_PACK,
        iteration_plan=quick_plan,
        max_validation_targets=1,
    )

    assert pack["status"] == "warning"
    assert pack["validation_target_count"] == 1
    assert pack["agent_decision"]["accepted_candidate"] == {
        "candidate_id": None,
        "name": None,
        "round_index": None,
        "agent_objective_score": None,
        "predicted_full_melt_time_s": None,
        "dominant_risk_time_s": None,
        "early_max_shell_stress_proxy_MPa": None,
        "full_melt_time_relative_error": None,
        "dominant_risk_time_relative_error": None,
    }
    assert pack["agent_decision"]["stability_rejected_candidates"][0]["candidate_id"] == "short_final_time"
    assert "predicted_full_melt_time_s missing" in pack["agent_decision"]["stability_rejected_candidates"][0]["warnings"][0]


def test_dewaxing_agent_iteration_pack_cli(tmp_path, capsys):
    exit_code = fastcfd_main(
        [
            "run-dewaxing-agent-iteration-pack",
            "--output-dir",
            str(tmp_path / "cli_iteration"),
            "--max-rounds",
            "1",
            "--max-candidates-per-round",
            "1",
            "--max-validation-targets",
            "0",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "warning"
    assert payload["candidate_count"] == 1
    assert payload["execution_boundary"]["new_fluent_calculation"] is False
    assert Path(payload["artifacts"]["iteration_report"]).exists()
