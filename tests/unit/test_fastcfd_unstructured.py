from __future__ import annotations

import json
from pathlib import Path

import pytest

from fromcad2cfd.cli import main as root_main
from fromcad2cfd_fastcfd.capabilities import capability_inventory
from fromcad2cfd_fastcfd.unstructured.channel_validation import (
    run_channel_convergence_case,
    run_channel_validation_case,
    write_unit_square_channel_mesh,
)
from fromcad2cfd_fastcfd.unstructured.diffusion import run_scalar_diffusion_case
from fromcad2cfd_fastcfd.unstructured.flow import run_flow_benchmark_case
from fromcad2cfd_fastcfd.unstructured.geometry import build_fv_geometry, node_scalar_cell_gradients
from fromcad2cfd_fastcfd.unstructured.gmsh import read_gmsh_v4_ascii
from fromcad2cfd_fastcfd.unstructured.inspect import inspect_mesh_file
from fromcad2cfd_fastcfd.unstructured.linear import SparseMatrixCSR, solve_linear_system
from fromcad2cfd_fastcfd.unstructured.mesh import dot, vector_sub
from fromcad2cfd_fastcfd.unstructured.obstacle import run_obstacle_channel_evidence, write_rectangular_obstacle_channel_mesh
from fromcad2cfd_fastcfd.unstructured.projection import run_projection_benchmark_case
from fromcad2cfd_fastcfd.unstructured.stokes import run_stokes_benchmark_case
from fromcad2cfd_fastcfd.vof_transport import run_vof_lite_transport_benchmark


REPO_ROOT = Path(__file__).resolve().parents[2]
CHANNEL_MESH = REPO_ROOT / "examples" / "unstructured" / "channel2d.msh"


def test_unstructured_backend_is_declared():
    inventory = capability_inventory()

    assert "unstructured_mesh_gateway" in inventory["validation_gates"]
    assert "unstructured_scalar_diffusion" in inventory["validation_gates"]
    assert "unstructured_linear_system" in inventory["validation_gates"]
    assert "unstructured_stokes_momentum" in inventory["validation_gates"]
    assert "unstructured_pressure_projection" in inventory["validation_gates"]
    assert "unstructured_boundary_contract" in inventory["validation_gates"]
    assert "unstructured_iterative_flow_benchmark" in inventory["validation_gates"]
    assert "unstructured_channel_validation" in inventory["validation_gates"]
    assert "unstructured_channel_convergence" in inventory["validation_gates"]
    assert "unstructured_obstacle_channel_evidence" in inventory["validation_gates"]
    assert "vof_lite_alpha_transport" in inventory["validation_gates"]
    assert inventory["validation_gates"]["unstructured_scalar_diffusion"]["status"] == "implemented_u4_u5"
    assert inventory["validation_gates"]["unstructured_linear_system"]["status"] == "implemented_u5"
    assert inventory["validation_gates"]["unstructured_stokes_momentum"]["status"] == "implemented_u6"
    assert inventory["validation_gates"]["unstructured_pressure_projection"]["status"] == "implemented_u7"
    assert inventory["validation_gates"]["unstructured_boundary_contract"]["status"] == "implemented_u9"
    assert inventory["validation_gates"]["unstructured_iterative_flow_benchmark"]["status"] == "implemented_u8_u10_u11"
    assert inventory["validation_gates"]["unstructured_channel_validation"]["status"] == "implemented_u12_u13"
    assert inventory["validation_gates"]["unstructured_channel_convergence"]["status"] == "implemented_u14"
    assert inventory["validation_gates"]["unstructured_obstacle_channel_evidence"]["status"] == "implemented_u18"
    assert inventory["validation_gates"]["vof_lite_alpha_transport"]["status"] == "implemented_u19"
    assert inventory["backend_families"]["unstructured_fvm"]["status"] == "boundary_aware_channel_validation_u0_u14"
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


def test_unstructured_sparse_matrix_and_solvers_match_dense_reference():
    matrix = SparseMatrixCSR.from_triplets(
        3,
        3,
        [
            (0, 0, 4.0),
            (0, 1, -1.0),
            (1, 0, -1.0),
            (1, 1, 4.0),
            (1, 2, -1.0),
            (2, 1, -1.0),
            (2, 2, 3.0),
        ],
    )
    rhs = [15.0, 10.0, 10.0]

    assert matrix.shape == (3, 3)
    assert matrix.nnz == 7
    assert matrix.matvec([1.0, 2.0, 3.0]) == pytest.approx([2.0, 4.0, 7.0])

    dense = solve_linear_system(matrix, rhs, method="dense_direct")
    sparse = solve_linear_system(matrix, rhs, method="sparse_cg")

    assert dense.converged is True
    assert sparse.converged is True
    assert sparse.iterations > 0
    assert sparse.values == pytest.approx(dense.values, abs=1.0e-10)
    assert sparse.final_residual_l2 < 1.0e-10


