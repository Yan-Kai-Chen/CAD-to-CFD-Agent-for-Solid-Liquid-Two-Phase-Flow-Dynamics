"""NX backend reverse-modeling job builders."""

from __future__ import annotations

from pathlib import Path

from .job_schema import NXJournalJob


def stl_import_convergent_step1_job(
    input_file: str | Path,
    output_dir: str | Path,
    *,
    model_name: str | None = None,
    cleanup: bool = True,
    minimum_angle_folded_facets_deg: float = 15.0,
    minimum_facet_number: int = 100,
    stl_file_units: str = "Millimeters",
    show_information_window: bool = False,
) -> NXJournalJob:
    """Create the user-taught reverse-modeling Step 1 STL import job."""

    source = Path(input_file)
    if source.suffix.lower() != ".stl":
        raise ValueError("Step 1 reverse-modeling import expects an .stl input file.")
    if minimum_angle_folded_facets_deg <= 0.0:
        raise ValueError("minimum_angle_folded_facets_deg must be positive.")
    if minimum_facet_number < 1:
        raise ValueError("minimum_facet_number must be positive.")
    if stl_file_units not in {"Millimeters", "Meters", "Inches"}:
        raise ValueError("stl_file_units must be one of: Millimeters, Meters, Inches.")

    return NXJournalJob(
        operation="reverse_step1_import_stl_convergent",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or f"{source.stem}_step1_convergent",
        parameters={
            "facet_body_output_type": "Convergent",
            "nx_facet_body_type": "Psm",
            "cleanup": bool(cleanup),
            "minimum_angle_folded_facets_deg": float(minimum_angle_folded_facets_deg),
            "minimum_facet_number": int(minimum_facet_number),
            "stl_file_units": stl_file_units,
            "show_information_window": bool(show_information_window),
        },
        export_formats=("NX_PRT", "PARASOLID_ATTEMPT"),
        metadata={
            "operation_family": "reverse_modeling",
            "reverse_modeling_step": "step1_import_stl_as_convergent_body",
            "source_type": "STL",
            "acceptance": "original STL preserved; imported copy saved as NX PRT; body classified as convergent; JSON and Markdown reports written",
            "user_taught_settings": {
                "facet_body_output_type": "Convergent",
                "cleanup": True,
                "minimum_angle_folded_facets_deg": 15.0,
                "minimum_facet_number": 100,
                "stl_file_units": "Millimeters",
            },
        },
    )


def cage_from_facet_body_step2_job(
    input_file: str | Path,
    output_dir: str | Path,
    *,
    model_name: str | None = None,
    average_size_mm: float = 10.0,
    body_selector: str = "all_convergent",
    show_deviation_plot: bool = False,
) -> NXJournalJob:
    """Create the user-taught reverse-modeling Step 2 cage-from-facet-body job."""

    source = Path(input_file)
    if source.suffix.lower() != ".prt":
        raise ValueError("Step 2 cage-from-facet-body expects a .prt input file from Step 1.")
    if average_size_mm <= 0.0:
        raise ValueError("average_size_mm must be positive.")
    if body_selector not in {"all_convergent", "all_bodies"}:
        raise ValueError("body_selector must be one of: all_convergent, all_bodies.")

    return NXJournalJob(
        operation="reverse_step2_cage_from_facet_body",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or f"{source.stem}_step2_cage",
        parameters={
            "average_size_mm": float(average_size_mm),
            "body_selector": body_selector,
            "show_deviation_plot": bool(show_deviation_plot),
            "nx_builder": "NXOpen.Features.Subdivision.CageFromFacetBodyBuilder",
            "requires_nx_version": "NX1926_or_newer",
            "requires_license": "nx_subdivision",
        },
        export_formats=("NX_PRT",),
        metadata={
            "operation_family": "reverse_modeling",
            "reverse_modeling_step": "step2_cage_from_facet_body",
            "source_type": "NX_PRT_WITH_CONVERGENT_BODIES",
            "acceptance": "original Step 1 PRT preserved; copied PRT saved; all selected convergent bodies used to create subdivision cage; JSON and Markdown reports written",
            "user_taught_settings": {
                "ui_command": "Insert > NX Creative Modeling > Cage from Facet Body",
                "facet_region_selection": "all convergent bodies",
                "average_size_mm": 10.0,
            },
        },
    )


def xoz_plane_combine_step3_step4_job(
    input_file: str | Path,
    output_dir: str | Path,
    *,
    model_name: str | None = None,
    square_size_mm: float = 1000.0,
    plane_offset_z_mm: float = 5.0,
    body_selector: str = "all_imported_sheet_bodies",
    run_combine: bool = True,
    export_parasolid: bool = True,
) -> NXJournalJob:
    """Create the user-taught reverse-modeling Step 3/4 XOY plane combine job."""

    source = Path(input_file)
    if source.suffix.lower() not in {".x_t", ".x_b"}:
        raise ValueError("Step 3/4 XOY plane combine expects a Parasolid .x_t or .x_b input.")
    if square_size_mm <= 0.0:
        raise ValueError("square_size_mm must be positive.")
    if body_selector not in {"all_imported_sheet_bodies", "all_imported_bodies"}:
        raise ValueError("body_selector must be one of: all_imported_sheet_bodies, all_imported_bodies.")

    return NXJournalJob(
        operation="reverse_step3_step4_xoz_plane_combine",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or f"{source.stem}_step3_step4_xoz_plane_combine",
        parameters={
            "square_size_mm": float(square_size_mm),
            "plane_offset_z_mm": float(plane_offset_z_mm),
            "body_selector": body_selector,
            "run_combine": bool(run_combine),
            "export_parasolid": bool(export_parasolid),
            "nx_builder": "NXOpen.Features.CombineSheetsBuilder",
            "requires_license": "solid_modeling",
        },
        export_formats=("NX_PRT", "PARASOLID_ATTEMPT"),
        metadata={
            "operation_family": "reverse_modeling",
            "reverse_modeling_step": "step3_step4_xoy_bounded_plane_and_combine",
            "source_type": "PARASOLID_FROM_REVERSE_MODELED_NX_RESULT",
            "acceptance": "original Parasolid preserved; copied input imported into new PRT; XOY bounded-plane sheet centered on origin is created, moved +Z, combined with selected imported bodies, and JSON/Markdown reports are written",
            "user_taught_settings": {
                "step3_plane": "XOY",
                "square_size_mm": 1000.0,
                "square_center": "origin",
                "plane_translate_axis": "Z",
                "plane_offset_z_mm": 5.0,
                "step4_ui_command": "Insert > Combine > Combine",
                "step4_region_selection": "recorded KeepOrRemove RegionTracker pattern",
                "legacy_command_name": "write-reverse-step3-step4-xoz-plane-combine-job",
            },
        },
    )
