from __future__ import annotations

from fromcad2cfd_fastcfd.practical_sweep import run_practical_parameter_sweep


def test_practical_parameter_sweep_writes_summary_risk_map_and_dt_table(tmp_path):
    output_dir = tmp_path / "sweep"

    result = run_practical_parameter_sweep(output_dir)
    manifest = result["manifest"]
    risk_map = result["risk_map"]

    assert manifest["case_count"] >= 10
    assert (output_dir / "sweep_summary.csv").exists()
    assert (output_dir / "sweep_manifest.json").exists()
    assert (output_dir / "risk_map.json").exists()
    assert (output_dir / "recommended_dt_table.csv").exists()
    assert risk_map["status_counts"]["block"] >= 1 or risk_map["status_counts"]["warn"] >= 1
    assert risk_map["fluent_launched"] is False
