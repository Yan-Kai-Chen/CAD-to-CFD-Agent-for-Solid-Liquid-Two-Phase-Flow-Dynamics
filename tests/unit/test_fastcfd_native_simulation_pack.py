from __future__ import annotations

import json

from fromcad2cfd_fastcfd.native_simulation_pack import (
    create_native_simulation_case_registry,
    run_native_simulation_validation_pack,
)


def test_native_simulation_registry_covers_structured_and_unstructured_cases():
    registry = create_native_simulation_case_registry()
    case_ids = {case.case_id for case in registry}
    runnable_cases = [case for case in registry if case.runner is not None]

    assert len(registry) >= 8
    assert len(runnable_cases) >= 5
    assert {
        "cavity2d_re_sweep",
        "channel2d_velocity_grid_sweep",
        "obstacle2d_shape_comparison",
        "poiseuille_channel_convergence",
        "steady_incompressible_channel",
        "vof_lite_alpha_transport",
        "turbulence_ladder",
    }.issubset(case_ids)


def test_native_simulation_validation_pack_writes_manifest_summary_and_outputs(tmp_path):
    output_dir = tmp_path / "native_pack"

    result = run_native_simulation_validation_pack(output_dir)
    manifest = result["outputs"]["manifest"]

    assert result["status"] == "success"
    assert manifest["schema_version"] == "fromcad2cfd_fastfluent_native_simulation_pack_v1"
    assert manifest["actual_simulation_case_count"] >= 5
    assert manifest["field_output_case_count"] >= 3
    assert manifest["convergence_case_count"] >= 1
    assert manifest["grid_convergence_case_count"] >= 1
    assert manifest["model_comparison_case_count"] >= 1
    assert manifest["acceptance_summary"]["s1_complete"] is True
    assert manifest["metadata"]["fluent_launched"] is False
    assert (output_dir / "simulation_manifest.json").exists()
    assert (output_dir / "simulation_summary.md").exists()
    assert (output_dir / "limitations.md").exists()
    assert (output_dir / "unstructured_cases" / "vof_lite_alpha_transport" / "simulation_result.json").exists()
    assert (output_dir / "passport_simulation_alignment" / "vof_passport_vs_vof_lite.md").exists()

    loaded = json.loads((output_dir / "simulation_manifest.json").read_text(encoding="utf-8"))
    assert loaded["acceptance_summary"]["at_least_five_native_cases_ran"] is True
    assert loaded["acceptance_summary"]["fluent_launched"] is False
