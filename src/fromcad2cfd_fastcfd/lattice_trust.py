"""Recipe-to-lattice domain summary and trust scoring."""

from __future__ import annotations

import math
from typing import Any

from .schemas import FastCFDJob


LATTICE_DOMAIN_SCHEMA_VERSION = "fromcad2cfd_lattice_domain_summary_v1"


def analyze_lattice_domain(job: FastCFDJob) -> dict[str, Any]:
    """Build a conservative lattice-domain summary from a bounded FastCFD recipe."""

    errors: list[str] = []
    warnings: list[str] = []
    nx = _positive_int(job.dimensions.get("nx"), "dimensions.nx", errors)
    ny = _positive_int(job.dimensions.get("ny"), "dimensions.ny", errors)
    cell = _positive_float(job.dimensions.get("cell_length_mm"), "dimensions.cell_length_mm", errors)
    domain = _domain(job, nx, ny, cell)
    zone_counts = _zone_counts(job, nx, ny, cell)
    resolution = _resolution(job, nx, ny, cell, domain)
    _collect_grid_warnings(nx, ny, zone_counts, warnings, errors)
    _collect_obstacle_warnings(resolution, warnings, errors)

    score = _trust_score(warnings, errors, resolution, zone_counts)
    status = "failed" if errors else ("warning" if warnings else "passed")
    return {
        "schema_version": LATTICE_DOMAIN_SCHEMA_VERSION,
        "status": status,
        "case_type": job.case_type,
        "grid": {
            "nx": nx,
            "ny": ny,
            "cell_length_mm": cell,
            "total_cells": zone_counts["total_cells"],
            "length_cells": nx,
            "height_cells": ny,
        },
        "domain": domain,
        "zone_counts": zone_counts,
        "resolution": resolution,
        "trust_score": score,
        "warnings": warnings,
        "errors": errors,
        "limitations": [
            "This summary is derived from the bounded FastCFD recipe, not from an imported Fluent mesh.",
            "Zone counts and obstacle cells are conservative estimates for agent decision support.",
            "Use the final Fluent mesh-quality report before production CFD decisions.",
        ],
    }


def lattice_domain_qoi_updates(summary: dict[str, Any]) -> dict[str, Any]:
    """Return compact QoI fields derived from the lattice-domain summary."""

    grid = summary.get("grid") if isinstance(summary.get("grid"), dict) else {}
    counts = summary.get("zone_counts") if isinstance(summary.get("zone_counts"), dict) else {}
    resolution = summary.get("resolution") if isinstance(summary.get("resolution"), dict) else {}
    obstacle_resolution = resolution.get("obstacle_resolution") if isinstance(resolution.get("obstacle_resolution"), dict) else {}
    obstacle_clearance = resolution.get("obstacle_clearance") if isinstance(resolution.get("obstacle_clearance"), dict) else {}
    return {
        "lattice_domain_status": summary.get("status", "unknown"),
        "lattice_trust_score": summary.get("trust_score"),
        "lattice_total_cells": grid.get("total_cells"),
        "lattice_fluid_cells": counts.get("fluid_cells"),
        "lattice_wall_cells": counts.get("wall_cells"),
        "lattice_obstacle_solid_cells": counts.get("obstacle_solid_cells"),
        "lattice_min_obstacle_resolution_cells": obstacle_resolution.get("min_size_cells"),
        "lattice_min_obstacle_clearance_cells": obstacle_clearance.get("min_clearance_cells"),
    }


def _domain(job: FastCFDJob, nx: int, ny: int, cell: float) -> dict[str, Any]:
    metadata_domain = job.metadata.get("domain") if isinstance(job.metadata.get("domain"), dict) else {}
    length = _first_float(metadata_domain, ("length_mm", "width_mm")) or nx * cell
    height = _first_float(metadata_domain, ("height_mm",)) or ny * cell
    return {
        "type": metadata_domain.get("type") or job.case_type,
        "length_mm": length,
        "height_mm": height,
        "source": "job.metadata.domain" if metadata_domain else "dimensions_from_grid",
    }


