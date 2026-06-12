"""CAD export format helpers."""

from __future__ import annotations


FORMAT_ALIASES = {
    "STEP": "STEP",
    "STP": "STEP",
    "PARASOLID": "PARASOLID",
    "X_T": "PARASOLID",
    "XT": "PARASOLID",
    "IGES": "IGES",
    "IGS": "IGES",
    "STL": "STL",
}

CFD_PREFERRED_FORMATS = ("STEP", "PARASOLID")


def normalize_export_format(format_name: str) -> str:
    normalized = format_name.strip().replace("-", "_").upper()
    try:
        return FORMAT_ALIASES[normalized]
    except KeyError as exc:
        allowed = ", ".join(sorted(FORMAT_ALIASES))
        raise ValueError(f"Unsupported export format: {format_name}. Allowed values: {allowed}") from exc


def is_cfd_preferred_format(format_name: str) -> bool:
    return normalize_export_format(format_name) in CFD_PREFERRED_FORMATS
