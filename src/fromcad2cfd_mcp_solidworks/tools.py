"""Planned MCP tool names for the SolidWorks module."""

SAFE_TOOL_NAMES = [
    "fromcad2cfd_solidworks_preflight",
    "fromcad2cfd_solidworks_create_test_geometry",
    "fromcad2cfd_solidworks_inspect_model",
    "fromcad2cfd_solidworks_safe_edit_dimension",
    "fromcad2cfd_solidworks_export_step",
    "fromcad2cfd_solidworks_get_last_report",
]

DISALLOWED_TOOL_NAMES = [
    "execute_python",
    "raw_com_call",
    "delete_file",
    "overwrite_file",
    "run_macro",
]
