"""Field-derived QoI extraction from FastFluent VTK XML outputs."""

from __future__ import annotations

from array import array
import base64
from dataclasses import dataclass
from pathlib import Path
import re
import statistics
import struct
import xml.etree.ElementTree as ET
from typing import Any

from .schemas import FastCFDJob


@dataclass(frozen=True)
class VTIArray:
    """Decoded VTK ImageData point-data array."""

    name: str
    data_type: str
    components: int
    values: array


@dataclass(frozen=True)
class VTIGrid:
    """Minimal VTK ImageData grid needed for FastCFD field analysis."""

    path: Path
    extent: tuple[int, int, int, int, int, int]
    origin: tuple[float, float, float]
    spacing: tuple[float, float, float]
    arrays: dict[str, VTIArray]

    @property
    def nx(self) -> int:
        return self.extent[1] - self.extent[0] + 1

    @property
    def ny(self) -> int:
        return self.extent[3] - self.extent[2] + 1

    @property
    def nz(self) -> int:
        return self.extent[5] - self.extent[4] + 1

    @property
    def point_count(self) -> int:
        return self.nx * self.ny * self.nz

    def point_index(self, ix: int, iy: int, iz: int = 0) -> int:
        return ix + self.nx * (iy + self.ny * iz)

    def coordinate(self, ix: int, iy: int, iz: int = 0) -> tuple[float, float, float]:
        return (
            self.origin[0] + ix * self.spacing[0],
            self.origin[1] + iy * self.spacing[1],
            self.origin[2] + iz * self.spacing[2],
        )


VTK_ARRAY_TYPECODES = {
    "Float64": "d",
    "Float32": "f",
    "UInt8": "B",
    "Int8": "b",
    "UInt16": "H",
    "Int16": "h",
    "UInt32": "I",
    "Int32": "i",
}


def read_vti_image_data(path: str | Path) -> VTIGrid:
    """Decode a VTK XML ImageData file with PointData arrays."""

    file_path = Path(path)
    root = ET.parse(file_path).getroot()
    image = root.find("ImageData")
    if image is None:
        raise ValueError(f"VTI file has no ImageData element: {file_path}")
    piece = image.find("Piece")
    if piece is None:
        raise ValueError(f"VTI file has no Piece element: {file_path}")
    extent = _parse_int_tuple(piece.get("Extent") or image.get("WholeExtent") or "", 6)
    origin = _parse_float_tuple(image.get("Origin") or "0 0 0", 3)
    spacing = _parse_float_tuple(image.get("Spacing") or "1 1 1", 3)
    byte_order = root.get("byte_order", "LittleEndian")
    point_data = piece.find("PointData")
    arrays: dict[str, VTIArray] = {}
    if point_data is not None:
        for element in point_data.findall("DataArray"):
            decoded = _decode_data_array(element, byte_order=byte_order)
            arrays[decoded.name] = decoded
    grid = VTIGrid(path=file_path, extent=extent, origin=origin, spacing=spacing, arrays=arrays)
    for item in arrays.values():
        expected = grid.point_count * item.components
        if len(item.values) != expected:
            raise ValueError(f"DataArray {item.name} has {len(item.values)} values; expected {expected}.")
    return grid


