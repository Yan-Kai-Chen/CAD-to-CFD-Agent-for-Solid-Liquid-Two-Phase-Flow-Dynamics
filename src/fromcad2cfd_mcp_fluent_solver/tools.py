"""Safe Fluent Solver MCP tool declarations and handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fromcad2cfd_fluent_solver.monitor_contract import monitor_contract
from fromcad2cfd_fluent_solver.schemas import (
    pyfluent_template,
    read_json,
    validate_resume_plan,
    validate_solver_plan,
)


ALLOWED_TOOLS = [
    "fromcad2cfd_fluent_solver_tool_inventory",
    "fromcad2cfd_fluent_solver_monitor_contract",
    "fromcad2cfd_fluent_solver_validate_plan",
    "fromcad2cfd_fluent_solver_write_pyfluent_template",
    "fromcad2cfd_fluent_solver_validate_resume_plan",
]

DISABLED_TOOLS = [
    "execute_python",
    "raw_pyfluent_call",
    "run_arbitrary_fluent_journal",
    "run_arbitrary_fluent_tui",
    "launch_fluent_solver",
    "raw_source_expression_edit",
    "delete_file",
    "overwrite_file",
    "upload_private_case_data",
]

TOOL_DESCRIPTIONS = {
    "fromcad2cfd_fluent_solver_tool_inventory": "Return safe Fluent Solver MCP tools and disabled tool names.",
    "fromcad2cfd_fluent_solver_monitor_contract": "Return required Fluent report monitor definitions.",
    "fromcad2cfd_fluent_solver_validate_plan": "Validate a public-safe Fluent Solver plan JSON file.",
    "fromcad2cfd_fluent_solver_write_pyfluent_template": "Write an advisory PyFluent setup template from a validated plan.",
    "fromcad2cfd_fluent_solver_validate_resume_plan": "Validate a Fluent resume plan JSON file.",
}


def tool_inventory() -> dict[str, object]:
    return {
        "allowed_tools": ALLOWED_TOOLS,
        "disabled_tools": DISABLED_TOOLS,
        "tool_descriptions": TOOL_DESCRIPTIONS,
    }


def fromcad2cfd_fluent_solver_tool_inventory() -> dict[str, object]:
    return tool_inventory()


def fromcad2cfd_fluent_solver_monitor_contract() -> dict[str, Any]:
    return monitor_contract()


def fromcad2cfd_fluent_solver_validate_plan(plan_path: str, public_mode: bool = True) -> dict[str, Any]:
    return validate_solver_plan(read_json(plan_path), public_mode=public_mode)


def fromcad2cfd_fluent_solver_write_pyfluent_template(plan_path: str, output_path: str) -> dict[str, Any]:
    plan = read_json(plan_path)
    validation = validate_solver_plan(plan, public_mode=False)
    if validation["status"] != "passed":
        return validation
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(pyfluent_template(plan), encoding="utf-8")
    return {"status": "success", "template": str(output)}


def fromcad2cfd_fluent_solver_validate_resume_plan(resume_plan_path: str, public_mode: bool = True) -> dict[str, Any]:
    return validate_resume_plan(read_json(resume_plan_path), public_mode=public_mode)


MCP_TOOL_FUNCTIONS = [
    fromcad2cfd_fluent_solver_tool_inventory,
    fromcad2cfd_fluent_solver_monitor_contract,
    fromcad2cfd_fluent_solver_validate_plan,
    fromcad2cfd_fluent_solver_write_pyfluent_template,
    fromcad2cfd_fluent_solver_validate_resume_plan,
]
