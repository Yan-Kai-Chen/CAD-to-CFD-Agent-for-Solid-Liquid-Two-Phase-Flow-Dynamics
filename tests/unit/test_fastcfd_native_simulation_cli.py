from __future__ import annotations

import json

from fromcad2cfd.cli import main as root_main


def test_native_simulation_validation_pack_cli_json(tmp_path, capsys):
    output_dir = tmp_path / "cli_native_pack"

    exit_code = root_main(["fastcfd", "native-simulation-validation-pack-demo", "--output-dir", str(output_dir)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["outputs"]["manifest"]["actual_simulation_case_count"] >= 5
    assert payload["outputs"]["manifest"]["acceptance_summary"]["s1_complete"] is True
    assert payload["outputs"]["manifest"]["metadata"]["fluent_launched"] is False
    assert (output_dir / "simulation_manifest.json").exists()
    assert (output_dir / "simulation_summary.md").exists()


def test_native_simulation_validation_pack_cli_markdown(tmp_path, capsys):
    output_dir = tmp_path / "cli_native_pack_markdown"

    exit_code = root_main(
        [
            "fastcfd",
            "native-simulation-validation-pack-demo",
            "--output-dir",
            str(output_dir),
            "--format",
            "markdown",
        ]
    )
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "FastFluent S1 Native Simulation Validation Pack" in stdout
    assert "Fluent launched: `False`" in stdout
    assert (output_dir / "simulation_manifest.json").exists()
