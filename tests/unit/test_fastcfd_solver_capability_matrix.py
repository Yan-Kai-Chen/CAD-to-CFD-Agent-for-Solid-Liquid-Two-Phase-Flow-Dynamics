from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.solver_capability_matrix import solver_capability_matrix, write_solver_capability_matrix


def test_solver_capability_matrix_lists_native_solver_routes():
    matrix = solver_capability_matrix()

    assert matrix["schema_version"] == "fastfluent_solver_capability_matrix_v1"
    ids = {item["id"] for item in matrix["capabilities"]}
    assert "unstructured_steady_incompressible" in ids
    assert "vof_lite_alpha_transport" in ids
    assert "standard_k_epsilon_channel" in ids
    assert "unified_transport_coupling_core" in ids
    assert "full_workflow_case_runner" in ids
    assert matrix["status_counts"]["bounded_native"] >= 6
    assert matrix["status_counts"]["implemented_s6"] == 1
    assert matrix["status_counts"]["implemented_s7"] == 1
    steady = next(item for item in matrix["capabilities"] if item["id"] == "unstructured_steady_incompressible")
    assert "hardening_summary" in steady["validation"]
    assert "passed_warning_failed_quality_status" in steady["validation"]
    assert steady["status"] == "hardened_s4"
    transport = next(item for item in matrix["capabilities"] if item["id"] == "unified_transport_coupling_core")
    assert "result_pack_compatibility" in transport["validation"]
    assert transport["status"] == "implemented_s6"
    workflow = next(item for item in matrix["capabilities"] if item["id"] == "full_workflow_case_runner")
    assert "stage_stop_on_failure" in workflow["validation"]
    assert workflow["status"] == "implemented_s7"


def test_solver_capability_matrix_writes_json_and_markdown(tmp_path):
    matrix = write_solver_capability_matrix(tmp_path / "matrix")

    assert Path(matrix["artifacts"]["solver_capability_matrix"]).exists()
    assert Path(matrix["artifacts"]["solver_capability_matrix_report"]).exists()
    payload = json.loads(Path(matrix["artifacts"]["solver_capability_matrix"]).read_text(encoding="utf-8"))
    assert payload["capability_count"] == matrix["capability_count"]


def test_solver_capability_matrix_cli_routes(tmp_path, capsys):
    exit_code = fastcfd_main(["solver-capability-matrix", "--output-dir", str(tmp_path / "matrix"), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["schema_version"] == "fastfluent_solver_capability_matrix_v1"
    assert Path(payload["artifacts"]["solver_capability_matrix_report"]).exists()
