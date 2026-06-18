"""Safe HyperMesh Meshing MCP tool declarations and handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fromcad2cfd_hypermesh_meshing.runtime import locate_hypermesh_runtime
from fromcad2cfd_hypermesh_meshing.schemas import (
    hypermesh_python_template,
    hypermesh_tcl_template,
    read_json,
    validate_meshing_plan,
)


ALLOWED_TOOLS = [
    "fromcad2cfd_hypermesh_meshing_tool_inventory",
    "fromcad2cfd_hypermesh_meshing_locate_runtime",
    "fromcad2cfd_hypermesh_meshing_validate_plan",
    "fromcad2cfd_hypermesh_meshing_write_python_template",
    "fromcad2cfd_hypermesh_meshing_write_tcl_template",
]

DISABLED_TOOLS = [
    "execute_python",
    "execute_tcl",
    "raw_hypermesh_command",
    "raw_gui_command_injection",
    "launch_hypermesh_without_validated_plan",
    "delete_file",
    "overwrite_file",
    "upload_private_geometry_or_mesh",
]

TOOL_DESCRIPTIONS = {
    "fromcad2cfd_hypermesh_meshing_tool_inventory": "Return safe HyperMesh Meshing MCP tools and disabled tool names.",
    "fromcad2cfd_hypermesh_meshing_locate_runtime": "Locate local HyperMesh / HyperWorks executables.",
    "fromcad2cfd_hypermesh_meshing_validate_plan": "Validate a public-safe HyperMesh CFD meshing plan JSON file.",
    "fromcad2cfd_hypermesh_meshing_write_python_template": "Write an advisory HyperMesh Python template from a validated plan.",
    "fromcad2cfd_hypermesh_meshing_write_tcl_template": "Write an advisory HyperMesh Tcl template from a validated plan.",
}


def tool_inventory() -> dict[str, object]:
    return {
        "allowed_tools": ALLOWED_TOOLS,
        "disabled_tools": DISABLED_TOOLS,
        "tool_descriptions": TOOL_DESCRIPTIONS,
    }


def fromcad2cfd_hypermesh_meshing_tool_inventory() -> dict[str, object]:
    return tool_inventory()


def fromcad2cfd_hypermesh_meshing_locate_runtime(extra_roots: list[str] | None = None) -> dict[str, Any]:
    return locate_hypermesh_runtime(extra_roots)


def fromcad2cfd_hypermesh_meshing_validate_plan(plan_path: str, public_mode: bool = True) -> dict[str, Any]:
    return validate_meshing_plan(read_json(plan_path), public_mode=public_mode)


def fromcad2cfd_hypermesh_meshing_write_python_template(plan_path: str, output_path: str) -> dict[str, Any]:
    plan = read_json(plan_path)
    validation = validate_meshing_plan(plan, public_mode=False)
    if validation["status"] != "passed":
        return validation
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(hypermesh_python_template(plan), encoding="utf-8")
    return {"status": "success", "template": str(output)}


def fromcad2cfd_hypermesh_meshing_write_tcl_template(plan_path: str, output_path: str) -> dict[str, Any]:
    plan = read_json(plan_path)
    validation = validate_meshing_plan(plan, public_mode=False)
    if validation["status"] != "passed":
        return validation
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(hypermesh_tcl_template(plan), encoding="utf-8")
    return {"status": "success", "template": str(output)}


MCP_TOOL_FUNCTIONS = [
    fromcad2cfd_hypermesh_meshing_tool_inventory,
    fromcad2cfd_hypermesh_meshing_locate_runtime,
    fromcad2cfd_hypermesh_meshing_validate_plan,
    fromcad2cfd_hypermesh_meshing_write_python_template,
    fromcad2cfd_hypermesh_meshing_write_tcl_template,
]
