from __future__ import annotations

import csv
import json
from pathlib import Path

from fromcad2cfd_fastcfd.capabilities import capability_inventory
from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.motion import (
    demo_motion_contract,
    sample_motion_contract,
    validate_motion_contract,
    write_demo_motion_case,
)
from fromcad2cfd_fastcfd.motion_adapter import adapt_motion_to_mesh
from fromcad2cfd_fastcfd.motion_quasi_steady import run_moving_obstacle_evidence_demo, run_quasi_steady_motion_case
from fromcad2cfd_fastcfd.motion_solver_preflight import run_motion_solver_preflight
from fromcad2cfd_fastcfd.solver_capability_matrix import solver_capability_matrix
from fromcad2cfd_fastcfd.unstructured.case_runner import run_unstructured_case_file, write_public_steady_channel_case
from fromcad2cfd_fastcfd.unstructured.channel_validation import write_unit_square_channel_mesh


def test_demo_motion_contract_validates():
    validation = validate_motion_contract(demo_motion_contract())

    assert validation["passed"] is True
    assert validation["motion_count"] == 3
    assert validation["evidence_level"] == "kinematic_preflight_only"
    ids = {item["id"] for item in validation["normalized_motions"]}
    assert "oscillating_obstacle_x" in ids
    assert "moving_wall_y" in ids
    assert "rotating_body_proxy" in ids


def test_motion_sampling_writes_summary_csv_and_report(tmp_path):
    result = sample_motion_contract(demo_motion_contract(), tmp_path / "sample", time_step_s=0.25, total_time_s=1.0)

    assert result["status"] == "success"
    assert result["sampling"]["time_count"] == 5
    assert result["sampling"]["sample_count"] == 15
    assert Path(result["artifacts"]["motion_summary"]).exists()
    assert Path(result["artifacts"]["motion_samples"]).exists()
    assert Path(result["artifacts"]["motion_report"]).exists()

    with Path(result["artifacts"]["motion_samples"]).open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    first_obstacle = next(row for row in rows if row["motion_id"] == "oscillating_obstacle_x" and row["time_s"] == "0.0")
    assert float(first_obstacle["dx_m"]) == 0.0
    assert float(first_obstacle["vx_m_s"]) > 0.0


def test_motion_contract_rejects_executable_keys():
    payload = demo_motion_contract()
    payload["motions"][0]["parameters"]["python"] = "print('unsafe')"

    validation = validate_motion_contract(payload)

    assert validation["passed"] is False
    assert "dangerous executable keys" in validation["errors"][0]


def test_motion_contract_rejects_missing_parameters():
    payload = demo_motion_contract()
    del payload["motions"][1]["parameters"]["velocity_m_s"]

    validation = validate_motion_contract(payload)

    assert validation["passed"] is False
    assert any("velocity_m_s" in error for error in validation["errors"])


def test_motion_cli_write_demo_validate_and_sample(tmp_path, capsys):
    demo_dir = tmp_path / "demo"
    sample_dir = tmp_path / "sample"

    exit_code = fastcfd_main(["motion", "write-demo", "--output-dir", str(demo_dir), "--format", "json"])
    demo_payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    motion_file = Path(demo_payload["motion_file"])
    assert motion_file.exists()

    exit_code = fastcfd_main(["motion", "validate", str(motion_file), "--format", "json"])
    validation = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert validation["passed"] is True

    exit_code = fastcfd_main(
        [
            "motion",
            "sample",
            str(motion_file),
            "--output-dir",
            str(sample_dir),
            "--time-step-s",
            "0.5",
            "--total-time-s",
            "1.0",
            "--format",
            "json",
        ]
    )
    sample = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert sample["sampling"]["sample_count"] == 9
    assert Path(sample["artifacts"]["motion_samples"]).exists()


