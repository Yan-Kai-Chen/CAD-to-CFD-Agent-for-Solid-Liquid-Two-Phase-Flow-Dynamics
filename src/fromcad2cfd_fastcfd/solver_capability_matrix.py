"""Solver capability matrix for FastFluent native expansion planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SOLVER_CAPABILITY_MATRIX_SCHEMA_VERSION = "fastfluent_solver_capability_matrix_v1"


def solver_capability_matrix() -> dict[str, Any]:
    """Return the current bounded FastFluent solver capability matrix."""

    capabilities = [
        _capability(
            "structured_lbm_cavity_channel_obstacle",
            status="bounded_native",
            physics=["incompressible_lbm"],
            mesh=["structured_cartesian_2d"],
            entrypoints=[
                "fastcfd write-cavity2d-job",
                "fastcfd write-channel2d-job",
                "fastcfd write-obstacle2d-job",
                "fastcfd run-fastfluent-job",
            ],
            validation=["physics_passport", "native_summary", "native_convergence", "field_qoi", "pilot_decision"],
            boundary="advisory pilot evidence, not final Fluent validation",
        ),
        _capability(
            "unstructured_scalar_diffusion_2d",
            status="bounded_native",
            physics=["steady_scalar_diffusion"],
            mesh=["gmsh_v4_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-diffusion"],
            validation=["manufactured_solution", "mesh_quality", "linear_residual", "solution_vtu"],
            boundary="manufactured benchmark route",
        ),
        _capability(
            "unstructured_scalar_diffusion_3d_tetra",
            status="bounded_native",
            physics=["steady_scalar_diffusion"],
            mesh=["gmsh_v4_tetra_3d"],
            entrypoints=["fastcfd unstructured solve-tetra-diffusion"],
            validation=["public_tetra_smoke", "mesh_quality", "linear_residual", "solution_vtu"],
            boundary="3D smoke benchmark route",
        ),
        _capability(
            "unstructured_stokes_momentum",
            status="bounded_native",
            physics=["linear_stokes_momentum"],
            mesh=["gmsh_v4_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-stokes"],
            validation=["manufactured_velocity", "linear_residual", "velocity_l2_error", "solution_vtu"],
            boundary="linear manufactured Stokes benchmark",
        ),
        _capability(
            "unstructured_projection_pressure_correction",
            status="bounded_native",
            physics=["pressure_correction_projection"],
            mesh=["gmsh_v4_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-projection", "fastcfd unstructured solve-flow-benchmark"],
            validation=["divergence_reduction", "pressure_linear_residual", "velocity_update_history"],
            boundary="controlled projection benchmark",
        ),
        _capability(
            "unstructured_steady_incompressible",
            status="hardened_s4",
            physics=["steady_incompressible_pressure_correction"],
            mesh=["gmsh_v4_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-steady-incompressible", "fastcfd unstructured run-case"],
            validation=[
                "mesh_quality",
                "boundary_contract",
                "linear_systems",
                "mass_flux",
                "divergence",
                "hardening_summary",
                "passed_warning_failed_quality_status",
                "agent_decision",
            ],
            boundary="bounded public case route, not production SIMPLE/PISO",
        ),
        _capability(
            "unstructured_channel_validation",
            status="bounded_native",
            physics=["poiseuille_channel_validation"],
            mesh=["gmsh_v4_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-channel-validation", "fastcfd unstructured solve-channel-convergence"],
            validation=["analytic_profile", "grid_convergence", "mass_balance"],
            boundary="public validation benchmark",
        ),
        _capability(
            "unstructured_body_fitted_obstacle",
            status="bounded_native",
            physics=["obstacle_channel_evidence"],
            mesh=["generated_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-obstacle-channel"],
            validation=["named_zone_preservation", "mesh_quality", "geometry_qoi"],
            boundary="geometry and setup evidence route",
        ),
        _capability(
            "motion_contract_preflight",
            status="implemented_motion_m0",
            physics=["kinematic_motion_preflight"],
            mesh=["mesh_independent_contract"],
            entrypoints=["fastcfd motion validate", "fastcfd motion sample"],
            validation=["dangerous_key_filter", "motion_sampling", "kinematic_report"],
            boundary="moving boundary and obstacle contract only, not dynamic mesh or FSI",
        ),
        _capability(
            "motion_mesh_adapter",
            status="implemented_motion_m1",
            physics=["kinematic_motion_preflight"],
            mesh=["gmsh_v4_named_boundary_patches"],
            entrypoints=["fastcfd motion adapt-mesh"],
            validation=["patch_binding", "boundary_node_inventory", "motion_courant_gate", "solver_adapter_json"],
            boundary="mesh-aware motion adapter only, not mesh deformation or moving-boundary CFD",
        ),
        _capability(
            "motion_solver_preflight",
            status="implemented_motion_m2",
            physics=["kinematic_motion_preflight"],
            mesh=["gmsh_v4_named_boundary_patches"],
            entrypoints=["fastcfd motion solver-preflight", "fastcfd unstructured run-case --motion-adapter"],
            validation=["adapter_status_gate", "active_motion_detection", "dynamic_mesh_block", "run_case_dispatch_gate"],
            boundary="solver-dispatch gate for static-grid motion evidence, not moving-mesh solving",
        ),
        _capability(
            "quasi_steady_motion_evidence",
            status="implemented_motion_m3",
            physics=["quasi_steady_kinematic_motion"],
            mesh=["gmsh_v4_named_boundary_patches"],
            entrypoints=["fastcfd motion quasi-steady"],
            validation=["motion_preflight", "snapshot_history", "steady_run_per_snapshot", "time_series_qoi"],
            boundary="static-grid snapshot evidence only, not dynamic mesh",
        ),
        _capability(
            "moving_obstacle_motion_evidence",
            status="implemented_motion_m4",
            physics=["quasi_steady_moving_obstacle_evidence"],
            mesh=["public_body_fitted_obstacle_channel"],
            entrypoints=["fastcfd motion moving-obstacle-demo"],
            validation=["obstacle_wall_binding", "obstacle_mesh_evidence", "quasi_steady_sequence"],
            boundary="public synthetic evidence route, not immersed-boundary or FSI solving",
        ),
        _capability(
            "native_result_bundle_unification",
            status="implemented_s5",
            physics=["native_result_packaging"],
            mesh=["route_independent"],
            entrypoints=["fastcfd result-pack compile-native"],
            validation=[
                "native_result_summary",
                "quality_status_preservation",
                "artifact_index",
                "agent_handoff",
                "screening_boundary",
            ],
            boundary="unified advisory evidence packaging, not solver execution",
        ),
        _capability(
            "unified_transport_coupling_core",
            status="implemented_s6",
            physics=["bounded_scalar_transport", "temperature_transport", "species_transport", "particle_concentration_proxy", "wax_fraction_proxy"],
            mesh=["gmsh_v4_triangle_2d", "generated_public_channel_2d"],
            entrypoints=["fastcfd transport demo", "fastcfd transport run"],
            validation=[
                "transport_case_schema",
                "courant_gate",
                "diffusion_gate",
                "boundedness_gate",
                "conservation_or_balance_qoi",
                "material_property_coupling",
                "result_pack_compatibility",
            ],
            boundary="unified scalar transport evidence, not coupled pressure-momentum or final Fluent validation",
        ),
        _capability(
            "full_workflow_case_runner",
            status="implemented_s7",
            physics=["workflow_orchestration", "native_advisory_transport"],
            mesh=["flow_pack_mesh_gateway", "generated_public_channel_2d"],
            entrypoints=["fastcfd workflow run", "fastcfd workflow demo"],
            validation=[
                "casespec_ingestion",
                "flow_pack_gate",
                "route_selection",
                "route_plan",
                "execution_gate",
                "controlled_runner",
                "native_advisory_transport",
                "result_pack",
                "agent_decision",
                "stage_stop_on_failure",
            ],
            boundary="agent workflow orchestration and advisory evidence only; no Fluent launch",
        ),
        _capability(
            "vof_lite_alpha_transport",
            status="advisory_native",
            physics=["bounded_alpha_transport"],
            mesh=["gmsh_v4_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-vof-lite"],
            validation=["bounded_alpha", "courant_check", "mass_balance"],
            boundary="VOF-lite transport evidence, not full VOF Navier-Stokes",
        ),
        _capability(
            "algebraic_eddy_viscosity_channel",
            status="advisory_native",
            physics=["zero_equation_eddy_viscosity"],
            mesh=["generated_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-turbulent-channel"],
            validation=["eddy_viscosity_activation", "velocity_update", "wall_no_slip"],
            boundary="local turbulence evidence benchmark",
        ),
        _capability(
            "standard_k_epsilon_channel",
            status="advisory_native",
            physics=["k_epsilon_transport"],
            mesh=["generated_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-kepsilon-channel"],
            validation=["positive_k", "positive_epsilon", "production", "eddy_viscosity"],
            boundary="bounded k-epsilon channel benchmark",
        ),
        _capability(
            "pressure_corrected_k_epsilon_channel",
            status="advisory_native",
            physics=["pressure_corrected_k_epsilon"],
            mesh=["generated_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-kepsilon-pressure-channel"],
            validation=["pressure_correction", "divergence_monitor", "positive_turbulence_fields"],
            boundary="bounded pressure-corrected turbulence benchmark",
        ),
        _capability(
            "menter_sst_channel",
            status="advisory_native",
            physics=["menter_sst_transport"],
            mesh=["generated_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-sst-channel"],
            validation=["positive_k_omega", "blending_functions", "eddy_viscosity"],
            boundary="bounded SST channel benchmark",
        ),
        _capability(
            "turbulence_ladder",
            status="advisory_native",
            physics=["turbulence_model_ranking"],
            mesh=["generated_triangle_2d"],
            entrypoints=["fastcfd unstructured solve-turbulence-ladder"],
            validation=["tiered_model_results", "recommendation", "failed_tier_reporting"],
            boundary="agent model-selection evidence, not final turbulence validation",
        ),
    ]
    counts = _status_counts(capabilities)
    return {
        "schema_version": SOLVER_CAPABILITY_MATRIX_SCHEMA_VERSION,
        "status": "success",
        "capability_count": len(capabilities),
        "status_counts": counts,
        "capabilities": capabilities,
        "priority_next_steps": [
            {
                "id": "moving_geometry_coupling",
                "why": "Moving boundaries and obstacles need a shared kinematic contract before dynamic mesh or immersed-boundary solvers are added.",
                "acceptance": ["motion_contract", "time_sampling", "solver_adapter_boundary"],
            },
        ],
        "global_boundary": [
            "FastFluent native routes are advisory and workflow-supporting.",
            "They do not replace Fluent for final CFD validation.",
            "Every new physics capability should declare mesh support, boundary support, conservation checks, convergence checks, and result-pack compatibility.",
        ],
    }


def write_solver_capability_matrix(output_dir: str | Path) -> dict[str, Any]:
    """Write the capability matrix as JSON and Markdown."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    matrix = solver_capability_matrix()
    artifacts = {
        "solver_capability_matrix": str(root / "solver_matrix.json"),
        "solver_capability_matrix_report": str(root / "solver_matrix.md"),
    }
    matrix["artifacts"] = artifacts
    _write_json(root / "solver_matrix.json", matrix)
    (root / "solver_matrix.md").write_text(solver_capability_matrix_markdown(matrix), encoding="utf-8")
    return matrix


