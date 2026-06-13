from __future__ import annotations

import json
from pathlib import Path

import pytest

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fastcfd.capabilities import capability_inventory
from fromcad2cfd_fastcfd.unstructured.diffusion import run_scalar_diffusion_case
from fromcad2cfd_fastcfd.unstructured.geometry import build_fv_geometry, node_scalar_cell_gradients
from fromcad2cfd_fastcfd.unstructured.gmsh import read_gmsh_v4_ascii
from fromcad2cfd_fastcfd.unstructured.inspect import inspect_mesh_file
from fromcad2cfd_fastcfd.unstructured.mesh import dot, vector_sub


REPO_ROOT = Path(__file__).resolve().parents[2]
CHANNEL_MESH = REPO_ROOT / "examples" / "unstructured" / "channel2d.msh"


def test_unstructured_backend_is_declared():
    inventory = capability_inventory()

    assert "unstructured_mesh_gateway" in inventory["validation_gates"]
    assert "unstructured_scalar_diffusion" in inventory["validation_gates"]
    assert inventory["validation_gates"]["unstructured_scalar_diffusion"]["status"] == "implemented_u4"
    assert inventory["backend_families"]["unstructured_fvm"]["status"] == "mesh_gateway_and_scalar_diffusion_u0_u4"
    assert "unstructured_fvm" in inventory["safe_backends"]
    assert "unstructured_flow_solver_without_mesh_quality_gate" in inventory["disabled_capabilities"]


def test_unstructured_inspect_mesh_preserves_zones_and_writes_outputs(tmp_path):
    result = inspect_mesh_file(CHANNEL_MESH, output_dir=tmp_path, required_patches=("inlet", "outlet", "wall"))

    assert result["status"] == "success"
    artifacts = result["outputs"]["artifacts"]
    for key in ["mesh_manifest", "mesh_quality", "mesh_report", "mesh_vtu", "fv_geometry", "inspection_status"]:
        assert key in artifacts
        assert Path(artifacts[key]).exists()
    manifest = json.loads(Path(artifacts["mesh_manifest"]).read_text(encoding="utf-8"))
    quality = json.loads(Path(artifacts["mesh_quality"]).read_text(encoding="utf-8"))
    fv_geometry = json.loads(Path(artifacts["fv_geometry"]).read_text(encoding="utf-8"))
    assert manifest["backend"] == "unstructured_fvm"
    assert manifest["solver_family"] == "finite_volume"
    assert manifest["cell_count"] == 2
    assert manifest["boundary_zone_counts"] == {"inlet": 1, "outlet": 1, "wall": 2}
    assert manifest["region_zone_counts"] == {"fluid": 2}
    assert quality["status"] == "passed"
    assert quality["metrics"]["non_positive_cell_measure_count"] == 0
    assert quality["checks"]["required_patches_present"] is True
    assert fv_geometry["schema_version"] == "fromcad2cfd_fastfluent_unstructured_fv_geometry_v1"
    assert fv_geometry["cell_count"] == 2
    assert fv_geometry["face_count"] == 5
    assert sorted(fv_geometry["boundary_patches"]) == ["inlet", "outlet", "wall"]
    assert len(fv_geometry["boundary_patches"]["inlet"]) == 1
    assert len(fv_geometry["boundary_patches"]["outlet"]) == 1
    assert len(fv_geometry["boundary_patches"]["wall"]) == 2


def test_unstructured_inspect_mesh_missing_required_patch_fails_closed(tmp_path):
    result = inspect_mesh_file(CHANNEL_MESH, output_dir=tmp_path, required_patches=("inlet", "outlet", "wall", "vent"))

    assert result["status"] == "failed"
    quality = result["outputs"]["quality"]
    assert "vent" in quality["missing_required_patches"]
    assert result["outputs"]["solver_execution"] == "not_attempted"
    assert result["outputs"]["fv_geometry"] is None
    assert Path(result["outputs"]["artifacts"]["mesh_quality"]).exists()


