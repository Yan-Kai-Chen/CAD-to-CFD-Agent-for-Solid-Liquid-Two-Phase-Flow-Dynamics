"""Semantic FastCFD scene validation and job compilation."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .paths import project_input_dir, project_output_dir, unique_path
from .physics_validator import validate_physics
from .registry import require_boundary_type, require_case_template
from .schemas import FastCFDJob, FastCFDScene


DEFAULT_PHYSICS = {
    "rho_ref_g_per_mm3": 0.001,
    "kinematic_viscosity_mm2_s": 0.02,
    "reference_velocity_mm_s": 0.03,
    "relaxation_time": 0.56,
    "total_steps": 200,
    "output_interval": 50,
    "thread_num": 1,
}


def default_scene(
    *,
    scene_type: str,
    model_name: str,
    length_mm: float = 120.0,
    height_mm: float = 40.0,
    cell_length_mm: float = 1.0,
    obstacle: str | None = None,
) -> FastCFDScene:
    """Create a public-safe default semantic scene."""

    if scene_type == "cavity2d":
        geometry = {
            "domain": {"type": "rectangle", "width_mm": 30.0, "height_mm": 30.0},
            "cell_length_mm": cell_length_mm,
        }
        zones = [
            {"name": "fluid", "semantic_type": "fluid"},
            {"name": "top", "semantic_type": "moving_wall", "velocity_mm_s": DEFAULT_PHYSICS["reference_velocity_mm_s"]},
            {"name": "stationary_walls", "semantic_type": "no_slip_wall", "members": ["left", "right", "bottom"]},
        ]
    elif scene_type == "channel2d":
        geometry = {
            "domain": {"type": "channel2d", "length_mm": length_mm, "height_mm": height_mm},
            "cell_length_mm": cell_length_mm,
        }
        zones = [
            {"name": "fluid", "semantic_type": "fluid"},
            {"name": "inlet", "semantic_type": "inlet", "velocity_mm_s": DEFAULT_PHYSICS["reference_velocity_mm_s"]},
            {"name": "outlet", "semantic_type": "outlet"},
            {"name": "walls", "semantic_type": "no_slip_wall", "members": ["top", "bottom"]},
        ]
    elif scene_type == "obstacle2d":
        obstacle_shape = _default_obstacle(obstacle or "circle", length_mm, height_mm)
        geometry = {
            "domain": {"type": "channel2d", "length_mm": length_mm, "height_mm": height_mm},
            "cell_length_mm": cell_length_mm,
            "obstacles": [obstacle_shape],
        }
        zones = [
            {"name": "fluid", "semantic_type": "fluid"},
            {"name": "inlet", "semantic_type": "inlet", "velocity_mm_s": DEFAULT_PHYSICS["reference_velocity_mm_s"]},
            {"name": "outlet", "semantic_type": "outlet"},
            {"name": "walls", "semantic_type": "no_slip_wall", "members": ["top", "bottom"]},
            {"name": "obstacle", "semantic_type": "obstacle_wall", "obstacle_names": [obstacle_shape["name"]]},
        ]
    elif scene_type == "dambreak2d":
        geometry = {
            "domain": {"type": "tank2d", "length_mm": length_mm, "height_mm": height_mm},
            "cell_length_mm": cell_length_mm,
            "initial_fluid_region": {"type": "rectangle", "x_min_mm": 0.0, "x_max_mm": length_mm * 0.4, "y_min_mm": 0.0, "y_max_mm": height_mm * 0.8},
        }
        zones = [
            {"name": "fluid", "semantic_type": "fluid"},
            {"name": "walls", "semantic_type": "no_slip_wall", "members": ["left", "right", "bottom"]},
            {"name": "free_surface", "semantic_type": "free_surface"},
        ]
    else:
        raise ValueError(f"Unsupported default FastCFD scene_type: {scene_type}")

    return FastCFDScene(
        scene_type=scene_type,
        units={"length": "mm", "time": "s", "density": "g/mm^3", "kinematic_viscosity": "mm^2/s"},
        geometry=geometry,
        zones=zones,
        physics_intent={
            "model": "single_phase_incompressible_lbm" if scene_type != "dambreak2d" else "free_surface_lbm_candidate",
            "rho_ref_g_per_mm3": DEFAULT_PHYSICS["rho_ref_g_per_mm3"],
            "kinematic_viscosity_mm2_s": DEFAULT_PHYSICS["kinematic_viscosity_mm2_s"],
            "reference_velocity_mm_s": DEFAULT_PHYSICS["reference_velocity_mm_s"],
            "relaxation_time": DEFAULT_PHYSICS["relaxation_time"],
            "qoi_targets": ["physics_passport", "fluent_hints"],
        },
        metadata={"model_name": model_name, "created_by": "fromcad2cfd_fastcfd.default_scene"},
    )


def write_scene(
    *,
    project: str,
    model_name: str,
    scene_type: str,
    length_mm: float = 120.0,
    height_mm: float = 40.0,
    cell_length_mm: float = 1.0,
    obstacle: str | None = None,
) -> dict[str, Any]:
    """Write a default semantic scene into the project input directory."""

    scene = default_scene(
        scene_type=scene_type,
        model_name=model_name,
        length_mm=length_mm,
        height_mm=height_mm,
        cell_length_mm=cell_length_mm,
        obstacle=obstacle,
    )
    report = validate_scene_semantics(scene)
    if report["status"] == "failed":
        raise ValueError("; ".join(report["errors"]))
    scene_path = unique_path(project_input_dir(project) / f"{model_name}_scene.json")
    scene_path.write_text(json.dumps(scene.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
    return {"status": "success", "scene_path": str(scene_path), "scene": scene.to_dict(), "validation": report}


def read_scene(path: str | Path) -> FastCFDScene:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    scene = FastCFDScene(
        scene_type=payload["scene_type"],
        units=payload.get("units") or {},
        geometry=payload.get("geometry") or {},
        zones=payload.get("zones") or [],
        physics_intent=payload.get("physics_intent") or {},
        schema_version=payload.get("schema_version", ""),
        metadata=payload.get("metadata") or {},
    )
    scene.validate()
    return scene


def validate_scene_semantics(scene: FastCFDScene) -> dict[str, Any]:
    """Validate semantic scene content without compiling or running a solver."""

    scene.validate()
    case = require_case_template(scene.scene_type)
    errors: list[str] = []
    warnings: list[str] = []

    domain = _domain(scene)
    cell_length = _cell_length(scene)
    if cell_length <= 0:
        errors.append("Scene cell_length_mm must be positive.")
    width, height = _domain_size(scene)
    if width <= 0 or height <= 0:
        errors.append("Scene domain dimensions must be positive.")
    zone_types = _zone_types(scene)
    for required in case.required_zones:
        if required not in zone_types and required not in {zone.get("name") for zone in scene.zones}:
            errors.append(f"Scene for {scene.scene_type} is missing required zone: {required}.")
    for zone_type in zone_types:
        if zone_type == "fluid":
            continue
        require_boundary_type(zone_type)
    if scene.scene_type in {"channel2d", "obstacle2d"} and {"inlet", "outlet"} - zone_types:
        errors.append(f"{scene.scene_type} requires inlet and outlet semantic zones.")
    if scene.scene_type == "obstacle2d":
        errors.extend(_obstacle_errors(scene, width, height))
        warnings.extend(_obstacle_warnings(scene, cell_length))
    if scene.scene_type == "dambreak2d" and "initial_fluid_region" not in scene.geometry:
        errors.append("dambreak2d requires initial_fluid_region.")

    return {
        "status": "failed" if errors else ("warning" if warnings else "passed"),
        "scene_type": scene.scene_type,
        "domain": domain,
        "zone_types": sorted(zone_types),
        "errors": errors,
        "warnings": warnings,
    }


def compile_scene_to_job(
    scene: FastCFDScene,
    *,
    project: str,
    model_name: str | None = None,
    backend: str = "mock",
) -> dict[str, Any]:
    """Compile a semantic FastCFD scene into a validated job JSON."""

    report = validate_scene_semantics(scene)
    if report["status"] == "failed":
        raise ValueError("; ".join(report["errors"]))

    case = require_case_template(scene.scene_type)
    if backend not in case.supported_backends:
        raise ValueError(f"Backend '{backend}' is not supported for scene type '{scene.scene_type}'.")

    name = model_name or str(scene.metadata.get("model_name") or scene.scene_type)
    width, height = _domain_size(scene)
    cell_length = _cell_length(scene)
    nx = max(1, int(round(width / cell_length)))
    ny = max(1, int(round(height / cell_length)))
    physics = {**DEFAULT_PHYSICS, **scene.physics_intent}
    reference_velocity = _reference_velocity_from_scene(scene, physics)
    dimensions: dict[str, Any] = {"nx": nx, "ny": ny, "cell_length_mm": cell_length}
    if scene.scene_type == "obstacle2d":
        dimensions["obstacles"] = scene.geometry.get("obstacles", [])
    if scene.scene_type == "dambreak2d":
        dimensions["initial_fluid_region"] = scene.geometry.get("initial_fluid_region")

    boundary_conditions = _boundary_conditions(scene, reference_velocity)
    solver_settings = {
        "total_steps": int(physics.get("total_steps", DEFAULT_PHYSICS["total_steps"])),
        "output_interval": int(physics.get("output_interval", DEFAULT_PHYSICS["output_interval"])),
        "relaxation_time": float(physics.get("relaxation_time", DEFAULT_PHYSICS["relaxation_time"])),
        "thread_num": int(physics.get("thread_num", DEFAULT_PHYSICS["thread_num"])),
    }
    job = FastCFDJob(
        case_type=scene.scene_type,
        backend=backend,
        output_dir=str(project_output_dir(project)),
        model_name=name,
        dimensions=dimensions,
        physical_properties={
            "rho_ref_g_per_mm3": float(physics["rho_ref_g_per_mm3"]),
            "kinematic_viscosity_mm2_s": float(physics["kinematic_viscosity_mm2_s"]),
        },
        boundary_conditions=boundary_conditions,
        solver_settings=solver_settings,
        units={"length": "mm", "time": "s", "density": "g/mm^3", "kinematic_viscosity": "mm^2/s"},
        metadata={
            "compiled_from_scene": True,
            "scene_type": scene.scene_type,
            "scene_validation": report,
            "domain": _domain(scene),
            "zones": scene.zones,
            "case_registry_status": case.status,
        },
    )
    physics_contract = validate_physics(job)
    job_path = unique_path(project_input_dir(project) / f"{name}_job.json")
    job.write(job_path)
    return {
        "status": "success",
        "job_path": str(job_path),
        "job": job.to_dict(),
        "scene_validation": report,
        "physics_contract": physics_contract.to_dict(),
    }


def compile_scene_file_to_job(
    scene_file: str | Path,
    *,
    project: str,
    model_name: str | None = None,
    backend: str = "mock",
) -> dict[str, Any]:
    scene = read_scene(scene_file)
    return compile_scene_to_job(scene, project=project, model_name=model_name, backend=backend)


def _domain(scene: FastCFDScene) -> dict[str, Any]:
    domain = scene.geometry.get("domain")
    if isinstance(domain, dict):
        return domain
    return scene.geometry


def _domain_size(scene: FastCFDScene) -> tuple[float, float]:
    domain = _domain(scene)
    if "width_mm" in domain:
        width = domain["width_mm"]
    elif "length_mm" in domain:
        width = domain["length_mm"]
    elif isinstance(domain.get("size_mm"), list) and domain["size_mm"]:
        width = domain["size_mm"][0]
    else:
        width = 0.0
    if "height_mm" in domain:
        height = domain["height_mm"]
    elif isinstance(domain.get("size_mm"), list) and len(domain["size_mm"]) > 1:
        height = domain["size_mm"][1]
    else:
        height = 0.0
    return float(width), float(height)


def _cell_length(scene: FastCFDScene) -> float:
    return float(scene.geometry.get("cell_length_mm", _domain(scene).get("cell_length_mm", 1.0)))


def _zone_types(scene: FastCFDScene) -> set[str]:
    types: set[str] = set()
    for zone in scene.zones:
        zone_type = zone.get("semantic_type") or zone.get("type") or zone.get("role") or zone.get("name")
        if zone_type:
            types.add(str(zone_type))
    return types


def _reference_velocity_from_scene(scene: FastCFDScene, physics: dict[str, Any]) -> float:
    for zone in scene.zones:
        if "velocity_mm_s" in zone:
            return float(zone["velocity_mm_s"])
    return float(physics.get("reference_velocity_mm_s", DEFAULT_PHYSICS["reference_velocity_mm_s"]))


def _boundary_conditions(scene: FastCFDScene, reference_velocity: float) -> dict[str, Any]:
    if scene.scene_type == "cavity2d":
        return {"moving_wall_velocity_mm_s": reference_velocity, "stationary_walls": ["left", "right", "bottom"]}
    if scene.scene_type in {"channel2d", "obstacle2d"}:
        payload: dict[str, Any] = {"inlet_velocity_mm_s": reference_velocity, "outlet": "pressure_outlet", "walls": ["top", "bottom"]}
        if scene.scene_type == "obstacle2d":
            payload["obstacle_walls"] = [obstacle["name"] for obstacle in scene.geometry.get("obstacles", [])]
        return payload
    if scene.scene_type == "dambreak2d":
        return {"reference_velocity_mm_s": reference_velocity, "walls": ["left", "right", "bottom"], "free_surface": True}
    raise ValueError(f"Unsupported scene type for boundary condition compilation: {scene.scene_type}")


def _default_obstacle(shape: str, length_mm: float, height_mm: float) -> dict[str, Any]:
    if shape == "rectangle":
        return {
            "name": "rect_obstacle_01",
            "type": "rectangle",
            "center_mm": [length_mm * 0.35, height_mm * 0.5],
            "width_mm": min(length_mm * 0.08, height_mm * 0.25),
            "height_mm": min(height_mm * 0.25, length_mm * 0.08),
        }
    if shape != "circle":
        raise ValueError("Supported default obstacle shapes are circle and rectangle.")
    return {"name": "circle_obstacle_01", "type": "circle", "center_mm": [length_mm * 0.35, height_mm * 0.5], "radius_mm": min(height_mm * 0.12, length_mm * 0.04)}


def _obstacle_errors(scene: FastCFDScene, width: float, height: float) -> list[str]:
    errors: list[str] = []
    obstacles = scene.geometry.get("obstacles") or []
    if not obstacles:
        return ["obstacle2d requires at least one obstacle."]
    for obstacle in obstacles:
        name = obstacle.get("name", "<unnamed>")
        center = obstacle.get("center_mm")
        if not isinstance(center, list) or len(center) != 2:
            errors.append(f"Obstacle {name} requires center_mm = [x, y].")
            continue
        x, y = float(center[0]), float(center[1])
        if obstacle.get("type") == "circle":
            radius = float(obstacle.get("radius_mm", 0.0))
            if radius <= 0:
                errors.append(f"Obstacle {name} radius_mm must be positive.")
            if x - radius <= 0 or x + radius >= width:
                errors.append(f"Obstacle {name} overlaps or touches inlet/outlet boundaries.")
            if y - radius <= 0 or y + radius >= height:
                errors.append(f"Obstacle {name} overlaps or touches wall boundaries.")
        elif obstacle.get("type") == "rectangle":
            half_w = float(obstacle.get("width_mm", 0.0)) / 2.0
            half_h = float(obstacle.get("height_mm", 0.0)) / 2.0
            if half_w <= 0 or half_h <= 0:
                errors.append(f"Obstacle {name} width_mm and height_mm must be positive.")
            if x - half_w <= 0 or x + half_w >= width:
                errors.append(f"Obstacle {name} overlaps or touches inlet/outlet boundaries.")
            if y - half_h <= 0 or y + half_h >= height:
                errors.append(f"Obstacle {name} overlaps or touches wall boundaries.")
        else:
            errors.append(f"Obstacle {name} has unsupported type: {obstacle.get('type')}.")
    return errors


def _obstacle_warnings(scene: FastCFDScene, cell_length: float) -> list[str]:
    warnings: list[str] = []
    for obstacle in scene.geometry.get("obstacles") or []:
        if obstacle.get("type") == "circle":
            resolution = float(obstacle.get("radius_mm", 0.0)) / cell_length
            if resolution < 3.0:
                warnings.append(f"Obstacle {obstacle.get('name', '<unnamed>')} radius resolves to fewer than 3 cells.")
        elif obstacle.get("type") == "rectangle":
            min_cells = min(float(obstacle.get("width_mm", 0.0)), float(obstacle.get("height_mm", 0.0))) / cell_length
            if min_cells < 3.0:
                warnings.append(f"Obstacle {obstacle.get('name', '<unnamed>')} minimum side resolves to fewer than 3 cells.")
    return warnings
