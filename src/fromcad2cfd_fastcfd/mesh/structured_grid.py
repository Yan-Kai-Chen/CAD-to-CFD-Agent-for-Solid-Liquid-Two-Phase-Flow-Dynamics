"""Structured-grid demo support for Mesh Gateway v2."""

from __future__ import annotations

from typing import Any


STRUCTURED_GRID_SCHEMA_VERSION = "fastfluent_structured_grid_v1"


def build_structured_grid_manifest(
    *,
    nx: int = 20,
    ny: int = 8,
    length_m: float = 1.0,
    height_m: float = 0.1,
) -> dict[str, Any]:
    """Build a public-safe structured-grid manifest."""

    if nx <= 0 or ny <= 0:
        raise ValueError("Structured grid nx and ny must be positive.")
    if length_m <= 0 or height_m <= 0:
        raise ValueError("Structured grid length_m and height_m must be positive.")
    dx = length_m / nx
    dy = height_m / ny
    return {
        "schema_version": STRUCTURED_GRID_SCHEMA_VERSION,
        "backend": "structured_grid",
        "mesh_source": "generated",
        "dimension": "2d",
        "node_count": (nx + 1) * (ny + 1),
        "cell_count": nx * ny,
        "nx": nx,
        "ny": ny,
        "length_m": length_m,
        "height_m": height_m,
        "dx_m": dx,
        "dy_m": dy,
        "boundary_zone_counts": {
            "inlet": ny,
            "outlet": ny,
            "top_wall": nx,
            "bottom_wall": nx,
        },
        "region_zone_counts": {"fluid": nx * ny},
    }


def build_structured_grid_quality(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build lightweight structured-grid quality metrics."""

    dx = float(manifest["dx_m"])
    dy = float(manifest["dy_m"])
    aspect_ratio = max(dx / dy, dy / dx)
    warnings = []
    if aspect_ratio > 20:
        warnings.append("Structured grid aspect ratio is high for a public screening demo.")
    return {
        "schema_version": "fastfluent_structured_grid_quality_v1",
        "status": "passed",
        "checks": {
            "positive_spacing": dx > 0 and dy > 0,
            "positive_cell_count": int(manifest["cell_count"]) > 0,
            "structured_connectivity": True,
        },
        "metrics": {
            "cell_count": manifest["cell_count"],
            "node_count": manifest["node_count"],
            "dx_m": dx,
            "dy_m": dy,
            "aspect_ratio": aspect_ratio,
        },
        "warnings": warnings,
        "blocking_errors": [],
        "limitations": [
            "This is a structured-grid gateway demo, not a full CFD mesh-quality audit.",
            "Skewness and non-orthogonality are exact for this orthogonal rectangular demo grid.",
        ],
    }


def build_structured_fv_geometry(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build a compact finite-volume geometry summary for a structured demo grid."""

    nx = int(manifest["nx"])
    ny = int(manifest["ny"])
    dx = float(manifest["dx_m"])
    dy = float(manifest["dy_m"])
    return {
        "schema_version": "fastfluent_structured_fv_geometry_v1",
        "cell_count": nx * ny,
        "face_count_estimate": (nx + 1) * ny + (ny + 1) * nx,
        "cell_measure": dx * dy,
        "boundary_patches": dict(manifest["boundary_zone_counts"]),
        "notes": ["This compact geometry summary is intended for Mesh Gateway v2 smoke tests."],
    }


def structured_grid_report(manifest: dict[str, Any], quality: dict[str, Any]) -> str:
    """Render a structured-grid report."""

    lines = [
        "# FastFluent Structured Mesh Gateway Demo",
        "",
        f"Status: `{quality.get('status')}`",
        f"Cells: `{manifest.get('cell_count')}`",
        f"Nodes: `{manifest.get('node_count')}`",
        f"Spacing: `{manifest.get('dx_m')}` m x `{manifest.get('dy_m')}` m",
        "",
        "## Boundary Zones",
        "",
    ]
    for name, count in sorted(manifest.get("boundary_zone_counts", {}).items()):
        lines.append(f"- `{name}`: `{count}`")
    lines.extend(["", "## Warnings", ""])
    warnings = quality.get("warnings", [])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def structured_grid_vtu(manifest: dict[str, Any]) -> str:
    """Return a simple VTU text for a rectangular structured grid as quads."""

    nx = int(manifest["nx"])
    ny = int(manifest["ny"])
    dx = float(manifest["dx_m"])
    dy = float(manifest["dy_m"])
    points = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            points.append(f"{i * dx:.17g} {j * dy:.17g} 0")
    connectivity = []
    offsets = []
    types = []
    offset = 0
    for j in range(ny):
        for i in range(nx):
            n0 = j * (nx + 1) + i
            n1 = n0 + 1
            n2 = n0 + (nx + 1) + 1
            n3 = n0 + (nx + 1)
            connectivity.extend([str(n0), str(n1), str(n2), str(n3)])
            offset += 4
            offsets.append(str(offset))
            types.append("9")
    return f"""<?xml version=\"1.0\"?>
<VTKFile type=\"UnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\">
  <UnstructuredGrid>
    <Piece NumberOfPoints=\"{len(points)}\" NumberOfCells=\"{nx * ny}\">
      <Points>
        <DataArray type=\"Float64\" NumberOfComponents=\"3\" format=\"ascii\">
          {' '.join(points)}
        </DataArray>
      </Points>
      <Cells>
        <DataArray type=\"Int64\" Name=\"connectivity\" format=\"ascii\">
          {' '.join(connectivity)}
        </DataArray>
        <DataArray type=\"Int64\" Name=\"offsets\" format=\"ascii\">
          {' '.join(offsets)}
        </DataArray>
        <DataArray type=\"UInt8\" Name=\"types\" format=\"ascii\">
          {' '.join(types)}
        </DataArray>
      </Cells>
    </Piece>
  </UnstructuredGrid>
</VTKFile>
"""
