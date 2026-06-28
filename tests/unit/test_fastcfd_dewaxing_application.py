from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.core.case_spec import validate_case_spec
from fromcad2cfd_fastcfd.dewaxing_application import (
    create_dewaxing_application_case,
    run_dewaxing_application_public_demo,
)


def test_dewaxing_application_case_is_valid_public_safe_casespec():
    case = create_dewaxing_application_case()
    validation = validate_case_spec(case)

    assert validation.status == "passed"
    assert case["case_type"] == "thermal.dewaxing"
    assert case["metadata"]["new_fluent_calculation"] is False
    assert "full_melt_time_s" in case["qoi_targets"]


def test_dewaxing_application_demo_links_fastfluent_to_existing_result_pack(tmp_path):
    result = run_dewaxing_application_public_demo(tmp_path / "app")

    assert result["schema_version"] == "fastfluent_dewaxing_application_bridge_v1"
    assert result["status"] == "success"
    assert result["route_selection"]["recommended_route"] == "dewaxing_native_application"
    assert result["route_plan"]["status"] == "ready_for_application"
    route_plan = json.loads(Path(result["artifacts"]["route_plan"]).read_text(encoding="utf-8"))
    assert route_plan["recommended_route"] == "dewaxing_native_application"
    assert Path(route_plan["artifacts"]["dewaxing_application_plan"]).exists()
    assert result["wax_h4_handoff"]["status"] in {"success", "partial"}
    assert result["fastfluent_native_dewaxing"]["quality_status"] == "passed"
    assert result["fastfluent_native_dewaxing"]["result_pack_status"] == "advisory_native_evidence"
    assert result["fastfluent_native_dewaxing"]["qoi"]["metrics"]["predicted_full_melt_time_s"] == 359.36
    assert result["dewaxing_result_pack_validation"]["status"] == "passed"
    assert result["agent_decision"]["fastfluent_application_continuity"] is True
    assert result["agent_decision"]["can_support_fastfluent_screening_decision"] is True
    assert result["agent_decision"]["can_support_native_dewaxing_reduced_order_decision"] is True
    assert result["agent_decision"]["can_support_new_fluent_calculation"] is False
    assert result["agent_decision"]["can_support_final_crack_probability"] is False
    assert result["execution_boundary"]["new_fluent_calculation"] is False
    assert result["execution_boundary"]["fastfluent_native_dewaxing_calculation"] is True
    assert result["execution_boundary"]["fastfluent_native_proxy_calculation"] is True

    native = result["fastfluent_native_proxy"]
    assert native["temperature"]["quality_status"] == "passed"
    assert native["wax_fraction"]["quality_status"] == "passed"
    assert native["temperature"]["result_pack_status"] == "advisory_native_evidence"
    assert native["wax_fraction"]["result_pack_status"] == "advisory_native_evidence"

    for key in ("application_manifest", "agent_decision", "agent_flow_report"):
        assert Path(result["artifacts"][key]).exists()


def test_dewaxing_application_cli_runs_public_demo(tmp_path, capsys):
    exit_code = fastcfd_main(["dewaxing-application-demo", "--output-dir", str(tmp_path / "cli"), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["dewaxing_result_pack_validation"]["status"] == "passed"
    assert payload["agent_decision"]["can_support_existing_fluent_result_review"] is True
