"""NX backend surface-repair job builders."""

from __future__ import annotations

from pathlib import Path

from .job_schema import NXJournalJob


def thicken_face_job(
    input_file: str | Path,
    output_dir: str | Path,
    *,
    model_name: str | None = None,
    body_index: int = 1,
    face_index: int = 1,
    thickness_mm: float = 2.0,
    extract_face_first: bool = True,
    expected_min_solid_bodies: int = 1,
) -> NXJournalJob:
    """Create a copied-model job for thickening one selected face or sheet face."""

    source = Path(input_file)
    if body_index < 1:
        raise ValueError("body_index must be 1-based and positive.")
    if face_index < 1:
        raise ValueError("face_index must be 1-based and positive.")
    if thickness_mm <= 0.0:
        raise ValueError("thickness_mm must be positive.")
    if expected_min_solid_bodies < 1:
        raise ValueError("expected_min_solid_bodies must be positive.")

    return NXJournalJob(
        operation="thicken_face",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or f"{source.stem}_thicken_face",
        parameters={
            "body_index": body_index,
            "face_index": face_index,
            "thickness_mm": float(thickness_mm),
            "extract_face_first": bool(extract_face_first),
            "expected_min_solid_bodies": int(expected_min_solid_bodies),
        },
        metadata={
            "operation_family": "surface_repair",
            "surface_operation": "thicken",
            "selector_basis": "1-based body and face indices after copied-model inspection",
        },
    )


def sew_sheet_bodies_job(
    input_file: str | Path,
    output_dir: str | Path,
    *,
    model_name: str | None = None,
    target_sheet_body_index: int = 1,
    tool_sheet_body_indices: tuple[int, ...] | list[int] = (2,),
    tolerance_mm: float = 0.01,
    expected_min_solid_bodies: int = 1,
    expected_max_sheet_bodies: int | None = None,
) -> NXJournalJob:
    """Create a copied-model job for sewing selected sheet bodies."""

    source = Path(input_file)
    if target_sheet_body_index < 1:
        raise ValueError("target_sheet_body_index must be 1-based and positive.")
    if not tool_sheet_body_indices:
        raise ValueError("At least one tool sheet body index is required.")
    normalized_tools = tuple(int(index) for index in tool_sheet_body_indices)
    if any(index < 1 for index in normalized_tools):
        raise ValueError("tool_sheet_body_indices must contain positive 1-based indices.")
    if target_sheet_body_index in normalized_tools:
        raise ValueError("target_sheet_body_index must not also be listed as a tool sheet body.")
    if tolerance_mm <= 0.0:
        raise ValueError("tolerance_mm must be positive.")
    if expected_min_solid_bodies < 1:
        raise ValueError("expected_min_solid_bodies must be positive.")
    if expected_max_sheet_bodies is not None and expected_max_sheet_bodies < 0:
        raise ValueError("expected_max_sheet_bodies must be non-negative when provided.")

    parameters = {
        "target_sheet_body_index": int(target_sheet_body_index),
        "tool_sheet_body_indices": list(normalized_tools),
        "tolerance_mm": float(tolerance_mm),
        "expected_min_solid_bodies": int(expected_min_solid_bodies),
    }
    if expected_max_sheet_bodies is not None:
        parameters["expected_max_sheet_bodies"] = int(expected_max_sheet_bodies)

    return NXJournalJob(
        operation="sew_sheet_bodies",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or f"{source.stem}_sew_sheet_bodies",
        parameters=parameters,
        metadata={
            "operation_family": "surface_repair",
            "surface_operation": "sew",
            "selector_basis": "1-based sheet body indices after copied-model inspection",
        },
    )
