from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.execution_gate import audit_execution_gate, run_execution_gate_demo, validate_execution_gate
from fromcad2cfd_fastcfd.route_plan import run_route_plan_demo


def test_execution_gate_audits_route_plan_without_execution(tmp_path):
    plan_demo = run_route_plan_demo(tmp_path / "plan_demo")
    route_plan = plan_demo["outputs"]["artifacts"]["route_plan"]

    gate = audit_execution_gate(route_plan, output_dir=tmp_path / "gate")

    assert gate["schema_version"] == "fastfluent_execution_gate_v1"
    assert gate["solver_execution"] == "not_attempted"
    assert gate["execution_mode"] == "dry_run"
    assert gate["execution_boundary"]["gate_executes_solver"] is False
    assert gate["job_audit"]["status"] == "passed"
    assert Path(gate["artifacts"]["runbook"]).exists()
    assert Path(gate["artifacts"]["dry_run_ledger"]).exists()


def test_execution_gate_validation_passes_for_demo_gate(tmp_path):
    plan_demo = run_route_plan_demo(tmp_path / "plan_demo")
    gate = audit_execution_gate(plan_demo["outputs"]["artifacts"]["route_plan"], output_dir=tmp_path / "gate")

    validation = validate_execution_gate(tmp_path / "gate")

    assert validation["passed"]
    assert validation["gate_status"] == gate["status"]
    assert validation["recommended_route"] == "native_fastfluent_structured"


def test_execution_gate_demo_writes_status(tmp_path):
    result = run_execution_gate_demo(tmp_path / "demo")

    assert result["operation"] == "execution_gate_demo"
    assert result["outputs"]["solver_execution"] == "not_attempted"
    assert Path(result["outputs"]["artifacts"]["execution_gate"]).exists()
    assert Path(result["outputs"]["artifacts"]["runbook"]).exists()


def test_execution_gate_cli_routes(tmp_path, capsys):
    demo_dir = tmp_path / "demo"
    audit_dir = tmp_path / "audit"

    demo_exit = fastcfd_main(["execution-gate", "demo", "--output-dir", str(demo_dir), "--format", "json"])
    demo_payload = json.loads(capsys.readouterr().out)
    audit_exit = fastcfd_main(
        [
            "execution-gate",
            "audit",
            str(demo_dir / "p"),
            "--output-dir",
            str(audit_dir),
            "--format",
            "json",
        ]
    )
    audit_payload = json.loads(capsys.readouterr().out)
    validate_exit = fastcfd_main(["execution-gate", "validate", str(audit_dir), "--format", "json"])
    validate_payload = json.loads(capsys.readouterr().out)

    assert demo_exit in {0, 2}
    assert demo_payload["outputs"]["solver_execution"] == "not_attempted"
    assert audit_exit in {0, 2}
    assert audit_payload["solver_execution"] == "not_attempted"
    assert validate_exit == 0
    assert validate_payload["passed"]
