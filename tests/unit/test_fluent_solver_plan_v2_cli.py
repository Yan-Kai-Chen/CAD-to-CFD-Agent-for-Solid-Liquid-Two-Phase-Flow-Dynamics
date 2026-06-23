from __future__ import annotations

import json

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fluent_solver.patch_preview import create_synthetic_solver_plan_patch


def test_root_cli_write_plan_v2_demo_writes_base_plan_and_report(tmp_path, capsys):
    output_dir = tmp_path / "plan_v2_demo"

    exit_code = root_main(["fluent-solver", "write-plan-v2-demo", "--output-dir", str(output_dir), "--case-name", "cli_unit"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert (output_dir / "base_solver_plan_v2.json").exists()
    assert (output_dir / "base_solver_plan_v2_report.md").exists()


def test_root_cli_preview_patch_writes_all_preview_artifacts(tmp_path, capsys):
    base_dir = tmp_path / "base"
    preview_dir = tmp_path / "preview"
    patch_path = tmp_path / "solver_plan_patch.json"
    root_main(["fluent-solver", "write-plan-v2-demo", "--output-dir", str(base_dir), "--case-name", "cli_unit"])
    capsys.readouterr()
    patch_path.write_text(json.dumps(create_synthetic_solver_plan_patch("cli_unit")), encoding="utf-8")

    exit_code = root_main(
        [
            "fluent-solver",
            "preview-patch",
            "--base-plan",
            str(base_dir / "base_solver_plan_v2.json"),
            "--patch",
            str(patch_path),
            "--output-dir",
            str(preview_dir),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["preview_status"] == "ready_for_review"
    for name in [
        "patched_solver_plan_preview.json",
        "patch_application_report.md",
        "conflict_report.json",
        "before_after_diff.md",
        "reviewer_checklist.md",
    ]:
        assert (preview_dir / name).exists()


def test_root_cli_plan_v2_patch_preview_demo_writes_full_bundle(tmp_path, capsys):
    output_dir = tmp_path / "full_demo"

    exit_code = root_main(["fluent-solver", "plan-v2-patch-preview-demo", "--output-dir", str(output_dir), "--case-name", "cli_unit"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert (output_dir / "base_solver_plan_v2.json").exists()
    assert (output_dir / "base_solver_plan_v2_report.md").exists()
    assert (output_dir / "patch" / "solver_plan_patch.json").exists()
    assert (output_dir / "preview" / "patched_solver_plan_preview.json").exists()
    assert (output_dir / "preview" / "reviewer_checklist.md").exists()
