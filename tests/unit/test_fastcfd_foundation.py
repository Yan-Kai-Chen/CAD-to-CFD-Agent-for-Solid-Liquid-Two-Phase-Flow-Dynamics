from __future__ import annotations

import base64
import json
from pathlib import Path
import struct

import pytest

import fromcad2cfd_fastcfd.paths as fastcfd_paths
import fromcad2cfd_fastcfd.fastfluent_backend as fastfluent_backend
from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fastcfd.capabilities import capability_inventory, capability_markdown
from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.fastfluent_backend import (
    run_fastfluent_cavity2d_job,
    run_fastfluent_job,
    write_cavity2d_job,
    write_channel2d_job,
    write_obstacle2d_job,
)
from fromcad2cfd_fastcfd.field_qoi import analyze_fastfluent_fields, read_vti_image_data
from fromcad2cfd_fastcfd.lattice_trust import analyze_lattice_domain
from fromcad2cfd_fastcfd.mock_runner import demo_cavity2d_job, run_mock_job, write_demo_job
from fromcad2cfd_fastcfd.native_summary import (
    NATIVE_CONVERGENCE_FILENAME,
    NATIVE_SUMMARY_FILENAME,
    read_native_convergence,
    read_native_summary,
)
from fromcad2cfd_fastcfd.pilot_decision import build_pilot_decision
from fromcad2cfd_fastcfd.physics_validator import validate_physics
from fromcad2cfd_fastcfd.preflight import detect_fastcfd_environment, run_preflight
from fromcad2cfd_fastcfd.registry import registry_inventory, registry_markdown
from fromcad2cfd_fastcfd.scene_compiler import compile_scene_file_to_job, default_scene, validate_scene_semantics, write_scene
from fromcad2cfd_fastcfd.schemas import FastCFDJob, FastCFDScene, read_job


def _vtk_binary_f64(values):
    payload = struct.pack("<" + "d" * len(values), *values)
    return base64.b64encode(struct.pack("<I", len(payload))).decode("ascii") + base64.b64encode(payload).decode("ascii")


def _vtk_binary_u8(values):
    payload = bytes(values)
    return base64.b64encode(struct.pack("<I", len(payload))).decode("ascii") + base64.b64encode(payload).decode("ascii")


def _write_test_vti_pair(vtk_dir: Path, stem: str = "channel2d", step: int = 50, nx: int = 6, ny: int = 4) -> tuple[Path, Path]:
    vtk_dir.mkdir(parents=True, exist_ok=True)
    point_count = nx * ny
    rho = [1.0 + 0.001 * (index % nx) for index in range(point_count)]
    velocity = []
    flags = []
    for iy in range(ny):
        for ix in range(nx):
            velocity.extend([0.01 + 0.002 * ix, 0.001 * (iy - ny / 2)])
            flags.append(4 if iy in {0, ny - 1} else 2)
    field_path = vtk_dir / f"{stem}_T{step}_B0.vti"
    flag_path = vtk_dir / "GeoFlag_B0.vti"
    extent = f"0 {nx - 1} 0 {ny - 1} 0 0"
    field_path.write_text(
        f"""<?xml version=\"1.0\"?>
<VTKFile type=\"ImageData\" version=\"0.1\" byte_order=\"LittleEndian\">
<ImageData WholeExtent=\"{extent}\" Origin=\"-0.5 -0.5 0\" Spacing=\"1 1 1\">
<Piece Extent=\"{extent}\">
<PointData>
<DataArray type=\"Float64\" Name=\"Rho\" format=\"binary\" encoding=\"base64\" NumberOfComponents=\"1\">
{_vtk_binary_f64(rho)}
</DataArray>
<DataArray type=\"Float64\" Name=\"Velocity\" format=\"binary\" encoding=\"base64\" NumberOfComponents=\"2\">
{_vtk_binary_f64(velocity)}
</DataArray>
</PointData>
</Piece>
</ImageData>
</VTKFile>
""",
        encoding="utf-8",
    )
    flag_path.write_text(
        f"""<?xml version=\"1.0\"?>
<VTKFile type=\"ImageData\" version=\"0.1\" byte_order=\"LittleEndian\">
<ImageData WholeExtent=\"{extent}\" Origin=\"-0.5 -0.5 0\" Spacing=\"1 1 1\">
<Piece Extent=\"{extent}\">
<PointData>
<DataArray type=\"UInt8\" Name=\"flag\" format=\"binary\" encoding=\"base64\" NumberOfComponents=\"1\">
{_vtk_binary_u8(flags)}
</DataArray>
</PointData>
</Piece>
</ImageData>
</VTKFile>
""",
        encoding="utf-8",
    )
    (vtk_dir / f"{stem}{step}.vtm").write_text("<VTKFile></VTKFile>", encoding="utf-8")
    return field_path, flag_path


