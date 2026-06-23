"""Safe kinematic motion contracts for FastFluent workflows.

This module describes moving boundaries, obstacles, and bodies as validated
kinematic inputs. It intentionally does not implement dynamic mesh, FSI, or
production CFD motion solving.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


MOTION_CONTRACT_SCHEMA_VERSION = "fastfluent_motion_contract_v1"
MOTION_EVIDENCE_LEVEL = "kinematic_preflight_only"

ALLOWED_TARGET_TYPES = {"boundary", "obstacle", "body"}
ALLOWED_MOTION_KINDS = {
    "stationary",
    "constant_translation",
    "sinusoidal_translation",
    "constant_rotation",
    "oscillatory_rotation",
}
EXPECTED_UNITS = {"length": "m", "time": "s", "angle": "rad"}
DANGEROUS_KEYS = {
    "cmd",
    "code",
    "command",
    "command_line",
    "delete",
    "executable",
    "exec",
    "python",
    "remove",
    "script",
    "shell",
    "source_code",
    "subprocess",
    "udf",
}


def validate_motion_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a motion contract and return a JSON-serializable report."""

    errors: list[str] = []
    warnings: list[str] = []
    normalized_motions: list[dict[str, Any]] = []

    if not isinstance(payload, dict):
        return _validation_result(errors=["payload must be a JSON object"])

    dangerous_paths = _dangerous_key_paths(payload)
    if dangerous_paths:
        errors.append("dangerous executable keys are not allowed: " + ", ".join(dangerous_paths))

    schema_version = payload.get("schema_version")
    if schema_version not in (None, MOTION_CONTRACT_SCHEMA_VERSION):
        errors.append(f"schema_version must be {MOTION_CONTRACT_SCHEMA_VERSION!r}")

    top_units = payload.get("units", EXPECTED_UNITS)
    _validate_units(top_units, "units", errors)

    motions = payload.get("motions")
    if not isinstance(motions, list) or not motions:
        errors.append("motions must be a non-empty list")
        return _validation_result(errors=errors, warnings=warnings)

    seen_ids: set[str] = set()
    for index, item in enumerate(motions):
        path = f"motions[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object")
            continue

        motion_id = _string_field(item, "id", path, errors)
        if motion_id:
            if motion_id in seen_ids:
                errors.append(f"{path}.id must be unique: {motion_id}")
            seen_ids.add(motion_id)

        target_type = _string_field(item, "target_type", path, errors)
        if target_type and target_type not in ALLOWED_TARGET_TYPES:
            errors.append(f"{path}.target_type must be one of {sorted(ALLOWED_TARGET_TYPES)}")

        target_name = _string_field(item, "target_name", path, errors)
        target_patch_name = item.get("target_patch_name")
        if target_patch_name is not None and (not isinstance(target_patch_name, str) or not target_patch_name.strip()):
            errors.append(f"{path}.target_patch_name must be a non-empty string when provided")
        motion_kind = _string_field(item, "motion_kind", path, errors)
        if motion_kind and motion_kind not in ALLOWED_MOTION_KINDS:
            errors.append(f"{path}.motion_kind must be one of {sorted(ALLOWED_MOTION_KINDS)}")

        units = item.get("units", top_units)
        _validate_units(units, f"{path}.units", errors)

        reference_point = _vector_field(item, "reference_point", path, errors)
        parameters = item.get("parameters", {})
        if not isinstance(parameters, dict):
            errors.append(f"{path}.parameters must be an object")
            parameters = {}

        axis = item.get("axis", [0.0, 0.0, 1.0])
        if motion_kind in {"constant_rotation", "oscillatory_rotation"}:
            axis = _vector_value(axis, f"{path}.axis", errors)
            if axis and _norm(axis) <= 0.0:
                errors.append(f"{path}.axis must be nonzero for rotation")
        elif "axis" in item:
            axis = _vector_value(axis, f"{path}.axis", errors)
        else:
            axis = [0.0, 0.0, 1.0]

        if motion_kind:
            _validate_motion_parameters(motion_kind, parameters, path, errors)

        if motion_id and target_type and target_name and motion_kind and reference_point is not None and axis is not None:
            normalized_motions.append(
                {
                    "id": motion_id,
                    "target_type": target_type,
                    "target_name": target_name,
                    "target_patch_name": target_patch_name.strip() if isinstance(target_patch_name, str) else target_name,
                    "motion_kind": motion_kind,
                    "reference_point": reference_point,
                    "axis": _unit_vector(axis) if _norm(axis) > 0.0 else axis,
                    "parameters": parameters,
                    "units": units,
                }
            )

    if len(normalized_motions) != len(motions):
        warnings.append("some motions could not be normalized because validation failed")

    return _validation_result(errors=errors, warnings=warnings, normalized_motions=normalized_motions)