def test_motion_registered_in_capability_inventory_and_matrix(tmp_path):
    status = write_demo_motion_case(tmp_path / "demo")
    inventory = capability_inventory()
    matrix = solver_capability_matrix()

    assert status["status"] == "success"
    assert "motion_contract_preflight" in inventory["validation_gates"]
    assert "motion_mesh_adapter" in inventory["validation_gates"]
    assert "motion_solver_preflight" in inventory["validation_gates"]
    assert "quasi_steady_motion_evidence" in inventory["validation_gates"]
    assert "moving_obstacle_motion_evidence" in inventory["validation_gates"]
    ids = {item["id"] for item in matrix["capabilities"]}
    assert "motion_contract_preflight" in ids
    assert "motion_mesh_adapter" in ids
    assert "motion_solver_preflight" in ids
    assert "quasi_steady_motion_evidence" in ids
    assert "moving_obstacle_motion_evidence" in ids


def test_motion_adapter_binds_to_gmsh_boundary_patch(tmp_path):
    mesh_file = write_unit_square_channel_mesh(tmp_path / "channel.msh", nx=4, ny=2)
    payload = {
        "schema_version": "fastfluent_motion_contract_v1",
        "units": {"length": "m", "time": "s", "angle": "rad"},
        "motions": [
            {
                "id": "moving_wall",
                "target_type": "boundary",
                "target_name": "top_bottom_wall",
                "target_patch_name": "wall",
                "motion_kind": "constant_translation",
                "reference_point": [0.0, 0.0, 0.0],
                "parameters": {"velocity_m_s": [0.01, 0.0, 0.0]},
            }
        ],
    }

    result = adapt_motion_to_mesh(payload, mesh_file, tmp_path / "adapter", time_step_s=0.1, total_time_s=0.2)

    assert result["status"] == "passed"
    assert result["bindings"][0]["patch_name"] == "wall"
    assert result["bindings"][0]["node_count"] > 0
    assert result["bindings"][0]["boundary_element_count"] > 0
    assert result["bindings"][0]["motion_qoi"]["motion_courant"] > 0.0
    assert Path(result["artifacts"]["motion_mesh_adapter"]).exists()
    assert Path(result["artifacts"]["motion_mesh_adapter_report"]).exists()


def test_motion_adapter_blocks_missing_patch(tmp_path):
    mesh_file = write_unit_square_channel_mesh(tmp_path / "channel.msh", nx=2, ny=1)
    payload = {
        "schema_version": "fastfluent_motion_contract_v1",
        "units": {"length": "m", "time": "s", "angle": "rad"},
        "motions": [
            {
                "id": "moving_unknown",
                "target_type": "boundary",
                "target_name": "unknown_wall",
                "motion_kind": "constant_translation",
                "reference_point": [0.0, 0.0, 0.0],
                "parameters": {"velocity_m_s": [0.01, 0.0, 0.0]},
            }
        ],
    }

    result = adapt_motion_to_mesh(payload, mesh_file, tmp_path / "missing_patch", time_step_s=0.1, total_time_s=0.1)

    assert result["status"] == "failed"
    assert any("unknown_wall" in error for error in result["blocking_errors"])


