from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.result_pack import compile_native_result_pack, validate_result_pack
from fromcad2cfd_fastcfd.transport_core import (
    demo_transport_case,
    run_transport_coupling_case,
    run_transport_coupling_demo,
    validate_transport_case,
)


def test_s6_demo_transport_case_validates_alpha():
    case = demo_transport_case(quantity="alpha")
    validation = validate_transport_case(case)

    assert case["schema_version"] == "fastfluent_transport_case_v1"
    assert case["field"]["name"] == "alpha"
    assert validation["passed"]


def test_s6_alpha_transport_writes_result_packable_artifacts(tmp_path):
    result = run_transport_coupling_demo(tmp_path / "alpha", quantity="alpha")

    assert result["status"] == "success"
    assert result["quality_status"] == "passed"
    artifacts = result["outputs"]["artifacts"]
    assert Path(artifacts["transport_qoi"]).exists()
    assert Path(artifacts["transport_solution_vtu"]).exists()
    assert Path(artifacts["transport_status"]).exists()
    qoi = result["outputs"]["qoi"]
    assert qoi["field"]["quantity"] == "volume_fraction"
    assert qoi["acceptance"]["declared_bounds_respected"] is True
    assert qoi["metrics"]["relative_balance_error"] < 1.0e-8

    pack = compile_native_result_pack(artifacts["transport_status"], output_dir=tmp_path / "pack")
    validation = validate_result_pack(tmp_path / "pack")

    assert pack["status"] == "advisory_native_evidence"
    assert pack["native_result"]["result_kind"] == "unified_transport_coupling"
    assert pack["usage_boundary"]["valid_for_screening_decision"] is True
    assert validation["passed"]


def test_s6_temperature_transport_evaluates_material_coupling(tmp_path):
    result = run_transport_coupling_demo(tmp_path / "temperature", quantity="temperature")

    assert result["status"] == "success"
    qoi = result["outputs"]["qoi"]
    assert qoi["field"]["quantity"] == "temperature"
    assert qoi["material_couplings"]["property_count"] == 1
    prop = qoi["material_couplings"]["properties"][0]
    assert prop["property"] == "dynamic_viscosity_Pa_s"
    assert prop["max"] > prop["min"] > 0


def test_s6_transport_blocks_unstable_time_step(tmp_path):
    case = demo_transport_case(quantity="alpha")
    case["time_step_s"] = 10.0

    result = run_transport_coupling_case(case, output_dir=tmp_path / "unstable")

    assert result["status"] == "failed"
    assert result["quality_status"] == "failed"
    assert any("Courant" in item for item in result["blocking_errors"])


def test_s6_transport_cli_routes_and_compile_native(tmp_path, capsys):
    case_file = tmp_path / "case.json"
    run_dir = tmp_path / "run"
    pack_dir = tmp_path / "pack"

    write_exit = fastcfd_main(["transport", "write-demo", "--case-file", str(case_file), "--quantity", "species", "--format", "json"])
    write_payload = json.loads(capsys.readouterr().out)
    validate_exit = fastcfd_main(["transport", "validate", str(case_file), "--format", "json"])
    validate_payload = json.loads(capsys.readouterr().out)
    run_exit = fastcfd_main(["transport", "run", str(case_file), "--output-dir", str(run_dir), "--format", "json"])
    run_payload = json.loads(capsys.readouterr().out)
    pack_exit = fastcfd_main(["result-pack", "compile-native", str(run_dir / "status.json"), "--output-dir", str(pack_dir), "--format", "json"])
    pack_payload = json.loads(capsys.readouterr().out)

    assert write_exit == 0
    assert write_payload["case"]["field"]["quantity"] == "species"
    assert validate_exit == 0
    assert validate_payload["passed"]
    assert run_exit == 0
    assert run_payload["quality_status"] == "passed"
    assert pack_exit == 0
    assert pack_payload["native_result"]["result_kind"] == "unified_transport_coupling"
