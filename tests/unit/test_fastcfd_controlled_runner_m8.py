from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.controlled_runner import run_controlled_runner, run_controlled_runner_demo, validate_controlled_runner
from fromcad2cfd_fastcfd.execution_gate import run_execution_gate_demo


def test_controlled_runner_dry_run_records_no_solver_execution(tmp_path):
    gate_demo = run_execution_gate_demo(tmp_path / "gate_demo")
    gate_path = gate_demo["outputs"]["artifacts"]["execution_gate"]

    result = run_controlled_runner(gate_path, output_dir=tmp_path / "controlled", mode="dry_run")

    assert result["schema_version"] == "fastfluent_controlled_runner_v1"
    assert result["status"] == "ready_not_executed"
    assert result["run_result"]["solver_execution"] == "not_attempted"
    assert result["execution_boundary"]["runner_executes_real_fastfluent"] is False
    assert Path(result["artifacts"]["command_ledger"]).exists()
    assert Path(result["artifacts"]["execution_transcript"]).exists()


def test_controlled_runner_validation_passes_for_demo(tmp_path):
    gate_demo = run_execution_gate_demo(tmp_path / "gate_demo")
    run_controlled_runner(gate_demo["outputs"]["artifacts"]["execution_gate"], output_dir=tmp_path / "controlled")

    validation = validate_controlled_runner(tmp_path / "controlled")

    assert validation["passed"]
    assert validation["controlled_run_status"] == "ready_not_executed"
    assert validation["mode"] == "dry_run"


def test_controlled_runner_demo_writes_status(tmp_path):
    result = run_controlled_runner_demo(tmp_path / "demo")

    assert result["operation"] == "controlled_runner_demo"
    assert result["status"] == "ready_not_executed"
    assert result["outputs"]["solver_execution"] == "not_attempted"
    assert Path(result["outputs"]["artifacts"]["controlled_run"]).exists()


def test_controlled_runner_cli_routes(tmp_path, capsys):
    demo_dir = tmp_path / "demo"
    run_dir = tmp_path / "run"

    demo_exit = fastcfd_main(["controlled-runner", "demo", "--output-dir", str(demo_dir), "--format", "json"])
    demo_payload = json.loads(capsys.readouterr().out)
    run_exit = fastcfd_main(
        [
            "controlled-runner",
            "run",
            str(demo_dir / "g"),
            "--output-dir",
            str(run_dir),
            "--format",
            "json",
        ]
    )
    run_payload = json.loads(capsys.readouterr().out)
    validate_exit = fastcfd_main(["controlled-runner", "validate", str(run_dir), "--format", "json"])
    validate_payload = json.loads(capsys.readouterr().out)

    assert demo_exit == 0
    assert demo_payload["outputs"]["solver_execution"] == "not_attempted"
    assert run_exit == 0
    assert run_payload["run_result"]["solver_execution"] == "not_attempted"
    assert validate_exit == 0
    assert validate_payload["passed"]