def analyze_fastfluent_fields(output_dir: str | Path, job: FastCFDJob) -> dict[str, Any]:
    """Extract conservative field-derived QoI from FastFluent VTK XML files."""

    output = Path(output_dir)
    warnings: list[str] = []
    selected = _latest_field_vti(output)
    if selected is None:
        return {
            "status": "not_available",
            "warnings": ["No final FastFluent field VTI file was found."],
            "metrics": {},
            "fluent_hint_inputs": {},
        }
    try:
        field_grid = read_vti_image_data(selected)
    except Exception as exc:
        return {
            "status": "failed",
            "selected_field_file": str(selected),
            "warnings": [f"Failed to parse field VTI: {exc}"],
            "metrics": {},
            "fluent_hint_inputs": {},
        }

    flag_grid = None
    flag_file = _latest_flag_vti(output)
    if flag_file:
        try:
            flag_grid = read_vti_image_data(flag_file)
        except Exception as exc:
            warnings.append(f"Failed to parse GeoFlag VTI; flag-aware masks disabled: {exc}")

    velocity = _find_array(field_grid, ("Velocity", "physVelocity", "Velo"))
    rho = _find_array(field_grid, ("Rho", "physRho", "rho"))
    if velocity is None or velocity.components < 2:
        return {
            "status": "failed",
            "selected_field_file": str(selected),
            "warnings": warnings + ["No 2-component velocity array was found."],
            "metrics": {},
            "fluent_hint_inputs": {},
        }

    selected_step = _step_from_name(selected.name)
    flag_counts = _flag_counts(flag_grid)
    fluid_indices = _fluid_indices(field_grid, flag_grid)
    speed_values = [_speed_at(velocity, index) for index in fluid_indices]
    speed_summary = _summary(speed_values)
    centerline = _centerline_samples(field_grid, velocity, flag_grid)
    inlet = _column_velocity_stats(field_grid, velocity, flag_grid, ix=1)
    outlet = _column_velocity_stats(field_grid, velocity, flag_grid, ix=max(1, field_grid.nx - 2))
    rho_summary = _summary([float(rho.values[index * rho.components]) for index in fluid_indices]) if rho else {}
    wake = _wake_bbox_proxy(field_grid, velocity, flag_grid, job, inlet)
    refinement = _refinement_hints(field_grid, velocity, flag_grid, job, inlet)

    metrics = {
        "selected_step": selected_step,
        "selected_field_file": str(selected),
        "flag_file": str(flag_file) if flag_file else None,
        "grid": {
            "point_count": field_grid.point_count,
            "nx_points": field_grid.nx,
            "ny_points": field_grid.ny,
            "origin": list(field_grid.origin),
            "spacing": list(field_grid.spacing),
        },
        "arrays": sorted(field_grid.arrays),
        "flag_counts": flag_counts,
        "speed_summary": speed_summary,
        "rho_summary": rho_summary,
        "centerline_velocity_samples": centerline,
        "inlet_velocity_profile": inlet,
        "outlet_velocity_spread": outlet,
        "wake_bbox_proxy": wake,
        "refinement_hints": refinement,
    }
    return {
        "status": "parsed",
        "selected_step": selected_step,
        "selected_field_file": str(selected),
        "warnings": warnings,
        "metrics": metrics,
        "fluent_hint_inputs": _fluent_hint_inputs(metrics),
    }


def _decode_data_array(element: ET.Element, *, byte_order: str) -> VTIArray:
    name = element.get("Name") or "unnamed"
    data_type = element.get("type") or "Float64"
    components = int(element.get("NumberOfComponents") or "1")
    fmt = element.get("format")
    encoding = element.get("encoding")
    if fmt != "binary" or encoding != "base64":
        raise ValueError(f"Only binary/base64 DataArray is supported; got format={fmt}, encoding={encoding}.")
    typecode = VTK_ARRAY_TYPECODES.get(data_type)
    if not typecode:
        raise ValueError(f"Unsupported VTK DataArray type: {data_type}.")
    raw_text = "".join((element.text or "").split())
    blob = _decode_vtk_base64_binary(raw_text)
    endian = "<" if byte_order != "BigEndian" else ">"
    payload = blob
    if len(blob) >= 4:
        byte_count = struct.unpack(endian + "I", blob[:4])[0]
        if byte_count == len(blob) - 4:
            payload = blob[4:]
    values = array(typecode)
    values.frombytes(payload)
    if (byte_order == "BigEndian" and _is_little_endian()) or (byte_order != "BigEndian" and not _is_little_endian()):
        values.byteswap()
    return VTIArray(name=name, data_type=data_type, components=components, values=values)


def _decode_vtk_base64_binary(raw_text: str) -> bytes:
    """Decode VTK XML binary text, including split header/payload base64 blocks."""

    if not raw_text:
        return b""
    direct = base64.b64decode(raw_text)
    if len(direct) >= 4:
        header_size = struct.unpack("<I", direct[:4])[0]
        if header_size == len(direct) - 4:
            return direct
    # Some FastFluent/VTK writers emit the 4-byte byte-count header as one
    # padded base64 block, immediately followed by a second block for payload.
    if raw_text[6:8] == "==" and len(raw_text) > 8:
        return base64.b64decode(raw_text[:8]) + base64.b64decode(raw_text[8:])
    return direct


