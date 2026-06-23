"""Fluent Solver module placeholder."""

__version__ = "0.2.0"
"""Public-safe Fluent Solver plan validation and template helpers."""

from .monitor_contract import monitor_contract
from .patch_preview import apply_solver_plan_patch_preview, write_patch_preview_bundle
from .schemas import SOLVER_PLAN_SCHEMA_VERSION, validate_resume_plan, validate_solver_plan
from .solver_plan_v2 import SOLVER_PLAN_V2_SCHEMA_VERSION, create_minimal_solver_plan_v2, validate_solver_plan_v2

__all__ = [
    "SOLVER_PLAN_SCHEMA_VERSION",
    "SOLVER_PLAN_V2_SCHEMA_VERSION",
    "apply_solver_plan_patch_preview",
    "create_minimal_solver_plan_v2",
    "monitor_contract",
    "validate_resume_plan",
    "validate_solver_plan",
    "validate_solver_plan_v2",
    "write_patch_preview_bundle",
]
