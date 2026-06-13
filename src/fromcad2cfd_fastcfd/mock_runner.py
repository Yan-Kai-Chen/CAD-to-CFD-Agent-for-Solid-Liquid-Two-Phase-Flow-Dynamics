"""Deterministic FastCFD mock backend for agent workflow validation."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .lattice_trust import analyze_lattice_domain, lattice_domain_qoi_updates
from .paths import project_input_dir, project_output_dir, project_reports_dir, unique_path
from .physics_validator import contract_has_blocking_errors, validate_physics
from .pilot_decision import build_pilot_decision, pilot_decision_qoi_updates
from .schemas import (
    ClaimLedger,
    FastCFDJob,
    FlowFingerprint,
    FluentHints,
    PhysicsContract,
    QoIManifest,
    ResultManifest,
    read_job,
)


def demo_cavity2d_job(output_dir: str | Path, *, model_name: str = "fastcfd_mock_cavity2d") -> FastCFDJob:
    """Create a small deterministic cavity2d mock job."""

    return FastCFDJob(
        case_type="cavity2d",
        backend="mock",
        output_dir=str(output_dir),
        model_name=model_name,
        dimensions={"nx": 30, "ny": 30, "cell_length_mm": 1.0},
        physical_properties={"rho_ref_g_per_mm3": 0.001, "kinematic_viscosity_mm2_s": 0.02},
        boundary_conditions={"moving_wall_velocity_mm_s": 0.03, "stationary_walls": ["left", "right", "bottom"]},
        solver_settings={"total_steps": 200, "output_interval": 50, "relaxation_time": 0.56, "thread_num": 1},
        metadata={
            "advisory_scope": "deterministic mock for FastCFD agent workflow validation",
            "source_template": "cavity2d",
        },
    )


def write_demo_job(
    *,
    project: str = "fastcfd_mock_cavity2d",
    model_name: str = "fastcfd_mock_cavity2d",
    case_type: str = "cavity2d",
    backend: str = "mock",
) -> dict[str, Any]:
    """Write a public-safe FastCFD demo job without executing it."""

    if case_type != "cavity2d":
        raise ValueError("Only cavity2d demo jobs are implemented in the first FastCFD batch.")
    if backend != "mock":
        raise ValueError("write_demo_job currently creates mock jobs only.")
    job = demo_cavity2d_job(project_output_dir(project), model_name=model_name)
    job_path = unique_path(project_input_dir(project) / f"{job.model_name}_job.json")
    job.write(job_path)
    return {"status": "success", "job_path": str(job_path), "job": job.to_dict()}


def _stable_run_id(job: FastCFDJob) -> str:
    payload = json.dumps(job.to_dict(), sort_keys=True, ensure_ascii=True)
    return "mock_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _generated_ini(job: FastCFDJob) -> str:
    reference_velocity = _job_reference_velocity(job)
    return "\n".join(
        [
            "[parallel]",
            f"thread_num = {int(job.solver_settings.get('thread_num', 1))}",
            "",
            "[Mesh]",
            f"Ni = {int(job.dimensions['nx'])}",
            f"Nj = {int(job.dimensions['ny'])}",
            f"Cell_Len = {float(job.dimensions['cell_length_mm'])}",
            "BlockCellLen = 10",
            "",
            "[Physical_Property]",
            f"rho_ref = {float(job.physical_properties['rho_ref_g_per_mm3'])}",
            f"Kine_Visc = {float(job.physical_properties['kinematic_viscosity_mm2_s'])}",
            "",
            "[Init_Conditions]",
            "U_Ini0 = 0",
            "U_Ini1 = 0",
            f"U_Max = {reference_velocity}",
            "",
            "[Boundary_Conditions]",
            f"Velo_Wall0 = {reference_velocity}",
            "Velo_Wall1 = 0",
            "",
            "[LB]",
            f"RT = {float(job.solver_settings.get('relaxation_time', 0.56))}",
            "",
            "[Simulation_Settings]",
            f"TotalStep = {int(job.solver_settings['total_steps'])}",
            f"OutputStep = {int(job.solver_settings['output_interval'])}",
            "",
            "[tolerance]",
            "tol = 1e-5",
            "",
        ]
    )


def _job_reference_velocity(job: FastCFDJob) -> float:
    for key in ("moving_wall_velocity_mm_s", "inlet_velocity_mm_s", "reference_velocity_mm_s", "u_ref_mm_s"):
        if key in job.boundary_conditions:
            return float(job.boundary_conditions[key])
    return 0.0


def _physics_contract(job: FastCFDJob, *, mock_backend: bool = False) -> PhysicsContract:
    contract = validate_physics(job, profile="agent")
    limitations = list(contract.limitations)
    if mock_backend:
        limitations.extend(
            [
                "This is a deterministic mock backend, not a numerical CFD solve.",
                "QoI values are workflow fixtures for parser and reporting validation.",
                "Use real FastFluent/Fluent runs before making engineering decisions.",
            ]
        )
    return PhysicsContract(
        status=contract.status,
        case_type=contract.case_type,
        checks=contract.checks,
        limitations=limitations,
        thresholds=contract.thresholds,
        validator_version=contract.validator_version,
        remediation_suggestions=contract.remediation_suggestions,
    )


def run_mock_job(job_path: str | Path) -> dict[str, Any]:
    """Run a deterministic mock FastCFD job and write the full artifact contract."""

    job = read_job(job_path)
    if job.backend != "mock":
        raise ValueError("run_mock_job only accepts backend='mock'.")
    run_id = _stable_run_id(job)
    output_dir = Path(job.output_dir)
    logs_dir = output_dir / "logs"
    reports_dir = output_dir.parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    contract = _physics_contract(job, mock_backend=True)
    physics_path = _write_json(unique_path(output_dir / "physics_contract.json"), contract.to_dict())
    if contract_has_blocking_errors(contract):
        return _blocked_mock_result(job_path, job, contract, {"physics_contract": str(physics_path)})

    ini_path = unique_path(output_dir / "generated.ini")
    ini_path.write_text(_generated_ini(job), encoding="utf-8")
    log_path = unique_path(logs_dir / "mock_solver.log")
    log_path.write_text(
        "\n".join(
            [
                "FastCFD mock backend started.",
                f"run_id={run_id}",
                f"case_type={job.case_type}",
                "status=success",
                "FastCFD mock backend completed.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    convergence_path = unique_path(output_dir / "convergence.csv")
    with convergence_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "residual"])
        writer.writeheader()
        for step, residual in [(0, 1.0), (50, 0.1), (100, 0.0218098), (150, 0.00824974), (200, 0.00830784)]:
            writer.writerow({"step": step, "residual": residual})

    lattice_summary = analyze_lattice_domain(job)
    lattice_summary_path = _write_json(unique_path(output_dir / "lattice_domain_summary.json"), lattice_summary)
    qoi = QoIManifest(
        run_id=run_id,
        metrics={
            "final_residual": 0.00830784,
            "average_mlups": 8.90435,
            "max_velocity_mm_s": _job_reference_velocity(job),
            "total_steps": int(job.solver_settings["total_steps"]),
            **lattice_domain_qoi_updates(lattice_summary),
        },
        unavailable={"field_statistics": "Mock backend does not produce real velocity or pressure fields."},
        limitations=contract.limitations,
    )
    qoi_path = _write_json(unique_path(output_dir / "qoi.json"), qoi.to_dict())
    fingerprint = FlowFingerprint(
        run_id=run_id,
        metrics={
            "recirculation_ratio": None,
            "wake_bbox": None,
            "stagnation_ratio": None,
            "high_shear_proxy": None,
            "outlet_contamination_risk": "unknown",
        },
        unavailable={"all_field_derived_metrics": "No real field output is available from the mock backend."},
    )
    fingerprint_path = _write_json(unique_path(output_dir / "flow_fingerprint.json"), fingerprint.to_dict())
    mock_field_analysis = {
        "status": "not_available",
        "warnings": ["Mock backend does not produce real velocity or pressure fields."],
        "metrics": {},
        "fluent_hint_inputs": {},
    }
    mock_native_convergence = {
        "status": "not_available",
        "path": str(convergence_path),
        "warnings": ["Mock convergence.csv is a deterministic fixture, not native FastFluent residual history."],
        "metrics": {},
    }
    pilot_decision = build_pilot_decision(
        job=job,
        lattice_summary=lattice_summary,
        field_analysis=mock_field_analysis,
        native_convergence=mock_native_convergence,
        artifact_refs={
            "qoi": str(qoi_path),
            "field_qoi": "",
            "lattice_domain_summary": str(lattice_summary_path),
            "native_convergence": str(convergence_path),
            "stdout": str(log_path),
        },
    )
    qoi_payload = qoi.to_dict()
    qoi_payload["metrics"].update(pilot_decision_qoi_updates(pilot_decision))
    _write_json(qoi_path, qoi_payload)
    pilot_decision_path = _write_json(unique_path(output_dir / "pilot_decision.json"), pilot_decision)
    hints = FluentHints(
        run_id=run_id,
        hints=[
            {
                "category": "initialization",
                "hint": "Use the FastCFD mock only to verify workflow plumbing before real solver execution.",
                "evidence": ["qoi.json:mock_backend", "physics_contract.json:mock_limitations"],
                "confidence": "low",
            },
            {
                "category": "mesh",
                "hint": "Do not derive mesh sizing from mock-only fields.",
                "evidence": ["flow_fingerprint.json:all_field_derived_metrics unavailable"],
                "confidence": "high",
            },
            {
                "category": "handoff_decision",
                "hint": f"Follow the mock pilot decision status only for workflow plumbing: {pilot_decision.get('status')}.",
                "evidence": [str(pilot_decision_path), str(lattice_summary_path)],
                "confidence": "low",
            },
        ],
        limitations=contract.limitations,
    )
    hints_path = _write_json(unique_path(output_dir / "fluent_hints.json"), hints.to_dict())
    ledger = ClaimLedger(
        run_id=run_id,
        claims=[
            {
                "claim": "FastCFD mock workflow completed.",
                "evidence": [str(log_path), str(qoi_path)],
                "confidence": "high",
                "limitation": "This does not validate numerical CFD accuracy.",
            },
            {
                "claim": "FastCFD result is advisory only.",
                "evidence": [str(physics_path), str(hints_path)],
                "confidence": "high",
                "limitation": "Use real FastFluent or Fluent for physics decisions.",
            },
            {
                "claim": "Mock route writes lattice-domain and pilot-decision artifacts for interface testing.",
                "evidence": [str(lattice_summary_path), str(pilot_decision_path)],
                "confidence": "high",
                "limitation": "The mock decision is not numerical CFD evidence.",
            },
        ],
    )
    ledger_path = _write_json(unique_path(output_dir / "claim_ledger.json"), ledger.to_dict())

    artifacts = {
        "generated_ini": str(ini_path),
        "log": str(log_path),
        "convergence_csv": str(convergence_path),
        "physics_contract": str(physics_path),
        "lattice_domain_summary": str(lattice_summary_path),
        "qoi": str(qoi_path),
        "flow_fingerprint": str(fingerprint_path),
        "pilot_decision": str(pilot_decision_path),
        "fluent_hints": str(hints_path),
        "claim_ledger": str(ledger_path),
    }
    manifest = ResultManifest(
        run_id=run_id,
        status="success",
        backend="mock",
        case_type=job.case_type,
        job_path=str(job_path),
        artifacts=artifacts,
        parser_status="not_applicable_mock",
        warnings=["Mock backend produced no real field outputs."],
    )
    manifest_path = _write_json(unique_path(output_dir / "result_manifest.json"), manifest.to_dict())
    artifacts["result_manifest"] = str(manifest_path)

    report_payload = {
        "run_id": run_id,
        "status": "success",
        "backend": "mock",
        "case_type": job.case_type,
        "model_name": job.model_name,
        "message": "FastCFD deterministic mock run completed.",
        "artifacts": artifacts,
        "limitations": contract.limitations,
    }
    report_json = _write_json(unique_path(reports_dir / f"{job.model_name}_{run_id}_fastcfd_report.json"), report_payload)
    report_md = unique_path(reports_dir / f"{job.model_name}_{run_id}_fastcfd_report.md")
    report_md.write_text(_markdown_report(report_payload), encoding="utf-8")
    artifacts["fastcfd_report_json"] = str(report_json)
    artifacts["fastcfd_report_markdown"] = str(report_md)
    _write_json(
        Path(artifacts["result_manifest"]),
        ResultManifest(
            run_id=run_id,
            status="success",
            backend="mock",
            case_type=job.case_type,
            job_path=str(job_path),
            artifacts=artifacts,
            parser_status="not_applicable_mock",
            warnings=["Mock backend produced no real field outputs."],
        ).to_dict(),
    )

    return AgentResult.success(
        backend="fastcfd",
        operation="run_mock_job",
        message="FastCFD deterministic mock run completed.",
        outputs={"run_id": run_id, "artifacts": artifacts},
        reports={"json": str(report_json), "markdown": str(report_md)},
        metadata={"case_type": job.case_type, "advisory_only": True},
    ).to_dict()


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# FastCFD Mock Run Report",
        "",
        f"Status: `{payload['status']}`",
        f"Backend: `{payload['backend']}`",
        f"Case type: `{payload['case_type']}`",
        f"Run ID: `{payload['run_id']}`",
        "",
        "## Artifacts",
        "",
    ]
    for key, value in payload["artifacts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in payload["limitations"])
    lines.append("")
    return "\n".join(lines)


def _blocked_mock_result(job_path: str | Path, job: FastCFDJob, contract: PhysicsContract, artifacts: dict[str, str]) -> dict[str, Any]:
    output_dir = Path(job.output_dir)
    reports_dir = output_dir.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    errors = list(contract.checks.get("errors") or ["FastCFD physics validation failed."])
    payload = {
        "run_id": _stable_run_id(job),
        "status": "failed",
        "backend": "mock",
        "case_type": job.case_type,
        "model_name": job.model_name,
        "message": "FastCFD physics validation blocked execution.",
        "artifacts": artifacts,
        "errors": errors,
        "limitations": contract.limitations,
    }
    report_json = _write_json(unique_path(reports_dir / f"{job.model_name}_physics_blocked_fastcfd_report.json"), payload)
    report_md = unique_path(reports_dir / f"{job.model_name}_physics_blocked_fastcfd_report.md")
    report_md.write_text(_markdown_report(payload), encoding="utf-8")
    artifacts["fastcfd_report_json"] = str(report_json)
    artifacts["fastcfd_report_markdown"] = str(report_md)
    return AgentResult(
        status="failed",
        backend="fastcfd",
        operation="run_mock_job",
        message="FastCFD physics validation blocked execution.",
        outputs={"run_id": payload["run_id"], "artifacts": artifacts},
        reports={"json": str(report_json), "markdown": str(report_md)},
        errors=errors,
        metadata={"case_type": job.case_type, "advisory_only": True, "job_path": str(job_path)},
    ).to_dict()
