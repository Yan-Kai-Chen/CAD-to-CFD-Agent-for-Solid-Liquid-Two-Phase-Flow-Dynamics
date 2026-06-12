"""NX model inspection placeholders."""

from __future__ import annotations

from pathlib import Path

from fromcad2cfd_cad import AgentResult

from .job_schema import NXJournalJob


def inspect_model_placeholder(input_file: str | Path) -> AgentResult:
    return AgentResult(
        status="skipped",
        backend="nx",
        operation="inspect_model",
        message="NX model inspection requires the NXOpen journal runner and is not executed by the scaffold.",
        outputs={"input_file": str(input_file)},
    )


def inspection_job(input_file: str | Path, output_dir: str | Path, *, model_name: str | None = None) -> NXJournalJob:
    """Create a controlled NX model inspection job for a copied input model."""

    source = Path(input_file)
    stem = model_name or f"{source.stem}_inspection"
    return NXJournalJob(
        operation="inspect_model",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=stem,
        parameters={},
        metadata={
            "operation_family": "surface_repair",
            "intent": "classify bodies before repair, sewing, thickening, or reverse modeling",
        },
    )