def _write_native_summary(output_dir: Path, case_type: str = "channel2d", field_prefix: str = "channel2d") -> Path:
    path = output_dir / NATIVE_SUMMARY_FILENAME
    path.write_text(
        json.dumps(
            {
                "schema_version": "fromcad2cfd_fastfluent_native_summary_v1",
                "case_type": case_type,
                "executable_role": "fastfluent_example",
                "completed_steps": 100,
                "requested_total_steps": 100,
                "output_interval": 50,
                "final_residual": 0.125,
                "physical_time_s": 1.25,
                "field_prefix": field_prefix,
                "grid": {"nx": 6, "ny": 4, "cell_length_mm": 1.0},
                "physical_properties": {"rho_ref_g_per_mm3": 1.0e-9, "kinematic_viscosity_mm2_s": 1.0},
                "boundary_conditions": {"reference_velocity_mm_s": 0.03},
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_native_convergence(output_dir: Path) -> Path:
    path = output_dir / NATIVE_CONVERGENCE_FILENAME
    path.write_text("step,residual\n50,0.25\n100,0.125\n", encoding="utf-8")
    return path


def test_fastcfd_job_round_trips(tmp_path):
    job = demo_cavity2d_job(tmp_path / "output", model_name="unit_fastcfd")
    job_path = tmp_path / "job.json"
    job.write(job_path)

    loaded = read_job(job_path)

    assert loaded.case_type == "cavity2d"
    assert loaded.backend == "mock"
    assert loaded.model_name == "unit_fastcfd"
    assert loaded.dimensions["nx"] == 30


def test_fastcfd_job_rejects_unknown_case(tmp_path):
    job = demo_cavity2d_job(tmp_path / "output")
    payload = job.to_dict()
    payload["case_type"] = "arbitrary_cpp_case"
    job_path = tmp_path / "bad_job.json"
    job_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported FastCFD case_type"):
        read_job(job_path)


def test_fastcfd_schema_rejects_dangerous_keys(tmp_path):
    job = demo_cavity2d_job(tmp_path / "output")
    payload = job.to_dict()
    payload["metadata"]["command"] = "g++ unsafe.cpp"
    job_path = tmp_path / "bad_job.json"
    job_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Dangerous FastCFD schema key"):
        read_job(job_path)


def test_fastcfd_scene_validates_minimal_semantics():
    scene = FastCFDScene(
        scene_type="cavity2d",
        units={"length": "mm"},
        geometry={"kind": "rectangle", "width_mm": 30, "height_mm": 30},
        zones=[{"name": "fluid", "role": "fluid_domain"}],
        physics_intent={"flow_regime": "pilot"},
    )

    scene.validate()


def test_fastcfd_capability_registry_blocks_arbitrary_cases():
    inventory = capability_inventory()

    assert "cavity2d" in inventory["allowed_case_templates"]
    assert inventory["validation_gates"]["physics_passport"]["status"] == "implemented"
    assert "arbitrary_cpp_generation" in inventory["disabled_capabilities"]
    assert "arbitrary_fastfluent_case_path" in inventory["disabled_capabilities"]
    assert "cavity2d" in capability_markdown()
    assert "physics_passport" in capability_markdown()


def test_fastcfd_registry_is_source_of_truth():
    registry = registry_inventory()

    assert registry["schema"] == "fromcad2cfd_fastcfd_registry_v1"
    assert registry["cases"]["cavity2d"]["supported_backends"] == ["mock", "fastfluent"]
    assert registry["cases"]["channel2d"]["supported_backends"] == ["mock", "fastfluent"]
    assert registry["cases"]["obstacle2d"]["status"] == "mock_ready_real_backend_supported"
    assert registry["cases"]["obstacle2d"]["real_backend"] == "fastfluent"
    assert registry["boundary_types"]["obstacle_wall"]["semantic_zone"] == "wall"
    assert "FastCFD Registry" in registry_markdown()


def test_fastcfd_vti_binary_parser_decodes_velocity(tmp_path):
    field_path, flag_path = _write_test_vti_pair(tmp_path / "vtkoutput" / "vtidata")

    field_grid = read_vti_image_data(field_path)
    flag_grid = read_vti_image_data(flag_path)

    assert field_grid.nx == 6
    assert field_grid.ny == 4
    assert field_grid.arrays["Velocity"].components == 2
    assert field_grid.arrays["Velocity"].values[0] == pytest.approx(0.01)
    assert field_grid.arrays["Rho"].values[1] == pytest.approx(1.001)
    assert flag_grid.arrays["flag"].values[0] == 4


def test_fastcfd_field_qoi_extracts_channel_metrics(tmp_path):
    output_dir = tmp_path / "output"
    _write_test_vti_pair(output_dir / "vtkoutput" / "vtidata", stem="channel2d", step=100)
    job = FastCFDJob(
        case_type="channel2d",
        backend="fastfluent",
        output_dir=str(output_dir),
        model_name="unit_field_qoi",
        dimensions={"nx": 6, "ny": 4, "cell_length_mm": 1.0},
        physical_properties={"rho_ref_g_per_mm3": 1.0e-9, "kinematic_viscosity_mm2_s": 1.0},
        boundary_conditions={"inlet_velocity_mm_s": 0.03, "outlet": {"type": "pressure"}},
        solver_settings={"total_steps": 100, "output_interval": 50},
    )

    analysis = analyze_fastfluent_fields(output_dir, job)

    assert analysis["status"] == "parsed"
    assert analysis["selected_step"] == 100
    assert analysis["metrics"]["speed_summary"]["count"] > 0
    assert analysis["metrics"]["outlet_velocity_spread"]["spread_ratio"] is not None
    assert analysis["fluent_hint_inputs"]["outlet_spread_ratio"] is not None


def test_fastcfd_native_summary_parser_reads_run_contract(tmp_path):
    _write_native_summary(tmp_path, case_type="channel2d", field_prefix="cavblock2d")

    summary = read_native_summary(tmp_path)

    assert summary["status"] == "parsed"
    assert summary["metrics"]["case_type"] == "channel2d"
    assert summary["metrics"]["completed_steps"] == 100
    assert summary["metrics"]["grid"]["nx"] == 6
    assert summary["metrics"]["field_prefix"] == "cavblock2d"


def test_fastcfd_native_convergence_parser_reads_residual_history(tmp_path):
    _write_native_convergence(tmp_path)

    convergence = read_native_convergence(tmp_path)

    assert convergence["status"] == "parsed"
    assert convergence["metrics"]["sample_count"] == 2
    assert convergence["metrics"]["first_step"] == 50
    assert convergence["metrics"]["last_step"] == 100
    assert convergence["metrics"]["final_residual"] == pytest.approx(0.125)
    assert convergence["metrics"]["reduction_ratio"] == pytest.approx(0.5)


def test_fastcfd_lattice_domain_summary_scores_obstacle_recipe(tmp_path):
    job = FastCFDJob(
        case_type="obstacle2d",
        backend="mock",
        output_dir=str(tmp_path / "output"),
        model_name="unit_lattice_obstacle",
        units={"length": "mm", "time": "s", "density": "g/mm^3", "kinematic_viscosity": "mm^2/s"},
        dimensions={"nx": 120, "ny": 40, "cell_length_mm": 1.0, "obstacles": [{"name": "obstacle_01", "type": "circle", "center_mm": [42.0, 20.0], "radius_mm": 4.0}]},
        physical_properties={"rho_ref_g_per_mm3": 0.001, "kinematic_viscosity_mm2_s": 0.02},
        boundary_conditions={"inlet_velocity_mm_s": 0.03, "outlet": {"type": "pressure"}},
        solver_settings={"total_steps": 100, "output_interval": 50, "relaxation_time": 0.56, "thread_num": 1},
        metadata={"domain": {"type": "channel2d", "length_mm": 120.0, "height_mm": 40.0}},
    )

    summary = analyze_lattice_domain(job)

    assert summary["schema_version"] == "fromcad2cfd_lattice_domain_summary_v1"
    assert summary["status"] in {"passed", "warning"}
    assert summary["zone_counts"]["total_cells"] == 4800
    assert summary["zone_counts"]["obstacle_solid_cells"] > 0
    assert summary["resolution"]["obstacle_resolution"]["min_size_cells"] == pytest.approx(8.0)
    assert 0.0 <= summary["trust_score"] <= 1.0


def test_fastcfd_pilot_decision_flags_increasing_residual(tmp_path):
    job = demo_cavity2d_job(tmp_path / "output")
    lattice = analyze_lattice_domain(job)
    decision = build_pilot_decision(
        job=job,
        lattice_summary=lattice,
        field_analysis={"status": "parsed", "metrics": {}, "fluent_hint_inputs": {}},
        native_convergence={
            "status": "parsed",
            "path": str(tmp_path / "fastfluent_native_convergence.csv"),
            "metrics": {"reduction_ratio": 1.2, "nonincreasing_fraction": 0.0},
        },
        artifact_refs={"lattice_domain_summary": "lattice_domain_summary.json", "native_convergence": "fastfluent_native_convergence.csv"},
    )

    assert decision["schema_version"] == "fromcad2cfd_pilot_decision_v1"
    assert decision["status"] == "extend_pilot_before_handoff"
    assert decision["confidence"] in {"low", "medium"}
    assert any(action["action"] == "extend_or_recondition_pilot_run" for action in decision["recommended_actions"])


def test_fastcfd_preflight_gracefully_skips_missing_root(tmp_path):
    missing = tmp_path / "missing_source"
    report = detect_fastcfd_environment(str(missing))
    result = run_preflight(str(missing)).to_dict()

    assert report.status == "skipped"
    assert result["status"] == "skipped"
    assert "capabilities" in result["outputs"]


def test_fastcfd_write_demo_job_and_mock_runner(tmp_path, monkeypatch):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)

    written = write_demo_job(project="unit_fastcfd", model_name="unit_mock")
    result = run_mock_job(written["job_path"])
    artifacts = result["outputs"]["artifacts"]

    assert result["status"] == "success"
    assert Path(written["job_path"]).exists()
    for key in [
        "generated_ini",
        "convergence_csv",
        "physics_contract",
        "lattice_domain_summary",
        "qoi",
        "flow_fingerprint",
        "pilot_decision",
        "fluent_hints",
        "claim_ledger",
        "result_manifest",
        "fastcfd_report_json",
        "fastcfd_report_markdown",
    ]:
        assert key in artifacts
        assert Path(artifacts[key]).exists()
    qoi = json.loads(Path(artifacts["qoi"]).read_text(encoding="utf-8"))
    assert qoi["metrics"]["final_residual"] == 0.00830784
    assert qoi["metrics"]["lattice_domain_status"] == "passed"
    assert qoi["metrics"]["pilot_decision_status"] == "insufficient_evidence"
    contract = json.loads(Path(artifacts["physics_contract"]).read_text(encoding="utf-8"))
    assert contract["status"] == "passed"
    assert contract["checks"]["mach_lattice_estimate"] < 0.08
    hints = json.loads(Path(artifacts["fluent_hints"]).read_text(encoding="utf-8"))
    assert all("evidence" in hint for hint in hints["hints"])


def test_fastcfd_physics_validator_pass_warning_and_fail(tmp_path):
    valid = demo_cavity2d_job(tmp_path / "valid")
    passed = validate_physics(valid)

    assert passed.status == "passed"
    assert passed.checks["reynolds_number"] > 0
    assert passed.checks["omega"] == pytest.approx(1 / 0.56)

    warning_payload = json.loads(json.dumps(valid.to_dict()))
    warning_payload["solver_settings"]["relaxation_time"] = 0.53
    warning_job = FastCFDJob(
        case_type=warning_payload["case_type"],
        backend=warning_payload["backend"],
        output_dir=warning_payload["output_dir"],
        model_name="warning_job",
        units=warning_payload["units"],
        dimensions=warning_payload["dimensions"],
        physical_properties=warning_payload["physical_properties"],
        boundary_conditions=warning_payload["boundary_conditions"],
        solver_settings=warning_payload["solver_settings"],
        metadata=warning_payload["metadata"],
    )
    warned = validate_physics(warning_job)

    assert warned.status == "warning"
    assert warned.checks["stability_band"] == "accepted_with_warning"

    failed_payload = json.loads(json.dumps(valid.to_dict()))
    failed_payload["boundary_conditions"]["moving_wall_velocity_mm_s"] = 0.2
    failed_job = FastCFDJob(
        case_type=failed_payload["case_type"],
        backend=failed_payload["backend"],
        output_dir=failed_payload["output_dir"],
        model_name="failed_job",
        units=failed_payload["units"],
        dimensions=failed_payload["dimensions"],
        physical_properties=failed_payload["physical_properties"],
        boundary_conditions=failed_payload["boundary_conditions"],
        solver_settings=failed_payload["solver_settings"],
        metadata=failed_payload["metadata"],
    )
    failed = validate_physics(failed_job)

    assert failed.status == "failed"
    assert any("Mach" in error for error in failed.checks["errors"])


def test_fastcfd_validate_job_cli_blocks_bad_physics(tmp_path, capsys):
    job = demo_cavity2d_job(tmp_path / "bad_cli")
    payload = job.to_dict()
    payload["solver_settings"]["relaxation_time"] = 0.51
    job_path = tmp_path / "bad_cli_job.json"
    job_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    assert fastcfd_main(["validate-job", "--job-file", str(job_path)]) == 2
    output = json.loads(capsys.readouterr().out)

    assert output["status"] == "failed"
    assert output["checks"]["stability_band"] == "rejected"


def test_fastcfd_write_real_cavity2d_job(tmp_path, monkeypatch):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)

    written = write_cavity2d_job(project="unit_real", model_name="unit_real", nx=24, ny=12, total_steps=100, output_interval=25)
    payload = json.loads(Path(written["job_path"]).read_text(encoding="utf-8"))

    assert payload["backend"] == "fastfluent"
    assert payload["case_type"] == "cavity2d"
    assert payload["dimensions"]["nx"] == 24
    assert payload["solver_settings"]["output_interval"] == 25


def test_fastcfd_write_real_channel_and_obstacle_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)

    channel = write_channel2d_job(project="unit_channel", model_name="unit_channel", total_steps=100, output_interval=25)
    obstacle = write_obstacle2d_job(
        project="unit_obstacle",
        model_name="unit_obstacle",
        obstacle="rectangle",
        total_steps=100,
        output_interval=25,
    )
    channel_payload = json.loads(Path(channel["job_path"]).read_text(encoding="utf-8"))
    obstacle_payload = json.loads(Path(obstacle["job_path"]).read_text(encoding="utf-8"))

    assert channel_payload["backend"] == "fastfluent"
    assert channel_payload["case_type"] == "channel2d"
    assert channel_payload["boundary_conditions"]["inlet_velocity_mm_s"] == pytest.approx(0.03)
    assert obstacle_payload["backend"] == "fastfluent"
    assert obstacle_payload["case_type"] == "obstacle2d"
    assert obstacle_payload["dimensions"]["obstacles"][0]["type"] == "rectangle"


