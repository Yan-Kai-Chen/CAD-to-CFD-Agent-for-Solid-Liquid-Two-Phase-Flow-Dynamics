from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fluent_solver.monitor_contract import monitor_contract
from fromcad2cfd_fluent_solver.schemas import SOLVER_PLAN_SCHEMA_VERSION, validate_resume_plan, validate_solver_plan
from fromcad2cfd_mcp_fluent_solver.server import server_descriptor
from fromcad2cfd_mcp_fluent_solver.tools import DISABLED_TOOLS, tool_inventory


def _solver_plan() -> dict:
    return {
        "schema_version": SOLVER_PLAN_SCHEMA_VERSION,
        "plan_name": "unit_solver_plan",
        "mesh_input": "sandbox/input/unit.msh.h5",
        "case_output": "sandbox/output/unit.cas.h5",
        "data_output": "sandbox/output/unit.dat.h5",
        "physics": {
            "energy": True,
            "species_model": "species-transport",
            "turbulence_model": "k-omega-sst",
        },
        "boundaries": {
            "inlet": {"type": "mass-flow-inlet", "mass_flow_rate_kg_s": 0.61},
            "wall": {"type": "wall"},
        },
        "transient": {
            "mode": "adaptive",
            "total_time_s": 4.1,
            "initial_time_step_s": 0.001,
            "min_time_step_s": 0.001,
            "max_time_step_s": 0.05,
            "courant_number": 2.0,
            "max_iterations_per_step": 20,
        },
    }


def test_solver_plan_validation_accepts_public_relative_paths():
    result = validate_solver_plan(_solver_plan())

    assert result["status"] == "passed"
    assert result["monitor_contract"]["schema_version"] == "fromcad2cfd_fluent_monitor_contract_v1"


def test_solver_plan_validation_rejects_public_absolute_paths():
    plan = _solver_plan()
    plan["mesh_input"] = str(Path.cwd() / "sandbox" / "input" / "unit.msh.h5")

    result = validate_solver_plan(plan)

    assert result["status"] == "failed"
    assert any("absolute" in message for message in result["errors"])


def test_resume_plan_rejects_suspicious_small_checkpoint():
    result = validate_resume_plan(
        {
            "schema_version": "fromcad2cfd_fluent_solver_resume_plan_v1",
            "resume_name": "unit_resume",
            "case_input": "sandbox/input/unit.cas.h5",
            "data_input": "sandbox/input/unit-00200.dat.h5",
            "resume_flow_time_s": 0.2,
            "target_flow_time_s": 4.1,
            "data_file_size_bytes": 10,
            "minimum_expected_data_size_bytes": 100,
        }
    )

    assert result["status"] == "failed"
    assert any("suspiciously small" in message for message in result["errors"])


def test_root_cli_routes_fluent_solver_validate_plan(tmp_path, capsys):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_solver_plan()), encoding="utf-8")

    exit_code = root_main(["fluent-solver", "validate-plan", "--plan", str(plan_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "passed"


def test_root_cli_writes_pyfluent_template(tmp_path, capsys):
    plan_path = tmp_path / "plan.json"
    output_path = tmp_path / "template.py"
    plan_path.write_text(json.dumps(_solver_plan()), encoding="utf-8")

    exit_code = root_main(["fluent-solver", "write-template", "--plan", str(plan_path), "--output", str(output_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert output_path.exists()
    assert "pyfluent.launch_fluent" in output_path.read_text(encoding="utf-8")


def test_monitor_contract_contains_wall_heat_and_surface_load_proxy_fields():
    contract = monitor_contract()

    assert "vol_avg_temperature" in contract["global_monitor"]["report_defs"]
    assert "outer_wall_total_heat_transfer_rate" in contract["wall_monitor"]["report_defs"]
    assert "model_max_abs_pressure" in contract["wall_monitor"]["report_defs"]


def test_fluent_solver_mcp_inventory_is_safe():
    inventory = tool_inventory()
    descriptor = server_descriptor()

    assert "fromcad2cfd_fluent_solver_validate_plan" in inventory["allowed_tools"]
    assert "raw_pyfluent_call" in DISABLED_TOOLS
    assert "launch_fluent_solver" in descriptor["disabled_tools"]
    assert "raw_pyfluent_call" not in inventory["allowed_tools"]
