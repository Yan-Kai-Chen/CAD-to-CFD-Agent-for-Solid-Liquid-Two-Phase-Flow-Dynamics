from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd.cli import main as root_main
import fromcad2cfd_nx.paths as nx_paths
from fromcad2cfd_nx.capabilities import capability_inventory, capability_markdown
from fromcad2cfd_nx.curve_surface import curve_surface_demo_job, transform_profile_pack_demo_job
from fromcad2cfd_nx.export import export_job, import_parasolid_job
from fromcad2cfd_nx.geometry import boolean_subtract_demo_recipe, cylinder_recipe, geometry_job_from_recipe, plate_with_hole_recipe
from fromcad2cfd_nx.inspect_model import inspection_job
from fromcad2cfd_nx.job_schema import NX_JOB_SCHEMA_VERSION, NXJournalJob, read_job
from fromcad2cfd_nx.preflight import capabilities_from_preflight, detect_nx_environment
from fromcad2cfd_nx.reverse_modeling import (
    cage_from_facet_body_step2_job,
    stl_import_convergent_step1_job,
    xoz_plane_combine_step3_step4_job,
)
from fromcad2cfd_nx.runner import prepare_journal_command, run_journal_command
from fromcad2cfd_nx.solid_modeling import (
    basic_solid_pack_demo_job,
    boolean_subtract_bodies_job,
    edge_wall_trim_pack_demo_job,
    fluid_domain_cylinder_demo_job,
    plane_cut_body_job,
)
from fromcad2cfd_nx.surface_repair import sew_sheet_bodies_job, thicken_face_job


def _fake_nx_install(root: Path) -> Path:
    base = root / "Siemens" / "NX"
    nxbin = base / "NXBIN"
    nxbin.mkdir(parents=True)
    (nxbin / "run_journal.exe").write_text("fake runner", encoding="utf-8")
    (nxbin / "ugraf.exe").write_text("fake nx", encoding="utf-8")
    return base


def test_detect_nx_environment_with_fake_install(tmp_path, monkeypatch):
    base = _fake_nx_install(tmp_path)
    monkeypatch.setenv("UGII_BASE_DIR", str(base))

    report = detect_nx_environment(extra_base_dirs=[base])
    capabilities = capabilities_from_preflight(report)

    assert report.status == "success"
    assert report.can_run_journal is True
    assert report.run_journal and report.run_journal.endswith("run_journal.exe")
    assert capabilities.backend == "nx"
    assert capabilities.supports_batch_runner is True


def test_nx_capability_inventory_is_machine_readable():
    inventory = capability_inventory()
    names = {item["name"] for item in inventory["capabilities"]}

    assert inventory["schema_version"] == "fromcad2cfd_nx_capabilities_v1"
    assert "basic_solid_pack" in names
    assert "fluid_domain_cylinder_demo" in names
    assert "reverse_step3_step4_xoy_plane_combine" in names
    assert "nx_mcp_safe_inventory" in names
    assert inventory["capability_count"] == len(inventory["capabilities"])


def test_nx_capability_markdown_mentions_boundaries():
    markdown = capability_markdown()

    assert "Siemens NX Capability Inventory" in markdown
    assert "No arbitrary NXOpen execution is exposed" in markdown
    assert "basic_solid_pack" in markdown


def test_nx_job_schema_round_trip(tmp_path):
    job = NXJournalJob(
        operation="create_cylinder",
        output_dir=str(tmp_path / "output"),
        model_name="unit_cylinder",
        parameters={"radius_mm": 10.0, "height_mm": 20.0},
    )
    path = job.write(tmp_path / "job.json")
    loaded = read_job(path)

    assert loaded.schema_version == NX_JOB_SCHEMA_VERSION
    assert loaded.operation == "create_cylinder"
    assert loaded.parameters["radius_mm"] == 10.0


def test_geometry_job_builders(tmp_path):
    cylinder = cylinder_recipe(radius_mm=3.0, height_mm=9.0, model_name="cyl")
    plate = plate_with_hole_recipe(width_mm=20.0, height_mm=10.0, thickness_mm=2.0, hole_radius_mm=1.0)
    boolean = boolean_subtract_demo_recipe(outer_radius_mm=30.0, outer_height_mm=50.0, tool_radius_mm=5.0, tool_height_mm=60.0)

    cylinder_job = geometry_job_from_recipe(cylinder, output_dir=tmp_path)
    plate_job = geometry_job_from_recipe(plate, output_dir=tmp_path)
    boolean_job = geometry_job_from_recipe(boolean, output_dir=tmp_path)

    assert cylinder_job.operation == "create_cylinder"
    assert cylinder_job.parameters["height_mm"] == 9.0
    assert plate_job.operation == "create_plate_with_hole"
    assert boolean_job.operation == "create_boolean_subtract_demo"
    assert boolean_job.parameters["tool_radius_mm"] == 5.0


