"""Safety policy helpers."""

from __future__ import annotations

from pathlib import Path


PRIVATE_CAD_EXTENSIONS = {
    ".sldprt",
    ".sldasm",
    ".slddrw",
    ".step",
    ".stp",
    ".x_t",
    ".x_b",
    ".iges",
    ".igs",
    ".stl",
    ".3mf",
    ".obj",
}


def is_private_geometry_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in PRIVATE_CAD_EXTENSIONS