def test_fastcfd_real_backend_contract_with_mocked_subprocess(tmp_path, monkeypatch):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)
    written = write_cavity2d_job(project="unit_real_run", model_name="unit_real_run")
    source_root = tmp_path / "fastfluent"
    example_dir = source_root / "examples" / "cavity2d"
    example_dir.mkdir(parents=True)
    (source_root / "src").mkdir()
    (example_dir / "cavity2d.exe").write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(fastfluent_backend, "_build_cavity2d", lambda source, timeout_sec: (True, {"returncode": 0}))

    class Completed:
        returncode = 0
        stdout = "[Step: 50]  MLUPs: 10.24  Res: 0.1\nAverage_MLUPs: 8.90435\nTime Elapsed:  0.023 s\n"
        stderr = ""

    def fake_run(argv, cwd, capture_output, text, timeout, check):
        vtk_dir = Path(cwd) / "vtkoutput" / "vtidata"
        vtk_dir.mkdir(parents=True)
        (vtk_dir / "cavity2d50.vtm").write_text("<VTKFile></VTKFile>", encoding="utf-8")
        return Completed()

    monkeypatch.setattr(fastfluent_backend.subprocess, "run", fake_run)

    result = run_fastfluent_cavity2d_job(written["job_path"], source_root=source_root)
    artifacts = result["outputs"]["artifacts"]

    assert result["status"] == "success"
    assert result["outputs"]["field_output_count"] == 1
    assert Path(artifacts["generated_ini"]).name == "cavity2d.ini"
    assert Path(artifacts["qoi"]).exists()
    qoi = json.loads(Path(artifacts["qoi"]).read_text(encoding="utf-8"))
    assert qoi["metrics"]["average_mlups"] == 8.90435


