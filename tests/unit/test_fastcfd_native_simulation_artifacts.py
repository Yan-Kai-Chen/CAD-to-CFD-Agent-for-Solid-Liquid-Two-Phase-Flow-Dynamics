from __future__ import annotations

import json

from fromcad2cfd_fastcfd.native_simulation_artifacts import (
    NATIVE_SIMULATION_RESULT_SCHEMA_VERSION,
    build_native_simulation_result,
    validate_native_simulation_result,
    write_native_simulation_result,
)


def test_native_simulation_result_contract_accepts_complete_payload(tmp_path):
    payload = build_native_simulation_result(
        case_id="demo_case",
        case_name="Demo Case",
        module="unit",
        backend="unstructured_fvm",
        backend_status="available",
        status="pass",
        qoi_summary={"metrics": {"l2_error": 0.0}},
        field_outputs=[{"path": str(tmp_path / "field_output.vtu"), "kind": "vtu"}],
        warnings=[],
        blocking_errors=[],
    )

    validation = validate_native_simulation_result(payload)

    assert validation.passed
    assert payload["schema_version"] == NATIVE_SIMULATION_RESULT_SCHEMA_VERSION
    assert isinstance(payload["qoi_summary"], dict)
    assert isinstance(payload["field_outputs"], list)
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["blocking_errors"], list)


def test_native_simulation_result_records_unavailable_backend(tmp_path):
    payload = build_native_simulation_result(
        case_id="structured_backend",
        case_name="Structured Backend",
        module="structured_cases",
        backend="structured_lbm",
        backend_status="unavailable",
        status="unavailable",
        warnings=["backend unavailable"],
        limitations=["no fake output"],
    )
    path = write_native_simulation_result(payload, tmp_path / "simulation_result.json")
    loaded = json.loads(path.read_text(encoding="utf-8"))

    assert loaded["status"] == "unavailable"
    assert loaded["backend_status"] == "unavailable"
    assert loaded["field_outputs"] == []


def test_native_simulation_result_rejects_dangerous_key_names():
    payload = build_native_simulation_result(
        case_id="safe_case",
        case_name="Safe Case",
        module="unit",
        backend="unstructured_fvm",
        backend_status="available",
        status="pass",
    )
    payload["metadata"]["raw_pyfluent"] = "blocked"

    validation = validate_native_simulation_result(payload)

    assert not validation.passed
    assert any("Dangerous key names" in error for error in validation.errors)
