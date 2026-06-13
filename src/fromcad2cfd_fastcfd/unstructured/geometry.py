"""Finite-volume geometry operators for the unstructured FastFluent gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import acos, degrees
from typing import Any

from .mesh import FaceRecord, MeshElement, UnstructuredMesh, cross, dot, norm, vector_sub


FV_GEOMETRY_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_fv_geometry_v1"


@dataclass(frozen=True)
class FVCellGeometry:
    cell_index: int
    element_tag: int
    kind: str
    node_tags: tuple[int, ...]
    center: tuple[float, float, float]
    signed_measure: float
    measure: float
    physical_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_index": self.cell_index,
            "element_tag": self.element_tag,
            "kind": self.kind,
            "node_tags": list(self.node_tags),
            "center": list(self.center),
            "signed_measure": self.signed_measure,
            "measure": self.measure,
            "physical_name": self.physical_name,
        }


@dataclass(frozen=True)
class FVFaceGeometry:
    face_index: int
    node_tags: tuple[int, ...]
    owner: int
    neighbor: int | None
    center: tuple[float, float, float]
    area_vector: tuple[float, float, float]
    area: float
    patch_name: str | None = None
    non_orthogonality_deg: float | None = None
    boundary_element_tags: tuple[int, ...] = ()

    @property
    def is_boundary(self) -> bool:
        return self.neighbor is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "face_index": self.face_index,
            "node_tags": list(self.node_tags),
            "owner": self.owner,
            "neighbor": self.neighbor,
            "center": list(self.center),
            "area_vector": list(self.area_vector),
            "area": self.area,
            "patch_name": self.patch_name,
            "non_orthogonality_deg": self.non_orthogonality_deg,
            "boundary_element_tags": list(self.boundary_element_tags),
        }


@dataclass(frozen=True)
class FVGeometry:
    cells: list[FVCellGeometry]
    faces: list[FVFaceGeometry]
    boundary_patches: dict[str, list[int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        measures = [cell.measure for cell in self.cells]
        boundary_face_count = sum(1 for face in self.faces if face.is_boundary)
        internal_face_count = len(self.faces) - boundary_face_count
        return {
            "schema_version": FV_GEOMETRY_SCHEMA_VERSION,
            "backend": "unstructured_fvm",
            "solver_family": "finite_volume",
            "cell_count": len(self.cells),
            "face_count": len(self.faces),
            "boundary_face_count": boundary_face_count,
            "internal_face_count": internal_face_count,
            "min_cell_measure": min(measures) if measures else None,
            "max_cell_measure": max(measures) if measures else None,
            "boundary_patches": {name: list(indices) for name, indices in sorted(self.boundary_patches.items())},
            "cells": [cell.to_dict() for cell in self.cells],
            "faces": [face.to_dict() for face in self.faces],
            "limitations": [
                "This artifact contains finite-volume geometry operators only.",
                "No scalar, momentum, VOF, or rheology solver is executed in this gate.",
            ],
        }


def build_fv_geometry(mesh: UnstructuredMesh) -> FVGeometry:
    """Build owner-neighbour finite-volume geometry from an inspected mesh."""

    cells = [_build_cell_geometry(mesh, index, cell) for index, cell in enumerate(mesh.cells)]
    for cell in cells:
        if cell.measure <= 0:
            raise ValueError(f"Cannot build FV geometry because cell {cell.cell_index} has non-positive measure.")
    face_records = mesh.faces()
    faces: list[FVFaceGeometry] = []
    boundary_patches: dict[str, list[int]] = {}
    for face_index, record in enumerate(sorted(face_records.values(), key=lambda item: item.key)):
        if not record.owners:
            raise ValueError(f"Cannot build FV geometry because face {record.key} has no owner cell.")
        if len(record.owners) > 2:
            raise ValueError(f"Cannot build FV geometry because face {record.key} is nonmanifold.")
        owner = record.owners[0]
        neighbor = record.owners[1] if len(record.owners) == 2 else None
        face = _build_face_geometry(mesh, record, face_index=face_index, owner=owner, neighbor=neighbor)
        faces.append(face)
        if face.patch_name:
            boundary_patches.setdefault(face.patch_name, []).append(face.face_index)
    return FVGeometry(cells=cells, faces=faces, boundary_patches=boundary_patches)


def node_scalar_cell_gradients(mesh: UnstructuredMesh, node_values: dict[int, float]) -> dict[int, tuple[float, float, float]]:
    """Reconstruct one scalar gradient per cell from nodal values.

    This is an operator validation helper for U3 and later manufactured-solution
    tests. It does not claim to be the final cell-centered FVM gradient scheme.
    """

    gradients: dict[int, tuple[float, float, float]] = {}
    for index, cell in enumerate(mesh.cells):
        points = [mesh.nodes[tag].to_tuple() for tag in cell.node_tags]
        values = [float(node_values[tag]) for tag in cell.node_tags]
        if cell.kind in {"triangle", "quad"}:
            gradients[index] = _linear_gradient(points, values, dimension=2)
        elif cell.kind == "tetra":
            gradients[index] = _linear_gradient(points, values, dimension=3)
        else:
            raise ValueError(f"Unsupported cell kind for gradient reconstruction: {cell.kind}")
    return gradients


def _build_cell_geometry(mesh: UnstructuredMesh, index: int, cell: MeshElement) -> FVCellGeometry:
    signed_measure = mesh.cell_signed_measure(cell)
    return FVCellGeometry(
        cell_index=index,
        element_tag=cell.tag,
        kind=cell.kind,
        node_tags=cell.node_tags,
        center=mesh.cell_center(cell),
        signed_measure=signed_measure,
        measure=abs(signed_measure),
        physical_name=cell.primary_physical_name,
    )


def _build_face_geometry(
    mesh: UnstructuredMesh,
    record: FaceRecord,
    *,
    face_index: int,
    owner: int,
    neighbor: int | None,
) -> FVFaceGeometry:
    center = mesh.face_center(record.key)
    owner_center = mesh.cell_center(mesh.cells[owner])
    raw_area_vector = _raw_face_area_vector(mesh, record.key)
    owner_to_face = vector_sub(center, owner_center)
    if dot(raw_area_vector, owner_to_face) < 0:
        raw_area_vector = (-raw_area_vector[0], -raw_area_vector[1], -raw_area_vector[2])
    area = norm(raw_area_vector)
    non_orthogonality = None
    if neighbor is not None:
        neighbor_center = mesh.cell_center(mesh.cells[neighbor])
        owner_to_neighbor = vector_sub(neighbor_center, owner_center)
        denominator = norm(owner_to_neighbor) * area
        if denominator > 0:
            cosine = min(1.0, max(0.0, abs(dot(owner_to_neighbor, raw_area_vector)) / denominator))
            non_orthogonality = degrees(acos(cosine))
    return FVFaceGeometry(
        face_index=face_index,
        node_tags=record.key,
        owner=owner,
        neighbor=neighbor,
        center=center,
        area_vector=raw_area_vector,
        area=area,
        patch_name=record.patch_name,
        non_orthogonality_deg=non_orthogonality,
        boundary_element_tags=tuple(record.boundary_element_tags),
    )


def _raw_face_area_vector(mesh: UnstructuredMesh, key: tuple[int, ...]) -> tuple[float, float, float]:
    points = [mesh.nodes[tag].to_tuple() for tag in key]
    if len(points) == 2:
        edge = vector_sub(points[1], points[0])
        return (edge[1], -edge[0], 0.0)
    if len(points) == 3:
        normal = cross(vector_sub(points[1], points[0]), vector_sub(points[2], points[0]))
        return (0.5 * normal[0], 0.5 * normal[1], 0.5 * normal[2])
    if len(points) == 4:
        n1 = cross(vector_sub(points[1], points[0]), vector_sub(points[2], points[0]))
        n2 = cross(vector_sub(points[2], points[0]), vector_sub(points[3], points[0]))
        return (0.5 * (n1[0] + n2[0]), 0.5 * (n1[1] + n2[1]), 0.5 * (n1[2] + n2[2]))
    raise ValueError(f"Unsupported face with {len(points)} nodes.")


def _linear_gradient(points: list[tuple[float, float, float]], values: list[float], *, dimension: int) -> tuple[float, float, float]:
    if len(points) != len(values):
        raise ValueError("Point/value count mismatch for gradient reconstruction.")
    if dimension == 2:
        matrix = [[point[0], point[1], 1.0] for point in points]
        coeffs = _least_squares_solve(matrix, values, unknown_count=3)
        return (coeffs[0], coeffs[1], 0.0)
    if dimension == 3:
        matrix = [[point[0], point[1], point[2], 1.0] for point in points]
        coeffs = _least_squares_solve(matrix, values, unknown_count=4)
        return (coeffs[0], coeffs[1], coeffs[2])
    raise ValueError(f"Unsupported gradient dimension: {dimension}")


def _least_squares_solve(matrix: list[list[float]], values: list[float], *, unknown_count: int) -> list[float]:
    normal = [[0.0 for _ in range(unknown_count)] for _ in range(unknown_count)]
    rhs = [0.0 for _ in range(unknown_count)]
    for row, value in zip(matrix, values):
        for i in range(unknown_count):
            rhs[i] += row[i] * value
            for j in range(unknown_count):
                normal[i][j] += row[i] * row[j]
    return _solve_linear_system(normal, rhs)


def _solve_linear_system(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    size = len(rhs)
    augmented = [list(row) + [rhs[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot_row = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        pivot = augmented[pivot_row][column]
        if abs(pivot) < 1.0e-14:
            raise ValueError("Degenerate geometry for linear gradient reconstruction.")
        if pivot_row != column:
            augmented[column], augmented[pivot_row] = augmented[pivot_row], augmented[column]
        scale = augmented[column][column]
        for item in range(column, size + 1):
            augmented[column][item] /= scale
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            for item in range(column, size + 1):
                augmented[row][item] -= factor * augmented[column][item]
    return [augmented[row][size] for row in range(size)]