def sample_motion_contract(
    payload: dict[str, Any],
    output_dir: str | Path,
    *,
    time_step_s: float = 0.1,
    total_time_s: float = 1.0,
) -> dict[str, Any]:
    """Validate, sample, and write motion evidence artifacts."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    validation = validate_motion_contract(payload)
    if time_step_s <= 0.0:
        validation["passed"] = False
        validation["status"] = "failed"
        validation.setdefault("errors", []).append("time_step_s must be positive")
    if total_time_s < 0.0:
        validation["passed"] = False
        validation["status"] = "failed"
        validation.setdefault("errors", []).append("total_time_s must be nonnegative")

    artifacts = {
        "motion_summary": str(root / "motion_summary.json"),
        "motion_samples": str(root / "motion_samples.csv"),
        "motion_report": str(root / "motion_report.md"),
    }

    if not validation["passed"]:
        result = {
            "schema_version": MOTION_CONTRACT_SCHEMA_VERSION,
            "status": "failed",
            "evidence_level": MOTION_EVIDENCE_LEVEL,
            "validation": validation,
            "artifacts": artifacts,
        }
        _write_json(root / "motion_summary.json", result)
        (root / "motion_report.md").write_text(motion_report_markdown(result), encoding="utf-8")
        return result

    samples: list[dict[str, Any]] = []
    for t in _sample_times(time_step_s, total_time_s):
        for item in validation["normalized_motions"]:
            samples.append(_sample_motion(item, t))

    _write_motion_samples(root / "motion_samples.csv", samples)
    max_translation = max((_translation_magnitude(sample) for sample in samples), default=0.0)
    max_speed = max((_speed_magnitude(sample) for sample in samples), default=0.0)
    max_abs_angle = max((abs(float(sample["angle_rad"])) for sample in samples), default=0.0)
    max_abs_omega = max((abs(float(sample["angular_velocity_rad_s"])) for sample in samples), default=0.0)

    result = {
        "schema_version": MOTION_CONTRACT_SCHEMA_VERSION,
        "status": "success",
        "evidence_level": MOTION_EVIDENCE_LEVEL,
        "validation": validation,
        "sampling": {
            "time_step_s": time_step_s,
            "total_time_s": total_time_s,
            "sample_count": len(samples),
            "motion_count": validation["motion_count"],
            "time_count": len(_sample_times(time_step_s, total_time_s)),
            "max_translation_m": max_translation,
            "max_speed_m_s": max_speed,
            "max_abs_angle_rad": max_abs_angle,
            "max_abs_angular_velocity_rad_s": max_abs_omega,
        },
        "artifacts": artifacts,
        "limitations": _motion_limitations(),
    }
    _write_json(root / "motion_summary.json", result)
    (root / "motion_report.md").write_text(motion_report_markdown(result), encoding="utf-8")
    return result


def write_demo_motion_case(output_dir: str | Path) -> dict[str, Any]:
    """Write a small public motion contract fixture."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    motion_file = root / "motion.json"
    payload = demo_motion_contract()
    _write_json(motion_file, payload)
    validation = validate_motion_contract(payload)
    result = {
        "schema_version": MOTION_CONTRACT_SCHEMA_VERSION,
        "status": "success" if validation["passed"] else "failed",
        "motion_file": str(motion_file),
        "validation": validation,
    }
    _write_json(root / "demo_status.json", result)
    return result


def demo_motion_contract() -> dict[str, Any]:
    """Return an executable-code-free motion contract example."""

    return {
        "schema_version": MOTION_CONTRACT_SCHEMA_VERSION,
        "case_id": "public_motion_contract_demo",
        "description": "Kinematic moving-boundary and moving-obstacle contract for agent preflight.",
        "units": EXPECTED_UNITS,
        "motions": [
            {
                "id": "oscillating_obstacle_x",
                "target_type": "obstacle",
                "target_name": "cylinder_obstacle",
                "motion_kind": "sinusoidal_translation",
                "reference_point": [0.0, 0.0, 0.0],
                "parameters": {"amplitude_m": [0.02, 0.0, 0.0], "frequency_hz": 0.5, "phase_rad": 0.0},
            },
            {
                "id": "moving_wall_y",
                "target_type": "boundary",
                "target_name": "top_wall",
                "motion_kind": "constant_translation",
                "reference_point": [0.0, 0.5, 0.0],
                "parameters": {"velocity_m_s": [0.0, 0.1, 0.0]},
            },
            {
                "id": "rotating_body_proxy",
                "target_type": "body",
                "target_name": "rotor_proxy",
                "motion_kind": "constant_rotation",
                "reference_point": [0.0, 0.0, 0.0],
                "axis": [0.0, 0.0, 1.0],
                "parameters": {"angular_velocity_rad_s": 2.0 * math.pi},
            },
        ],
    }


