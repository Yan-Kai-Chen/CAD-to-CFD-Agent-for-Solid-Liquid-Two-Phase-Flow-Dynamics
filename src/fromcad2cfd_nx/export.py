"""NX export job helpers."""

from __future__ import annotations

from pathlib import Path

from fromcad2cfd_cad.formats import normalize_export_format

from .job_schema import NXJournalJob


def export_job(input_file: str | Path, output_dir: str | Path, fmt: str = "STEP", *, model_name: str | None = None) -> NXJournalJob:
    normalized = normalize_export_format(fmt)
    source = Path(input_file)
    return NXJournalJob(
        operation="export_geometry",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or source.stem,
        export_formats=(normalized,),
        parameters={"format": normalized},
    )


def import_parasolid_job(input_file: str | Path, output_dir: str | Path, *, model_name: str | None = None) -> NXJournalJob:
    """Create a controlled job for importing a Parasolid file into a new NX PRT."""

    source = Path(input_file)
    suffix = source.suffix.lower()
    if suffix not in {".x_t", ".x_b"}:
        raise ValueError("import_parasolid_job expects a Parasolid .x_t or .x_b input file.")
    return NXJournalJob(
        operation="import_parasolid",
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or f"{source.stem}_imported",
        parameters={},
        metadata={
            "operation_family": "format_bridge",
            "source_format": "PARASOLID",
            "target_format": "NX_PRT",
            "acceptance": "new PRT contains at least one imported body and is re-exported as Parasolid",
        },
    )