def test_unstructured_scalar_diffusion_linear_solution_is_exact(tmp_path):
    result = run_scalar_diffusion_case(CHANNEL_MESH, output_dir=tmp_path, manufactured_solution="linear")

    assert result["status"] == "success"
    artifacts = result["outputs"]["artifacts"]
    for key in ["qoi", "linear_system", "residual_history", "solution_vtu", "fv_geometry", "diffusion_status"]:
        assert key in artifacts
        assert Path(artifacts[key]).exists()
    qoi = result["outputs"]["qoi"]
    assert qoi["schema_version"] == "fromcad2cfd_fastfluent_unstructured_scalar_diffusion_v1"
    assert qoi["manufactured_solution"] == "linear"
    assert qoi["metrics"]["node_linf_error"] == pytest.approx(0.0, abs=1.0e-10)
    assert qoi["metrics"]["cell_center_l2_error"] == pytest.approx(0.0, abs=1.0e-10)
    assert qoi["metrics"]["final_residual_l2"] < 1.0e-10
    assert qoi["linear_system"]["method"] == "sparse_cg"
    assert qoi["linear_system"]["storage"] == "csr"
    assert result["outputs"]["solver_execution"] == "scalar_diffusion_linear_system"


def test_unstructured_scalar_diffusion_sparse_and_dense_solvers_match(tmp_path):
    mesh_path = _write_unit_square_tri_mesh(tmp_path / "unit_square.msh", nx=3, ny=3)

    sparse_result = run_scalar_diffusion_case(
        mesh_path,
        output_dir=tmp_path / "sparse",
        manufactured_solution="quadratic_bubble",
        linear_solver="sparse_cg",
    )
    dense_result = run_scalar_diffusion_case(
        mesh_path,
        output_dir=tmp_path / "dense",
        manufactured_solution="quadratic_bubble",
        linear_solver="dense_direct",
    )

    assert sparse_result["status"] == "success"
    assert dense_result["status"] == "success"
    sparse_qoi = sparse_result["outputs"]["qoi"]
    dense_qoi = dense_result["outputs"]["qoi"]
    assert sparse_qoi["linear_system"]["method"] == "sparse_cg"
    assert dense_qoi["linear_system"]["method"] == "dense_direct"
    assert sparse_qoi["linear_system"]["nnz"] == dense_qoi["linear_system"]["nnz"]
    assert sparse_qoi["metrics"]["cell_center_l2_error"] == pytest.approx(
        dense_qoi["metrics"]["cell_center_l2_error"],
        abs=1.0e-10,
    )
    assert sparse_qoi["metrics"]["final_residual_l2"] < 1.0e-10


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
            "--linear-solver",
            "sparse-cg",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["solution_vtu"]).exists()
    assert Path(payload["outputs"]["artifacts"]["residual_history"]).exists()
    assert Path(payload["outputs"]["artifacts"]["linear_system"]).exists()
    assert payload["outputs"]["qoi"]["linear_system"]["method"] == "sparse_cg"


def test_unstructured_stokes_linear_divergence_free_solution_is_exact(tmp_path):
    result = run_stokes_benchmark_case(
        CHANNEL_MESH,
        output_dir=tmp_path,
        manufactured_solution="linear_divergence_free",
        pressure_gradient=(0.25, -0.75),
    )

    assert result["status"] == "success"
    artifacts = result["outputs"]["artifacts"]
    for key in ["stokes_qoi", "stokes_linear_systems", "stokes_residual_history", "stokes_solution_vtu", "stokes_status"]:
        assert key in artifacts
        assert Path(artifacts[key]).exists()
    qoi = result["outputs"]["qoi"]
    assert qoi["schema_version"] == "fromcad2cfd_fastfluent_unstructured_stokes_benchmark_v1"
    assert qoi["manufactured_solution"] == "linear_divergence_free"
    assert qoi["pressure"]["gradient"] == [0.25, -0.75]
    assert qoi["metrics"]["node_velocity_linf_error"] == pytest.approx(0.0, abs=1.0e-10)
    assert qoi["metrics"]["cell_center_velocity_l2_error"] == pytest.approx(0.0, abs=1.0e-10)
    assert qoi["metrics"]["cell_divergence_l2"] == pytest.approx(0.0, abs=1.0e-10)
    assert qoi["linear_systems"]["u"]["method"] == "sparse_cg"
    assert qoi["linear_systems"]["v"]["method"] == "sparse_cg"
    assert result["outputs"]["solver_execution"] == "stokes_momentum_linear_system"