def solver_capability_matrix_markdown(matrix: dict[str, Any]) -> str:
    """Render the capability matrix as Markdown."""

    lines = [
        "# FastFluent Solver Capability Matrix",
        "",
        f"- Capability count: `{matrix.get('capability_count')}`",
        f"- Status counts: `{json.dumps(matrix.get('status_counts', {}), ensure_ascii=True)}`",
        "",
        "| Capability | Status | Physics | Mesh | Boundary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in matrix.get("capabilities", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("id")),
                    str(item.get("status")),
                    ", ".join(item.get("physics", [])),
                    ", ".join(item.get("mesh", [])),
                    str(item.get("boundary")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Priority Next Steps", ""])
    for step in matrix.get("priority_next_steps", []):
        lines.append(f"- `{step.get('id')}`: {step.get('why')}")
    lines.extend(["", "## Boundary", ""])
    for item in matrix.get("global_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _capability(
    capability_id: str,
    *,
    status: str,
    physics: list[str],
    mesh: list[str],
    entrypoints: list[str],
    validation: list[str],
    boundary: str,
) -> dict[str, Any]:
    return {
        "id": capability_id,
        "status": status,
        "physics": physics,
        "mesh": mesh,
        "entrypoints": entrypoints,
        "validation": validation,
        "boundary": boundary,
    }


def _status_counts(capabilities: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in capabilities:
        status = str(item.get("status"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path
