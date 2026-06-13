"""Agent-safe unstructured mesh inspection utilities for FastFluent."""

from .diffusion import run_scalar_diffusion_case, solve_manufactured_diffusion
from .geometry import build_fv_geometry, node_scalar_cell_gradients
from .inspect import inspect_mesh_file
from .mesh import UnstructuredMesh

__all__ = [
    "UnstructuredMesh",
    "build_fv_geometry",
    "inspect_mesh_file",
    "node_scalar_cell_gradients",
    "run_scalar_diffusion_case",
    "solve_manufactured_diffusion",
]
