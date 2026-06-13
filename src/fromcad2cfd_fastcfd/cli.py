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
from .fluent_hints import compile_fluent_setup_hints
from .mock_runner import run_mock_job, write_demo_job
from .physics_validator import contract_has_blocking_errors, validate_physics
from .prediction import build_prediction_from_output, write_prediction_artifacts
from .preflight import run_preflight
from .registry import registry_inventory, registry_markdown
from .rheology import run_rheology_benchmark_file, write_demo_rheology_case
from .screening import run_parameter_screening
from .scene_compiler import compile_scene_file_to_job, read_scene, validate_scene_semantics, write_scene
from .schemas import read_job
from .paths import unique_path
from .unstructured.channel_validation import run_channel_convergence_case, run_channel_validation_case
from .unstructured.diffusion import run_scalar_diffusion_case
from .unstructured.flow import run_flow_benchmark_case
from .unstructured.inspect import inspect_mesh_file
from .unstructured.obstacle import run_obstacle_channel_evidence
from .unstructured.projection import run_projection_benchmark_case
from .unstructured.stokes import run_stokes_benchmark_case
from .turbulence import validate_turbulence_case_file, write_demo_turbulence_case
from .vof import validate_vof_case_file, write_demo_vof_case
from .vof_transport import run_vof_lite_transport_benchmark


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

    write_vof = sub.add_parser("write-vof-demo", help="Write a public-safe VOF physics-passport demo case.")
    write_vof.add_argument("--output-dir", default=None, help="Directory for vof_case.json.")
    write_vof.add_argument("--case-name", default="public_dambreak2d_vof_passport")

    validate_vof = sub.add_parser("validate-vof", help="Validate a VOF physics passport and write Fluent setup hints.")
    validate_vof.add_argument("--case-file", required=True)
    validate_vof.add_argument("--output-dir", default=None)
    validate_vof.add_argument("--format", choices=("json", "markdown"), default="json")

    write_turbulence = sub.add_parser("write-turbulence-demo", help="Write a public-safe turbulence passport demo case.")
    write_turbulence.add_argument("--output-dir", default=None, help="Directory for turbulence_case.json.")
    write_turbulence.add_argument("--case-name", default="public_channel2d_turbulence_passport")

    validate_turbulence = sub.add_parser("validate-turbulence", help="Validate a turbulence passport and write Fluent setup hints.")
    validate_turbulence.add_argument("--case-file", required=True)
    validate_turbulence.add_argument("--output-dir", default=None)
    validate_turbulence.add_argument("--format", choices=("json", "markdown"), default="json")

    write_rheology = sub.add_parser("write-rheology-demo", help="Write a public-safe non-Newtonian rheology demo case.")
    write_rheology.add_argument("--output-dir", default=None, help="Directory for rheology_case.json.")
    write_rheology.add_argument("--case-name", default="public_power_law_shear_thinning_passport")

    run_rheology = sub.add_parser("run-rheology-benchmark", help="Run a rheology passport and shear-rate benchmark.")
    run_rheology.add_argument("--case-file", required=True)
    run_rheology.add_argument("--output-dir", default=None)
    run_rheology.add_argument("--format", choices=("json", "markdown"), default="json")

    compile_hints = sub.add_parser("compile-fluent-hints", help="Compile evidence-checked Fluent setup hints from FastFluent artifacts.")
    compile_hints.add_argument("--evidence-files", required=True, help="Comma-separated JSON evidence artifact paths.")
    compile_hints.add_argument("--output-dir", default=None)
    compile_hints.add_argument("--format", choices=("json", "markdown"), default="json")

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
    solve_diffusion.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_diffusion.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_diffusion.add_argument("--max-linear-iterations", type=int, default=None)
    solve_diffusion.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_stokes = unstructured_sub.add_parser("solve-stokes", help="Run a manufactured Stokes momentum benchmark.")
    solve_stokes.add_argument("mesh_file", help="Path to a Gmsh .msh v4 ASCII mesh.")
    solve_stokes.add_argument("--output-dir", default=None, help="Directory for Stokes benchmark artifacts.")
    solve_stokes.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_stokes.add_argument(
        "--manufactured-solution",
        choices=("pressure_driven_shear", "linear_divergence_free", "poiseuille_channel"),
        default="pressure_driven_shear",
    )
    solve_stokes.add_argument("--viscosity", type=float, default=1.0)
    solve_stokes.add_argument("--pressure-gradient", default="1.0,0.0", help="Comma-separated dpdx,dpdy for the manufactured pressure field.")
    solve_stokes.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_stokes.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_stokes.add_argument("--max-linear-iterations", type=int, default=None)
    solve_stokes.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_projection = unstructured_sub.add_parser("solve-projection", help="Run a manufactured pressure-correction projection benchmark.")
    solve_projection.add_argument("mesh_file", help="Path to a Gmsh .msh v4 ASCII mesh.")
    solve_projection.add_argument("--output-dir", default=None, help="Directory for projection benchmark artifacts.")
    solve_projection.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_projection.add_argument("--manufactured-solution", choices=("quadratic_correction", "linear_correction"), default="quadratic_correction")
    solve_projection.add_argument("--correction-strength", type=float, default=1.0)
    solve_projection.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_projection.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_projection.add_argument("--max-linear-iterations", type=int, default=None)
    solve_projection.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_flow = unstructured_sub.add_parser("solve-flow-benchmark", help="Run the iterative projection-flow benchmark.")
    solve_flow.add_argument("mesh_file", help="Path to a Gmsh .msh v4 ASCII mesh.")
    solve_flow.add_argument("--output-dir", default=None, help="Directory for flow benchmark artifacts.")
    solve_flow.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_flow.add_argument("--iterations", type=int, default=5)
    solve_flow.add_argument("--correction-strength", type=float, default=1.0)
    solve_flow.add_argument("--relaxation", type=float, default=1.0)
    solve_flow.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_flow.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_flow.add_argument("--max-linear-iterations", type=int, default=None)
    solve_flow.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_channel = unstructured_sub.add_parser("solve-channel-validation", help="Run a boundary-aware Poiseuille channel validation case.")
    solve_channel.add_argument("mesh_file", help="Path to a Gmsh .msh v4 ASCII mesh.")
    solve_channel.add_argument("--output-dir", default=None, help="Directory for channel validation artifacts.")
    solve_channel.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_channel.add_argument("--viscosity", type=float, default=1.0)
    solve_channel.add_argument("--pressure-drop", type=float, default=1.0)
    solve_channel.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_channel.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_channel.add_argument("--max-linear-iterations", type=int, default=None)
    solve_channel.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_channel_convergence = unstructured_sub.add_parser(
        "solve-channel-convergence",
        help="Run channel validation across generated or provided mesh levels.",
    )
    solve_channel_convergence.add_argument("mesh_files", nargs="*", help="Optional Gmsh .msh files. If omitted, public synthetic meshes are generated.")
    solve_channel_convergence.add_argument("--output-dir", default=None, help="Directory for channel convergence artifacts.")
    solve_channel_convergence.add_argument("--mesh-levels", default="2,4,8", help="Comma-separated generated mesh levels when mesh files are omitted.")
    solve_channel_convergence.add_argument("--viscosity", type=float, default=1.0)
    solve_channel_convergence.add_argument("--pressure-drop", type=float, default=1.0)
    solve_channel_convergence.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_channel_convergence.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_channel_convergence.add_argument("--max-linear-iterations", type=int, default=None)
    solve_channel_convergence.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_obstacle = unstructured_sub.add_parser("solve-obstacle-channel", help="Generate or inspect a public body-fitted obstacle-channel evidence case.")
    solve_obstacle.add_argument("mesh_file", nargs="?", help="Optional Gmsh .msh file. If omitted, a public synthetic mesh is generated.")
    solve_obstacle.add_argument("--output-dir", default=None, help="Directory for obstacle-channel artifacts.")
    solve_obstacle.add_argument("--nx", type=int, default=16)
    solve_obstacle.add_argument("--ny", type=int, default=8)
    solve_obstacle.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_vof_lite = unstructured_sub.add_parser("solve-vof-lite", help="Run a bounded VOF-lite alpha transport benchmark.")
    solve_vof_lite.add_argument("mesh_file", nargs="?", help="Optional Gmsh .msh file. If omitted, a public unit-square channel mesh is generated.")
    solve_vof_lite.add_argument("--output-dir", default=None, help="Directory for VOF-lite artifacts.")
    solve_vof_lite.add_argument("--steps", type=int, default=20)
    solve_vof_lite.add_argument("--time-step-s", type=float, default=0.02)
    solve_vof_lite.add_argument("--velocity", default="0.1,0.0", help="Comma-separated ux,uy.")
    solve_vof_lite.add_argument("--inlet-alpha", type=float, default=1.0)
    solve_vof_lite.add_argument("--initial-column-fraction", type=float, default=0.35)
    solve_vof_lite.add_argument("--format", choices=("json", "markdown"), default="json")

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
    if args.command == "write-vof-demo":
        result = write_demo_vof_case(output_dir=args.output_dir, case_name=args.case_name)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "validate-vof":
        result = validate_vof_case_file(args.case_file, output_dir=args.output_dir)
        if args.format == "markdown":
            passport = result.get("outputs", {}).get("passport", {})
            checks = passport.get("checks", {})
            print(f"# FastFluent VOF Physics Passport\n\nStatus: `{result.get('status')}`\n")
            print(f"- Passport status: `{passport.get('status')}`")
            print(f"- Reynolds number: `{checks.get('reynolds_number')}`")
            print(f"- Weber number: `{checks.get('weber_number')}`")
            print(f"- Bond number: `{checks.get('bond_number')}`")
            print(f"- VOF Courant number: `{checks.get('courant_number')}`")
            print(f"- Errors: `{result.get('errors', [])}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "write-turbulence-demo":
        result = write_demo_turbulence_case(output_dir=args.output_dir, case_name=args.case_name)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "validate-turbulence":
        result = validate_turbulence_case_file(args.case_file, output_dir=args.output_dir)
        if args.format == "markdown":
            passport = result.get("outputs", {}).get("passport", {})
            checks = passport.get("checks", {})
            print(f"# FastFluent Turbulence Passport\n\nStatus: `{result.get('status')}`\n")
            print(f"- Passport status: `{passport.get('status')}`")
            print(f"- Reynolds number: `{checks.get('reynolds_number')}`")
            print(f"- Estimated y-plus: `{checks.get('estimated_y_plus')}`")
            print(f"- Flow regime: `{passport.get('flow_regime')}`")
            print(f"- Errors: `{result.get('errors', [])}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "write-rheology-demo":
        result = write_demo_rheology_case(output_dir=args.output_dir, case_name=args.case_name)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "run-rheology-benchmark":
        result = run_rheology_benchmark_file(args.case_file, output_dir=args.output_dir)
        if args.format == "markdown":
            passport = result.get("outputs", {}).get("passport", {})
            checks = passport.get("checks", {})
            print(f"# FastFluent Rheology Benchmark\n\nStatus: `{result.get('status')}`\n")
            print(f"- Passport status: `{passport.get('status')}`")
            print(f"- Model: `{passport.get('model')}`")
            print(f"- Trend: `{checks.get('trend')}`")
            print(f"- Viscosity ratio: `{checks.get('viscosity_ratio')}`")
            print(f"- Errors: `{result.get('errors', [])}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "compile-fluent-hints":
        result = compile_fluent_setup_hints(
            [Path(item.strip()) for item in args.evidence_files.split(",") if item.strip()],
            output_dir=args.output_dir,
        )
        if args.format == "markdown":
            compiled = result.get("outputs", {}).get("compiled_hints", {})
            print(f"# FastFluent Fluent Setup Hints\n\nStatus: `{result.get('status')}`\n")
            print(f"- Hint count: `{compiled.get('hint_count')}`")
            print(f"- Evidence file count: `{compiled.get('evidence_file_count')}`")
            print(f"- Errors: `{result.get('errors', [])}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
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
        if args.unstructured_command == "solve-flow-benchmark":
            result = run_flow_benchmark_case(
                args.mesh_file,
                output_dir=args.output_dir,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
                iterations=args.iterations,
                correction_strength=args.correction_strength,
                relaxation=args.relaxation,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                print(f"# FastFluent Unstructured Flow Benchmark\n\nStatus: `{result.get('status')}`\n")
                print(f"- Iterations: `{qoi.get('iterations')}`")
                print(f"- Initial divergence L2: `{metrics.get('initial_divergence_l2')}`")
                print(f"- Final divergence L2: `{metrics.get('final_divergence_l2')}`")
                print(f"- Global divergence reduction ratio: `{metrics.get('global_divergence_reduction_ratio')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-channel-validation":
            result = run_channel_validation_case(
                args.mesh_file,
                output_dir=args.output_dir,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
                viscosity=args.viscosity,
                pressure_drop=args.pressure_drop,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                print(f"# FastFluent Unstructured Channel Validation\n\nStatus: `{result.get('status')}`\n")
                print(f"- Pressure drop: `{qoi.get('pressure_drop')}`")
                print(f"- Cell-center velocity L2 error: `{metrics.get('cell_center_velocity_l2_error')}`")
                print(f"- Cell divergence L2: `{metrics.get('cell_divergence_l2')}`")
                print(f"- Mass-balance absolute flux: `{metrics.get('mass_balance_abs_flux')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-channel-convergence":
            result = run_channel_convergence_case(
                mesh_files=[Path(item) for item in args.mesh_files] if args.mesh_files else None,
                mesh_levels=tuple(_parse_int_list(args.mesh_levels)),
                output_dir=args.output_dir,
                viscosity=args.viscosity,
                pressure_drop=args.pressure_drop,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
            )
            if args.format == "markdown":
                convergence = result.get("outputs", {}).get("convergence", {})
                print(f"# FastFluent Unstructured Channel Convergence\n\nStatus: `{result.get('status')}`\n")
                print(f"- Case count: `{convergence.get('case_count')}`")
                print(f"- Monotonic error decrease: `{convergence.get('monotonic_error_decrease')}`")
                print(f"- Observed orders: `{convergence.get('observed_orders')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-obstacle-channel":
            result = run_obstacle_channel_evidence(
                args.mesh_file,
                output_dir=args.output_dir,
                nx=args.nx,
                ny=args.ny,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                print(f"# FastFluent Public Obstacle Channel\n\nStatus: `{result.get('status')}`\n")
                print(f"- Cells: `{qoi.get('cell_count')}`")
                print(f"- Blockage ratio: `{qoi.get('blockage_ratio')}`")
                print(f"- Boundary zones: `{qoi.get('boundary_zone_counts')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-vof-lite":
            result = run_vof_lite_transport_benchmark(
                args.mesh_file,
                output_dir=args.output_dir,
                steps=args.steps,
                time_step_s=args.time_step_s,
                velocity_m_s=_parse_velocity(args.velocity),
                inlet_alpha=args.inlet_alpha,
                initial_column_fraction=args.initial_column_fraction,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                print(f"# FastFluent VOF-Lite Alpha Transport\n\nStatus: `{result.get('status')}`\n")
                print(f"- Max Courant number: `{metrics.get('max_courant_number')}`")
                print(f"- Alpha range: `{metrics.get('min_alpha')}` to `{metrics.get('max_alpha')}`")
                print(f"- Relative balance error: `{metrics.get('relative_balance_error')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-projection":
            result = run_projection_benchmark_case(
                args.mesh_file,
                output_dir=args.output_dir,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
                manufactured_solution=args.manufactured_solution,
                correction_strength=args.correction_strength,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                print(f"# FastFluent Unstructured Projection Benchmark\n\nStatus: `{result.get('status')}`\n")
                print(f"- Manufactured solution: `{qoi.get('manufactured_solution')}`")
                print(f"- Predicted divergence L2: `{metrics.get('predicted_divergence_l2')}`")
                print(f"- Corrected divergence L2: `{metrics.get('corrected_divergence_l2')}`")
                print(f"- Divergence reduction ratio: `{metrics.get('divergence_reduction_ratio')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-stokes":
            result = run_stokes_benchmark_case(
                args.mesh_file,
                output_dir=args.output_dir,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
                manufactured_solution=args.manufactured_solution,
                viscosity=args.viscosity,
                pressure_gradient=_parse_pressure_gradient(args.pressure_gradient),
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                pressure = qoi.get("pressure", {})
                print(f"# FastFluent Unstructured Stokes Benchmark\n\nStatus: `{result.get('status')}`\n")
                print(f"- Manufactured solution: `{qoi.get('manufactured_solution')}`")
                print(f"- Pressure gradient: `{pressure.get('gradient')}`")
                print(f"- Cell-center velocity L2 error: `{metrics.get('cell_center_velocity_l2_error')}`")
                print(f"- Cell divergence L2: `{metrics.get('cell_divergence_l2')}`")
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
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                linear_system = qoi.get("linear_system", {})
                print(f"# FastFluent Unstructured Scalar Diffusion\n\nStatus: `{result.get('status')}`\n")
                print(f"- Manufactured solution: `{qoi.get('manufactured_solution')}`")
                print(f"- Linear solver: `{linear_system.get('method')}`")
                print(f"- Matrix nnz: `{linear_system.get('nnz')}`")
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


def _parse_int_list(text: str) -> list[int]:
    values = []
    for item in text.split(","):
        stripped = item.strip()
        if stripped:
            values.append(int(stripped))
    if not values:
        raise ValueError("Expected at least one integer value.")
    return values


def _parse_pressure_gradient(text: str) -> tuple[float, float]:
    values = _parse_float_list(text)
    if len(values) != 2:
        raise ValueError("Expected pressure gradient as two comma-separated values: dpdx,dpdy.")
    return (values[0], values[1])


def _parse_velocity(text: str) -> tuple[float, float]:
    values = _parse_float_list(text)
    if len(values) != 2:
        raise ValueError("Expected velocity as two comma-separated values: ux,uy.")
    return (values[0], values[1])


if __name__ == "__main__":
    raise SystemExit(main())
