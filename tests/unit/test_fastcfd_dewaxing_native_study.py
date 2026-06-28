from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.dewaxing_native_study import run_dewaxing_native_study


PUBLIC_PACK = "examples/postprocessing/dewaxing_result_pack"


def test_dewaxing_native_study_runs_variants_and_guidance(tmp_path):
    study = run_dewaxing_native_study(output_dir=tmp_path / "study", comparison_pack=PUBLIC_PACK, max_variants=3)
    guidance = study["guidance"]

    assert study["status"] == "success"
    assert study["variant_count"] == 3
    assert study["execution_boundary"]["native_dewaxing_solver_runs"] == 3
    assert guidance["best_match_variant"]["variant_id"] in {"baseline", "htc_low", "htc_high"}
    assert guidance["claim_boundary"]["can_support_fastfluent_screening_decision"] is True
    assert guidance["claim_boundary"]["can_support_final_cfd_validation"] is False
    assert any("Full-melt timing is most sensitive" in item for item in guidance["recommendations"])
    assert Path(study["artifacts"]["variant_summary_csv"]).exists()
    assert Path(study["artifacts"]["dewaxing_guidance"]).exists()


def test_dewaxing_native_study_preserves_variant_result_packs(tmp_path):
    study = run_dewaxing_native_study(output_dir=tmp_path / "study", comparison_pack=PUBLIC_PACK, max_variants=2)

    for variant in study["variants"]:
        assert Path(variant["artifacts"]["native_result"]).exists()
        assert Path(variant["artifacts"]["result_pack"]).exists()
        assert variant["result_pack_status"] in {"advisory_native_evidence", "native_evidence_warning"}


def test_dewaxing_native_study_cli(tmp_path, capsys):
    exit_code = fastcfd_main(
        [
            "run-dewaxing-native-study",
            "--output-dir",
            str(tmp_path / "cli"),
            "--max-variants",
            "2",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["variant_count"] == 2
    assert payload["guidance"]["claim_boundary"]["can_support_new_fluent_calculation"] is False
