"""NX backend solid-modeling job builders."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .job_schema import NXJournalJob


def basic_solid_pack_demo_job(
    output_dir: str | Path,
    *,
    model_name: str = "nx_basic_solid_pack_demo",
    block_length_mm: float = 20.0,
    block_width_mm: float = 20.0,
    block_height_mm: float = 20.0,
    sphere_diameter_mm: float = 18.0,
    cone_base_diameter_mm: float = 18.0,
    cone_top_diameter_mm: float = 6.0,
    cone_height_mm: float = 24.0,
    boolean_block_length_mm: float = 24.0,
    boolean_block_width_mm: float = 20.0,
    boolean_block_height_mm: float = 20.0,
    boolean_overlap_mm: float = 12.0,
    translate_copy_y_mm: float = 35.0,
) -> NXJournalJob:
    """Create a synthetic job covering basic NX primitives, booleans, and copy-translate."""

    positive_values = {
        "block_length_mm": block_length_mm,
        "block_width_mm": block_width_mm,
        "block_height_mm": block_height_mm,
        "sphere_diameter_mm": sphere_diameter_mm,
        "cone_base_diameter_mm": cone_base_diameter_mm,
        "cone_top_diameter_mm": cone_top_diameter_mm,
        "cone_height_mm": cone_height_mm,
        "boolean_block_length_mm": boolean_block_length_mm,
        "boolean_block_width_mm": boolean_block_width_mm,
        "boolean_block_height_mm": boolean_block_height_mm,
        "boolean_overlap_mm": boolean_overlap_mm,
        "translate_copy_y_mm": translate_copy_y_mm,
    }
    for name, value in positive_values.items():
        if float(value) <= 0.0:
            raise ValueError(f"{name} must be positive.")
    if float(cone_top_diameter_mm) >= float(cone_base_diameter_mm):
        raise ValueError("cone_top_diameter_mm must be smaller than cone_base_diameter_mm.")
    if float(boolean_overlap_mm) >= float(boolean_block_length_mm):
        raise ValueError("boolean_overlap_mm must be smaller than boolean_block_length_mm.")

    return NXJournalJob(
        operation="create_basic_solid_pack_demo",
        output_dir=str(output_dir),
        model_name=model_name,
        parameters={name: float(value) for name, value in positive_values.items()},
        metadata={
            "operation_family": "solid_modeling",
            "capability_pack": "basic_solid_modeling",
            "covered_operations": ["block", "sphere", "cone", "boolean_unite", "boolean_intersect", "copy_translate"],
            "acceptance": "six solid bodies saved as PRT and exported as Parasolid",
        },
    )


def edge_wall_trim_pack_demo_job(
    output_dir: str | Path,
    *,
    model_name: str = "nx_edge_wall_trim_pack_demo",
    edge_radius_mm: float = 2.0,
    chamfer_offset_mm: float = 2.0,
    chamfer_angle_deg: float = 45.0,
    shell_thickness_mm: float = 0.5,
    shell_face_thickness_mm: float = 1.0,
    taper_base_diameter_mm: float = 18.0,
    taper_top_diameter_mm: float = 10.0,
    taper_height_mm: float = 24.0,
    plane_cut_x_mm: float = 110.0,
) -> NXJournalJob:
    """Create a synthetic job covering edge, wall, taper, trim, and Parasolid import coverage."""

    positive_values = {
        "edge_radius_mm": edge_radius_mm,
        "chamfer_offset_mm": chamfer_offset_mm,
        "chamfer_angle_deg": chamfer_angle_deg,
        "shell_thickness_mm": shell_thickness_mm,
        "shell_face_thickness_mm": shell_face_thickness_mm,
        "taper_base_diameter_mm": taper_base_diameter_mm,
        "taper_top_diameter_mm": taper_top_diameter_mm,
        "taper_height_mm": taper_height_mm,
    }
    for name, value in positive_values.items():
        if float(value) <= 0.0:
            raise ValueError(f"{name} must be positive.")
    if float(taper_top_diameter_mm) >= float(taper_base_diameter_mm):
        raise ValueError("taper_top_diameter_mm must be smaller than taper_base_diameter_mm.")

    parameters = {name: float(value) for name, value in positive_values.items()}
    parameters["plane_cut_x_mm"] = float(plane_cut_x_mm)
    return NXJournalJob(
        operation="create_edge_wall_trim_pack_demo",
        output_dir=str(output_dir),
        model_name=model_name,
        parameters=parameters,
        metadata={
            "operation_family": "solid_modeling",
            "capability_pack": "edge_wall_trim_import",
            "covered_operations": [
                "edge_blend_fillet",
                "chamfer",
                "shell_remove_face",
                "shell_face",
                "tapered_frustum",
                "plane_cut_by_cutter",
                "parasolid_export",
                "parasolid_import_to_prt",
            ],
            "draft_feature_status": "true DraftBody is not agent-facing yet; taper is represented by a controlled frustum",
            "acceptance": "solid bodies saved as PRT, exported as Parasolid, and re-imported into a controlled PRT",
        },
    )


def boolean_subtract_bodies_job(
    input_file: str | Path,
    output_dir: str | Path,
    *,
    model_name: str | None = None,
    target_body_index: int = 1,
    tool_body_indices: Sequence[int] = (2,),
    expected_body_count: int = 1,
    retain_target_body: bool = False,
    retain_tool_bodies: bool = False,
) -> NXJournalJob:
    """Create a controlled job for subtracting selected tool bodies from one target body."""

    source = Path(input_file)
    if target_body_index < 1:
        raise ValueError("target_body_index must be 1-based and positive.")
    tools = tuple(int(index) for index in tool_body_indices)
    if not tools:
        raise ValueError("At least one tool body index is required.")
    if any(index < 1 for index in tools):
        raise ValueError("tool_body_indices must be 1-based and positive.")
    if target_body_index in tools:
        raise ValueError("target body cannot also be a tool body.")
    if expected_body_count < 1:
        raise ValueError("expected_body_count must be positive.")

    return NXJournalJob(
        operation="boolean_subtract_bodies",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or f"{source.stem}_boolean_subtract",
        parameters={
            "target_body_index": target_body_index,
            "tool_body_indices": list(tools),
            "expected_body_count": expected_body_count,
            "retain_target_body": bool(retain_target_body),
            "retain_tool_bodies": bool(retain_tool_bodies),
        },
        metadata={
            "operation_family": "solid_modeling",
            "boolean_type": "subtract",
            "selector_basis": "1-based body index after copied-model inspection",
        },
    )


def plane_cut_body_job(
    input_file: str | Path,
    output_dir: str | Path,
    *,
    model_name: str | None = None,
    body_index: int = 1,
    plane_axis: str = "x",
    plane_offset_mm: float = 0.0,
    remove_side: str = "positive",
    cutter_extent_mm: float = 1000.0,
) -> NXJournalJob:
    """Create a copied-model job for cutting one solid body by an axis-aligned plane."""

    source = Path(input_file)
    axis = plane_axis.lower()
    side = remove_side.lower()
    if body_index < 1:
        raise ValueError("body_index must be 1-based and positive.")
    if axis not in {"x", "y", "z"}:
        raise ValueError("plane_axis must be x, y, or z.")
    if side not in {"positive", "negative"}:
        raise ValueError("remove_side must be positive or negative.")
    if float(cutter_extent_mm) <= 0.0:
        raise ValueError("cutter_extent_mm must be positive.")

    return NXJournalJob(
        operation="plane_cut_body",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or f"{source.stem}_plane_cut",
        parameters={
            "body_index": int(body_index),
            "plane_axis": axis,
            "plane_offset_mm": float(plane_offset_mm),
            "remove_side": side,
            "cutter_extent_mm": float(cutter_extent_mm),
        },
        metadata={
            "operation_family": "solid_modeling",
            "trim_type": "axis_aligned_plane_cut_by_subtract_cutter",
            "selector_basis": "1-based solid body index after copied-model inspection",
        },
    )
