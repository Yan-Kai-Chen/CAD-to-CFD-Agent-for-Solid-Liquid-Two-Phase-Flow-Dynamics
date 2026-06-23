"""Material contracts for FastFluent."""

from __future__ import annotations

from .material_contract import (
    MATERIAL_CONTRACT_SCHEMA_VERSION,
    demo_materials,
    run_material_contract_demo,
    validate_material_contract,
)

__all__ = [
    "MATERIAL_CONTRACT_SCHEMA_VERSION",
    "demo_materials",
    "run_material_contract_demo",
    "validate_material_contract",
]
