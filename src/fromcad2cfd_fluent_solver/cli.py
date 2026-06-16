"""CLI for public-safe Fluent Solver planning helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .monitor_contract import monitor_contract
from .schemas import pyfluent_template, read_json, validate_resume_plan, validate_solver_plan, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd fluent-solver")
    sub = parser.add_subparsers(dest="command")

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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
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
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
