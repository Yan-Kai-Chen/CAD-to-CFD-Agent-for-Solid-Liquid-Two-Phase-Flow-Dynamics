"""CLI for public-safe Fluent Solver planning helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .monitor_contract import monitor_contract
from .patch_preview import (
    apply_solver_plan_patch_preview,
    write_patch_preview_bundle,
    write_plan_v2_patch_preview_demo,
)
from .schemas import pyfluent_template, read_json, validate_resume_plan, validate_solver_plan, write_json
from .solver_plan_v2 import (
    create_minimal_solver_plan_v2,
    validate_solver_plan_v2,
    write_solver_plan_v2_json,
    write_solver_plan_v2_report,
)


CAPABILITIES = {
    "schema_version": "fromcad2cfd_fluent_solver_capabilities_v1",
    "backend": "fluent_solver",
    "status": "preview_planning",
    "capabilities": {
        "fluent_solver_plan_v1": {
            "status": "implemented",
            "entrypoint": "fromcad2cfd fluent-solver validate-plan",
        },
        "fluent_solver_plan_v2": {
            "status": "implemented_preview_only",
            "entrypoint": "fromcad2cfd fluent-solver write-plan-v2-demo",
        },
        "fluent_solver_patch_preview": {
            "status": "implemented_preview_only",
            "entrypoint": "fromcad2cfd fluent-solver preview-patch",
        },
        "fluent_solver_reviewer_checklist": {
            "status": "implemented_preview_only",
            "entrypoint": "fromcad2cfd fluent-solver preview-patch",
        },
    },
    "disabled_capabilities": [
        "fluent_launch",
        "pyfluent_execution",
        "raw_tui_execution",
        "udf_generation",
        "case_data_editing",
    ],
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd fluent-solver")
    sub = parser.add_subparsers(dest="command")

    capabilities = sub.add_parser("capabilities", help="Print safe Fluent Solver planning capabilities.")
    capabilities.add_argument("--format", choices=("json", "markdown"), default="json")

    validate = sub.add_parser("validate-plan", help="Validate a public-safe Fluent Solver plan JSON.")
    validate.add_argument("--plan", required=True, help="Path to solver plan JSON.")
    validate.add_argument("--allow-absolute", action="store_true", help="Allow local absolute paths for private local use.")

    template = sub.add_parser("write-template", help="Write an advisory PyFluent setup template from a solver plan.")
    template.add_argument("--plan", required=True, help="Path to solver plan JSON.")
    template.add_argument("--output", required=True, help="Output Python template path.")

    contract = sub.add_parser("monitor-contract", help="Print the required Fluent monitor contract.")
    contract.add_argument("--output", default=None, help="Optional JSON output path.")

    resume = sub.add_parser("validate-resume", help="Validate a Fluent resume plan JSON.")
    resume.add_argument("--plan", required=True, help="Path to resume plan JSON.")
    resume.add_argument("--allow-absolute", action="store_true", help="Allow local absolute paths for private local use.")

    write_plan_v2 = sub.add_parser("write-plan-v2-demo", help="Write a public Solver Plan v2 preview demo.")
    write_plan_v2.add_argument("--output-dir", required=True, help="Output directory for base Solver Plan v2 artifacts.")
    write_plan_v2.add_argument("--case-name", default="public_solver_plan_v2_demo")

    preview_patch = sub.add_parser("preview-patch", help="Apply a FastFluent solver_plan_patch.json to a Solver Plan v2 preview.")
    preview_patch.add_argument("--base-plan", required=True, help="Path to base_solver_plan_v2.json.")
    preview_patch.add_argument("--patch", required=True, help="Path to solver_plan_patch.json.")
    preview_patch.add_argument("--output-dir", required=True, help="Output directory for preview artifacts.")
    preview_patch.add_argument("--format", choices=("json", "markdown"), default="json")

    preview_demo = sub.add_parser("plan-v2-patch-preview-demo", help="Write a complete public Solver Plan v2 patch-preview demo tree.")
    preview_demo.add_argument("--patch", default=None, help="Optional FastFluent solver_plan_patch.json. If omitted, a synthetic public patch is used.")
    preview_demo.add_argument("--output-dir", required=True, help="Output directory for the full demo tree.")
    preview_demo.add_argument("--case-name", default="public_solver_plan_v2_patch_demo")
    preview_demo.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "capabilities":
        if args.format == "markdown":
            print("# Fluent Solver Capabilities\n")
            for name, info in CAPABILITIES["capabilities"].items():
                print(f"- `{name}`: `{info['status']}` via `{info['entrypoint']}`")
            print("\n## Disabled Capabilities\n")
            for item in CAPABILITIES["disabled_capabilities"]:
                print(f"- `{item}`")
        else:
            print(json.dumps(CAPABILITIES, ensure_ascii=True, indent=2))
        return 0
    if args.command == "validate-plan":
        result = validate_solver_plan(read_json(args.plan), public_mode=not args.allow_absolute)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] == "passed" else 2
    if args.command == "write-template":
        plan = read_json(args.plan)
        result = validate_solver_plan(plan, public_mode=False)
        if result["status"] != "passed":
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 2
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(pyfluent_template(plan), encoding="utf-8")
        print(json.dumps({"status": "success", "template": str(output)}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "monitor-contract":
        payload = monitor_contract()
        if args.output:
            write_json(args.output, payload)
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0
    if args.command == "validate-resume":
        result = validate_resume_plan(read_json(args.plan), public_mode=not args.allow_absolute)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] == "passed" else 2
    if args.command == "write-plan-v2-demo":
        output_dir = Path(args.output_dir)
        plan = create_minimal_solver_plan_v2(args.case_name)
        write_solver_plan_v2_json(plan, output_dir / "base_solver_plan_v2.json")
        write_solver_plan_v2_report(plan, output_dir / "base_solver_plan_v2_report.md")
        validation = validate_solver_plan_v2(plan)
        result = {
            "status": "success" if validation.is_valid else "failed",
            "validation": validation.to_dict(),
            "artifacts": {
                "base_solver_plan_v2": str(output_dir / "base_solver_plan_v2.json"),
                "base_solver_plan_v2_report": str(output_dir / "base_solver_plan_v2_report.md"),
            },
        }
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if validation.is_valid else 2
    if args.command == "preview-patch":
        base_plan = read_json(args.base_plan)
        patch = read_json(args.patch)
        result = apply_solver_plan_patch_preview(base_plan, patch)
        write_patch_preview_bundle(result, Path(args.output_dir))
        payload = {
            "status": "success" if result.preview_status != "blocked" else "blocked",
            "preview_status": result.preview_status,
            "applied_operation_count": len(result.applied_operations),
            "skipped_operation_count": len(result.skipped_operations),
            "conflict_count": len(result.conflicts),
            "blocking_error_count": len(result.blocking_errors),
            "artifacts": {
                "patched_solver_plan_preview": str(Path(args.output_dir) / "patched_solver_plan_preview.json"),
                "patch_application_report": str(Path(args.output_dir) / "patch_application_report.md"),
                "conflict_report": str(Path(args.output_dir) / "conflict_report.json"),
                "before_after_diff": str(Path(args.output_dir) / "before_after_diff.md"),
                "reviewer_checklist": str(Path(args.output_dir) / "reviewer_checklist.md"),
            },
        }
        if args.format == "markdown":
            print("# Fluent Solver Plan v2 Patch Preview\n")
            print(f"- Preview status: `{payload['preview_status']}`")
            print(f"- Applied operations: `{payload['applied_operation_count']}`")
            print(f"- Conflicts: `{payload['conflict_count']}`")
            print(f"- Blocking errors: `{payload['blocking_error_count']}`")
        else:
            print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0 if result.preview_status != "blocked" else 2
    if args.command == "plan-v2-patch-preview-demo":
        result = write_plan_v2_patch_preview_demo(output_dir=args.output_dir, patch=args.patch, case_name=args.case_name)
        if args.format == "markdown":
            print("# Fluent Solver Plan v2 Patch Preview Demo\n")
            print(f"- Status: `{result['status']}`")
            print(f"- Preview status: `{result['preview_status']}`")
            for key, value in result["artifacts"].items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] == "success" else 2
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