def test_unstructured_inspect_mesh_negative_area_fails_closed(tmp_path):
    invalid_mesh = tmp_path / "negative_area.msh"
    invalid_mesh.write_text(CHANNEL_MESH.read_text(encoding="utf-8").replace("5 1 2 3", "5 1 3 2"), encoding="utf-8")

    result = inspect_mesh_file(invalid_mesh, output_dir=tmp_path / "inspect", required_patches=("inlet", "outlet", "wall"))

    assert result["status"] == "failed"
    assert result["outputs"]["quality"]["metrics"]["non_positive_cell_measure_count"] == 1
    assert any("non-positive" in error for error in result["errors"])


def test_unstructured_inspect_mesh_cli_route(tmp_path, capsys):
    exit_code = root_main(
        [
            "fastcfd",
            "unstructured",
            "inspect-mesh",
            str(CHANNEL_MESH),
            "--output-dir",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["mesh_vtu"]).exists()
    assert Path(payload["outputs"]["artifacts"]["fv_geometry"]).exists()


def test_unstructured_fv_geometry_orients_area_vectors_from_owner():
    mesh = read_gmsh_v4_ascii(CHANNEL_MESH)
    geometry = build_fv_geometry(mesh)

    assert len(geometry.cells) == 2
    assert len(geometry.faces) == 5
    assert all(cell.measure > 0 for cell in geometry.cells)
    for face in geometry.faces:
        owner_center = geometry.cells[face.owner].center
        owner_to_face = vector_sub(face.center, owner_center)
        assert dot(face.area_vector, owner_to_face) >= -1.0e-12
        assert face.area > 0
        if face.neighbor is not None:
            neighbor_center = geometry.cells[face.neighbor].center
            owner_to_neighbor = vector_sub(neighbor_center, owner_center)
            assert dot(face.area_vector, owner_to_neighbor) > 0
            assert face.non_orthogonality_deg is not None


def test_unstructured_node_scalar_gradients_reconstruct_constant_and_linear_fields():
    mesh = read_gmsh_v4_ascii(CHANNEL_MESH)
    constant_values = {tag: 7.0 for tag in mesh.nodes}
    linear_values = {tag: 2.0 * node.x - 3.0 * node.y + 5.0 for tag, node in mesh.nodes.items()}

    constant_gradients = node_scalar_cell_gradients(mesh, constant_values)
    linear_gradients = node_scalar_cell_gradients(mesh, linear_values)

    for gradient in constant_gradients.values():
        assert gradient[0] == pytest.approx(0.0, abs=1.0e-12)
        assert gradient[1] == pytest.approx(0.0, abs=1.0e-12)
        assert gradient[2] == pytest.approx(0.0, abs=1.0e-12)
    for gradient in linear_gradients.values():
        assert gradient[0] == pytest.approx(2.0)
        assert gradient[1] == pytest.approx(-3.0)
        assert gradient[2] == pytest.approx(0.0)


def test_unstructured_scalar_diffusion_linear_solution_is_exact(tmp_path):
    result = run_scalar_diffusion_case(CHANNEL_MESH, output_dir=tmp_path, manufactured_solution="linear")

    assert result["status"] == "success"
    artifacts = result["outputs"]["artifacts"]
    for key in ["qoi", "residual_history", "solution_vtu", "fv_geometry", "diffusion_status"]:
        assert key in artifacts
        assert Path(artifacts[key]).exists()
    qoi = result["outputs"]["qoi"]
    assert qoi["schema_version"] == "fromcad2cfd_fastfluent_unstructured_scalar_diffusion_v1"
    assert qoi["manufactured_solution"] == "linear"
    assert qoi["metrics"]["node_linf_error"] == pytest.approx(0.0, abs=1.0e-10)
    assert qoi["metrics"]["cell_center_l2_error"] == pytest.approx(0.0, abs=1.0e-10)
    assert qoi["metrics"]["final_residual_l2"] < 1.0e-10
    assert result["outputs"]["solver_execution"] == "scalar_diffusion"


def test_unstructured_scalar_diffusion_quadratic_error_decreases_with_refinement(tmp_path):
    coarse = _write_unit_square_tri_mesh(tmp_path / "coarse.msh", nx=2, ny=2)
    fine = _write_unit_square_tri_mesh(tmp_path / "fine.msh", nx=4, ny=4)

    coarse_result = run_scalar_diffusion_case(coarse, output_dir=tmp_path / "coarse_out", manufactured_solution="quadratic_bubble")
    fine_result = run_scalar_diffusion_case(fine, output_dir=tmp_path / "fine_out", manufactured_solution="quadratic_bubble")

    assert coarse_result["status"] == "success"
    assert fine_result["status"] == "success"
    coarse_error = coarse_result["outputs"]["qoi"]["metrics"]["cell_center_l2_error"]
    fine_error = fine_result["outputs"]["qoi"]["metrics"]["cell_center_l2_error"]
    assert coarse_error > 0
    assert fine_error < coarse_error
    assert fine_result["outputs"]["qoi"]["metrics"]["final_residual_l2"] < 1.0e-10


def test_unstructured_scalar_diffusion_cli_route(tmp_path, capsys):
    exit_code = root_main(
        [
            "fastcfd",
            "unstructured",
            "solve-diffusion",
            str(CHANNEL_MESH),
            "--output-dir",
            str(tmp_path),
            "--manufactured-solution",
            "linear",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["solution_vtu"]).exists()
    assert Path(payload["outputs"]["artifacts"]["residual_history"]).exists()


def _write_unit_square_tri_mesh(path: Path, *, nx: int, ny: int) -> Path:
    def node_tag(i: int, j: int) -> int:
        return j * (nx + 1) + i + 1

    node_count = (nx + 1) * (ny + 1)
    triangle_count = 2 * nx * ny
    boundary_count = 2 * nx + 2 * ny
    element_count = triangle_count + boundary_count
    lines = [
        "$MeshFormat",
        "4.1 0 8",
        "$EndMeshFormat",
        "$PhysicalNames",
        "4",
        '1 1 "inlet"',
        '1 2 "outlet"',
        '1 3 "wall"',
        '2 10 "fluid"',
        "$EndPhysicalNames",
        "$Entities",
        "0 4 1 0",
        "1 0 0 0 0 1 0 1 1",
        "2 1 0 0 1 1 0 1 2",
        "3 0 0 0 1 0 0 1 3",
        "4 0 1 0 1 1 0 1 3",
        "1 0 0 0 1 1 0 1 10",
        "$EndEntities",
        "$Nodes",
        f"1 {node_count} 1 {node_count}",
        f"2 1 0 {node_count}",
    ]
    lines.extend(str(tag) for tag in range(1, node_count + 1))
    for j in range(ny + 1):
        for i in range(nx + 1):
            lines.append(f"{i / nx:.17g} {j / ny:.17g} 0")
    lines.extend(
        [
            "$EndNodes",
            "$Elements",
            f"5 {element_count} 1 {element_count}",
            f"1 1 1 {ny}",
        ]
    )
    element_tag = 1
    for j in range(ny):
        lines.append(f"{element_tag} {node_tag(0, j)} {node_tag(0, j + 1)}")
        element_tag += 1
    lines.append(f"1 2 1 {ny}")
    for j in range(ny):
        lines.append(f"{element_tag} {node_tag(nx, j)} {node_tag(nx, j + 1)}")
        element_tag += 1
    lines.append(f"1 3 1 {nx}")
    for i in range(nx):
        lines.append(f"{element_tag} {node_tag(i, 0)} {node_tag(i + 1, 0)}")
        element_tag += 1
    lines.append(f"1 4 1 {nx}")
    for i in range(nx):
        lines.append(f"{element_tag} {node_tag(i, ny)} {node_tag(i + 1, ny)}")
        element_tag += 1
    lines.append(f"2 1 2 {triangle_count}")
    for j in range(ny):
        for i in range(nx):
            n00 = node_tag(i, j)
            n10 = node_tag(i + 1, j)
            n11 = node_tag(i + 1, j + 1)
            n01 = node_tag(i, j + 1)
            lines.append(f"{element_tag} {n00} {n10} {n11}")
            element_tag += 1
            lines.append(f"{element_tag} {n00} {n11} {n01}")
            element_tag += 1
    lines.append("$EndElements")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
