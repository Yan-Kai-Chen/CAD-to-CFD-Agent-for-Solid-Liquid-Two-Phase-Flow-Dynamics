"""Agent-safe unstructured mesh inspection utilities for FastFluent."""

from .boundary import validate_boundary_contract
from .benchmark_suite import run_public_benchmark_suite
from .case_runner import run_unstructured_case_file, write_public_steady_channel_case
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
from .kepsilon_channel import (
    run_kepsilon_channel_case,
    run_pressure_corrected_kepsilon_channel_case,
    solve_kepsilon_channel,
    solve_pressure_corrected_kepsilon_channel,
)
from .linear import SparseMatrixCSR, solve_linear_system
from .mesh import UnstructuredMesh
from .obstacle import run_obstacle_channel_evidence, write_rectangular_obstacle_channel_mesh
from .projection import run_projection_benchmark_case, solve_manufactured_projection
from .stokes import run_stokes_benchmark_case, solve_manufactured_stokes
from .sst_channel import run_sst_channel_case, solve_sst_channel
from .steady_incompressible import run_steady_incompressible_case, solve_steady_incompressible
from .tetra_validation import run_tetra_diffusion_case, write_unit_cube_tetra_mesh
from .turbulent_channel import run_turbulent_channel_case, solve_algebraic_eddy_viscosity_channel
from .turbulence_ladder import run_turbulence_ladder_case

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
    "run_public_benchmark_suite",
    "run_scalar_diffusion_case",
    "run_stokes_benchmark_case",
    "run_steady_incompressible_case",
    "run_tetra_diffusion_case",
    "run_unstructured_case_file",
    "run_kepsilon_channel_case",
    "run_pressure_corrected_kepsilon_channel_case",
    "run_sst_channel_case",
    "run_turbulent_channel_case",
    "run_turbulence_ladder_case",
    "solve_channel_poiseuille",
    "solve_iterative_projection_flow",
    "solve_kepsilon_channel",
    "solve_pressure_corrected_kepsilon_channel",
    "solve_sst_channel",
    "solve_steady_incompressible",
    "solve_manufactured_projection",
    "solve_manufactured_diffusion",
    "solve_manufactured_stokes",
    "solve_linear_system",
    "solve_algebraic_eddy_viscosity_channel",
    "validate_boundary_contract",
    "write_rectangular_obstacle_channel_mesh",
    "write_public_steady_channel_case",
    "write_unit_cube_tetra_mesh",
    "write_unit_square_channel_mesh",
]
