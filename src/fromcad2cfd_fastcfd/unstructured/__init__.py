"""Agent-safe unstructured mesh inspection utilities for FastFluent."""

from .boundary import validate_boundary_contract
from .channel_validation import (
    run_channel_convergence_case,
    run_channel_validation_case,
    solve_channel_poiseuille,
    write_unit_square_channel_mesh,
)
from .diffusion import run_scalar_diffusion_case, solve_manufactured_diffusion
from .flow import run_flow_benchmark_case, solve_iterative_projection_flow
from .geometry import build_fv_geometry, node_scalar_cell_gradients
from .inspect import inspect_mesh_file
from .linear import SparseMatrixCSR, solve_linear_system
from .mesh import UnstructuredMesh
from .obstacle import run_obstacle_channel_evidence, write_rectangular_obstacle_channel_mesh
from .projection import run_projection_benchmark_case, solve_manufactured_projection
from .stokes import run_stokes_benchmark_case, solve_manufactured_stokes

__all__ = [
    "SparseMatrixCSR",
    "UnstructuredMesh",
    "build_fv_geometry",
    "inspect_mesh_file",
    "node_scalar_cell_gradients",
    "run_channel_convergence_case",
    "run_channel_validation_case",
    "run_flow_benchmark_case",
    "run_obstacle_channel_evidence",
    "run_projection_benchmark_case",
    "run_scalar_diffusion_case",
    "run_stokes_benchmark_case",
    "solve_channel_poiseuille",
    "solve_iterative_projection_flow",
    "solve_manufactured_projection",
    "solve_manufactured_diffusion",
    "solve_manufactured_stokes",
    "solve_linear_system",
    "validate_boundary_contract",
    "write_rectangular_obstacle_channel_mesh",
    "write_unit_square_channel_mesh",
]
