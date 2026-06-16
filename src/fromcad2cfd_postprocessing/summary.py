"""Postprocessing summaries for Fluent report monitor files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .monitor_parser import parse_monitor_file


SUMMARY_SCHEMA_VERSION = "fromcad2cfd_fluent_post_summary_v1"


GLOBAL_COLUMNS = [
    "Time Step",
    "flow-time",
    "delta-time",
    "iters-per-timestep",
    "vol_avg_abs_pressure",
    "vol_avg_temperature",
    "vol_max_temperature",
    "vol_min_temperature",
    "vol_max_velocity",
    "vol_avg_h2o_mass_fraction",
    "vol_avg_o2_mass_fraction",
    "vol_avg_n2_mass_fraction",
    "inlet_mass_flow_rate",
]

WALL_COLUMNS = [
    "Time Step",
    "flow-time",
    "delta-time",
    "all_walls_avg_abs_pressure",
    "all_walls_max_abs_pressure",
    "all_walls_avg_wall_adjacent_temperature",
    "all_walls_max_wall_adjacent_temperature",
    "all_walls_avg_wall_shear",
    "all_walls_max_wall_shear",
    "all_walls_total_heat_transfer_rate",
    "outer_wall_avg_abs_pressure",
    "outer_wall_max_abs_pressure",
    "outer_wall_avg_wall_adjacent_temperature",
    "outer_wall_max_wall_adjacent_temperature",
    "outer_wall_total_heat_transfer_rate",
    "model_avg_abs_pressure",
    "model_max_abs_pressure",
    "model_avg_wall_adjacent_temperature",
    "model_max_wall_adjacent_temperature",
]


def summarize_run(
    global_monitor: str | Path,
    *,
    wall_monitor: str | Path | None = None,
    output_dir: str | Path | None = None,
    model_name: str = "fluent_post_summary",
) -> dict[str, Any]:
    global_data = parse_monitor_file(global_monitor, min_columns=13, column_names=GLOBAL_COLUMNS, include_rows=True)
    global_rows = global_data.get("rows") or []
    if not global_rows:
        raise ValueError(f"No numeric global monitor rows found: {global_monitor}")
    final = global_rows[-1]
    summary: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": "success",
        "model_name": model_name,
        "inputs": {"global_monitor": str(global_monitor), "wall_monitor": str(wall_monitor) if wall_monitor else None},
        "global": {
            "row_count": len(global_rows),
            "final": {
                "step": int(final["Time Step"]),
                "flow_time_s": final["flow-time"],
                "avg_abs_pressure_pa": final["vol_avg_abs_pressure"],
                "avg_abs_pressure_bar": final["vol_avg_abs_pressure"] / 100000.0,
                "avg_temperature_k": final["vol_avg_temperature"],
                "avg_temperature_c": final["vol_avg_temperature"] - 273.15,
                "max_temperature_c": final["vol_max_temperature"] - 273.15,
                "min_temperature_c": final["vol_min_temperature"] - 273.15,
                "avg_h2o_mass_fraction": final["vol_avg_h2o_mass_fraction"],
                "inlet_mass_flow_rate_kg_s": final["inlet_mass_flow_rate"],
            },
            "peaks": {
                "max_temperature_c": max(row["vol_max_temperature"] - 273.15 for row in global_rows),
                "max_pressure_bar": max(row["vol_avg_abs_pressure"] / 100000.0 for row in global_rows),
                "max_velocity_m_s": max(row["vol_max_velocity"] for row in global_rows),
            },
        },
        "interpretation_notes": [
            "Pressure metrics are absolute pressure unless the monitor source says otherwise.",
            "Fluent pressure on a wall is a normal fluid-load proxy, not solid structural stress.",
            "Wall shear is a tangential fluid-load proxy.",
        ],
    }
    if wall_monitor:
        wall_data = parse_monitor_file(wall_monitor, min_columns=19, column_names=WALL_COLUMNS, include_rows=True)
        wall_rows = wall_data.get("rows") or []
        if wall_rows:
            wall_final = wall_rows[-1]
            summary["wall"] = {
                "row_count": len(wall_rows),
                "final": {
                    "step": int(wall_final["Time Step"]),
                    "flow_time_s": wall_final["flow-time"],
                    "all_wall_adjacent_avg_temperature_c": wall_final["all_walls_avg_wall_adjacent_temperature"] - 273.15,
                    "all_wall_adjacent_max_temperature_c": wall_final["all_walls_max_wall_adjacent_temperature"] - 273.15,
                    "outer_wall_heat_absorption_kw": -wall_final["outer_wall_total_heat_transfer_rate"] / 1000.0,
                    "all_wall_heat_absorption_kw": -wall_final["all_walls_total_heat_transfer_rate"] / 1000.0,
                    "model_max_pressure_bar": wall_final["model_max_abs_pressure"] / 100000.0,
                    "model_max_wall_adjacent_temperature_c": wall_final["model_max_wall_adjacent_temperature"] - 273.15,
                },
                "peaks": {
                    "max_model_pressure_bar": max(row["model_max_abs_pressure"] / 100000.0 for row in wall_rows),
                    "max_wall_shear_pa": max(row["all_walls_max_wall_shear"] for row in wall_rows),
                },
            }
    if output_dir:
        report_dir = Path(output_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        json_path = report_dir / f"{model_name}_summary.json"
        md_path = report_dir / f"{model_name}_summary.md"
        json_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        md_path.write_text(_markdown_summary(summary), encoding="utf-8")
        summary["reports"] = {"json": str(json_path), "markdown": str(md_path)}
    return summary


def compare_summaries(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_final = left["global"]["final"]
    right_final = right["global"]["final"]
    return {
        "schema_version": "fromcad2cfd_fluent_post_compare_v1",
        "status": "success",
        "left_model_name": left.get("model_name"),
        "right_model_name": right.get("model_name"),
        "delta_final": {
            "avg_temperature_c": right_final["avg_temperature_c"] - left_final["avg_temperature_c"],
            "avg_abs_pressure_bar": right_final["avg_abs_pressure_bar"] - left_final["avg_abs_pressure_bar"],
            "avg_h2o_mass_fraction": right_final["avg_h2o_mass_fraction"] - left_final["avg_h2o_mass_fraction"],
        },
    }


def _markdown_summary(summary: dict[str, Any]) -> str:
    final = summary["global"]["final"]
    lines = [
        f"# Fluent Postprocessing Summary: {summary['model_name']}",
        "",
        "## Final Global State",
        "",
        f"- Step: `{final['step']}`",
        f"- Flow time: `{final['flow_time_s']:.6f} s`",
        f"- Average absolute pressure: `{final['avg_abs_pressure_bar']:.6f} bar`",
        f"- Average temperature: `{final['avg_temperature_c']:.3f} C`",
        f"- Maximum temperature: `{final['max_temperature_c']:.3f} C`",
        f"- Average H2O mass fraction: `{final['avg_h2o_mass_fraction']:.6g}`",
        "",
    ]
    if "wall" in summary:
        wall = summary["wall"]["final"]
        lines.extend(
            [
                "## Final Wall Indicators",
                "",
                f"- All-wall heat absorption: `{wall['all_wall_heat_absorption_kw']:.3f} kW`",
                f"- Outer-wall heat absorption: `{wall['outer_wall_heat_absorption_kw']:.3f} kW`",
                f"- Model max pressure: `{wall['model_max_pressure_bar']:.6f} bar`",
                f"- Model max wall-adjacent temperature: `{wall['model_max_wall_adjacent_temperature_c']:.3f} C`",
                "",
            ]
        )
    lines.extend(["## Notes", "", *[f"- {note}" for note in summary["interpretation_notes"]], ""])
    return "\n".join(lines)