def test_fastcfd_real_channel2d_backend_contract_with_mocked_subprocess(tmp_path, monkeypatch):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)
    written = write_channel2d_job(project="unit_channel_run", model_name="unit_channel_run", total_steps=100, output_interval=50)
    source_root = tmp_path / "fastfluent"
    example_dir = source_root / "examples" / "openboundary2d"
    example_dir.mkdir(parents=True)
    (source_root / "src").mkdir()
    (example_dir / "openbd2d.exe").write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(fastfluent_backend, "_build_openboundary2d", lambda source, timeout_sec: (True, {"returncode": 0}))

    class Completed:
        returncode = 0
        stdout = "[Step: 50]  MLUPs: 10.24  Res: 0.1\nTotal Step:    100\nAverage_MLUPs: 7.5\nTime Elapsed:  0.02 s\n"
        stderr = ""

    def fake_run(argv, cwd, capture_output, text, timeout, check):
        vtk_dir = Path(cwd) / "vtkoutput" / "vtidata"
        _write_test_vti_pair(vtk_dir, stem="channel2d", step=50)
        _write_native_summary(Path(cwd), case_type="channel2d", field_prefix="cavblock2d")
        _write_native_convergence(Path(cwd))
        return Completed()

    monkeypatch.setattr(fastfluent_backend.subprocess, "run", fake_run)

    result = run_fastfluent_job(written["job_path"], source_root=source_root)
    artifacts = result["outputs"]["artifacts"]

    assert result["status"] == "success"
    assert result["outputs"]["field_output_count"] == 3
    assert Path(artifacts["generated_ini"]).name == "openbd2dparam.ini"
    assert Path(artifacts["field_qoi"]).exists()
    assert Path(artifacts["flow_fingerprint"]).exists()
    assert Path(artifacts["lattice_domain_summary"]).exists()
    assert Path(artifacts["pilot_decision"]).exists()
    assert Path(artifacts["native_summary"]).exists()
    assert Path(artifacts["native_convergence"]).exists()
    qoi = json.loads(Path(artifacts["qoi"]).read_text(encoding="utf-8"))
    assert qoi["metrics"]["average_mlups"] == 7.5
    assert qoi["metrics"]["reference_velocity_mm_s"] == pytest.approx(0.03)
    assert qoi["metrics"]["field_parser_status"] == "parsed"
    assert qoi["metrics"]["native_summary_status"] == "parsed"
    assert qoi["metrics"]["native_completed_steps"] == 100
    assert qoi["metrics"]["native_convergence_status"] == "parsed"
    assert qoi["metrics"]["native_convergence_final_residual"] == pytest.approx(0.125)
    assert qoi["metrics"]["lattice_domain_status"] == "passed"
    assert qoi["metrics"]["pilot_decision_status"] in {"proceed_with_advisory_handoff", "review_domain_extent"}


