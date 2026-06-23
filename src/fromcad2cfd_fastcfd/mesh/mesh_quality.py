"""Mesh Gateway v2 wrapper around existing mesh-quality diagnostics."""

from __future__ import annotations

from fromcad2cfd_fastcfd.unstructured.quality import (
    MESH_MANIFEST_SCHEMA_VERSION,
    MESH_QUALITY_SCHEMA_VERSION,
    build_mesh_manifest,
    evaluate_mesh_quality,
)

__all__ = [
    "MESH_MANIFEST_SCHEMA_VERSION",
    "MESH_QUALITY_SCHEMA_VERSION",
    "build_mesh_manifest",
    "evaluate_mesh_quality",
]
