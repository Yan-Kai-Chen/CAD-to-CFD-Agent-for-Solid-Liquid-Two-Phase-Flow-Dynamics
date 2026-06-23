"""Quasi-steady motion evidence routes for FastFluent."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .motion_adapter import adapt_motion_to_mesh
from .motion_solver_preflight import run_motion_solver_preflight
from .unstructured.case_runner import run_unstructured_case_file
from .unstructured.obstacle import run_obstacle_channel_evidence, write_rectangular_obstacle_channel_mesh


QUASI_STEADY_SCHEMA_VERSION = "fastfluent_quasi_steady_motion_v1"
MOVING_OBSTACLE_SCHEMA_VERSION = "fastfluent_moving_obstacle_evidence_v1"


def run_quasi_steady_motion_case(
    case_file: str | Path,
    motion_adapter_file: str | Path,
    output_dir: str | Path,
    *,
    execution_mode: str = "static_grid_motion_evidence",
    max_snapshots: int | None = None,
) -> dict[str, Any]:
    """Run a bounded quasi-steady motion evidence sequence.

    Each snapshot uses the current static-grid solver route. Motion is attached
    as evidence and summarized by time; no mesh deformation is applied.
    """

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    case_path = Path(case_file)
    adapter_path = Path(motion_adapter_file)
    adapter = _read_json(adapter_path)
    preflight = run_motion_solver_preflight(
        adapter_path,
        root / "pre",
        solver_family="steady_incompressible",
        execution_mode=execution_mode,
        case_file=case_path,
    )
    samples = _read_motion_samples(_motion_samples_path(adapter, adapter_path))
    times = _sample_times(samples)
    if max_snapshots is not None:
        if max_snapshots < 1:
            raise ValueError("max_snapshots must be at least 1 when provided.")
        times = times[:max_snapshots]

    snapshots: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    if preflight["solver_dispatch_allowed"]:
        for index, time_s in enumerate(times):
            snap_dir = root / f"s{index:03d}"
            result = run_unstructured_case_file(
                case_path,
                output_dir=snap_dir,
                motion_adapter_file=adapter_path,
                motion_execution_mode=execution_mode,
            )
            motion_qoi = _motion_qoi_at_time(samples, time_s)
            row = _history_row(index=index, time_s=time_s, run_result=result, motion_qoi=motion_qoi, preflight=preflight)
            snapshots.append(
                {
                    "index": index,
                    "time_s": time_s,
                    "status": result.get("status"),
                    "quality_status": _snapshot_quality_status(result),
                    "snapshot_dir": str(snap_dir),
                    "case_status": result.get("outputs", {}).get("artifacts", {}).get("case_status"),
                    "motion_qoi": motion_qoi,
                    "solver_qoi": _compact_solver_qoi(result),
                    "errors": result.get("errors", []),
                }
            )
            history_rows.append(row)

    overall_status = _overall_status(preflight, snapshots)
    summary_qoi = _summary_qoi(history_rows, preflight)
    quality_status = _quality_status_from_history(history_rows, preflight)
    agent_decision = _quasi_agent_decision(quality_status=quality_status, summary_qoi=summary_qoi, preflight=preflight)
    artifacts = {
        "preflight": preflight["artifacts"]["motion_solver_preflight"],
        "decision": preflight["artifacts"]["motion_solver_decision"],
        "qs_summary": str(root / "qs_summary.json"),
        "qs_history": str(root / "qs_history.csv"),
        "qs_report": str(root / "qs_report.md"),
    }
    result = {
        "schema_version": QUASI_STEADY_SCHEMA_VERSION,
        "status": overall_status,
        "case_file": str(case_path),
        "motion_adapter_file": str(adapter_path),
        "execution_mode": execution_mode,
        "preflight": preflight,
        "sample_count": len(times),
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "quality_status": quality_status,
        "summary_qoi": summary_qoi,
        "agent_decision": agent_decision,
        "artifacts": artifacts,
        "blocking_errors": [] if preflight["solver_dispatch_allowed"] else list(preflight.get("blocking_errors", [])),
        "quality_warnings": agent_decision.get("warnings", []),
        "limitations": _quasi_steady_limitations(),
    }
    _write_history(root / "qs_history.csv", history_rows)
    _write_json(root / "qs_summary.json", result)
    _write_text(root / "qs_report.md", quasi_steady_markdown(result))
    return result


def run_moving_obstacle_evidence_demo(
    output_dir: str | Path,
    *,
    nx: int = 12,
    ny: int = 6,
    time_step_s: float = 0.05,
    total_time_s: float = 0.2,
    iterations: int = 2,
) -> dict[str, Any]:
    """Run a public moving-obstacle evidence demo without private geometry."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    mesh_path = write_rectangular_obstacle_channel_mesh(root / "obs.msh", nx=nx, ny=ny)
    case_path = _write_obstacle_case(root / "case.json", mesh_path, iterations=iterations)
    motion_payload = _moving_obstacle_motion_payload()
    _write_json(root / "motion.json", motion_payload)
    adapter = adapt_motion_to_mesh(
        motion_payload,
        mesh_path,
        root / "ad",
        time_step_s=time_step_s,
        total_time_s=total_time_s,
    )
    obstacle_evidence = run_obstacle_channel_evidence(mesh_path, output_dir=root / "oe", nx=nx, ny=ny)
    quasi = run_quasi_steady_motion_case(case_path, adapter["artifacts"]["motion_mesh_adapter"], root / "qs")
    status = "success" if adapter["status"] in {"passed", "warning"} and obstacle_evidence["status"] == "success" and quasi["status"] == "success" else "failed"
    quality_status = "failed" if status != "success" else quasi.get("quality_status", "unknown")
    agent_decision = _moving_obstacle_agent_decision(status=status, quality_status=quality_status, quasi=quasi)
    result = {
        "schema_version": MOVING_OBSTACLE_SCHEMA_VERSION,
        "status": status,
        "quality_status": quality_status,
        "mesh_file": str(mesh_path),
        "case_file": str(case_path),
        "motion_file": str(root / "motion.json"),
        "motion_adapter": adapter,
        "obstacle_evidence": _compact_result(obstacle_evidence),
        "quasi_steady": _compact_quasi(quasi),
        "agent_decision": agent_decision,
        "artifacts": {
            "mesh": str(mesh_path),
            "case": str(case_path),
            "motion": str(root / "motion.json"),
            "motion_adapter": adapter["artifacts"]["motion_mesh_adapter"],
            "obstacle_evidence": obstacle_evidence.get("outputs", {}).get("artifacts", {}).get("obstacle_status"),
            "quasi_steady_summary": quasi["artifacts"]["qs_summary"],
            "moving_obstacle_summary": str(root / "mo_summary.json"),
            "moving_obstacle_report": str(root / "mo_report.md"),
        },
        "limitations": [
            "This is a public synthetic moving-obstacle evidence demo.",
            "The obstacle geometry is not actually displaced in the mesh.",
            "No dynamic mesh, immersed-boundary solve, or FSI coupling is performed.",
        ],
    }
    _write_json(root / "mo_summary.json", result)
    _write_text(root / "mo_report.md", moving_obstacle_markdown(result))
    return result