def test_unstructured_stokes_pressure_driven_shear_error_decreases_with_refinement(tmp_path):
    coarse = _write_unit_square_tri_mesh(tmp_path / "stokes_coarse.msh", nx=2, ny=2)
    fine = _write_unit_square_tri_mesh(tmp_path / "stokes_fine.msh", nx=4, ny=4)

    coarse_result = run_stokes_benchmark_case(
        coarse,
        output_dir=tmp_path / "coarse_out",
        manufactured_solution="pressure_driven_shear",
        pressure_gradient=(1.0, 0.0),
    )
    fine_result = run_stokes_benchmark_case(
        fine,
        output_dir=tmp_path / "fine_out",
        manufactured_solution="pressure_driven_shear",
        pressure_gradient=(1.0, 0.0),
    )

    assert coarse_result["status"] == "success"
    assert fine_result["status"] == "success"
    coarse_qoi = coarse_result["outputs"]["qoi"]
    fine_qoi = fine_result["outputs"]["qoi"]
    coarse_error = coarse_qoi["metrics"]["cell_center_velocity_l2_error"]
    fine_error = fine_qoi["metrics"]["cell_center_velocity_l2_error"]
    assert coarse_error > 0
    assert fine_error < coarse_error
    assert fine_qoi["metrics"]["cell_divergence_l2"] == pytest.approx(0.0, abs=1.0e-10)
    assert fine_qoi["metrics"]["u_final_residual_l2"] < 1.0e-10
    assert fine_qoi["metrics"]["v_final_residual_l2"] < 1.0e-10


