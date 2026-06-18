"""CLI for HyperMesh CFD meshing workflow contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapter import (
    parse_hmbatch_log,
    parse_surface_mesh_log,
    run_hmbatch_script,
    write_smoke_blockmesh_tcl,
    write_surface_mesh_reports,
    write_surface_mesh_tcl,
)
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

    smoke = sub.add_parser("write-smoke-tcl", help="Write a controlled hmbatch smoke-test Tcl script.")
    smoke.add_argument("--output", required=True, help="Output Tcl path.")
    smoke.add_argument("--hm-output", required=True, help="Output HyperMesh .hm path created by the smoke script.")

    surface_tcl = sub.add_parser("write-surface-mesh-tcl", help="Write a controlled 2D surface-mesh Tcl script.")
    surface_tcl.add_argument("--geometry-input", required=True, help="CAD geometry input path.")
    surface_tcl.add_argument("--output", required=True, help="Output Tcl path.")
    surface_tcl.add_argument("--hm-output", required=True, help="Output HyperMesh .hm path.")
    surface_tcl.add_argument("--target-size-m", type=float, required=True, help="Target surface element size in meters.")

    run_tcl = sub.add_parser("run-tcl-template", help="Run a FromCAD2CFD-generated Tcl script with hmbatch.")
    run_tcl.add_argument("--script", required=True, help="Generated Tcl script path.")
    run_tcl.add_argument("--log", required=True, help="Log output path.")
    run_tcl.add_argument("--manifest", default=None, help="Optional run manifest JSON path.")
    run_tcl.add_argument("--runtime-root", default=None, help="Optional local Altair installation root.")
    run_tcl.add_argument("--timeout-s", type=int, default=300, help="Timeout in seconds.")

    parse_log = sub.add_parser("parse-hmbatch-log", help="Parse FromCAD2CFD markers from a hmbatch log.")
    parse_log.add_argument("--log", required=True, help="hmbatch log path.")

    parse_surface = sub.add_parser("parse-surface-mesh-log", help="Parse a controlled surface-mesh log.")
    parse_surface.add_argument("--log", required=True, help="hmbatch log path.")
    parse_surface.add_argument("--json-report", default=None, help="Optional JSON report path.")
    parse_surface.add_argument("--markdown-report", default=None, help="Optional Markdown report path.")
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
    if args.command == "write-smoke-tcl":
        print(json.dumps(write_smoke_blockmesh_tcl(args.output, args.hm_output), ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-surface-mesh-tcl":
        print(
            json.dumps(
                write_surface_mesh_tcl(
                    args.output,
                    geometry_input=args.geometry_input,
                    hm_output=args.hm_output,
                    target_size_m=args.target_size_m,
                ),
                ensure_ascii=True,
                indent=2,
            )
        )
        return 0
    if args.command == "run-tcl-template":
        result = run_hmbatch_script(
            args.script,
            log_path=args.log,
            manifest_path=args.manifest,
            runtime_root=args.runtime_root,
            timeout_s=args.timeout_s,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] == "passed" else 2
    if args.command == "parse-hmbatch-log":
        print(json.dumps(parse_hmbatch_log(args.log), ensure_ascii=True, indent=2))
        return 0
    if args.command == "parse-surface-mesh-log":
        if args.json_report or args.markdown_report:
            result = write_surface_mesh_reports(
                args.log,
                json_report=args.json_report,
                markdown_report=args.markdown_report,
            )
        else:
            result = parse_surface_mesh_log(args.log)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] in {"passed", "review"} else 2
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
