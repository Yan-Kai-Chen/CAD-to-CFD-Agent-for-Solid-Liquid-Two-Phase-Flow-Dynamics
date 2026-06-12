"""Command-line interface for the Siemens NX backend scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from .curve_surface import curve_surface_demo_job, transform_profile_pack_demo_job
from .export import import_parasolid_job
from .geometry import boolean_subtract_demo_recipe, cylinder_recipe, geometry_job_from_recipe, plate_with_hole_recipe
from .inspect_model import inspection_job
from .paths import project_input_dir, project_output_dir, unique_path
from .preflight import run_preflight
from .reverse_modeling import cage_from_facet_body_step2_job, stl_import_convergent_step1_job, xoz_plane_combine_step3_step4_job
from .solid_modeling import basic_solid_pack_demo_job, boolean_subtract_bodies_job, edge_wall_trim_pack_demo_job, plane_cut_body_job
from .surface_repair import sew_sheet_bodies_job, thicken_face_job


def _copy_input_to_project(input_file: str, project: str) -> Path:
    source = Path(input_file)
    if not source.exists():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    target = unique_path(project_input_dir(project) / source.name)
    shutil.copy2(source, target)
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd nx")
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="Detect Siemens NX and journal runner availability.")
    preflight.add_argument("--no-report", action="store_true", help="Print only; do not write preflight report files.")

    job = sub.add_parser("write-job", help="Write a backend-neutral NX journal job JSON without running NX.")
    job.add_argument("--recipe", choices=["cylinder", "plate-with-hole", "boolean-subtract-demo"], default="cylinder")
    job.add_argument("--project", default="nx_test_project")
    job.add_argument("--model-name", default=None)
    job.add_argument("--radius-mm", type=float, default=10.0)
    job.add_argument("--height-mm", type=float, default=20.0)
    job.add_argument("--width-mm", type=float, default=60.0)
    job.add_argument("--thickness-mm", type=float, default=5.0)
    job.add_argument("--hole-radius-mm", type=float, default=5.0)
    job.add_argument("--outer-radius-mm", type=float, default=50.0)
    job.add_argument("--outer-height-mm", type=float, default=100.0)
    job.add_argument("--tool-radius-mm", type=float, default=10.0)
    job.add_argument("--tool-height-mm", type=float, default=120.0)

    inspect = sub.add_parser("write-inspect-job", help="Write an NX model inspection job JSON without running NX.")
    inspect.add_argument("--input-file", required=True)
    inspect.add_argument("--project", default="nx_inspection_project")
    inspect.add_argument("--model-name", default=None)

    boolean = sub.add_parser("write-boolean-subtract-job", help="Write a copied-model boolean subtract job JSON without running NX.")
    boolean.add_argument("--input-file", required=True)
    boolean.add_argument("--project", default="nxb")
    boolean.add_argument("--model-name", default=None)
    boolean.add_argument("--target-body-index", type=int, default=1)
    boolean.add_argument("--tool-body-indices", default="2", help="Comma-separated 1-based tool body indices.")
    boolean.add_argument("--expected-body-count", type=int, default=1)
    boolean.add_argument("--retain-target-body", action="store_true")
    boolean.add_argument("--retain-tool-bodies", action="store_true")

    basic_pack = sub.add_parser("write-basic-solid-pack-job", help="Write a synthetic NX basic solid-modeling capability-pack job JSON without running NX.")
    basic_pack.add_argument("--project", default="nx_basic_solid_pack_demo")
    basic_pack.add_argument("--model-name", default="nx_basic_solid_pack_demo")
    basic_pack.add_argument("--block-length-mm", type=float, default=20.0)
    basic_pack.add_argument("--block-width-mm", type=float, default=20.0)
    basic_pack.add_argument("--block-height-mm", type=float, default=20.0)
    basic_pack.add_argument("--sphere-diameter-mm", type=float, default=18.0)
    basic_pack.add_argument("--cone-base-diameter-mm", type=float, default=18.0)
    basic_pack.add_argument("--cone-top-diameter-mm", type=float, default=6.0)
    basic_pack.add_argument("--cone-height-mm", type=float, default=24.0)
    basic_pack.add_argument("--boolean-block-length-mm", type=float, default=24.0)
    basic_pack.add_argument("--boolean-block-width-mm", type=float, default=20.0)
    basic_pack.add_argument("--boolean-block-height-mm", type=float, default=20.0)
    basic_pack.add_argument("--boolean-overlap-mm", type=float, default=12.0)
    basic_pack.add_argument("--translate-copy-y-mm", type=float, default=35.0)

    edge_wall_trim = sub.add_parser(
        "write-edge-wall-trim-pack-job",
        help="Write a synthetic NX edge, wall, taper, plane-cut, and Parasolid import pack job JSON without running NX.",
    )
    edge_wall_trim.add_argument("--project", default="nx_edge_wall_trim_pack_demo")
    edge_wall_trim.add_argument("--model-name", default="nx_edge_wall_trim_pack_demo")
    edge_wall_trim.add_argument("--edge-radius-mm", type=float, default=2.0)
    edge_wall_trim.add_argument("--chamfer-offset-mm", type=float, default=2.0)
    edge_wall_trim.add_argument("--chamfer-angle-deg", type=float, default=45.0)
    edge_wall_trim.add_argument("--shell-thickness-mm", type=float, default=0.5)
    edge_wall_trim.add_argument("--shell-face-thickness-mm", type=float, default=1.0)
    edge_wall_trim.add_argument("--taper-base-diameter-mm", type=float, default=18.0)
    edge_wall_trim.add_argument("--taper-top-diameter-mm", type=float, default=10.0)
    edge_wall_trim.add_argument("--taper-height-mm", type=float, default=24.0)
    edge_wall_trim.add_argument("--plane-cut-x-mm", type=float, default=110.0)

    plane_cut = sub.add_parser("write-plane-cut-body-job", help="Write a copied-model axis-aligned plane-cut job JSON without running NX.")
    plane_cut.add_argument("--input-file", required=True)
    plane_cut.add_argument("--project", default="nx_plane_cut")
    plane_cut.add_argument("--model-name", default=None)
    plane_cut.add_argument("--body-index", type=int, default=1)
    plane_cut.add_argument("--plane-axis", choices=["x", "y", "z"], default="x")
    plane_cut.add_argument("--plane-offset-mm", type=float, default=0.0)
    plane_cut.add_argument("--remove-side", choices=["positive", "negative"], default="positive")
    plane_cut.add_argument("--cutter-extent-mm", type=float, default=1000.0)

    import_parasolid = sub.add_parser("write-import-parasolid-job", help="Write a controlled Parasolid import-to-PRT job JSON without running NX.")
    import_parasolid.add_argument("--input-file", required=True)
    import_parasolid.add_argument("--project", default="nx_import_parasolid")
    import_parasolid.add_argument("--model-name", default=None)

    thicken = sub.add_parser("write-thicken-face-job", help="Write a copied-model face/sheet thicken job JSON without running NX.")
    thicken.add_argument("--input-file", required=True)
    thicken.add_argument("--project", default="nxt")
    thicken.add_argument("--model-name", default=None)
    thicken.add_argument("--body-index", type=int, default=1)
    thicken.add_argument("--face-index", type=int, default=1)
    thicken.add_argument("--thickness-mm", type=float, default=2.0)
    thicken.add_argument("--no-extract-face-first", action="store_true")
    thicken.add_argument("--expected-min-solid-bodies", type=int, default=1)

    sew = sub.add_parser("write-sew-sheet-bodies-job", help="Write a copied-model sheet-body sew job JSON without running NX.")
    sew.add_argument("--input-file", required=True)
    sew.add_argument("--project", default="nxs")
    sew.add_argument("--model-name", default=None)
    sew.add_argument("--target-sheet-body-index", type=int, default=1)
    sew.add_argument("--tool-sheet-body-indices", default="2", help="Comma-separated 1-based tool sheet body indices.")
    sew.add_argument("--tolerance-mm", type=float, default=0.01)
    sew.add_argument("--expected-min-solid-bodies", type=int, default=1)
    sew.add_argument("--expected-max-sheet-bodies", type=int, default=None)

    curve_surface = sub.add_parser("write-curve-surface-demo-job", help="Write a synthetic basic-curve and bounded-plane surface job JSON without running NX.")
    curve_surface.add_argument("--project", default="nx_curve_surface_demo")
    curve_surface.add_argument("--model-name", default="nx_curve_surface_demo")
    curve_surface.add_argument("--rectangle-width-mm", type=float, default=40.0)
    curve_surface.add_argument("--rectangle-height-mm", type=float, default=30.0)
    curve_surface.add_argument("--circle-radius-mm", type=float, default=8.0)
    curve_surface.add_argument("--ellipse-major-radius-mm", type=float, default=12.0)
    curve_surface.add_argument("--ellipse-minor-radius-mm", type=float, default=6.0)

    transform_profile = sub.add_parser(
        "write-transform-profile-pack-job",
        help="Write a synthetic NX transform, derived-curve, revolve, sweep, and loft capability-pack job JSON without running NX.",
    )
    transform_profile.add_argument("--project", default="nx_transform_profile_pack_demo")
    transform_profile.add_argument("--model-name", default="nx_transform_profile_pack_demo")
    transform_profile.add_argument("--rotate-angle-deg", type=float, default=45.0)
    transform_profile.add_argument("--sweep-height-mm", type=float, default=25.0)
    transform_profile.add_argument("--loft-height-mm", type=float, default=24.0)
    transform_profile.add_argument("--revolve-angle-deg", type=float, default=360.0)

    reverse_step1 = sub.add_parser(
        "write-reverse-step1-stl-import-job",
        help="Write a copied-input NX reverse-modeling Step 1 job for STL import as a cleaned convergent body.",
    )
    reverse_step1.add_argument("--input-file", required=True)
    reverse_step1.add_argument("--project", default="nx_reverse_step1_stl_import")
    reverse_step1.add_argument("--model-name", default=None)
    reverse_step1.add_argument("--minimum-angle-folded-facets-deg", type=float, default=15.0)
    reverse_step1.add_argument("--minimum-facet-number", type=int, default=100)
    reverse_step1.add_argument("--stl-file-units", choices=["Millimeters", "Meters", "Inches"], default="Millimeters")
    reverse_step1.add_argument("--no-cleanup", action="store_true")
    reverse_step1.add_argument("--show-information-window", action="store_true")

    reverse_step2 = sub.add_parser(
        "write-reverse-step2-cage-from-facet-body-job",
        help="Write a copied-input NX reverse-modeling Step 2 job for Cage from Facet Body.",
    )
    reverse_step2.add_argument("--input-file", required=True)
    reverse_step2.add_argument("--project", default="nx_reverse_step2_cage_from_facet_body")
    reverse_step2.add_argument("--model-name", default=None)
    reverse_step2.add_argument("--average-size-mm", type=float, default=10.0)
    reverse_step2.add_argument("--body-selector", choices=["all_convergent", "all_bodies"], default="all_convergent")
    reverse_step2.add_argument("--show-deviation-plot", action="store_true")

    reverse_step3_step4 = sub.add_parser(
        "write-reverse-step3-step4-xoz-plane-combine-job",
        help="Write a copied-input NX reverse-modeling Step 3/4 job for XOY bounded-plane creation and Combine. The xoz command name is legacy-compatible.",
    )
    reverse_step3_step4.add_argument("--input-file", required=True)
    reverse_step3_step4.add_argument("--project", default="nx_reverse_step3_step4_xoz_plane_combine")
    reverse_step3_step4.add_argument("--model-name", default=None)
    reverse_step3_step4.add_argument("--square-size-mm", type=float, default=1000.0)
    reverse_step3_step4.add_argument("--plane-offset-z-mm", type=float, default=5.0)
    reverse_step3_step4.add_argument(
        "--body-selector",
        choices=["all_imported_sheet_bodies", "all_imported_bodies"],
        default="all_imported_sheet_bodies",
    )
    reverse_step3_step4.add_argument("--no-combine", action="store_true")
    reverse_step3_step4.add_argument("--no-parasolid-export", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preflight":
        result = run_preflight(write_reports=not args.no_report)
        print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
        return 0 if result.status in {"success", "partial"} else 2
    if args.command == "write-job":
        if args.recipe == "cylinder":
            recipe = cylinder_recipe(
                radius_mm=args.radius_mm,
                height_mm=args.height_mm,
                model_name=args.model_name or "nx_test_cylinder",
            )
        elif args.recipe == "plate-with-hole":
            recipe = plate_with_hole_recipe(
                width_mm=args.width_mm,
                height_mm=args.height_mm,
                thickness_mm=args.thickness_mm,
                hole_radius_mm=args.hole_radius_mm,
                model_name=args.model_name or "nx_plate_with_hole",
            )
        else:
            recipe = boolean_subtract_demo_recipe(
                outer_radius_mm=args.outer_radius_mm,
                outer_height_mm=args.outer_height_mm,
                tool_radius_mm=args.tool_radius_mm,
                tool_height_mm=args.tool_height_mm,
                model_name=args.model_name or "nx_boolean_subtract_demo",
            )
        output_dir = project_output_dir(args.project)
        job = geometry_job_from_recipe(recipe, output_dir=output_dir)
        job_path = unique_path(project_input_dir(args.project) / f"{recipe.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-inspect-job":
        output_dir = project_output_dir(args.project)
        job = inspection_job(args.input_file, output_dir=output_dir, model_name=args.model_name)
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-boolean-subtract-job":
        tool_indices = [int(item.strip()) for item in str(args.tool_body_indices).split(",") if item.strip()]
        output_dir = project_output_dir(args.project)
        job = boolean_subtract_bodies_job(
            args.input_file,
            output_dir=output_dir,
            model_name=args.model_name,
            target_body_index=args.target_body_index,
            tool_body_indices=tool_indices,
            expected_body_count=args.expected_body_count,
            retain_target_body=args.retain_target_body,
            retain_tool_bodies=args.retain_tool_bodies,
        )
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-basic-solid-pack-job":
        output_dir = project_output_dir(args.project)
        job = basic_solid_pack_demo_job(
            output_dir=output_dir,
            model_name=args.model_name,
            block_length_mm=args.block_length_mm,
            block_width_mm=args.block_width_mm,
            block_height_mm=args.block_height_mm,
            sphere_diameter_mm=args.sphere_diameter_mm,
            cone_base_diameter_mm=args.cone_base_diameter_mm,
            cone_top_diameter_mm=args.cone_top_diameter_mm,
            cone_height_mm=args.cone_height_mm,
            boolean_block_length_mm=args.boolean_block_length_mm,
            boolean_block_width_mm=args.boolean_block_width_mm,
            boolean_block_height_mm=args.boolean_block_height_mm,
            boolean_overlap_mm=args.boolean_overlap_mm,
            translate_copy_y_mm=args.translate_copy_y_mm,
        )
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-edge-wall-trim-pack-job":
        output_dir = project_output_dir(args.project)
        job = edge_wall_trim_pack_demo_job(
            output_dir=output_dir,
            model_name=args.model_name,
            edge_radius_mm=args.edge_radius_mm,
            chamfer_offset_mm=args.chamfer_offset_mm,
            chamfer_angle_deg=args.chamfer_angle_deg,
            shell_thickness_mm=args.shell_thickness_mm,
            shell_face_thickness_mm=args.shell_face_thickness_mm,
            taper_base_diameter_mm=args.taper_base_diameter_mm,
            taper_top_diameter_mm=args.taper_top_diameter_mm,
            taper_height_mm=args.taper_height_mm,
            plane_cut_x_mm=args.plane_cut_x_mm,
        )
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-plane-cut-body-job":
        output_dir = project_output_dir(args.project)
        job = plane_cut_body_job(
            args.input_file,
            output_dir=output_dir,
            model_name=args.model_name,
            body_index=args.body_index,
            plane_axis=args.plane_axis,
            plane_offset_mm=args.plane_offset_mm,
            remove_side=args.remove_side,
            cutter_extent_mm=args.cutter_extent_mm,
        )
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-import-parasolid-job":
        output_dir = project_output_dir(args.project)
        job = import_parasolid_job(args.input_file, output_dir=output_dir, model_name=args.model_name)
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-thicken-face-job":
        output_dir = project_output_dir(args.project)
        job = thicken_face_job(
            args.input_file,
            output_dir=output_dir,
            model_name=args.model_name,
            body_index=args.body_index,
            face_index=args.face_index,
            thickness_mm=args.thickness_mm,
            extract_face_first=not args.no_extract_face_first,
            expected_min_solid_bodies=args.expected_min_solid_bodies,
        )
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-sew-sheet-bodies-job":
        tool_indices = [int(item.strip()) for item in str(args.tool_sheet_body_indices).split(",") if item.strip()]
        output_dir = project_output_dir(args.project)
        job = sew_sheet_bodies_job(
            args.input_file,
            output_dir=output_dir,
            model_name=args.model_name,
            target_sheet_body_index=args.target_sheet_body_index,
            tool_sheet_body_indices=tool_indices,
            tolerance_mm=args.tolerance_mm,
            expected_min_solid_bodies=args.expected_min_solid_bodies,
            expected_max_sheet_bodies=args.expected_max_sheet_bodies,
        )
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-curve-surface-demo-job":
        output_dir = project_output_dir(args.project)
        job = curve_surface_demo_job(
            output_dir=output_dir,
            model_name=args.model_name,
            rectangle_width_mm=args.rectangle_width_mm,
            rectangle_height_mm=args.rectangle_height_mm,
            circle_radius_mm=args.circle_radius_mm,
            ellipse_major_radius_mm=args.ellipse_major_radius_mm,
            ellipse_minor_radius_mm=args.ellipse_minor_radius_mm,
        )
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-transform-profile-pack-job":
        output_dir = project_output_dir(args.project)
        job = transform_profile_pack_demo_job(
            output_dir=output_dir,
            model_name=args.model_name,
            rotate_angle_deg=args.rotate_angle_deg,
            sweep_height_mm=args.sweep_height_mm,
            loft_height_mm=args.loft_height_mm,
            revolve_angle_deg=args.revolve_angle_deg,
        )
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-reverse-step1-stl-import-job":
        copied_input = _copy_input_to_project(args.input_file, args.project)
        output_dir = project_output_dir(args.project)
        job = stl_import_convergent_step1_job(
            copied_input,
            output_dir=output_dir,
            model_name=args.model_name,
            cleanup=not args.no_cleanup,
            minimum_angle_folded_facets_deg=args.minimum_angle_folded_facets_deg,
            minimum_facet_number=args.minimum_facet_number,
            stl_file_units=args.stl_file_units,
            show_information_window=args.show_information_window,
        )
        job.metadata["original_source_file"] = str(Path(args.input_file))
        job.metadata["copied_input_file"] = str(copied_input)
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-reverse-step2-cage-from-facet-body-job":
        copied_input = _copy_input_to_project(args.input_file, args.project)
        output_dir = project_output_dir(args.project)
        job = cage_from_facet_body_step2_job(
            copied_input,
            output_dir=output_dir,
            model_name=args.model_name,
            average_size_mm=args.average_size_mm,
            body_selector=args.body_selector,
            show_deviation_plot=args.show_deviation_plot,
        )
        job.metadata["original_source_file"] = str(Path(args.input_file))
        job.metadata["copied_input_file"] = str(copied_input)
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-reverse-step3-step4-xoz-plane-combine-job":
        copied_input = _copy_input_to_project(args.input_file, args.project)
        output_dir = project_output_dir(args.project)
        job = xoz_plane_combine_step3_step4_job(
            copied_input,
            output_dir=output_dir,
            model_name=args.model_name,
            square_size_mm=args.square_size_mm,
            plane_offset_z_mm=args.plane_offset_z_mm,
            body_selector=args.body_selector,
            run_combine=not args.no_combine,
            export_parasolid=not args.no_parasolid_export,
        )
        job.metadata["original_source_file"] = str(Path(args.input_file))
        job.metadata["copied_input_file"] = str(copied_input)
        job_path = unique_path(project_input_dir(args.project) / f"{job.model_name}_job.json")
        job.write(job_path)
        print(json.dumps({"status": "success", "job_path": str(job_path), "job": job.to_dict()}, ensure_ascii=True, indent=2))
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
