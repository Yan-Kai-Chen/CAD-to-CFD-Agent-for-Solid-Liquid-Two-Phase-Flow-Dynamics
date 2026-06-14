"""Agent-safe JSON case runner for unstructured FastFluent routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from ..paths import unique_path
from .boundary import BoundaryCondition, boundary_conditions_from_dict
from .steady_incompressible import run_steady_incompressible_case


UNSTRUCTURED_CASE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_case_v1"


def run_unstructured_case_file(
    case_file: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run an agent-safe unstructured case JSON file."""

    case_path = Path(case_file)
    target_dir = Path(output_dir) if output_dir else unique_path(case_path.parent / f"{case_path.stem}_run")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        raw = json.loads(case_path.read_text(encoding="utf-8"))
        normalized = normalize_unstructured_case(raw, case_path=case_path)
        normalized_path = _write_json(target_dir / "normalized_case.json", normalized)
        solver_family = normalized["solver"]["family"]
        if solver_family != "steady_incompressible":
            failure = AgentResult.failed(
                backend="unstructured_fvm",
                operation="run_unstructured_case",
                message="Unstructured case solver family is not implemented.",
                errors=[f"Unsupported solver family: {solver_family}"],
                metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
            )
            failure.outputs["artifacts"] = {
                "normalized_case": str(normalized_path),
                "case_status": str(target_dir / "case_status.json"),
            }
            _write_json(target_dir / "case_status.json", failure.to_dict())
            return failure.to_dict()
        conditions = _conditions_from_normalized_case(normalized)
        result = run_steady_incompressible_case(
            normalized["mesh_file"],
            output_dir=target_dir / "steady_incompressible",
            boundary_conditions=conditions,
            required_patches=tuple(normalized["required_patches"]),
            density=normalized["physics"]["density"],
            viscosity=normalized["physics"]["viscosity"],
            body_force=tuple(normalized["physics"]["body_force"]),
            iterations=normalized["solver"]["iterations"],
            pressure_relaxation=normalized["solver"]["pressure_relaxation"],
            linear_solver=normalized["solver"]["linear_solver"],
            linear_tolerance=normalized["solver"]["linear_tolerance"],
            max_linear_iterations=normalized["solver"]["max_linear_iterations"],
        )
        artifacts = result.setdefault("outputs", {}).setdefault("artifacts", {})
        artifacts["normalized_case"] = str(normalized_path)
        result["outputs"]["case"] = normalized
        result["outputs"]["runner_execution"] = "unstructured_case_runner"
        result.setdefault("metadata", {}).update({"case_file": str(case_path), "output_dir": str(target_dir)})
        artifacts["case_status"] = str(_write_json(target_dir / "case_status.json", result))
        return result
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failure = AgentResult.failed(
            backend="unstructured_fvm",
            operation="run_unstructured_case",
            message="Unstructured case failed before solver dispatch.",
            errors=[str(exc)],
            metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"case_status": str(target_dir / "case_status.json")}
        _write_json(target_dir / "case_status.json", failure.to_dict())
        return failure.to_dict()


