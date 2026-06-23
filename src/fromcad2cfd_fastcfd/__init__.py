"""Agent-safe FastCFD layer for lightweight FastFluent-derived CFD screening."""

from __future__ import annotations

from .boundary.boundary_contract import run_boundary_contract_demo, validate_boundary_contract
from .capabilities import capability_inventory
from .core.case_spec import explain_case_spec_markdown, read_case_spec, validate_case_spec
from .core.evidence_bundle import summarize_evidence_bundle_markdown, validate_evidence_bundle
from .core.units import validate_unit_contract
from .controlled_runner import run_controlled_runner, run_controlled_runner_demo, validate_controlled_runner
from .execution_gate import audit_execution_gate, run_execution_gate_demo, validate_execution_gate
from .fastfluent_backend import run_fastfluent_cavity2d_job, write_cavity2d_job
from .fluent_hints import compile_fluent_setup_hints
from .fluent_patch_compiler import (
    compile_rheology_patch_from_artifact,
    compile_solver_plan_patch_from_passport,
    compile_turbulence_patch_from_artifact,
    compile_vof_patch_from_artifact,
    run_existing_passport_patch_demo,
    run_steam_air_handoff_demo,
)
from .flow_pack import build_flow_pack, export_flow_pack_evidence_bundle, validate_flow_pack
from .materials.material_contract import run_material_contract_demo, validate_material_contract
from .mesh.mesh_gateway import generate_structured_mesh_demo, inspect_mesh_gateway
from .mock_runner import run_mock_job, write_demo_job
from .motion import sample_motion_contract, validate_motion_contract, write_demo_motion_case
from .motion_adapter import adapt_motion_to_mesh
from .motion_quasi_steady import run_moving_obstacle_evidence_demo, run_quasi_steady_motion_case
from .motion_solver_preflight import run_motion_solver_preflight
from .native_simulation_pack import create_native_simulation_case_registry, run_native_simulation_validation_pack
from .preflight import detect_fastcfd_environment, resolve_fastfluent_source_root, run_preflight
from .prediction import build_prediction_from_output, build_prediction_report
from .practical_native_demo_pack import run_practical_native_demo_pack
from .practical_setup import run_practical_native_setup_demo
from .route_plan import compile_route_plan, run_route_plan_demo, validate_route_plan
from .route_selector import route_catalog, run_route_selector_demo, select_route
from .result_pack import compile_native_result_pack, compile_result_pack, run_result_pack_demo, validate_result_pack
from .rheology import run_rheology_benchmark_file
from .screening import run_parameter_screening
from .schemas import FastCFDJob, FastCFDScene, read_job
from .solver_capability_matrix import solver_capability_matrix, write_solver_capability_matrix
from .steam_air_condensation import validate_steam_air_condensation_case_file, write_demo_steam_air_case
from .steam_air_condensation_v2 import (
    build_steam_air_condensation_passport_v2,
    demo_steam_air_condensation_case_v2,
    run_steam_air_v2_demo,
    validate_steam_air_condensation_v2_case_file,
    write_demo_steam_air_v2_case,
)
from .solid_liquid_suspension import (
    build_solid_liquid_suspension_passport,
    demo_solid_liquid_suspension_case,
    run_solid_liquid_handoff_demo,
    validate_solid_liquid_suspension_case_file,
    write_demo_solid_liquid_case,
)
from .transport_core import (
    demo_transport_case,
    run_transport_coupling_case,
    run_transport_coupling_demo,
    validate_transport_case,
)
from .turbulence import validate_turbulence_case_file
from .vof_transport import run_vof_lite_transport_benchmark
from .wax_rheology_phase_change import (
    build_wax_rheology_phase_change_passport,
    create_demo_wax_rheology_case,
    run_wax_rheology_handoff_demo,
    validate_wax_rheology_phase_change_case_file,
    write_demo_wax_rheology_case,
)
from .workflow_runner import run_workflow, run_workflow_demo

__all__ = [
    "FastCFDJob",
    "FastCFDScene",
    "capability_inventory",
    "build_prediction_from_output",
    "build_prediction_report",
    "build_flow_pack",
    "compile_fluent_setup_hints",
    "compile_route_plan",
    "compile_result_pack",
    "compile_native_result_pack",
    "audit_execution_gate",
    "adapt_motion_to_mesh",
    "compile_rheology_patch_from_artifact",
    "compile_solver_plan_patch_from_passport",
    "compile_turbulence_patch_from_artifact",
    "compile_vof_patch_from_artifact",
    "detect_fastcfd_environment",
    "explain_case_spec_markdown",
    "export_flow_pack_evidence_bundle",
    "generate_structured_mesh_demo",
    "inspect_mesh_gateway",
    "resolve_fastfluent_source_root",
    "read_job",
    "read_case_spec",
    "run_boundary_contract_demo",
    "run_fastfluent_cavity2d_job",
    "run_material_contract_demo",
    "run_mock_job",
    "run_motion_solver_preflight",
    "run_moving_obstacle_evidence_demo",
    "run_quasi_steady_motion_case",
    "sample_motion_contract",
    "run_native_simulation_validation_pack",
    "run_practical_native_demo_pack",
    "run_practical_native_setup_demo",
    "run_parameter_screening",
    "run_preflight",
    "run_rheology_benchmark_file",
    "run_controlled_runner",
    "run_controlled_runner_demo",
    "run_route_selector_demo",
    "run_route_plan_demo",
    "run_execution_gate_demo",
    "run_result_pack_demo",
    "run_existing_passport_patch_demo",
    "run_solid_liquid_handoff_demo",
    "run_steam_air_handoff_demo",
    "run_steam_air_v2_demo",
    "run_vof_lite_transport_benchmark",
    "run_wax_rheology_handoff_demo",
    "summarize_evidence_bundle_markdown",
    "solver_capability_matrix",
    "select_route",
    "route_catalog",
    "validate_turbulence_case_file",
    "validate_boundary_contract",
    "validate_case_spec",
    "validate_evidence_bundle",
    "validate_flow_pack",
    "validate_route_plan",
    "validate_execution_gate",
    "validate_controlled_runner",
    "validate_result_pack",
    "validate_material_contract",
    "validate_motion_contract",
    "validate_wax_rheology_phase_change_case_file",
    "validate_unit_contract",
    "validate_solid_liquid_suspension_case_file",
    "validate_steam_air_condensation_case_file",
    "validate_steam_air_condensation_v2_case_file",
    "write_cavity2d_job",
    "create_native_simulation_case_registry",
    "write_demo_job",
    "write_demo_motion_case",
    "write_solver_capability_matrix",
    "write_demo_solid_liquid_case",
    "write_demo_steam_air_case",
    "write_demo_steam_air_v2_case",
    "write_demo_wax_rheology_case",
    "build_solid_liquid_suspension_passport",
    "build_wax_rheology_phase_change_passport",
    "demo_solid_liquid_suspension_case",
    "demo_transport_case",
    "create_demo_wax_rheology_case",
    "build_steam_air_condensation_passport_v2",
    "demo_steam_air_condensation_case_v2",
    "run_transport_coupling_case",
    "run_transport_coupling_demo",
    "validate_transport_case",
    "run_workflow",
    "run_workflow_demo",
]
