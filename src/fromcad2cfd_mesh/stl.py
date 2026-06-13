"""Small STL inspection helpers with no third-party dependencies."""

from __future__ import annotations

from dataclasses import dataclass
import re
import struct
from pathlib import Path
from typing import Iterable


_VERTEX_RE = re.compile(r"^\s*vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$")


@dataclass(frozen=True)
class STLInspection:
    """Minimal STL topology summary for coarse solidification routing."""

    path: str
    file_size_bytes: int
    format: str
    triangle_count: int
    vertex_count: int
    unique_vertex_count: int
    unique_edge_count: int
    boundary_edge_count: int
    nonmanifold_edge_count: int

    @property
    def is_probably_watertight(self) -> bool:
        return self.triangle_count > 0 and self.boundary_edge_count == 0 and self.nonmanifold_edge_count == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "file_size_bytes": self.file_size_bytes,
            "format": self.format,
            "triangle_count": self.triangle_count,
            "vertex_count": self.vertex_count,
            "unique_vertex_count": self.unique_vertex_count,
            "unique_edge_count": self.unique_edge_count,
            "boundary_edge_count": self.boundary_edge_count,
            "nonmanifold_edge_count": self.nonmanifold_edge_count,
            "is_probably_watertight": self.is_probably_watertight,
        }


def _round_vertex(vertex: tuple[float, float, float], precision: int = 9) -> tuple[float, float, float]:
    return tuple(round(value, precision) for value in vertex)


def _edge_key(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    return tuple(sorted((_round_vertex(a), _round_vertex(b))))  # type: ignore[return-value]


def _edge_counts(triangles: Iterable[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]) -> tuple[int, int, int, int, int]:
    edge_counts: dict[tuple[tuple[float, float, float], tuple[float, float, float]], int] = {}
    vertices: list[tuple[float, float, float]] = []
    triangle_count = 0
    for tri in triangles:
        triangle_count += 1
        a, b, c = tri
        vertices.extend([a, b, c])
        for edge in (_edge_key(a, b), _edge_key(b, c), _edge_key(c, a)):
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    boundary = sum(1 for count in edge_counts.values() if count == 1)
    nonmanifold = sum(1 for count in edge_counts.values() if count > 2)
    return triangle_count, len(vertices), len({_round_vertex(vertex) for vertex in vertices}), len(edge_counts), boundary, nonmanifold


def _binary_triangles(data: bytes, triangle_count: int):
    offset = 84
    for _ in range(triangle_count):
        chunk = data[offset : offset + 50]
        values = struct.unpack("<12fH", chunk)
        yield (
            (float(values[3]), float(values[4]), float(values[5])),
            (float(values[6]), float(values[7]), float(values[8])),
            (float(values[9]), float(values[10]), float(values[11])),
        )
        offset += 50


def _ascii_triangles(text: str):
    vertices: list[tuple[float, float, float]] = []
    for line in text.splitlines():
        match = _VERTEX_RE.match(line)
        if match:
            vertices.append((float(match.group(1)), float(match.group(2)), float(match.group(3))))
            if len(vertices) == 3:
                yield (vertices[0], vertices[1], vertices[2])
                vertices = []


def inspect_stl(path: str | Path) -> STLInspection:
    source = Path(path)
    data = source.read_bytes()
    file_size = len(data)
    fmt = "ascii"
    triangles = []

    if file_size >= 84:
        count = struct.unpack("<I", data[80:84])[0]
        expected_size = 84 + 50 * count
        if expected_size == file_size:
            fmt = "binary"
            triangles = list(_binary_triangles(data, count))
        else:
            text = data.decode("utf-8", errors="ignore")
            triangles = list(_ascii_triangles(text))
    else:
        text = data.decode("utf-8", errors="ignore")
        triangles = list(_ascii_triangles(text))

    triangle_count, vertex_count, unique_vertex_count, unique_edge_count, boundary, nonmanifold = _edge_counts(triangles)
    return STLInspection(
        path=str(source),
        file_size_bytes=file_size,
        format=fmt,
        triangle_count=triangle_count,
        vertex_count=vertex_count,
        unique_vertex_count=unique_vertex_count,
        unique_edge_count=unique_edge_count,
        boundary_edge_count=boundary,
        nonmanifold_edge_count=nonmanifold,
    )
