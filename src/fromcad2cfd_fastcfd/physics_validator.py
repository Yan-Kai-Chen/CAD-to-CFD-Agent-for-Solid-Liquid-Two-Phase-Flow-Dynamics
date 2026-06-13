"""Physics validation and passport generation for FastCFD jobs."""

from __future__ import annotations

import math
from typing import Any

from .schemas import FastCFDJob, PhysicsContract


CS2_LATTICE = 1.0 / 3.0
CS_LATTICE = math.sqrt(CS2_LATTICE)

TAU_RECOMMENDED_MIN = 0.55
TAU_RECOMMENDED_MAX = 1.20
TAU_ACCEPTED_MIN = 0.52
TAU_ACCEPTED_MAX = 2.00
MACH_RECOMMENDED_MAX = 0.08
MACH_ACCEPTED_MAX = 0.10

AGENT_LIMITS = {
    "max_cells_2d": 2_000_000,
    "max_steps": 200_000,
    "max_timeout_seconds": 900,
}

CI_LIMITS = {
    "max_cells_2d": 50_000,
    "max_steps": 2_000,
    "max_timeout_seconds": 60,
}


def validation_thresholds(profile: str = "agent") -> dict[str, Any]:
    """Return the active physics and resource thresholds."""

    return {
        "tau": {
            "recommended_min": TAU_RECOMMENDED_MIN,
            "recommended_max": TAU_RECOMMENDED_MAX,
            "accepted_min": TAU_ACCEPTED_MIN,
            "accepted_max": TAU_ACCEPTED_MAX,
        },
        "mach_lattice": {
            "recommended_max": MACH_RECOMMENDED_MAX,
            "accepted_max": MACH_ACCEPTED_MAX,
        },
        "resources": CI_LIMITS if profile == "ci" else AGENT_LIMITS,
    }


def validate_physics(
    job: FastCFDJob,
    *,
    profile: str = "agent",
    allow_debug_override: bool = False,
) -> PhysicsContract:
    """Return a machine-readable physics passport for a FastCFD job."""

    errors: list[str] = []
    warnings: list[str] = []
    remediation: list[str] = []
    checks: dict[str, Any] = {}

    limits = CI_LIMITS if profile == "ci" else AGENT_LIMITS

    rho = _positive_float(job.physical_properties, "rho_ref_g_per_mm3", errors)
    viscosity = _positive_float(job.physical_properties, "kinematic_viscosity_mm2_s", errors)
    cell_length = _positive_float(job.dimensions, "cell_length_mm", errors)
    nx = _positive_int(job.dimensions, "nx", errors)
    ny = _positive_int(job.dimensions, "ny", errors)
    nz = _positive_int(job.dimensions, "nz", errors, required=False)
    total_steps = _positive_int(job.solver_settings, "total_steps", errors)
    output_interval = _positive_int(job.solver_settings, "output_interval", errors)
    timeout_seconds = int(float(job.solver_settings.get("timeout_seconds", limits["max_timeout_seconds"])))
    tau = _positive_float(job.solver_settings, "relaxation_time", errors, aliases=("rt", "tau"))
    velocity = _reference_velocity(job, errors)

    dimensions_count = 3 if nz else 2
    cell_count = nx * ny * (nz or 1) if nx and ny else 0
    length_scale_mm = nx * cell_length if nx and cell_length else None
    reynolds = velocity * length_scale_mm / viscosity if velocity is not None and length_scale_mm and viscosity else None
    omega = 1.0 / tau if tau else None
    nu_lattice = CS2_LATTICE * (tau - 0.5) if tau else None
    lattice_velocity = _estimate_lattice_velocity(
        physical_velocity=velocity,
        reynolds=reynolds,
        nu_lattice=nu_lattice,
        lattice_length=nx,
    )
    mach = abs(lattice_velocity) / CS_LATTICE if lattice_velocity is not None else None

    checks.update(
        {
            "profile": profile,
            "dimension": dimensions_count,
            "rho_ref_g_per_mm3": rho,
            "kinematic_viscosity_mm2_s": viscosity,
            "cell_length_mm": cell_length,
            "nx": nx,
            "ny": ny,
            "nz": nz,
            "cell_count": cell_count,
            "length_scale_mm": length_scale_mm,
            "reference_velocity_mm_s": velocity,
            "reynolds_number": reynolds,
            "tau": tau,
            "rt": tau,
            "omega": omega,
            "nu_lattice_estimate": nu_lattice,
            "lattice_velocity_estimate": lattice_velocity,
            "mach_lattice_estimate": mach,
            "total_steps": total_steps,
            "output_interval": output_interval,
            "timeout_seconds": timeout_seconds,
            "resource_limits": limits,
        }
    )

    if output_interval and total_steps and output_interval > total_steps:
        errors.append("output_interval must not exceed total_steps.")
        remediation.append("Reduce output_interval or increase total_steps.")
    if total_steps and total_steps > limits["max_steps"]:
        errors.append(f"total_steps exceeds the {profile} limit: {total_steps} > {limits['max_steps']}.")
        remediation.append("Reduce total_steps or use an explicitly reviewed local profile.")
    if timeout_seconds > limits["max_timeout_seconds"]:
        errors.append(f"timeout_seconds exceeds the {profile} limit: {timeout_seconds} > {limits['max_timeout_seconds']}.")
        remediation.append("Reduce timeout_seconds or run outside agent-managed execution.")
    if dimensions_count == 2 and cell_count > limits["max_cells_2d"]:
        errors.append(f"2D cell_count exceeds the {profile} limit: {cell_count} > {limits['max_cells_2d']}.")
        remediation.append("Reduce nx/ny or increase cell_length_mm.")
    if tau is not None:
        if tau < TAU_ACCEPTED_MIN or tau > TAU_ACCEPTED_MAX:
            message = f"tau/RT is outside accepted FastCFD limits: {tau}."
            if allow_debug_override:
                warnings.append(message + " Debug override allowed this job.")
            else:
                errors.append(message)
                remediation.append("Choose a tau/RT in [0.52, 2.00], preferably [0.55, 1.20].")
        elif tau < TAU_RECOMMENDED_MIN or tau > TAU_RECOMMENDED_MAX:
            warnings.append(f"tau/RT is outside the recommended band: {tau}.")
    if nu_lattice is not None and nu_lattice <= 0:
        errors.append(f"Estimated lattice viscosity must be positive; got {nu_lattice}.")
        remediation.append("Use tau/RT greater than 0.5.")
    if mach is not None:
        if mach >= MACH_ACCEPTED_MAX:
            message = f"lattice Mach estimate is too high: {mach:.6g}."
            if allow_debug_override:
                warnings.append(message + " Debug override allowed this job.")
            else:
                errors.append(message)
                remediation.append("Reduce reference velocity, increase viscosity, or revise lattice scaling.")
        elif mach >= MACH_RECOMMENDED_MAX:
            warnings.append(f"lattice Mach estimate is above the recommended band: {mach:.6g}.")

    stability_band = _stability_band(errors, warnings)
    checks["stability_band"] = stability_band
    checks["warnings"] = warnings
    checks["errors"] = errors

    status = "failed" if errors else ("warning" if warnings else "passed")
    limitations = [
        "FastCFD/FastFluent is an advisory pilot solver and does not replace Fluent validation.",
        "Physics checks are conservative gates for agent-managed runs, not a proof of final CFD accuracy.",
    ]
    return PhysicsContract(
        status=status,
        case_type=job.case_type,
        checks=checks,
        thresholds=validation_thresholds(profile),
        limitations=limitations,
        remediation_suggestions=remediation,
    )


