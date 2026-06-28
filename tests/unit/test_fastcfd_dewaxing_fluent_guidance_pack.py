from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.dewaxing_fluent_guidance_pack import compile_dewaxing_fluent_guidance_pack


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_study_pack(root: Path) -> Path:
    _write_json(
        root / "dewaxing_guidance.json",
        {
            "status": "success",
            "best_match_variant": {"variant_id": "shell_thin"},
            "closest_full_melt_variant": {"variant_id": "wax_layer_thick"},
            "closest_risk_window_variant": {"variant_id": "baseline"},
        },
    )
    _write_json(
        root / "sensitivity_summary.json",
        {
            "top_by_metric": {
                "predicted_full_melt_time_s": [{"parameter_group": "steam_boundary_temperature_K"}],
                "dominant_risk_time_s": [{"parameter_group": "initial_temperature_K"}],
                "early_max_shell_stress_proxy_MPa": [{"parameter_group": "steam_boundary_temperature_K"}],
                "peak_pressure_risk_proxy": [{"parameter_group": "wax_thermal_conductivity"}],
            },
            "rows": [
                {
                    "parameter_group": "steam_boundary_temperature_K",
                    "metric": "predicted_full_melt_time_s",
                    "relative_sensitivity": 0.82,
                    "low_variant": "steam_low",
                    "high_variant": "steam_high",
                },
                {
                    "parameter_group": "initial_temperature_K",
                    "metric": "dominant_risk_time_s",
                    "relative_sensitivity": 0.71,
                    "low_variant": "initial_low",
                    "high_variant": "initial_high",
                },
                {
                    "parameter_group": "wax_thermal_conductivity",
                    "metric": "peak_pressure_risk_proxy",
                    "relative_sensitivity": 0.34,
                    "low_variant": "wax_k_low",
                    "high_variant": "wax_k_high",
                },
            ],
        },
    )
    _write_json(
        root / "study_manifest.json",
        {"status": "success", "execution_boundary": {"native_dewaxing_solver_runs": 15}},
    )
    return root


def _write_validation_pack(root: Path) -> Path:
    return _write_json(
        root / "validation_pack_manifest.json",
        {
            "status": "success",
            "quality_status": "passed",
            "execution_boundary": {
                "new_fluent_calculation": False,
                "native_dewaxing_solver_runs": 10,
                "native_cell_time_steps": 20525400,
            },
        },
    )


def _write_iteration_pack(root: Path) -> Path:
    return _write_json(
        root / "agent_iteration_manifest.json",
        {
            "status": "success",
            "candidate_count": 16,
            "candidates": [
                {
                    "candidate_id": "path106_initial6",
                    "name": "path thickness 1.06 and initial temperature +6 K",
                    "metrics": {
                        "predicted_full_melt_time_s": 386.8,
                        "dominant_risk_time_s": 102.209953,
                        "early_max_shell_stress_proxy_MPa": 1.670091,
                    },
                    "comparison_metrics": {
                        "full_melt_time_relative_error": 0.054279,
                        "dominant_risk_time_relative_error": 0.014995,
                    },
                    "edits": [
                        {"path": "domain.thickness_m", "operation": "scale", "value": 1.06},
                        {"path": "initial.temperature_K", "operation": "offset", "value": 6.0},
                    ],
                }
            ],
            "agent_decision": {
                "accepted_candidate": {"candidate_id": "path106_initial6"},
                "stability_rejected_candidates": [
                    {"candidate_id": "fit1"},
                    {"candidate_id": "fit2"},
                    {"candidate_id": "fit3"},
                    {"candidate_id": "fit4"},
                    {"candidate_id": "fit5"},
                ],
                "objective_improvement_vs_baseline": 0.46099,
                "objective_improvement_vs_shell_thin": 0.34364,
            },
            "execution_boundary": {
                "new_fluent_calculation": False,
                "fluent_launched": False,
                "native_dewaxing_solver_runs": 46,
                "native_cell_time_steps": 80140000,
            },
        },
    )


