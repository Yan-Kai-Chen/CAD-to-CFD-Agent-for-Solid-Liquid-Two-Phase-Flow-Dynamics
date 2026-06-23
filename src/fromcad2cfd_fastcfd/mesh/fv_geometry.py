"""Mesh Gateway v2 wrapper around finite-volume geometry construction."""

from __future__ import annotations

from fromcad2cfd_fastcfd.unstructured.geometry import FV_GEOMETRY_SCHEMA_VERSION, build_fv_geometry

__all__ = ["FV_GEOMETRY_SCHEMA_VERSION", "build_fv_geometry"]