def contract_has_blocking_errors(contract: PhysicsContract) -> bool:
    """Return True when a physics contract must block execution."""

    return contract.status == "failed" or bool(contract.checks.get("errors"))


def _positive_float(
    mapping: dict[str, Any],
    key: str,
    errors: list[str],
    *,
    aliases: tuple[str, ...] = (),
    required: bool = True,
) -> float | None:
    value = None
    present_key = None
    for candidate in (key, *aliases):
        if candidate in mapping:
            value = mapping[candidate]
            present_key = candidate
            break
    if value is None:
        if required:
            errors.append(f"Missing required physics value: {key}.")
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"Physics value must be numeric: {present_key}.")
        return None
    if number <= 0:
        errors.append(f"Physics value must be positive: {present_key}.")
        return None
    return number


def _positive_int(
    mapping: dict[str, Any],
    key: str,
    errors: list[str],
    *,
    required: bool = True,
) -> int | None:
    value = mapping.get(key)
    if value is None:
        if required:
            errors.append(f"Missing required integer value: {key}.")
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        errors.append(f"Integer value must be numeric: {key}.")
        return None
    if number <= 0:
        errors.append(f"Integer value must be positive: {key}.")
        return None
    return number


def _reference_velocity(job: FastCFDJob, errors: list[str]) -> float | None:
    candidates = (
        "moving_wall_velocity_mm_s",
        "inlet_velocity_mm_s",
        "u_ref_mm_s",
        "reference_velocity_mm_s",
    )
    for key in candidates:
        if key in job.boundary_conditions:
            try:
                velocity = float(job.boundary_conditions[key])
            except (TypeError, ValueError):
                errors.append(f"Reference velocity must be numeric: {key}.")
                return None
            if velocity < 0:
                errors.append(f"Reference velocity must be non-negative: {key}.")
                return None
            return velocity
    errors.append("Missing reference velocity in boundary_conditions.")
    return None


def _estimate_lattice_velocity(
    *,
    physical_velocity: float | None,
    reynolds: float | None,
    nu_lattice: float | None,
    lattice_length: int | None,
) -> float | None:
    if reynolds is not None and nu_lattice is not None and lattice_length:
        return reynolds * nu_lattice / lattice_length
    return physical_velocity


def _stability_band(errors: list[str], warnings: list[str]) -> str:
    if errors:
        return "rejected"
    if warnings:
        return "accepted_with_warning"
    return "recommended"
