from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.controlled_runner import run_controlled_runner
from fromcad2cfd_fastcfd.execution_gate import run_execution_gate_demo
from fromcad2cfd_fastcfd.motion_quasi_steady import run_moving_obstacle_evidence_demo
from fromcad2cfd_fastcfd.result_pack import compile_native_result_pack, compile_result_pack, run_result_pack_demo, validate_result_pack
from fromcad2cfd_fastcfd.unstructured.steady_incompressible import run_steady_incompressible_case
from tests.unit.test_fastcfd_unstructured import write_unit_square_channel_mesh


def test_result_pack_compiles_dry_run_controlled_runner(tmp_path):
    gate_demo = run_execution_gate_demo(tmp_path / "gate_demo")
    controlled = run_controlled_runner(gate_demo["outputs"]["artifacts"]["execution_gate"], output_dir=tmp_path / "controlled")

    pack = compile_result_pack(controlled["artifacts"]["controlled_run"], output_dir=tmp_path / "result_pack")

    assert pack["schema_version"] == "fastfluent_result_pack_v1"
    assert pack["status"] == "review_only"
    assert pack["evidence_level"] == "no_solver_evidence"
    assert pack["decision"]["can_support_workflow_decision"] is True
    assert pack["decision"]["can_support_physics_decision"] is False
    assert Path(pack["artifacts"]["decision_brief"]).exists()
    assert Path(pack["artifacts"]["agent_handoff"]).exists()


def test_result_pack_validation_passes_for_dry_run_pack(tmp_path):
    gate_demo = run_execution_gate_demo(tmp_path / "gate_demo")
    controlled = run_controlled_runner(gate_demo["outputs"]["artifacts"]["execution_gate"], output_dir=tmp_path / "controlled")
    pack = compile_result_pack(controlled["artifacts"]["controlled_run"], output_dir=tmp_path / "result_pack")

    validation = validate_result_pack(tmp_path / "result_pack")

    assert validation["passed"]
    assert validation["result_pack_status"] == pack["status"]
    assert validation["evidence_level"] == "no_solver_evidence"


def test_result_pack_demo_writes_status(tmp_path):
    result = run_result_pack_demo(tmp_path / "demo")

    assert result["operation"] == "result_pack_demo"
    assert result["status"] == "review_only"
    assert result["outputs"]["evidence_level"] == "no_solver_evidence"
    assert Path(result["outputs"]["artifacts"]["result_pack"]).exists()


def test_result_pack_cli_routes(tmp_path, capsys):
    demo_dir = tmp_path / "demo"
    compile_dir = tmp_path / "compiled"

    demo_exit = fastcfd_main(["result-pack", "demo", "--output-dir", str(demo_dir), "--format", "json"])
    demo_payload = json.loads(capsys.readouterr().out)
    compile_exit = fastcfd_main(
        [
            "result-pack",
            "compile",
            str(demo_dir / "x"),
            "--output-dir",
            str(compile_dir),
            "--format",
            "json",
        ]
    )
    compile_payload = json.loads(capsys.readouterr().out)
    validate_exit = fastcfd_main(["result-pack", "validate", str(compile_dir), "--format", "json"])
    validate_payload = json.loads(capsys.readouterr().out)

    assert demo_exit == 0
    assert demo_payload["outputs"]["evidence_level"] == "no_solver_evidence"
    assert compile_exit == 0
    assert compile_payload["status"] == "review_only"
    assert validate_exit == 0
    assert validate_payload["passed"]


def test_native_result_pack_preserves_passed_steady_hardening(tmp_path):
    mesh_path = write_unit_square_channel_mesh(tmp_path / "steady.msh", nx=8, ny=4)
    result = run_steady_incompressible_case(mesh_path, output_dir=tmp_path / "steady_out", iterations=8, viscosity=1.0e-2)

    pack = compile_native_result_pack(result["outputs"]["artifacts"]["steady_status"], output_dir=tmp_path / "native_pack")
    validation = validate_result_pack(tmp_path / "native_pack")

    assert pack["status"] == "advisory_native_evidence"
    assert pack["source_kind"] == "native_result"
    assert pack["quality_status"] == "passed"
    assert pack["native_result"]["result_kind"] == "steady_incompressible"
    assert pack["decision"]["can_support_screening_decision"] is True
    assert pack["decision"]["can_support_physics_decision"] is True
    assert pack["usage_boundary"]["valid_for_final_cfd_validation"] is False
    assert Path(pack["artifacts"]["native_result_summary"]).exists()
    assert validation["passed"]


def test_native_result_pack_preserves_warning_motion_evidence(tmp_path):
    result = run_moving_obstacle_evidence_demo(tmp_path / "moving", nx=8, ny=4, total_time_s=0.1, iterations=1)

    pack = compile_native_result_pack(result["artifacts"]["moving_obstacle_summary"], output_dir=tmp_path / "moving_pack")
    validation = validate_result_pack(tmp_path / "moving_pack")

    assert pack["status"] == "native_evidence_warning"
    assert pack["quality_status"] == "warning"
    assert pack["native_result"]["result_kind"] == "moving_obstacle_motion_evidence"
    assert pack["decision"]["can_support_screening_decision"] is True
    assert pack["decision"]["can_support_physics_decision"] is False
    assert pack["decision"]["recommended_next_action"] == "use_for_screening_only_and_repair_before_fluent_handoff"
    assert validation["passed"]
    assert any("warning" in item.lower() for item in validation["warnings"])


def test_native_result_pack_blocks_failed_native_result_but_validates_schema(tmp_path):
    failed_path = tmp_path / "failed" / "status.json"
    failed_path.parent.mkdir()
    failed_path.write_text(
        json.dumps(
            {
                "schema_version": "fromcad2cfd_fastfluent_unstructured_steady_incompressible_v1",
                "status": "failed",
                "operation": "solve_steady_incompressible",
                "errors": ["synthetic failure"],
                "outputs": {"artifacts": {}},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    pack = compile_native_result_pack(failed_path, output_dir=tmp_path / "failed_pack")
    validation = validate_result_pack(tmp_path / "failed_pack")

    assert pack["status"] == "blocked_native_evidence"
    assert pack["quality_status"] == "failed"
    assert pack["decision"]["can_support_screening_decision"] is False
    assert pack["decision"]["can_support_final_cfd_validation"] is False
    assert validation["passed"]
    assert any("failed" in item.lower() for item in validation["warnings"])


def test_native_result_pack_cli_compile_native_route(tmp_path, capsys):
    mesh_path = write_unit_square_channel_mesh(tmp_path / "steady_cli.msh", nx=8, ny=4)
    result = run_steady_incompressible_case(mesh_path, output_dir=tmp_path / "steady_cli_out", iterations=8, viscosity=1.0e-2)

    exit_code = fastcfd_main(
        [
            "result-pack",
            "compile-native",
            result["outputs"]["artifacts"]["steady_status"],
            "--output-dir",
            str(tmp_path / "native_cli_pack"),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["source_kind"] == "native_result"
    assert payload["quality_status"] == "passed"
    assert Path(payload["artifacts"]["agent_handoff"]).exists()