def test_fastcfd_real_obstacle2d_backend_contract_with_mocked_subprocess(tmp_path, monkeypatch):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)
    written = write_obstacle2d_job(project="unit_obstacle_run", model_name="unit_obstacle_run", total_steps=100, output_interval=50)
    source_root = tmp_path / "fastfluent"
    (source_root / "src").mkdir(parents=True)
    generated_source = tmp_path / "generated" / "obstacle2d.cpp"
    generated_source.parent.mkdir()
    generated_source.write_text("placeholder", encoding="utf-8")
    exe = generated_source.with_suffix(".exe")
    exe.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(
        fastfluent_backend,
        "_build_generated_obstacle2d",
        lambda source, output_dir, job, timeout_sec: (
            True,
            {"returncode": 0, "generated_source": str(generated_source), "executable": str(exe), "obstacle_summary": {"type": "circle"}},
        ),
    )

    class Completed:
        returncode = 0
        stdout = "Obstacle cells: 69\n[Step: 50]  MLUPs: 10.24  Res: 0.1\nTotal Step:    100\nAverage_MLUPs: 6.25\nTime Elapsed:  0.03 s\n"
        stderr = ""

    def fake_run(argv, cwd, capture_output, text, timeout, check):
        vtk_dir = Path(cwd) / "vtkoutput" / "vtidata"
        vtk_dir.mkdir(parents=True)
        (vtk_dir / "obstacle2d50.vtm").write_text("<VTKFile></VTKFile>", encoding="utf-8")
        _write_native_summary(Path(cwd), case_type="obstacle2d", field_prefix="obstacle2d")
        _write_native_convergence(Path(cwd))
        return Completed()

    monkeypatch.setattr(fastfluent_backend.subprocess, "run", fake_run)

    result = run_fastfluent_job(written["job_path"], source_root=source_root)
    artifacts = result["outputs"]["artifacts"]

    assert result["status"] == "success"
    assert Path(artifacts["generated_ini"]).name == "obstacle2dparam.ini"
    assert Path(artifacts["generated_source"]).exists()
    assert Path(artifacts["lattice_domain_summary"]).exists()
    assert Path(artifacts["pilot_decision"]).exists()
    assert Path(artifacts["native_summary"]).exists()
    assert Path(artifacts["native_convergence"]).exists()
    assert Path(artifacts["obstacle_summary"]).exists()
    qoi = json.loads(Path(artifacts["qoi"]).read_text(encoding="utf-8"))
    assert qoi["metrics"]["average_mlups"] == 6.25
    assert qoi["metrics"]["obstacle"]["type"] == "circle"
    assert qoi["metrics"]["native_summary_status"] == "parsed"
    assert qoi["metrics"]["native_convergence_status"] == "parsed"