def test_unstructured_stokes_cli_route(tmp_path, capsys):
    exit_code = root_main(
        [
            "fastcfd",
            "unstructured",
            "solve-stokes",
            str(CHANNEL_MESH),
            "--output-dir",
            str(tmp_path),
            "--manufactured-solution",
            "linear_divergence_free",
            "--pressure-gradient",
            "0.25,-0.75",
            "--linear-solver",
            "sparse-cg",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["stokes_solution_vtu"]).exists()
    assert Path(payload["outputs"]["artifacts"]["stokes_qoi"]).exists()
    assert payload["outputs"]["qoi"]["pressure"]["gradient"] == [0.25, -0.75]
    assert payload["outputs"]["qoi"]["metrics"]["cell_divergence_l2"] < 1.0e-10


def test_unstructured_projection_reduces_divergence(tmp_path):
    mesh_path = _write_unit_square_tri_mesh(tmp_path / "projection.msh", nx=4, ny=4)

    result = run_projection_benchmark_case(
        mesh_path,
        output_dir=tmp_path / "projection_out",
        manufactured_solution="quadratic_correction",
        correction_strength=1.0,
    )

    assert result["status"] == "success"
    artifacts = result["outputs"]["artifacts"]
    for key in ["projection_qoi", "projection_linear_system", "projection_residual_history", "projection_solution_vtu", "projection_status"]:
        assert key in artifacts
        assert Path(artifacts[key]).exists()
    qoi = result["outputs"]["qoi"]
    metrics = qoi["metrics"]
    assert qoi["schema_version"] == "fromcad2cfd_fastfluent_unstructured_projection_benchmark_v1"
    assert qoi["manufactured_solution"] == "quadratic_correction"
    assert metrics["predicted_divergence_l2"] > 0.5
    assert metrics["corrected_divergence_l2"] < metrics["predicted_divergence_l2"]
    assert metrics["divergence_reduction_ratio"] < 1.0
    assert metrics["pressure_correction_final_residual_l2"] < 1.0e-10
    assert result["outputs"]["solver_execution"] == "pressure_projection_linear_system"


def test_unstructured_projection_error_decreases_with_refinement(tmp_path):
    coarse = _write_unit_square_tri_mesh(tmp_path / "projection_coarse.msh", nx=3, ny=3)
    fine = _write_unit_square_tri_mesh(tmp_path / "projection_fine.msh", nx=6, ny=6)

    coarse_result = run_projection_benchmark_case(coarse, output_dir=tmp_path / "coarse_out")
    fine_result = run_projection_benchmark_case(fine, output_dir=tmp_path / "fine_out")

    assert coarse_result["status"] == "success"
    assert fine_result["status"] == "success"
    coarse_metrics = coarse_result["outputs"]["qoi"]["metrics"]
    fine_metrics = fine_result["outputs"]["qoi"]["metrics"]
    assert fine_metrics["corrected_divergence_l2"] < coarse_metrics["corrected_divergence_l2"]
    assert fine_metrics["node_velocity_l2_error"] < coarse_metrics["node_velocity_l2_error"]


def test_unstructured_projection_cli_route(tmp_path, capsys):
    mesh_path = _write_unit_square_tri_mesh(tmp_path / "projection_cli.msh", nx=4, ny=4)

    exit_code = root_main(
        [
            "fastcfd",
            "unstructured",
            "solve-projection",
            str(mesh_path),
            "--output-dir",
            str(tmp_path / "projection_cli_out"),
            "--manufactured-solution",
            "quadratic_correction",
            "--correction-strength",
            "1.0",
            "--linear-solver",
            "sparse-cg",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["projection_solution_vtu"]).exists()
    assert Path(payload["outputs"]["artifacts"]["projection_qoi"]).exists()
    assert payload["outputs"]["qoi"]["metrics"]["divergence_reduction_ratio"] < 1.0


def test_unstructured_flow_benchmark_reduces_divergence_and_writes_artifacts(tmp_path):
    mesh_path = _write_unit_square_tri_mesh(tmp_path / "flow.msh", nx=4, ny=4)

    result = run_flow_benchmark_case(mesh_path, output_dir=tmp_path / "flow_out", iterations=5)

    assert result["status"] == "success"
    artifacts = result["outputs"]["artifacts"]
    for key in [
        "flow_boundary_contract",
        "flow_qoi",
        "flow_residual_history",
        "flow_solution_vtu",
        "flow_report",
        "flow_status",
    ]:
        assert key in artifacts
        assert Path(artifacts[key]).exists()
    qoi = result["outputs"]["qoi"]
    metrics = qoi["metrics"]
    assert qoi["schema_version"] == "fromcad2cfd_fastfluent_unstructured_flow_benchmark_v1"
    assert qoi["iterations"] == 5
    assert qoi["residual_history_rows"] == 5
    assert metrics["initial_divergence_l2"] > metrics["final_divergence_l2"]
    assert metrics["global_divergence_reduction_ratio"] < 1.0
    assert metrics["final_pressure_residual_l2"] < 1.0e-10
    assert result["outputs"]["boundary_contract"]["status"] == "passed"
    assert result["outputs"]["solver_execution"] == "iterative_projection_flow_benchmark"


def test_unstructured_flow_benchmark_boundary_contract_fails_closed(tmp_path):
    mesh_path = _write_unit_square_tri_mesh(tmp_path / "flow_missing_patch.msh", nx=2, ny=2)

    result = run_flow_benchmark_case(
        mesh_path,
        output_dir=tmp_path / "blocked",
        required_patches=("inlet", "outlet", "wall", "vent"),
    )

    assert result["status"] == "failed"
    assert result["outputs"]["boundary_contract"]["status"] == "failed"
    assert "vent" in result["outputs"]["boundary_contract"]["missing_required_patches"]
    assert result["outputs"]["solver_execution"] == "blocked_by_boundary_contract"
    assert Path(result["outputs"]["artifacts"]["flow_boundary_contract"]).exists()
    assert "flow_qoi" not in result["outputs"]["artifacts"]


def test_unstructured_flow_benchmark_cli_route(tmp_path, capsys):
    mesh_path = _write_unit_square_tri_mesh(tmp_path / "flow_cli.msh", nx=4, ny=4)

    exit_code = root_main(
        [
            "fastcfd",
            "unstructured",
            "solve-flow-benchmark",
            str(mesh_path),
            "--output-dir",
            str(tmp_path / "flow_cli_out"),
            "--iterations",
            "5",
            "--linear-solver",
            "sparse-cg",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["flow_solution_vtu"]).exists()
    assert Path(payload["outputs"]["artifacts"]["flow_qoi"]).exists()
    assert payload["outputs"]["qoi"]["metrics"]["global_divergence_reduction_ratio"] < 1.0


def test_unstructured_channel_validation_boundary_contract_drives_poiseuille_case(tmp_path):
    mesh_path = _write_unit_square_tri_mesh(tmp_path / "channel_validation.msh", nx=4, ny=4)

    result = run_channel_validation_case(mesh_path, output_dir=tmp_path / "channel_out", viscosity=1.0, pressure_drop=1.0)

    assert result["status"] == "success"
    artifacts = result["outputs"]["artifacts"]
    for key in [
        "channel_boundary_contract",
        "channel_qoi",
        "channel_residual_history",
        "channel_solution_vtu",
        "channel_report",
        "channel_status",
    ]:
        assert key in artifacts
        assert Path(artifacts[key]).exists()
    contract = result["outputs"]["boundary_contract"]
    qoi = result["outputs"]["qoi"]
    metrics = qoi["metrics"]
    assert contract["status"] == "passed"
    assert contract["conditions"]["inlet"]["kind"] == "velocity_profile_dirichlet"
    assert qoi["schema_version"] == "fromcad2cfd_fastfluent_unstructured_channel_validation_v1"
    assert qoi["solver_family"] == "boundary_aware_poiseuille_channel_validation"
    assert qoi["acceptance"]["linear_systems_converged"] is True
    assert qoi["acceptance"]["pressure_drives_positive_x_flow"] is True
    assert qoi["acceptance"]["divergence_within_benchmark_tolerance"] is True
    assert metrics["cell_center_velocity_l2_error"] > 0
    assert metrics["cell_divergence_l2"] < 1.0e-10
    assert metrics["u_final_residual_l2"] < 1.0e-10
    assert metrics["v_final_residual_l2"] < 1.0e-10
    assert result["outputs"]["solver_execution"] == "boundary_aware_poiseuille_channel_validation"


def test_unstructured_channel_validation_boundary_contract_fails_closed(tmp_path):
    mesh_path = _write_unit_square_tri_mesh(tmp_path / "channel_missing_patch.msh", nx=2, ny=2)

    result = run_channel_validation_case(
        mesh_path,
        output_dir=tmp_path / "blocked_channel",
        required_patches=("inlet", "outlet", "wall", "vent"),
    )

    assert result["status"] == "failed"
    assert result["outputs"]["boundary_contract"]["status"] == "failed"
    assert "vent" in result["outputs"]["boundary_contract"]["missing_required_patches"]
    assert result["outputs"]["solver_execution"] == "blocked_by_boundary_contract"
    assert Path(result["outputs"]["artifacts"]["channel_boundary_contract"]).exists()
    assert "channel_qoi" not in result["outputs"]["artifacts"]


def test_unstructured_channel_convergence_generated_meshes_decrease_error(tmp_path):
    result = run_channel_convergence_case(output_dir=tmp_path / "convergence", mesh_levels=(2, 4, 8))

    assert result["status"] == "success"
    artifacts = result["outputs"]["artifacts"]
    assert Path(artifacts["channel_convergence"]).exists()
    assert Path(artifacts["channel_convergence_report"]).exists()
    convergence = result["outputs"]["convergence"]
    errors = [case["cell_center_velocity_l2_error"] for case in convergence["cases"]]
    assert convergence["schema_version"] == "fromcad2cfd_fastfluent_unstructured_channel_convergence_v1"
    assert convergence["case_count"] == 3
    assert convergence["monotonic_error_decrease"] is True
    assert errors[2] < errors[1] < errors[0]
    assert all(order > 0 for order in convergence["observed_orders"])


def test_unstructured_channel_validation_cli_route(tmp_path, capsys):
    mesh_path = _write_unit_square_tri_mesh(tmp_path / "channel_cli.msh", nx=4, ny=4)

    exit_code = root_main(
        [
            "fastcfd",
            "unstructured",
            "solve-channel-validation",
            str(mesh_path),
            "--output-dir",
            str(tmp_path / "channel_cli_out"),
            "--pressure-drop",
            "1.0",
            "--linear-solver",
            "sparse-cg",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["channel_solution_vtu"]).exists()
    assert payload["outputs"]["qoi"]["metrics"]["cell_divergence_l2"] < 1.0e-10


def test_unstructured_channel_convergence_cli_route(tmp_path, capsys):
    exit_code = root_main(
        [
            "fastcfd",
            "unstructured",
            "solve-channel-convergence",
            "--output-dir",
            str(tmp_path / "channel_convergence_cli_out"),
            "--mesh-levels",
            "2,4,8",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["channel_convergence"]).exists()
    assert payload["outputs"]["convergence"]["monotonic_error_decrease"] is True


def test_unstructured_write_unit_square_channel_mesh(tmp_path):
    mesh_path = write_unit_square_channel_mesh(tmp_path / "generated_channel.msh", nx=3)
    mesh = read_gmsh_v4_ascii(mesh_path)

    assert mesh.boundary_zone_counts() == {"inlet": 3, "outlet": 3, "wall": 6}
    assert mesh.region_zone_counts() == {"fluid": 18}


def test_unstructured_public_obstacle_channel_mesh_preserves_body_fitted_patch(tmp_path):
    mesh_path = write_rectangular_obstacle_channel_mesh(tmp_path / "obstacle_channel.msh", nx=12, ny=6)
    mesh = read_gmsh_v4_ascii(mesh_path)

    assert mesh.boundary_zone_counts()["obstacle_wall"] > 0
    assert mesh.boundary_zone_counts()["inlet"] == 6
    assert mesh.boundary_zone_counts()["outlet"] == 6
    assert mesh.region_zone_counts()["fluid"] > 0

    result = run_obstacle_channel_evidence(mesh_path, output_dir=tmp_path / "obstacle_out")

    assert result["status"] == "success"
    qoi = result["outputs"]["qoi"]
    artifacts = result["outputs"]["artifacts"]
    assert qoi["schema_version"] == "fromcad2cfd_fastfluent_unstructured_obstacle_channel_evidence_v1"
    assert qoi["acceptance"]["obstacle_wall_present"] is True
    assert qoi["acceptance"]["public_synthetic_case"] is True
    assert qoi["blockage_ratio"] > 0
    for key in ["obstacle_mesh", "mesh_manifest", "mesh_quality", "obstacle_boundary_contract", "obstacle_qoi", "obstacle_report", "obstacle_status"]:
        assert Path(artifacts[key]).exists()


def test_unstructured_public_obstacle_channel_cli_route(tmp_path, capsys):
    exit_code = root_main(
        [
            "fastcfd",
            "unstructured",
            "solve-obstacle-channel",
            "--output-dir",
            str(tmp_path / "obstacle_cli_out"),
            "--nx",
            "12",
            "--ny",
            "6",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["obstacle_qoi"]).exists()
    assert payload["outputs"]["qoi"]["boundary_zone_counts"]["obstacle_wall"] > 0


def test_unstructured_vof_lite_alpha_transport_is_bounded(tmp_path):
    mesh_path = write_unit_square_channel_mesh(tmp_path / "vof_lite.msh", nx=4, ny=4)

    result = run_vof_lite_transport_benchmark(mesh_path, output_dir=tmp_path / "vof_lite_out", steps=8, time_step_s=0.01)

    assert result["status"] == "success"
    qoi = result["outputs"]["qoi"]
    metrics = qoi["metrics"]
    artifacts = result["outputs"]["artifacts"]
    assert qoi["schema_version"] == "fromcad2cfd_fastfluent_vof_lite_alpha_transport_v1"
    assert qoi["acceptance"]["bounded_alpha"] is True
    assert qoi["acceptance"]["courant_within_limit"] is True
    assert metrics["min_alpha"] >= 0.0
    assert metrics["max_alpha"] <= 1.0
    assert metrics["max_courant_number"] <= 0.5
    assert result["outputs"]["solver_execution"] == "vof_lite_bounded_alpha_transport"
    for key in ["vof_lite_history", "vof_lite_qoi", "vof_lite_solution_vtu", "vof_lite_report", "vof_lite_status"]:
        assert Path(artifacts[key]).exists()


def test_unstructured_vof_lite_cli_route(tmp_path, capsys):
    exit_code = root_main(
        [
            "fastcfd",
            "unstructured",
            "solve-vof-lite",
            "--output-dir",
            str(tmp_path / "vof_lite_cli_out"),
            "--steps",
            "8",
            "--time-step-s",
            "0.01",
            "--velocity",
            "0.1,0.0",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert Path(payload["outputs"]["artifacts"]["vof_lite_qoi"]).exists()
    assert payload["outputs"]["qoi"]["acceptance"]["bounded_alpha"] is True


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
