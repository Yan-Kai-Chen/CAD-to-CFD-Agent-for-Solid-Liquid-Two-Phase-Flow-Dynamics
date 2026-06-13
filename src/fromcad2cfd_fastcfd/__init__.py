"""Agent-safe FastCFD layer for lightweight FastFluent-derived CFD screening."""

from __future__ import annotations

from .capabilities import capability_inventory
from .fastfluent_backend import run_fastfluent_cavity2d_job, write_cavity2d_job
from .fluent_hints import compile_fluent_setup_hints
from .mock_runner import run_mock_job, write_demo_job
from .preflight import detect_fastcfd_environment, run_preflight
from .prediction import build_prediction_from_output, build_prediction_report
from .rheology import run_rheology_benchmark_file
from .screening import run_parameter_screening
from .schemas import FastCFDJob, FastCFDScene, read_job
from .turbulence import validate_turbulence_case_file
from .vof_transport import run_vof_lite_transport_benchmark

__all__ = [
    "FastCFDJob",
    "FastCFDScene",
    "capability_inventory",
    "build_prediction_from_output",
    "build_prediction_report",
    "compile_fluent_setup_hints",
    "detect_fastcfd_environment",
    "read_job",
    "run_fastfluent_cavity2d_job",
    "run_mock_job",
    "run_parameter_screening",
    "run_preflight",
    "run_rheology_benchmark_file",
    "run_vof_lite_transport_benchmark",
    "validate_turbulence_case_file",
    "write_cavity2d_job",
    "write_demo_job",
]
