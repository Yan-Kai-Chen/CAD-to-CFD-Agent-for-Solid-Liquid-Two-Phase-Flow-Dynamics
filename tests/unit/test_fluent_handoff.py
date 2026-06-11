import json
from pathlib import Path

from fromcad2cfd_solidworks.fluent_handoff import FLUENT_HANDOFF_SCHEMA_VERSION, write_fluent_handoff_from_report
from fromcad2cfd_solidworks.paths import project_output_dir, project_reports_dir


def test_write_fluent_handoff_from_successful_report():
    project = "phase8_unit_test"
    output_dir = project_output_dir(project)
    report_dir = project_reports_dir(project)

    part_path = output_dir / "unit_external.SLDPRT"
    step_path = output_dir / "unit_external.STEP"
    part_path.write_text("dummy part placeholder", encoding="utf-8")
    step_path.write_text("ISO-10303-21;", encoding="utf-8")

    source_report = report_dir / "unit_external_report.json"
    source_report.write_text(
        json.dumps(
            {
                "status": "success",
                "outputs": {"part": str(part_path), "step": str(step_path)},
                "plan": {
                    "schema_version": "fromcad2cfd_solidworks_plan_v1",
                    "project": project,
                    "model_name": "unit_external",
                    "template": {
                        "template_name": "external-cylinder-flow",
                        "parameters": {"domain_length_mm": 100},
                    },
                    "operations": [
                        {
                            "id": "fluid_domain_box",
                            "op": "create_rectangular_prism",
                            "args": {"width_mm": 100, "height_mm": 42, "depth_mm": 20},
                        }
                    ],
                },
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = write_fluent_handoff_from_report(source_report, project=project)

    assert result["status"] == "success"
    manifest_path = Path(result["outputs"]["json_manifest"])
    checklist_path = Path(result["outputs"]["markdown_checklist"])
    assert manifest_path.exists()
    assert checklist_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == FLUENT_HANDOFF_SCHEMA_VERSION
    assert manifest["handoff_scope"] == "geometry_only"
    assert manifest["geometry_files"]["step_exists"] is True
    assert any(hint["name"] == "inlet" for hint in manifest["boundary_hints"])


def test_fluent_handoff_recovers_template_from_source_plan():
    project = "phase8_unit_test"
    output_dir = project_output_dir(project)
    report_dir = project_reports_dir(project)

    step_path = output_dir / "unit_shell.STEP"
    step_path.write_text("ISO-10303-21;", encoding="utf-8")

    source_plan = report_dir / "unit_shell_plan.json"
    source_plan.write_text(
        json.dumps(
            {
                "template": {
                    "template_name": "shell-thicken-wall",
                    "parameters": {"shell_thickness_mm": 1.8},
                }
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    source_report = report_dir / "unit_shell_report.json"
    source_report.write_text(
        json.dumps(
            {
                "status": "success",
                "request": {"plan_path": str(source_plan)},
                "outputs": {"step": str(step_path)},
                "plan": {
                    "schema_version": "fromcad2cfd_solidworks_plan_v1",
                    "project": project,
                    "model_name": "unit_shell",
                    "operations": [],
                },
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = write_fluent_handoff_from_report(source_report, project=project)
    manifest = json.loads(Path(result["outputs"]["json_manifest"]).read_text(encoding="utf-8"))

    assert manifest["solidworks"]["template_name"] == "shell-thicken-wall"
    assert manifest["solidworks"]["template_parameters"]["shell_thickness_mm"] == 1.8

