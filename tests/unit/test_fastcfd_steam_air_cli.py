from __future__ import annotations

import json

from fromcad2cfd_fastcfd.cli import main as fastcfd_main


def test_steam_air_cli_writes_case_passport_patch_and_demo(tmp_path):
    demo_dir = tmp_path / "steam_air_demo"

    assert fastcfd_main(["write-steam-air-demo", "--output-dir", str(demo_dir)]) == 0
    case_file = demo_dir / "steam_air_condensation_case.json"
    assert case_file.exists()

    passport_dir = demo_dir / "passport"
    assert (
        fastcfd_main(
            [
                "validate-steam-air-condensation",
                "--case",
                str(case_file),
                "--output-dir",
                str(passport_dir),
            ]
        )
        == 0
    )
    passport_file = passport_dir / "steam_air_condensation_passport.json"
    hints_file = passport_dir / "steam_air_condensation_fluent_hints.json"
    report_file = passport_dir / "steam_air_condensation_report.md"
    assert passport_file.exists()
    assert hints_file.exists()
    assert report_file.exists()

    patch_file = demo_dir / "solver_plan_patch.json"
    assert fastcfd_main(["compile-fluent-patch", "--input", str(passport_file), "--output", str(patch_file)]) == 0
    assert patch_file.exists()
    assert (demo_dir / "solver_plan_patch_report.md").exists()
    patch = json.loads(patch_file.read_text(encoding="utf-8"))
    assert patch["patches"]
    assert patch["evidence"]

    full_demo_dir = tmp_path / "steam_air_handoff_demo"
    assert fastcfd_main(["steam-air-handoff-demo", "--output-dir", str(full_demo_dir)]) == 0
    assert (full_demo_dir / "steam_air_condensation_case.json").exists()
    assert (full_demo_dir / "passport" / "steam_air_condensation_passport.json").exists()
    assert (full_demo_dir / "solver_plan_patch.json").exists()
