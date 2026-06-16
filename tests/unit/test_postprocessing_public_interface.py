from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_mcp_postprocessing.server import server_descriptor
from fromcad2cfd_mcp_postprocessing.tools import DISABLED_TOOLS, tool_inventory
from fromcad2cfd_postprocessing.monitor_parser import parse_monitor_file
from fromcad2cfd_postprocessing.summary import summarize_run
from fromcad2cfd_postprocessing.video_plan import write_video_plan


GLOBAL_TEXT = '''"global_monitors"
"Time Step" "flow-time etc.."
("Time Step" "flow-time" "delta-time" "iters-per-timestep" "vol_avg_abs_pressure" "vol_avg_temperature" "vol_max_temperature" "vol_min_temperature" "vol_max_velocity" "vol_avg_h2o_mass_fraction" "vol_avg_o2_mass_fraction" "vol_avg_n2_mass_fraction" "inlet_mass_flow_rate")
0 0 0.001 0 101325 293.15 293.15 293.15 0 0.0 0.232 0.768 0
100 0.1 0.001 20 118500 315.0 443.15 293.15 18.0 0.050 0.220 0.730 0.61
200 0.2 0.001 20 130000 334.0 444.0 293.45 46.0 0.106 0.207 0.687 0.61
'''

WALL_TEXT = '''"wall_exposure_indicators"
"Time Step" "flow-time etc.."
("Time Step" "flow-time" "delta-time" "all_walls_avg_abs_pressure" "all_walls_max_abs_pressure" "all_walls_avg_wall_adjacent_temperature" "all_walls_max_wall_adjacent_temperature" "all_walls_avg_wall_shear" "all_walls_max_wall_shear" "all_walls_total_heat_transfer_rate" "outer_wall_avg_abs_pressure" "outer_wall_max_abs_pressure" "outer_wall_avg_wall_adjacent_temperature" "outer_wall_max_wall_adjacent_temperature" "outer_wall_total_heat_transfer_rate" "model_avg_abs_pressure" "model_max_abs_pressure" "model_avg_wall_adjacent_temperature" "model_max_wall_adjacent_temperature")
0 0 0.001 101325 101325 293.15 293.15 0 0 0 101325 101325 293.15 293.15 0 101325 101325 293.15 293.15
200 0.2 0.001 130100 130500 333.0 442.7 0.33 6.6 -26000 130120 130500 331.0 442.7 -22500 130000 130400 344.0 438.2
'''


def _write_monitors(tmp_path: Path) -> tuple[Path, Path]:
    global_path = tmp_path / "global_monitors.out"
    wall_path = tmp_path / "wall_exposure_indicators.out"
    global_path.write_text(GLOBAL_TEXT, encoding="utf-8")
    wall_path.write_text(WALL_TEXT, encoding="utf-8")
    return global_path, wall_path


def test_parse_monitor_file_detects_header_and_rows(tmp_path):
    global_path, _ = _write_monitors(tmp_path)

    result = parse_monitor_file(global_path, min_columns=13, include_rows=False)

    assert result["status"] == "parsed"
    assert result["row_count"] == 3
    assert result["column_names"][4] == "vol_avg_abs_pressure"
    assert result["last_row"]["vol_avg_temperature"] == 334.0


def test_summarize_run_writes_json_and_markdown(tmp_path):
    global_path, wall_path = _write_monitors(tmp_path)

    summary = summarize_run(global_path, wall_monitor=wall_path, output_dir=tmp_path / "reports", model_name="unit")

    assert summary["status"] == "success"
    assert summary["global"]["final"]["avg_temperature_c"] == 60.85000000000002
    assert summary["wall"]["final"]["all_wall_heat_absorption_kw"] == 26.0
    assert Path(summary["reports"]["json"]).exists()
    assert Path(summary["reports"]["markdown"]).exists()


def test_root_cli_routes_post_summary(tmp_path, capsys):
    global_path, wall_path = _write_monitors(tmp_path)

    exit_code = root_main(
        [
            "post",
            "summarize-run",
            "--global-monitor",
            str(global_path),
            "--wall-monitor",
            str(wall_path),
            "--output-dir",
            str(tmp_path / "reports"),
            "--model-name",
            "unit_cli",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["global"]["final"]["step"] == 200


def test_write_video_plan_from_autosave_names(tmp_path):
    autosave = tmp_path / "autosave"
    autosave.mkdir()
    for step in (20, 100, 200):
        (autosave / f"unit-{step:05d}.dat.h5").write_text("placeholder", encoding="utf-8")

    result = write_video_plan(autosave, output_path=tmp_path / "video_plan.json", field="temperature", time_step_s=0.001, interval_s=0.1)

    assert result["status"] == "success"
    assert result["frame_count"] == 2
    assert result["frames"][0]["step"] == 100


def test_postprocessing_mcp_inventory_is_safe():
    inventory = tool_inventory()
    descriptor = server_descriptor()

    assert "fromcad2cfd_post_summarize_run" in inventory["allowed_tools"]
    assert "execute_shell" in DISABLED_TOOLS
    assert "claim_solid_structural_stress" in descriptor["disabled_tools"]
    assert "run_ffmpeg" not in inventory["allowed_tools"]
