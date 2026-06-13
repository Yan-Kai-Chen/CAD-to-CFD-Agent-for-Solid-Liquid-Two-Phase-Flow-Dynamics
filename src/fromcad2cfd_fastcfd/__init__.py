"""Agent-safe FastCFD layer for lightweight FastFluent-derived pilot runs."""

from __future__ import annotations

from .capabilities import capability_inventory
from .fastfluent_backend import run_fastfluent_cavity2d_job, write_cavity2d_job
from .mock_runner import run_mock_job, write_demo_job
from .preflight import detect_fastcfd_environment, run_preflight
from .schemas import FastCFDJob, FastCFDScene, read_job

__all__ = [
    "FastCFDJob",
    "FastCFDScene",
    "capability_inventory",
    "detect_fastcfd_environment",
    "read_job",
    "run_fastfluent_cavity2d_job",
    "run_mock_job",
    "run_preflight",
    "write_cavity2d_job",
    "write_demo_job",
]
