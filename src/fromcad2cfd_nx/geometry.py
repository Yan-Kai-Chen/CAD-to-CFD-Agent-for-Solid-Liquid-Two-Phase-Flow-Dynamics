"""NX backend geometry job builders."""

from __future__ import annotations

from pathlib import Path

from fromcad2cfd_cad import GeometryRecipe

from .job_schema import NXJournalJob


def cylinder_recipe(radius_mm: float = 10.0, height_mm: float = 20.0, *, model_name: str = "nx_test_cylinder") -> GeometryRecipe:
    return GeometryRecipe(
        recipe_name="cylinder",
        model_name=model_name,
        parameters_mm={"radius_mm": radius_mm, "height_mm": height_mm},
    )


def plate_with_hole_recipe(
    *,
    width_mm: float = 60.0,
    height_mm: float = 40.0,
    thickness_mm: float = 5.0,
    hole_radius_mm: float = 5.0,
    model_name: str = "nx_plate_with_hole",
) -> GeometryRecipe:
    return GeometryRecipe(
        recipe_name="plate_with_hole",
        model_name=model_name,
        parameters_mm={
            "width_mm": width_mm,
            "height_mm": height_mm,
            "thickness_mm": thickness_mm,
            "hole_radius_mm": hole_radius_mm,
        },
    )


def boolean_subtract_demo_recipe(
    *,
    outer_radius_mm: float = 50.0,
    outer_height_mm: float = 100.0,
    tool_radius_mm: float = 10.0,
    tool_height_mm: float = 120.0,
    model_name: str = "nx_boolean_subtract_demo",
) -> GeometryRecipe:
    """Build a controlled outer-cylinder minus inner-cylinder smoke recipe."""

    return GeometryRecipe(
        recipe_name="boolean_subtract_demo",
        model_name=model_name,
        parameters_mm={
            "outer_radius_mm": outer_radius_mm,
            "outer_height_mm": outer_height_mm,
            "tool_radius_mm": tool_radius_mm,
            "tool_height_mm": tool_height_mm,
        },
        metadata={
            "operation_family": "solid_modeling",
            "boolean_type": "subtract",
            "acceptance": "one hollow solid body exported as PRT and Parasolid",
        },
    )


def geometry_job_from_recipe(recipe: GeometryRecipe, output_dir: str | Path) -> NXJournalJob:
    return NXJournalJob(
        operation=f"create_{recipe.recipe_name}",
        output_dir=str(output_dir),
        model_name=recipe.model_name,
        parameters=recipe.parameters_mm,
        metadata=recipe.metadata,
    )