def quasi_steady_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# FastFluent Quasi-Steady Motion Evidence",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Quality status: `{result.get('quality_status')}`",
        f"- Execution mode: `{result.get('execution_mode')}`",
        f"- Snapshot count: `{result.get('snapshot_count')}`",
        f"- Max motion Courant: `{result.get('summary_qoi', {}).get('max_motion_courant')}`",
        f"- Mean final divergence L2: `{result.get('summary_qoi', {}).get('mean_final_divergence_l2')}`",
        f"- Recommended next action: `{result.get('agent_decision', {}).get('recommended_next_action')}`",
        "",
        "## Boundary",
        "",
    ]
    lines.extend(f"- {item}" for item in result.get("limitations", []))
    if result.get("blocking_errors"):
        lines.extend(["", "## Blocking Errors", ""])
        lines.extend(f"- {item}" for item in result["blocking_errors"])
    lines.append("")
    return "\n".join(lines)


def moving_obstacle_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# FastFluent Moving-Obstacle Evidence Demo",
            "",
            f"- Status: `{result.get('status')}`",
            f"- Quality status: `{result.get('quality_status')}`",
            f"- Mesh: `{result.get('mesh_file')}`",
            f"- Quasi-steady status: `{result.get('quasi_steady', {}).get('status')}`",
            f"- Recommended next action: `{result.get('agent_decision', {}).get('recommended_next_action')}`",
            f"- Snapshot count: `{result.get('quasi_steady', {}).get('snapshot_count')}`",
            "",
            "## Boundary",
            "",
            "- Public synthetic geometry only.",
            "- No mesh deformation, immersed-boundary solve, FSI, or Fluent replacement is claimed.",
            "",
        ]
    )


