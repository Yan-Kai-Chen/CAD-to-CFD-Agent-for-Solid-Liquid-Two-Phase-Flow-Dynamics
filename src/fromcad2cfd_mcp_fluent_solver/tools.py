"""Safe Fluent Solver MCP tool declarations and handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fromcad2cfd_fluent_solver.monitor_contract import monitor_contract
from fromcad2cfd_fluent_solver.patch_preview import apply_solver_plan_patch_preview, write_patch_preview_bundle
from fromcad2cfd_fluent_solver.schemas import (
    pyfluent_template,
    read_json,
    validate_resume_plan,
    validate_solver_plan,
)
from fromcad2cfd_fluent_solver.solver_plan_v2 import (
    create_minimal_solver_plan_v2,
    validate_solver_plan_v2,
    write_solver_plan_v2_json,
    write_solver_plan_v2_report,
)


ALLOWED_TOOLS = [
    "fromcad2cfd_fluent_solver_tool_inventory",
    "fromcad2cfd_fluent_solver_monitor_contract",
    "fromcad2cfd_fluent_solver_validate_plan",
    "fromcad2cfd_fluent_solver_write_pyfluent_template",
    "fromcad2cfd_fluent_solver_validate_resume_plan",
    "fromcad2cfd_fluent_solver_write_plan_v2_demo",
    "fromcad2cfd_fluent_solver_preview_patch",
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
    "fromcad2cfd_fluent_solver_write_plan_v2_demo": "Write a preview-only Fluent Solver Plan v2 demo JSON and Markdown report.",
    "fromcad2cfd_fluent_solver_preview_patch": "Apply a FastFluent solver_plan_patch.json to a Solver Plan v2 preview without launching Fluent.",
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


def fromcad2cfd_fluent_solver_write_plan_v2_demo(output_dir: str, case_name: str = "public_solver_plan_v2_demo") -> dict[str, Any]:
    output = Path(output_dir)
    plan = create_minimal_solver_plan_v2(case_name)
    write_solver_plan_v2_json(plan, output / "base_solver_plan_v2.json")
    write_solver_plan_v2_report(plan, output / "base_solver_plan_v2_report.md")
    validation = validate_solver_plan_v2(plan)
    return {
        "status": "success" if validation.is_valid else "failed",
        "artifacts": {
            "base_solver_plan_v2": str(output / "base_solver_plan_v2.json"),
            "base_solver_plan_v2_report": str(output / "base_solver_plan_v2_report.md"),
        },
        "validation": validation.to_dict(),
    }


def fromcad2cfd_fluent_solver_preview_patch(base_plan_path: str, patch_path: str, output_dir: str) -> dict[str, Any]:
    result = apply_solver_plan_patch_preview(read_json(base_plan_path), read_json(patch_path))
    output = Path(output_dir)
    write_patch_preview_bundle(result, output)
    return {
        "status": "success" if result.preview_status != "blocked" else "blocked",
        "preview_status": result.preview_status,
        "artifacts": {
            "patched_solver_plan_preview": str(output / "patched_solver_plan_preview.json"),
            "patch_application_report": str(output / "patch_application_report.md"),
            "conflict_report": str(output / "conflict_report.json"),
            "before_after_diff": str(output / "before_after_diff.md"),
            "reviewer_checklist": str(output / "reviewer_checklist.md"),
        },
        "conflicts": result.conflicts,
        "blocking_errors": result.blocking_errors,
    }


MCP_TOOL_FUNCTIONS = [
    fromcad2cfd_fluent_solver_tool_inventory,
    fromcad2cfd_fluent_solver_monitor_contract,
    fromcad2cfd_fluent_solver_validate_plan,
    fromcad2cfd_fluent_solver_write_pyfluent_template,
    fromcad2cfd_fluent_solver_validate_resume_plan,
    fromcad2cfd_fluent_solver_write_plan_v2_demo,
    fromcad2cfd_fluent_solver_preview_patch,
]
