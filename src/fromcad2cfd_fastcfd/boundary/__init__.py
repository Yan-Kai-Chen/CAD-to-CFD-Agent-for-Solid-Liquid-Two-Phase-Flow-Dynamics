"""Boundary-condition contracts for FastFluent."""

from __future__ import annotations

from .boundary_contract import (
    BOUNDARY_CONTRACT_SCHEMA_VERSION,
    demo_boundary_conditions,
    run_boundary_contract_demo,
    validate_boundary_contract,
)

__all__ = [
    "BOUNDARY_CONTRACT_SCHEMA_VERSION",
    "demo_boundary_conditions",
    "run_boundary_contract_demo",
    "validate_boundary_contract",
]
