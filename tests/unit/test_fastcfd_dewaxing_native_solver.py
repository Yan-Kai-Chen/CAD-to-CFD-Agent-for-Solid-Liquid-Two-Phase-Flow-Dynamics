from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.dewaxing_native_solver import run_dewaxing_native_solver
from fromcad2cfd_fastcfd.result_pack import compile_native_result_pack, validate_result_pack


PUBLIC_PACK = "examples/postprocessing/dewaxing_result_pack"


def test_dewaxing_native_solver_computes_melt_and_compares_to_pack(tmp_path):
    result = run_dewaxing_native_solver(output_dir=tmp_path / "native", comparison_pack=PUBLIC_PACK)
    metrics = result["outputs"]["qoi"]["metrics"]
    comparison = result["outputs"]["comparison"]["metrics"]

    assert result["status"] == "success"
    assert result["quality_status"] == "passed"
    assert metrics["full_melt_reached"] is True
    assert metrics["predicted_full_melt_time_s"] == 359.36
    assert metrics["final_avg_liquid_fraction"] == 1.0
    assert metrics["energy_balance_relative_error"] < 0.08
    assert comparison["full_melt_time_relative_error"] < 0.20
    assert comparison["dominant_risk_time_relative_error"] < 0.60
    assert result["metadata"]["new_fluent_calculation"] is False
    assert Path(result["outputs"]["artifacts"]["final_field"]).exists()
    assert Path(result["outputs"]["artifacts"]["history"]).exists()


def test_dewaxing_native_solver_compiles_native_result_pack(tmp_path):
    result = run_dewaxing_native_solver(output_dir=tmp_path / "native", comparison_pack=PUBLIC_PACK)
    pack = compile_native_result_pack(result["outputs"]["artifacts"]["status"], output_dir=tmp_path / "pack")
    validation = validate_result_pack(tmp_path / "pack")

    assert pack["status"] == "advisory_native_evidence"
    assert pack["quality_status"] == "passed"
    assert pack["native_result"]["result_kind"] == "dewaxing_native_reduced_order_solver"
    assert pack["evidence_level"] == "native_dewaxing_reduced_order_advisory"
    assert validation["passed"] is True


def test_dewaxing_native_solver_cli(tmp_path, capsys):
    exit_code = fastcfd_main(["run-dewaxing-native-solver", "--output-dir", str(tmp_path / "cli"), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["quality_status"] == "passed"
    assert payload["outputs"]["qoi"]["metrics"]["predicted_full_melt_time_s"] == 359.36
