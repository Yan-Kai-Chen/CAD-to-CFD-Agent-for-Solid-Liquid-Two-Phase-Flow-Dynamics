"""Mesh preprocessing and coarse solidification helpers."""

from .freecad_solidify import (
    FreeCADPreflight,
    freecad_preflight,
    run_freecad_solidify_job,
    solidify_freecad_job,
    write_solidify_freecad_job,
)

__all__ = [
    "FreeCADPreflight",
    "freecad_preflight",
    "run_freecad_solidify_job",
    "solidify_freecad_job",
    "write_solidify_freecad_job",
]