def test_inspection_job_builder(tmp_path):
    source = tmp_path / "source.prt"
    source.write_text("placeholder", encoding="utf-8")

    job = inspection_job(source, tmp_path / "output")

    assert job.operation == "inspect_model"
    assert job.input_file == str(source)
    assert job.metadata["operation_family"] == "surface_repair"


def test_boolean_subtract_bodies_job_builder(tmp_path):
    source = tmp_path / "source.prt"
    source.write_text("placeholder", encoding="utf-8")

    job = boolean_subtract_bodies_job(
        source,
        tmp_path / "output",
        target_body_index=1,
        tool_body_indices=(2, 3),
        expected_body_count=1,
    )

    assert job.operation == "boolean_subtract_bodies"
    assert job.input_file == str(source)
    assert job.parameters["target_body_index"] == 1
    assert job.parameters["tool_body_indices"] == [2, 3]
    assert job.metadata["selector_basis"] == "1-based body index after copied-model inspection"


def test_basic_solid_pack_demo_job_builder(tmp_path):
    job = basic_solid_pack_demo_job(
        tmp_path / "output",
        model_name="basic_pack",
        block_length_mm=21.0,
        sphere_diameter_mm=19.0,
        cone_base_diameter_mm=18.0,
        cone_top_diameter_mm=5.0,
        boolean_overlap_mm=10.0,
    )

    assert job.operation == "create_basic_solid_pack_demo"
    assert job.model_name == "basic_pack"
    assert job.parameters["block_length_mm"] == 21.0
    assert job.parameters["sphere_diameter_mm"] == 19.0
    assert job.metadata["capability_pack"] == "basic_solid_modeling"
    assert "boolean_unite" in job.metadata["covered_operations"]
    assert "copy_translate" in job.metadata["covered_operations"]


def test_fluid_domain_cylinder_demo_job_builder(tmp_path):
    job = fluid_domain_cylinder_demo_job(
        tmp_path / "output",
        model_name="fluid_domain",
        domain_radius_mm=500.0,
        domain_length_mm=1200.0,
        obstacle_radius_mm=12.0,
        obstacle_length_mm=1400.0,
    )

    assert job.operation == "create_boolean_subtract_demo"
    assert job.model_name == "fluid_domain"
    assert job.parameters["outer_radius_mm"] == 500.0
    assert job.parameters["outer_height_mm"] == 1200.0
    assert job.parameters["tool_radius_mm"] == 12.0
    assert job.parameters["tool_height_mm"] == 1400.0
    assert job.metadata["operation_family"] == "cfd_domain_construction"
    assert job.metadata["capability_pack"] == "fluid_domain_cylinder_demo"
    assert "boolean_subtract" in job.metadata["covered_operations"]


def test_edge_wall_trim_pack_demo_job_builder(tmp_path):
    job = edge_wall_trim_pack_demo_job(
        tmp_path / "output",
        model_name="edge_wall_trim",
        edge_radius_mm=1.5,
        chamfer_offset_mm=1.25,
        shell_thickness_mm=0.75,
        taper_base_diameter_mm=20.0,
        taper_top_diameter_mm=12.0,
        plane_cut_x_mm=95.0,
    )

    assert job.operation == "create_edge_wall_trim_pack_demo"
    assert job.model_name == "edge_wall_trim"
    assert job.parameters["edge_radius_mm"] == 1.5
    assert job.parameters["plane_cut_x_mm"] == 95.0
    assert job.metadata["capability_pack"] == "edge_wall_trim_import"
    assert "plane_cut_by_cutter" in job.metadata["covered_operations"]
    assert "parasolid_import_to_prt" in job.metadata["covered_operations"]


