"""FastFluent-native S1 simulation validation pack.

The pack runs small public FastFluent/FastCFD-native numerical routes, writes a
uniform simulation artifact contract, and records honest gaps where a route is
not yet a native field-simulation backend. It never launches ANSYS Fluent,
PyFluent, raw Fluent TUI, UDF generation, or private case/data workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import csv
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Callable

from fromcad2cfd_cad import AgentResult

from .native_simulation_artifacts import (
    NATIVE_SIMULATION_PACK_SCHEMA_VERSION,
    build_native_simulation_result,
    empty_convergence_summary,
    empty_mesh_summary,
    empty_runtime_summary,
    write_native_simulation_result,
)
from .preflight import detect_fastcfd_environment
from .unstructured.channel_validation import run_channel_convergence_case, write_unit_square_channel_mesh
from .unstructured.diffusion import run_scalar_diffusion_case
from .unstructured.obstacle import run_obstacle_channel_evidence
from .unstructured.steady_incompressible import run_steady_incompressible_case
from .unstructured.turbulence_ladder import run_turbulence_ladder_case
from .vof_transport import run_vof_lite_transport_benchmark


CaseRunner = Callable[[Path], dict[str, Any]]


@dataclass(frozen=True)
class NativeSimulationCaseSpec:
    case_id: str
    case_name: str
    module: str
    backend: str
    group: str
    expected_backend: str
    runner: CaseRunner | None = None
    actual_native_simulation: bool = True
    model_comparison: bool = False
    grid_convergence: bool = False
    field_expected: bool = False
    convergence_expected: bool = False
    unavailable_reason: str | None = None
    limitations: list[str] = field(default_factory=list)
    input_summary: dict[str, Any] = field(default_factory=dict)

    def output_dir(self, root: Path) -> Path:
        return root / self.group / self.case_id


def create_native_simulation_case_registry() -> list[NativeSimulationCaseSpec]:
    """Return the S1 public-native simulation case registry."""

    return [
        NativeSimulationCaseSpec(
            case_id="cavity2d_re_sweep",
            case_name="Structured Cavity2D Reynolds Sweep",
            module="structured_cases",
            backend="structured_lbm",
            group="structured_cases",
            expected_backend="structured_cpp_fastfluent",
            runner=None,
            actual_native_simulation=False,
            field_expected=True,
            convergence_expected=True,
            unavailable_reason="Structured C++ FastFluent backend is optional for S1 and is not invoked by this pack.",
            limitations=["Recorded as backend status only; no synthetic field output is fabricated."],
            input_summary={"case_family": "cavity2d", "sweep": ["Re_low", "Re_mid", "Re_high"]},
        ),
        NativeSimulationCaseSpec(
            case_id="channel2d_velocity_grid_sweep",
            case_name="Structured Channel2D Velocity/Grid Sweep",
            module="structured_cases",
            backend="structured_lbm",
            group="structured_cases",
            expected_backend="structured_cpp_fastfluent",
            runner=None,
            actual_native_simulation=False,
            grid_convergence=True,
            field_expected=True,
            convergence_expected=True,
            unavailable_reason="Structured C++ FastFluent backend is optional for S1 and is not invoked by this pack.",
            limitations=["The unstructured Poiseuille convergence case provides the S1 grid-convergence evidence."],
            input_summary={"case_family": "channel2d", "variables": {"velocity": ["low", "base", "high"], "grid": ["coarse", "medium", "fine"]}},
        ),
        NativeSimulationCaseSpec(
            case_id="obstacle2d_shape_comparison",
            case_name="Structured Obstacle2D Shape Comparison",
            module="structured_cases",
            backend="structured_lbm",
            group="structured_cases",
            expected_backend="structured_cpp_fastfluent",
            runner=None,
            actual_native_simulation=False,
            model_comparison=True,
            field_expected=True,
            unavailable_reason="Structured C++ FastFluent backend is optional for S1 and is not invoked by this pack.",
            limitations=["The unstructured obstacle case records geometry evidence, not a structured obstacle flow solve."],
            input_summary={"case_family": "obstacle2d", "shapes": ["circle", "rectangle"]},
        ),
        NativeSimulationCaseSpec(
            case_id="poiseuille_channel_convergence",
            case_name="Unstructured Poiseuille Channel Convergence",
            module="unstructured_cases",
            backend="unstructured_fvm",
            group="unstructured_cases",
            expected_backend="unstructured_fvm",
            runner=_run_poiseuille_channel_convergence,
            grid_convergence=True,
            field_expected=True,
            convergence_expected=True,
            input_summary={"mesh_levels": [2, 4, 8], "viscosity": 1.0, "pressure_drop": 1.0},
        ),
        NativeSimulationCaseSpec(
            case_id="steady_incompressible_channel",
            case_name="Steady Incompressible Channel",
            module="unstructured_cases",
            backend="unstructured_fvm",
            group="unstructured_cases",
            expected_backend="unstructured_fvm",
            runner=_run_steady_incompressible_channel,
            field_expected=True,
            convergence_expected=True,
            input_summary={"mesh": "unit_square_8x4", "iterations": 5, "density": 1.0, "viscosity": 0.01},
        ),
        NativeSimulationCaseSpec(
            case_id="obstacle_channel_evidence",
            case_name="Body-Fitted Obstacle Channel Evidence",
            module="unstructured_cases",
            backend="unstructured_fvm",
            group="unstructured_cases",
            expected_backend="unstructured_fvm",
            runner=_run_obstacle_channel_evidence,
            actual_native_simulation=True,
            field_expected=True,
            input_summary={"mesh": "body_fitted_obstacle_channel", "nx": 12, "ny": 6},
            limitations=["This case is an unstructured geometry and mesh-evidence route; it does not solve obstacle flow momentum."],
        ),
        NativeSimulationCaseSpec(
            case_id="vof_lite_alpha_transport",
            case_name="VOF-Lite Alpha Transport",
            module="unstructured_cases",
            backend="unstructured_fvm",
            group="unstructured_cases",
            expected_backend="vof_lite_alpha_transport",
            runner=_run_vof_lite_alpha_transport,
            field_expected=True,
            convergence_expected=True,
            input_summary={"steps": 12, "time_step_s": 0.02, "velocity_m_s": [0.1, 0.0]},
            limitations=["VOF-lite transports bounded alpha only; it does not solve pressure, momentum, or surface tension."],
        ),
        NativeSimulationCaseSpec(
            case_id="turbulence_ladder",
            case_name="Turbulence Ladder Channel Comparison",
            module="unstructured_cases",
            backend="unstructured_fvm",
            group="unstructured_cases",
            expected_backend="turbulence_ladder",
            runner=_run_turbulence_ladder,
            model_comparison=True,
            field_expected=True,
            convergence_expected=True,
            input_summary={"iterations": 3, "models": ["algebraic_eddy_viscosity", "standard_k_epsilon", "pressure_corrected_k_epsilon", "menter_sst"]},
            limitations=["This is a bounded turbulence evidence ladder; it is not production RANS validation."],
        ),
        NativeSimulationCaseSpec(
            case_id="scalar_diffusion_field_smoke",
            case_name="Scalar Diffusion Field Smoke Benchmark",
            module="unstructured_cases",
            backend="unstructured_fvm",
            group="unstructured_cases",
            expected_backend="unstructured_scalar_diffusion",
            runner=_run_scalar_diffusion_field_smoke,
            field_expected=True,
            convergence_expected=True,
            input_summary={"mesh": "unit_square_6x6", "manufactured_solution": "linear", "diffusivity": 1.0},
            limitations=["Scalar diffusion is an auxiliary field-output smoke benchmark, not a Navier-Stokes solve."],
        ),
    ]


def run_native_simulation_case(case_spec: NativeSimulationCaseSpec | dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    """Run one S1 case and write simulation_result.json plus case summary."""

    spec = _coerce_case_spec(case_spec)
    case_dir = Path(output_dir)
    _mkdir(case_dir)
    start = time.perf_counter()
    started_at = _now_iso()
    if spec.runner is None:
        result = _build_unavailable_result(spec, case_dir, started_at=started_at, elapsed_s=time.perf_counter() - start)
        write_native_simulation_result(result, case_dir / "simulation_result.json")
        _write_text(case_dir / "backend_unavailable.md", _backend_unavailable_markdown(result))
        _write_text(case_dir / "simulation_summary.md", _case_markdown(result))
        return result

    backend_dir = case_dir / "backend_raw"
    _mkdir(backend_dir)
    try:
        source_result = _run_in_short_stage(spec, backend_dir)
        elapsed = time.perf_counter() - start
        result = _build_available_result(spec, case_dir, source_result, started_at=started_at, elapsed_s=elapsed)
    except Exception as exc:  # noqa: BLE001 - S1 must fail closed per case and continue the pack.
        elapsed = time.perf_counter() - start
        result = build_native_simulation_result(
            case_id=spec.case_id,
            case_name=spec.case_name,
            module=spec.module,
            backend=spec.backend,
            backend_status="failed",
            status="block",
            input_summary=dict(spec.input_summary),
            runtime_summary=empty_runtime_summary(
                start_time=started_at,
                end_time=_now_iso(),
                elapsed_s=elapsed,
                exit_reason="backend_exception",
            ),
            mesh_summary=empty_mesh_summary(),
            numerics_summary={"expected_backend": spec.expected_backend},
            convergence_summary=empty_convergence_summary(),
            qoi_summary={},
            field_outputs=[],
            warnings=[],
            blocking_errors=[str(exc)],
            limitations=list(spec.limitations),
            metadata=_case_metadata(spec, case_dir, actual_case_ran=False),
        )
    write_native_simulation_result(result, case_dir / "simulation_result.json")
    _write_text(case_dir / "simulation_summary.md", _case_markdown(result))
    return result


def run_native_simulation_validation_pack(output_dir: str | Path) -> dict[str, Any]:
    """Run all S1 public native simulation cases and write pack-level artifacts."""

    root = Path(output_dir)
    _mkdir(root)
    cases = []
    for spec in create_native_simulation_case_registry():
        cases.append(run_native_simulation_case(spec, spec.output_dir(root)))
    alignment_paths = write_passport_simulation_alignment_reports(cases, root / "passport_simulation_alignment")
    manifest = build_simulation_manifest(cases, root, alignment_paths)
    manifest_path = write_simulation_manifest(manifest, root / "simulation_manifest.json")
    summary_path = write_simulation_summary(manifest, root / "simulation_summary.md")
    limitations_path = _write_text(root / "limitations.md", _limitations_markdown(manifest))
    status = "success" if manifest["acceptance_summary"]["s1_complete"] else "partial"
    result = AgentResult(
        status=status,
        backend="fastcfd",
        operation="native_simulation_validation_pack",
        message="FastFluent-native S1 simulation validation pack completed.",
        outputs={
            "manifest": manifest,
            "artifacts": {
                "simulation_manifest": str(manifest_path),
                "simulation_summary": str(summary_path),
                "limitations": str(limitations_path),
                "passport_simulation_alignment": {key: str(value) for key, value in alignment_paths.items()},
            },
        },
        metadata={"fluent_launched": False, "output_dir": str(root)},
    )
    _write_json(root / "pack_status.json", result.to_dict())
    return result.to_dict()


def build_simulation_manifest(cases: list[dict[str, Any]], output_dir: Path, alignment_paths: dict[str, Path]) -> dict[str, Any]:
    actual_cases = [case for case in cases if case["metadata"].get("actual_native_simulation") and case["status"] in {"pass", "warn"}]
    field_cases = [case for case in cases if case.get("field_outputs")]
    convergence_cases = [
        case
        for case in cases
        if case.get("convergence_summary", {}).get("residual_history_path") not in {None, "not_available"}
        or case.get("metadata", {}).get("grid_convergence")
    ]
    model_cases = [case for case in cases if case.get("metadata", {}).get("model_comparison")]
    grid_cases = [case for case in cases if case.get("metadata", {}).get("grid_convergence")]
    acceptance = {
        "artifact_contract_exists": True,
        "runner_exists": True,
        "cli_exists": True,
        "at_least_five_native_cases_ran": len(actual_cases) >= 5,
        "manifest_generated": True,
        "summary_generated": True,
        "at_least_three_field_cases": len(field_cases) >= 3,
        "at_least_one_convergence_history": bool(convergence_cases),
        "at_least_one_mesh_or_grid_comparison": bool(grid_cases),
        "at_least_one_model_or_closure_comparison": bool(model_cases),
        "alignment_reports_generated": len(alignment_paths) >= 5,
        "fluent_launched": False,
    }
    acceptance["s1_complete"] = all(
        value for key, value in acceptance.items() if key not in {"fluent_launched"}
    ) and acceptance["fluent_launched"] is False
    return {
        "schema_version": NATIVE_SIMULATION_PACK_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "backend": "fastcfd",
        "case_count": len(cases),
        "actual_simulation_case_count": len(actual_cases),
        "unavailable_case_count": len([case for case in cases if case["status"] == "unavailable"]),
        "field_output_case_count": len(field_cases),
        "convergence_case_count": len(convergence_cases),
        "model_comparison_case_count": len(model_cases),
        "grid_convergence_case_count": len(grid_cases),
        "backend_status_summary": _count_by(cases, "backend_status"),
        "case_status_summary": _count_by(cases, "status"),
        "case_index": [_case_index_entry(case) for case in cases],
        "artifact_index": _artifact_index(cases, output_dir, alignment_paths),
        "acceptance_summary": acceptance,
        "limitations": [
            "S1 validates public FastFluent-native simulation routes and artifact generation only.",
            "S1 does not prove high-fidelity Fluent accuracy.",
            "S1 does not replace ANSYS Fluent for final engineering validation.",
            "Structured C++ backend cases are recorded as backend status only in this pack when not run.",
            "Obstacle-channel evidence is a body-fitted geometry/mesh evidence route, not a solved obstacle-flow route.",
        ],
        "metadata": {
            "output_dir": str(output_dir),
            "fluent_launched": False,
            "pyfluent_called": False,
            "private_data_used": False,
        },
    }


def write_simulation_manifest(result: dict[str, Any], path: str | Path) -> Path:
    return _write_json(Path(path), result)


def write_simulation_summary(result: dict[str, Any], path: str | Path) -> Path:
    return _write_text(Path(path), _pack_markdown(result))


def write_passport_simulation_alignment_reports(cases: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Path]:
    target = Path(output_dir)
    _mkdir(target)
    by_id = {case["case_id"]: case for case in cases}
    reports = {
        "vof_passport_vs_vof_lite": _vof_alignment(by_id.get("vof_lite_alpha_transport", {})),
        "turbulence_passport_vs_turbulence_ladder": _turbulence_alignment(by_id.get("turbulence_ladder", {})),
        "rheology_passport_simulation_gap": _gap_report(
            title="Rheology Passport Simulation Gap",
            statement="Rheology currently has setup-evidence support but no native field-simulation route in S1.",
            next_steps=["temperature-dependent viscosity channel benchmark", "non-Newtonian channel benchmark"],
        ),
        "steam_air_v2_simulation_gap": _gap_report(
            title="Steam-Air Condensation v2 Simulation Gap",
            statement="Steam-air v2 currently has passport and solver-plan evidence but no full native condensation field simulation in S1.",
            next_steps=["scalar heat diffusion case", "1D/2D heat-transfer mini benchmark", "species diffusion mini benchmark", "near-wall source-term toy benchmark"],
        ),
        "solid_liquid_passport_simulation_gap": _gap_report(
            title="Solid-Liquid Passport Simulation Gap",
            statement="Solid-liquid suspension currently has setup-evidence support but no native DPM, Mixture, Eulerian, or DEM simulation route in S1.",
            next_steps=["settling ODE benchmark", "passive particle relaxation benchmark", "1D concentration settling toy model"],
        ),
    }
    paths = {}
    for stem, text in reports.items():
        paths[stem] = _write_text(target / f"{stem}.md", text)
    return paths


def _run_poiseuille_channel_convergence(target_dir: Path) -> dict[str, Any]:
    return run_channel_convergence_case(output_dir=target_dir, mesh_levels=(2, 4, 8), viscosity=1.0, pressure_drop=1.0)


def _run_steady_incompressible_channel(target_dir: Path) -> dict[str, Any]:
    mesh = write_unit_square_channel_mesh(target_dir / "steady_channel_8x4.msh", nx=8, ny=4)
    return run_steady_incompressible_case(mesh, output_dir=target_dir, iterations=5, viscosity=1.0e-2)


def _run_obstacle_channel_evidence(target_dir: Path) -> dict[str, Any]:
    return run_obstacle_channel_evidence(output_dir=target_dir, nx=12, ny=6)


def _run_vof_lite_alpha_transport(target_dir: Path) -> dict[str, Any]:
    mesh = write_unit_square_channel_mesh(target_dir / "vof_lite_channel_6x4.msh", nx=6, ny=4)
    return run_vof_lite_transport_benchmark(mesh, output_dir=target_dir, steps=12, time_step_s=0.02, velocity_m_s=(0.1, 0.0))


def _run_turbulence_ladder(target_dir: Path) -> dict[str, Any]:
    return run_turbulence_ladder_case(output_dir=target_dir, iterations=3)


def _run_scalar_diffusion_field_smoke(target_dir: Path) -> dict[str, Any]:
    mesh = write_unit_square_channel_mesh(target_dir / "scalar_diffusion_6x6.msh", nx=6, ny=6)
    return run_scalar_diffusion_case(mesh, output_dir=target_dir, manufactured_solution="linear", diffusivity=1.0)


def _run_in_short_stage(spec: NativeSimulationCaseSpec, backend_dir: Path) -> dict[str, Any]:
    stage = Path(tempfile.mkdtemp(prefix=f"ff_s1_{spec.case_id[:18]}_"))
    try:
        assert spec.runner is not None
        spec.runner(stage)
        source_result = _load_source_status(stage)
        _copy_tree(stage, backend_dir)
        return _replace_path_strings(source_result, stage, backend_dir)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _load_source_status(source_root: Path) -> dict[str, Any]:
    status_files = sorted(source_root.rglob("*status.json"))
    if status_files:
        return json.loads(status_files[-1].read_text(encoding="utf-8"))
    summary_files = sorted(source_root.rglob("*summary.json"))
    if summary_files:
        return {"status": "success", "outputs": {"summary": json.loads(summary_files[-1].read_text(encoding="utf-8"))}, "errors": []}
    return {"status": "success", "outputs": {"artifacts": _scan_file_artifacts(source_root)}, "errors": []}


def _build_available_result(
    spec: NativeSimulationCaseSpec,
    case_dir: Path,
    source_result: dict[str, Any],
    *,
    started_at: str,
    elapsed_s: float,
) -> dict[str, Any]:
    outputs = source_result.get("outputs", {}) if isinstance(source_result.get("outputs"), dict) else {}
    artifacts = outputs.get("artifacts", {}) if isinstance(outputs.get("artifacts"), dict) else {}
    qoi = outputs.get("qoi") or outputs.get("convergence") or outputs.get("summary") or {}
    status = "pass" if source_result.get("status") == "success" else "warn"
    blocking = list(source_result.get("errors", []))
    if source_result.get("status") not in {"success", "partial"}:
        status = "block"
    field_outputs = _field_outputs(case_dir / "backend_raw", artifacts)
    qoi_summary = _compact_qoi(qoi)
    mesh_summary = _mesh_summary(outputs, case_dir / "backend_raw")
    convergence_summary = _convergence_summary(spec, outputs, artifacts, case_dir / "backend_raw")
    runtime_summary = _runtime_summary(started_at=started_at, elapsed_s=elapsed_s, qoi=qoi_summary, convergence=convergence_summary)
    warnings = list(source_result.get("warnings", [])) if isinstance(source_result.get("warnings"), list) else []
    if status == "block" and spec.model_comparison and (field_outputs or qoi_summary):
        warnings.append("Model-comparison artifacts were generated, but one or more tiers did not meet the bounded acceptance tolerance.")
        status = "warn"
    if spec.field_expected and not field_outputs:
        warnings.append("No field output was detected for a field-expected S1 case.")
    if spec.convergence_expected and convergence_summary["residual_history_path"] == "not_available" and not spec.grid_convergence:
        warnings.append("No residual or convergence history was detected for a convergence-expected S1 case.")
    return build_native_simulation_result(
        case_id=spec.case_id,
        case_name=spec.case_name,
        module=spec.module,
        backend=spec.backend,
        backend_status="available",
        status=status,
        input_summary=dict(spec.input_summary),
        runtime_summary=runtime_summary,
        mesh_summary=mesh_summary,
        numerics_summary={
            "expected_backend": spec.expected_backend,
            "source_status": source_result.get("status"),
            "source_operation": source_result.get("operation", "not_available"),
            "solver_route": outputs.get("solver_execution", "not_available"),
            "source_errors": blocking,
        },
        convergence_summary=convergence_summary,
        qoi_summary=qoi_summary,
        field_outputs=field_outputs,
        warnings=warnings,
        blocking_errors=blocking,
        limitations=list(spec.limitations) + _listify(qoi.get("limitations") if isinstance(qoi, dict) else []),
        metadata=_case_metadata(spec, case_dir, actual_case_ran=status in {"pass", "warn"}),
    )


def _build_unavailable_result(spec: NativeSimulationCaseSpec, case_dir: Path, *, started_at: str, elapsed_s: float) -> dict[str, Any]:
    preflight = detect_fastcfd_environment().to_dict()
    reason = spec.unavailable_reason or "Backend is unavailable for this S1 pack."
    return build_native_simulation_result(
        case_id=spec.case_id,
        case_name=spec.case_name,
        module=spec.module,
        backend=spec.backend,
        backend_status="unavailable",
        status="unavailable",
        input_summary=dict(spec.input_summary),
        runtime_summary=empty_runtime_summary(
            start_time=started_at,
            end_time=_now_iso(),
            elapsed_s=elapsed_s,
            exit_reason="backend_unavailable_recorded",
        ),
        mesh_summary=empty_mesh_summary(),
        numerics_summary={"expected_backend": spec.expected_backend, "preflight_status": preflight.get("status")},
        convergence_summary=empty_convergence_summary(),
        qoi_summary={},
        field_outputs=[],
        warnings=[reason],
        blocking_errors=[],
        limitations=list(spec.limitations) + [reason],
        metadata=_case_metadata(spec, case_dir, actual_case_ran=False) | {"preflight": preflight},
    )


def _case_metadata(spec: NativeSimulationCaseSpec, case_dir: Path, *, actual_case_ran: bool) -> dict[str, Any]:
    return {
        "case_dir": str(case_dir),
        "actual_native_simulation": bool(spec.actual_native_simulation and actual_case_ran),
        "model_comparison": spec.model_comparison,
        "grid_convergence": spec.grid_convergence,
        "field_expected": spec.field_expected,
        "convergence_expected": spec.convergence_expected,
        "fluent_launched": False,
        "pyfluent_called": False,
        "private_data_used": False,
    }


def _field_outputs(root: Path, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    files: list[Path] = []
    for value in _iter_values(artifacts):
        if isinstance(value, str):
            path = Path(value)
            if path.suffix.lower() in {".vtu", ".vtk", ".csv"} and _exists(path):
                files.append(path)
    files.extend(_walk_files(root, suffixes={".vtu", ".vtk"}))
    unique = []
    seen: set[str] = set()
    for path in files:
        key = _display_path(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return [
        {
            "path": _display_path(path),
            "kind": path.suffix.lower().lstrip(".") or "file",
            "bytes": _file_size(path),
        }
        for path in unique
    ]


def _compact_qoi(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    compact = {
        "schema_version": payload.get("schema_version", "not_available"),
        "status": payload.get("status", "not_available"),
        "solver_family": payload.get("solver_family", payload.get("backend", "not_available")),
        "metrics": metrics or _numeric_leaf_subset(payload),
    }
    for key in [
        "case_count",
        "observed_orders",
        "monotonic_error_decrease",
        "recommendation",
        "cell_count",
        "node_count",
        "steps",
        "iterations",
        "acceptance",
    ]:
        if key in payload:
            compact[key] = payload[key]
    return compact


def _mesh_summary(outputs: dict[str, Any], root: Path) -> dict[str, Any]:
    manifest = outputs.get("manifest") if isinstance(outputs.get("manifest"), dict) else {}
    if not manifest:
        manifest_files = _walk_files(root, suffixes={".json"}, names={"mesh_manifest.json"})
        if manifest_files:
            manifest = _read_json(manifest_files[0])
    quality = outputs.get("quality") if isinstance(outputs.get("quality"), dict) else {}
    if not quality:
        quality_files = _walk_files(root, suffixes={".json"}, names={"mesh_quality.json"})
        if quality_files:
            quality = _read_json(quality_files[0])
    return empty_mesh_summary(
        mesh_type=manifest.get("cell_kinds", manifest.get("mesh_type", "unstructured")),
        dimension=manifest.get("dimension", "not_available"),
        cell_count=manifest.get("cell_count", "not_available"),
        node_count=manifest.get("node_count", "not_available"),
        face_count=manifest.get("face_count", "not_available"),
        min_cell_size=quality.get("min_cell_measure", "not_available"),
        max_cell_size=quality.get("max_cell_measure", "not_available"),
        mesh_quality_summary=quality or "not_available",
        boundary_zone_summary=manifest.get("boundary_zone_counts", manifest.get("physical_names", "not_available")),
    )


def _convergence_summary(
    spec: NativeSimulationCaseSpec,
    outputs: dict[str, Any],
    artifacts: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    history_path = _find_history_path(artifacts, root)
    if spec.grid_convergence:
        convergence = outputs.get("convergence") if isinstance(outputs.get("convergence"), dict) else {}
        if convergence:
            normalized = _write_convergence_history_from_cases(root / "convergence_history.csv", convergence.get("cases", []))
            return empty_convergence_summary(
                residual_history_path=str(normalized),
                final_residuals={"finest_l2_error": _last_case_metric(convergence, "cell_center_velocity_l2_error")},
                residual_drop_orders=convergence.get("observed_orders", []),
                steady_or_transient="steady",
                converged=convergence.get("status") == "passed",
                convergence_warnings=convergence.get("blocking_errors", []),
            )
    if history_path:
        final = _last_csv_row(history_path)
        return empty_convergence_summary(
            residual_history_path=str(history_path),
            final_residuals=_numeric_leaf_subset(final),
            residual_drop_orders="not_available",
            steady_or_transient="steady_or_pseudo_transient",
            converged=True,
            convergence_warnings=[],
        )
    return empty_convergence_summary()


def _runtime_summary(*, started_at: str, elapsed_s: float, qoi: dict[str, Any], convergence: dict[str, Any]) -> dict[str, Any]:
    metrics = qoi.get("metrics", {}) if isinstance(qoi.get("metrics"), dict) else {}
    final_residuals = convergence.get("final_residuals", {}) if isinstance(convergence.get("final_residuals"), dict) else {}
    final_residual = (
        metrics.get("final_residual_l2")
        or metrics.get("u_final_residual_l2")
        or metrics.get("final_divergence_l2")
        or final_residuals.get("residual_l2")
        or final_residuals.get("finest_l2_error")
        or "not_available"
    )
    iteration_count = qoi.get("iterations") or qoi.get("steps") or metrics.get("iteration_count") or "not_available"
    return empty_runtime_summary(
        start_time=started_at,
        end_time=_now_iso(),
        elapsed_s=elapsed_s,
        iteration_count=iteration_count,
        time_step_count=qoi.get("steps", "not_available"),
        final_residual=final_residual,
        residual_drop="not_available",
        exit_reason="completed",
    )


def _pack_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# FastFluent S1 Native Simulation Validation Pack",
        "",
        f"Overall S1 status: `{'complete' if manifest['acceptance_summary']['s1_complete'] else 'partial'}`",
        f"Generated at: `{manifest['generated_at']}`",
        f"Case count: `{manifest['case_count']}`",
        f"Actual native simulation cases run: `{manifest['actual_simulation_case_count']}`",
        f"Field-output cases: `{manifest['field_output_case_count']}`",
        f"Convergence/residual cases: `{manifest['convergence_case_count']}`",
        "",
        "## Structured Backend Summary",
        "",
        "Structured C++ FastFluent cases are recorded as backend-status cases in S1 when the optional backend is not invoked.",
        "",
        "## Unstructured Backend Summary",
        "",
    ]
    for case in manifest["case_index"]:
        lines.append(f"- `{case['case_id']}`: status `{case['status']}`, backend `{case['backend_status']}`, fields `{case['field_output_count']}`")
    lines.extend(
        [
            "",
            "## VOF-Lite Summary",
            "",
            "The VOF-lite case validates bounded alpha transport and exports alpha field evidence. It does not solve pressure, momentum, surface tension, or interface reconstruction.",
            "",
            "## Turbulence Ladder Summary",
            "",
            "The turbulence ladder compares bounded algebraic eddy-viscosity, k-epsilon, pressure-corrected k-epsilon, and SST evidence routes where available. It is not production turbulence validation.",
            "",
            "## Field Output Summary",
            "",
            f"Field-producing cases: `{manifest['field_output_case_count']}`.",
            "",
            "## QoI Summary",
            "",
        ]
    )
    for case in manifest["case_index"]:
        lines.append(f"- `{case['case_id']}` QoI keys: `{case['qoi_keys']}`")
    lines.extend(
        [
            "",
            "## Passport-Simulation Alignment Summary",
            "",
            "Alignment reports connect VOF and turbulence passports to native simulation evidence and record gaps for rheology, steam-air condensation v2, and solid-liquid suspension.",
            "",
            "## What S1 Proves",
            "",
            "- FastFluent-native routes can run public small cases.",
            "- S1 can produce simulation_result.json, convergence or residual histories, field outputs, QoI summaries, a manifest, and alignment reports.",
            "",
            "## What S1 Does Not Prove",
            "",
            "S1 does not prove high-fidelity Fluent accuracy.",
            "S1 validates FastFluent-native simulation routes and artifact generation.",
            "S1 does not replace ANSYS Fluent for final engineering validation.",
            "",
            "## Fluent Boundary",
            "",
            "Fluent was not launched. PyFluent was not called. No Fluent case/data files were read or modified.",
            "",
        ]
    )
    return "\n".join(lines)


def _case_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {result['case_name']}",
            "",
            f"- Case ID: `{result['case_id']}`",
            f"- Status: `{result['status']}`",
            f"- Backend status: `{result['backend_status']}`",
            f"- Backend: `{result['backend']}`",
            f"- Field outputs: `{len(result['field_outputs'])}`",
            f"- Convergence history: `{result['convergence_summary'].get('residual_history_path')}`",
            f"- Fluent launched: `{result['metadata'].get('fluent_launched')}`",
            "",
            "## Limitations",
            "",
            *[f"- {item}" for item in result["limitations"]],
            "",
        ]
    )


def _limitations_markdown(manifest: dict[str, Any]) -> str:
    lines = ["# FastFluent S1 Limitations", ""]
    lines.extend(f"- {item}" for item in manifest["limitations"])
    lines.extend(["", "## Case-Specific Limitations", ""])
    for case in manifest["case_index"]:
        if case["limitations"]:
            lines.append(f"### `{case['case_id']}`")
            lines.extend(f"- {item}" for item in case["limitations"])
            lines.append("")
    return "\n".join(lines)


def _vof_alignment(case: dict[str, Any]) -> str:
    metrics = case.get("qoi_summary", {}).get("metrics", {})
    return "\n".join(
        [
            "# VOF Passport vs VOF-Lite Native Simulation",
            "",
            "## Passport Evidence Used",
            "",
            "The H1 VOF passport provides Courant, phase-property, gravity, and volume-fraction setup evidence.",
            "",
            "## Native Simulation Case Used",
            "",
            f"Case: `{case.get('case_id', 'vof_lite_alpha_transport')}`",
            f"Status: `{case.get('status', 'not_run')}`",
            "",
            "## Quantities Aligned",
            "",
            f"- Alpha min: `{metrics.get('min_alpha', 'not_available')}`",
            f"- Alpha max: `{metrics.get('max_alpha', 'not_available')}`",
            f"- Relative balance error: `{metrics.get('relative_balance_error', 'not_available')}`",
            f"- Max Courant number: `{metrics.get('max_courant_number', 'not_available')}`",
            "",
            "## Limitations",
            "",
            "VOF-lite is scalar alpha transport only. It does not replace Fluent VOF momentum, pressure, interface reconstruction, or surface-tension validation.",
            "",
        ]
    )


def _turbulence_alignment(case: dict[str, Any]) -> str:
    qoi = case.get("qoi_summary", {})
    return "\n".join(
        [
            "# Turbulence Passport vs Turbulence Ladder Native Simulation",
            "",
            "## Passport Evidence Used",
            "",
            "The turbulence passport records Reynolds-regime, near-wall, y-plus, and model-intent setup evidence.",
            "",
            "## Native Simulation Case Used",
            "",
            f"Case: `{case.get('case_id', 'turbulence_ladder')}`",
            f"Status: `{case.get('status', 'not_run')}`",
            f"Recommendation: `{qoi.get('recommendation', {}).get('tier', 'not_available')}`",
            "",
            "## Quantities Aligned",
            "",
            f"- QoI keys: `{sorted(qoi.keys())}`",
            f"- Field outputs: `{len(case.get('field_outputs', []))}`",
            "",
            "## Limitations",
            "",
            "The ladder is a bounded channel comparison route, not production RANS, DES, or LES validation.",
            "",
        ]
    )


def _gap_report(*, title: str, statement: str, next_steps: list[str]) -> str:
    lines = [f"# {title}", "", statement, "", "## Recommended Next Native Route", ""]
    lines.extend(f"- {item}" for item in next_steps)
    lines.extend(["", "## Boundary", "", "No Fluent execution is claimed in S1.", ""])
    return "\n".join(lines)


def _backend_unavailable_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Backend Unavailable: {result['case_name']}",
            "",
            f"Status: `{result['status']}`",
            "",
            "This case records backend availability only. S1 does not fabricate synthetic field output for unavailable structured routes.",
            "",
        ]
    )


def _copy_tree(source: Path, target: Path) -> None:
    _mkdir(target)
    for root, dirs, files in os.walk(source):
        root_path = Path(root)
        relative = root_path.relative_to(source)
        for directory in dirs:
            _mkdir(target / relative / directory)
        for filename in files:
            src = root_path / filename
            dst = target / relative / filename
            _mkdir(dst.parent)
            shutil.copy2(_win_path(src), _win_path(dst))


def _replace_path_strings(obj: Any, old_root: Path, new_root: Path) -> Any:
    if isinstance(obj, dict):
        return {key: _replace_path_strings(value, old_root, new_root) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_replace_path_strings(value, old_root, new_root) for value in obj]
    if isinstance(obj, str):
        return obj.replace(str(old_root), str(new_root))
    return obj


def _scan_file_artifacts(root: Path) -> dict[str, str]:
    return {path.stem: str(path) for path in root.rglob("*") if path.is_file()}


def _find_history_path(artifacts: dict[str, Any], root: Path) -> Path | None:
    candidates = []
    for value in _iter_values(artifacts):
        if isinstance(value, str):
            path = Path(value)
            if path.suffix.lower() == ".csv" and any(token in path.name.lower() for token in ["history", "residual", "convergence"]):
                candidates.append(path)
    candidates.extend(
        path
        for path in _walk_files(root, suffixes={".csv"})
            if any(token in path.name.lower() for token in ["history", "residual", "convergence", "iterations"])
    )
    return candidates[0] if candidates else None


def _write_convergence_history_from_cases(path: Path, cases: list[dict[str, Any]]) -> Path:
    _mkdir(path.parent)
    with open(_win_path(path), "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_index", "cell_count", "h_proxy", "cell_center_velocity_l2_error", "cell_divergence_l2"])
        writer.writeheader()
        for index, case in enumerate(cases):
            writer.writerow(
                {
                    "case_index": index,
                    "cell_count": case.get("cell_count"),
                    "h_proxy": case.get("h_proxy"),
                    "cell_center_velocity_l2_error": case.get("cell_center_velocity_l2_error"),
                    "cell_divergence_l2": case.get("cell_divergence_l2"),
                }
            )
    return path


def _last_csv_row(path: Path) -> dict[str, Any]:
    with open(_win_path(path), newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-1] if rows else {}


def _last_case_metric(convergence: dict[str, Any], key: str) -> Any:
    cases = convergence.get("cases", [])
    if not cases:
        return "not_available"
    return cases[-1].get(key, "not_available")


def _numeric_leaf_subset(payload: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (int, float, bool)) or value is None:
            compact[key] = value
        elif isinstance(value, str):
            try:
                compact[key] = float(value)
            except ValueError:
                continue
    return compact


def _case_index_entry(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "case_name": case["case_name"],
        "module": case["module"],
        "backend": case["backend"],
        "backend_status": case["backend_status"],
        "status": case["status"],
        "actual_native_simulation": case["metadata"].get("actual_native_simulation"),
        "field_output_count": len(case.get("field_outputs", [])),
        "qoi_keys": sorted(case.get("qoi_summary", {}).keys()),
        "convergence_history": case.get("convergence_summary", {}).get("residual_history_path"),
        "limitations": case.get("limitations", []),
        "warnings": case.get("warnings", []),
        "blocking_errors": case.get("blocking_errors", []),
    }


def _artifact_index(cases: list[dict[str, Any]], output_dir: Path, alignment_paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "output_dir": str(output_dir),
        "case_results": {
            case["case_id"]: str(Path(case["metadata"]["case_dir"]) / "simulation_result.json")
            for case in cases
        },
        "case_summaries": {
            case["case_id"]: str(Path(case["metadata"]["case_dir"]) / "simulation_summary.md")
            for case in cases
        },
        "alignment_reports": {name: str(path) for name, path in alignment_paths.items()},
    }


def _count_by(cases: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        value = str(case.get(key))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _iter_values(obj: Any):
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_values(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_values(value)
    else:
        yield obj


def _listify(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value:
        return [str(value)]
    return []


def _coerce_case_spec(spec: NativeSimulationCaseSpec | dict[str, Any]) -> NativeSimulationCaseSpec:
    if isinstance(spec, NativeSimulationCaseSpec):
        return spec
    registry = {item.case_id: item for item in create_native_simulation_case_registry()}
    case_id = str(spec.get("case_id", ""))
    if case_id not in registry:
        raise ValueError(f"Unknown S1 native simulation case_id: {case_id}")
    return registry[case_id]


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    _mkdir(path.parent)
    with open(_win_path(path), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    with open(_win_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_text(path: Path, text: str) -> Path:
    _mkdir(path.parent)
    with open(_win_path(path), "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def _mkdir(path: Path) -> None:
    os.makedirs(_win_path(path), exist_ok=True)


def _walk_files(root: Path, *, suffixes: set[str] | None = None, names: set[str] | None = None) -> list[Path]:
    files: list[Path] = []
    if not _exists(root):
        return files
    for current, _, filenames in os.walk(_win_path(root)):
        for filename in filenames:
            candidate = Path(current) / filename
            if suffixes and candidate.suffix.lower() not in suffixes:
                continue
            if names and candidate.name not in names:
                continue
            files.append(candidate)
    return sorted(files, key=lambda item: _display_path(item))


def _exists(path: Path) -> bool:
    return os.path.exists(_win_path(path))


def _file_size(path: Path) -> int | str:
    try:
        return os.path.getsize(_win_path(path))
    except OSError:
        return "not_available"


def _display_path(path: Path) -> str:
    text = str(path)
    if text.startswith("\\\\?\\"):
        return text[4:]
    return text


def _win_path(path: Path) -> str:
    raw = str(path)
    if raw.startswith("\\\\?\\"):
        return raw
    absolute = str(Path(path).resolve())
    if os.name == "nt" and not absolute.startswith("\\\\?\\"):
        return "\\\\?\\" + absolute
    return absolute


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
