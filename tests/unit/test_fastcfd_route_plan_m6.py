from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.route_plan import compile_route_plan, run_route_plan_demo, validate_route_plan
from fromcad2cfd_fastcfd.route_selector import run_route_selector_demo
from fromcad2cfd_fastcfd.schemas import read_job


def test_route_plan_compiles_structured_fastfluent_job(tmp_path):
    selector_demo = run_route_selector_demo(tmp_path / "selector")
    route_selection = selector_demo["outputs"]["artifacts"]["route_selection"]

    plan = compile_route_plan(route_selection, output_dir=tmp_path / "plan")

    assert plan["schema_version"] == "fastfluent_route_plan_v1"
    assert plan["status"] == "ready_for_approval"
    assert plan["recommended_route"] == "native_fastfluent_structured"
    assert plan["execution_boundary"]["compiler_executes_solver"] is False
    assert plan["materialized_job"]["physics_status"] in {"passed", "warning"}
    assert Path(plan["materialized_job"]["job_path"]).exists()
    assert Path(plan["materialized_job"]["physics_passport_path"]).exists()
    job = read_job(plan["materialized_job"]["job_path"])
    assert job.case_type == "channel2d"
    assert job.backend == "fastfluent"


def test_route_plan_validation_passes_for_demo_plan(tmp_path):
    selector_demo = run_route_selector_demo(tmp_path / "selector")
    plan = compile_route_plan(selector_demo["outputs"]["artifacts"]["route_selection"], output_dir=tmp_path / "plan")

    validation = validate_route_plan(tmp_path / "plan")

    assert validation["passed"]
    assert validation["plan_status"] == plan["status"]
    assert validation["recommended_route"] == "native_fastfluent_structured"


def test_route_plan_demo_writes_status_and_artifacts(tmp_path):
    result = run_route_plan_demo(tmp_path / "demo")

    assert result["status"] == "ready_for_approval"
    assert result["outputs"]["recommended_route"] == "native_fastfluent_structured"
    assert Path(result["outputs"]["artifacts"]["route_plan"]).exists()
    assert Path(result["outputs"]["artifacts"]["approval_gate"]).exists()


def test_route_plan_cli_routes(tmp_path, capsys):
    demo_dir = tmp_path / "demo"
    compile_dir = tmp_path / "compiled"

    demo_exit = fastcfd_main(["route-plan", "demo", "--output-dir", str(demo_dir), "--format", "json"])
    demo_payload = json.loads(capsys.readouterr().out)
    compile_exit = fastcfd_main(
        [
            "route-plan",
            "compile",
            str(demo_dir / "s"),
            "--output-dir",
            str(compile_dir),
            "--format",
            "json",
        ]
    )
    compile_payload = json.loads(capsys.readouterr().out)
    validate_exit = fastcfd_main(["route-plan", "validate", str(compile_dir), "--format", "json"])
    validate_payload = json.loads(capsys.readouterr().out)

    assert demo_exit == 0
    assert demo_payload["status"] == "ready_for_approval"
    assert compile_exit == 0
    assert compile_payload["recommended_route"] == "native_fastfluent_structured"
    assert validate_exit == 0
    assert validate_payload["passed"]
