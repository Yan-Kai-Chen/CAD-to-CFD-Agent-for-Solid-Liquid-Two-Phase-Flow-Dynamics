"""Safe Siemens NX MCP tool declarations and handlers."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from fromcad2cfd_nx.capabilities import capability_inventory, capability_markdown
from fromcad2cfd_nx.curve_surface import curve_surface_demo_job, transform_profile_pack_demo_job
from fromcad2cfd_nx.export import import_parasolid_job
from fromcad2cfd_nx.geometry import boolean_subtract_demo_recipe, cylinder_recipe, geometry_job_from_recipe, plate_with_hole_recipe
from fromcad2cfd_nx.inspect_model import inspection_job
from fromcad2cfd_nx.job_schema import NXJournalJob, read_job
from fromcad2cfd_nx.paths import PROJECTS_ROOT, logs_dir, project_input_dir, project_output_dir, project_reports_dir, unique_path
from fromcad2cfd_nx.preflight import run_preflight
from fromcad2cfd_nx.reverse_modeling import cage_from_facet_body_step2_job, stl_import_convergent_step1_job, xoz_plane_combine_step3_step4_job
from fromcad2cfd_nx.runner import prepare_journal_command
from fromcad2cfd_nx.solid_modeling import (
    basic_solid_pack_demo_job,
    boolean_subtract_bodies_job,
    edge_wall_trim_pack_demo_job,
    fluid_domain_cylinder_demo_job,
    plane_cut_body_job,
)
from fromcad2cfd_nx.surface_repair import sew_sheet_bodies_job, thicken_face_job


JOURNALS_DIR = Path(__file__).resolve().parents[1] / "fromcad2cfd_nx" / "journals"

JOURNAL_FILES_BY_OPERATION = {
    "create_cylinder": "create_cylinder.py",
    "create_boolean_subtract_demo": "create_boolean_subtract_demo.py",
    "create_basic_solid_pack_demo": "create_basic_solid_pack_demo.py",
    "create_edge_wall_trim_pack_demo": "create_edge_wall_trim_pack_demo.py",
    "boolean_subtract_bodies": "boolean_subtract_bodies.py",
    "plane_cut_body": "plane_cut_body.py",
    "import_parasolid": "import_parasolid.py",
    "inspect_model": "inspect_model.py",
    "thicken_face": "thicken_face.py",
    "sew_sheet_bodies": "sew_sheet_bodies.py",
    "create_curve_surface_demo": "create_curve_surface_demo.py",
    "create_transform_profile_pack_demo": "create_transform_profile_pack_demo.py",
    "reverse_step1_import_stl_convergent": "import_stl_convergent_step1.py",
    "reverse_step2_cage_from_facet_body": "cage_from_facet_body_step2.py",
    "reverse_step3_step4_xoz_plane_combine": "xoz_plane_combine_step3_step4.py",
}

ALLOWED_TOOLS = [
    "fromcad2cfd_nx_tool_inventory",
    "fromcad2cfd_nx_capabilities",
    "fromcad2cfd_nx_preflight",
    "fromcad2cfd_nx_write_geometry_job",
    "fromcad2cfd_nx_write_solid_modeling_job",
    "fromcad2cfd_nx_write_basic_solid_pack_job",
    "fromcad2cfd_nx_write_fluid_domain_demo_job",
    "fromcad2cfd_nx_write_edge_wall_trim_pack_job",
    "fromcad2cfd_nx_write_boolean_subtract_job",
    "fromcad2cfd_nx_write_plane_cut_body_job",
    "fromcad2cfd_nx_write_import_parasolid_job",
    "fromcad2cfd_nx_write_surface_inspection_job",
    "fromcad2cfd_nx_write_thicken_face_job",
    "fromcad2cfd_nx_write_sew_sheet_bodies_job",
    "fromcad2cfd_nx_write_curve_surface_demo_job",
    "fromcad2cfd_nx_write_transform_profile_pack_job",
    "fromcad2cfd_nx_write_reverse_step1_stl_import_job",
    "fromcad2cfd_nx_write_reverse_step2_cage_from_facet_body_job",
    "fromcad2cfd_nx_write_reverse_step3_step4_xoz_plane_combine_job",
    "fromcad2cfd_nx_prepare_journal_command",
    "fromcad2cfd_nx_inspect_model",
    "fromcad2cfd_nx_get_last_report",
]

DISABLED_TOOLS = [
    "execute_python",
    "raw_nxopen_call",
    "run_arbitrary_journal",
    "record_journal",
    "delete_file",
    "overwrite_file",
    "fromcad2cfd_nx_safe_edit_expression",
    "fromcad2cfd_nx_export_geometry",
]

TOOL_DESCRIPTIONS = {
    "fromcad2cfd_nx_tool_inventory": "Return the safe NX MCP tool inventory and disabled tool names.",
    "fromcad2cfd_nx_capabilities": "Return the Siemens NX capability inventory as JSON or Markdown.",
    "fromcad2cfd_nx_preflight": "Detect NX installation and journal-runner availability without opening models.",
    "fromcad2cfd_nx_write_geometry_job": "Write a controlled public-safe NX geometry job JSON.",
    "fromcad2cfd_nx_write_solid_modeling_job": "Write one of the controlled NX solid-modeling capability-pack jobs.",
    "fromcad2cfd_nx_write_basic_solid_pack_job": "Write a validated NX job for block, sphere, cone, boolean unite/intersect, and copy-translate.",
    "fromcad2cfd_nx_write_fluid_domain_demo_job": "Write a public-safe cylindrical CFD fluid-domain job by subtracting a centered cylindrical obstacle from a cylindrical domain.",
    "fromcad2cfd_nx_write_edge_wall_trim_pack_job": "Write a validated NX job for edge blend, chamfer, shell, shell-face, controlled taper/frustum, plane cut, Parasolid export, and Parasolid import coverage.",
    "fromcad2cfd_nx_write_boolean_subtract_job": "Write a copied-model NX boolean subtract job using explicit target/tool body selectors.",
    "fromcad2cfd_nx_write_plane_cut_body_job": "Write a copied-model NX plane-cut job that removes one side of an axis-aligned plane through a generated cutter body.",
    "fromcad2cfd_nx_write_import_parasolid_job": "Write a controlled NX job that imports Parasolid `.x_t` or `.x_b` into a new `.prt` and verifies re-export.",
    "fromcad2cfd_nx_write_surface_inspection_job": "Write a copied-model NX inspection job JSON before any surface repair.",
    "fromcad2cfd_nx_write_thicken_face_job": "Write a copied-model NX thicken job using explicit body/face selectors.",
    "fromcad2cfd_nx_write_sew_sheet_bodies_job": "Write a copied-model NX sew job using explicit sheet-body selectors and tolerance.",
    "fromcad2cfd_nx_write_curve_surface_demo_job": "Write a synthetic NX job for line/arc/ellipse curves and a bounded-plane sheet.",
    "fromcad2cfd_nx_write_transform_profile_pack_job": "Write a validated NX job for rotate copy, mirror body, project curve, intersection curve, revolve, sweep, and loft coverage.",
    "fromcad2cfd_nx_write_reverse_step1_stl_import_job": "Write a copied-input NX reverse-modeling Step 1 job that imports STL as cleaned convergent bodies.",
    "fromcad2cfd_nx_write_reverse_step2_cage_from_facet_body_job": "Write a copied-input NX reverse-modeling Step 2 job that runs Cage from Facet Body.",
    "fromcad2cfd_nx_write_reverse_step3_step4_xoz_plane_combine_job": "Write a copied-input NX reverse-modeling Step 3/4 XOY plane CombineSheets job. The xoz name is legacy-compatible.",
    "fromcad2cfd_nx_prepare_journal_command": "Prepare but do not execute a run_journal command for a controlled job.",
    "fromcad2cfd_nx_inspect_model": "Alias for writing a copied-model NX inspection job.",
    "fromcad2cfd_nx_get_last_report": "Return the newest NX JSON and Markdown reports under project folders.",
}


def tool_inventory() -> dict[str, object]:
    return {
        "allowed_tools": ALLOWED_TOOLS,
        "disabled_tools": DISABLED_TOOLS,
        "tool_descriptions": TOOL_DESCRIPTIONS,
        "journal_operations": dict(JOURNAL_FILES_BY_OPERATION),
    }


def _parse_int_csv(value: str) -> list[int]:
    values = [int(item.strip()) for item in str(value).split(",") if item.strip()]
    if not values:
        raise ValueError("At least one index is required.")
    return values


def _copy_input_to_project(input_file: str, project: str) -> Path:
    source = Path(input_file)
    if not source.exists():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    target = unique_path(project_input_dir(project) / source.name)
    shutil.copy2(source, target)
    return target


def _write_job(project: str, job: NXJournalJob) -> dict[str, Any]:
    job_path = unique_path(project_input_dir(project) / f"{job.model_name}_job.json")
    job.write(job_path)
    return {"status": "success", "job_path": str(job_path), "job": job.to_dict()}


def _response_for_copied_input(project: str, copied_input: Path, original_input: str, job: NXJournalJob) -> dict[str, Any]:
    job.metadata["original_source_file"] = str(Path(original_input))
    job.metadata["copied_input_file"] = str(copied_input)
    return _write_job(project, job)


def _journal_path_for_operation(operation: str) -> Path:
    journal_name = JOURNAL_FILES_BY_OPERATION.get(operation)
    if not journal_name:
        raise ValueError(f"No controlled journal is registered for operation: {operation}")
    journal = JOURNALS_DIR / journal_name
    if not journal.exists():
        raise FileNotFoundError(f"Registered NX journal does not exist: {journal}")
    return journal


def fromcad2cfd_nx_tool_inventory() -> dict[str, object]:
    return tool_inventory()


def fromcad2cfd_nx_capabilities(format: str = "json") -> dict[str, Any] | str:
    if format == "markdown":
        return capability_markdown()
    if format != "json":
        raise ValueError("format must be 'json' or 'markdown'.")
    return capability_inventory()


def fromcad2cfd_nx_preflight(write_reports: bool = False) -> dict[str, Any]:
    return run_preflight(write_reports=write_reports).to_dict()


def fromcad2cfd_nx_write_geometry_job(
    recipe: str = "cylinder",
    project: str = "nx_geometry_demo",
    model_name: str | None = None,
    radius_mm: float = 10.0,
    height_mm: float = 20.0,
    width_mm: float = 60.0,
    thickness_mm: float = 5.0,
    hole_radius_mm: float = 5.0,
    outer_radius_mm: float = 50.0,
    outer_height_mm: float = 100.0,
    tool_radius_mm: float = 10.0,
    tool_height_mm: float = 120.0,
) -> dict[str, Any]:
    if recipe == "cylinder":
        geometry_recipe = cylinder_recipe(radius_mm=radius_mm, height_mm=height_mm, model_name=model_name or "nx_test_cylinder")
    elif recipe == "plate-with-hole":
        geometry_recipe = plate_with_hole_recipe(
            width_mm=width_mm,
            height_mm=height_mm,
            thickness_mm=thickness_mm,
            hole_radius_mm=hole_radius_mm,
            model_name=model_name or "nx_plate_with_hole",
        )
    elif recipe == "boolean-subtract-demo":
        geometry_recipe = boolean_subtract_demo_recipe(
            outer_radius_mm=outer_radius_mm,
            outer_height_mm=outer_height_mm,
            tool_radius_mm=tool_radius_mm,
            tool_height_mm=tool_height_mm,
            model_name=model_name or "nx_boolean_subtract_demo",
        )
    else:
        raise ValueError("recipe must be one of: cylinder, plate-with-hole, boolean-subtract-demo.")
    return _write_job(project, geometry_job_from_recipe(geometry_recipe, output_dir=project_output_dir(project)))


def fromcad2cfd_nx_write_solid_modeling_job(pack: str = "basic", project: str = "nx_solid_modeling_demo", model_name: str | None = None) -> dict[str, Any]:
    if pack == "basic":
        return fromcad2cfd_nx_write_basic_solid_pack_job(project=project, model_name=model_name or "nx_basic_solid_pack_demo")
    if pack == "edge-wall-trim":
        return fromcad2cfd_nx_write_edge_wall_trim_pack_job(project=project, model_name=model_name or "nx_edge_wall_trim_pack_demo")
    if pack == "transform-profile":
        return fromcad2cfd_nx_write_transform_profile_pack_job(project=project, model_name=model_name or "nx_transform_profile_pack_demo")
    if pack == "fluid-domain":
        return fromcad2cfd_nx_write_fluid_domain_demo_job(project=project, model_name=model_name or "nx_fluid_domain_cylinder_demo")
    raise ValueError("pack must be one of: basic, edge-wall-trim, transform-profile, fluid-domain.")


def fromcad2cfd_nx_write_basic_solid_pack_job(project: str = "nx_basic_solid_pack_demo", model_name: str = "nx_basic_solid_pack_demo") -> dict[str, Any]:
    return _write_job(project, basic_solid_pack_demo_job(output_dir=project_output_dir(project), model_name=model_name))


def fromcad2cfd_nx_write_fluid_domain_demo_job(
    project: str = "nx_fluid_domain_cylinder_demo",
    model_name: str = "nx_fluid_domain_cylinder_demo",
    domain_radius_mm: float = 500.0,
    domain_length_mm: float = 1200.0,
    obstacle_radius_mm: float = 10.0,
    obstacle_length_mm: float = 1400.0,
) -> dict[str, Any]:
    return _write_job(
        project,
        fluid_domain_cylinder_demo_job(
            output_dir=project_output_dir(project),
            model_name=model_name,
            domain_radius_mm=domain_radius_mm,
            domain_length_mm=domain_length_mm,
            obstacle_radius_mm=obstacle_radius_mm,
            obstacle_length_mm=obstacle_length_mm,
        ),
    )


def fromcad2cfd_nx_write_edge_wall_trim_pack_job(project: str = "nx_edge_wall_trim_pack_demo", model_name: str = "nx_edge_wall_trim_pack_demo") -> dict[str, Any]:
    return _write_job(project, edge_wall_trim_pack_demo_job(output_dir=project_output_dir(project), model_name=model_name))


def fromcad2cfd_nx_write_boolean_subtract_job(
    input_file: str,
    project: str = "nx_boolean_subtract",
    model_name: str | None = None,
    target_body_index: int = 1,
    tool_body_indices: str = "2",
    expected_body_count: int = 1,
    retain_target_body: bool = False,
    retain_tool_bodies: bool = False,
) -> dict[str, Any]:
    copied_input = _copy_input_to_project(input_file, project)
    job = boolean_subtract_bodies_job(
        copied_input,
        output_dir=project_output_dir(project),
        model_name=model_name,
        target_body_index=target_body_index,
        tool_body_indices=_parse_int_csv(tool_body_indices),
        expected_body_count=expected_body_count,
        retain_target_body=retain_target_body,
        retain_tool_bodies=retain_tool_bodies,
    )
    return _response_for_copied_input(project, copied_input, input_file, job)


def fromcad2cfd_nx_write_plane_cut_body_job(
    input_file: str,
    project: str = "nx_plane_cut",
    model_name: str | None = None,
    body_index: int = 1,
    plane_axis: str = "x",
    plane_offset_mm: float = 0.0,
    remove_side: str = "positive",
    cutter_extent_mm: float = 1000.0,
) -> dict[str, Any]:
    copied_input = _copy_input_to_project(input_file, project)
    job = plane_cut_body_job(
        copied_input,
        output_dir=project_output_dir(project),
        model_name=model_name,
        body_index=body_index,
        plane_axis=plane_axis,
        plane_offset_mm=plane_offset_mm,
        remove_side=remove_side,
        cutter_extent_mm=cutter_extent_mm,
    )
    return _response_for_copied_input(project, copied_input, input_file, job)


def fromcad2cfd_nx_write_import_parasolid_job(input_file: str, project: str = "nx_import_parasolid", model_name: str | None = None) -> dict[str, Any]:
    copied_input = _copy_input_to_project(input_file, project)
    job = import_parasolid_job(copied_input, output_dir=project_output_dir(project), model_name=model_name)
    return _response_for_copied_input(project, copied_input, input_file, job)


def fromcad2cfd_nx_write_surface_inspection_job(input_file: str, project: str = "nx_inspection_project", model_name: str | None = None) -> dict[str, Any]:
    copied_input = _copy_input_to_project(input_file, project)
    job = inspection_job(copied_input, output_dir=project_output_dir(project), model_name=model_name)
    return _response_for_copied_input(project, copied_input, input_file, job)


def fromcad2cfd_nx_inspect_model(input_file: str, project: str = "nx_inspection_project", model_name: str | None = None) -> dict[str, Any]:
    return fromcad2cfd_nx_write_surface_inspection_job(input_file=input_file, project=project, model_name=model_name)


def fromcad2cfd_nx_write_thicken_face_job(
    input_file: str,
    project: str = "nx_thicken_face",
    model_name: str | None = None,
    body_index: int = 1,
    face_index: int = 1,
    thickness_mm: float = 2.0,
    extract_face_first: bool = True,
    expected_min_solid_bodies: int = 1,
) -> dict[str, Any]:
    copied_input = _copy_input_to_project(input_file, project)
    job = thicken_face_job(
        copied_input,
        output_dir=project_output_dir(project),
        model_name=model_name,
        body_index=body_index,
        face_index=face_index,
        thickness_mm=thickness_mm,
        extract_face_first=extract_face_first,
        expected_min_solid_bodies=expected_min_solid_bodies,
    )
    return _response_for_copied_input(project, copied_input, input_file, job)


def fromcad2cfd_nx_write_sew_sheet_bodies_job(
    input_file: str,
    project: str = "nx_sew_sheet_bodies",
    model_name: str | None = None,
    target_sheet_body_index: int = 1,
    tool_sheet_body_indices: str = "2",
    tolerance_mm: float = 0.01,
    expected_min_solid_bodies: int = 1,
    expected_max_sheet_bodies: int | None = None,
) -> dict[str, Any]:
    copied_input = _copy_input_to_project(input_file, project)
    job = sew_sheet_bodies_job(
        copied_input,
        output_dir=project_output_dir(project),
        model_name=model_name,
        target_sheet_body_index=target_sheet_body_index,
        tool_sheet_body_indices=_parse_int_csv(tool_sheet_body_indices),
        tolerance_mm=tolerance_mm,
        expected_min_solid_bodies=expected_min_solid_bodies,
        expected_max_sheet_bodies=expected_max_sheet_bodies,
    )
    return _response_for_copied_input(project, copied_input, input_file, job)


def fromcad2cfd_nx_write_curve_surface_demo_job(project: str = "nx_curve_surface_demo", model_name: str = "nx_curve_surface_demo") -> dict[str, Any]:
    return _write_job(project, curve_surface_demo_job(output_dir=project_output_dir(project), model_name=model_name))


def fromcad2cfd_nx_write_transform_profile_pack_job(project: str = "nx_transform_profile_pack_demo", model_name: str = "nx_transform_profile_pack_demo") -> dict[str, Any]:
    return _write_job(project, transform_profile_pack_demo_job(output_dir=project_output_dir(project), model_name=model_name))


def fromcad2cfd_nx_write_reverse_step1_stl_import_job(
    input_file: str,
    project: str = "nx_reverse_step1_stl_import",
    model_name: str | None = None,
    cleanup: bool = True,
    minimum_angle_folded_facets_deg: float = 15.0,
    minimum_facet_number: int = 100,
    stl_file_units: str = "Millimeters",
) -> dict[str, Any]:
    copied_input = _copy_input_to_project(input_file, project)
    job = stl_import_convergent_step1_job(
        copied_input,
        output_dir=project_output_dir(project),
        model_name=model_name,
        cleanup=cleanup,
        minimum_angle_folded_facets_deg=minimum_angle_folded_facets_deg,
        minimum_facet_number=minimum_facet_number,
        stl_file_units=stl_file_units,
    )
    return _response_for_copied_input(project, copied_input, input_file, job)


def fromcad2cfd_nx_write_reverse_step2_cage_from_facet_body_job(
    input_file: str,
    project: str = "nx_reverse_step2_cage_from_facet_body",
    model_name: str | None = None,
    average_size_mm: float = 10.0,
    body_selector: str = "all_convergent",
) -> dict[str, Any]:
    copied_input = _copy_input_to_project(input_file, project)
    job = cage_from_facet_body_step2_job(
        copied_input,
        output_dir=project_output_dir(project),
        model_name=model_name,
        average_size_mm=average_size_mm,
        body_selector=body_selector,
    )
    return _response_for_copied_input(project, copied_input, input_file, job)


def fromcad2cfd_nx_write_reverse_step3_step4_xoz_plane_combine_job(
    input_file: str,
    project: str = "nx_reverse_step3_step4_xoz_plane_combine",
    model_name: str | None = None,
    square_size_mm: float = 1000.0,
    plane_offset_z_mm: float = 5.0,
    body_selector: str = "all_imported_sheet_bodies",
    run_combine: bool = True,
    export_parasolid: bool = True,
) -> dict[str, Any]:
    copied_input = _copy_input_to_project(input_file, project)
    job = xoz_plane_combine_step3_step4_job(
        copied_input,
        output_dir=project_output_dir(project),
        model_name=model_name,
        square_size_mm=square_size_mm,
        plane_offset_z_mm=plane_offset_z_mm,
        body_selector=body_selector,
        run_combine=run_combine,
        export_parasolid=export_parasolid,
    )
    return _response_for_copied_input(project, copied_input, input_file, job)


def fromcad2cfd_nx_prepare_journal_command(job_path: str, run_journal: str | None = None) -> dict[str, Any]:
    job = read_job(job_path)
    journal = _journal_path_for_operation(job.operation)
    command = prepare_journal_command(job_path=job_path, journal_path=journal, run_journal=run_journal)
    return {
        "status": "success",
        "operation": job.operation,
        "job_path": str(job_path),
        "journal_path": str(journal),
        "argv": command.argv(),
        "execute": False,
    }


def fromcad2cfd_nx_get_last_report(project: str | None = None) -> dict[str, Any]:
    roots = [project_reports_dir(project)] if project else [PROJECTS_ROOT, logs_dir()]
    json_reports: list[Path] = []
    markdown_reports: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        json_reports.extend(root.rglob("*.json"))
        markdown_reports.extend(root.rglob("*.md"))

    def newest(paths: list[Path]) -> str | None:
        if not paths:
            return None
        return str(max(paths, key=lambda path: path.stat().st_mtime))

    return {
        "status": "success",
        "project": project,
        "json": newest(json_reports),
        "markdown": newest(markdown_reports),
    }


MCP_TOOL_FUNCTIONS = [
    fromcad2cfd_nx_tool_inventory,
    fromcad2cfd_nx_capabilities,
    fromcad2cfd_nx_preflight,
    fromcad2cfd_nx_write_geometry_job,
    fromcad2cfd_nx_write_solid_modeling_job,
    fromcad2cfd_nx_write_basic_solid_pack_job,
    fromcad2cfd_nx_write_fluid_domain_demo_job,
    fromcad2cfd_nx_write_edge_wall_trim_pack_job,
    fromcad2cfd_nx_write_boolean_subtract_job,
    fromcad2cfd_nx_write_plane_cut_body_job,
    fromcad2cfd_nx_write_import_parasolid_job,
    fromcad2cfd_nx_write_surface_inspection_job,
    fromcad2cfd_nx_write_thicken_face_job,
    fromcad2cfd_nx_write_sew_sheet_bodies_job,
    fromcad2cfd_nx_write_curve_surface_demo_job,
    fromcad2cfd_nx_write_transform_profile_pack_job,
    fromcad2cfd_nx_write_reverse_step1_stl_import_job,
    fromcad2cfd_nx_write_reverse_step2_cage_from_facet_body_job,
    fromcad2cfd_nx_write_reverse_step3_step4_xoz_plane_combine_job,
    fromcad2cfd_nx_prepare_journal_command,
    fromcad2cfd_nx_inspect_model,
    fromcad2cfd_nx_get_last_report,
]