def test_plane_cut_body_job_builder(tmp_path):
    source = tmp_path / "source.prt"
    source.write_text("placeholder", encoding="utf-8")

    job = plane_cut_body_job(
        source,
        tmp_path / "output",
        body_index=2,
        plane_axis="z",
        plane_offset_mm=4.5,
        remove_side="negative",
        cutter_extent_mm=250.0,
    )

    assert job.operation == "plane_cut_body"
    assert job.input_file == str(source)
    assert job.parameters["body_index"] == 2
    assert job.parameters["plane_axis"] == "z"
    assert job.parameters["remove_side"] == "negative"
    assert job.metadata["trim_type"] == "axis_aligned_plane_cut_by_subtract_cutter"


def test_thicken_face_job_builder(tmp_path):
    source = tmp_path / "surface_source.prt"
    source.write_text("placeholder", encoding="utf-8")

    job = thicken_face_job(source, tmp_path / "output", body_index=1, face_index=2, thickness_mm=1.5)

    assert job.operation == "thicken_face"
    assert job.input_file == str(source)
    assert job.parameters["face_index"] == 2
    assert job.parameters["thickness_mm"] == 1.5
    assert job.metadata["surface_operation"] == "thicken"


def test_sew_sheet_bodies_job_builder(tmp_path):
    source = tmp_path / "sheet_source.prt"
    source.write_text("placeholder", encoding="utf-8")

    job = sew_sheet_bodies_job(
        source,
        tmp_path / "output",
        target_sheet_body_index=2,
        tool_sheet_body_indices=(3, 4),
        tolerance_mm=0.02,
        expected_min_solid_bodies=1,
        expected_max_sheet_bodies=0,
    )

    assert job.operation == "sew_sheet_bodies"
    assert job.input_file == str(source)
    assert job.parameters["target_sheet_body_index"] == 2
    assert job.parameters["tool_sheet_body_indices"] == [3, 4]
    assert job.parameters["tolerance_mm"] == 0.02
    assert job.parameters["expected_max_sheet_bodies"] == 0
    assert job.metadata["surface_operation"] == "sew"


def test_curve_surface_demo_job_builder(tmp_path):
    job = curve_surface_demo_job(
        tmp_path / "output",
        model_name="curve_surface",
        rectangle_width_mm=42.0,
        rectangle_height_mm=24.0,
        circle_radius_mm=5.0,
        ellipse_major_radius_mm=9.0,
        ellipse_minor_radius_mm=4.0,
    )

    assert job.operation == "create_curve_surface_demo"
    assert job.model_name == "curve_surface"
    assert job.parameters["rectangle_width_mm"] == 42.0
    assert job.parameters["circle_radius_mm"] == 5.0
    assert job.metadata["operation_family"] == "curve_surface"
    assert job.metadata["surface_operation"] == "bounded_plane_from_closed_curves"


def test_transform_profile_pack_demo_job_builder(tmp_path):
    job = transform_profile_pack_demo_job(
        tmp_path / "output",
        model_name="transform_profile",
        rotate_angle_deg=35.0,
        sweep_height_mm=31.0,
        loft_height_mm=27.0,
        revolve_angle_deg=270.0,
    )

    assert job.operation == "create_transform_profile_pack_demo"
    assert job.model_name == "transform_profile"
    assert job.parameters["rotate_angle_deg"] == 35.0
    assert job.parameters["sweep_height_mm"] == 31.0
    assert job.metadata["capability_pack"] == "transform_profile_modeling"
    assert "rotate_copy" in job.metadata["covered_operations"]
    assert "loft_through_curves" in job.metadata["covered_operations"]


def test_stl_import_convergent_step1_job_builder(tmp_path):
    source = tmp_path / "source.stl"
    source.write_text("solid empty\nendsolid empty\n", encoding="utf-8")

    job = stl_import_convergent_step1_job(
        source,
        tmp_path / "output",
        model_name="step1_convergent",
        minimum_angle_folded_facets_deg=15.0,
        minimum_facet_number=100,
    )

    assert job.operation == "reverse_step1_import_stl_convergent"
    assert job.input_file == str(source)
    assert job.model_name == "step1_convergent"
    assert job.parameters["facet_body_output_type"] == "Convergent"
    assert job.parameters["nx_facet_body_type"] == "Psm"
    assert job.parameters["cleanup"] is True
    assert job.parameters["minimum_angle_folded_facets_deg"] == 15.0
    assert job.parameters["minimum_facet_number"] == 100
    assert job.parameters["stl_file_units"] == "Millimeters"
    assert job.metadata["reverse_modeling_step"] == "step1_import_stl_as_convergent_body"