def motion_report_markdown(result: dict[str, Any]) -> str:
    """Render a compact motion evidence report."""

    validation = result.get("validation", {})
    sampling = result.get("sampling", {})
    lines = [
        "# FastFluent Motion Contract Report",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Evidence level: `{result.get('evidence_level', MOTION_EVIDENCE_LEVEL)}`",
        f"- Motion count: `{validation.get('motion_count', 0)}`",
        f"- Validation passed: `{validation.get('passed')}`",
        "",
    ]
    if validation.get("errors"):
        lines.extend(["## Errors", ""])
        lines.extend(f"- {item}" for item in validation.get("errors", []))
        lines.append("")
    if sampling:
        lines.extend(
            [
                "## Sampling",
                "",
                f"- Time step: `{sampling.get('time_step_s')}` s",
                f"- Total time: `{sampling.get('total_time_s')}` s",
                f"- Sample rows: `{sampling.get('sample_count')}`",
                f"- Max translation: `{sampling.get('max_translation_m')}` m",
                f"- Max speed: `{sampling.get('max_speed_m_s')}` m/s",
                f"- Max absolute angle: `{sampling.get('max_abs_angle_rad')}` rad",
                "",
            ]
        )
    lines.extend(["## Motion Objects", ""])
    for item in validation.get("normalized_motions", []):
        lines.append(
            f"- `{item['id']}`: `{item['target_type']}` `{item['target_name']}` with `{item['motion_kind']}`"
        )
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in result.get("limitations", _motion_limitations()))
    lines.append("")
    return "\n".join(lines)


def _validate_motion_parameters(kind: str, parameters: dict[str, Any], path: str, errors: list[str]) -> None:
    if kind == "stationary":
        return
    if kind == "constant_translation":
        _vector_value(parameters.get("velocity_m_s"), f"{path}.parameters.velocity_m_s", errors)
        return
    if kind == "sinusoidal_translation":
        _vector_value(parameters.get("amplitude_m"), f"{path}.parameters.amplitude_m", errors)
        frequency = _number_value(parameters.get("frequency_hz"), f"{path}.parameters.frequency_hz", errors)
        if frequency is not None and frequency <= 0.0:
            errors.append(f"{path}.parameters.frequency_hz must be positive")
        if "phase_rad" in parameters:
            _number_value(parameters.get("phase_rad"), f"{path}.parameters.phase_rad", errors)
        return
    if kind == "constant_rotation":
        _number_value(parameters.get("angular_velocity_rad_s"), f"{path}.parameters.angular_velocity_rad_s", errors)
        return
    if kind == "oscillatory_rotation":
        amplitude = _number_value(parameters.get("amplitude_rad"), f"{path}.parameters.amplitude_rad", errors)
        frequency = _number_value(parameters.get("frequency_hz"), f"{path}.parameters.frequency_hz", errors)
        if amplitude is not None and amplitude < 0.0:
            errors.append(f"{path}.parameters.amplitude_rad must be nonnegative")
        if frequency is not None and frequency <= 0.0:
            errors.append(f"{path}.parameters.frequency_hz must be positive")
        if "phase_rad" in parameters:
            _number_value(parameters.get("phase_rad"), f"{path}.parameters.phase_rad", errors)


def _sample_motion(item: dict[str, Any], time_s: float) -> dict[str, Any]:
    kind = item["motion_kind"]
    params = item.get("parameters", {})
    axis = item.get("axis", [0.0, 0.0, 1.0])

    displacement = [0.0, 0.0, 0.0]
    velocity = [0.0, 0.0, 0.0]
    angle_rad = 0.0
    angular_velocity_rad_s = 0.0

    if kind == "constant_translation":
        velocity = [float(value) for value in params["velocity_m_s"]]
        displacement = [value * time_s for value in velocity]
    elif kind == "sinusoidal_translation":
        amplitude = [float(value) for value in params["amplitude_m"]]
        frequency = float(params["frequency_hz"])
        phase = float(params.get("phase_rad", 0.0))
        omega = 2.0 * math.pi * frequency
        displacement = [value * math.sin(omega * time_s + phase) for value in amplitude]
        velocity = [value * omega * math.cos(omega * time_s + phase) for value in amplitude]
    elif kind == "constant_rotation":
        angular_velocity_rad_s = float(params["angular_velocity_rad_s"])
        angle_rad = angular_velocity_rad_s * time_s
    elif kind == "oscillatory_rotation":
        amplitude = float(params["amplitude_rad"])
        frequency = float(params["frequency_hz"])
        phase = float(params.get("phase_rad", 0.0))
        omega = 2.0 * math.pi * frequency
        angle_rad = amplitude * math.sin(omega * time_s + phase)
        angular_velocity_rad_s = amplitude * omega * math.cos(omega * time_s + phase)

    return {
        "time_s": _round_float(time_s),
        "motion_id": item["id"],
        "target_type": item["target_type"],
        "target_name": item["target_name"],
        "motion_kind": kind,
        "dx_m": _round_float(displacement[0]),
        "dy_m": _round_float(displacement[1]),
        "dz_m": _round_float(displacement[2]),
        "vx_m_s": _round_float(velocity[0]),
        "vy_m_s": _round_float(velocity[1]),
        "vz_m_s": _round_float(velocity[2]),
        "angle_rad": _round_float(angle_rad),
        "angular_velocity_rad_s": _round_float(angular_velocity_rad_s),
        "axis_x": _round_float(axis[0]),
        "axis_y": _round_float(axis[1]),
        "axis_z": _round_float(axis[2]),
    }


