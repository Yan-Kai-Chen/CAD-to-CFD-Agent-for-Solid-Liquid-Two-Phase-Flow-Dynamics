"""Command-line interface for agent-safe FastCFD workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fromcad2cfd_cad import AgentResult

from .capabilities import capability_inventory, capability_markdown
from .fastfluent_backend import (
    run_fastfluent_cavity2d_job,
    run_fastfluent_job,
    write_cavity2d_job,
    write_channel2d_job,
    write_obstacle2d_job,
)
from .mock_runner import run_mock_job, write_demo_job
from .physics_validator import contract_has_blocking_errors, validate_physics
from .prediction import build_prediction_from_output, write_prediction_artifacts
from .preflight import run_preflight
from .registry import registry_inventory, registry_markdown
from .screening import run_parameter_screening
from .scene_compiler import compile_scene_file_to_job, read_scene, validate_scene_semantics, write_scene
from .schemas import read_job
from .paths import unique_path
from .unstructured.diffusion import run_scalar_diffusion_case
from .unstructured.inspect import inspect_mesh_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd fastcfd")
    sub = parser.add_subparsers(dest="command", required=True)

    capabilities = sub.add_parser("capabilities", help="Print the FastCFD capability inventory.")
    capabilities.add_argument("--format", choices=("json", "markdown"), default="json")

    registry = sub.add_parser("registry", help="Print the FastCFD source-of-truth registry.")
    registry.add_argument("--format", choices=("json", "markdown"), default="json")

    preflight = sub.add_parser("preflight", help="Check optional FastFluent source and build environment.")
    preflight.add_argument("--source-root", default=None, help="Explicit FastFluent source root.")

    write_demo = sub.add_parser("write-demo-job", help="Write a public-safe FastCFD mock demo job.")
    write_demo.add_argument("--project", default="fastcfd_mock_cavity2d")
    write_demo.add_argument("--model-name", default="fastcfd_mock_cavity2d")
    write_demo.add_argument("--case-type", default="cavity2d")
    write_demo.add_argument("--backend", default="mock")

    run_mock = sub.add_parser("run-mock-job", help="Run a deterministic FastCFD mock job.")
    run_mock.add_argument("--job-file", required=True)

    validate_job = sub.add_parser("validate-job", help="Validate a FastCFD job and print its physics passport.")
    validate_job.add_argument("--job-file", required=True)
    validate_job.add_argument("--profile", choices=("agent", "ci"), default="agent")

    write_scene_parser = sub.add_parser("write-scene", help="Write a public-safe semantic FastCFD scene.")
    write_scene_parser.add_argument("--project", required=True)
    write_scene_parser.add_argument("--model-name", required=True)
    write_scene_parser.add_argument("--scene-type", choices=("cavity2d", "channel2d", "obstacle2d", "dambreak2d"), default="cavity2d")
    write_scene_parser.add_argument("--length-mm", type=float, default=120.0)
    write_scene_parser.add_argument("--height-mm", type=float, default=40.0)
    write_scene_parser.add_argument("--cell-length-mm", type=float, default=1.0)
    write_scene_parser.add_argument("--obstacle", choices=("circle", "rectangle"), default=None)

    validate_scene_parser = sub.add_parser("validate-scene", help="Validate a semantic FastCFD scene.")
    validate_scene_parser.add_argument("--scene-file", required=True)

    compile_scene_parser = sub.add_parser("compile-scene", help="Compile a semantic FastCFD scene into a validated job.")
    compile_scene_parser.add_argument("--scene-file", required=True)
    compile_scene_parser.add_argument("--project", required=True)
    compile_scene_parser.add_argument("--model-name", default=None)
    compile_scene_parser.add_argument("--backend", choices=("mock", "fastfluent"), default="mock")

    write_cavity = sub.add_parser("write-cavity2d-job", help="Write a controlled real FastFluent cavity2d job.")
    write_cavity.add_argument("--project", default="fastcfd_cavity2d_real")
    write_cavity.add_argument("--model-name", default="fastcfd_cavity2d_real")
    write_cavity.add_argument("--nx", type=int, default=30)
    write_cavity.add_argument("--ny", type=int, default=30)
    write_cavity.add_argument("--total-steps", type=int, default=200)
    write_cavity.add_argument("--output-interval", type=int, default=50)

    write_channel = sub.add_parser("write-channel2d-job", help="Write a controlled real FastFluent channel2d job.")
    write_channel.add_argument("--project", default="fastcfd_channel2d_real")
    write_channel.add_argument("--model-name", default="fastcfd_channel2d_real")
    write_channel.add_argument("--length-mm", type=float, default=120.0)
    write_channel.add_argument("--height-mm", type=float, default=40.0)
    write_channel.add_argument("--cell-length-mm", type=float, default=1.0)
    write_channel.add_argument("--total-steps", type=int, default=200)
    write_channel.add_argument("--output-interval", type=int, default=50)

    write_obstacle = sub.add_parser("write-obstacle2d-job", help="Write a controlled real FastFluent obstacle2d job.")
    write_obstacle.add_argument("--project", default="fastcfd_obstacle2d_real")
    write_obstacle.add_argument("--model-name", default="fastcfd_obstacle2d_real")
    write_obstacle.add_argument("--length-mm", type=float, default=120.0)
    write_obstacle.add_argument("--height-mm", type=float, default=40.0)
    write_obstacle.add_argument("--cell-length-mm", type=float, default=1.0)
    write_obstacle.add_argument("--obstacle", choices=("circle", "rectangle"), default="circle")
    write_obstacle.add_argument("--total-steps", type=int, default=200)
    write_obstacle.add_argument("--output-interval", type=int, default=50)

    run_real = sub.add_parser("run-fastfluent-job", help="Build and run a controlled real FastFluent job.")
    run_real.add_argument("--job-file", required=True)
    run_real.add_argument("--source-root", required=True)
    run_real.add_argument("--build-timeout-sec", type=int, default=240)
    run_real.add_argument("--run-timeout-sec", type=int, default=240)

    run_cavity = sub.add_parser("run-fastfluent-cavity2d-job", help="Build and run a controlled real FastFluent cavity2d job.")
    run_cavity.add_argument("--job-file", required=True)
    run_cavity.add_argument("--source-root", required=True)
    run_cavity.add_argument("--build-timeout-sec", type=int, default=240)
    run_cavity.add_argument("--run-timeout-sec", type=int, default=240)

    predict = sub.add_parser("predict-from-output", help="Build a preliminary CFD prediction report from FastCFD output artifacts.")
    predict.add_argument("--fastcfd-output-dir", required=True)
    predict.add_argument("--job-file", default=None)
    predict.add_argument("--output-dir", default=None)
    predict.add_argument("--model-name", default=None)

    screen = sub.add_parser("screen-parameters", help="Create a bounded pre-run physics screening matrix from a FastCFD job.")
    screen.add_argument("--job-file", required=True)
    screen.add_argument("--velocity-multipliers", default="0.5,1.0,2.0")
    screen.add_argument("--cell-length-multipliers", default="1.0")
    screen.add_argument("--max-variants", type=int, default=12)
    screen.add_argument("--output-dir", default=None)
    screen.add_argument("--model-name", default=None)

    unstructured = sub.add_parser("unstructured", help="Run unstructured FastFluent mesh gateway commands.")
    unstructured_sub = unstructured.add_subparsers(dest="unstructured_command", required=True)
    inspect_mesh = unstructured_sub.add_parser("inspect-mesh", help="Inspect a Gmsh v4 ASCII mesh before any solver execution.")
    inspect_mesh.add_argument("mesh_file", help="Path to a Gmsh .msh v4 ASCII mesh.")
    inspect_mesh.add_argument("--output-dir", default=None, help="Directory for mesh_manifest.json, mesh_quality.json, and mesh.vtu.")
    inspect_mesh.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    inspect_mesh.add_argument("--format", choices=("json", "markdown"), default="json")
    inspect_mesh.add_argument("--no-write-vtu", action="store_true", help="Skip mesh.vtu preview output.")
    solve_diffusion = unstructured_sub.add_parser("solve-diffusion", help="Run a manufactured scalar diffusion benchmark.")
    solve_diffusion.add_argument("mesh_file", help="Path to a Gmsh .msh v4 ASCII mesh.")
    solve_diffusion.add_argument("--output-dir", default=None, help="Directory for diffusion artifacts.")
    solve_diffusion.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_diffusion.add_argument("--manufactured-solution", choices=("linear", "quadratic_bubble"), default="linear")
    solve_diffusion.add_argument("--diffusivity", type=float, default=1.0)
    solve_diffusion.add_argument("--format", choices=("json", "markdown"), default="json")

    mock_demo = sub.add_parser("mock-demo", help="Write and run the deterministic cavity2d mock demo.")
    mock_demo.add_argument("--project", default="fastcfd_mock_cavity2d")
    mock_demo.add_argument("--model-name", default="fastcfd_mock_cavity2d")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "capabilities":
        if args.format == "markdown":
            print(capability_markdown())
        else:
            print(json.dumps(capability_inventory(), ensure_ascii=True, indent=2))
        return 0
    if args.command == "registry":
        if args.format == "markdown":
            print(registry_markdown())
        else:
            print(json.dumps(registry_inventory(), ensure_ascii=True, indent=2))
        return 0
    if args.command == "preflight":
        result = run_preflight(args.source_root).to_dict()
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] in {"success", "partial", "skipped"} else 2
    if args.command == "write-demo-job":
        result = write_demo_job(
            project=args.project,
            model_name=args.model_name,
            case_type=args.case_type,
            backend=args.backend,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "run-mock-job":
        result = run_mock_job(args.job_file)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "validate-job":
        try:
            job = read_job(args.job_file)
            contract = validate_physics(job, profile=args.profile)
            print(json.dumps(contract.to_dict(), ensure_ascii=True, indent=2))
            return 2 if contract_has_blocking_errors(contract) else 0
        except Exception as exc:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="validate_job",
                message="FastCFD job validation failed.",
                errors=[str(exc)],
                metadata={"job_file": args.job_file},
            )
            print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
            return 2
    if args.command == "write-scene":
        result = write_scene(
            project=args.project,
            model_name=args.model_name,
            scene_type=args.scene_type,
            length_mm=args.length_mm,
            height_mm=args.height_mm,
            cell_length_mm=args.cell_length_mm,
            obstacle=args.obstacle,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "validate-scene":
        try:
            scene = read_scene(args.scene_file)
            result = validate_scene_semantics(scene)
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result["status"] in {"passed", "warning"} else 2
        except Exception as exc:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="validate_scene",
                message="FastCFD scene validation failed.",
                errors=[str(exc)],
                metadata={"scene_file": args.scene_file},
            )
            print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
            return 2
    if args.command == "compile-scene":
        try:
            result = compile_scene_file_to_job(
                args.scene_file,
                project=args.project,
                model_name=args.model_name,
                backend=args.backend,
            )
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result["physics_contract"]["status"] in {"passed", "warning"} else 2
        except Exception as exc:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="compile_scene",
                message="FastCFD scene compilation failed.",
                errors=[str(exc)],
                metadata={"scene_file": args.scene_file, "project": args.project},
            )
            print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
            return 2
    if args.command == "write-cavity2d-job":
        result = write_cavity2d_job(
            project=args.project,
            model_name=args.model_name,
            nx=args.nx,
            ny=args.ny,
            total_steps=args.total_steps,
            output_interval=args.output_interval,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-channel2d-job":
        result = write_channel2d_job(
            project=args.project,
            model_name=args.model_name,
            length_mm=args.length_mm,
            height_mm=args.height_mm,
            cell_length_mm=args.cell_length_mm,
            total_steps=args.total_steps,
            output_interval=args.output_interval,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-obstacle2d-job":
        result = write_obstacle2d_job(
            project=args.project,
            model_name=args.model_name,
            length_mm=args.length_mm,
            height_mm=args.height_mm,
            cell_length_mm=args.cell_length_mm,
            obstacle=args.obstacle,
            total_steps=args.total_steps,
            output_interval=args.output_interval,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "run-fastfluent-job":
        result = run_fastfluent_job(
            args.job_file,
            source_root=args.source_root,
            build_timeout_sec=args.build_timeout_sec,
            run_timeout_sec=args.run_timeout_sec,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "run-fastfluent-cavity2d-job":
        result = run_fastfluent_cavity2d_job(
            args.job_file,
            source_root=args.source_root,
            build_timeout_sec=args.build_timeout_sec,
            run_timeout_sec=args.run_timeout_sec,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "predict-from-output":
        try:
            report = build_prediction_from_output(args.fastcfd_output_dir, job_file=args.job_file)
            output_dir = Path(args.output_dir) if args.output_dir else Path(args.fastcfd_output_dir)
            reports_dir = output_dir.parent / "reports"
            paths = write_prediction_artifacts(
                report=report,
                output_dir=output_dir,
                reports_dir=reports_dir,
                model_name=args.model_name or str(report.get("model_name") or "fastcfd_prediction"),
                unique_path=unique_path,
            )
            report["artifacts"] = paths
            print(json.dumps(report, ensure_ascii=True, indent=2))
            return 0 if report.get("status") != "blocked" else 2
        except Exception as exc:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="predict_from_output",
                message="FastCFD prediction report generation failed.",
                errors=[str(exc)],
                metadata={"fastcfd_output_dir": args.fastcfd_output_dir, "job_file": args.job_file},
            )
            print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
            return 2
    if args.command == "screen-parameters":
        try:
            job = read_job(args.job_file)
            output_dir = args.output_dir or str(Path(job.output_dir).parent / "reports")
            result = run_parameter_screening(
                args.job_file,
                velocity_multipliers=_parse_float_list(args.velocity_multipliers),
                cell_length_multipliers=_parse_float_list(args.cell_length_multipliers),
                max_variants=args.max_variants,
                output_dir=output_dir,
                model_name=args.model_name,
            )
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0
        except Exception as exc:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="screen_parameters",
                message="FastCFD parameter screening failed.",
                errors=[str(exc)],
                metadata={"job_file": args.job_file},
            )
            print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
            return 2
    if args.command == "unstructured":
        if args.unstructured_command == "inspect-mesh":
            result = inspect_mesh_file(
                args.mesh_file,
                output_dir=args.output_dir,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
                write_vtu=not args.no_write_vtu,
            )
            if args.format == "markdown":
                quality = result.get("outputs", {}).get("quality", {})
                manifest = result.get("outputs", {}).get("manifest", {})
                print(f"# FastFluent Unstructured Mesh Inspection\n\nStatus: `{result.get('status')}`\n")
                print(f"- Mesh: `{manifest.get('mesh_name')}`")
                print(f"- Cells: `{manifest.get('cell_count')}`")
                print(f"- Boundary zones: `{quality.get('boundary_zone_counts')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-diffusion":
            result = run_scalar_diffusion_case(
                args.mesh_file,
                output_dir=args.output_dir,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
                manufactured_solution=args.manufactured_solution,
                diffusivity=args.diffusivity,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                print(f"# FastFluent Unstructured Scalar Diffusion\n\nStatus: `{result.get('status')}`\n")
                print(f"- Manufactured solution: `{qoi.get('manufactured_solution')}`")
                print(f"- Cell-center L2 error: `{metrics.get('cell_center_l2_error')}`")
                print(f"- Final residual L2: `{metrics.get('final_residual_l2')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
    if args.command == "mock-demo":
        written = write_demo_job(project=args.project, model_name=args.model_name)
        result = run_mock_job(written["job_path"])
        result["written_job"] = written
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    raise AssertionError(f"Unhandled command: {args.command}")


def _parse_float_list(text: str) -> list[float]:
    values = []
    for item in text.split(","):
        stripped = item.strip()
        if stripped:
            values.append(float(stripped))
    if not values:
        raise ValueError("Expected at least one numeric multiplier.")
    return values


if __name__ == "__main__":
    raise SystemExit(main())