def _write_fluent_bridge_pack(root: Path) -> Path:
    return _write_json(
        root / "dewaxing_result_status.json",
        {
            "status": "success",
            "early_steam_shock_qoi": {
                "stage": "0-4.1 s",
                "case_count": 6,
                "max_crack_driving_index_over_3p6mpa": 0.0147,
                "max_mean_heat_dose": {"heat_dose_kj_m2": 31.60},
                "max_shell_mean_rise": {"shell_mean_rise_c": 1.804},
                "max_impact_impulse": {"impact_impulse_n_s": 27.91},
            },
            "full_cycle_wax_qoi": {
                "melt_completion": {
                    "first_full_melt_time_s": 409.0,
                    "latest_avg_liquid_fraction": 0.9973977417,
                },
                "dominant_risk_window": {
                    "time_s": 100.7,
                    "peak_effective_pressure_mpa": 4.465776,
                    "peak_wall_vm_p995_mpa": 42.4515,
                },
                "drainage_relief": {
                    "stress_drop_fraction_peak_to_latest_p995": 0.942,
                },
            },
        },
    )


def test_dewaxing_fluent_guidance_pack_compiles_guidance_chain(tmp_path):
    study = _write_study_pack(tmp_path / "study")
    _write_validation_pack(tmp_path / "validation")
    _write_iteration_pack(tmp_path / "iteration")
    _write_fluent_bridge_pack(tmp_path / "fluent")

    pack = compile_dewaxing_fluent_guidance_pack(
        study_pack=study,
        validation_pack=tmp_path / "validation",
        iteration_pack=tmp_path / "iteration",
        fluent_bridge_pack=tmp_path / "fluent",
        output_dir=tmp_path / "guidance",
        manuscript_title="Dewaxing Guidance Test",
    )

    assert pack["status"] == "success"
    assert pack["execution_boundary"]["new_fluent_calculation"] is False
    assert pack["execution_boundary"]["native_dewaxing_solver_rerun"] is False
    assert pack["summary"]["process_partition_count"] == 5
    assert pack["summary"]["fluent_validation_target_count"] == 7
    assert pack["summary"]["accepted_candidate_id"] == "path106_initial6"
    assert pack["summary"]["iteration_solver_runs"] == 46
    assert len(pack["tables"]) == 4
    assert len(pack["figures"]) == 1
    assert pack["figure_style"]["style_name"] == "nature_soft_statistical"
    assert Path(pack["artifacts"]["guidance_report"]).exists()
    assert Path(pack["artifacts"]["fluent_handoff_brief"]).exists()

    target_table = Path(pack["artifacts"]["tables_dir"]) / "table_02_fluent_validation_targets.md"
    workflow_figure = Path(pack["figures"][0]["path"])
    report = Path(pack["artifacts"]["guidance_report"]).read_text(encoding="utf-8")
    results = Path(pack["artifacts"]["results_section"]).read_text(encoding="utf-8")
    figure_text = workflow_figure.read_text(encoding="utf-8")
    assert "F2_risk_window_refinement" in target_table.read_text(encoding="utf-8")
    assert "FastFluent is the guidance layer" in report
    assert "FastFluent partitioned the dewaxing process" in results
    assert figure_text.startswith("<svg")
    assert "FastFluent-guided Fluent dewaxing workflow" in figure_text
    assert "retrospective confirmation layer" in figure_text
    assert any("FastFluent partitions" in item for item in pack["guidance_claims"]["supported_claims"])


def test_dewaxing_fluent_guidance_pack_cli(tmp_path, capsys):
    _write_study_pack(tmp_path / "study")
    _write_validation_pack(tmp_path / "validation")
    _write_iteration_pack(tmp_path / "iteration")
    _write_fluent_bridge_pack(tmp_path / "fluent")

    exit_code = fastcfd_main(
        [
            "compile-dewaxing-fluent-guidance-pack",
            "--study-pack",
            str(tmp_path / "study"),
            "--validation-pack",
            str(tmp_path / "validation"),
            "--iteration-pack",
            str(tmp_path / "iteration"),
            "--fluent-bridge-pack",
            str(tmp_path / "fluent"),
            "--output-dir",
            str(tmp_path / "cli_guidance"),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["summary"]["accepted_candidate_id"] == "path106_initial6"
    assert payload["summary"]["dominant_risk_time_s"] == 100.7
    assert Path(payload["artifacts"]["paper_outline"]).exists()
    assert Path(payload["figures"][0]["path"]).exists()