def _write_motion_samples(path: Path, samples: list[dict[str, Any]]) -> None:
    fieldnames = [
        "time_s",
        "motion_id",
        "target_type",
        "target_name",
        "motion_kind",
        "dx_m",
        "dy_m",
        "dz_m",
        "vx_m_s",
        "vy_m_s",
        "vz_m_s",
        "angle_rad",
        "angular_velocity_rad_s",
        "axis_x",
        "axis_y",
        "axis_z",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(samples)


def _sample_times(time_step_s: float, total_time_s: float) -> list[float]:
    count = int(math.floor(total_time_s / time_step_s))
    times = [_round_float(i * time_step_s) for i in range(count + 1)]
    if not times or not math.isclose(times[-1], total_time_s, rel_tol=0.0, abs_tol=1.0e-12):
        times.append(_round_float(total_time_s))
    return times


def _validation_result(
    *,
    errors: list[str],
    warnings: list[str] | None = None,
    normalized_motions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_motions = normalized_motions or []
    return {
        "schema_version": MOTION_CONTRACT_SCHEMA_VERSION,
        "status": "passed" if not errors else "failed",
        "passed": not errors,
        "errors": errors,
        "warnings": warnings or [],
        "motion_count": len(normalized_motions),
        "normalized_motions": normalized_motions,
        "sample_safe": not errors,
        "evidence_level": MOTION_EVIDENCE_LEVEL,
        "limitations": _motion_limitations(),
    }


def _string_field(item: dict[str, Any], key: str, path: str, errors: list[str]) -> str | None:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key} must be a non-empty string")
        return None
    return value.strip()


def _vector_field(item: dict[str, Any], key: str, path: str, errors: list[str]) -> list[float] | None:
    if key not in item:
        errors.append(f"{path}.{key} is required")
        return None
    return _vector_value(item.get(key), f"{path}.{key}", errors)


def _vector_value(value: Any, path: str, errors: list[str]) -> list[float] | None:
    if not isinstance(value, list | tuple) or len(value) != 3:
        errors.append(f"{path} must be a 3-value numeric vector")
        return None
    vector: list[float] = []
    for index, component in enumerate(value):
        number = _number_value(component, f"{path}[{index}]", errors)
        if number is None:
            return None
        vector.append(number)
    return vector


def _number_value(value: Any, path: str, errors: list[str]) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        errors.append(f"{path} must be numeric")
        return None
    value = float(value)
    if not math.isfinite(value):
        errors.append(f"{path} must be finite")
        return None
    return value


def _validate_units(units: Any, path: str, errors: list[str]) -> None:
    if not isinstance(units, dict):
        errors.append(f"{path} must be an object")
        return
    for key, expected in EXPECTED_UNITS.items():
        if units.get(key) != expected:
            errors.append(f"{path}.{key} must be {expected!r}")


def _dangerous_key_paths(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key).lower() in DANGEROUS_KEYS:
                hits.append(child_path)
            hits.extend(_dangerous_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_dangerous_key_paths(child, f"{path}[{index}]"))
    return hits


def _norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _unit_vector(vector: list[float]) -> list[float]:
    norm = _norm(vector)
    if norm <= 0.0:
        return vector
    return [_round_float(value / norm) for value in vector]


def _translation_magnitude(sample: dict[str, Any]) -> float:
    return math.sqrt(float(sample["dx_m"]) ** 2 + float(sample["dy_m"]) ** 2 + float(sample["dz_m"]) ** 2)


def _speed_magnitude(sample: dict[str, Any]) -> float:
    return math.sqrt(float(sample["vx_m_s"]) ** 2 + float(sample["vy_m_s"]) ** 2 + float(sample["vz_m_s"]) ** 2)


def _round_float(value: float) -> float:
    return round(float(value), 12)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _motion_limitations() -> list[str]:
    return [
        "This is a kinematic preflight contract only.",
        "It does not perform dynamic mesh deformation.",
        "It does not perform FSI coupling.",
        "It does not replace Fluent dynamic mesh or final CFD validation.",
    ]
