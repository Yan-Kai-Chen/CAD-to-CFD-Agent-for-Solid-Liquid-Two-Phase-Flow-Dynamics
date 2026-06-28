from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.dewaxing_native_validation_pack import (
    default_dewaxing_native_validation_plan,
    run_dewaxing_native_validation_pack,
)


PUBLIC_PACK = "examples/postprocessing/dewaxing_result_pack"


def test_dewaxing_native_validation_plan_profiles():
    smoke = default_dewaxing_native_validation_plan("smoke")
    standard = default_dewaxing_native_validation_plan("standard")

    assert len(smoke) == 4
    assert len(standard) == 10
    assert {item["target_id"] for item in smoke} == {"baseline", "shell_thin"}
    assert {item["case_variant"] for item in smoke} == {"current", "coarse_grid"}
    assert {"fine_grid", "dt_large", "dt_small"}.issubset({item["case_variant"] for item in standard})


def test_dewaxing_native_validation_pack_writes_evidence(tmp_path):
    pack = run_dewaxing_native_validation_pack(output_dir=tmp_path / "validation", comparison_pack=PUBLIC_PACK, profile="smoke")
    decision = pack["agent_validation_decision"]

    assert pack["status"] == "success"
    assert pack["validation_case_count"] == 4
    assert pack["execution_boundary"]["new_fluent_calculation"] is False
    assert pack["execution_boundary"]["native_dewaxing_solver_runs"] == 4
    assert pack["execution_boundary"]["native_cell_time_steps"] > 0
    assert decision["claim_boundary"]["can_support_fastfluent_screening_decision"] is True
    assert decision["claim_boundary"]["can_support_final_cfd_validation"] is False
    assert decision["recommended_target_id"] in {"baseline", "shell_thin"}
    assert Path(pack["artifacts"]["paper_tables"]).exists()
    assert Path(pack["artifacts"]["study_interpretation"]).exists()
    assert Path(pack["artifacts"]["agent_validation_decision"]).exists()
    assert "targets" in pack["qoi_stability"]
    for case in pack["cases"]:
        assert Path(case["artifacts"]["native_result"]).exists()
        assert Path(case["artifacts"]["result_pack"]).exists()
        assert case["result_pack_validation_status"] == "passed"


def test_dewaxing_native_validation_pack_cli(tmp_path, capsys):
    exit_code = fastcfd_main(
        [
            "run-dewaxing-native-validation-pack",
            "--output-dir",
            str(tmp_path / "cli"),
            "--profile",
            "smoke",
            "--max-cases",
            "2",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["validation_case_count"] == 2
    assert payload["execution_boundary"]["new_fluent_calculation"] is False
    assert payload["agent_validation_decision"]["claim_boundary"]["can_support_new_fluent_calculation"] is False
