from __future__ import annotations

import json

from fromcad2cfd.cli import main as root_main


def test_wax_cli_writes_case_passport_patch_and_demo(tmp_path, capsys):
    demo_dir = tmp_path / "wax_cli_demo"

    exit_code = root_main(["fastcfd", "write-wax-rheology-demo", "--output-dir", str(demo_dir)])
    payload = json.loads(capsys.readouterr().out)
    case_file = demo_dir / "wax_rheology_phase_change_case.json"
    assert exit_code == 0
    assert payload["status"] == "success"
    assert case_file.exists()
    assert payload["metadata"]["fluent_launched"] is False

    passport_dir = demo_dir / "passport"
    exit_code = root_main(["fastcfd", "validate-wax-rheology-phase-change", "--case", str(case_file), "--output-dir", str(passport_dir)])
    payload = json.loads(capsys.readouterr().out)
    passport_file = passport_dir / "wax_rheology_phase_change_passport.json"
    assert exit_code == 0
    assert payload["status"] == "success"
    assert passport_file.exists()
    assert (passport_dir / "wax_rheology_phase_change_fluent_hints.json").exists()
    assert (passport_dir / "wax_rheology_phase_change_report.md").exists()

    patch_file = demo_dir / "compiled_solver_plan_patch.json"
    exit_code = root_main(["fastcfd", "compile-fluent-patch", "--input", str(passport_file), "--output", str(patch_file)])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert patch_file.exists()

    full_demo_dir = tmp_path / "wax_handoff_demo"
    exit_code = root_main(["fastcfd", "wax-rheology-handoff-demo", "--output-dir", str(full_demo_dir)])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] in {"success", "partial"}
    assert payload["metadata"]["fluent_launched"] is False
    assert (full_demo_dir / "solver_plan_patch.json").exists()