def normalize_unstructured_case(raw: dict[str, Any], *, case_path: Path | None = None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Unstructured case must be a JSON object.")
    mesh_file = raw.get("mesh_file")
    if not isinstance(mesh_file, str) or not mesh_file:
        raise ValueError("Unstructured case requires a non-empty mesh_file.")
    base = case_path.parent if case_path else Path.cwd()
    mesh_path = Path(mesh_file)
    if not mesh_path.is_absolute():
        mesh_path = (base / mesh_path).resolve()
    boundary_payload = raw.get("boundary_conditions")
    if not isinstance(boundary_payload, dict) or not boundary_payload:
        raise ValueError("Unstructured case requires boundary_conditions.")
    conditions = boundary_conditions_from_dict(boundary_payload)
    physics = raw.get("physics") or {}
    if not isinstance(physics, dict):
        raise ValueError("Unstructured case physics must be an object when provided.")
    solver = raw.get("solver") or {}
    if not isinstance(solver, dict):
        raise ValueError("Unstructured case solver must be an object when provided.")
    body_force = physics.get("body_force", [0.0, 0.0])
    if not _is_numeric_vector(body_force, length=2):
        raise ValueError("Unstructured case physics.body_force must contain two numbers.")
    required_patches = raw.get("required_patches") or list(boundary_payload)
    if not isinstance(required_patches, list) or not all(isinstance(item, str) and item for item in required_patches):
        raise ValueError("Unstructured case required_patches must be a list of patch names.")
    normalized = {
        "schema_version": UNSTRUCTURED_CASE_SCHEMA_VERSION,
        "case_name": str(raw.get("case_name") or Path(mesh_file).stem),
        "mesh_file": str(mesh_path),
        "required_patches": required_patches,
        "physics": {
            "model": str(physics.get("model") or "steady_incompressible"),
            "density": float(physics.get("density", 1.0)),
            "viscosity": float(physics.get("viscosity", 1.0e-3)),
            "body_force": [float(body_force[0]), float(body_force[1])],
        },
        "boundary_conditions": {name: condition.to_dict() for name, condition in sorted(conditions.items())},
        "solver": {
            "family": str(solver.get("family") or physics.get("model") or "steady_incompressible"),
            "iterations": int(solver.get("iterations", 8)),
            "pressure_relaxation": float(solver.get("pressure_relaxation", 0.45)),
            "linear_solver": str(solver.get("linear_solver", "sparse_cg")),
            "linear_tolerance": float(solver.get("linear_tolerance", 1.0e-12)),
            "max_linear_iterations": solver.get("max_linear_iterations"),
        },
        "limitations": [
            "This case schema is an agent-safe unstructured FastFluent route.",
            "The current executable solver family is steady_incompressible.",
            "Unsupported solver families or boundary-condition kinds fail closed.",
        ],
    }
    if normalized["physics"]["density"] <= 0:
        raise ValueError("Unstructured case physics.density must be positive.")
    if normalized["physics"]["viscosity"] <= 0:
        raise ValueError("Unstructured case physics.viscosity must be positive.")
    if normalized["solver"]["iterations"] < 1:
        raise ValueError("Unstructured case solver.iterations must be at least 1.")
    if normalized["solver"]["max_linear_iterations"] is not None:
        normalized["solver"]["max_linear_iterations"] = int(normalized["solver"]["max_linear_iterations"])
    return normalized


def write_public_steady_channel_case(
    path: str | Path,
    *,
    mesh_file: str | Path,
    case_name: str = "public_steady_channel_case",
    inlet_velocity: tuple[float, float] = (1.0, 0.0),
    density: float = 1.0,
    viscosity: float = 1.0e-2,
    iterations: int = 8,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    mesh_path = Path(mesh_file)
    mesh_text = str(mesh_path if mesh_path.is_absolute() else mesh_path.resolve())
    payload = {
        "schema_version": UNSTRUCTURED_CASE_SCHEMA_VERSION,
        "case_name": case_name,
        "mesh_file": mesh_text,
        "required_patches": ["inlet", "outlet", "wall"],
        "physics": {
            "model": "steady_incompressible",
            "density": density,
            "viscosity": viscosity,
            "body_force": [0.0, 0.0],
        },
        "boundary_conditions": {
            "inlet": {"kind": "velocity_inlet", "velocity": [inlet_velocity[0], inlet_velocity[1]], "role": "uniform inlet velocity"},
            "outlet": {"kind": "pressure_outlet", "pressure": 0.0, "role": "pressure outlet reference"},
            "wall": {"kind": "no_slip_wall", "role": "no-slip channel walls"},
        },
        "solver": {
            "family": "steady_incompressible",
            "iterations": iterations,
            "pressure_relaxation": 0.45,
            "linear_solver": "sparse_cg",
            "linear_tolerance": 1.0e-12,
            "max_linear_iterations": None,
        },
    }
    output.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return output


def _conditions_from_normalized_case(case: dict[str, Any]) -> dict[str, BoundaryCondition]:
    return boundary_conditions_from_dict(case["boundary_conditions"])


def _is_numeric_vector(value: Any, *, length: int) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == length and all(isinstance(item, (int, float)) for item in value)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path