def test_fastcfd_scene_write_validate_compile_and_mock_run(tmp_path, monkeypatch):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)

    scene_result = write_scene(
        project="unit_scene",
        model_name="unit_obstacle_scene",
        scene_type="obstacle2d",
        length_mm=120,
        height_mm=40,
        cell_length_mm=1,
        obstacle="circle",
    )
    scene_path = Path(scene_result["scene_path"])
    compile_result = compile_scene_file_to_job(
        scene_path,
        project="unit_scene",
        model_name="unit_obstacle_job",
        backend="mock",
    )
    job = read_job(compile_result["job_path"])
    run_result = run_mock_job(compile_result["job_path"])

    assert scene_result["validation"]["status"] == "passed"
    assert compile_result["scene_validation"]["status"] == "passed"
    assert compile_result["physics_contract"]["status"] == "passed"
    assert job.case_type == "obstacle2d"
    assert job.boundary_conditions["inlet_velocity_mm_s"] == pytest.approx(0.03)
    assert job.dimensions["nx"] == 120
    assert job.dimensions["ny"] == 40
    assert job.dimensions["obstacles"][0]["type"] == "circle"
    assert run_result["status"] == "success"
    assert Path(run_result["outputs"]["artifacts"]["physics_contract"]).exists()


def test_fastcfd_scene_semantics_blocks_invalid_obstacle():
    scene = default_scene(scene_type="obstacle2d", model_name="bad_obstacle")
    scene.geometry["obstacles"][0]["center_mm"] = [1.0, 20.0]

    report = validate_scene_semantics(scene)

    assert report["status"] == "failed"
    assert any("inlet/outlet" in error for error in report["errors"])


