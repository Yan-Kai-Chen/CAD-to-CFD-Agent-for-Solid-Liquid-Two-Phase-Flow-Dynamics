"""Command-line interface for mesh preprocessing and coarse solidification."""

from __future__ import annotations

import argparse
import json

from .freecad_solidify import freecad_preflight, run_freecad_solidify_job, write_solidify_freecad_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd mesh")
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="Detect FreeCADCmd availability for mesh solidification.")
    preflight.add_argument("--freecadcmd", default=None, help="Explicit FreeCADCmd executable path.")

    write_job = sub.add_parser("write-solidify-freecad-job", help="Write a copied-input FreeCAD mesh-to-solid job without executing it.")
    write_job.add_argument("--input-file", required=True)
    write_job.add_argument("--project", default="mesh_solidify_freecad")
    write_job.add_argument("--model-name", default=None)
    write_job.add_argument("--sew-tolerance-mm", type=float, default=0.05)
    write_job.add_argument("--no-refine-shape", action="store_true")
    write_job.add_argument("--no-save-fcstd", action="store_true")
    write_job.add_argument("--no-export-step", action="store_true")

    run_job = sub.add_parser("run-solidify-freecad-job", help="Execute a previously written FreeCAD mesh-to-solid job.")
    run_job.add_argument("--job-file", required=True)
    run_job.add_argument("--freecadcmd", default=None)
    run_job.add_argument("--timeout-sec", type=int, default=3600)

    solidify = sub.add_parser("solidify-freecad", help="Write and optionally execute a FreeCAD mesh-to-solid job.")
    solidify.add_argument("--input-file", required=True)
    solidify.add_argument("--project", default="mesh_solidify_freecad")
    solidify.add_argument("--model-name", default=None)
    solidify.add_argument("--sew-tolerance-mm", type=float, default=0.05)
    solidify.add_argument("--no-refine-shape", action="store_true")
    solidify.add_argument("--no-save-fcstd", action="store_true")
    solidify.add_argument("--no-export-step", action="store_true")
    solidify.add_argument("--freecadcmd", default=None)
    solidify.add_argument("--timeout-sec", type=int, default=3600)
    solidify.add_argument("--no-execute", action="store_true", help="Only write the job JSON.")

    return parser


def _write_job_from_args(args: argparse.Namespace) -> dict[str, object]:
    return write_solidify_freecad_job(
        args.input_file,
        project=args.project,
        model_name=args.model_name,
        sew_tolerance_mm=args.sew_tolerance_mm,
        refine_shape=not args.no_refine_shape,
        save_fcstd=not args.no_save_fcstd,
        export_step=not args.no_export_step,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preflight":
        result = freecad_preflight(args.freecadcmd).to_dict()
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] == "success" else 2
    if args.command == "write-solidify-freecad-job":
        result = _write_job_from_args(args)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "run-solidify-freecad-job":
        result = run_freecad_solidify_job(args.job_file, freecadcmd=args.freecadcmd, timeout_sec=args.timeout_sec)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "solidify-freecad":
        written = _write_job_from_args(args)
        if args.no_execute:
            print(json.dumps(written, ensure_ascii=True, indent=2))
            return 0
        result = run_freecad_solidify_job(written["job_path"], freecadcmd=args.freecadcmd, timeout_sec=args.timeout_sec)
        result["written_job"] = written
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
