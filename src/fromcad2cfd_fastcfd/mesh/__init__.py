"""Mesh Gateway v2 public facade for FastFluent."""

from __future__ import annotations

from .mesh_gateway import generate_structured_mesh_demo, inspect_mesh_gateway
from .structured_grid import build_structured_grid_manifest

__all__ = [
    "build_structured_grid_manifest",
    "generate_structured_mesh_demo",
    "inspect_mesh_gateway",
]
