"""Core unstructured mesh data structures.

This module intentionally models only mesh topology and metadata. It does not
run solvers or accept executable hooks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from pathlib import Path
from typing import Any


SUPPORTED_VOLUME_ELEMENT_TYPES = {2: "triangle", 3: "quad", 4: "tetra"}
SUPPORTED_BOUNDARY_ELEMENT_TYPES = {1: "line", 2: "triangle", 3: "quad"}
VTK_CELL_TYPES = {"line": 3, "triangle": 5, "quad": 9, "tetra": 10}


@dataclass(frozen=True)
class Node:
    tag: int
    x: float
    y: float
    z: float

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass(frozen=True)
class MeshElement:
    tag: int
    entity_dim: int
    entity_tag: int
    element_type: int
    node_tags: tuple[int, ...]
    physical_tags: tuple[int, ...] = ()
    physical_names: tuple[str, ...] = ()

    @property
    def kind(self) -> str:
        if self.entity_dim == 1 and self.element_type == 1:
            return "line"
        return SUPPORTED_VOLUME_ELEMENT_TYPES.get(self.element_type, f"unsupported_{self.element_type}")

    @property
    def primary_physical_tag(self) -> int | None:
        return self.physical_tags[0] if self.physical_tags else None

    @property
    def primary_physical_name(self) -> str | None:
        return self.physical_names[0] if self.physical_names else None


@dataclass
class FaceRecord:
    key: tuple[int, ...]
    owners: list[int] = field(default_factory=list)
    boundary_element_tags: list[int] = field(default_factory=list)
    physical_tags: set[int] = field(default_factory=set)
    physical_names: set[str] = field(default_factory=set)

    @property
    def is_boundary(self) -> bool:
        return len(self.owners) == 1

    @property
    def is_internal(self) -> bool:
        return len(self.owners) == 2

    @property
    def is_nonmanifold(self) -> bool:
        return len(self.owners) > 2

    @property
    def patch_name(self) -> str | None:
        return sorted(self.physical_names)[0] if self.physical_names else None


@dataclass
class UnstructuredMesh:
    source_path: str
    mesh_format: str
    nodes: dict[int, Node]
    cells: list[MeshElement]
    boundary_elements: list[MeshElement]
    physical_names: dict[tuple[int, int], str]
    entity_physical_tags: dict[tuple[int, int], tuple[int, ...]]
    warnings: list[str] = field(default_factory=list)

    @property
    def cell_dimension(self) -> int:
        if not self.cells:
            return 0
        return max(cell.entity_dim for cell in self.cells)

    def cell_type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for cell in self.cells:
            counts[cell.kind] = counts.get(cell.kind, 0) + 1
        return counts

    def boundary_zone_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for element in self.boundary_elements:
            name = element.primary_physical_name or "unassigned"
            counts[name] = counts.get(name, 0) + 1
        return counts

    def region_zone_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for cell in self.cells:
            name = cell.primary_physical_name or "unassigned"
            counts[name] = counts.get(name, 0) + 1
        return counts

    def faces(self) -> dict[tuple[int, ...], FaceRecord]:
        faces: dict[tuple[int, ...], FaceRecord] = {}
        for cell_index, cell in enumerate(self.cells):
            for key in cell_face_keys(cell):
                faces.setdefault(key, FaceRecord(key=key)).owners.append(cell_index)
        for element in self.boundary_elements:
            key = face_key(element.node_tags)
            record = faces.setdefault(key, FaceRecord(key=key))
            record.boundary_element_tags.append(element.tag)
            record.physical_tags.update(element.physical_tags)
            record.physical_names.update(element.physical_names)
        return faces

    def cell_center(self, cell: MeshElement) -> tuple[float, float, float]:
        points = [self.nodes[tag].to_tuple() for tag in cell.node_tags]
        count = len(points)
        return (
            sum(point[0] for point in points) / count,
            sum(point[1] for point in points) / count,
            sum(point[2] for point in points) / count,
        )

    def face_center(self, key: tuple[int, ...]) -> tuple[float, float, float]:
        points = [self.nodes[tag].to_tuple() for tag in key]
        count = len(points)
        return (
            sum(point[0] for point in points) / count,
            sum(point[1] for point in points) / count,
            sum(point[2] for point in points) / count,
        )

    def cell_signed_measure(self, cell: MeshElement) -> float:
        points = [self.nodes[tag].to_tuple() for tag in cell.node_tags]
        if cell.kind == "triangle":
            return triangle_signed_area_xy(points[0], points[1], points[2])
        if cell.kind == "quad":
            return polygon_signed_area_xy(points)
        if cell.kind == "tetra":
            return tetra_signed_volume(points[0], points[1], points[2], points[3])
        return 0.0

    def physical_name_table(self) -> list[dict[str, Any]]:
        rows = []
        for (dim, tag), name in sorted(self.physical_names.items()):
            rows.append({"dimension": dim, "tag": tag, "name": name})
        return rows

    def source_name(self) -> str:
        return Path(self.source_path).name


def face_key(node_tags: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(int(tag) for tag in node_tags))


def cell_face_keys(cell: MeshElement) -> list[tuple[int, ...]]:
    nodes = cell.node_tags
    if cell.kind == "triangle":
        return [face_key((nodes[0], nodes[1])), face_key((nodes[1], nodes[2])), face_key((nodes[2], nodes[0]))]
    if cell.kind == "quad":
        return [
            face_key((nodes[0], nodes[1])),
            face_key((nodes[1], nodes[2])),
            face_key((nodes[2], nodes[3])),
            face_key((nodes[3], nodes[0])),
        ]
    if cell.kind == "tetra":
        return [
            face_key((nodes[0], nodes[1], nodes[2])),
            face_key((nodes[0], nodes[1], nodes[3])),
            face_key((nodes[0], nodes[2], nodes[3])),
            face_key((nodes[1], nodes[2], nodes[3])),
        ]
    return []


def triangle_signed_area_xy(a: tuple[float, float, float], b: tuple[float, float, float], c: tuple[float, float, float]) -> float:
    return 0.5 * ((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def polygon_signed_area_xy(points: list[tuple[float, float, float]]) -> float:
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return 0.5 * area


def tetra_signed_volume(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    c: tuple[float, float, float],
    d: tuple[float, float, float],
) -> float:
    ab = vector_sub(b, a)
    ac = vector_sub(c, a)
    ad = vector_sub(d, a)
    return dot(ab, cross(ac, ad)) / 6.0


def vector_sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: tuple[float, float, float]) -> float:
    return sqrt(dot(a, a))
