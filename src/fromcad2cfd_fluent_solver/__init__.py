"""Fluent Solver module placeholder."""

__version__ = "0.2.0"
"""Public-safe Fluent Solver plan validation and template helpers."""

from .monitor_contract import monitor_contract
from .schemas import SOLVER_PLAN_SCHEMA_VERSION, validate_resume_plan, validate_solver_plan

__all__ = [
    "SOLVER_PLAN_SCHEMA_VERSION",
    "monitor_contract",
    "validate_resume_plan",
    "validate_solver_plan",
]
