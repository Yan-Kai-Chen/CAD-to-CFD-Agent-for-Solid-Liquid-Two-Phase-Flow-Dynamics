"""Safety instructions for future MCP wrappers."""

MCP_SAFETY_POLICY = """
Expose high-level CAD operations only. Do not expose arbitrary Python,
raw COM calls, direct file deletion, or overwrite primitives. All model edits
must operate on copied working files and must emit Markdown and JSON reports.
"""
