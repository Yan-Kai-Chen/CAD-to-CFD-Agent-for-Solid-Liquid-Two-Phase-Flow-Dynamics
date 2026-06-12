"""Siemens NX backend scaffold for the CAD-to-CFD framework."""

from .preflight import NXPreflightReport, detect_nx_environment, run_preflight

__all__ = ["NXPreflightReport", "detect_nx_environment", "run_preflight"]
