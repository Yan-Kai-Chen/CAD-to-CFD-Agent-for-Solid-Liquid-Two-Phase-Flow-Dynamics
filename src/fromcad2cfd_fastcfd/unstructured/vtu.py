"""VTU writer for public-safe unstructured mesh previews."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from .mesh import VTK_CELL_TYPES, UnstructuredMesh


def write_mesh_vtu(mesh: UnstructuredMesh, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    connectivity = []
    offsets = []
    vtk_types = []
    region_tags = []
    cell_measures = []
    offset = 0
    for cell in mesh.cells:
        connectivity.extend(str(node_index[tag]) for tag in cell.node_tags)
        offset += len(cell.node_tags)
        offsets.append(str(offset))
        vtk_types.append(str(VTK_CELL_TYPES[cell.kind]))
        region_tags.append(str(cell.primary_physical_tag or 0))
        cell_measures.append(f"{mesh.cell_signed_measure(cell):.17g}")
    points = []
    for tag in node_tags:
        node = mesh.nodes[tag]
        points.append(f"{node.x:.17g} {node.y:.17g} {node.z:.17g}")
    text = f"""<?xml version=\"1.0\"?>
<VTKFile type=\"UnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\">
  <UnstructuredGrid>
    <Piece NumberOfPoints=\"{len(node_tags)}\" NumberOfCells=\"{len(mesh.cells)}\">
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
          {' '.join(vtk_types)}
        </DataArray>
      </Cells>
      <CellData>
        <DataArray type=\"Int64\" Name=\"region_physical_tag\" format=\"ascii\">
          {' '.join(region_tags)}
        </DataArray>
        <DataArray type=\"Float64\" Name=\"signed_cell_measure\" format=\"ascii\">
          {' '.join(cell_measures)}
        </DataArray>
      </CellData>
      <FieldData>
        <DataArray type=\"String\" Name=\"source_mesh\" NumberOfTuples=\"1\" format=\"ascii\">
          {escape(mesh.source_name())}
        </DataArray>
      </FieldData>
    </Piece>
  </UnstructuredGrid>
</VTKFile>
"""
    output.write_text(text, encoding="utf-8")
    return output


def write_scalar_solution_vtu(
    mesh: UnstructuredMesh,
    path: str | Path,
    node_values: dict[int, float],
    *,
    exact_values: dict[int, float] | None = None,
    error_values: dict[int, float] | None = None,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    node_tags = sorted(mesh.nodes)
    node_index = {tag: index for index, tag in enumerate(node_tags)}
    connectivity = []
    offsets = []
    vtk_types = []
    offset = 0
    for cell in mesh.cells:
        connectivity.extend(str(node_index[tag]) for tag in cell.node_tags)
        offset += len(cell.node_tags)
        offsets.append(str(offset))
        vtk_types.append(str(VTK_CELL_TYPES[cell.kind]))
    points = []
    for tag in node_tags:
        node = mesh.nodes[tag]
        points.append(f"{node.x:.17g} {node.y:.17g} {node.z:.17g}")
    scalar_values = " ".join(f"{float(node_values[tag]):.17g}" for tag in node_tags)
    point_arrays = [
        f"""        <DataArray type=\"Float64\" Name=\"phi\" format=\"ascii\">
          {scalar_values}
        </DataArray>"""
    ]
    if exact_values is not None:
        exact_text = " ".join(f"{float(exact_values[tag]):.17g}" for tag in node_tags)
        point_arrays.append(
            f"""        <DataArray type=\"Float64\" Name=\"phi_exact\" format=\"ascii\">
          {exact_text}
        </DataArray>"""
        )
    if error_values is not None:
        error_text = " ".join(f"{float(error_values[tag]):.17g}" for tag in node_tags)
        point_arrays.append(
            f"""        <DataArray type=\"Float64\" Name=\"phi_error\" format=\"ascii\">
          {error_text}
        </DataArray>"""
        )
    text = f"""<?xml version=\"1.0\"?>
<VTKFile type=\"UnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\">
  <UnstructuredGrid>
    <Piece NumberOfPoints=\"{len(node_tags)}\" NumberOfCells=\"{len(mesh.cells)}\">
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
          {' '.join(vtk_types)}
        </DataArray>
      </Cells>
      <PointData Scalars=\"phi\">
{chr(10).join(point_arrays)}
      </PointData>
      <FieldData>
        <DataArray type=\"String\" Name=\"source_mesh\" NumberOfTuples=\"1\" format=\"ascii\">
          {escape(mesh.source_name())}
        </DataArray>
      </FieldData>
    </Piece>
  </UnstructuredGrid>
</VTKFile>
"""
    output.write_text(text, encoding="utf-8")
    return output