def _is_little_endian() -> bool:
    return struct.pack("=I", 1)[0] == 1


def _parse_int_tuple(text: str, count: int) -> tuple[int, ...]:
    values = tuple(int(item) for item in text.split())
    if len(values) != count:
        raise ValueError(f"Expected {count} integer values, got {text!r}.")
    return values


def _parse_float_tuple(text: str, count: int) -> tuple[float, ...]:
    values = tuple(float(item) for item in text.split())
    if len(values) != count:
        raise ValueError(f"Expected {count} float values, got {text!r}.")
    return values


def _latest_field_vti(output_dir: Path) -> Path | None:
    files = sorted((output_dir / "vtkoutput").rglob("*.vti"))
    candidates = [file for file in files if "_T" in file.name and "GeoFlag" not in file.name]
    if not candidates:
        return None
    return max(candidates, key=lambda file: (_step_from_name(file.name), file.name))


def _latest_flag_vti(output_dir: Path) -> Path | None:
    files = sorted((output_dir / "vtkoutput").rglob("GeoFlag*_B*.vti"))
    return files[-1] if files else None


def _step_from_name(name: str) -> int:
    match = re.search(r"_T(\d+)_", name)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\.vt", name)
    return int(match.group(1)) if match else 0


def _find_array(grid: VTIGrid, names: tuple[str, ...]) -> VTIArray | None:
    lowered = {name.lower(): name for name in grid.arrays}
    for candidate in names:
        actual = lowered.get(candidate.lower())
        if actual:
            return grid.arrays[actual]
    return None


def _flag_counts(flag_grid: VTIGrid | None) -> dict[str, int]:
    if not flag_grid:
        return {}
    flag = _find_array(flag_grid, ("flag",))
    if not flag:
        return {}
    counts: dict[str, int] = {}
    for value in flag.values:
        key = str(int(value))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _fluid_indices(grid: VTIGrid, flag_grid: VTIGrid | None) -> list[int]:
    indices: list[int] = []
    flag = _find_array(flag_grid, ("flag",)) if flag_grid and flag_grid.point_count == grid.point_count else None
    for iy in range(1, max(1, grid.ny - 1)):
        for ix in range(1, max(1, grid.nx - 1)):
            index = grid.point_index(ix, iy)
            if flag is not None and int(flag.values[index]) in {1, 4}:
                continue
            indices.append(index)
    return indices


def _speed_at(velocity: VTIArray, index: int) -> float:
    offset = index * velocity.components
    u = float(velocity.values[offset])
    v = float(velocity.values[offset + 1])
    return (u * u + v * v) ** 0.5


def _vector_at(velocity: VTIArray, index: int) -> tuple[float, float]:
    offset = index * velocity.components
    return float(velocity.values[offset]), float(velocity.values[offset + 1])


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "std": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
    }