def _zone_counts(job: FastCFDJob, nx: int, ny: int, cell: float) -> dict[str, int]:
    total = nx * ny
    interior = max(nx - 2, 0) * max(ny - 2, 0)
    counts: dict[str, int] = {
        "total_cells": total,
        "fluid_cells": interior,
        "wall_cells": 0,
        "inlet_cells": 0,
        "outlet_cells": 0,
        "moving_wall_cells": 0,
        "obstacle_solid_cells": 0,
        "obstacle_wall_cells": 0,
    }
    if job.case_type == "cavity2d":
        counts["moving_wall_cells"] = nx
        counts["wall_cells"] = max(nx - 2, 0) + 2 * max(ny - 1, 0)
    elif job.case_type in {"channel2d", "obstacle2d"}:
        counts["wall_cells"] = 2 * nx
        counts["inlet_cells"] = max(ny - 2, 0)
        counts["outlet_cells"] = max(ny - 2, 0)
        if job.case_type == "obstacle2d":
            solid, wall = _estimated_obstacle_counts(job, cell, interior)
            counts["obstacle_solid_cells"] = solid
            counts["obstacle_wall_cells"] = wall
            counts["fluid_cells"] = max(interior - solid, 0)
    return counts


def _estimated_obstacle_counts(job: FastCFDJob, cell: float, max_cells: int) -> tuple[int, int]:
    obstacle = _first_obstacle(job)
    if not obstacle or cell <= 0:
        return 0, 0
    if obstacle.get("type") == "circle":
        radius = _safe_float(obstacle.get("radius_mm")) or 0.0
        area_cells = math.pi * (radius / cell) ** 2
        wall_cells = 2 * math.pi * radius / cell
    else:
        width = _safe_float(obstacle.get("width_mm")) or 0.0
        height = _safe_float(obstacle.get("height_mm")) or 0.0
        area_cells = width * height / (cell * cell)
        wall_cells = 2 * (width + height) / cell
    return max(0, min(max_cells, int(round(area_cells)))), max(0, int(round(wall_cells)))


def _resolution(job: FastCFDJob, nx: int, ny: int, cell: float, domain: dict[str, Any]) -> dict[str, Any]:
    length = float(domain.get("length_mm") or nx * cell)
    height = float(domain.get("height_mm") or ny * cell)
    result: dict[str, Any] = {
        "cells_per_length": length / cell if cell > 0 else None,
        "cells_per_height": height / cell if cell > 0 else None,
        "minimum_cross_stream_cells": min(nx, ny),
        "grid_aspect_ratio": max(nx / ny, ny / nx) if nx > 0 and ny > 0 else None,
    }
    if job.case_type == "obstacle2d":
        result["obstacle_resolution"] = _obstacle_resolution(job, cell)
        result["obstacle_clearance"] = _obstacle_clearance(job, cell, length, height)
    return result


def _obstacle_resolution(job: FastCFDJob, cell: float) -> dict[str, Any]:
    obstacle = _first_obstacle(job)
    if not obstacle or cell <= 0:
        return {"status": "missing_obstacle"}
    if obstacle.get("type") == "circle":
        radius = _safe_float(obstacle.get("radius_mm")) or 0.0
        min_size = 2 * radius / cell
        return {"type": "circle", "diameter_cells": min_size, "min_size_cells": min_size}
    width = _safe_float(obstacle.get("width_mm")) or 0.0
    height = _safe_float(obstacle.get("height_mm")) or 0.0
    return {
        "type": obstacle.get("type"),
        "width_cells": width / cell,
        "height_cells": height / cell,
        "min_size_cells": min(width / cell, height / cell),
    }


