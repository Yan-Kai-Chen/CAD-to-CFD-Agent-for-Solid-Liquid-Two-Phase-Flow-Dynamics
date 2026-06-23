"""Agent-safe FastCFD layer for lightweight FastFluent-derived CFD screening."""

from __future__ import annotations

from .capabilities import capability_inventory
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
from .mock_runner import run_mock_job, write_demo_job
from .native_simulation_pack import create_native_simulation_case_registry, run_native_simulation_validation_pack
from .preflight import detect_fastcfd_environment, resolve_fastfluent_source_root, run_preflight
from .prediction import build_prediction_from_output, build_prediction_report
from .practical_native_demo_pack import run_practical_native_demo_pack
from .rheology import run_rheology_benchmark_file
from .screening import run_parameter_screening
from .schemas import FastCFDJob, FastCFDScene, read_job
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
from .turbulence import validate_turbulence_case_file
from .vof_transport import run_vof_lite_transport_benchmark
from .wax_rheology_phase_change import (
    build_wax_rheology_phase_change_passport,
    create_demo_wax_rheology_case,
    run_wax_rheology_handoff_demo,
    validate_wax_rheology_phase_change_case_file,
    write_demo_wax_rheology_case,
)

__all__ = [
    "FastCFDJob",
    "FastCFDScene",
    "capability_inventory",
    "build_prediction_from_output",
    "build_prediction_report",
    "compile_fluent_setup_hints",
    "compile_rheology_patch_from_artifact",
    "compile_solver_plan_patch_from_passport",
    "compile_turbulence_patch_from_artifact",
    "compile_vof_patch_from_artifact",
    "detect_fastcfd_environment",
    "resolve_fastfluent_source_root",
    "read_job",
    "run_fastfluent_cavity2d_job",
    "run_mock_job",
    "run_native_simulation_validation_pack",
    "run_practical_native_demo_pack",
    "run_parameter_screening",
    "run_preflight",
    "run_rheology_benchmark_file",
    "run_existing_passport_patch_demo",
    "run_solid_liquid_handoff_demo",
    "run_steam_air_handoff_demo",
    "run_steam_air_v2_demo",
    "run_vof_lite_transport_benchmark",
    "run_wax_rheology_handoff_demo",
    "validate_turbulence_case_file",
    "validate_wax_rheology_phase_change_case_file",
    "validate_solid_liquid_suspension_case_file",
    "validate_steam_air_condensation_case_file",
    "validate_steam_air_condensation_v2_case_file",
    "write_cavity2d_job",
    "create_native_simulation_case_registry",
    "write_demo_job",
    "write_demo_solid_liquid_case",
    "write_demo_steam_air_case",
    "write_demo_steam_air_v2_case",
    "write_demo_wax_rheology_case",
    "build_solid_liquid_suspension_passport",
    "build_wax_rheology_phase_change_passport",
    "demo_solid_liquid_suspension_case",
    "create_demo_wax_rheology_case",
    "build_steam_air_condensation_passport_v2",
    "demo_steam_air_condensation_case_v2",
]