def _centerline_samples(grid: VTIGrid, velocity: VTIArray, flag_grid: VTIGrid | None) -> list[dict[str, float]]:
    iy = max(1, min(grid.ny - 2, grid.ny // 2))
    sample_count = min(9, max(1, grid.nx - 2))
    x_indices = _sample_indices(1, max(1, grid.nx - 2), sample_count)
    samples: list[dict[str, float]] = []
    for ix in x_indices:
        index = grid.point_index(ix, iy)
        u, v = _vector_at(velocity, index)
        x, y, _ = grid.coordinate(ix, iy)
        samples.append({"x": x, "y": y, "u": u, "v": v, "speed": (u * u + v * v) ** 0.5})
    return samples


def _sample_indices(start: int, stop: int, count: int) -> list[int]:
    if count <= 1 or start >= stop:
        return [start]
    return sorted({round(start + (stop - start) * i / (count - 1)) for i in range(count)})


def _column_velocity_stats(grid: VTIGrid, velocity: VTIArray, flag_grid: VTIGrid | None, *, ix: int) -> dict[str, Any]:
    flag = _find_array(flag_grid, ("flag",)) if flag_grid and flag_grid.point_count == grid.point_count else None
    u_values: list[float] = []
    speed_values: list[float] = []
    for iy in range(1, max(1, grid.ny - 1)):
        index = grid.point_index(ix, iy)
        if flag is not None and int(flag.values[index]) in {1, 4}:
            continue
        u, v = _vector_at(velocity, index)
        u_values.append(u)
        speed_values.append((u * u + v * v) ** 0.5)
    u_summary = _summary(u_values)
    speed_summary = _summary(speed_values)
    mean_abs_u = statistics.fmean([abs(value) for value in u_values]) if u_values else None
    spread_ratio = None
    if mean_abs_u and mean_abs_u > 0 and u_summary["std"] is not None:
        spread_ratio = float(u_summary["std"]) / mean_abs_u
    x, _, _ = grid.coordinate(ix, 0)
    return {
        "x": x,
        "sample_count": len(u_values),
        "u": u_summary,
        "speed": speed_summary,
        "spread_ratio": spread_ratio,
        "reverse_flow_fraction": sum(1 for value in u_values if value < 0) / len(u_values) if u_values else None,
    }


def _wake_bbox_proxy(grid: VTIGrid, velocity: VTIArray, flag_grid: VTIGrid | None, job: FastCFDJob, inlet: dict[str, Any]) -> dict[str, Any]:
    if job.case_type != "obstacle2d":
        return {"status": "not_applicable"}
    obstacle = _first_obstacle(job)
    if not obstacle:
        return {"status": "missing_obstacle"}
    center = obstacle.get("center_mm") or [0.0, 0.0]
    radius_like = _obstacle_radius_like(obstacle)
    upstream_speed = _safe_float((inlet.get("speed") or {}).get("mean"))
    if upstream_speed is None or upstream_speed <= 0:
        upstream_speed = _safe_float((inlet.get("u") or {}).get("mean")) or 0.0
    if upstream_speed <= 0:
        return {"status": "insufficient_upstream_velocity"}
    threshold = 0.7 * upstream_speed
    flag = _find_array(flag_grid, ("flag",)) if flag_grid and flag_grid.point_count == grid.point_count else None
    points: list[tuple[float, float, float]] = []
    downstream_start = float(center[0]) + radius_like
    y_min = float(center[1]) - 2.5 * radius_like
    y_max = float(center[1]) + 2.5 * radius_like
    for iy in range(1, max(1, grid.ny - 1)):
        for ix in range(1, max(1, grid.nx - 1)):
            index = grid.point_index(ix, iy)
            if flag is not None and int(flag.values[index]) in {1, 4}:
                continue
            x, y, _ = grid.coordinate(ix, iy)
            if x <= downstream_start or y < y_min or y > y_max:
                continue
            speed = _speed_at(velocity, index)
            if speed <= threshold:
                points.append((x, y, speed))
    if not points:
        return {"status": "not_detected", "threshold": threshold, "upstream_mean_speed": upstream_speed}
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    speeds = [point[2] for point in points]
    return {
        "status": "detected",
        "threshold": threshold,
        "upstream_mean_speed": upstream_speed,
        "point_count": len(points),
        "bbox_mm": {"x_min": min(xs), "x_max": max(xs), "y_min": min(ys), "y_max": max(ys)},
        "length_mm": max(xs) - min(xs),
        "min_speed": min(speeds),
        "mean_speed": statistics.fmean(speeds),
    }


def _refinement_hints(grid: VTIGrid, velocity: VTIArray, flag_grid: VTIGrid | None, job: FastCFDJob, inlet: dict[str, Any]) -> dict[str, Any]:
    near_wall = _near_wall_shear_proxy(grid, velocity)
    result: dict[str, Any] = {"near_wall_shear_proxy": near_wall}
    if job.case_type == "obstacle2d":
        result["obstacle_near_field_gradient_proxy"] = _obstacle_gradient_proxy(grid, velocity, job)
    ratios = []
    if near_wall.get("max_abs_du_dy") is not None:
        ratios.append(float(near_wall["max_abs_du_dy"]))
    obstacle_proxy = result.get("obstacle_near_field_gradient_proxy")
    if isinstance(obstacle_proxy, dict) and obstacle_proxy.get("max_speed_gradient") is not None:
        ratios.append(float(obstacle_proxy["max_speed_gradient"]))
    result["suggested_fluent_focus"] = _suggested_fluent_focus(job, ratios)
    return result


def _near_wall_shear_proxy(grid: VTIGrid, velocity: VTIArray) -> dict[str, Any]:
    if grid.ny < 4:
        return {"status": "insufficient_grid"}
    values: list[float] = []
    for ix in range(1, max(1, grid.nx - 1)):
        lower_u, _ = _vector_at(velocity, grid.point_index(ix, 1))
        lower_next_u, _ = _vector_at(velocity, grid.point_index(ix, 2))
        upper_u, _ = _vector_at(velocity, grid.point_index(ix, grid.ny - 2))
        upper_next_u, _ = _vector_at(velocity, grid.point_index(ix, grid.ny - 3))
        dy = abs(grid.spacing[1]) or 1.0
        values.append(abs((lower_next_u - lower_u) / dy))
        values.append(abs((upper_next_u - upper_u) / dy))
    summary = _summary(values)
    return {"status": "computed", "max_abs_du_dy": summary["max"], "mean_abs_du_dy": summary["mean"]}


def _obstacle_gradient_proxy(grid: VTIGrid, velocity: VTIArray, job: FastCFDJob) -> dict[str, Any]:
    obstacle = _first_obstacle(job)
    if not obstacle:
        return {"status": "missing_obstacle"}
    center = obstacle.get("center_mm") or [0.0, 0.0]
    radius_like = _obstacle_radius_like(obstacle)
    gradients: list[float] = []
    for iy in range(2, max(2, grid.ny - 2)):
        for ix in range(2, max(2, grid.nx - 2)):
            x, y, _ = grid.coordinate(ix, iy)
            distance = ((x - float(center[0])) ** 2 + (y - float(center[1])) ** 2) ** 0.5
            if distance < radius_like or distance > radius_like + 4 * max(abs(grid.spacing[0]), abs(grid.spacing[1]), 1.0):
                continue
            left = _speed_at(velocity, grid.point_index(ix - 1, iy))
            right = _speed_at(velocity, grid.point_index(ix + 1, iy))
            bottom = _speed_at(velocity, grid.point_index(ix, iy - 1))
            top = _speed_at(velocity, grid.point_index(ix, iy + 1))
            dx = abs(grid.spacing[0]) or 1.0
            dy = abs(grid.spacing[1]) or 1.0
            gradients.append((((right - left) / (2 * dx)) ** 2 + ((top - bottom) / (2 * dy)) ** 2) ** 0.5)
    summary = _summary(gradients)
    return {"status": "computed" if gradients else "not_detected", "max_speed_gradient": summary["max"], "mean_speed_gradient": summary["mean"]}


def _suggested_fluent_focus(job: FastCFDJob, gradients: list[float]) -> list[str]:
    suggestions = ["Keep inlet, outlet, walls, and solid-body named selections explicit in Fluent."]
    if job.case_type in {"channel2d", "obstacle2d"}:
        suggestions.append("Review outlet placement if outlet velocity spread or reverse-flow fraction is high.")
    if job.case_type == "obstacle2d":
        suggestions.append("Use local sizing and boundary-layer controls around the obstacle and downstream wake region.")
    if gradients and max(gradients) > 0:
        suggestions.append("Use parsed field gradients only as relative refinement evidence, not final mesh-quality proof.")
    return suggestions


def _first_obstacle(job: FastCFDJob) -> dict[str, Any] | None:
    obstacles = job.dimensions.get("obstacles") or []
    return dict(obstacles[0]) if obstacles else None


def _obstacle_radius_like(obstacle: dict[str, Any]) -> float:
    if obstacle.get("type") == "circle":
        return float(obstacle.get("radius_mm", 0.0))
    return 0.5 * max(float(obstacle.get("width_mm", 0.0)), float(obstacle.get("height_mm", 0.0)))


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fluent_hint_inputs(metrics: dict[str, Any]) -> dict[str, Any]:
    outlet = metrics.get("outlet_velocity_spread") or {}
    wake = metrics.get("wake_bbox_proxy") or {}
    return {
        "outlet_spread_ratio": outlet.get("spread_ratio"),
        "outlet_reverse_flow_fraction": outlet.get("reverse_flow_fraction"),
        "wake_status": wake.get("status"),
        "wake_bbox_mm": wake.get("bbox_mm"),
        "refinement_focus": (metrics.get("refinement_hints") or {}).get("suggested_fluent_focus", []),
    }