def _obstacle_clearance(job: FastCFDJob, cell: float, length: float, height: float) -> dict[str, Any]:
    obstacle = _first_obstacle(job)
    if not obstacle or cell <= 0:
        return {"status": "missing_obstacle"}
    center = obstacle.get("center_mm") or [0.0, 0.0]
    cx = float(center[0])
    cy = float(center[1])
    radius_like = _obstacle_radius_like(obstacle)
    clearances = {
        "left_cells": (cx - radius_like) / cell,
        "right_cells": (length - cx - radius_like) / cell,
        "bottom_cells": (cy - radius_like) / cell,
        "top_cells": (height - cy - radius_like) / cell,
    }
    clearances["min_clearance_cells"] = min(clearances.values())
    return clearances


def _collect_grid_warnings(nx: int, ny: int, counts: dict[str, int], warnings: list[str], errors: list[str]) -> None:
    if nx < 5 or ny < 5:
        errors.append("The recipe grid is too small to form a meaningful 2D lattice domain.")
    elif nx < 20 or ny < 10:
        warnings.append("The recipe grid is coarse; use this run only as a workflow and physics-passport check.")
    if counts["fluid_cells"] <= 0:
        errors.append("No positive fluid-cell estimate remains after recipe zoning.")
    if counts["total_cells"] > 2_000_000:
        warnings.append("The recipe grid is large for the current pilot workflow and may need resource planning.")


def _collect_obstacle_warnings(resolution: dict[str, Any], warnings: list[str], errors: list[str]) -> None:
    obstacle_resolution = resolution.get("obstacle_resolution")
    if not isinstance(obstacle_resolution, dict):
        return
    min_size = _safe_float(obstacle_resolution.get("min_size_cells"))
    if min_size is None or min_size <= 0:
        errors.append("The obstacle is missing or has no positive lattice resolution.")
    elif min_size < 3:
        errors.append("The obstacle has fewer than 3 cells across its smallest resolved size.")
    elif min_size < 6:
        warnings.append("The obstacle has fewer than 6 cells across its smallest resolved size.")
    clearance = resolution.get("obstacle_clearance")
    if isinstance(clearance, dict):
        min_clearance = _safe_float(clearance.get("min_clearance_cells"))
        if min_clearance is None:
            errors.append("Obstacle clearance could not be estimated.")
        elif min_clearance <= 1:
            errors.append("The obstacle is too close to a domain boundary for the bounded pilot lattice.")
        elif min_clearance < 3:
            warnings.append("The obstacle has less than 3 cells of clearance to at least one domain boundary.")


def _trust_score(warnings: list[str], errors: list[str], resolution: dict[str, Any], counts: dict[str, int]) -> float:
    if errors:
        base = 0.35
    else:
        base = 1.0
    base -= 0.08 * len(warnings)
    if counts.get("fluid_cells", 0) < 500:
        base -= 0.08
    obstacle = resolution.get("obstacle_resolution")
    if isinstance(obstacle, dict):
        min_size = _safe_float(obstacle.get("min_size_cells"))
        if min_size is not None and min_size < 10:
            base -= max(0.0, (10.0 - min_size) * 0.02)
    return round(max(0.0, min(1.0, base)), 3)


def _first_obstacle(job: FastCFDJob) -> dict[str, Any] | None:
    obstacles = job.dimensions.get("obstacles") or []
    return dict(obstacles[0]) if obstacles else None


def _obstacle_radius_like(obstacle: dict[str, Any]) -> float:
    if obstacle.get("type") == "circle":
        return float(obstacle.get("radius_mm", 0.0))
    return 0.5 * max(float(obstacle.get("width_mm", 0.0)), float(obstacle.get("height_mm", 0.0)))


def _positive_int(value: Any, name: str, errors: list[str]) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        errors.append(f"{name} must be a positive integer.")
        return 0
    if parsed <= 0:
        errors.append(f"{name} must be positive.")
        return 0
    return parsed


def _positive_float(value: Any, name: str, errors: list[str]) -> float:
    parsed = _safe_float(value)
    if parsed is None or parsed <= 0:
        errors.append(f"{name} must be positive.")
        return 0.0
    return parsed


def _first_float(mapping: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = _safe_float(mapping.get(key))
        if value is not None:
            return value
    return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
