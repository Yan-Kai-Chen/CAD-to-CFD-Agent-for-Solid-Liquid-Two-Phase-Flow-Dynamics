from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .app import (
    run_create_cylinder,
    run_phase2_modeling_demo,
    run_phase3_advanced_demo,
    run_phase4_complete_demo,
    run_preflight,
)
from .cfd_templates import available_templates, parse_param_overrides, write_cfd_template_plan
from .fluent_handoff import write_fluent_handoff_from_report
from .import_cleanup import run_phase9_faceted_sphere_cleanup_demo
from .plan_executor import execute_plan_file
from .safe_edit import execute_safe_edit_plan_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd solidworks")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", help="Check SolidWorks COM availability and local templates.")

    cylinder = sub.add_parser("create-cylinder", help="Create a controlled test cylinder.")
    cylinder.add_argument("--project", default="test_project")
    cylinder.add_argument("--radius-mm", type=float, default=10.0)
    cylinder.add_argument("--height-mm", type=float, default=20.0)
    cylinder.add_argument("--hidden", action="store_true", help="Do not force SolidWorks visible.")

    phase2 = sub.add_parser("create-modeling-demo", help="Run Phase2 modeling operation smoke tests.")
    phase2.add_argument("--project", default="phase2_modeling_demo")
    phase2.add_argument("--hidden", action="store_true", help="Do not force SolidWorks visible.")

    phase3 = sub.add_parser("create-advanced-demo", help="Run Phase3 advanced modeling operation smoke tests.")
    phase3.add_argument("--project", default="phase3_advanced_modeling_demo")
    phase3.add_argument("--hidden", action="store_true", help="Do not force SolidWorks visible.")

    phase4 = sub.add_parser("create-complete-demo", help="Run Phase4 complete modeling operation smoke tests.")
    phase4.add_argument("--project", default="phase4_complete_modeling_demo")
    phase4.add_argument("--hidden", action="store_true", help="Do not force SolidWorks visible.")

    plan = sub.add_parser("execute-plan", help="Execute a SolidWorks Agent JSON modeling plan.")
    plan.add_argument("--plan", required=True, help="Path to a workspace-local JSON plan file.")
    plan.add_argument("--hidden", action="store_true", help="Do not force SolidWorks visible.")

    safe_edit = sub.add_parser("safe-edit", help="Safely edit an existing copied SolidWorks part from a JSON plan.")
    safe_edit.add_argument("--plan", required=True, help="Path to a workspace-local safe-edit JSON plan file.")
    safe_edit.add_argument("--hidden", action="store_true", help="Do not force SolidWorks visible.")

    cfd_plan = sub.add_parser("write-cfd-plan", help="Write a CFD-oriented SolidWorks Agent plan from a named template.")
    cfd_plan.add_argument("--template", required=True, choices=available_templates())
    cfd_plan.add_argument("--project", default="phase7_cfd_templates")
    cfd_plan.add_argument("--model-name", default=None)
    cfd_plan.add_argument("--output", default=None, help="Workspace-local output JSON path. Defaults to project input directory.")
    cfd_plan.add_argument("--param", action="append", default=[], help="Template parameter override as key=value. Can be repeated.")

    fluent_handoff = sub.add_parser("write-fluent-handoff", help="Write a geometry-only Fluent handoff manifest from a successful execution report.")
    fluent_handoff.add_argument("--report", required=True, help="Workspace-local SolidWorks Agent JSON report.")
    fluent_handoff.add_argument("--project", default="phase8_fluent_handoff")

    phase9 = sub.add_parser("create-faceted-sphere-cleanup-demo", help="Run Phase9 faceted sphere audit and analytic rebuild demo.")
    phase9.add_argument("--project", default="phase9_import_cleanup_demo")
    phase9.add_argument("--radius-mm", type=float, default=20.0)
    phase9.add_argument("--latitude-segments", type=int, default=24)
    phase9.add_argument("--hidden", action="store_true", help="Do not force SolidWorks visible.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preflight":
        result = run_preflight()
    elif args.command == "create-cylinder":
        result = run_create_cylinder(
            project=args.project,
            radius_mm=args.radius_mm,
            height_mm=args.height_mm,
            visible=not args.hidden,
        )
    elif args.command == "create-modeling-demo":
        result = run_phase2_modeling_demo(
            project=args.project,
            visible=not args.hidden,
        )
    elif args.command == "create-advanced-demo":
        result = run_phase3_advanced_demo(
            project=args.project,
            visible=not args.hidden,
        )
    elif args.command == "create-complete-demo":
        result = run_phase4_complete_demo(
            project=args.project,
            visible=not args.hidden,
        )
    elif args.command == "execute-plan":
        result = execute_plan_file(
            Path(args.plan),
            visible=not args.hidden,
        )
    elif args.command == "safe-edit":
        result = execute_safe_edit_plan_file(
            Path(args.plan),
            visible=not args.hidden,
        )
    elif args.command == "write-cfd-plan":
        result = write_cfd_template_plan(
            args.template,
            project=args.project,
            model_name=args.model_name,
            output_path=Path(args.output) if args.output else None,
            params=parse_param_overrides(args.param),
        )
    elif args.command == "write-fluent-handoff":
        result = write_fluent_handoff_from_report(
            Path(args.report),
            project=args.project,
        )
    elif args.command == "create-faceted-sphere-cleanup-demo":
        result = run_phase9_faceted_sphere_cleanup_demo(
            project=args.project,
            radius_mm=args.radius_mm,
            latitude_segments=args.latitude_segments,
            visible=not args.hidden,
        )
    else:  # pragma: no cover
        raise AssertionError(args.command)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"success", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

