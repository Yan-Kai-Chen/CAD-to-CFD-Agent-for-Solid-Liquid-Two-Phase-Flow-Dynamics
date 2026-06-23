from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.file_io import path_is_file, read_json_file
from fromcad2cfd_fastcfd.workflow_runner import run_workflow, run_workflow_demo


CASE_FILE = "examples/fastcfd/casespec_v3/channel_flow_case.json"


def test_s7_workflow_dry_run_compiles_review_only_result_pack(tmp_path):
    result = run_workflow(CASE_FILE, output_dir=tmp_path / "dry", mode="dry_run", mesh_mode="structured-demo")

    assert result["schema_version"] == "fastfluent_workflow_runner_v1"
    assert result["status"] == "review_only"
    assert result["case_id"] == "channel_flow_demo"
    assert [stage["stage"] for stage in result["stages"]] == [
        "flow_pack",
        "route_selection",
        "route_plan",
        "execution_gate",
        "controlled_runner",
        "result_pack",
    ]
    assert result["agent_decision"]["can_support_workflow_decision"] is True
    assert result["agent_decision"]["can_support_screening_decision"] is False
    assert Path(result["artifacts"]["workflow_manifest"]).exists()
    assert Path(result["artifacts"]["result_pack"]).exists()


def test_s7_workflow_native_advisory_runs_s6_and_compiles_native_result_pack(tmp_path):
    result = run_workflow(CASE_FILE, output_dir=tmp_path / "native", mode="native_advisory", mesh_mode="structured-demo")

    assert result["status"] == "native_advisory_complete"
    assert result["case_id"] == "channel_flow_demo"
    assert any(stage["stage"] == "native_advisory" for stage in result["stages"])
    assert result["result_pack"]["status"] == "advisory_native_evidence"
    assert result["result_pack"]["quality_status"] == "passed"
    assert result["agent_decision"]["can_support_screening_decision"] is True
    assert result["agent_decision"]["can_support_final_cfd_validation"] is False
    assert path_is_file(result["artifacts"]["native_result"])
    native_payload = read_json_file(result["artifacts"]["native_result"])
    assert native_payload["operation"] == "run_transport_coupling"


def test_s7_workflow_cli_demo_native_advisory(tmp_path, capsys):
    exit_code = fastcfd_main(["workflow", "demo", "--output-dir", str(tmp_path / "demo"), "--mode", "native_advisory", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "native_advisory_complete"
    assert payload["case_id"] == "channel_flow_demo"
    assert Path(payload["artifacts"]["workflow_report"]).exists()
    assert Path(payload["artifacts"]["result_pack"]).exists()


def test_s7_workflow_stops_on_invalid_casespec(tmp_path):
    bad_case = tmp_path / "bad_case.json"
    bad_case.write_text(json.dumps({"schema_version": "fastfluent_case_spec_v3", "case_id": "bad"}), encoding="utf-8")

    result = run_workflow(bad_case, output_dir=tmp_path / "bad", mode="native_advisory")

    assert result["status"] == "blocked"
    assert result["stages"][0]["stage"] == "flow_pack"
    assert result["agent_decision"]["can_support_workflow_decision"] is False
    assert "native_result" not in result["artifacts"]


def test_s7_workflow_demo_defaults_to_native_advisory(tmp_path):
    result = run_workflow_demo(tmp_path / "default_demo")

    assert result["status"] == "native_advisory_complete"
    assert result["mode"] == "native_advisory"


def test_s7_workflow_native_advisory_handles_deep_windows_paths(tmp_path):
    deep_root = tmp_path / ("deep_" + "x" * 40) / ("workflow_" + "y" * 40) / ("native_" + "z" * 40)

    result = run_workflow(CASE_FILE, output_dir=deep_root, mode="native_advisory", mesh_mode="structured-demo")

    assert result["status"] == "native_advisory_complete"
    assert result["case_id"] == "channel_flow_demo"
    assert result["agent_decision"]["can_support_screening_decision"] is True
    assert path_is_file(result["artifacts"]["workflow_manifest"])
    assert path_is_file(result["artifacts"]["native_result"])
    assert path_is_file(result["artifacts"]["result_pack"])
