"""Safe Fluent postprocessing MCP tool declarations and handlers."""

from __future__ import annotations

from typing import Any

from fromcad2cfd_postprocessing.monitor_parser import parse_monitor_file
from fromcad2cfd_postprocessing.summary import summarize_run
from fromcad2cfd_postprocessing.video_plan import write_video_plan


ALLOWED_TOOLS = [
    "fromcad2cfd_post_tool_inventory",
    "fromcad2cfd_post_parse_monitor",
    "fromcad2cfd_post_summarize_run",
    "fromcad2cfd_post_write_video_plan",
]

DISABLED_TOOLS = [
    "execute_shell",
    "run_ffmpeg",
    "fluent_gui_automation",
    "read_private_case_data",
    "export_private_case_data",
    "delete_file",
    "overwrite_file",
    "claim_solid_structural_stress",
]

TOOL_DESCRIPTIONS = {
    "fromcad2cfd_post_tool_inventory": "Return safe Fluent postprocessing MCP tools and disabled tool names.",
    "fromcad2cfd_post_parse_monitor": "Parse a Fluent report monitor file into rows and first/last state.",
    "fromcad2cfd_post_summarize_run": "Summarize Fluent global and optional wall monitor files.",
    "fromcad2cfd_post_write_video_plan": "Write a public-safe autosave frame plan for a field video.",
}


def tool_inventory() -> dict[str, object]:
    return {
        "allowed_tools": ALLOWED_TOOLS,
        "disabled_tools": DISABLED_TOOLS,
        "tool_descriptions": TOOL_DESCRIPTIONS,
    }


def fromcad2cfd_post_tool_inventory() -> dict[str, object]:
    return tool_inventory()


def fromcad2cfd_post_parse_monitor(monitor_path: str, min_columns: int = 2, include_rows: bool = False) -> dict[str, Any]:
    return parse_monitor_file(monitor_path, min_columns=min_columns, include_rows=include_rows)


def fromcad2cfd_post_summarize_run(
    global_monitor: str,
    wall_monitor: str | None = None,
    output_dir: str | None = None,
    model_name: str = "fluent_post_summary",
) -> dict[str, Any]:
    return summarize_run(global_monitor, wall_monitor=wall_monitor, output_dir=output_dir, model_name=model_name)


def fromcad2cfd_post_write_video_plan(
    autosave_dir: str,
    output_path: str,
    field: str,
    time_step_s: float = 0.001,
    interval_s: float = 0.1,
) -> dict[str, Any]:
    return write_video_plan(
        autosave_dir,
        output_path=output_path,
        field=field,
        time_step_s=time_step_s,
        interval_s=interval_s,
    )


MCP_TOOL_FUNCTIONS = [
    fromcad2cfd_post_tool_inventory,
    fromcad2cfd_post_parse_monitor,
    fromcad2cfd_post_summarize_run,
    fromcad2cfd_post_write_video_plan,
]
