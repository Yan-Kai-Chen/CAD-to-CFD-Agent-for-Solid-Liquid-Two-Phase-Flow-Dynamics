"""Mesh-quality diagnostics for the unstructured FastFluent gateway."""

from __future__ import annotations

from math import acos, degrees
from typing import Any

from .mesh import UnstructuredMesh, cross, dot, norm, vector_sub


MESH_QUALITY_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_mesh_quality_v1"
MESH_MANIFEST_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_mesh_manifest_v1"


def build_mesh_manifest(mesh: UnstructuredMesh) -> dict[str, Any]:
    faces = mesh.faces()
    boundary_faces = [record for record in faces.values() if record.is_boundary]
    internal_faces = [record for record in faces.values() if record.is_internal]
    return {
        "schema_version": MESH_MANIFEST_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "solver_family": "finite_volume",
        "mesh_format": mesh.mesh_format,
        "mesh_source": mesh.source_path,
        "mesh_name": mesh.source_name(),
        "cell_dimension": mesh.cell_dimension,
        "node_count": len(mesh.nodes),
        "cell_count": len(mesh.cells),
        "boundary_element_count": len(mesh.boundary_elements),
        "boundary_face_count": len(boundary_faces),
        "internal_face_count": len(internal_faces),
        "cell_type_counts": mesh.cell_type_counts(),
        "boundary_zone_counts": mesh.boundary_zone_counts(),
        "region_zone_counts": mesh.region_zone_counts(),
        "physical_names": mesh.physical_name_table(),
        "notes": [
            "This is a mesh inspection artifact only; no unstructured flow solver is executed.",
            "Unstructured FVM support starts with mesh topology, quality, and named-zone preservation gates.",
        ],
    }


def evaluate_mesh_quality(mesh: UnstructuredMesh, *, required_patches: tuple[str, ...] = ("inlet", "outlet", "wall")) -> dict[str, Any]:
    faces = mesh.faces()
    boundary_faces = [record for record in faces.values() if record.is_boundary]
    internal_faces = [record for record in faces.values() if record.is_internal]
    nonmanifold_faces = [record for record in faces.values() if record.is_nonmanifold]
    ungrouped_boundary_faces = [record for record in boundary_faces if not record.physical_names]
    orphan_boundary_elements = [
        element
        for element in mesh.boundary_elements
        if tuple(sorted(element.node_tags)) not in faces or not faces[tuple(sorted(element.node_tags))].owners
    ]
    signed_measures = [mesh.cell_signed_measure(cell) for cell in mesh.cells]
    positive_measures = [value for value in signed_measures if value > 0]
    negative_or_zero = [value for value in signed_measures if value <= 0]
    boundary_zone_counts = mesh.boundary_zone_counts()
    region_zone_counts = mesh.region_zone_counts()
    missing_required = [name for name in required_patches if boundary_zone_counts.get(name, 0) <= 0]
    if not region_zone_counts or (len(region_zone_counts) == 1 and "unassigned" in region_zone_counts):
        missing_required.append("fluid")
    max_non_orthogonality = _max_non_orthogonality_deg(mesh, internal_faces)
    min_measure = min(positive_measures) if positive_measures else None
    max_measure = max(positive_measures) if positive_measures else None
    measure_ratio = max_measure / min_measure if min_measure and max_measure else None
    checks = {
        "positive_cell_measures": len(negative_or_zero) == 0,
        "required_patches_present": not missing_required,
        "boundary_faces_grouped": len(ungrouped_boundary_faces) == 0,
        "no_orphan_boundary_elements": len(orphan_boundary_elements) == 0,
        "no_nonmanifold_faces": len(nonmanifold_faces) == 0,
    }
    blocking_errors = []
    if negative_or_zero:
        blocking_errors.append(f"{len(negative_or_zero)} cells have non-positive signed area/volume.")
    if missing_required:
        blocking_errors.append(f"Missing required boundary or region names: {', '.join(sorted(set(missing_required)))}.")
    if ungrouped_boundary_faces:
        blocking_errors.append(f"{len(ungrouped_boundary_faces)} boundary faces have no physical group.")
    if orphan_boundary_elements:
        blocking_errors.append(f"{len(orphan_boundary_elements)} boundary elements do not match a cell boundary face.")
    if nonmanifold_faces:
        blocking_errors.append(f"{len(nonmanifold_faces)} faces have more than two owner cells.")
    status = "failed" if blocking_errors else "passed"
    return {
        "schema_version": MESH_QUALITY_SCHEMA_VERSION,
        "backend": "unstructured_fvm",
        "status": status,
        "checks": checks,
        "blocking_errors": blocking_errors,
        "warnings": list(mesh.warnings),
        "required_patches": list(required_patches),
        "missing_required_patches": sorted(set(missing_required)),
        "metrics": {
            "node_count": len(mesh.nodes),
            "cell_count": len(mesh.cells),
            "boundary_face_count": len(boundary_faces),
            "internal_face_count": len(internal_faces),
            "boundary_element_count": len(mesh.boundary_elements),
            "nonmanifold_face_count": len(nonmanifold_faces),
            "ungrouped_boundary_face_count": len(ungrouped_boundary_faces),
            "orphan_boundary_element_count": len(orphan_boundary_elements),
            "non_positive_cell_measure_count": len(negative_or_zero),
            "min_positive_cell_measure": min_measure,
            "max_positive_cell_measure": max_measure,
            "cell_measure_ratio": measure_ratio,
            "max_non_orthogonality_deg_proxy": max_non_orthogonality,
        },
        "boundary_zone_counts": boundary_zone_counts,
        "region_zone_counts": region_zone_counts,
        "limitations": [
            "Quality metrics are pre-solver gate diagnostics, not a substitute for a full CFD mesh-quality audit.",
            "Non-orthogonality and skewness are lightweight proxies for early agent screening.",
        ],
    }


def _max_non_orthogonality_deg(mesh: UnstructuredMesh, internal_faces) -> float | None:
    values = []
    for record in internal_faces:
        if len(record.owners) != 2:
            continue
        owner = mesh.cells[record.owners[0]]
        neighbor = mesh.cells[record.owners[1]]
        owner_center = mesh.cell_center(owner)
        neighbor_center = mesh.cell_center(neighbor)
        center_delta = vector_sub(neighbor_center, owner_center)
        face_normal = _face_normal(mesh, record.key)
        denom = norm(center_delta) * norm(face_normal)
        if denom <= 0:
            continue
        cosine = min(1.0, max(0.0, abs(dot(center_delta, face_normal)) / denom))
        values.append(degrees(acos(cosine)))
    return max(values) if values else None


def _face_normal(mesh: UnstructuredMesh, key: tuple[int, ...]) -> tuple[float, float, float]:
    points = [mesh.nodes[tag].to_tuple() for tag in key]
    if len(points) == 2:
        edge = vector_sub(points[1], points[0])
        return (-edge[1], edge[0], 0.0)
    if len(points) >= 3:
        return cross(vector_sub(points[1], points[0]), vector_sub(points[2], points[0]))
    return (0.0, 0.0, 0.0)
