"""Mesh Gateway v2 wrapper around the existing Gmsh reader."""

from __future__ import annotations

from fromcad2cfd_fastcfd.unstructured.gmsh import GmshReadError, read_gmsh_v4_ascii

__all__ = ["GmshReadError", "read_gmsh_v4_ascii"]
