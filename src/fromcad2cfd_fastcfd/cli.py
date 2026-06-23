"""Command-line interface for agent-safe FastCFD workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fromcad2cfd_cad import AgentResult

from .boundary.boundary_contract import run_boundary_contract_demo
from .capabilities import capability_inventory, capability_markdown
from .core.case_spec import explain_case_spec_markdown, read_case_spec, validate_case_spec
from .core.evidence_bundle import summarize_evidence_bundle_markdown, validate_evidence_bundle
from .controlled_runner import (
    controlled_runner_markdown,
    controlled_runner_validation_markdown,
    run_controlled_runner,
    run_controlled_runner_demo,
    validate_controlled_runner,
)
from .execution_gate import (
    audit_execution_gate,
    execution_gate_markdown,
    execution_gate_validation_markdown,
    run_execution_gate_demo,
    validate_execution_gate,
)
from .fastfluent_backend import (
    run_fastfluent_cavity2d_job,
    run_fastfluent_job,
    write_cavity2d_job,
    write_channel2d_job,
    write_obstacle2d_job,
)
from .fluent_hints import compile_fluent_setup_hints
from .fluent_patch_compiler import (
    compile_solver_plan_patch_from_passport,
    run_existing_passport_patch_demo,
    run_steam_air_handoff_demo,
    write_solver_plan_patch_bundle,
)
from .flow_pack import (
    build_flow_pack,
    export_flow_pack_evidence_bundle,
    flow_pack_markdown,
    flow_pack_validation_markdown,
    validate_flow_pack,
)
from .horizontal_validation_pack import run_horizontal_validation_pack
from .materials.material_contract import run_material_contract_demo
from .mesh.mesh_gateway import generate_structured_mesh_demo, inspect_mesh_gateway
from .mock_runner import run_mock_job, write_demo_job
from .motion import motion_report_markdown, sample_motion_contract, validate_motion_contract, write_demo_motion_case
from .motion_adapter import adapt_motion_to_mesh, motion_adapter_markdown
from .motion_quasi_steady import (
    moving_obstacle_markdown,
    quasi_steady_markdown,
    run_moving_obstacle_evidence_demo,
    run_quasi_steady_motion_case,
)
from .motion_solver_preflight import motion_solver_preflight_markdown, run_motion_solver_preflight
from .native_simulation_pack import run_native_simulation_validation_pack
from .physics_validator import contract_has_blocking_errors, validate_physics
from .prediction import build_prediction_from_output, write_prediction_artifacts
from .practical_native_demo_pack import run_practical_native_demo_pack
from .practical_setup import run_practical_native_setup_demo
from .preflight import run_preflight
from .registry import registry_inventory, registry_markdown
from .result_pack import (
    compile_native_result_pack,
    compile_result_pack,
    result_pack_markdown,
    result_pack_validation_markdown,
    run_result_pack_demo,
    validate_result_pack,
)
from .route_plan import (
    compile_route_plan,
    route_plan_markdown,
    route_plan_validation_markdown,
    run_route_plan_demo,
    validate_route_plan,
)
from .route_selector import route_catalog, route_selection_markdown, run_route_selector_demo, select_route
from .rheology import run_rheology_benchmark_file, write_demo_rheology_case
from .screening import run_parameter_screening
from .scene_compiler import compile_scene_file_to_job, read_scene, validate_scene_semantics, write_scene
from .schemas import read_job
from .paths import unique_path
from .solver_capability_matrix import solver_capability_matrix, solver_capability_matrix_markdown, write_solver_capability_matrix
from .solid_liquid_suspension import (
    run_solid_liquid_handoff_demo,
    validate_solid_liquid_suspension_case_file,
    write_demo_solid_liquid_case,
)
from .steam_air_condensation import validate_steam_air_condensation_case_file, write_demo_steam_air_case
from .steam_air_condensation_v2 import (
    run_steam_air_v2_demo,
    validate_steam_air_condensation_v2_case_file,
    write_demo_steam_air_v2_case,
)
from .transport_core import (
    demo_transport_case,
    run_transport_coupling_case,
    run_transport_coupling_demo,
    transport_markdown,
    validate_transport_case,
)
from .unstructured.channel_validation import run_channel_convergence_case, run_channel_validation_case
from .unstructured.benchmark_suite import run_public_benchmark_suite
from .unstructured.case_runner import run_unstructured_case_file, write_public_steady_channel_case
from .unstructured.diffusion import run_scalar_diffusion_case
from .unstructured.flow import run_flow_benchmark_case
from .unstructured.inspect import inspect_mesh_file
from .unstructured.kepsilon_channel import run_kepsilon_channel_case, run_pressure_corrected_kepsilon_channel_case
from .unstructured.obstacle import run_obstacle_channel_evidence
from .unstructured.projection import run_projection_benchmark_case
from .unstructured.stokes import run_stokes_benchmark_case
from .unstructured.sst_channel import run_sst_channel_case
from .unstructured.steady_incompressible import run_steady_incompressible_case
from .unstructured.tetra_validation import run_tetra_diffusion_case
from .unstructured.turbulent_channel import run_turbulent_channel_case
from .unstructured.turbulence_ladder import run_turbulence_ladder_case
from .turbulence import validate_turbulence_case_file, write_demo_turbulence_case
from .vof import validate_vof_case_file, write_demo_vof_case
from .vof_transport import run_vof_lite_transport_benchmark
from .wax_rheology_phase_change import (
    run_wax_rheology_handoff_demo,
    validate_wax_rheology_phase_change_case_file,
    write_demo_wax_rheology_case,
)
from .workflow_runner import run_workflow, run_workflow_demo, workflow_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd fastcfd")
    sub = parser.add_subparsers(dest="command", required=True)

    capabilities = sub.add_parser("capabilities", help="Print the FastCFD capability inventory.")
    capabilities.add_argument("--format", choices=("json", "markdown"), default="json")

    solver_matrix = sub.add_parser("solver-capability-matrix", help="Print or write the FastFluent native solver capability matrix.")
    solver_matrix.add_argument("--output-dir", default=None)
    solver_matrix.add_argument("--format", choices=("json", "markdown"), default="markdown")

    motion = sub.add_parser("motion", help="Validate and sample safe kinematic motion contracts.")
    motion_sub = motion.add_subparsers(dest="motion_command", required=True)
    motion_demo = motion_sub.add_parser("write-demo", help="Write a public motion contract demo file.")
    motion_demo.add_argument("--output-dir", required=True)
    motion_demo.add_argument("--format", choices=("json", "markdown"), default="json")
    motion_validate = motion_sub.add_parser("validate", help="Validate a motion contract JSON file.")
    motion_validate.add_argument("motion_file")
    motion_validate.add_argument("--format", choices=("json", "markdown"), default="json")
    motion_sample = motion_sub.add_parser("sample", help="Sample a motion contract into JSON, CSV, and Markdown evidence.")
    motion_sample.add_argument("motion_file")
    motion_sample.add_argument("--output-dir", required=True)
    motion_sample.add_argument("--time-step-s", type=float, default=0.1)
    motion_sample.add_argument("--total-time-s", type=float, default=1.0)
    motion_sample.add_argument("--format", choices=("json", "markdown"), default="json")
    motion_adapt = motion_sub.add_parser("adapt-mesh", help="Bind a motion contract to mesh boundary patches and motion-CFL gates.")
    motion_adapt.add_argument("motion_file")
    motion_adapt.add_argument("mesh_file")
    motion_adapt.add_argument("--output-dir", required=True)
    motion_adapt.add_argument("--time-step-s", type=float, default=0.1)
    motion_adapt.add_argument("--total-time-s", type=float, default=1.0)
    motion_adapt.add_argument("--characteristic-length-m", type=float, default=None)
    motion_adapt.add_argument("--cfl-warn", type=float, default=0.5)
    motion_adapt.add_argument("--cfl-fail", type=float, default=1.0)
    motion_adapt.add_argument("--format", choices=("json", "markdown"), default="json")
    motion_solver_preflight = motion_sub.add_parser(
        "solver-preflight",
        help="Check whether a motion mesh adapter may be attached before solver dispatch.",
    )
    motion_solver_preflight.add_argument("motion_adapter_file")
    motion_solver_preflight.add_argument("--output-dir", required=True)
    motion_solver_preflight.add_argument("--case-file", default=None)
    motion_solver_preflight.add_argument("--solver-family", default="steady_incompressible")
    motion_solver_preflight.add_argument(
        "--execution-mode",
        choices=("static_grid_motion_evidence", "require_dynamic_mesh", "block_on_motion"),
        default="static_grid_motion_evidence",
    )
    motion_solver_preflight.add_argument("--format", choices=("json", "markdown"), default="json")
    motion_quasi = motion_sub.add_parser("quasi-steady", help="Run a bounded quasi-steady static-grid motion evidence sequence.")
    motion_quasi.add_argument("case_file")
    motion_quasi.add_argument("motion_adapter_file")
    motion_quasi.add_argument("--output-dir", required=True)
    motion_quasi.add_argument(
        "--execution-mode",
        choices=("static_grid_motion_evidence", "require_dynamic_mesh", "block_on_motion"),
        default="static_grid_motion_evidence",
    )
    motion_quasi.add_argument("--max-snapshots", type=int, default=None)
    motion_quasi.add_argument("--format", choices=("json", "markdown"), default="json")
    motion_obstacle = motion_sub.add_parser("moving-obstacle-demo", help="Run the public moving-obstacle evidence demo.")
    motion_obstacle.add_argument("--output-dir", required=True)
    motion_obstacle.add_argument("--nx", type=int, default=12)
    motion_obstacle.add_argument("--ny", type=int, default=6)
    motion_obstacle.add_argument("--time-step-s", type=float, default=0.05)
    motion_obstacle.add_argument("--total-time-s", type=float, default=0.2)
    motion_obstacle.add_argument("--iterations", type=int, default=2)
    motion_obstacle.add_argument("--format", choices=("json", "markdown"), default="json")

    registry = sub.add_parser("registry", help="Print the FastCFD source-of-truth registry.")
    registry.add_argument("--format", choices=("json", "markdown"), default="json")

    validate_case = sub.add_parser("validate-case", help="Validate a FastFluent CaseSpec v3 file.")
    validate_case.add_argument("case_file")
    validate_case.add_argument("--output-dir", default=None)
    validate_case.add_argument("--format", choices=("json", "markdown"), default="json")

    explain_case = sub.add_parser("explain-case", help="Explain a FastFluent CaseSpec v3 file.")
    explain_case.add_argument("case_file")
    explain_case.add_argument("--format", choices=("json", "markdown"), default="markdown")

    evidence = sub.add_parser("evidence", help="Validate or summarize FastFluent EvidenceBundle v3 outputs.")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    validate_bundle = evidence_sub.add_parser("validate-bundle", help="Validate an EvidenceBundle v3 directory.")
    validate_bundle.add_argument("bundle_dir")
    validate_bundle.add_argument("--format", choices=("json", "markdown"), default="json")
    summarize_bundle = evidence_sub.add_parser("summarize-bundle", help="Summarize an EvidenceBundle v3 directory.")
    summarize_bundle.add_argument("bundle_dir")
    summarize_bundle.add_argument("--format", choices=("json", "markdown"), default="markdown")

    bc = sub.add_parser("bc", help="Run FastFluent boundary-condition contract commands.")
    bc_sub = bc.add_subparsers(dest="bc_command", required=True)
    bc_demo = bc_sub.add_parser("validate-demo-pack", help="Write and validate a public boundary-condition contract demo pack.")
    bc_demo.add_argument("--output-dir", required=True)
    bc_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    materials = sub.add_parser("materials", help="Run FastFluent material contract commands.")
    materials_sub = materials.add_subparsers(dest="materials_command", required=True)
    materials_demo = materials_sub.add_parser("validate-demo-pack", help="Write and validate a public material contract demo pack.")
    materials_demo.add_argument("--output-dir", required=True)
    materials_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    mesh = sub.add_parser("mesh", help="Run FastFluent Mesh Gateway v2 commands.")
    mesh_sub = mesh.add_subparsers(dest="mesh_command", required=True)
    mesh_inspect = mesh_sub.add_parser("inspect", help="Inspect a Gmsh mesh through Mesh Gateway v2.")
    mesh_inspect.add_argument("mesh_file")
    mesh_inspect.add_argument("--output-dir", required=True)
    mesh_inspect.add_argument("--required-patches", default="inlet,outlet,wall")
    mesh_inspect.add_argument("--format", choices=("json", "markdown"), default="json")
    structured_demo = mesh_sub.add_parser("generate-structured-demo", help="Generate a structured Mesh Gateway v2 demo.")
    structured_demo.add_argument("--output-dir", required=True)
    structured_demo.add_argument("--nx", type=int, default=20)
    structured_demo.add_argument("--ny", type=int, default=8)
    structured_demo.add_argument("--length-m", type=float, default=1.0)
    structured_demo.add_argument("--height-m", type=float, default=0.1)
    structured_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    flow_pack = sub.add_parser("flow-pack", help="Build and validate setup-only FastFluent Flow Packs.")
    flow_pack_sub = flow_pack.add_subparsers(dest="flow_pack_command", required=True)
    flow_pack_build = flow_pack_sub.add_parser("build", help="Build a Flow Pack from a CaseSpec v3 file.")
    flow_pack_build.add_argument("case_file")
    flow_pack_build.add_argument("--output-dir", required=True)
    flow_pack_build.add_argument("--mesh-file", default=None)
    flow_pack_build.add_argument("--mesh-mode", choices=("auto", "structured-demo", "gmsh", "none"), default="auto")
    flow_pack_build.add_argument("--required-patches", default=None)
    flow_pack_build.add_argument("--format", choices=("json", "markdown"), default="json")
    flow_pack_demo = flow_pack_sub.add_parser("build-demo", help="Build the public channel-flow Flow Pack demo.")
    flow_pack_demo.add_argument("--output-dir", required=True)
    flow_pack_demo.add_argument("--case-file", default="examples/fastcfd/casespec_v3/channel_flow_case.json")
    flow_pack_demo.add_argument("--format", choices=("json", "markdown"), default="json")
    flow_pack_validate = flow_pack_sub.add_parser("validate", help="Validate a Flow Pack output directory.")
    flow_pack_validate.add_argument("flow_pack_dir")
    flow_pack_validate.add_argument("--format", choices=("json", "markdown"), default="json")
    flow_pack_export = flow_pack_sub.add_parser("export-evidence-bundle", help="Export a setup-only EvidenceBundle v3 from a Flow Pack.")
    flow_pack_export.add_argument("flow_pack_dir")
    flow_pack_export.add_argument("--output-dir", default=None)
    flow_pack_export.add_argument("--format", choices=("json", "markdown"), default="json")

    route_selector = sub.add_parser("route-selector", help="Select the next controlled FastFluent route from setup evidence.")
    route_selector_sub = route_selector.add_subparsers(dest="route_selector_command", required=True)
    route_catalog_cmd = route_selector_sub.add_parser("catalog", help="Print the M5 route selector catalog.")
    route_catalog_cmd.add_argument("--format", choices=("json", "markdown"), default="json")
    route_select = route_selector_sub.add_parser("select", help="Select the next route from a Flow Pack directory.")
    route_select.add_argument("flow_pack_dir")
    route_select.add_argument("--output-dir", default=None)
    route_select.add_argument("--format", choices=("json", "markdown"), default="json")
    route_demo = route_selector_sub.add_parser("demo", help="Build a public Flow Pack demo and select the next route.")
    route_demo.add_argument("--output-dir", required=True)
    route_demo.add_argument("--case-file", default="examples/fastcfd/casespec_v3/channel_flow_case.json")
    route_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    route_plan = sub.add_parser("route-plan", help="Compile M5 route selections into pre-execution route plans.")
    route_plan_sub = route_plan.add_subparsers(dest="route_plan_command", required=True)
    route_plan_compile = route_plan_sub.add_parser("compile", help="Compile a route_selection.json file or directory into a route plan.")
    route_plan_compile.add_argument("route_selection")
    route_plan_compile.add_argument("--output-dir", required=True)
    route_plan_compile.add_argument("--profile", choices=("agent", "ci"), default="agent")
    route_plan_compile.add_argument("--no-materialize-job", action="store_true")
    route_plan_compile.add_argument("--format", choices=("json", "markdown"), default="json")
    route_plan_validate = route_plan_sub.add_parser("validate", help="Validate a route plan file or directory.")
    route_plan_validate.add_argument("route_plan")
    route_plan_validate.add_argument("--format", choices=("json", "markdown"), default="json")
    route_plan_demo = route_plan_sub.add_parser("demo", help="Run the public route-selector demo and compile an M6 route plan.")
    route_plan_demo.add_argument("--output-dir", required=True)
    route_plan_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    execution_gate = sub.add_parser("execution-gate", help="Audit route plans before any controlled solver execution.")
    execution_gate_sub = execution_gate.add_subparsers(dest="execution_gate_command", required=True)
    execution_gate_audit = execution_gate_sub.add_parser("audit", help="Dry-run audit a route plan and write an execution package.")
    execution_gate_audit.add_argument("route_plan")
    execution_gate_audit.add_argument("--output-dir", required=True)
    execution_gate_audit.add_argument("--source-root", default=None)
    execution_gate_audit.add_argument("--format", choices=("json", "markdown"), default="json")
    execution_gate_validate = execution_gate_sub.add_parser("validate", help="Validate an execution gate file or directory.")
    execution_gate_validate.add_argument("execution_gate")
    execution_gate_validate.add_argument("--format", choices=("json", "markdown"), default="json")
    execution_gate_demo = execution_gate_sub.add_parser("demo", help="Run the public route-plan demo and audit it with Execution Gate.")
    execution_gate_demo.add_argument("--output-dir", required=True)
    execution_gate_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    controlled_runner = sub.add_parser("controlled-runner", help="Record controlled post-gate execution ledgers.")
    controlled_runner_sub = controlled_runner.add_subparsers(dest="controlled_runner_command", required=True)
    controlled_runner_run = controlled_runner_sub.add_parser("run", help="Run the M8 Controlled Runner from an execution gate.")
    controlled_runner_run.add_argument("execution_gate")
    controlled_runner_run.add_argument("--output-dir", required=True)
    controlled_runner_run.add_argument("--mode", choices=("dry_run", "mock"), default="dry_run")
    controlled_runner_run.add_argument("--approval-id", default=None)
    controlled_runner_run.add_argument("--format", choices=("json", "markdown"), default="json")
    controlled_runner_validate = controlled_runner_sub.add_parser("validate", help="Validate a Controlled Runner file or directory.")
    controlled_runner_validate.add_argument("controlled_run")
    controlled_runner_validate.add_argument("--format", choices=("json", "markdown"), default="json")
    controlled_runner_demo = controlled_runner_sub.add_parser("demo", help="Run the public M8 Controlled Runner demo.")
    controlled_runner_demo.add_argument("--output-dir", required=True)
    controlled_runner_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    result_pack = sub.add_parser("result-pack", help="Compile agent-facing result packages from controlled or native outputs.")
    result_pack_sub = result_pack.add_subparsers(dest="result_pack_command", required=True)
    result_pack_compile = result_pack_sub.add_parser("compile", help="Compile a Result Pack from a controlled_run.json file or directory.")
    result_pack_compile.add_argument("controlled_run")
    result_pack_compile.add_argument("--output-dir", required=True)
    result_pack_compile.add_argument("--format", choices=("json", "markdown"), default="json")
    result_pack_compile_native = result_pack_sub.add_parser("compile-native", help="Compile a Result Pack from a native FastFluent result file or directory.")
    result_pack_compile_native.add_argument("native_result")
    result_pack_compile_native.add_argument("--output-dir", required=True)
    result_pack_compile_native.add_argument("--format", choices=("json", "markdown"), default="json")
    result_pack_validate = result_pack_sub.add_parser("validate", help="Validate a Result Pack file or directory.")
    result_pack_validate.add_argument("result_pack")
    result_pack_validate.add_argument("--format", choices=("json", "markdown"), default="json")
    result_pack_demo = result_pack_sub.add_parser("demo", help="Run the public M9 Result Pack demo.")
    result_pack_demo.add_argument("--output-dir", required=True)
    result_pack_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    transport = sub.add_parser("transport", help="Run S6 unified scalar transport coupling commands.")
    transport_sub = transport.add_subparsers(dest="transport_command", required=True)
    transport_write_demo = transport_sub.add_parser("write-demo", help="Write a public S6 transport case JSON.")
    transport_write_demo.add_argument("--case-file", required=True)
    transport_write_demo.add_argument(
        "--quantity",
        choices=("alpha", "temperature", "species", "particle_concentration", "wax_fraction"),
        default="alpha",
    )
    transport_write_demo.add_argument("--format", choices=("json", "markdown"), default="json")
    transport_validate = transport_sub.add_parser("validate", help="Validate a S6 transport case JSON.")
    transport_validate.add_argument("case_file")
    transport_validate.add_argument("--format", choices=("json", "markdown"), default="json")
    transport_run = transport_sub.add_parser("run", help="Run a S6 transport case JSON on a mesh or generated public mesh.")
    transport_run.add_argument("case_file")
    transport_run.add_argument("--mesh-file", default=None)
    transport_run.add_argument("--output-dir", required=True)
    transport_run.add_argument("--format", choices=("json", "markdown"), default="json")
    transport_demo = transport_sub.add_parser("demo", help="Run a public S6 transport coupling demo.")
    transport_demo.add_argument("--output-dir", required=True)
    transport_demo.add_argument(
        "--quantity",
        choices=("alpha", "temperature", "species", "particle_concentration", "wax_fraction"),
        default="alpha",
    )
    transport_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    workflow = sub.add_parser("workflow", help="Run S7 full FastFluent agent workflows.")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_run = workflow_sub.add_parser("run", help="Run the S7 workflow from a CaseSpec v3 file.")
    workflow_run.add_argument("--case-file", required=True)
    workflow_run.add_argument("--output-dir", required=True)
    workflow_run.add_argument("--mode", choices=("dry_run", "native_advisory"), default="dry_run")
    workflow_run.add_argument("--mesh-file", default=None)
    workflow_run.add_argument("--mesh-mode", choices=("auto", "structured-demo", "gmsh", "none"), default="auto")
    workflow_run.add_argument("--required-patches", default=None)
    workflow_run.add_argument("--native-route", choices=("transport",), default="transport")
    workflow_run.add_argument(
        "--transport-quantity",
        choices=("alpha", "temperature", "species", "particle_concentration", "wax_fraction"),
        default="alpha",
    )
    workflow_run.add_argument("--source-root", default=None)
    workflow_run.add_argument("--format", choices=("json", "markdown"), default="json")
    workflow_demo = workflow_sub.add_parser("demo", help="Run the public S7 workflow demo.")
    workflow_demo.add_argument("--output-dir", required=True)
    workflow_demo.add_argument("--mode", choices=("dry_run", "native_advisory"), default="native_advisory")
    workflow_demo.add_argument("--format", choices=("json", "markdown"), default="json")

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
    run_real.add_argument("--source-root", default=None, help="FastFluent C++ source root. Defaults to vendored cpp/fastfluent_core when available.")
    run_real.add_argument("--build-timeout-sec", type=int, default=240)
    run_real.add_argument("--run-timeout-sec", type=int, default=240)

    run_cavity = sub.add_parser("run-fastfluent-cavity2d-job", help="Build and run a controlled real FastFluent cavity2d job.")
    run_cavity.add_argument("--job-file", required=True)
    run_cavity.add_argument("--source-root", default=None, help="FastFluent C++ source root. Defaults to vendored cpp/fastfluent_core when available.")
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

    write_wax = sub.add_parser("write-wax-rheology-demo", help="Write a public wax rheology / phase-change demo case.")
    write_wax.add_argument("--output-dir", required=True, help="Directory for wax_rheology_phase_change_case.json.")
    write_wax.add_argument("--case-name", default="wax_arrhenius_softening_demo")
    write_wax.add_argument("--format", choices=("json", "markdown"), default="json")

    validate_wax = sub.add_parser("validate-wax-rheology-phase-change", help="Validate a wax rheology / phase-change case and write passport artifacts.")
    validate_wax.add_argument("--case", required=True, help="wax_rheology_phase_change_case.json path.")
    validate_wax.add_argument("--output-dir", required=True, help="Directory for passport, hints, and report.")
    validate_wax.add_argument("--format", choices=("json", "markdown"), default="json")

    wax_demo = sub.add_parser("wax-rheology-handoff-demo", help="Run the H4 wax case -> passport -> patch demo pipeline.")
    wax_demo.add_argument("--output-dir", required=True, help="Directory for the H4 wax handoff demo artifact chain.")
    wax_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    compile_hints = sub.add_parser("compile-fluent-hints", help="Compile evidence-checked Fluent setup hints from FastFluent artifacts.")
    compile_hints.add_argument("--evidence-files", required=True, help="Comma-separated JSON evidence artifact paths.")
    compile_hints.add_argument("--output-dir", default=None)
    compile_hints.add_argument("--format", choices=("json", "markdown"), default="json")

    write_steam_air = sub.add_parser("write-steam-air-demo", help="Write a public steam-air condensation demo case.")
    write_steam_air.add_argument("--output-dir", required=True, help="Directory for steam_air_condensation_case.json.")
    write_steam_air.add_argument("--case-name", default="steam_air_wall_condensation_demo")
    write_steam_air.add_argument("--format", choices=("json", "markdown"), default="json")

    validate_steam_air = sub.add_parser("validate-steam-air-condensation", help="Validate a steam-air condensation case and write passport artifacts.")
    validate_steam_air.add_argument("--case", required=True, help="steam_air_condensation_case.json path.")
    validate_steam_air.add_argument("--output-dir", required=True, help="Directory for passport, hints, and report.")
    validate_steam_air.add_argument("--format", choices=("json", "markdown"), default="json")

    compile_patch = sub.add_parser("compile-fluent-patch", help="Compile a FastFluent passport into a solver_plan_patch.json bundle.")
    compile_patch.add_argument("--input", required=True, help="FastFluent passport JSON path.")
    compile_patch.add_argument("--output", required=True, help="Output solver_plan_patch.json path.")
    compile_patch.add_argument("--format", choices=("json", "markdown"), default="json")

    steam_air_demo = sub.add_parser("steam-air-handoff-demo", help="Run the public steam-air case -> passport -> patch demo pipeline.")
    steam_air_demo.add_argument("--output-dir", required=True, help="Directory for the full handoff demo artifact chain.")
    steam_air_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    write_steam_air_v2 = sub.add_parser("write-steam-air-v2-demo", help="Write a public steam-air condensation v2 demo case.")
    write_steam_air_v2.add_argument("--output-dir", required=True, help="Directory for steam_air_condensation_case_v2.json.")
    write_steam_air_v2.add_argument("--case-name", default="steam_air_wall_condensation_v2_demo")
    write_steam_air_v2.add_argument("--format", choices=("json", "markdown"), default="json")

    validate_steam_air_v2 = sub.add_parser("validate-steam-air-condensation-v2", help="Validate a steam-air condensation v2 case and write passport artifacts.")
    validate_steam_air_v2.add_argument("--case", required=True, help="steam_air_condensation_case_v2.json path.")
    validate_steam_air_v2.add_argument("--output-dir", required=True, help="Directory for v2 passport, hints, and report.")
    validate_steam_air_v2.add_argument("--format", choices=("json", "markdown"), default="json")

    steam_air_v2_demo = sub.add_parser("steam-air-v2-demo", help="Run the H2 steam-air v2 case -> passport -> patch demo pipeline.")
    steam_air_v2_demo.add_argument("--output-dir", required=True, help="Directory for the H2 steam-air v2 demo artifact chain.")
    steam_air_v2_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    write_solid_liquid = sub.add_parser("write-solid-liquid-demo", help="Write a public solid-liquid suspension demo case.")
    write_solid_liquid.add_argument("--output-dir", required=True, help="Directory for solid_liquid_suspension_case.json.")
    write_solid_liquid.add_argument("--case-name", default="solid_liquid_suspension_demo")
    write_solid_liquid.add_argument("--format", choices=("json", "markdown"), default="json")

    validate_solid_liquid = sub.add_parser("validate-solid-liquid-suspension", help="Validate a solid-liquid suspension case and write passport artifacts.")
    validate_solid_liquid.add_argument("--case", required=True, help="solid_liquid_suspension_case.json path.")
    validate_solid_liquid.add_argument("--output-dir", required=True, help="Directory for passport, hints, and report.")
    validate_solid_liquid.add_argument("--format", choices=("json", "markdown"), default="json")

    solid_liquid_demo = sub.add_parser("solid-liquid-handoff-demo", help="Run the H3 solid-liquid suspension case -> passport -> patch demo pipeline.")
    solid_liquid_demo.add_argument("--output-dir", required=True, help="Directory for the H3 solid-liquid demo artifact chain.")
    solid_liquid_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    existing_patch_demo = sub.add_parser(
        "existing-passport-patch-demo",
        help="Run the H1 VOF + turbulence + rheology passport -> solver-plan patch demo.",
    )
    existing_patch_demo.add_argument("--output-dir", required=True, help="Directory for H1 patch demo artifacts.")
    existing_patch_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    validation_pack_demo = sub.add_parser(
        "horizontal-validation-pack-demo",
        help="Run the H3.5 public H1-H3 horizontal validation pack.",
    )
    validation_pack_demo.add_argument("--output-dir", required=True, help="Directory for validation pack artifacts.")
    validation_pack_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    native_simulation_pack_demo = sub.add_parser(
        "native-simulation-validation-pack-demo",
        help="Run the S1 public FastFluent-native simulation validation pack without launching Fluent.",
    )
    native_simulation_pack_demo.add_argument("--output-dir", required=True, help="Directory for S1 native simulation artifacts.")
    native_simulation_pack_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    practical_native_demo = sub.add_parser(
        "practical-native-demo-pack",
        help="Run the S2 practical FastFluent-native function expansion pack without launching Fluent.",
    )
    practical_native_demo.add_argument("--output-dir", required=True, help="Directory for S2 practical native artifacts.")
    practical_native_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    practical_setup_demo = sub.add_parser(
        "practical-native-setup-demo",
        help="Run the S3 practical native geometry, boundary-condition, initial-field, and case-template setup pack.",
    )
    practical_setup_demo.add_argument("--output-dir", required=True, help="Directory for S3 practical native setup artifacts.")
    practical_setup_demo.add_argument("--format", choices=("json", "markdown"), default="json")

    unstructured = sub.add_parser("unstructured", help="Run unstructured FastFluent mesh gateway commands.")
    unstructured_sub = unstructured.add_subparsers(dest="unstructured_command", required=True)
    inspect_mesh = unstructured_sub.add_parser("inspect-mesh", help="Inspect a Gmsh v4 ASCII mesh before any solver execution.")
    inspect_mesh.add_argument("mesh_file", help="Path to a Gmsh .msh v4 ASCII mesh.")
    inspect_mesh.add_argument("--output-dir", default=None, help="Directory for mesh_manifest.json, mesh_quality.json, and mesh.vtu.")
    inspect_mesh.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    inspect_mesh.add_argument("--format", choices=("json", "markdown"), default="json")
    inspect_mesh.add_argument("--no-write-vtu", action="store_true", help="Skip mesh.vtu preview output.")
    run_case = unstructured_sub.add_parser("run-case", help="Run an agent-safe unstructured case JSON file.")
    run_case.add_argument("case_file", help="Unstructured case JSON file.")
    run_case.add_argument("--output-dir", default=None, help="Directory for case-run artifacts.")
    run_case.add_argument("--motion-adapter", default=None, help="Optional motion_adapter.json file to preflight before solver dispatch.")
    run_case.add_argument(
        "--motion-execution-mode",
        choices=("static_grid_motion_evidence", "require_dynamic_mesh", "block_on_motion"),
        default="static_grid_motion_evidence",
        help="How motion evidence should affect solver dispatch.",
    )
    run_case.add_argument("--format", choices=("json", "markdown"), default="json")
    write_steady_case = unstructured_sub.add_parser("write-steady-channel-case", help="Write a public steady incompressible channel case JSON.")
    write_steady_case.add_argument("--case-file", required=True, help="Output case JSON path.")
    write_steady_case.add_argument("--mesh-file", required=True, help="Mesh path to reference from the case JSON.")
    write_steady_case.add_argument("--case-name", default="public_steady_channel_case")
    write_steady_case.add_argument("--inlet-velocity", default="1.0,0.0", help="Comma-separated ux,uy.")
    write_steady_case.add_argument("--density", type=float, default=1.0)
    write_steady_case.add_argument("--viscosity", type=float, default=1.0e-2)
    write_steady_case.add_argument("--iterations", type=int, default=8)
    write_steady_case.add_argument("--format", choices=("json", "markdown"), default="json")
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
    solve_tetra = unstructured_sub.add_parser(
        "solve-tetra-diffusion",
        help="Run a public 3D tetra scalar diffusion smoke benchmark.",
    )
    solve_tetra.add_argument("mesh_file", nargs="?", help="Optional Gmsh .msh tetra mesh. If omitted, a public unit-cube tetra mesh is generated.")
    solve_tetra.add_argument("--output-dir", default=None, help="Directory for tetra diffusion artifacts.")
    solve_tetra.add_argument("--diffusivity", type=float, default=1.0)
    solve_tetra.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_tetra.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_tetra.add_argument("--max-linear-iterations", type=int, default=None)
    solve_tetra.add_argument("--format", choices=("json", "markdown"), default="json")
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
    solve_steady = unstructured_sub.add_parser(
        "solve-steady-incompressible",
        help="Run a controlled steady incompressible pressure-correction case with default inlet/outlet/wall BCs.",
    )
    solve_steady.add_argument("mesh_file", help="Path to a Gmsh .msh v4 ASCII mesh.")
    solve_steady.add_argument("--output-dir", default=None, help="Directory for steady incompressible artifacts.")
    solve_steady.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_steady.add_argument("--density", type=float, default=1.0)
    solve_steady.add_argument("--viscosity", type=float, default=1.0e-2)
    solve_steady.add_argument("--body-force", default="0.0,0.0", help="Comma-separated force_x,force_y.")
    solve_steady.add_argument("--iterations", type=int, default=8)
    solve_steady.add_argument("--pressure-relaxation", type=float, default=0.45)
    solve_steady.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_steady.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_steady.add_argument("--max-linear-iterations", type=int, default=None)
    solve_steady.add_argument("--format", choices=("json", "markdown"), default="json")
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
    solve_turbulent = unstructured_sub.add_parser(
        "solve-turbulent-channel",
        help="Run a simplified algebraic eddy-viscosity turbulent channel benchmark.",
    )
    solve_turbulent.add_argument("mesh_file", nargs="?", help="Optional Gmsh .msh file. If omitted, a public channel mesh is generated.")
    solve_turbulent.add_argument("--output-dir", default=None, help="Directory for turbulent-channel artifacts.")
    solve_turbulent.add_argument("--density", type=float, default=1.0)
    solve_turbulent.add_argument("--molecular-viscosity", type=float, default=1.0e-3)
    solve_turbulent.add_argument("--pressure-drop", type=float, default=0.05)
    solve_turbulent.add_argument("--iterations", type=int, default=12)
    solve_turbulent.add_argument("--relaxation", type=float, default=0.55)
    solve_turbulent.add_argument("--kappa", type=float, default=0.41)
    solve_turbulent.add_argument("--max-mixing-length-fraction", type=float, default=0.09)
    solve_turbulent.add_argument("--turbulent-viscosity-cap-ratio", type=float, default=1000.0)
    solve_turbulent.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_turbulent.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_turbulent.add_argument("--max-linear-iterations", type=int, default=None)
    solve_turbulent.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_turbulent.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_kepsilon = unstructured_sub.add_parser(
        "solve-kepsilon-channel",
        help="Run a bounded standard k-epsilon two-equation turbulent channel benchmark.",
    )
    solve_kepsilon.add_argument("mesh_file", nargs="?", help="Optional Gmsh .msh file. If omitted, a public channel mesh is generated.")
    solve_kepsilon.add_argument("--output-dir", default=None, help="Directory for k-epsilon channel artifacts.")
    solve_kepsilon.add_argument("--density", type=float, default=1.0)
    solve_kepsilon.add_argument("--molecular-viscosity", type=float, default=1.0e-3)
    solve_kepsilon.add_argument("--pressure-drop", type=float, default=0.05)
    solve_kepsilon.add_argument("--iterations", type=int, default=12)
    solve_kepsilon.add_argument("--relaxation", type=float, default=0.45)
    solve_kepsilon.add_argument("--c-mu", type=float, default=0.09)
    solve_kepsilon.add_argument("--c-epsilon-1", type=float, default=1.44)
    solve_kepsilon.add_argument("--c-epsilon-2", type=float, default=1.92)
    solve_kepsilon.add_argument("--sigma-k", type=float, default=1.0)
    solve_kepsilon.add_argument("--sigma-epsilon", type=float, default=1.3)
    solve_kepsilon.add_argument("--turbulence-intensity", type=float, default=0.05)
    solve_kepsilon.add_argument("--turbulent-length-scale-fraction", type=float, default=0.07)
    solve_kepsilon.add_argument("--turbulent-viscosity-cap-ratio", type=float, default=1000.0)
    solve_kepsilon.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_kepsilon.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_kepsilon.add_argument("--max-linear-iterations", type=int, default=None)
    solve_kepsilon.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_kepsilon.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_pressure_kepsilon = unstructured_sub.add_parser(
        "solve-kepsilon-pressure-channel",
        help="Run a bounded pressure-corrected standard k-epsilon turbulent channel benchmark.",
    )
    solve_pressure_kepsilon.add_argument("mesh_file", nargs="?", help="Optional Gmsh .msh file. If omitted, a public channel mesh is generated.")
    solve_pressure_kepsilon.add_argument("--output-dir", default=None, help="Directory for pressure-corrected k-epsilon artifacts.")
    solve_pressure_kepsilon.add_argument("--density", type=float, default=1.0)
    solve_pressure_kepsilon.add_argument("--molecular-viscosity", type=float, default=1.0e-3)
    solve_pressure_kepsilon.add_argument("--pressure-drop", type=float, default=0.05)
    solve_pressure_kepsilon.add_argument("--iterations", type=int, default=10)
    solve_pressure_kepsilon.add_argument("--relaxation", type=float, default=0.4)
    solve_pressure_kepsilon.add_argument("--pressure-relaxation", type=float, default=0.35)
    solve_pressure_kepsilon.add_argument("--c-mu", type=float, default=0.09)
    solve_pressure_kepsilon.add_argument("--c-epsilon-1", type=float, default=1.44)
    solve_pressure_kepsilon.add_argument("--c-epsilon-2", type=float, default=1.92)
    solve_pressure_kepsilon.add_argument("--sigma-k", type=float, default=1.0)
    solve_pressure_kepsilon.add_argument("--sigma-epsilon", type=float, default=1.3)
    solve_pressure_kepsilon.add_argument("--turbulence-intensity", type=float, default=0.05)
    solve_pressure_kepsilon.add_argument("--turbulent-length-scale-fraction", type=float, default=0.07)
    solve_pressure_kepsilon.add_argument("--turbulent-viscosity-cap-ratio", type=float, default=1000.0)
    solve_pressure_kepsilon.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_pressure_kepsilon.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_pressure_kepsilon.add_argument("--max-linear-iterations", type=int, default=None)
    solve_pressure_kepsilon.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_pressure_kepsilon.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_sst = unstructured_sub.add_parser(
        "solve-sst-channel",
        help="Run a bounded Menter k-omega SST two-equation turbulent channel benchmark.",
    )
    solve_sst.add_argument("mesh_file", nargs="?", help="Optional Gmsh .msh file. If omitted, a public channel mesh is generated.")
    solve_sst.add_argument("--output-dir", default=None, help="Directory for SST channel artifacts.")
    solve_sst.add_argument("--density", type=float, default=1.0)
    solve_sst.add_argument("--molecular-viscosity", type=float, default=1.0e-3)
    solve_sst.add_argument("--pressure-drop", type=float, default=0.05)
    solve_sst.add_argument("--iterations", type=int, default=10)
    solve_sst.add_argument("--relaxation", type=float, default=0.35)
    solve_sst.add_argument("--beta-star", type=float, default=0.09)
    solve_sst.add_argument("--sigma-k1", type=float, default=0.85)
    solve_sst.add_argument("--sigma-omega1", type=float, default=0.5)
    solve_sst.add_argument("--beta1", type=float, default=0.075)
    solve_sst.add_argument("--sigma-k2", type=float, default=1.0)
    solve_sst.add_argument("--sigma-omega2", type=float, default=0.856)
    solve_sst.add_argument("--beta2", type=float, default=0.0828)
    solve_sst.add_argument("--kappa", type=float, default=0.41)
    solve_sst.add_argument("--a1", type=float, default=0.31)
    solve_sst.add_argument("--turbulence-intensity", type=float, default=0.05)
    solve_sst.add_argument("--turbulent-length-scale-fraction", type=float, default=0.07)
    solve_sst.add_argument("--turbulent-viscosity-cap-ratio", type=float, default=1000.0)
    solve_sst.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_sst.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_sst.add_argument("--max-linear-iterations", type=int, default=None)
    solve_sst.add_argument("--required-patches", default="inlet,outlet,wall", help="Comma-separated required boundary patch names.")
    solve_sst.add_argument("--format", choices=("json", "markdown"), default="json")
    solve_turbulence_ladder = unstructured_sub.add_parser(
        "solve-turbulence-ladder",
        help="Run algebraic, k-epsilon, pressure-corrected k-epsilon, and SST channel benchmarks and compare evidence.",
    )
    solve_turbulence_ladder.add_argument("--output-dir", default=None, help="Directory for turbulence ladder artifacts.")
    solve_turbulence_ladder.add_argument("--density", type=float, default=1.0)
    solve_turbulence_ladder.add_argument("--molecular-viscosity", type=float, default=1.0e-3)
    solve_turbulence_ladder.add_argument("--pressure-drop", type=float, default=0.05)
    solve_turbulence_ladder.add_argument("--iterations", type=int, default=8)
    solve_turbulence_ladder.add_argument("--linear-solver", choices=("sparse-cg", "dense-direct"), default="sparse-cg")
    solve_turbulence_ladder.add_argument("--linear-tolerance", type=float, default=1.0e-12)
    solve_turbulence_ladder.add_argument("--max-linear-iterations", type=int, default=None)
    solve_turbulence_ladder.add_argument("--format", choices=("json", "markdown"), default="json")
    run_benchmark_suite = unstructured_sub.add_parser(
        "run-benchmark-suite",
        help="Run the public unstructured validation suite.",
    )
    run_benchmark_suite.add_argument("--output-dir", default=None, help="Directory for public benchmark suite artifacts.")
    run_benchmark_suite.add_argument("--iterations", type=int, default=8)
    run_benchmark_suite.add_argument("--format", choices=("json", "markdown"), default="json")

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
    if args.command == "solver-capability-matrix":
        matrix = write_solver_capability_matrix(args.output_dir) if args.output_dir else solver_capability_matrix()
        if args.format == "markdown":
            print(solver_capability_matrix_markdown(matrix))
        else:
            print(json.dumps(matrix, ensure_ascii=True, indent=2))
        return 0
    if args.command == "motion":
        if args.motion_command == "write-demo":
            result = write_demo_motion_case(args.output_dir)
            if args.format == "markdown":
                print(motion_report_markdown({"status": result["status"], "validation": result["validation"]}))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result["status"] == "success" else 2
        if args.motion_command == "solver-preflight":
            try:
                result = run_motion_solver_preflight(
                    args.motion_adapter_file,
                    args.output_dir,
                    solver_family=args.solver_family,
                    execution_mode=args.execution_mode,
                    case_file=args.case_file,
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                result = {"status": "failed", "errors": [str(exc)]}
                print(json.dumps(result, ensure_ascii=True, indent=2))
                return 2
            if args.format == "markdown":
                print(motion_solver_preflight_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result["solver_dispatch_allowed"] else 2
        if args.motion_command == "quasi-steady":
            try:
                result = run_quasi_steady_motion_case(
                    args.case_file,
                    args.motion_adapter_file,
                    args.output_dir,
                    execution_mode=args.execution_mode,
                    max_snapshots=args.max_snapshots,
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                result = {"status": "failed", "errors": [str(exc)]}
                print(json.dumps(result, ensure_ascii=True, indent=2))
                return 2
            if args.format == "markdown":
                print(quasi_steady_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result["status"] == "success" else 2
        if args.motion_command == "moving-obstacle-demo":
            try:
                result = run_moving_obstacle_evidence_demo(
                    args.output_dir,
                    nx=args.nx,
                    ny=args.ny,
                    time_step_s=args.time_step_s,
                    total_time_s=args.total_time_s,
                    iterations=args.iterations,
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                result = {"status": "failed", "errors": [str(exc)]}
                print(json.dumps(result, ensure_ascii=True, indent=2))
                return 2
            if args.format == "markdown":
                print(moving_obstacle_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result["status"] == "success" else 2
        try:
            motion_payload = json.loads(Path(args.motion_file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            result = {"status": "failed", "errors": [str(exc)]}
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 2
        if args.motion_command == "validate":
            result = validate_motion_contract(motion_payload)
            if args.format == "markdown":
                print(motion_report_markdown({"status": result["status"], "validation": result}))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result["passed"] else 2
        if args.motion_command == "sample":
            result = sample_motion_contract(
                motion_payload,
                args.output_dir,
                time_step_s=args.time_step_s,
                total_time_s=args.total_time_s,
            )
            if args.format == "markdown":
                print(motion_report_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result["status"] == "success" else 2
        if args.motion_command == "adapt-mesh":
            try:
                result = adapt_motion_to_mesh(
                    motion_payload,
                    args.mesh_file,
                    args.output_dir,
                    time_step_s=args.time_step_s,
                    total_time_s=args.total_time_s,
                    characteristic_length_m=args.characteristic_length_m,
                    cfl_warn=args.cfl_warn,
                    cfl_fail=args.cfl_fail,
                )
            except (OSError, ValueError) as exc:
                result = {"status": "failed", "errors": [str(exc)]}
                print(json.dumps(result, ensure_ascii=True, indent=2))
                return 2
            if args.format == "markdown":
                print(motion_adapter_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result["status"] in {"passed", "warning"} else 2
    if args.command == "registry":
        if args.format == "markdown":
            print(registry_markdown())
        else:
            print(json.dumps(registry_inventory(), ensure_ascii=True, indent=2))
        return 0
    if args.command == "validate-case":
        try:
            payload = read_case_spec(args.case_file)
            validation = validate_case_spec(payload)
            result = validation.to_dict()
            if args.output_dir:
                output_dir = Path(args.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                (output_dir / "case_validation.json").write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
                (output_dir / "case_summary.md").write_text(explain_case_spec_markdown(payload, validation), encoding="utf-8")
                (output_dir / "unsupported_features.json").write_text(
                    json.dumps({"unsupported_features": validation.unsupported_features}, ensure_ascii=True, indent=2),
                    encoding="utf-8",
                )
                (output_dir / "claim_level.json").write_text(
                    json.dumps({"claim_level": validation.claim_level}, ensure_ascii=True, indent=2),
                    encoding="utf-8",
                )
                result["artifacts"] = {
                    "case_validation": str(output_dir / "case_validation.json"),
                    "case_summary": str(output_dir / "case_summary.md"),
                    "unsupported_features": str(output_dir / "unsupported_features.json"),
                    "claim_level": str(output_dir / "claim_level.json"),
                }
            if args.format == "markdown":
                print(explain_case_spec_markdown(payload, validation))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if validation.passed else 2
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            result = {
                "schema_version": "fastfluent_case_spec_validation_v1",
                "status": "failed",
                "passed": False,
                "errors": [str(exc)],
            }
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 2
    if args.command == "explain-case":
        try:
            payload = read_case_spec(args.case_file)
            validation = validate_case_spec(payload)
            if args.format == "json":
                print(json.dumps({"validation": validation.to_dict(), "case": payload}, ensure_ascii=True, indent=2))
            else:
                print(explain_case_spec_markdown(payload, validation))
            return 0 if validation.passed else 2
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            if args.format == "json":
                print(json.dumps({"schema_version": "fastfluent_case_spec_validation_v1", "status": "failed", "errors": [str(exc)]}, ensure_ascii=True, indent=2))
            else:
                print(f"# FastFluent CaseSpec v3 Summary\n\nValidation: `failed`\n\n## Errors\n\n- {exc}\n")
            return 2
    if args.command == "evidence":
        validation = validate_evidence_bundle(args.bundle_dir)
        if args.evidence_command == "validate-bundle":
            if args.format == "markdown":
                print(summarize_evidence_bundle_markdown(args.bundle_dir, validation))
            else:
                print(json.dumps(validation.to_dict(), ensure_ascii=True, indent=2))
            return 0 if validation.passed else 2
        if args.evidence_command == "summarize-bundle":
            if args.format == "json":
                print(json.dumps({"validation": validation.to_dict()}, ensure_ascii=True, indent=2))
            else:
                print(summarize_evidence_bundle_markdown(args.bundle_dir, validation))
            return 0 if validation.passed else 2
    if args.command == "bc":
        if args.bc_command == "validate-demo-pack":
            result = run_boundary_contract_demo(args.output_dir)
            if args.format == "markdown":
                report_path = Path(result["outputs"]["artifacts"]["boundary_validation"])
                print(report_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
    if args.command == "materials":
        if args.materials_command == "validate-demo-pack":
            result = run_material_contract_demo(args.output_dir)
            if args.format == "markdown":
                report_path = Path(result["outputs"]["artifacts"]["material_model_report"])
                print(report_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
    if args.command == "mesh":
        if args.mesh_command == "inspect":
            required_patches = tuple(item.strip() for item in args.required_patches.split(",") if item.strip())
            result = inspect_mesh_gateway(args.mesh_file, output_dir=args.output_dir, required_patches=required_patches)
            if args.format == "markdown":
                report_path = Path(result["outputs"]["artifacts"]["mesh_report"])
                print(report_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.mesh_command == "generate-structured-demo":
            result = generate_structured_mesh_demo(
                args.output_dir,
                nx=args.nx,
                ny=args.ny,
                length_m=args.length_m,
                height_m=args.height_m,
            )
            if args.format == "markdown":
                report_path = Path(result["outputs"]["artifacts"]["mesh_quality_report"])
                print(report_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
    if args.command == "flow-pack":
        if args.flow_pack_command == "build":
            required_patches = tuple(item.strip() for item in args.required_patches.split(",") if item.strip()) if args.required_patches else None
            result = build_flow_pack(
                args.case_file,
                output_dir=args.output_dir,
                mesh_file=args.mesh_file,
                mesh_mode=args.mesh_mode,
                required_patches=required_patches,
            )
            if args.format == "markdown":
                print(flow_pack_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"success", "partial"} else 2
        if args.flow_pack_command == "build-demo":
            result = build_flow_pack(
                args.case_file,
                output_dir=args.output_dir,
                mesh_mode="structured-demo",
            )
            if args.format == "markdown":
                print(flow_pack_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"success", "partial"} else 2
        if args.flow_pack_command == "validate":
            result = validate_flow_pack(args.flow_pack_dir)
            if args.format == "markdown":
                print(flow_pack_validation_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("passed") else 2
        if args.flow_pack_command == "export-evidence-bundle":
            result = export_flow_pack_evidence_bundle(args.flow_pack_dir, output_dir=args.output_dir)
            if args.format == "markdown":
                summary_path = Path(result["outputs"]["artifacts"]["evidence_bundle_summary"])
                print(summary_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
    if args.command == "route-selector":
        if args.route_selector_command == "catalog":
            catalog = route_catalog()
            if args.format == "markdown":
                print("# FastFluent Route Selector Catalog\n")
                for name, route in catalog["routes"].items():
                    print(f"## `{name}`\n")
                    print(f"- Type: `{route.get('route_type')}`")
                    print(f"- Solver execution allowed by route: `{route.get('allowed_to_execute_solver')}`")
                    print(f"- Goal: {route.get('goal')}\n")
            else:
                print(json.dumps(catalog, ensure_ascii=True, indent=2))
            return 0
        if args.route_selector_command == "select":
            result = select_route(args.flow_pack_dir, output_dir=args.output_dir)
            if args.format == "markdown":
                print(route_selection_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.route_selector_command == "demo":
            result = run_route_selector_demo(args.output_dir, case_file=args.case_file)
            if args.format == "markdown":
                report_path = Path(result["outputs"]["artifacts"]["route_selection_report"])
                print(report_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
    if args.command == "route-plan":
        if args.route_plan_command == "compile":
            result = compile_route_plan(
                args.route_selection,
                output_dir=args.output_dir,
                profile=args.profile,
                materialize_job=not args.no_materialize_job,
            )
            if args.format == "markdown":
                print(route_plan_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"ready_for_approval", "review_only"} else 2
        if args.route_plan_command == "validate":
            result = validate_route_plan(args.route_plan)
            if args.format == "markdown":
                print(route_plan_validation_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("passed") else 2
        if args.route_plan_command == "demo":
            result = run_route_plan_demo(args.output_dir)
            if args.format == "markdown":
                report_path = Path(result["outputs"]["artifacts"]["route_plan_report"])
                print(report_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"ready_for_approval", "review_only"} else 2
    if args.command == "execution-gate":
        if args.execution_gate_command == "audit":
            result = audit_execution_gate(args.route_plan, output_dir=args.output_dir, source_root=args.source_root)
            if args.format == "markdown":
                print(execution_gate_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"ready_for_approval", "review_only"} else 2
        if args.execution_gate_command == "validate":
            result = validate_execution_gate(args.execution_gate)
            if args.format == "markdown":
                print(execution_gate_validation_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("passed") else 2
        if args.execution_gate_command == "demo":
            result = run_execution_gate_demo(args.output_dir)
            if args.format == "markdown":
                report_path = Path(result["outputs"]["artifacts"]["runbook"])
                print(report_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"ready_for_approval", "review_only"} else 2
    if args.command == "controlled-runner":
        if args.controlled_runner_command == "run":
            result = run_controlled_runner(
                args.execution_gate,
                output_dir=args.output_dir,
                mode=args.mode,
                approval_id=args.approval_id,
            )
            if args.format == "markdown":
                print(controlled_runner_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"ready_not_executed", "success"} else 2
        if args.controlled_runner_command == "validate":
            result = validate_controlled_runner(args.controlled_run)
            if args.format == "markdown":
                print(controlled_runner_validation_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("passed") else 2
        if args.controlled_runner_command == "demo":
            result = run_controlled_runner_demo(args.output_dir)
            if args.format == "markdown":
                report_path = Path(result["outputs"]["artifacts"]["execution_transcript"])
                print(report_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"ready_not_executed", "success"} else 2
    if args.command == "result-pack":
        if args.result_pack_command == "compile":
            result = compile_result_pack(args.controlled_run, output_dir=args.output_dir)
            if args.format == "markdown":
                print(result_pack_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"review_only", "workflow_validated_only", "advisory_native_evidence"} else 2
        if args.result_pack_command == "compile-native":
            result = compile_native_result_pack(args.native_result, output_dir=args.output_dir)
            if args.format == "markdown":
                print(result_pack_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"advisory_native_evidence", "native_evidence_warning"} else 2
        if args.result_pack_command == "validate":
            result = validate_result_pack(args.result_pack)
            if args.format == "markdown":
                print(result_pack_validation_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("passed") else 2
        if args.result_pack_command == "demo":
            result = run_result_pack_demo(args.output_dir)
            if args.format == "markdown":
                report_path = Path(result["outputs"]["artifacts"]["decision_brief"])
                print(report_path.read_text(encoding="utf-8"))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") in {"review_only", "workflow_validated_only", "advisory_native_evidence"} else 2
    if args.command == "transport":
        if args.transport_command == "write-demo":
            payload = demo_transport_case(quantity=args.quantity)
            case_path = Path(args.case_file)
            case_path.parent.mkdir(parents=True, exist_ok=True)
            case_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
            result = {
                "schema_version": "fastfluent_transport_write_demo_v1",
                "status": "success",
                "case_file": str(case_path),
                "case": payload,
            }
            if args.format == "markdown":
                print(
                    "# FastFluent S6 Transport Demo Case\n\n"
                    f"- Status: `success`\n- Case file: `{case_path}`\n- Quantity: `{payload['field']['quantity']}`\n"
                )
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0
        if args.transport_command == "validate":
            try:
                payload = json.loads(Path(args.case_file).read_text(encoding="utf-8"))
                result = validate_transport_case(payload)
            except (OSError, json.JSONDecodeError) as exc:
                result = {
                    "schema_version": "fastfluent_transport_case_validation_v1",
                    "status": "failed",
                    "passed": False,
                    "errors": [str(exc)],
                    "warnings": [],
                }
            if args.format == "markdown":
                print("# FastFluent S6 Transport Case Validation\n")
                print(f"- Status: `{result.get('status')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("passed") else 2
        if args.transport_command == "run":
            result = run_transport_coupling_case(args.case_file, mesh_file=args.mesh_file, output_dir=args.output_dir)
            if args.format == "markdown":
                print(transport_markdown(result.get("outputs", {}).get("qoi", {})))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("quality_status") in {"passed", "warning"} else 2
        if args.transport_command == "demo":
            result = run_transport_coupling_demo(args.output_dir, quantity=args.quantity)
            if args.format == "markdown":
                print(transport_markdown(result.get("outputs", {}).get("qoi", {})))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("quality_status") in {"passed", "warning"} else 2
    if args.command == "workflow":
        if args.workflow_command == "run":
            required_patches = tuple(item.strip() for item in args.required_patches.split(",") if item.strip()) if args.required_patches else None
            result = run_workflow(
                args.case_file,
                output_dir=args.output_dir,
                mode=args.mode,
                mesh_file=args.mesh_file,
                mesh_mode=args.mesh_mode,
                required_patches=required_patches,
                native_route=args.native_route,
                transport_quantity=args.transport_quantity,
                source_root=args.source_root,
            )
            if args.format == "markdown":
                print(workflow_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") not in {"failed", "blocked", "blocked_native_evidence"} else 2
        if args.workflow_command == "demo":
            result = run_workflow_demo(args.output_dir, mode=args.mode)
            if args.format == "markdown":
                print(workflow_markdown(result))
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") not in {"failed", "blocked", "blocked_native_evidence"} else 2
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
    if args.command == "write-wax-rheology-demo":
        result = write_demo_wax_rheology_case(output_dir=args.output_dir, case_name=args.case_name)
        if args.format == "markdown":
            print("# FastFluent Wax Rheology / Phase-Change Demo Case\n")
            print(f"- Case file: `{result.get('outputs', {}).get('case_file')}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "validate-wax-rheology-phase-change":
        result = validate_wax_rheology_phase_change_case_file(args.case, output_dir=args.output_dir)
        if args.format == "markdown":
            passport = result.get("outputs", {}).get("passport", {})
            computed = passport.get("computed_quantities", {})
            recommendation = computed.get("recommendation", {})
            phase = computed.get("phase_change", {})
            softening = computed.get("softening", {})
            print("# FastFluent Wax Rheology / Phase-Change Passport\n")
            print(f"- Result status: `{result.get('status')}`")
            print(f"- Passport status: `{passport.get('status')}`")
            print(f"- Material model recommendation: `{recommendation.get('material_model_recommendation')}`")
            print(f"- Softening regime: `{softening.get('softening_regime')}`")
            print(f"- Phase-change stiffness risk: `{phase.get('phase_change_stiffness_risk')}`")
            print(f"- Recommended dt s: `{recommendation.get('recommended_time_step_s')}`")
            print(f"- Errors: `{result.get('errors', [])}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "wax-rheology-handoff-demo":
        result = run_wax_rheology_handoff_demo(output_dir=args.output_dir)
        if args.format == "markdown":
            artifacts = result.get("outputs", {}).get("artifacts", {})
            passport = result.get("outputs", {}).get("passport", {})
            patch = result.get("outputs", {}).get("patch", {})
            computed = passport.get("computed_quantities", {})
            recommendation = computed.get("recommendation", {})
            print("# FastFluent Wax Rheology / Phase-Change Handoff Demo\n")
            print(f"- Status: `{result.get('status')}`")
            print(f"- Passport status: `{passport.get('status')}`")
            print(f"- Material model recommendation: `{recommendation.get('material_model_recommendation')}`")
            print(f"- Patch status: `{patch.get('status')}`")
            print(f"- Patch count: `{len(patch.get('patches', []))}`")
            print(f"- Evidence count: `{len(patch.get('evidence', []))}`")
            for key, value in artifacts.items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
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
    if args.command == "write-steam-air-demo":
        result = write_demo_steam_air_case(output_dir=args.output_dir, case_name=args.case_name)
        if args.format == "markdown":
            print("# FastFluent Steam-Air Demo Case\n")
            print(f"- Case file: `{result.get('outputs', {}).get('case_file')}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "validate-steam-air-condensation":
        result = validate_steam_air_condensation_case_file(args.case, output_dir=args.output_dir)
        if args.format == "markdown":
            passport = result.get("outputs", {}).get("passport", {})
            computed = passport.get("computed_quantities", {})
            print("# FastFluent Steam-Air Condensation Passport\n")
            print(f"- Result status: `{result.get('status')}`")
            print(f"- Passport status: `{passport.get('status')}`")
            print(f"- Wall subcooling K: `{computed.get('wall_subcooling_K')}`")
            print(f"- Non-condensable risk: `{computed.get('non_condensable_layer_risk')}`")
            print(f"- Recommended dt s: `{computed.get('recommended_time_step_s')}`")
            print(f"- Source stiffness risk: `{computed.get('source_term_stiffness_risk')}`")
            print(f"- Errors: `{result.get('errors', [])}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "compile-fluent-patch":
        patch = compile_solver_plan_patch_from_passport(args.input)
        result = write_solver_plan_patch_bundle(patch, output=args.output)
        if args.format == "markdown":
            validation = result.get("outputs", {}).get("validation", {})
            patch_payload = result.get("outputs", {}).get("patch", {})
            print("# FastFluent Solver Plan Patch\n")
            print(f"- Result status: `{result.get('status')}`")
            print(f"- Patch status: `{patch_payload.get('status')}`")
            print(f"- Patch count: `{validation.get('checked_patch_count')}`")
            print(f"- Evidence count: `{validation.get('checked_evidence_count')}`")
            print(f"- Errors: `{result.get('errors', [])}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
    if args.command == "steam-air-handoff-demo":
        result = run_steam_air_handoff_demo(output_dir=args.output_dir)
        if args.format == "markdown":
            artifacts = result.get("outputs", {}).get("artifacts", {})
            print("# FastFluent Steam-Air Handoff Demo\n")
            print(f"- Status: `{result.get('status')}`")
            for key, value in artifacts.items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
    if args.command == "write-steam-air-v2-demo":
        result = write_demo_steam_air_v2_case(output_dir=args.output_dir, case_name=args.case_name)
        if args.format == "markdown":
            print("# FastFluent Steam-Air v2 Demo Case\n")
            print(f"- Case file: `{result.get('outputs', {}).get('case_file')}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "validate-steam-air-condensation-v2":
        result = validate_steam_air_condensation_v2_case_file(args.case, output_dir=args.output_dir)
        if args.format == "markdown":
            passport = result.get("outputs", {}).get("passport", {})
            computed = passport.get("computed_quantities", {})
            print("# FastFluent Steam-Air Condensation v2 Passport\n")
            print(f"- Result status: `{result.get('status')}`")
            print(f"- Passport status: `{passport.get('status')}`")
            print(f"- Reynolds number: `{computed.get('reynolds_number')}`")
            print(f"- Prandtl number: `{computed.get('prandtl_number')}`")
            print(f"- Jakob number: `{computed.get('jakob_number')}`")
            print(f"- HTC W/m2K: `{computed.get('estimated_htc_W_m2K')}`")
            print(f"- Mass-transfer resistance: `{computed.get('mass_transfer_resistance')}`")
            print(f"- Source stiffness level: `{computed.get('source_term_stiffness_level')}`")
            print(f"- Errors: `{result.get('errors', [])}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "steam-air-v2-demo":
        result = run_steam_air_v2_demo(output_dir=args.output_dir)
        if args.format == "markdown":
            artifacts = result.get("outputs", {}).get("artifacts", {})
            patch = result.get("outputs", {}).get("patch", {})
            print("# FastFluent Steam-Air v2 Demo\n")
            print(f"- Status: `{result.get('status')}`")
            print(f"- Patch status: `{patch.get('status')}`")
            print(f"- Patch count: `{len(patch.get('patches', []))}`")
            print(f"- Evidence count: `{len(patch.get('evidence', []))}`")
            for key, value in artifacts.items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
    if args.command == "write-solid-liquid-demo":
        result = write_demo_solid_liquid_case(output_dir=args.output_dir, case_name=args.case_name)
        if args.format == "markdown":
            print("# FastFluent Solid-Liquid Suspension Demo Case\n")
            print(f"- Case file: `{result.get('outputs', {}).get('case_file')}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "validate-solid-liquid-suspension":
        result = validate_solid_liquid_suspension_case_file(args.case, output_dir=args.output_dir)
        if args.format == "markdown":
            passport = result.get("outputs", {}).get("passport", {})
            computed = passport.get("computed_quantities", {})
            print("# FastFluent Solid-Liquid Suspension Passport\n")
            print(f"- Result status: `{result.get('status')}`")
            print(f"- Passport status: `{passport.get('status')}`")
            print(f"- Recommended model: `{computed.get('recommended_model')}`")
            print(f"- Particle Reynolds number: `{computed.get('particle_reynolds_number')}`")
            print(f"- Stokes number: `{computed.get('stokes_number')}`")
            print(f"- Settling velocity m/s: `{computed.get('settling_velocity_m_s')}`")
            print(f"- Mass loading: `{computed.get('particle_mass_loading')}`")
            print(f"- Particle time-step risk: `{computed.get('particle_time_step_risk')}`")
            print(f"- Errors: `{result.get('errors', [])}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") == "success" else 2
    if args.command == "solid-liquid-handoff-demo":
        result = run_solid_liquid_handoff_demo(output_dir=args.output_dir)
        if args.format == "markdown":
            artifacts = result.get("outputs", {}).get("artifacts", {})
            passport = result.get("outputs", {}).get("passport", {})
            patch = result.get("outputs", {}).get("patch", {})
            computed = passport.get("computed_quantities", {})
            print("# FastFluent Solid-Liquid Suspension Handoff Demo\n")
            print(f"- Status: `{result.get('status')}`")
            print(f"- Passport status: `{passport.get('status')}`")
            print(f"- Recommended model: `{computed.get('recommended_model')}`")
            print(f"- Patch status: `{patch.get('status')}`")
            print(f"- Patch count: `{len(patch.get('patches', []))}`")
            print(f"- Evidence count: `{len(patch.get('evidence', []))}`")
            for key, value in artifacts.items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
    if args.command == "existing-passport-patch-demo":
        result = run_existing_passport_patch_demo(output_dir=args.output_dir)
        if args.format == "markdown":
            artifacts = result.get("outputs", {}).get("artifacts", {})
            summary = result.get("outputs", {}).get("conflict_summary", {})
            print("# FastFluent Existing Passport Patch Demo\n")
            print(f"- Status: `{result.get('status')}`")
            print(f"- Combined patch status: `{summary.get('status')}`")
            print(f"- Combined evidence count: `{summary.get('evidence_count')}`")
            print(f"- Combined patch count: `{summary.get('patch_count')}`")
            for key, value in artifacts.items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
    if args.command == "horizontal-validation-pack-demo":
        result = run_horizontal_validation_pack(output_dir=args.output_dir)
        if args.format == "markdown":
            artifacts = result.get("outputs", {}).get("artifacts", {})
            manifest = result.get("outputs", {}).get("manifest", {})
            summary = manifest.get("test_status_summary", {})
            print("# FastFluent Horizontal H3.5 Validation Pack\n")
            print(f"- Status: `{result.get('status')}`")
            print(f"- Case count: `{manifest.get('case_count')}`")
            print(f"- Valid patches: `{summary.get('valid_patch_count')}`")
            print(f"- Invalid patches: `{summary.get('invalid_patch_count')}`")
            print(f"- Fluent launched: `{manifest.get('metadata', {}).get('fluent_launched')}`")
            for key, value in artifacts.items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
    if args.command == "native-simulation-validation-pack-demo":
        result = run_native_simulation_validation_pack(output_dir=args.output_dir)
        if args.format == "markdown":
            artifacts = result.get("outputs", {}).get("artifacts", {})
            manifest = result.get("outputs", {}).get("manifest", {})
            acceptance = manifest.get("acceptance_summary", {})
            print("# FastFluent S1 Native Simulation Validation Pack\n")
            print(f"- Status: `{result.get('status')}`")
            print(f"- Case count: `{manifest.get('case_count')}`")
            print(f"- Actual native simulation cases: `{manifest.get('actual_simulation_case_count')}`")
            print(f"- Field-output cases: `{manifest.get('field_output_case_count')}`")
            print(f"- Convergence cases: `{manifest.get('convergence_case_count')}`")
            print(f"- Model-comparison cases: `{manifest.get('model_comparison_case_count')}`")
            print(f"- S1 complete: `{acceptance.get('s1_complete')}`")
            print(f"- Fluent launched: `{manifest.get('metadata', {}).get('fluent_launched')}`")
            for key, value in artifacts.items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
    if args.command == "practical-native-demo-pack":
        result = run_practical_native_demo_pack(output_dir=args.output_dir)
        if args.format == "markdown":
            artifacts = result.get("outputs", {}).get("artifacts", {})
            manifest = result.get("outputs", {}).get("manifest", {})
            acceptance = manifest.get("acceptance_summary", {})
            print("# FastFluent S2 Practical Native Function Expansion Pack\n")
            print(f"- Status: `{result.get('status')}`")
            print(f"- Case count: `{manifest.get('case_count')}`")
            print(f"- Heat diffusion 1D: `{acceptance.get('heat_diffusion_1d_demo')}`")
            print(f"- Scalar transport: `{acceptance.get('scalar_transport_demo')}`")
            print(f"- Material property field: `{acceptance.get('arrhenius_property_demo')}`")
            print(f"- Source ramp/clamp: `{acceptance.get('source_term_ramp_clamp_demo')}`")
            print(f"- Parameter sweep: `{acceptance.get('parameter_sweep_demo')}`")
            print(f"- Wax application demo: `{acceptance.get('wax_application_demo')}`")
            print(f"- Fluent launched: `{manifest.get('metadata', {}).get('fluent_launched')}`")
            for key, value in artifacts.items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
    if args.command == "practical-native-setup-demo":
        result = run_practical_native_setup_demo(output_dir=args.output_dir)
        if args.format == "markdown":
            artifacts = result.get("outputs", {}).get("artifacts", {})
            manifest = result.get("outputs", {}).get("manifest", {})
            acceptance = manifest.get("acceptance_summary", {})
            channel = manifest.get("channel_2d_summary", {})
            print("# FastFluent S3 Practical Native Setup Pack\n")
            print(f"- Status: `{result.get('status')}`")
            print(f"- Channel nodes: `{channel.get('node_count')}`")
            print(f"- Boundary contract valid: `{acceptance.get('boundary_condition_contract_valid')}`")
            print(f"- Initial temperature field: `{acceptance.get('initial_temperature_field_generated')}`")
            print(f"- Initial scalar field: `{acceptance.get('initial_scalar_field_generated')}`")
            print(f"- Initial velocity field: `{acceptance.get('initial_velocity_field_generated')}`")
            print(f"- Case templates: `{acceptance.get('case_templates_generated')}`")
            print(f"- Fluent launched: `{manifest.get('metadata', {}).get('fluent_launched')}`")
            for key, value in artifacts.items():
                print(f"- {key}: `{value}`")
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {"success", "partial"} else 2
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
        if args.unstructured_command == "run-case":
            result = run_unstructured_case_file(
                args.case_file,
                output_dir=args.output_dir,
                motion_adapter_file=args.motion_adapter,
                motion_execution_mode=args.motion_execution_mode,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                motion_preflight = result.get("outputs", {}).get("motion_solver_preflight", {})
                print(f"# FastFluent Unstructured Case\n\nStatus: `{result.get('status')}`\n")
                print(f"- Solver: `{qoi.get('solver_family')}`")
                print(f"- Final divergence L2: `{metrics.get('final_divergence_l2')}`")
                print(f"- Mass-flux relative imbalance: `{metrics.get('mass_flux', {}).get('relative_imbalance')}`")
                print(f"- Motion preflight: `{motion_preflight.get('status')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "write-steady-channel-case":
            case_path = write_public_steady_channel_case(
                args.case_file,
                mesh_file=args.mesh_file,
                case_name=args.case_name,
                inlet_velocity=_parse_velocity(args.inlet_velocity),
                density=args.density,
                viscosity=args.viscosity,
                iterations=args.iterations,
            )
            payload = {
                "status": "success",
                "operation": "write_steady_channel_case",
                "outputs": {"case_file": str(case_path)},
            }
            if args.format == "markdown":
                print("# FastFluent Steady Channel Case\n")
                print(f"- Case file: `{case_path}`")
            else:
                print(json.dumps(payload, ensure_ascii=True, indent=2))
            return 0
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
        if args.unstructured_command == "solve-tetra-diffusion":
            result = run_tetra_diffusion_case(
                args.mesh_file,
                output_dir=args.output_dir,
                diffusivity=args.diffusivity,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                linear_system = qoi.get("linear_system", {})
                tetra_case = result.get("outputs", {}).get("tetra_case", {})
                print(f"# FastFluent 3D Tetra Diffusion\n\nStatus: `{result.get('status')}`\n")
                print(f"- Mesh: `{tetra_case.get('mesh_file')}`")
                print(f"- Cells: `{qoi.get('cell_count')}`")
                print(f"- Linear solver: `{linear_system.get('method')}`")
                print(f"- Cell-center L2 error: `{metrics.get('cell_center_l2_error')}`")
                print(f"- Final residual L2: `{metrics.get('final_residual_l2')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-steady-incompressible":
            result = run_steady_incompressible_case(
                args.mesh_file,
                output_dir=args.output_dir,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
                density=args.density,
                viscosity=args.viscosity,
                body_force=_parse_pressure_gradient(args.body_force),
                iterations=args.iterations,
                pressure_relaxation=args.pressure_relaxation,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                hardening = result.get("outputs", {}).get("hardening_summary", {})
                print(f"# FastFluent Steady Incompressible Case\n\nStatus: `{result.get('status')}`\n")
                print(f"- Hardening status: `{hardening.get('status')}`")
                print(f"- Final divergence L2: `{metrics.get('final_divergence_l2')}`")
                print(f"- Mass-flux relative imbalance: `{metrics.get('mass_flux', {}).get('relative_imbalance')}`")
                print(f"- Boundary error: `{metrics.get('velocity_boundary_error')}`")
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
        if args.unstructured_command == "solve-turbulent-channel":
            result = run_turbulent_channel_case(
                args.mesh_file,
                output_dir=args.output_dir,
                density=args.density,
                molecular_viscosity=args.molecular_viscosity,
                pressure_drop=args.pressure_drop,
                iterations=args.iterations,
                relaxation=args.relaxation,
                kappa=args.kappa,
                max_mixing_length_fraction=args.max_mixing_length_fraction,
                turbulent_viscosity_cap_ratio=args.turbulent_viscosity_cap_ratio,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                print(f"# FastFluent Turbulent Channel Benchmark\n\nStatus: `{result.get('status')}`\n")
                print(f"- Bulk Reynolds number: `{metrics.get('bulk_reynolds_number')}`")
                print(f"- Max turbulent viscosity ratio: `{metrics.get('max_turbulent_viscosity_ratio')}`")
                print(f"- Final velocity update L2: `{metrics.get('final_velocity_update_l2')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-kepsilon-channel":
            result = run_kepsilon_channel_case(
                args.mesh_file,
                output_dir=args.output_dir,
                density=args.density,
                molecular_viscosity=args.molecular_viscosity,
                pressure_drop=args.pressure_drop,
                iterations=args.iterations,
                relaxation=args.relaxation,
                c_mu=args.c_mu,
                c_epsilon_1=args.c_epsilon_1,
                c_epsilon_2=args.c_epsilon_2,
                sigma_k=args.sigma_k,
                sigma_epsilon=args.sigma_epsilon,
                turbulence_intensity=args.turbulence_intensity,
                turbulent_length_scale_fraction=args.turbulent_length_scale_fraction,
                turbulent_viscosity_cap_ratio=args.turbulent_viscosity_cap_ratio,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                print(f"# FastFluent k-epsilon Channel Benchmark\n\nStatus: `{result.get('status')}`\n")
                print(f"- Bulk Reynolds number: `{metrics.get('bulk_reynolds_number')}`")
                print(f"- Mean k: `{metrics.get('mean_turbulent_kinetic_energy')}`")
                print(f"- Mean epsilon: `{metrics.get('mean_epsilon')}`")
                print(f"- Max turbulent viscosity ratio: `{metrics.get('max_turbulent_viscosity_ratio')}`")
                print(f"- Final velocity update L2: `{metrics.get('final_velocity_update_l2')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-kepsilon-pressure-channel":
            result = run_pressure_corrected_kepsilon_channel_case(
                args.mesh_file,
                output_dir=args.output_dir,
                density=args.density,
                molecular_viscosity=args.molecular_viscosity,
                pressure_drop=args.pressure_drop,
                iterations=args.iterations,
                relaxation=args.relaxation,
                pressure_relaxation=args.pressure_relaxation,
                c_mu=args.c_mu,
                c_epsilon_1=args.c_epsilon_1,
                c_epsilon_2=args.c_epsilon_2,
                sigma_k=args.sigma_k,
                sigma_epsilon=args.sigma_epsilon,
                turbulence_intensity=args.turbulence_intensity,
                turbulent_length_scale_fraction=args.turbulent_length_scale_fraction,
                turbulent_viscosity_cap_ratio=args.turbulent_viscosity_cap_ratio,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                print(f"# FastFluent Pressure-Corrected k-epsilon Channel Benchmark\n\nStatus: `{result.get('status')}`\n")
                print(f"- Bulk Reynolds number: `{metrics.get('bulk_reynolds_number')}`")
                print(f"- Mean k: `{metrics.get('mean_turbulent_kinetic_energy')}`")
                print(f"- Mean epsilon: `{metrics.get('mean_epsilon')}`")
                print(f"- Max turbulent viscosity ratio: `{metrics.get('max_turbulent_viscosity_ratio')}`")
                print(f"- Final divergence L2: `{metrics.get('final_divergence_l2')}`")
                print(f"- Final velocity update L2: `{metrics.get('final_velocity_update_l2')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-sst-channel":
            result = run_sst_channel_case(
                args.mesh_file,
                output_dir=args.output_dir,
                density=args.density,
                molecular_viscosity=args.molecular_viscosity,
                pressure_drop=args.pressure_drop,
                iterations=args.iterations,
                relaxation=args.relaxation,
                beta_star=args.beta_star,
                sigma_k1=args.sigma_k1,
                sigma_omega1=args.sigma_omega1,
                beta1=args.beta1,
                sigma_k2=args.sigma_k2,
                sigma_omega2=args.sigma_omega2,
                beta2=args.beta2,
                kappa=args.kappa,
                a1=args.a1,
                turbulence_intensity=args.turbulence_intensity,
                turbulent_length_scale_fraction=args.turbulent_length_scale_fraction,
                turbulent_viscosity_cap_ratio=args.turbulent_viscosity_cap_ratio,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
                required_patches=tuple(item.strip() for item in args.required_patches.split(",") if item.strip()),
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                metrics = qoi.get("metrics", {})
                print(f"# FastFluent Menter k-omega SST Channel Benchmark\n\nStatus: `{result.get('status')}`\n")
                print(f"- Bulk Reynolds number: `{metrics.get('bulk_reynolds_number')}`")
                print(f"- Mean k: `{metrics.get('mean_turbulent_kinetic_energy')}`")
                print(f"- Mean omega: `{metrics.get('mean_omega')}`")
                print(f"- Max turbulent viscosity ratio: `{metrics.get('max_turbulent_viscosity_ratio')}`")
                print(f"- Mean F1: `{metrics.get('mean_f1')}`")
                print(f"- Mean F2: `{metrics.get('mean_f2')}`")
                print(f"- Final velocity update L2: `{metrics.get('final_velocity_update_l2')}`")
                print(f"- Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "solve-turbulence-ladder":
            result = run_turbulence_ladder_case(
                output_dir=args.output_dir,
                iterations=args.iterations,
                density=args.density,
                molecular_viscosity=args.molecular_viscosity,
                pressure_drop=args.pressure_drop,
                linear_solver=args.linear_solver,
                linear_tolerance=args.linear_tolerance,
                max_linear_iterations=args.max_linear_iterations,
            )
            if args.format == "markdown":
                qoi = result.get("outputs", {}).get("qoi", {})
                print("# FastFluent Turbulence Ladder\n")
                print(f"Status: `{result.get('status')}`")
                print(f"Recommended tier: `{qoi.get('recommendation', {}).get('tier')}`")
                print(f"Errors: `{result.get('errors', [])}`")
            else:
                print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("status") == "success" else 2
        if args.unstructured_command == "run-benchmark-suite":
            result = run_public_benchmark_suite(output_dir=args.output_dir, iterations=args.iterations)
            if args.format == "markdown":
                summary = result.get("outputs", {}).get("summary", {})
                print("# FastFluent Public Unstructured Benchmark Suite\n")
                print(f"Status: `{result.get('status')}`")
                print(f"Cases: `{summary.get('case_order')}`")
                print(f"Errors: `{result.get('errors', [])}`")
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