def _write_obstacle_case(path: Path, mesh_path: Path, *, iterations: int) -> Path:
    payload = {
        "schema_version": "fromcad2cfd_fastfluent_unstructured_case_v1",
        "case_name": "public_moving_obstacle_evidence_case",
        "mesh_file": str(mesh_path.resolve()),
        "required_patches": ["inlet", "outlet", "wall", "obstacle_wall"],
        "physics": {
            "model": "steady_incompressible",
            "density": 1.0,
            "viscosity": 0.01,
            "body_force": [0.0, 0.0],
        },
        "boundary_conditions": {
            "inlet": {"kind": "velocity_inlet", "velocity": [1.0, 0.0], "role": "uniform inlet velocity"},
            "outlet": {"kind": "pressure_outlet", "pressure": 0.0, "role": "pressure outlet reference"},
            "wall": {"kind": "no_slip_wall", "role": "outer no-slip channel walls"},
            "obstacle_wall": {"kind": "no_slip_wall", "role": "moving-obstacle wall represented as static no-slip evidence"},
        },
        "solver": {
            "family": "steady_incompressible",
            "iterations": iterations,
            "pressure_relaxation": 0.45,
            "linear_solver": "sparse_cg",
            "linear_tolerance": 1.0e-12,
            "max_linear_iterations": None,
        },
    }
    return _write_json(path, payload)


def _moving_obstacle_motion_payload() -> dict[str, Any]:
    return {
        "schema_version": "fastfluent_motion_contract_v1",
        "case_id": "public_moving_obstacle_motion_demo",
        "units": {"length": "m", "time": "s", "angle": "rad"},
        "motions": [
            {
                "id": "oscillating_obstacle_wall",
                "target_type": "obstacle",
                "target_name": "public_rectangular_obstacle",
                "target_patch_name": "obstacle_wall",
                "motion_kind": "sinusoidal_translation",
                "reference_point": [0.5, 0.5, 0.0],
                "parameters": {"amplitude_m": [0.005, 0.0, 0.0], "frequency_hz": 1.0, "phase_rad": 0.0},
            }
        ],
    }