def test_cage_from_facet_body_step2_job_builder(tmp_path):
    source = tmp_path / "source_step1.prt"
    source.write_text("placeholder", encoding="utf-8")

    job = cage_from_facet_body_step2_job(
        source,
        tmp_path / "output",
        model_name="step2_cage",
        average_size_mm=10.0,
    )

    assert job.operation == "reverse_step2_cage_from_facet_body"
    assert job.input_file == str(source)
    assert job.model_name == "step2_cage"
    assert job.export_formats == ("NX_PRT",)
    assert job.parameters["average_size_mm"] == 10.0
    assert job.parameters["body_selector"] == "all_convergent"
    assert job.parameters["requires_license"] == "nx_subdivision"
    assert job.metadata["reverse_modeling_step"] == "step2_cage_from_facet_body"


def test_xoz_plane_combine_step3_step4_job_builder(tmp_path):
    source = tmp_path / "step3_example.x_t"
    source.write_text("placeholder", encoding="utf-8")

    job = xoz_plane_combine_step3_step4_job(
        source,
        tmp_path / "output",
        model_name="step3_step4",
        square_size_mm=1000.0,
        plane_offset_z_mm=5.0,
    )

    assert job.operation == "reverse_step3_step4_xoz_plane_combine"
    assert job.input_file == str(source)
    assert job.model_name == "step3_step4"
    assert job.export_formats == ("NX_PRT", "PARASOLID_ATTEMPT")
    assert job.parameters["square_size_mm"] == 1000.0
    assert job.parameters["plane_offset_z_mm"] == 5.0
    assert job.parameters["body_selector"] == "all_imported_sheet_bodies"
    assert job.parameters["nx_builder"] == "NXOpen.Features.CombineSheetsBuilder"
    assert job.metadata["reverse_modeling_step"] == "step3_step4_xoy_bounded_plane_and_combine"
    assert job.metadata["user_taught_settings"]["step3_plane"] == "XOY"
    assert job.metadata["user_taught_settings"]["legacy_command_name"] == "write-reverse-step3-step4-xoz-plane-combine-job"


def test_export_job_normalizes_format(tmp_path):
    job = export_job(tmp_path / "model.prt", tmp_path / "output", "x_t")

    assert job.operation == "export_geometry"
    assert job.export_formats == ("PARASOLID",)


def test_import_parasolid_job_builder(tmp_path):
    source = tmp_path / "model.x_t"
    source.write_text("placeholder", encoding="utf-8")

    job = import_parasolid_job(source, tmp_path / "output", model_name="imported_model")

    assert job.operation == "import_parasolid"
    assert job.input_file == str(source)
    assert job.model_name == "imported_model"
    assert job.metadata["source_format"] == "PARASOLID"
    assert job.metadata["target_format"] == "NX_PRT"


def test_prepare_journal_command_and_skip_execution(tmp_path):
    run_journal = tmp_path / "run_journal.exe"
    journal = tmp_path / "journal.py"
    job_path = tmp_path / "job.json"
    run_journal.write_text("fake runner", encoding="utf-8")
    journal.write_text("print('fake')", encoding="utf-8")
    job_path.write_text(json.dumps({"schema_version": NX_JOB_SCHEMA_VERSION}), encoding="utf-8")

    command = prepare_journal_command(job_path, journal, run_journal=str(run_journal))
    result = run_journal_command(command, execute=False)

    assert command.argv() == [str(run_journal), str(journal), "-args", str(job_path)]
    assert result.status == "skipped"
    assert "execute=False" in result.message


def test_root_cli_exposes_nx_preflight(capsys):
    exit_code = root_main(["nx", "preflight", "--no-report"])

    captured = capsys.readouterr()
    assert exit_code in {0, 2}
    assert '"backend": "nx"' in captured.out


def test_root_cli_writes_fluid_domain_demo_job(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(nx_paths, "PROJECTS_ROOT", tmp_path)

    exit_code = root_main(
        [
            "nx",
            "write-fluid-domain-demo-job",
            "--project",
            "unit_cli_fluid_domain",
            "--model-name",
            "unit_cli_fluid_domain",
            "--domain-radius-mm",
            "500",
            "--domain-length-mm",
            "1200",
            "--obstacle-radius-mm",
            "10",
            "--obstacle-length-mm",
            "1400",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["job"]["operation"] == "create_boolean_subtract_demo"
    assert payload["job"]["metadata"]["capability_pack"] == "fluid_domain_cylinder_demo"
