"""Turbulence benchmark ladder for agent-facing FastFluent evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .channel_validation import write_unit_square_channel_mesh
from .kepsilon_channel import run_kepsilon_channel_case, run_pressure_corrected_kepsilon_channel_case
from .sst_channel import run_sst_channel_case
from .turbulent_channel import run_turbulent_channel_case


TURBULENCE_LADDER_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_turbulence_ladder_v1"


def run_turbulence_ladder_case(
    *,
    output_dir: str | Path | None = None,
    iterations: int = 8,
    density: float = 1.0,
    molecular_viscosity: float = 1.0e-3,
    pressure_drop: float = 0.05,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
) -> dict[str, Any]:
    """Run all bounded turbulence channel evidence tiers on one public mesh."""

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "unstructured_turbulence_ladder" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        if iterations < 3:
            raise ValueError("Turbulence ladder iterations must be at least 3.")
        mesh_path = write_unit_square_channel_mesh(target_dir / "public_turbulence_ladder_channel.msh", nx=10, ny=10)
        algebraic = run_turbulent_channel_case(
            mesh_path,
            output_dir=target_dir / "01_algebraic_eddy_viscosity",
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        kepsilon = run_kepsilon_channel_case(
            mesh_path,
            output_dir=target_dir / "02_standard_kepsilon",
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        pressure_kepsilon = run_pressure_corrected_kepsilon_channel_case(
            mesh_path,
            output_dir=target_dir / "03_pressure_corrected_kepsilon",
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        sst = run_sst_channel_case(
            mesh_path,
            output_dir=target_dir / "04_menter_sst",
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
            iterations=iterations,
            linear_solver=linear_solver,
            linear_tolerance=linear_tolerance,
            max_linear_iterations=max_linear_iterations,
        )
        summary = _build_ladder_summary(
            mesh_path=mesh_path,
            cases={
                "algebraic_eddy_viscosity": algebraic,
                "standard_kepsilon": kepsilon,
                "pressure_corrected_kepsilon": pressure_kepsilon,
                "menter_sst": sst,
            },
            iterations=iterations,
            density=density,
            molecular_viscosity=molecular_viscosity,
            pressure_drop=pressure_drop,
        )
        artifacts = {
            "public_mesh": str(mesh_path),
            "algebraic_status": algebraic["outputs"]["artifacts"].get("turbulent_channel_status", ""),
            "kepsilon_status": kepsilon["outputs"]["artifacts"].get("kepsilon_status", ""),
            "pressure_kepsilon_status": pressure_kepsilon["outputs"]["artifacts"].get("pressure_kepsilon_status", ""),
            "sst_status": sst["outputs"]["artifacts"].get("sst_status", ""),
            "turbulence_ladder_qoi": str(_write_json(target_dir / "turbulence_ladder_qoi.json", summary)),
            "turbulence_ladder_report": str(_write_text(target_dir / "turbulence_ladder_report.md", _ladder_markdown(summary))),
        }
        if summary["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="solve_turbulence_ladder",
                message="Turbulence ladder completed but one or more tiers failed.",
                errors=summary["blocking_errors"],
                metadata={"output_dir": str(target_dir), "mesh_file": str(mesh_path)},
            )
            result.outputs.update({"artifacts": artifacts, "qoi": summary, "solver_execution": "turbulence_ladder_failed_acceptance"})
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="solve_turbulence_ladder",
                message="Turbulence benchmark ladder completed.",
                outputs={"artifacts": artifacts, "qoi": summary, "solver_execution": "turbulence_ladder"},
                metadata={"output_dir": str(target_dir), "mesh_file": str(mesh_path)},
            )
        artifacts["turbulence_ladder_status"] = str(_write_json(target_dir / "turbulence_ladder_status.json", result.to_dict()))
        return result.to_dict()
    except (OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="solve_turbulence_ladder",
            message="Turbulence ladder failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"turbulence_ladder_status": str(target_dir / "turbulence_ladder_status.json")}
        _write_json(target_dir / "turbulence_ladder_status.json", failure.to_dict())
        return failure.to_dict()


def _build_ladder_summary(
    *,
    mesh_path: Path,
    cases: dict[str, dict[str, Any]],
    iterations: int,
    density: float,
    molecular_viscosity: float,
    pressure_drop: float,
) -> dict[str, Any]:
    case_summaries = {}
    blocking_errors = []
    for name, result in cases.items():
        qoi = result.get("outputs", {}).get("qoi", {})
        metrics = qoi.get("metrics", {})
        acceptance = qoi.get("acceptance", {})
        passed = result.get("status") == "success" and qoi.get("status") == "passed"
        if not passed:
            blocking_errors.append(f"{name} failed: {result.get('errors') or qoi.get('blocking_errors')}")
        case_summaries[name] = {
            "status": result.get("status"),
            "qoi_status": qoi.get("status"),
            "solver_family": qoi.get("solver_family"),
            "closure_model": qoi.get("closure_model", {}).get("model"),
            "acceptance": acceptance,
            "metrics": {
                "bulk_reynolds_number": metrics.get("bulk_reynolds_number"),
                "max_turbulent_viscosity_ratio": metrics.get("max_turbulent_viscosity_ratio"),
                "mean_turbulent_viscosity_ratio": metrics.get("mean_turbulent_viscosity_ratio"),
                "mean_turbulent_kinetic_energy": metrics.get("mean_turbulent_kinetic_energy"),
                "mean_epsilon": metrics.get("mean_epsilon"),
                "mean_omega": metrics.get("mean_omega"),
                "mean_f1": metrics.get("mean_f1"),
                "mean_f2": metrics.get("mean_f2"),
                "final_velocity_update_l2": metrics.get("final_velocity_update_l2"),
                "final_divergence_l2": metrics.get("final_divergence_l2"),
                "final_step_divergence_reduction_ratio": metrics.get("final_step_divergence_reduction_ratio"),
                "wall_no_slip_abs_max": metrics.get("wall_no_slip_abs_max"),
            },
        }
    recommendation = _recommend_next_step(case_summaries)
    return {
        "schema_version": TURBULENCE_LADDER_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "status": "passed" if not blocking_errors else "failed",
        "mesh_file": str(mesh_path),
        "iterations": iterations,
        "density": density,
        "molecular_viscosity": molecular_viscosity,
        "pressure_drop": pressure_drop,
        "case_order": ["algebraic_eddy_viscosity", "standard_kepsilon", "pressure_corrected_kepsilon", "menter_sst"],
        "cases": case_summaries,
        "recommendation": recommendation,
        "blocking_errors": blocking_errors,
        "limitations": [
            "The ladder compares bounded local channel benchmarks only.",
            "It is an agent evidence summary for selecting later Fluent setup work, not production CFD validation.",
            "Private engineering geometry, Fluent case/data files, and arbitrary solver inputs are not used.",
        ],
    }


def _recommend_next_step(case_summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sst_case = case_summaries.get("menter_sst", {})
    pressure_case = case_summaries.get("pressure_corrected_kepsilon", {})
    kepsilon_case = case_summaries.get("standard_kepsilon", {})
    algebraic_case = case_summaries.get("algebraic_eddy_viscosity", {})
    if sst_case.get("status") == "success" and sst_case.get("qoi_status") == "passed":
        return {
            "tier": "menter_sst",
            "next_action": "Use SST as the strongest local turbulence-closure evidence, while retaining pressure-corrected k-epsilon as separate pressure-velocity coupling evidence.",
            "evidence": [
                f"max_mu_t_over_mu={sst_case.get('metrics', {}).get('max_turbulent_viscosity_ratio')}",
                f"mean_f1={sst_case.get('metrics', {}).get('mean_f1')}",
                f"mean_f2={sst_case.get('metrics', {}).get('mean_f2')}",
            ],
        }
    if pressure_case.get("status") == "success" and pressure_case.get("qoi_status") == "passed":
        return {
            "tier": "pressure_corrected_kepsilon",
            "next_action": "Use pressure-corrected k-epsilon evidence as the strongest local turbulence pre-check before Fluent RANS setup.",
            "evidence": [
                f"max_mu_t_over_mu={pressure_case.get('metrics', {}).get('max_turbulent_viscosity_ratio')}",
                f"final_step_divergence_ratio={pressure_case.get('metrics', {}).get('final_step_divergence_reduction_ratio')}",
            ],
        }
    if kepsilon_case.get("status") == "success" and kepsilon_case.get("qoi_status") == "passed":
        return {
            "tier": "standard_kepsilon",
            "next_action": "Use two-equation k-epsilon evidence, but defer pressure-velocity coupling claims.",
            "evidence": [f"max_mu_t_over_mu={kepsilon_case.get('metrics', {}).get('max_turbulent_viscosity_ratio')}"],
        }
    if algebraic_case.get("status") == "success" and algebraic_case.get("qoi_status") == "passed":
        return {
            "tier": "algebraic_eddy_viscosity",
            "next_action": "Use algebraic eddy-viscosity evidence only and rerun k-epsilon diagnostics before Fluent RANS setup.",
            "evidence": [f"max_mu_t_over_mu={algebraic_case.get('metrics', {}).get('max_turbulent_viscosity_ratio')}"],
        }
    return {
        "tier": "blocked",
        "next_action": "Do not use turbulence benchmark evidence until failed tiers are repaired.",
        "evidence": [],
    }


def _ladder_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# FastFluent Turbulence Benchmark Ladder",
        "",
        f"Status: `{summary['status']}`",
        f"Recommended tier: `{summary['recommendation']['tier']}`",
        "",
        "## Cases",
        "",
    ]
    for name in summary["case_order"]:
        case = summary["cases"][name]
        metrics = case["metrics"]
        lines.extend(
            [
                f"### {name}",
                "",
                f"- Status: `{case['status']}`",
                f"- QoI status: `{case['qoi_status']}`",
                f"- Closure: `{case['closure_model']}`",
                f"- Re: `{metrics.get('bulk_reynolds_number')}`",
                f"- Max mu_t / mu: `{metrics.get('max_turbulent_viscosity_ratio')}`",
                f"- Wall no-slip max: `{metrics.get('wall_no_slip_abs_max')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "This ladder is a bounded local evidence comparison. It is not production Fluent validation.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
