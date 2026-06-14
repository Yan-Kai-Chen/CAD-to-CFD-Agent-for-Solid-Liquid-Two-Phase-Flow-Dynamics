"""Public validation suite for unstructured FastFluent routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .case_runner import run_unstructured_case_file, write_public_steady_channel_case
from .channel_validation import run_channel_validation_case, write_unit_square_channel_mesh
from .obstacle import run_obstacle_channel_evidence
from .turbulence_ladder import run_turbulence_ladder_case


PUBLIC_BENCHMARK_SUITE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_public_benchmark_suite_v1"


def run_public_benchmark_suite(
    *,
    output_dir: str | Path | None = None,
    iterations: int = 8,
) -> dict[str, Any]:
    """Run the current public unstructured benchmark evidence suite."""

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "unstructured_public_benchmark_suite" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        from ..vof_transport import run_vof_lite_transport_benchmark

        if iterations < 3:
            raise ValueError("Public benchmark suite iterations must be at least 3.")
        channel_mesh = write_unit_square_channel_mesh(target_dir / "public_suite_channel.msh", nx=8, ny=4)
        steady_case = write_public_steady_channel_case(
            target_dir / "steady_channel_case.json",
            mesh_file=channel_mesh.resolve(),
            case_name="public_suite_steady_channel",
            iterations=iterations,
        )
        cases = {
            "poiseuille_channel": run_channel_validation_case(
                channel_mesh,
                output_dir=target_dir / "01_poiseuille_channel",
                viscosity=1.0,
                pressure_drop=1.0,
            ),
            "steady_incompressible_case": run_unstructured_case_file(
                steady_case,
                output_dir=target_dir / "02_steady_incompressible_case",
            ),
            "body_fitted_obstacle_channel": run_obstacle_channel_evidence(
                output_dir=target_dir / "03_body_fitted_obstacle_channel",
                nx=12,
                ny=6,
            ),
            "vof_lite_alpha_transport": run_vof_lite_transport_benchmark(
                channel_mesh,
                output_dir=target_dir / "04_vof_lite_alpha_transport",
                steps=12,
                time_step_s=0.02,
                velocity_m_s=(0.1, 0.0),
            ),
            "turbulence_ladder": run_turbulence_ladder_case(
                output_dir=target_dir / "05_turbulence_ladder",
                iterations=iterations,
            ),
        }
        summary = _build_suite_summary(cases=cases, channel_mesh=channel_mesh, iterations=iterations)
        artifacts = {
            "public_channel_mesh": str(channel_mesh),
            "steady_case": str(steady_case),
            "benchmark_suite_summary": str(_write_json(target_dir / "benchmark_suite_summary.json", summary)),
            "benchmark_suite_report": str(_write_text(target_dir / "benchmark_suite_report.md", _suite_markdown(summary))),
        }
        for name, case in cases.items():
            artifacts[f"{name}_status"] = case.get("outputs", {}).get("artifacts", {}).get(
                _status_artifact_key(name),
                case.get("outputs", {}).get("artifacts", {}).get("case_status", ""),
            )
        if summary["status"] != "passed":
            result = AgentResult.failed(
                backend="unstructured_fvm",
                operation="run_public_benchmark_suite",
                message="Public unstructured benchmark suite completed but one or more cases failed.",
                errors=summary["blocking_errors"],
                metadata={"output_dir": str(target_dir)},
            )
            result.outputs.update({"artifacts": artifacts, "summary": summary, "solver_execution": "public_benchmark_suite_failed_acceptance"})
        else:
            result = AgentResult.success(
                backend="unstructured_fvm",
                operation="run_public_benchmark_suite",
                message="Public unstructured benchmark suite completed.",
                outputs={"artifacts": artifacts, "summary": summary, "solver_execution": "public_benchmark_suite"},
                metadata={"output_dir": str(target_dir)},
            )
        artifacts["benchmark_suite_status"] = str(_write_json(target_dir / "benchmark_suite_status.json", result.to_dict()))
        return result.to_dict()
    except (OSError, ValueError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="run_public_benchmark_suite",
            message="Public unstructured benchmark suite failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"benchmark_suite_status": str(target_dir / "benchmark_suite_status.json")}
        _write_json(target_dir / "benchmark_suite_status.json", failure.to_dict())
        return failure.to_dict()


def _build_suite_summary(*, cases: dict[str, dict[str, Any]], channel_mesh: Path, iterations: int) -> dict[str, Any]:
    case_summaries: dict[str, Any] = {}
    blocking_errors: list[str] = []
    for name, result in cases.items():
        passed = result.get("status") == "success"
        if not passed:
            blocking_errors.append(f"{name} failed: {result.get('errors')}")
        qoi = result.get("outputs", {}).get("qoi") or result.get("outputs", {}).get("summary") or result.get("outputs", {}).get("convergence") or {}
        case_summaries[name] = {
            "status": result.get("status"),
            "operation": result.get("operation"),
            "solver_execution": result.get("outputs", {}).get("solver_execution"),
            "errors": result.get("errors", []),
            "qoi_status": qoi.get("status"),
            "key_metrics": _extract_key_metrics(name, qoi),
        }
    return {
        "schema_version": PUBLIC_BENCHMARK_SUITE_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "status": "passed" if not blocking_errors else "failed",
        "channel_mesh": str(channel_mesh),
        "iterations": iterations,
        "case_order": list(cases),
        "cases": case_summaries,
        "blocking_errors": blocking_errors,
        "limitations": [
            "This suite is public-safe validation evidence for the current unstructured route.",
            "It combines controlled benchmarks and evidence gates; it is not production Fluent validation.",
            "Private engineering geometry and Fluent case/data files are not used.",
        ],
    }


def _extract_key_metrics(name: str, qoi: dict[str, Any]) -> dict[str, Any]:
    metrics = qoi.get("metrics", {})
    if name == "poiseuille_channel":
        return {
            "node_velocity_l2_error": metrics.get("node_velocity_l2_error"),
            "cell_center_velocity_l2_error": metrics.get("cell_center_velocity_l2_error"),
            "mass_balance_abs_flux": metrics.get("mass_balance_abs_flux"),
            "max_velocity_exact": metrics.get("max_velocity_exact"),
        }
    if name == "steady_incompressible_case":
        return {
            "final_divergence_l2": metrics.get("final_divergence_l2"),
            "mass_flux_relative_imbalance": metrics.get("mass_flux", {}).get("relative_imbalance"),
            "max_speed": metrics.get("max_speed"),
        }
    if name == "body_fitted_obstacle_channel":
        return {
            "blockage_ratio": qoi.get("blockage_ratio"),
            "top_clearance": qoi.get("top_clearance"),
            "bottom_clearance": qoi.get("bottom_clearance"),
        }
    if name == "vof_lite_alpha_transport":
        return {
            "max_courant_number": metrics.get("max_courant_number"),
            "relative_balance_error": metrics.get("relative_balance_error"),
            "min_alpha": metrics.get("min_alpha"),
            "max_alpha": metrics.get("max_alpha"),
        }
    if name == "turbulence_ladder":
        return {
            "recommendation": qoi.get("recommendation", {}).get("tier"),
            "case_count": len(qoi.get("case_order", [])),
        }
    return metrics


def _status_artifact_key(name: str) -> str:
    return {
        "poiseuille_channel": "channel_status",
        "steady_incompressible_case": "case_status",
        "body_fitted_obstacle_channel": "obstacle_channel_status",
        "vof_lite_alpha_transport": "vof_lite_status",
        "turbulence_ladder": "turbulence_ladder_status",
    }.get(name, "status")


def _suite_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# FastFluent Public Unstructured Benchmark Suite",
        "",
        f"Status: `{summary['status']}`",
        f"Iterations: `{summary['iterations']}`",
        "",
        "## Cases",
        "",
    ]
    for name in summary["case_order"]:
        case = summary["cases"][name]
        lines.extend(
            [
                f"### {name}",
                "",
                f"- Status: `{case['status']}`",
                f"- QoI status: `{case.get('qoi_status')}`",
                f"- Key metrics: `{json.dumps(case.get('key_metrics', {}), ensure_ascii=True)}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "This suite is public-safe validation evidence. It is not production Fluent validation.",
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
