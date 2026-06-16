"""Safety instructions for the postprocessing MCP server."""

POSTPROCESSING_MCP_INSTRUCTIONS = """
Expose only high-level Fluent postprocessing tools.

Never expose arbitrary shell execution, raw ffmpeg execution, direct Fluent GUI
automation, arbitrary case/data export, delete operations, overwrite
operations, or tools that package private Fluent case/data files.

The public surface parses Fluent report monitors, writes deterministic
summaries, creates public-safe video plans, and compares summary JSON files.
Pressure is a fluid normal-load proxy and wall shear is a tangential
fluid-load proxy; neither is solid structural stress.
"""