def _read_motion_samples(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sample_times(rows: list[dict[str, str]]) -> list[float]:
    return sorted({float(row["time_s"]) for row in rows})


def _motion_qoi_at_time(rows: list[dict[str, str]], time_s: float) -> dict[str, float]:
    selected = [row for row in rows if float(row["time_s"]) == time_s]
    return {
        "max_translation_m": max((_vector_norm(row, "d") for row in selected), default=0.0),
        "max_translation_speed_m_s": max((_vector_norm(row, "v") for row in selected), default=0.0),
        "max_abs_angle_rad": max((abs(float(row["angle_rad"])) for row in selected), default=0.0),
        "max_abs_angular_velocity_rad_s": max((abs(float(row["angular_velocity_rad_s"])) for row in selected), default=0.0),
    }


def _history_row(index: int, time_s: float, run_result: dict[str, Any], motion_qoi: dict[str, float], preflight: dict[str, Any]) -> dict[str, Any]:
    metrics = run_result.get("outputs", {}).get("qoi", {}).get("metrics", {})
    hardening = run_result.get("outputs", {}).get("hardening_summary", {})
    decision = hardening.get("decision", {})
    return {
        "snapshot_index": index,
        "time_s": time_s,
        "status": run_result.get("status"),
        "hardening_status": hardening.get("status"),
        "solver_execution_mode": run_result.get("outputs", {}).get("solver_execution_mode"),
        "max_motion_courant": preflight.get("max_motion_courant", 0.0),
        "max_translation_m": motion_qoi["max_translation_m"],
        "max_translation_speed_m_s": motion_qoi["max_translation_speed_m_s"],
        "max_abs_angle_rad": motion_qoi["max_abs_angle_rad"],
        "mean_speed": metrics.get("mean_speed"),
        "max_flow_speed": metrics.get("max_speed"),
        "final_divergence_l2": metrics.get("final_divergence_l2"),
        "mass_flux_relative_imbalance": (metrics.get("mass_flux") or {}).get("relative_imbalance"),
        "recommended_next_action": decision.get("recommended_next_action"),
    }


def _compact_solver_qoi(run_result: dict[str, Any]) -> dict[str, Any]:
    qoi = run_result.get("outputs", {}).get("qoi", {})
    metrics = qoi.get("metrics", {})
    hardening = run_result.get("outputs", {}).get("hardening_summary", {})
    decision = hardening.get("decision", {})
    return {
        "status": qoi.get("status"),
        "solver_family": qoi.get("solver_family"),
        "hardening_status": hardening.get("status"),
        "recommended_next_action": decision.get("recommended_next_action"),
        "usable_as_native_advisory_seed": decision.get("usable_as_native_advisory_seed"),
        "mean_speed": metrics.get("mean_speed"),
        "max_speed": metrics.get("max_speed"),
        "final_divergence_l2": metrics.get("final_divergence_l2"),
        "mass_flux_relative_imbalance": (metrics.get("mass_flux") or {}).get("relative_imbalance"),
    }


def _summary_qoi(rows: list[dict[str, Any]], preflight: dict[str, Any]) -> dict[str, Any]:
    divergences = [float(row["final_divergence_l2"]) for row in rows if row.get("final_divergence_l2") is not None]
    mass = [float(row["mass_flux_relative_imbalance"]) for row in rows if row.get("mass_flux_relative_imbalance") is not None]
    hardening_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("hardening_status") or "unknown")
        hardening_counts[status] = hardening_counts.get(status, 0) + 1
    return {
        "max_motion_courant": preflight.get("max_motion_courant", 0.0),
        "mean_final_divergence_l2": sum(divergences) / len(divergences) if divergences else None,
        "max_final_divergence_l2": max(divergences) if divergences else None,
        "mean_mass_flux_relative_imbalance": sum(mass) / len(mass) if mass else None,
        "max_mass_flux_relative_imbalance": max(mass) if mass else None,
        "hardening_status_counts": dict(sorted(hardening_counts.items())),
    }


def _overall_status(preflight: dict[str, Any], snapshots: list[dict[str, Any]]) -> str:
    if not preflight["solver_dispatch_allowed"]:
        return "failed"
    if not snapshots:
        return "failed"
    return "success" if all(item["status"] == "success" for item in snapshots) else "partial"


def _snapshot_quality_status(run_result: dict[str, Any]) -> str:
    if run_result.get("status") != "success":
        return "failed"
    return str(run_result.get("outputs", {}).get("hardening_summary", {}).get("status") or "unknown")


def _quality_status_from_history(rows: list[dict[str, Any]], preflight: dict[str, Any]) -> str:
    if not preflight["solver_dispatch_allowed"]:
        return "failed"
    if not rows:
        return "failed"
    statuses = {str(row.get("hardening_status") or "unknown") for row in rows}
    if "failed" in statuses or "unknown" in statuses:
        return "failed"
    if "warning" in statuses:
        return "warning"
    return "passed"


