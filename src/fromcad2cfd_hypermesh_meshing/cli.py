"""CLI for HyperMesh CFD meshing workflow contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runtime import locate_hypermesh_runtime
from .schemas import (
    hypermesh_python_template,
    hypermesh_tcl_template,
    read_json,
    validate_meshing_plan,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd hypermesh-meshing")
    sub = parser.add_subparsers(dest="command")

    locate = sub.add_parser("locate-runtime", help="Locate local HyperMesh executables.")
    locate.add_argument("--root", action="append", default=[], help="Additional Altair installation root.")

    validate = sub.add_parser("validate-plan", help="Validate a HyperMesh meshing plan JSON.")
    validate.add_argument("--plan", required=True, help="Path to meshing plan JSON.")
    validate.add_argument("--allow-absolute", action="store_true", help="Allow local absolute paths for private use.")

    py_template = sub.add_parser("write-python-template", help="Write an advisory HyperMesh Python template.")
    py_template.add_argument("--plan", required=True, help="Path to meshing plan JSON.")
    py_template.add_argument("--output", required=True, help="Output Python path.")

    tcl_template = sub.add_parser("write-tcl-template", help="Write an advisory HyperMesh Tcl template.")
    tcl_template.add_argument("--plan", required=True, help="Path to meshing plan JSON.")
    tcl_template.add_argument("--output", required=True, help="Output Tcl path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "locate-runtime":
        print(json.dumps(locate_hypermesh_runtime(args.root), ensure_ascii=True, indent=2))
        return 0
    if args.command == "validate-plan":
        result = validate_meshing_plan(read_json(args.plan), public_mode=not args.allow_absolute)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] == "passed" else 2
    if args.command == "write-python-template":
        plan = read_json(args.plan)
        result = validate_meshing_plan(plan, public_mode=False)
        if result["status"] != "passed":
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 2
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(hypermesh_python_template(plan), encoding="utf-8")
        print(json.dumps({"status": "success", "template": str(output)}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-tcl-template":
        plan = read_json(args.plan)
        result = validate_meshing_plan(plan, public_mode=False)
        if result["status"] != "passed":
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 2
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(hypermesh_tcl_template(plan), encoding="utf-8")
        print(json.dumps({"status": "success", "template": str(output)}, ensure_ascii=True, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
