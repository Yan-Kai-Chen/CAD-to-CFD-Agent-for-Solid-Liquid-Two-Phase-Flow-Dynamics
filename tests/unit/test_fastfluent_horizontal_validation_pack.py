from __future__ import annotations

import json

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fastcfd.horizontal_validation_pack import (
    create_validation_case_registry,
    run_horizontal_validation_pack,
)


def test_validation_case_registry_covers_h1_h2_h3_minimum():
    registry = create_validation_case_registry()
    module_counts: dict[str, int] = {}
    for spec in registry:
        module_counts[spec.module] = module_counts.get(spec.module, 0) + 1

    assert len(registry) == 23
    assert module_counts == {
        "vof": 4,
        "turbulence": 4,
        "rheology": 4,
        "steam_air_v2": 5,
        "solid_liquid": 6,
    }
    assert all(spec.expected_status in {"pass", "warn", "block"} for spec in registry)


def test_horizontal_validation_pack_writes_expected_tree_and_manifest(tmp_path):
    output_dir = tmp_path / "validation_pack"

    result = run_horizontal_validation_pack(output_dir)
    manifest = result["outputs"]["manifest"]
    summary = manifest["test_status_summary"]

    assert result["status"] in {"success", "partial"}
    assert manifest["schema_version"] == "fromcad2cfd_fastfluent_horizontal_validation_pack_v1"
    assert manifest["case_count"] == 27
    assert manifest["module_counts"] == {
        "combined_patches": 4,
        "rheology": 4,
        "solid_liquid": 6,
        "steam_air_v2": 5,
        "turbulence": 4,
        "vof": 4,
    }
    assert summary["invalid_patch_count"] == 0
    assert summary["validation_error_count"] == 0
    assert summary["valid_patch_count"] == 27
    assert manifest["metadata"]["fluent_launched"] is False
    assert (output_dir / "validation_manifest.json").exists()
    assert (output_dir / "validation_summary.md").exists()

    for relative in [
        "vof_cases/vof_case_01_gravity_dominant/input_case.json",
        "turbulence_cases/turbulence_case_03_high_re_sst/solver_plan_patch.json",
        "rheology_cases/rheology_case_04_large_viscosity_ratio/fluent_hints.json",
        "steam_air_v2_cases/steam_air_case_01_baseline/passport.json",
        "solid_liquid_cases/solid_liquid_case_06_cell_particle_block/solver_plan_patch_report.md",
        "combined_patch_cases/combined_case_04_conflict_review/conflict_summary.json",
    ]:
        assert (output_dir / relative).exists(), relative


def test_validation_pack_keeps_expected_block_cases_but_validates_patches(tmp_path):
    result = run_horizontal_validation_pack(tmp_path / "validation_pack")
    manifest = result["outputs"]["manifest"]
    cases = {item["case_id"]: item for item in manifest["case_index"]}

    assert cases["vof_case_04_high_cfl_block"]["actual_status"] == "block"
    assert cases["solid_liquid_case_06_cell_particle_block"]["actual_status"] == "block"
    assert cases["combined_case_04_conflict_review"]["actual_status"] == "warn"
    assert cases["combined_case_04_conflict_review"]["key_quantities"]["conflict_warning_count"] >= 1
    assert all(item["patch_valid"] for item in manifest["case_index"])
    assert all("raw_pyfluent" not in json.dumps(item).lower() for item in manifest["case_index"])


def test_horizontal_validation_pack_cli(tmp_path, capsys):
    output_dir = tmp_path / "cli_validation_pack"

    exit_code = root_main(["fastcfd", "horizontal-validation-pack-demo", "--output-dir", str(output_dir)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] in {"success", "partial"}
    assert payload["outputs"]["manifest"]["case_count"] == 27
    assert payload["outputs"]["manifest"]["metadata"]["fluent_launched"] is False
    assert (output_dir / "validation_manifest.json").exists()
    assert (output_dir / "validation_summary.md").exists()


def test_horizontal_validation_pack_markdown_cli(tmp_path, capsys):
    output_dir = tmp_path / "cli_validation_pack_markdown"

    exit_code = root_main(["fastcfd", "horizontal-validation-pack-demo", "--output-dir", str(output_dir), "--format", "markdown"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "FastFluent Horizontal H3.5 Validation Pack" in stdout
    assert "Fluent launched: `False`" in stdout
    assert (output_dir / "validation_manifest.json").exists()