def _quasi_agent_decision(*, quality_status: str, summary_qoi: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    actions: list[dict[str, str]] = []
    if not preflight["solver_dispatch_allowed"]:
        return {
            "usable_for_motion_screening": False,
            "usable_for_final_cfd_validation": False,
            "recommended_next_action": "blocked_by_motion_solver_preflight",
            "warnings": list(preflight.get("blocking_errors", [])),
            "agent_actions": [
                {
                    "action": "stop_and_repair_motion_contract_or_solver_request",
                    "priority": "critical",
                    "reason": "Motion solver preflight did not allow dispatch.",
                }
            ],
        }
    if quality_status == "passed":
        recommended = "use_as_motion_aware_advisory_seed"
        actions.append(
            {
                "action": "package_motion_screening_evidence",
                "priority": "medium",
                "reason": "All snapshots passed steady hardening gates.",
            }
        )
    elif quality_status == "warning":
        recommended = "use_for_screening_only_and_repair_before_fluent_handoff"
        warnings.append("At least one snapshot has marginal steady hardening quality.")
        if (summary_qoi.get("max_mass_flux_relative_imbalance") or 0.0) > 0.1:
            actions.append(
                {
                    "action": "repair_boundary_balance_or_refine_obstacle_region",
                    "priority": "high",
                    "reason": "Snapshot mass-flux imbalance exceeded the advisory tolerance.",
                }
            )
        if (summary_qoi.get("max_final_divergence_l2") or 0.0) > 0.5:
            actions.append(
                {
                    "action": "repair_pressure_correction_or_mesh_quality_before_fluent",
                    "priority": "high",
                    "reason": "Snapshot divergence exceeded the advisory tolerance.",
                }
            )
    else:
        recommended = "do_not_trust_motion_evidence_repair_case"
        actions.append(
            {
                "action": "stop_and_repair_snapshot_solver_failures",
                "priority": "critical",
                "reason": "One or more snapshots failed execution or hardening.",
            }
        )
    return {
        "usable_for_motion_screening": quality_status in {"passed", "warning"},
        "usable_for_final_cfd_validation": False,
        "recommended_next_action": recommended,
        "warnings": warnings,
        "agent_actions": actions,
    }


def _moving_obstacle_agent_decision(*, status: str, quality_status: str, quasi: dict[str, Any]) -> dict[str, Any]:
    if status != "success":
        return {
            "usable_for_motion_screening": False,
            "usable_for_final_cfd_validation": False,
            "recommended_next_action": "repair_moving_obstacle_demo_route",
            "agent_actions": [
                {
                    "action": "inspect_adapter_obstacle_evidence_and_quasi_steady_outputs",
                    "priority": "critical",
                    "reason": "The moving-obstacle route did not complete successfully.",
                }
            ],
        }
    decision = dict(quasi.get("agent_decision", {}))
    decision.setdefault("usable_for_motion_screening", quality_status in {"passed", "warning"})
    decision.setdefault("usable_for_final_cfd_validation", False)
    decision.setdefault("recommended_next_action", "use_for_screening_only_and_repair_before_fluent_handoff")
    return decision


def _motion_samples_path(adapter: dict[str, Any], adapter_path: Path) -> Path:
    raw = (adapter.get("artifacts") or {}).get("motion_samples") or (adapter.get("solver_adapter") or {}).get("motion_samples_csv")
    if not raw:
        raise ValueError("motion adapter does not contain a motion_samples artifact.")
    path = Path(raw)
    if path.is_absolute():
        return path
    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path
    return adapter_path.parent / path


def _vector_norm(row: dict[str, str], prefix: str) -> float:
    if prefix == "d":
        values = (float(row["dx_m"]), float(row["dy_m"]), float(row["dz_m"]))
    else:
        values = (float(row["vx_m_s"]), float(row["vy_m_s"]), float(row["vz_m_s"]))
    return sum(value * value for value in values) ** 0.5


def _write_history(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "snapshot_index",
        "time_s",
        "status",
        "hardening_status",
        "solver_execution_mode",
        "max_motion_courant",
        "max_translation_m",
        "max_translation_speed_m_s",
        "max_abs_angle_rad",
        "mean_speed",
        "max_flow_speed",
        "final_divergence_l2",
        "mass_flux_relative_imbalance",
        "recommended_next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": result.get("status"),
        "operation": result.get("operation"),
        "artifacts": result.get("outputs", {}).get("artifacts", {}),
        "errors": result.get("errors", []),
    }


def _compact_quasi(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": result.get("status"),
        "snapshot_count": result.get("snapshot_count"),
        "quality_status": result.get("quality_status"),
        "summary_qoi": result.get("summary_qoi"),
        "agent_decision": result.get("agent_decision"),
        "artifacts": result.get("artifacts", {}),
    }


def _quasi_steady_limitations() -> list[str]:
    return [
        "This is a quasi-steady static-grid evidence route.",
        "Motion is sampled and attached to each snapshot, but the mesh is not deformed.",
        "The route does not perform dynamic mesh, immersed-boundary CFD, or FSI.",
        "The output is advisory FastFluent evidence, not final Fluent validation.",
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
