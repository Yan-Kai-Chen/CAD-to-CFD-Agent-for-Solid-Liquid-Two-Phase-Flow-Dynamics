"""Agent-safe FastCFD layer for lightweight FastFluent-derived CFD screening."""

from __future__ import annotations

from .capabilities import capability_inventory
from .fastfluent_backend import run_fastfluent_cavity2d_job, write_cavity2d_job
from .mock_runner import run_mock_job, write_demo_job
from .preflight import detect_fastcfd_environment, run_preflight
from .prediction import build_prediction_from_output, build_prediction_report
from .screening import run_parameter_screening
from .schemas import FastCFDJob, FastCFDScene, read_job

__all__ = [
    "FastCFDJob",
    "FastCFDScene",
    "capability_inventory",
    "build_prediction_from_output",
    "build_prediction_report",
    "detect_fastcfd_environment",
    "read_job",
    "run_fastfluent_cavity2d_job",
    "run_mock_job",
    "run_parameter_screening",
    "run_preflight",
    "write_cavity2d_job",
    "write_demo_job",
]
