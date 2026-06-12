"""NX backend curve and surface job builders."""

from __future__ import annotations

from pathlib import Path

from .job_schema import NXJournalJob


def curve_surface_demo_job(
    output_dir: str | Path,
    *,
    model_name: str = "nx_curve_surface_demo",
    rectangle_width_mm: float = 40.0,
    rectangle_height_mm: float = 30.0,
    circle_radius_mm: float = 8.0,
    ellipse_major_radius_mm: float = 12.0,
    ellipse_minor_radius_mm: float = 6.0,
) -> NXJournalJob:
    """Create a synthetic job for basic curves plus a bounded-plane sheet surface."""

    if rectangle_width_mm <= 0.0 or rectangle_height_mm <= 0.0:
        raise ValueError("rectangle_width_mm and rectangle_height_mm must be positive.")
    if circle_radius_mm <= 0.0:
        raise ValueError("circle_radius_mm must be positive.")
    if ellipse_major_radius_mm <= 0.0 or ellipse_minor_radius_mm <= 0.0:
        raise ValueError("ellipse radii must be positive.")
    if ellipse_minor_radius_mm > ellipse_major_radius_mm:
        raise ValueError("ellipse_minor_radius_mm must be less than or equal to ellipse_major_radius_mm.")

    return NXJournalJob(
        operation="create_curve_surface_demo",
        output_dir=str(output_dir),
        model_name=model_name,
        parameters={
            "rectangle_width_mm": float(rectangle_width_mm),
            "rectangle_height_mm": float(rectangle_height_mm),
            "circle_radius_mm": float(circle_radius_mm),
            "ellipse_major_radius_mm": float(ellipse_major_radius_mm),
            "ellipse_minor_radius_mm": float(ellipse_minor_radius_mm),
        },
        metadata={
            "operation_family": "curve_surface",
            "curve_operations": ["line", "arc_circle", "ellipse"],
            "surface_operation": "bounded_plane_from_closed_curves",
            "acceptance": "basic curves saved in PRT; one bounded-plane sheet body exported as Parasolid",
        },
    )


def transform_profile_pack_demo_job(
    output_dir: str | Path,
    *,
    model_name: str = "nx_transform_profile_pack_demo",
    rotate_angle_deg: float = 45.0,
    sweep_height_mm: float = 25.0,
    loft_height_mm: float = 24.0,
    revolve_angle_deg: float = 360.0,
) -> NXJournalJob:
    """Create a synthetic job for transforms, derived curves, and profile-based features."""

    if rotate_angle_deg == 0.0:
        raise ValueError("rotate_angle_deg must be non-zero.")
    if sweep_height_mm <= 0.0:
        raise ValueError("sweep_height_mm must be positive.")
    if loft_height_mm <= 0.0:
        raise ValueError("loft_height_mm must be positive.")
    if revolve_angle_deg <= 0.0 or revolve_angle_deg > 360.0:
        raise ValueError("revolve_angle_deg must be in the range (0, 360].")

    return NXJournalJob(
        operation="create_transform_profile_pack_demo",
        output_dir=str(output_dir),
        model_name=model_name,
        parameters={
            "rotate_angle_deg": float(rotate_angle_deg),
            "sweep_height_mm": float(sweep_height_mm),
            "loft_height_mm": float(loft_height_mm),
            "revolve_angle_deg": float(revolve_angle_deg),
        },
        metadata={
            "operation_family": "curve_surface",
            "capability_pack": "transform_profile_modeling",
            "covered_operations": [
                "rotate_copy",
                "mirror_body",
                "project_curve_to_face",
                "intersection_curve_body_plane",
                "revolve_profile",
                "sweep_profile_along_path",
                "loft_through_curves",
            ],
            "acceptance": "seven solid bodies, one sheet body, PRT save, Parasolid export, JSON and Markdown reports",
        },
    )
