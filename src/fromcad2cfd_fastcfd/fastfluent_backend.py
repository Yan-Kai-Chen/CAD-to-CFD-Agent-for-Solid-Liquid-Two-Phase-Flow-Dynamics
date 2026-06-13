"""Controlled real FastFluent backend integration for fixed case templates."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any

from fromcad2cfd_cad import AgentResult

from .field_qoi import analyze_fastfluent_fields
from .lattice_trust import analyze_lattice_domain, lattice_domain_qoi_updates
from .mock_runner import _physics_contract
from .native_summary import native_convergence_qoi_updates, native_summary_qoi_updates, read_native_convergence, read_native_summary
from .pilot_decision import build_pilot_decision, pilot_decision_qoi_updates
from .paths import project_output_dir, unique_path
from .physics_validator import contract_has_blocking_errors
from .prediction import build_prediction_report, write_prediction_artifacts
from .preflight import detect_fastcfd_environment
from .schemas import ClaimLedger, FastCFDJob, FlowFingerprint, FluentHints, QoIManifest, ResultManifest, read_job


def write_cavity2d_job(
    *,
    project: str = "fastcfd_cavity2d_real",
    model_name: str = "fastcfd_cavity2d_real",
    nx: int = 30,
    ny: int = 30,
    total_steps: int = 200,
    output_interval: int = 50,
) -> dict[str, Any]:
    """Write a controlled real FastFluent cavity2d job."""

    from .mock_runner import demo_cavity2d_job
    from .paths import project_input_dir

    job = demo_cavity2d_job(project_output_dir(project), model_name=model_name)
    payload = job.to_dict()
    payload["backend"] = "fastfluent"
    payload["dimensions"]["nx"] = int(nx)
    payload["dimensions"]["ny"] = int(ny)
    payload["solver_settings"]["total_steps"] = int(total_steps)
    payload["solver_settings"]["output_interval"] = int(output_interval)
    payload["metadata"]["source_template"] = "FastFluent examples/cavity2d"
    payload["metadata"]["real_backend"] = True

    real_job = FastCFDJob(
        case_type=payload["case_type"],
        backend=payload["backend"],
        output_dir=payload["output_dir"],
        model_name=payload["model_name"],
        units=payload["units"],
        dimensions=payload["dimensions"],
        physical_properties=payload["physical_properties"],
        boundary_conditions=payload["boundary_conditions"],
        solver_settings=payload["solver_settings"],
        metadata=payload["metadata"],
    )
    job_path = unique_path(project_input_dir(project) / f"{real_job.model_name}_job.json")
    real_job.write(job_path)
    return {"status": "success", "job_path": str(job_path), "job": real_job.to_dict()}


def write_channel2d_job(
    *,
    project: str = "fastcfd_channel2d_real",
    model_name: str = "fastcfd_channel2d_real",
    length_mm: float = 120.0,
    height_mm: float = 40.0,
    cell_length_mm: float = 1.0,
    total_steps: int = 200,
    output_interval: int = 50,
) -> dict[str, Any]:
    """Write a controlled real FastFluent channel2d job through the scene route."""

    from .scene_compiler import compile_scene_to_job, default_scene

    scene = default_scene(
        scene_type="channel2d",
        model_name=model_name,
        length_mm=length_mm,
        height_mm=height_mm,
        cell_length_mm=cell_length_mm,
    )
    scene.physics_intent["total_steps"] = int(total_steps)
    scene.physics_intent["output_interval"] = int(output_interval)
    return compile_scene_to_job(scene, project=project, model_name=model_name, backend="fastfluent")


def write_obstacle2d_job(
    *,
    project: str = "fastcfd_obstacle2d_real",
    model_name: str = "fastcfd_obstacle2d_real",
    length_mm: float = 120.0,
    height_mm: float = 40.0,
    cell_length_mm: float = 1.0,
    obstacle: str = "circle",
    total_steps: int = 200,
    output_interval: int = 50,
) -> dict[str, Any]:
    """Write a controlled real FastFluent obstacle2d job through the scene route."""

    from .scene_compiler import compile_scene_to_job, default_scene

    scene = default_scene(
        scene_type="obstacle2d",
        model_name=model_name,
        length_mm=length_mm,
        height_mm=height_mm,
        cell_length_mm=cell_length_mm,
        obstacle=obstacle,
    )
    scene.physics_intent["total_steps"] = int(total_steps)
    scene.physics_intent["output_interval"] = int(output_interval)
    return compile_scene_to_job(scene, project=project, model_name=model_name, backend="fastfluent")


def _example_dir(source_root: Path, name: str) -> Path:
    return source_root / "examples" / name


def _build_make_example(source_root: Path, example: str, *, timeout_sec: int) -> tuple[bool, dict[str, Any]]:
    report = detect_fastcfd_environment(str(source_root))
    make_tool = report.make_tool
    example_dir = _example_dir(source_root, example)
    if report.status not in {"success", "partial"} or not make_tool:
        return False, {"status": report.status, "preflight": report.to_dict(), "message": "FastFluent build prerequisites are missing."}
    if not example_dir.is_dir():
        return False, {"status": "missing", "preflight": report.to_dict(), "message": f"FastFluent example is missing: {example}."}
    completed = subprocess.run([make_tool], cwd=example_dir, capture_output=True, text=True, timeout=timeout_sec, check=False)
    return completed.returncode == 0, {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "preflight": report.to_dict(),
        "make_tool": make_tool,
        "example": example,
    }


def _build_cavity2d(source_root: Path, *, timeout_sec: int) -> tuple[bool, dict[str, Any]]:
    return _build_make_example(source_root, "cavity2d", timeout_sec=timeout_sec)


def _build_openboundary2d(source_root: Path, *, timeout_sec: int) -> tuple[bool, dict[str, Any]]:
    return _build_make_example(source_root, "openboundary2d", timeout_sec=timeout_sec)


def _build_generated_obstacle2d(source_root: Path, output_dir: Path, job: FastCFDJob, *, timeout_sec: int) -> tuple[bool, dict[str, Any]]:
    report = detect_fastcfd_environment(str(source_root))
    compiler = report.compiler
    if report.status not in {"success", "partial"} or not compiler:
        return False, {"status": report.status, "preflight": report.to_dict(), "message": "FastFluent compile prerequisites are missing."}

    build_dir = output_dir / "generated_source" / "obstacle2d"
    build_dir.mkdir(parents=True, exist_ok=True)
    source_path = unique_path(build_dir / "obstacle2d.cpp")
    exe_path = source_path.with_suffix(".exe")
    source_path.write_text(_obstacle2d_source(), encoding="utf-8")

    command = [
        compiler,
        "-O3",
        "-march=native",
        "-fopenmp",
        "-DFLOAT_TYPE=double",
        "-std=c++17",
        "-fno-diagnostics-show-template-tree",
        "-I",
        str(source_root / "src"),
        str(source_path),
        "-o",
        str(exe_path),
        "-L",
        str(source_root / "lib"),
    ]
    completed = subprocess.run(command, cwd=build_dir, capture_output=True, text=True, timeout=timeout_sec, check=False)
    return completed.returncode == 0, {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "preflight": report.to_dict(),
        "compiler": compiler,
        "generated_source": str(source_path),
        "executable": str(exe_path),
        "command_preview": " ".join(command[:2] + ["...", str(source_path.name)]),
        "obstacle_summary": _obstacle_summary(job),
    }


def _case_executable(case_type: str, source_root: Path, build_report: dict[str, Any]) -> Path:
    if case_type == "cavity2d":
        return _example_dir(source_root, "cavity2d") / "cavity2d.exe"
    if case_type == "channel2d":
        return _example_dir(source_root, "openboundary2d") / "openbd2d.exe"
    if case_type == "obstacle2d":
        return Path(str(build_report.get("executable", "")))
    raise ValueError(f"Unsupported real FastFluent case_type: {case_type}")


def _ini_name(case_type: str) -> str:
    if case_type == "cavity2d":
        return "cavity2d.ini"
    if case_type == "channel2d":
        return "openbd2dparam.ini"
    if case_type == "obstacle2d":
        return "obstacle2dparam.ini"
    raise ValueError(f"Unsupported real FastFluent case_type: {case_type}")


def _build_case(case_type: str, source_root: Path, output_dir: Path, job: FastCFDJob, *, timeout_sec: int) -> tuple[bool, dict[str, Any]]:
    if case_type == "cavity2d":
        return _build_cavity2d(source_root, timeout_sec=timeout_sec)
    if case_type == "channel2d":
        return _build_openboundary2d(source_root, timeout_sec=timeout_sec)
    if case_type == "obstacle2d":
        return _build_generated_obstacle2d(source_root, output_dir, job, timeout_sec=timeout_sec)
    raise ValueError(f"Unsupported real FastFluent case_type: {case_type}")


def _parse_run_qoi(stdout: str, total_steps: int) -> dict[str, Any]:
    residuals = re.findall(r"Res:\s*([0-9.eE+-]+)", stdout)
    mlups = re.findall(r"Average_MLUPs:\s*([0-9.eE+-]+)", stdout)
    elapsed = re.findall(r"Time Elapsed:\s*([0-9.eE+-]+)", stdout)
    completed_steps = re.findall(r"Total Step:\s*([0-9]+)", stdout)
    return {
        "final_residual": float(residuals[-1]) if residuals else None,
        "average_mlups": float(mlups[-1]) if mlups else None,
        "elapsed_seconds": float(elapsed[-1]) if elapsed else None,
        "completed_steps": int(completed_steps[-1]) if completed_steps else None,
        "requested_total_steps": total_steps,
    }


def _index_vtk_outputs(output_dir: Path) -> list[dict[str, Any]]:
    vtk_root = output_dir / "vtkoutput"
    files = sorted(vtk_root.rglob("*.vt*")) if vtk_root.exists() else []
    indexed: list[dict[str, Any]] = []
    for file in files:
        indexed.append({"path": str(file), "name": file.name, "bytes": file.stat().st_size})
    return indexed


def run_fastfluent_job(
    job_path: str | Path,
    *,
    source_root: str | Path,
    build_timeout_sec: int = 240,
    run_timeout_sec: int = 240,
) -> dict[str, Any]:
    """Build and run a registry-approved real FastFluent job."""

    job = read_job(job_path)
    if job.backend != "fastfluent":
        raise ValueError("run_fastfluent_job requires backend='fastfluent'.")
    if job.case_type not in {"cavity2d", "channel2d", "obstacle2d"}:
        raise ValueError(f"No controlled real FastFluent backend is implemented for case_type='{job.case_type}'.")

    source = Path(source_root)
    output_dir = Path(job.output_dir)
    logs_dir = output_dir / "logs"
    reports_dir = output_dir.parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    contract = _physics_contract(job)
    physics_path = _write_json(unique_path(output_dir / "physics_contract.json"), contract.to_dict())
    if contract_has_blocking_errors(contract):
        return _blocked_result(
            job_path,
            job,
            {"physics_contract": contract.to_dict()},
            {"physics_contract": str(physics_path)},
            "FastFluent physics validation blocked execution.",
        )

    build_ok, build_report = _build_case(job.case_type, source, output_dir, job, timeout_sec=build_timeout_sec)
    build_log = unique_path(logs_dir / f"fastfluent_{job.case_type}_build.json")
    build_log.write_text(json.dumps(build_report, ensure_ascii=True, indent=2), encoding="utf-8")
    artifacts = {"physics_contract": str(physics_path), "build_log": str(build_log)}
    if build_report.get("generated_source"):
        artifacts["generated_source"] = str(build_report["generated_source"])
    if not build_ok:
        return _blocked_result(job_path, job, build_report, artifacts, f"FastFluent {job.case_type} build failed.")

    exe = _case_executable(job.case_type, source, build_report)
    if not exe.exists():
        return _blocked_result(job_path, job, build_report, artifacts, f"FastFluent {job.case_type} executable was not produced.")

    ini_path = unique_path(output_dir / _ini_name(job.case_type))
    ini_path.write_text(_generated_ini(job), encoding="utf-8")
    artifacts["generated_ini"] = str(ini_path)

    completed = subprocess.run([str(exe)], cwd=output_dir, capture_output=True, text=True, timeout=run_timeout_sec, check=False)
    stdout_path = unique_path(logs_dir / f"fastfluent_{job.case_type}_stdout.log")
    stderr_path = unique_path(logs_dir / f"fastfluent_{job.case_type}_stderr.log")
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    artifacts["stdout"] = str(stdout_path)
    artifacts["stderr"] = str(stderr_path)
    if completed.returncode != 0:
        return _blocked_result(
            job_path,
            job,
            {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr},
            artifacts,
            f"FastFluent {job.case_type} run failed.",
        )

    return _successful_result(job_path, job, completed.stdout, artifacts, build_report)


def run_fastfluent_cavity2d_job(
    job_path: str | Path,
    *,
    source_root: str | Path,
    build_timeout_sec: int = 240,
    run_timeout_sec: int = 240,
) -> dict[str, Any]:
    """Backward-compatible wrapper for the controlled cavity2d backend."""

    job = read_job(job_path)
    if job.case_type != "cavity2d" or job.backend != "fastfluent":
        raise ValueError("run_fastfluent_cavity2d_job requires case_type='cavity2d' and backend='fastfluent'.")
    return run_fastfluent_job(
        job_path,
        source_root=source_root,
        build_timeout_sec=build_timeout_sec,
        run_timeout_sec=run_timeout_sec,
    )


def _successful_result(
    job_path: str | Path,
    job: FastCFDJob,
    stdout: str,
    artifacts: dict[str, str],
    build_report: dict[str, Any],
) -> dict[str, Any]:
    output_dir = Path(job.output_dir)
    reports_dir = output_dir.parent / "reports"
    run_id = f"fastfluent_{job.case_type}"
    native_summary = read_native_summary(output_dir)
    native_summary_status = str(native_summary.get("status", "unknown"))
    native_summary_path = native_summary.get("path")
    if native_summary_status in {"parsed", "partial"} and native_summary_path:
        artifacts["native_summary"] = str(native_summary_path)
    native_convergence = read_native_convergence(output_dir)
    native_convergence_status = str(native_convergence.get("status", "unknown"))
    native_convergence_path = native_convergence.get("path")
    if native_convergence_status in {"parsed", "partial"} and native_convergence_path:
        artifacts["native_convergence"] = str(native_convergence_path)
    field_outputs = _index_vtk_outputs(output_dir)
    field_analysis = analyze_fastfluent_fields(output_dir, job)
    field_parser_status = str(field_analysis.get("status", "unknown"))
    field_warnings = list(field_analysis.get("warnings") or [])
    field_qoi_path = _write_json(unique_path(output_dir / "field_qoi.json"), field_analysis)
    artifacts["field_qoi"] = str(field_qoi_path)
    lattice_summary = analyze_lattice_domain(job)
    lattice_summary_path = _write_json(unique_path(output_dir / "lattice_domain_summary.json"), lattice_summary)
    artifacts["lattice_domain_summary"] = str(lattice_summary_path)

    fingerprint = FlowFingerprint(
        run_id=run_id,
        metrics=_flow_fingerprint_metrics(field_analysis),
        unavailable=_flow_fingerprint_unavailable(field_analysis),
    )
    fingerprint_path = _write_json(unique_path(output_dir / "flow_fingerprint.json"), fingerprint.to_dict())
    artifacts["flow_fingerprint"] = str(fingerprint_path)

    qoi_metrics = _parse_run_qoi(stdout, int(job.solver_settings["total_steps"]))
    qoi_metrics.update(
        {
            "nx": int(job.dimensions["nx"]),
            "ny": int(job.dimensions["ny"]),
            "cell_length_mm": float(job.dimensions["cell_length_mm"]),
            "reference_velocity_mm_s": _job_reference_velocity(job),
            "obstacle": _obstacle_summary(job) if job.case_type == "obstacle2d" else None,
        }
    )
    qoi_metrics.update(native_summary_qoi_updates(native_summary))
    qoi_metrics.update(native_convergence_qoi_updates(native_convergence))
    qoi_metrics.update(_field_qoi_metric_updates(field_analysis))
    qoi_metrics.update(lattice_domain_qoi_updates(lattice_summary))
    qoi = QoIManifest(
        run_id=run_id,
        metrics=qoi_metrics,
        unavailable=_qoi_unavailable(field_analysis, native_summary, native_convergence),
        limitations=[
            "FastCFD/FastFluent is an advisory pilot solver and does not replace Fluent validation.",
            "The lattice-domain summary is recipe-derived and must be checked against the final Fluent mesh.",
        ],
    )
    qoi_path = _write_json(unique_path(output_dir / "qoi.json"), qoi.to_dict())
    artifacts["qoi"] = str(qoi_path)

    pilot_decision = build_pilot_decision(
        job=job,
        lattice_summary=lattice_summary,
        field_analysis=field_analysis,
        native_convergence=native_convergence,
        artifact_refs={
            "qoi": str(qoi_path),
            "field_qoi": str(field_qoi_path),
            "lattice_domain_summary": str(lattice_summary_path),
            "native_convergence": str(native_convergence_path) if native_convergence_path else "",
            "stdout": artifacts.get("stdout", ""),
        },
    )
    qoi_metrics.update(pilot_decision_qoi_updates(pilot_decision))
    _write_json(qoi_path, qoi.to_dict() | {"metrics": qoi_metrics})
    pilot_decision_path = _write_json(unique_path(output_dir / "pilot_decision.json"), pilot_decision)
    artifacts["pilot_decision"] = str(pilot_decision_path)

    hints = FluentHints(
        run_id=run_id,
        hints=_fluent_hints(
            job,
            qoi_path,
            artifacts.get("stdout"),
            field_outputs,
            field_qoi_path,
            field_analysis,
            native_convergence,
            lattice_summary,
            lattice_summary_path,
            pilot_decision,
            pilot_decision_path,
        ),
        limitations=["Hints are advisory and must be reviewed before Fluent setup."],
    )
    hints_path = _write_json(unique_path(output_dir / "fluent_hints.json"), hints.to_dict())
    artifacts["fluent_hints"] = str(hints_path)

    ledger = ClaimLedger(
        run_id=run_id,
        claims=_claim_ledger(
            job,
            artifacts,
            qoi_path,
            field_qoi_path,
            field_analysis,
            native_summary,
            native_convergence,
            lattice_summary,
            lattice_summary_path,
            pilot_decision,
            pilot_decision_path,
        ),
    )
    ledger_path = _write_json(unique_path(output_dir / "claim_ledger.json"), ledger.to_dict())
    artifacts["claim_ledger"] = str(ledger_path)

    prediction_report = build_prediction_report(
        job=job,
        physics_contract=artifacts.get("physics_contract") and json.loads(Path(artifacts["physics_contract"]).read_text(encoding="utf-8")) or {},
        qoi=qoi.to_dict(),
        field_analysis=field_analysis,
        lattice_summary=lattice_summary,
        native_summary=native_summary,
        native_convergence=native_convergence,
        pilot_decision=pilot_decision,
        artifact_refs=artifacts,
    )
    artifacts.update(
        write_prediction_artifacts(
            report=prediction_report,
            output_dir=output_dir,
            reports_dir=reports_dir,
            model_name=job.model_name,
            unique_path=unique_path,
        )
    )

    if build_report.get("obstacle_summary"):
        obstacle_summary_path = _write_json(unique_path(output_dir / "obstacle_summary.json"), build_report["obstacle_summary"])
        artifacts["obstacle_summary"] = str(obstacle_summary_path)

    manifest = ResultManifest(
        run_id=run_id,
        status="success",
        backend="fastfluent",
        case_type=job.case_type,
        job_path=str(job_path),
        artifacts=artifacts,
        field_outputs=field_outputs,
        parser_status=field_parser_status,
        warnings=_result_warnings(field_warnings, native_summary, native_convergence, lattice_summary),
    )
    manifest_path = _write_json(unique_path(output_dir / "result_manifest.json"), manifest.to_dict())
    artifacts["result_manifest"] = str(manifest_path)

    report_payload = {
        "status": "success",
        "backend": "fastfluent",
        "case_type": job.case_type,
        "message": f"Controlled FastFluent {job.case_type} run completed.",
        "artifacts": artifacts,
        "field_output_count": len(field_outputs),
        "pilot_decision_status": pilot_decision.get("status"),
        "advisory_only": True,
    }
    report_json = _write_json(unique_path(reports_dir / f"{job.model_name}_fastfluent_report.json"), report_payload)
    report_md = unique_path(reports_dir / f"{job.model_name}_fastfluent_report.md")
    report_md.write_text(_markdown_report(report_payload), encoding="utf-8")
    artifacts["fastcfd_report_json"] = str(report_json)
    artifacts["fastcfd_report_markdown"] = str(report_md)
    _write_json(
        Path(artifacts["result_manifest"]),
        ResultManifest(
            run_id=run_id,
            status="success",
            backend="fastfluent",
            case_type=job.case_type,
            job_path=str(job_path),
            artifacts=artifacts,
            field_outputs=field_outputs,
            parser_status=field_parser_status,
            warnings=_result_warnings(field_warnings, native_summary, native_convergence, lattice_summary),
        ).to_dict(),
    )
    return AgentResult.success(
        backend="fastcfd",
        operation="run_fastfluent_job",
        message=f"Controlled FastFluent {job.case_type} run completed.",
        outputs={"artifacts": artifacts, "field_output_count": len(field_outputs)},
        reports={"json": str(report_json), "markdown": str(report_md)},
        metadata={"case_type": job.case_type, "advisory_only": True},
    ).to_dict()


def _generated_ini(job: FastCFDJob) -> str:
    reference_velocity = _job_reference_velocity(job)
    lines = [
        "[workdir]",
        "workdir_ = ./output",
        "",
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
    ]
    if job.case_type == "obstacle2d":
        lines.extend(_obstacle_ini_lines(job))
        lines.append("")
    lines.extend(
        [
            "[LB]",
            f"RT = {float(job.solver_settings.get('relaxation_time', 0.56))}",
            "",
            "[Simulation_Settings]",
            f"TotalStep = {int(job.solver_settings['total_steps'])}",
            f"OutputStep = {int(job.solver_settings['output_interval'])}",
            "",
            "[tolerance]",
            f"tol = {float(job.solver_settings.get('tolerance', 1e-5))}",
            "",
        ]
    )
    return "\n".join(lines)


def _job_reference_velocity(job: FastCFDJob) -> float:
    for key in ("moving_wall_velocity_mm_s", "inlet_velocity_mm_s", "reference_velocity_mm_s", "u_ref_mm_s"):
        if key in job.boundary_conditions:
            return float(job.boundary_conditions[key])
    return 0.0


def _obstacle(job: FastCFDJob) -> dict[str, Any]:
    obstacles = job.dimensions.get("obstacles") or []
    if not obstacles:
        raise ValueError("obstacle2d real backend requires dimensions.obstacles with one circle or rectangle obstacle.")
    return dict(obstacles[0])


def _obstacle_summary(job: FastCFDJob) -> dict[str, Any]:
    if job.case_type != "obstacle2d":
        return {}
    obstacle = _obstacle(job)
    summary = {
        "name": obstacle.get("name", "obstacle_01"),
        "type": obstacle.get("type"),
        "center_mm": obstacle.get("center_mm"),
    }
    for key in ("radius_mm", "width_mm", "height_mm"):
        if key in obstacle:
            summary[key] = obstacle[key]
    return summary


def _field_metrics(field_analysis: dict[str, Any]) -> dict[str, Any]:
    metrics = field_analysis.get("metrics") or {}
    return metrics if isinstance(metrics, dict) else {}


def _field_hint_inputs(field_analysis: dict[str, Any]) -> dict[str, Any]:
    inputs = field_analysis.get("fluent_hint_inputs") or {}
    return inputs if isinstance(inputs, dict) else {}


def _field_qoi_metric_updates(field_analysis: dict[str, Any]) -> dict[str, Any]:
    metrics = _field_metrics(field_analysis)
    hint_inputs = _field_hint_inputs(field_analysis)
    speed = metrics.get("speed_summary") or {}
    wake = metrics.get("wake_bbox_proxy") or {}
    outlet = metrics.get("outlet_velocity_spread") or {}
    return {
        "field_parser_status": field_analysis.get("status", "unknown"),
        "field_selected_step": field_analysis.get("selected_step"),
        "field_speed_mean": speed.get("mean"),
        "field_speed_max": speed.get("max"),
        "outlet_spread_ratio": hint_inputs.get("outlet_spread_ratio"),
        "outlet_reverse_flow_fraction": hint_inputs.get("outlet_reverse_flow_fraction"),
        "wake_status": wake.get("status"),
        "wake_bbox_mm": wake.get("bbox_mm"),
        "wake_length_mm": wake.get("length_mm"),
        "outlet_sample_count": outlet.get("sample_count"),
    }


def _qoi_unavailable(
    field_analysis: dict[str, Any],
    native_summary: dict[str, Any],
    native_convergence: dict[str, Any],
) -> dict[str, str]:
    unavailable: dict[str, str] = {}
    if native_summary.get("status") not in {"parsed", "partial"}:
        warnings = "; ".join(str(item) for item in (native_summary.get("warnings") or []) if item)
        unavailable["native_summary"] = warnings or "Native FastFluent summary was not emitted by this executable."
    if native_convergence.get("status") not in {"parsed", "partial"}:
        warnings = "; ".join(str(item) for item in (native_convergence.get("warnings") or []) if item)
        unavailable["native_convergence"] = warnings or "Native FastFluent convergence CSV was not emitted by this executable."
    if field_analysis.get("status") == "parsed":
        return unavailable
    warnings = "; ".join(str(item) for item in (field_analysis.get("warnings") or []) if item)
    unavailable["field_statistics"] = warnings or "No parseable FastFluent field VTI file was available."
    return unavailable


def _result_warnings(
    field_warnings: list[str],
    native_summary: dict[str, Any],
    native_convergence: dict[str, Any],
    lattice_summary: dict[str, Any],
) -> list[str]:
    warnings = list(field_warnings)
    warnings.extend(str(item) for item in (native_summary.get("warnings") or []) if item)
    warnings.extend(str(item) for item in (native_convergence.get("warnings") or []) if item)
    warnings.extend(str(item) for item in (lattice_summary.get("warnings") or []) if item)
    warnings.extend(str(item) for item in (lattice_summary.get("errors") or []) if item)
    return warnings


def _flow_fingerprint_metrics(field_analysis: dict[str, Any]) -> dict[str, Any]:
    metrics = _field_metrics(field_analysis)
    result: dict[str, Any] = {
        "field_parser_status": field_analysis.get("status", "unknown"),
        "selected_step": field_analysis.get("selected_step"),
    }
    if field_analysis.get("status") != "parsed":
        return result
    for key in (
        "grid",
        "flag_counts",
        "speed_summary",
        "rho_summary",
        "centerline_velocity_samples",
        "inlet_velocity_profile",
        "outlet_velocity_spread",
        "wake_bbox_proxy",
        "refinement_hints",
    ):
        result[key] = metrics.get(key)
    return result


def _flow_fingerprint_unavailable(field_analysis: dict[str, Any]) -> dict[str, str]:
    if field_analysis.get("status") == "parsed":
        return {}
    warnings = "; ".join(str(item) for item in (field_analysis.get("warnings") or []) if item)
    return {"flow_fingerprint": warnings or "Field-derived flow fingerprint could not be extracted."}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _obstacle_ini_lines(job: FastCFDJob) -> list[str]:
    obstacle = _obstacle(job)
    center = obstacle.get("center_mm") or [0.0, 0.0]
    obstacle_type = str(obstacle.get("type"))
    if obstacle_type == "circle":
        radius = float(obstacle.get("radius_mm", 0.0))
        if radius <= 0:
            raise ValueError("Circle obstacle requires positive radius_mm.")
        width = height = 0.0
    elif obstacle_type == "rectangle":
        width = float(obstacle.get("width_mm", 0.0))
        height = float(obstacle.get("height_mm", 0.0))
        if width <= 0 or height <= 0:
            raise ValueError("Rectangle obstacle requires positive width_mm and height_mm.")
        radius = 0.0
    else:
        raise ValueError(f"Unsupported obstacle type for real backend: {obstacle_type}")
    return [
        "[Obstacle]",
        f"Type = {obstacle_type}",
        f"CenterX = {float(center[0])}",
        f"CenterY = {float(center[1])}",
        f"Radius = {radius}",
        f"Width = {width}",
        f"Height = {height}",
    ]


def _fluent_hints(
    job: FastCFDJob,
    qoi_path: Path,
    stdout_path: str | None,
    field_outputs: list[dict[str, Any]],
    field_qoi_path: Path,
    field_analysis: dict[str, Any],
    native_convergence: dict[str, Any],
    lattice_summary: dict[str, Any],
    lattice_summary_path: Path,
    pilot_decision: dict[str, Any],
    pilot_decision_path: Path,
) -> list[dict[str, Any]]:
    field_parsed = field_analysis.get("status") == "parsed"
    hint_inputs = _field_hint_inputs(field_analysis)
    evidence = [str(qoi_path), str(field_qoi_path)]
    if stdout_path:
        evidence.append(stdout_path)
    hints = [
        {
            "category": "initialization",
            "hint": "Use the pilot run only as candidate evidence for reference velocity, Reynolds scale, and early initialization review.",
            "evidence": evidence,
            "confidence": "high" if field_parsed else ("medium" if field_outputs else "low"),
        }
    ]
    if field_parsed:
        hints.append(
            {
                "category": "initialization",
                "hint": "Use centerline velocity samples as a candidate initialization and convergence sanity-check trace before Fluent setup.",
                "evidence": [str(field_qoi_path), "field_qoi.metrics.centerline_velocity_samples"],
                "confidence": "medium",
            }
        )
    convergence_metrics = native_convergence.get("metrics") if isinstance(native_convergence.get("metrics"), dict) else {}
    reduction_ratio = _safe_float((convergence_metrics or {}).get("reduction_ratio"))
    if native_convergence.get("status") in {"parsed", "partial"}:
        if reduction_ratio is not None and reduction_ratio > 1.0:
            hints.append(
                {
                    "category": "solver_controls",
                    "hint": "The native residual history increased during the short pilot run; treat pilot-derived initialization and mesh hints as low-confidence until a longer or better-conditioned run is checked.",
                    "evidence": [str(native_convergence.get("path")), "native_convergence.reduction_ratio"],
                    "confidence": "medium",
                }
            )
        else:
            hints.append(
                {
                    "category": "solver_controls",
                    "hint": "Use the native residual history as a quick pilot convergence trace before carrying setup assumptions into Fluent.",
                    "evidence": [str(native_convergence.get("path")), "native_convergence.reduction_ratio"],
                    "confidence": "medium",
                }
            )
    lattice_status = lattice_summary.get("status")
    lattice_score = _safe_float(lattice_summary.get("trust_score"))
    if lattice_status == "failed":
        hints.append(
            {
                "category": "geometry",
                "hint": "Revise the recipe lattice domain before using pilot-derived Fluent setup hints because the lattice summary contains blocking errors.",
                "evidence": [str(lattice_summary_path), "lattice_domain_summary.errors"],
                "confidence": "high",
            }
        )
    elif lattice_status == "warning" or (lattice_score is not None and lattice_score < 0.85):
        hints.append(
            {
                "category": "geometry",
                "hint": "Review lattice resolution, obstacle clearance, and zone counts before mapping this pilot setup to Fluent.",
                "evidence": [str(lattice_summary_path), "lattice_domain_summary.trust_score"],
                "confidence": "medium",
            }
        )
    else:
        hints.append(
            {
                "category": "geometry",
                "hint": "Use the recipe-derived lattice domain summary as a bounded pre-Fluent check of grid size and semantic zones.",
                "evidence": [str(lattice_summary_path), "lattice_domain_summary.zone_counts"],
                "confidence": "medium",
            }
        )
    hints.append(
        {
            "category": "handoff_decision",
            "hint": f"Follow the bounded pilot decision status before carrying assumptions into Fluent: {pilot_decision.get('status', 'unknown')}.",
            "evidence": [str(pilot_decision_path), "pilot_decision.recommended_actions"],
            "confidence": str(pilot_decision.get("confidence", "low")),
        }
    )
    if job.case_type in {"channel2d", "obstacle2d"}:
        hints.append(
            {
                "category": "boundary_conditions",
                "hint": "Map the semantic inlet, outlet, and no-slip walls to Fluent named selections after CAD/mesh handoff.",
                "evidence": ["job.boundary_conditions", str(qoi_path)],
                "confidence": "medium",
            }
        )
        outlet_spread = _safe_float(hint_inputs.get("outlet_spread_ratio"))
        reverse_fraction = _safe_float(hint_inputs.get("outlet_reverse_flow_fraction"))
        if (outlet_spread is not None and outlet_spread > 0.25) or (reverse_fraction is not None and reverse_fraction > 0.0):
            hints.append(
                {
                    "category": "domain_extent",
                    "hint": "Review outlet placement and downstream length in Fluent because the pilot field shows elevated outlet spread or reverse-flow fraction.",
                    "evidence": [str(field_qoi_path), "field_qoi.fluent_hint_inputs.outlet_spread_ratio"],
                    "confidence": "medium",
                }
            )
    if job.case_type == "obstacle2d":
        hints.append(
            {
                "category": "mesh",
                "hint": "Review obstacle wake and near-wall refinement in Fluent; current FastCFD route uses a recipe obstacle, not imported CAD geometry.",
                "evidence": ["obstacle_summary.json", str(qoi_path), str(field_qoi_path)],
                "confidence": "medium",
            }
        )
        if hint_inputs.get("wake_status") == "detected":
            hints.append(
                {
                    "category": "mesh",
                    "hint": "Use the detected wake bounding box as a candidate local sizing region for Fluent mesh controls.",
                    "evidence": [str(field_qoi_path), "field_qoi.metrics.wake_bbox_proxy.bbox_mm"],
                    "confidence": "medium",
                }
            )
    focus_items = hint_inputs.get("refinement_focus") or []
    if field_parsed and focus_items:
        hints.append(
            {
                "category": "mesh",
                "hint": "Carry parsed field-gradient focus items into the Fluent meshing checklist as advisory refinement evidence.",
                "evidence": [str(field_qoi_path), "field_qoi.metrics.refinement_hints"],
                "confidence": "medium",
                "items": focus_items,
            }
        )
    return hints


def _claim_ledger(
    job: FastCFDJob,
    artifacts: dict[str, str],
    qoi_path: Path,
    field_qoi_path: Path,
    field_analysis: dict[str, Any],
    native_summary: dict[str, Any],
    native_convergence: dict[str, Any],
    lattice_summary: dict[str, Any],
    lattice_summary_path: Path,
    pilot_decision: dict[str, Any],
    pilot_decision_path: Path,
) -> list[dict[str, Any]]:
    claims = [
        {
            "claim": f"Controlled FastFluent {job.case_type} run completed.",
            "evidence": [artifacts.get("stdout", ""), str(qoi_path)],
            "confidence": "high",
            "limitation": "This validates the controlled backend path, not production CFD accuracy.",
        },
        {
            "claim": "FastCFD result is advisory pilot evidence.",
            "evidence": [artifacts.get("physics_contract", ""), artifacts.get("fluent_hints", "")],
            "confidence": "high",
            "limitation": "Use Fluent for final validated simulation decisions.",
        },
    ]
    if field_analysis.get("status") == "parsed":
        claims.append(
            {
                "claim": "FastFluent VTK XML fields were parsed into agent-readable field QoI.",
                "evidence": [str(field_qoi_path), artifacts.get("flow_fingerprint", "")],
                "confidence": "medium",
                "limitation": "The extracted values are pilot-field proxies and must not be treated as final CFD validation.",
            }
        )
    if native_summary.get("status") in {"parsed", "partial"}:
        claims.append(
            {
                "claim": "FastFluent executable emitted a native run summary contract.",
                "evidence": [artifacts.get("native_summary", ""), str(qoi_path)],
                "confidence": "medium",
                "limitation": "The native summary records run facts only; field statistics still come from VTK parsing.",
            }
        )
    if native_convergence.get("status") in {"parsed", "partial"}:
        claims.append(
            {
                "claim": "FastFluent executable emitted native residual convergence history.",
                "evidence": [artifacts.get("native_convergence", ""), str(qoi_path)],
                "confidence": "medium",
                "limitation": "The convergence CSV records residual history only; physical interpretation still requires review.",
            }
        )
    claims.append(
        {
            "claim": "Recipe geometry was summarized into a bounded lattice-domain trust report.",
            "evidence": [str(lattice_summary_path), artifacts.get("qoi", "")],
            "confidence": "medium" if lattice_summary.get("status") != "failed" else "low",
            "limitation": "The lattice report is a recipe-derived pilot check, not a Fluent mesh-quality report.",
        }
    )
    claims.append(
        {
            "claim": "A bounded pilot decision policy ranked the next Fluent handoff action.",
            "evidence": [str(pilot_decision_path), artifacts.get("fluent_hints", "")],
            "confidence": str(pilot_decision.get("confidence", "low")),
            "limitation": "The decision ranks workflow actions and does not certify final CFD accuracy.",
        }
    )
    return claims


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _blocked_result(job_path: str | Path, job: Any, details: dict[str, Any], artifacts: dict[str, str], message: str) -> dict[str, Any]:
    output_dir = Path(job.output_dir)
    reports_dir = output_dir.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = {"status": "partial", "message": message, "details": details, "artifacts": artifacts}
    report_json = _write_json(unique_path(reports_dir / f"{job.model_name}_fastfluent_blocked.json"), payload)
    report_md = unique_path(reports_dir / f"{job.model_name}_fastfluent_blocked.md")
    report_md.write_text(_markdown_report(payload), encoding="utf-8")
    return AgentResult(
        status="partial",
        backend="fastcfd",
        operation="run_fastfluent_job",
        message=message,
        outputs={"artifacts": artifacts},
        reports={"json": str(report_json), "markdown": str(report_md)},
        errors=[message],
        metadata={"job_path": str(job_path), "case_type": job.case_type},
    ).to_dict()


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = ["# FastCFD FastFluent Report", "", f"Status: `{payload.get('status')}`", f"Message: {payload.get('message', '')}", "", "## Artifacts", ""]
    for key, value in (payload.get("artifacts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Boundary", "", "- FastCFD/FastFluent output is advisory pilot evidence, not a final Fluent-grade result.", ""])
    return "\n".join(lines)


def _obstacle2d_source() -> str:
    return r'''#include "freelb.h"
#include "freelb.hh"

#include <fstream>

using T = FLOAT;
using LatSet = D2Q9<T>;

void WriteFastFluentNativeSummary(
    const std::string& case_type,
    int completed_steps,
    int requested_total_steps,
    int output_interval,
    T final_residual,
    int ni,
    int nj,
    T cell_len,
    T rho_ref_value,
    T kinematic_viscosity,
    T reference_velocity,
    T physical_time,
    const std::string& field_prefix,
    std::size_t obstacle_cells) {
  std::ofstream out("fastfluent_native_summary.json");
  if (!out) return;
  out << "{\n"
      << "  \"schema_version\": \"fromcad2cfd_fastfluent_native_summary_v1\",\n"
      << "  \"case_type\": \"" << case_type << "\",\n"
      << "  \"executable_role\": \"generated_obstacle2d\",\n"
      << "  \"completed_steps\": " << completed_steps << ",\n"
      << "  \"requested_total_steps\": " << requested_total_steps << ",\n"
      << "  \"output_interval\": " << output_interval << ",\n"
      << "  \"final_residual\": " << final_residual << ",\n"
      << "  \"physical_time_s\": " << physical_time << ",\n"
      << "  \"field_prefix\": \"" << field_prefix << "\",\n"
      << "  \"grid\": {\"nx\": " << ni << ", \"ny\": " << nj
      << ", \"cell_length_mm\": " << cell_len << "},\n"
      << "  \"physical_properties\": {\"rho_ref_g_per_mm3\": " << rho_ref_value
      << ", \"kinematic_viscosity_mm2_s\": " << kinematic_viscosity << "},\n"
      << "  \"boundary_conditions\": {\"reference_velocity_mm_s\": " << reference_velocity << "},\n"
      << "  \"obstacle_cells\": " << obstacle_cells << "\n"
      << "}\n";
}

void InitFastFluentNativeConvergence() {
  std::ofstream out("fastfluent_native_convergence.csv");
  if (!out) return;
  out << "step,residual\n";
}

void AppendFastFluentNativeConvergence(int step, T residual) {
  std::ofstream out("fastfluent_native_convergence.csv", std::ios::app);
  if (!out) return;
  out << step << "," << residual << "\n";
}

int Ni;
int Nj;
T Cell_Len;
T RT;
int Thread_Num;
T rho_ref;
T Kine_Visc;
Vector<T, LatSet::d> U_Ini;
T U_Max;
Vector<T, LatSet::d> U_Wall;
std::string ObstacleType;
T ObstacleCenterX;
T ObstacleCenterY;
T ObstacleRadius;
T ObstacleWidth;
T ObstacleHeight;
int MaxStep;
int OutputStep;
T tol;
std::string work_dir;

void readParam() {
  iniReader param_reader("obstacle2dparam.ini");
  work_dir = param_reader.getValue<std::string>("workdir", "workdir_");
  Thread_Num = param_reader.getValue<int>("parallel", "thread_num");
  Ni = param_reader.getValue<int>("Mesh", "Ni");
  Nj = param_reader.getValue<int>("Mesh", "Nj");
  Cell_Len = param_reader.getValue<T>("Mesh", "Cell_Len");
  rho_ref = param_reader.getValue<T>("Physical_Property", "rho_ref");
  Kine_Visc = param_reader.getValue<T>("Physical_Property", "Kine_Visc");
  U_Ini[0] = param_reader.getValue<T>("Init_Conditions", "U_Ini0");
  U_Ini[1] = param_reader.getValue<T>("Init_Conditions", "U_Ini1");
  U_Max = param_reader.getValue<T>("Init_Conditions", "U_Max");
  U_Wall[0] = param_reader.getValue<T>("Boundary_Conditions", "Velo_Wall0");
  U_Wall[1] = param_reader.getValue<T>("Boundary_Conditions", "Velo_Wall1");
  ObstacleType = param_reader.getValue<std::string>("Obstacle", "Type");
  ObstacleCenterX = param_reader.getValue<T>("Obstacle", "CenterX");
  ObstacleCenterY = param_reader.getValue<T>("Obstacle", "CenterY");
  ObstacleRadius = param_reader.getValue<T>("Obstacle", "Radius");
  ObstacleWidth = param_reader.getValue<T>("Obstacle", "Width");
  ObstacleHeight = param_reader.getValue<T>("Obstacle", "Height");
  RT = param_reader.getValue<T>("LB", "RT");
  MaxStep = param_reader.getValue<int>("Simulation_Settings", "TotalStep");
  OutputStep = param_reader.getValue<int>("Simulation_Settings", "OutputStep");
  tol = param_reader.getValue<T>("tolerance", "tol");

  std::cout << "------------Simulation Parameters:-------------\n" << std::endl;
  std::cout << "[Simulation_Settings]:"
            << "TotalStep:         " << MaxStep << "\n"
            << "OutputStep:        " << OutputStep << "\n"
            << "Tolerance:         " << tol << "\n"
            << "ObstacleType:      " << ObstacleType << "\n"
#ifdef _OPENMP
            << "Running on " << Thread_Num << " threads\n"
#endif
            << "----------------------------------------------" << std::endl;
}

int main() {
  constexpr std::uint8_t VoidFlag = std::uint8_t(1);
  constexpr std::uint8_t AABBFlag = std::uint8_t(2);
  constexpr std::uint8_t BouncebackFlag = std::uint8_t(4);
  constexpr std::uint8_t InletFlag = std::uint8_t(8);
  constexpr std::uint8_t OutletFlag = std::uint8_t(16);

  Printer::Print_BigBanner(std::string("Initializing..."));
  readParam();

  BaseConverter<T> BaseConv(LatSet::cs2);
  BaseConv.ConvertFromRT(Cell_Len, RT, rho_ref, Ni * Cell_Len, U_Max, Kine_Visc);
  UnitConvManager<T> ConvManager(&BaseConv);
  ConvManager.Check_and_Print();

  AABB<T, LatSet::d> cavity(Vector<T, LatSet::d>{},
                            Vector<T, LatSet::d>(T(Ni * Cell_Len), T(Nj * Cell_Len)));
  AABB<T, LatSet::d> left(Vector<T, LatSet::d>{},
                          Vector<T, LatSet::d>(T(1), T(Nj - 1) * Cell_Len));
  AABB<T, LatSet::d> right(Vector<T, LatSet::d>(T(Ni - 1) * Cell_Len, T(1)),
                           Vector<T, LatSet::d>(T(Ni * Cell_Len), T(Nj - 1) * Cell_Len));
  BlockGeometry2D<T> Geo(Ni, Nj, Thread_Num, cavity, Cell_Len);

  BlockFieldManager<FLAG, T, LatSet::d> FlagFM(Geo, VoidFlag);
  FlagFM.forEach(cavity, [&](FLAG& field, std::size_t id) { field.SetField(id, AABBFlag); });
  FlagFM.template SetupBoundary<LatSet>(cavity, BouncebackFlag);

  std::size_t obstacle_cells = 0;
  if (ObstacleType == "circle") {
    Circle<T> obstacle(ObstacleRadius, Vector<T, 2>{ObstacleCenterX, ObstacleCenterY});
    FlagFM.forEach(obstacle, [&](FLAG& field, std::size_t id) {
      if (util::isFlag(field.get(id), AABBFlag)) {
        field.SetField(id, BouncebackFlag);
        ++obstacle_cells;
      }
    });
  } else if (ObstacleType == "rectangle") {
    AABB<T, LatSet::d> obstacle(
      Vector<T, LatSet::d>{ObstacleCenterX - ObstacleWidth / T(2), ObstacleCenterY - ObstacleHeight / T(2)},
      Vector<T, LatSet::d>{ObstacleCenterX + ObstacleWidth / T(2), ObstacleCenterY + ObstacleHeight / T(2)});
    FlagFM.forEach(obstacle, [&](FLAG& field, std::size_t id) {
      if (util::isFlag(field.get(id), AABBFlag)) {
        field.SetField(id, BouncebackFlag);
        ++obstacle_cells;
      }
    });
  } else {
    std::cerr << "Unsupported obstacle type: " << ObstacleType << std::endl;
    return 2;
  }
  std::cout << "Obstacle cells: " << obstacle_cells << std::endl;

  FlagFM.forEach(left, [&](FLAG& field, std::size_t id) {
    if (util::isFlag(field.get(id), BouncebackFlag)) field.SetField(id, InletFlag);
  });
  FlagFM.forEach(right, [&](FLAG& field, std::size_t id) {
    if (util::isFlag(field.get(id), BouncebackFlag)) field.SetField(id, OutletFlag);
  });

  vtmwriter::ScalarWriter FlagWriter("flag", FlagFM);
  vtmwriter::vtmWriter<T, LatSet::d> GeoWriter("GeoFlag", Geo);
  GeoWriter.addWriterSet(FlagWriter);
  GeoWriter.WriteBinary();

  using FIELDS = TypePack<RHO<T>, VELOCITY<T, LatSet::d>, POP<T, LatSet::q>>;
  using CELL = Cell<T, LatSet, FIELDS>;
  ValuePack InitValues(BaseConv.getLatRhoInit(), Vector<T, LatSet::d>{}, T{});
  BlockLatticeManager<T, LatSet, FIELDS> NSLattice(Geo, InitValues, BaseConv);
  NSLattice.EnableToleranceU();
  T res = 1;

  Vector<T, LatSet::d> LatU_Wall = BaseConv.getLatticeU(U_Wall);
  NSLattice.getField<VELOCITY<T, LatSet::d>>().forEach(
    FlagFM, InletFlag,
    [&](auto& field, std::size_t id) { field.SetField(id, LatU_Wall); });

  BBLikeFixedBlockBdManager<bounceback::normal<CELL>,
                            BlockLatticeManager<T, LatSet, FIELDS>,
                            BlockFieldManager<FLAG, T, LatSet::d>>
    NS_BB("NS_BB", NSLattice, FlagFM, BouncebackFlag, VoidFlag);
  BBLikeFixedBlockBdManager<bounceback::movingwall<CELL>,
                            BlockLatticeManager<T, LatSet, FIELDS>,
                            BlockFieldManager<FLAG, T, LatSet::d>>
    NS_Inlet("NS_Inlet", NSLattice, FlagFM, InletFlag, VoidFlag);
  BBLikeFixedBlockBdManager<bounceback::anti_pressure<CELL>,
                            BlockLatticeManager<T, LatSet, FIELDS>,
                            BlockFieldManager<FLAG, T, LatSet::d>>
    NS_Outlet("NS_Outlet", NSLattice, FlagFM, OutletFlag, VoidFlag);
  BlockBoundaryManager BM(&NS_BB, &NS_Inlet, &NS_Outlet);

  using RhoUTask = tmp::Key_TypePair<AABBFlag | OutletFlag, moment::rhoU<CELL, true>>;
  using rhoTask = tmp::Key_TypePair<InletFlag, moment::rho<CELL>>;
  using RhoUTaskSelector = TaskSelector<std::uint8_t, CELL, RhoUTask>;
  using collisionTask = collision::BGK<moment::useFieldrhoU<CELL>, equilibrium::SecondOrder<CELL>>;

  vtmwriter::ScalarWriter RhoWriter("Rho", NSLattice.getField<RHO<T>>());
  vtmwriter::VectorWriter VecWriter("Velocity", NSLattice.getField<VELOCITY<T, 2>>());
  vtmwriter::vtmWriter<T, LatSet::d> NSWriter("obstacle2d", Geo);
  NSWriter.addWriterSet(RhoWriter, VecWriter);

  Timer MainLoopTimer;
  Timer OutputTimer;
  NSWriter.WriteBinary(MainLoopTimer());
  InitFastFluentNativeConvergence();
  Printer::Print_BigBanner(std::string("Start Calculation..."));

  while (MainLoopTimer() < MaxStep && res > tol) {
    NSLattice.ApplyCellDynamics<RhoUTaskSelector>(MainLoopTimer(), FlagFM);
    NSLattice.ApplyCellDynamics<collisionTask>(MainLoopTimer());
    NSLattice.Stream(MainLoopTimer());
    BM.Apply(MainLoopTimer());
    NSLattice.Communicate(MainLoopTimer());

    ++MainLoopTimer;
    ++OutputTimer;

    if (MainLoopTimer() % OutputStep == 0) {
      res = NSLattice.getToleranceU(-1);
      OutputTimer.Print_InnerLoopPerformance(Geo.getTotalCellNum(), OutputStep);
      Printer::Print_Res<T>(res);
      Printer::Endl();
      AppendFastFluentNativeConvergence(MainLoopTimer(), res);
      NSWriter.WriteBinary(MainLoopTimer());
    }
  }

  Printer::Print_BigBanner(std::string("Calculation Complete!"));
  MainLoopTimer.Print_MainLoopPerformance(Geo.getTotalCellNum());
  Printer::Print("Total PhysTime", BaseConv.getPhysTime(MainLoopTimer()));
  Printer::Endl();
  WriteFastFluentNativeSummary("obstacle2d", MainLoopTimer(), MaxStep, OutputStep, res,
                               Ni, Nj, Cell_Len, rho_ref, Kine_Visc, U_Max,
                               BaseConv.getPhysTime(MainLoopTimer()), "obstacle2d",
                               obstacle_cells);

  return 0;
}
'''
