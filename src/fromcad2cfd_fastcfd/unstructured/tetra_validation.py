"""Public-safe 3D tetrahedron mesh validation route for FastFluent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..paths import unique_path
from .diffusion import run_scalar_diffusion_case
from .mesh import tetra_signed_volume


TETRA_REQUIRED_PATCHES = ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")


def run_tetra_diffusion_case(
    mesh_file: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    diffusivity: float = 1.0,
    linear_solver: str = "sparse_cg",
    linear_tolerance: float = 1.0e-12,
    max_linear_iterations: int | None = None,
) -> dict[str, Any]:
    """Run the public 3D tetra scalar-diffusion smoke benchmark.

    If no mesh is provided, a synthetic unit cube is generated with six named
    surface patches, one interior node, and twelve tetrahedra. The solve uses a
    linear manufactured solution, so the internal node verifies 3D P1 assembly
    rather than only boundary-value plumbing.
    """

    target_dir = Path(output_dir) if output_dir else unique_path(Path.cwd() / "tetra_diffusion")
    target_dir.mkdir(parents=True, exist_ok=True)
    mesh_path = Path(mesh_file) if mesh_file else write_unit_cube_tetra_mesh(target_dir / "unit_cube_tetra.msh")
    result = run_scalar_diffusion_case(
        mesh_path,
        output_dir=target_dir,
        manufactured_solution="linear",
        diffusivity=diffusivity,
        linear_solver=linear_solver,
        linear_tolerance=linear_tolerance,
        max_linear_iterations=max_linear_iterations,
        required_patches=TETRA_REQUIRED_PATCHES,
    )
    outputs = result.setdefault("outputs", {})
    artifacts = outputs.setdefault("artifacts", {})
    artifacts.setdefault("tetra_mesh", str(mesh_path))
    outputs["tetra_case"] = {
        "schema_version": "fromcad2cfd_fastfluent_unstructured_tetra_case_v1",
        "mesh_file": str(mesh_path),
        "required_patches": list(TETRA_REQUIRED_PATCHES),
        "generated_mesh": mesh_file is None,
        "scope": "3D tetra mesh geometry and scalar diffusion assembly validation only.",
        "limitations": [
            "This gate validates tetra topology, FV geometry, and scalar diffusion assembly.",
            "It is not a 3D Navier-Stokes, VOF, turbulence, Fluent, or GPU solver.",
        ],
    }
    return result


def write_unit_cube_tetra_mesh(path: str | Path) -> Path:
    """Write a public synthetic unit-cube tetra mesh in Gmsh v4 ASCII."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    nodes = {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (1.0, 1.0, 0.0),
        4: (0.0, 1.0, 0.0),
        5: (0.0, 0.0, 1.0),
        6: (1.0, 0.0, 1.0),
        7: (1.0, 1.0, 1.0),
        8: (0.0, 1.0, 1.0),
        9: (0.5, 0.5, 0.5),
    }
    boundary_blocks = [
        (1, "xmin", [(1, 4, 8), (1, 8, 5)]),
        (2, "xmax", [(2, 3, 7), (2, 7, 6)]),
        (3, "ymin", [(1, 5, 6), (1, 6, 2)]),
        (4, "ymax", [(3, 4, 8), (3, 8, 7)]),
        (5, "zmin", [(1, 2, 3), (1, 3, 4)]),
        (6, "zmax", [(5, 7, 8), (5, 6, 7)]),
    ]
    boundary_faces = [face for _tag, _name, faces in boundary_blocks for face in faces]
    tetrahedra = [_orient_tetra(nodes, (*face, 9)) for face in boundary_faces]
    element_count = len(boundary_faces) + len(tetrahedra)
    lines = [
        "$MeshFormat",
        "4.1 0 8",
        "$EndMeshFormat",
        "$PhysicalNames",
        "7",
        '2 1 "xmin"',
        '2 2 "xmax"',
        '2 3 "ymin"',
        '2 4 "ymax"',
        '2 5 "zmin"',
        '2 6 "zmax"',
        '3 10 "fluid"',
        "$EndPhysicalNames",
        "$Entities",
        "0 0 6 1",
        "1 0 0 0 0 1 1 1 1",
        "2 1 0 0 1 1 1 1 2",
        "3 0 0 0 1 0 1 1 3",
        "4 0 1 0 1 1 1 1 4",
        "5 0 0 0 1 1 0 1 5",
        "6 0 0 1 1 1 1 1 6",
        "1 0 0 0 1 1 1 1 10",
        "$EndEntities",
        "$Nodes",
        f"1 {len(nodes)} 1 {len(nodes)}",
        f"3 1 0 {len(nodes)}",
    ]
    lines.extend(str(tag) for tag in sorted(nodes))
    for tag in sorted(nodes):
        x, y, z = nodes[tag]
        lines.append(f"{x:.17g} {y:.17g} {z:.17g}")
    lines.extend(["$EndNodes", "$Elements", f"7 {element_count} 1 {element_count}"])
    element_tag = 1
    for entity_tag, _name, faces in boundary_blocks:
        lines.append(f"2 {entity_tag} 2 {len(faces)}")
        for face in faces:
            lines.append(f"{element_tag} {' '.join(str(node) for node in face)}")
            element_tag += 1
    lines.append(f"3 1 4 {len(tetrahedra)}")
    for tetra in tetrahedra:
        lines.append(f"{element_tag} {' '.join(str(node) for node in tetra)}")
        element_tag += 1
    lines.append("$EndElements")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _orient_tetra(nodes: dict[int, tuple[float, float, float]], tetra: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    points = [nodes[tag] for tag in tetra]
    if tetra_signed_volume(points[0], points[1], points[2], points[3]) > 0:
        return tetra
    return (tetra[0], tetra[2], tetra[1], tetra[3])