def test_motion_adapter_cli_routes(tmp_path, capsys):
    mesh_file = write_unit_square_channel_mesh(tmp_path / "channel.msh", nx=4, ny=2)
    motion_file = tmp_path / "motion.json"
    motion_file.write_text(
        json.dumps(
            {
                "schema_version": "fastfluent_motion_contract_v1",
                "units": {"length": "m", "time": "s", "angle": "rad"},
                "motions": [
                    {
                        "id": "moving_wall",
                        "target_type": "boundary",
                        "target_name": "wall",
                        "motion_kind": "sinusoidal_translation",
                        "reference_point": [0.0, 0.0, 0.0],
                        "parameters": {"amplitude_m": [0.001, 0.0, 0.0], "frequency_hz": 1.0},
                    }
                ],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    exit_code = fastcfd_main(
        [
            "motion",
            "adapt-mesh",
            str(motion_file),
            str(mesh_file),
            "--output-dir",
            str(tmp_path / "adapter_cli"),
            "--time-step-s",
            "0.05",
            "--total-time-s",
            "0.1",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["solver_adapter"]["bindings"][0]["patch_name"] == "wall"
    assert Path(payload["artifacts"]["motion_mesh_adapter"]).exists()


def _write_wall_motion_adapter(tmp_path, *, velocity=(0.01, 0.0, 0.0)):
    mesh_file = write_unit_square_channel_mesh(tmp_path / "channel.msh", nx=4, ny=2)
    payload = {
        "schema_version": "fastfluent_motion_contract_v1",
        "units": {"length": "m", "time": "s", "angle": "rad"},
        "motions": [
            {
                "id": "moving_wall",
                "target_type": "boundary",
                "target_name": "wall",
                "motion_kind": "constant_translation",
                "reference_point": [0.0, 0.0, 0.0],
                "parameters": {"velocity_m_s": list(velocity)},
            }
        ],
    }
    adapter = adapt_motion_to_mesh(payload, mesh_file, tmp_path / "adapter", time_step_s=0.05, total_time_s=0.1)
    return mesh_file, Path(adapter["artifacts"]["motion_mesh_adapter"])


def test_motion_solver_preflight_allows_static_grid_motion_evidence(tmp_path):
    _mesh_file, adapter_file = _write_wall_motion_adapter(tmp_path)

    result = run_motion_solver_preflight(adapter_file, tmp_path / "preflight", solver_family="steady_incompressible")

    assert result["status"] == "passed"
    assert result["solver_dispatch_allowed"] is True
    assert result["solver_execution_mode"] == "static_grid_with_motion_evidence"
    assert result["active_motion_count"] == 1
    assert Path(result["artifacts"]["motion_solver_preflight"]).exists()
    assert Path(result["artifacts"]["motion_solver_decision"]).exists()


def test_motion_solver_preflight_blocks_dynamic_mesh_request(tmp_path):
    _mesh_file, adapter_file = _write_wall_motion_adapter(tmp_path)

    result = run_motion_solver_preflight(
        adapter_file,
        tmp_path / "dynamic_preflight",
        solver_family="steady_incompressible",
        execution_mode="require_dynamic_mesh",
    )

    assert result["status"] == "failed"
    assert result["solver_dispatch_allowed"] is False
    assert any("dynamic mesh" in error for error in result["blocking_errors"])


def test_unstructured_run_case_accepts_motion_adapter_as_static_evidence(tmp_path):
    mesh_file, adapter_file = _write_wall_motion_adapter(tmp_path)
    case_file = write_public_steady_channel_case(tmp_path / "case.json", mesh_file=mesh_file, iterations=2)

    result = run_unstructured_case_file(case_file, output_dir=tmp_path / "case_run", motion_adapter_file=adapter_file)

    assert result["status"] == "success"
    preflight = result["outputs"]["motion_solver_preflight"]
    assert preflight["solver_dispatch_allowed"] is True
    assert result["outputs"]["solver_execution_mode"] == "static_grid_with_motion_evidence"
    assert Path(result["outputs"]["artifacts"]["motion_solver_preflight"]).exists()


def test_unstructured_run_case_blocks_when_dynamic_mesh_required(tmp_path):
    mesh_file, adapter_file = _write_wall_motion_adapter(tmp_path)
    case_file = write_public_steady_channel_case(tmp_path / "case.json", mesh_file=mesh_file, iterations=1)

    result = run_unstructured_case_file(
        case_file,
        output_dir=tmp_path / "case_blocked",
        motion_adapter_file=adapter_file,
        motion_execution_mode="require_dynamic_mesh",
    )

    assert result["status"] == "failed"
    assert result["outputs"]["solver_execution"] == "blocked_by_motion_solver_preflight"
    assert any("dynamic mesh" in error for error in result["errors"])


def test_motion_solver_preflight_cli_and_run_case_cli(tmp_path, capsys):
    mesh_file, adapter_file = _write_wall_motion_adapter(tmp_path)
    case_file = write_public_steady_channel_case(tmp_path / "case.json", mesh_file=mesh_file, iterations=1)

    exit_code = fastcfd_main(
        [
            "motion",
            "solver-preflight",
            str(adapter_file),
            "--output-dir",
            str(tmp_path / "cli_preflight"),
            "--solver-family",
            "steady_incompressible",
            "--format",
            "json",
        ]
    )
    preflight = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert preflight["solver_dispatch_allowed"] is True

    exit_code = fastcfd_main(
        [
            "unstructured",
            "run-case",
            str(case_file),
            "--motion-adapter",
            str(adapter_file),
            "--output-dir",
            str(tmp_path / "cli_case_run"),
            "--format",
            "json",
        ]
    )
    case_run = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert case_run["status"] == "success"
    assert case_run["outputs"]["motion_solver_preflight"]["solver_dispatch_allowed"] is True


def test_quasi_steady_motion_case_runs_snapshot_sequence(tmp_path):
    mesh_file, adapter_file = _write_wall_motion_adapter(tmp_path)
    case_file = write_public_steady_channel_case(tmp_path / "case.json", mesh_file=mesh_file, iterations=8)

    result = run_quasi_steady_motion_case(case_file, adapter_file, tmp_path / "qs", max_snapshots=2)

    assert result["status"] == "success"
    assert result["quality_status"] == "warning"
    assert result["snapshot_count"] == 2
    assert result["summary_qoi"]["max_motion_courant"] > 0.0
    assert result["summary_qoi"]["hardening_status_counts"]["warning"] == 2
    assert result["agent_decision"]["recommended_next_action"] == "use_for_screening_only_and_repair_before_fluent_handoff"
    assert Path(result["artifacts"]["qs_summary"]).exists()
    assert Path(result["artifacts"]["qs_history"]).exists()
    assert Path(result["artifacts"]["qs_report"]).exists()
    assert Path(result["snapshots"][0]["case_status"]).exists()


def test_quasi_steady_motion_case_blocks_dynamic_mesh_request(tmp_path):
    mesh_file, adapter_file = _write_wall_motion_adapter(tmp_path)
    case_file = write_public_steady_channel_case(tmp_path / "case.json", mesh_file=mesh_file, iterations=1)

    result = run_quasi_steady_motion_case(
        case_file,
        adapter_file,
        tmp_path / "qs_blocked",
        execution_mode="require_dynamic_mesh",
    )

    assert result["status"] == "failed"
    assert result["snapshot_count"] == 0
    assert any("dynamic mesh" in error for error in result["blocking_errors"])


def test_moving_obstacle_evidence_demo_runs_public_route(tmp_path):
    result = run_moving_obstacle_evidence_demo(tmp_path / "moving_obstacle", nx=8, ny=4, total_time_s=0.1, iterations=1)

    assert result["status"] == "success"
    assert result["quality_status"] == "warning"
    assert result["motion_adapter"]["bindings"][0]["patch_name"] == "obstacle_wall"
    assert result["quasi_steady"]["status"] == "success"
    assert result["quasi_steady"]["quality_status"] == "warning"
    assert result["quasi_steady"]["agent_decision"]["recommended_next_action"] == "use_for_screening_only_and_repair_before_fluent_handoff"
    assert result["quasi_steady"]["snapshot_count"] >= 2
    assert Path(result["artifacts"]["moving_obstacle_summary"]).exists()
    assert Path(result["artifacts"]["moving_obstacle_report"]).exists()


def test_quasi_steady_and_moving_obstacle_cli_routes(tmp_path, capsys):
    mesh_file, adapter_file = _write_wall_motion_adapter(tmp_path)
    case_file = write_public_steady_channel_case(tmp_path / "case.json", mesh_file=mesh_file, iterations=1)

    exit_code = fastcfd_main(
        [
            "motion",
            "quasi-steady",
            str(case_file),
            str(adapter_file),
            "--output-dir",
            str(tmp_path / "qs_cli"),
            "--max-snapshots",
            "2",
            "--format",
            "json",
        ]
    )
    quasi = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert quasi["status"] == "success"
    assert quasi["snapshot_count"] == 2

    exit_code = fastcfd_main(
        [
            "motion",
            "moving-obstacle-demo",
            "--output-dir",
            str(tmp_path / "mo_cli"),
            "--nx",
            "8",
            "--ny",
            "4",
            "--total-time-s",
            "0.1",
            "--iterations",
            "1",
            "--format",
            "json",
        ]
    )
    moving = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert moving["status"] == "success"
    assert moving["quality_status"] == "warning"
    assert moving["motion_adapter"]["bindings"][0]["patch_name"] == "obstacle_wall"