def test_fastcfd_real_backend_physics_block_stops_before_build(tmp_path, monkeypatch):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)
    written = write_cavity2d_job(project="unit_real_blocked", model_name="unit_real_blocked")
    job_path = Path(written["job_path"])
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    payload["solver_settings"]["relaxation_time"] = 0.51
    job_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def unexpected_build(source, timeout_sec):
        raise AssertionError("real backend build should not run after physics validation failure")

    monkeypatch.setattr(fastfluent_backend, "_build_cavity2d", unexpected_build)

    result = run_fastfluent_cavity2d_job(job_path, source_root=tmp_path / "fastfluent")
    artifacts = result["outputs"]["artifacts"]

    assert result["status"] == "partial"
    assert "physics validation blocked" in result["message"]
    assert Path(artifacts["physics_contract"]).exists()


def test_fastcfd_cli_foundation_commands(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)

    assert fastcfd_main(["capabilities"]) == 0
    assert "cavity2d" in capsys.readouterr().out
    assert fastcfd_main(["preflight", "--source-root", str(tmp_path / "missing")]) == 0
    assert "skipped" in capsys.readouterr().out
    assert fastcfd_main(["mock-demo", "--project", "unit_cli", "--model-name", "unit_cli_model"]) == 0
    assert "FastCFD deterministic mock run completed" in capsys.readouterr().out
    assert fastcfd_main(["registry", "--format", "markdown"]) == 0
    assert "FastCFD Registry" in capsys.readouterr().out


def test_fastcfd_cli_scene_commands(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fastcfd_paths, "PROJECTS_ROOT", tmp_path)

    assert fastcfd_main(
        [
            "write-scene",
            "--project",
            "unit_cli_scene",
            "--model-name",
            "unit_cli_obstacle",
            "--scene-type",
            "obstacle2d",
            "--obstacle",
            "rectangle",
        ]
    ) == 0
    scene_result = json.loads(capsys.readouterr().out)
    scene_path = scene_result["scene_path"]

    assert fastcfd_main(["validate-scene", "--scene-file", scene_path]) == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["status"] == "passed"

    assert fastcfd_main(
        [
            "compile-scene",
            "--scene-file",
            scene_path,
            "--project",
            "unit_cli_scene",
            "--model-name",
            "unit_cli_obstacle_job",
        ]
    ) == 0
    compiled = json.loads(capsys.readouterr().out)
    assert Path(compiled["job_path"]).exists()
    assert compiled["job"]["case_type"] == "obstacle2d"


def test_root_cli_routes_fastcfd(capsys):
    assert root_main(["fastcfd", "capabilities", "--format", "markdown"]) == 0
    assert "FastCFD Capability Inventory" in capsys.readouterr().out
