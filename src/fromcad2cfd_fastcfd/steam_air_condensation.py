"""Steam-air wall-condensation screening passport for FastFluent.

This is an engineering readiness gate for Fluent setup planning. It is not a
high-fidelity condensation solver and does not execute Fluent.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .paths import unique_path
from .solver_plan_patch import find_dangerous_keys


STEAM_AIR_CASE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_steam_air_condensation_case_v1"
STEAM_AIR_PASSPORT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_steam_air_condensation_passport_v1"
STEAM_AIR_FLUENT_HINTS_SCHEMA_VERSION = "fromcad2cfd_fastfluent_steam_air_condensation_fluent_hints_v1"
ALLOWED_CONDENSATION_MODEL = "near_wall_limited_engineering"

SATURATION_TABLE = [
    (101325.0, 373.15),
    (200000.0, 393.36),
    (300000.0, 406.67),
    (500000.0, 424.98),
    (700000.0, 438.03),
    (1000000.0, 453.03),
    (1500000.0, 471.45),
    (2000000.0, 485.53),
]

DEFAULT_LIMITATIONS = [
    "This passport uses a bounded engineering saturation-temperature table, not IAPWS thermodynamics.",
    "This is a setup-readiness and Fluent-handoff artifact, not final CFD validation.",
    "Condensation source-term behavior must be reviewed in Fluent with mesh, boundary, and monitor evidence.",
]


def demo_steam_air_condensation_case(case_name: str = "steam_air_wall_condensation_demo") -> dict[str, Any]:
    return {
        "schema_version": STEAM_AIR_CASE_SCHEMA_VERSION,
        "case_name": case_name,
        "pressure_pa": 700000.0,
        "inlet_temperature_K": 438.0,
        "wall_temperature_K": 363.0,
        "steam_mass_fraction": 0.92,
        "air_mass_fraction": 0.08,
        "reference_velocity_m_s": 12.0,
        "length_scale_m": 0.05,
        "near_wall_cell_length_m": 0.0005,
        "time_step_s": 0.0005,
        "thermal_diffusivity_m2_s": 2.0e-5,
        "latent_heat_j_kg": 2257000.0,
        "condensation_model": ALLOWED_CONDENSATION_MODEL,
        "units": {
            "pressure": "Pa",
            "temperature": "K",
            "length": "m",
            "time": "s",
        },
        "metadata": {
            "purpose": "public synthetic early steam-air wall condensation screening demo",
        },
    }


def write_demo_steam_air_case(
    *,
    output_dir: str | Path | None = None,
    case_name: str = "steam_air_wall_condensation_demo",
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "steam_air_demo" / "input")
    target_dir.mkdir(parents=True, exist_ok=True)
    case = demo_steam_air_condensation_case(case_name=case_name)
    case_file = _write_json(target_dir / "steam_air_condensation_case.json", case)
    result = AgentResult.success(
        backend="fastcfd",
        operation="write_steam_air_demo",
        message="Public steam-air condensation demo case written.",
        outputs={"case_file": str(case_file), "case": case},
        metadata={"output_dir": str(target_dir)},
    )
    return result.to_dict()


def read_steam_air_condensation_case(path: str | Path) -> dict[str, Any]:
    with open(_windows_long_path(Path(path)), "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_steam_air_condensation_case_file(
    case_file: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "steam_air_condensation" / "passport")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        case_path = Path(case_file)
        case = read_steam_air_condensation_case(case_path)
        passport = build_steam_air_condensation_passport(case, source_artifact=str(case_path))
        hints = build_steam_air_fluent_hints(passport)
        artifacts = {
            "passport": str(_write_json(target_dir / "steam_air_condensation_passport.json", passport)),
            "fluent_hints": str(_write_json(target_dir / "steam_air_condensation_fluent_hints.json", hints)),
            "report": str(_write_text(target_dir / "steam_air_condensation_report.md", steam_air_condensation_report(passport, hints))),
        }
        result_status = "success" if passport["status"] in {"pass", "warn"} else "failed"
        if result_status == "success":
            result = AgentResult.success(
                backend="fastcfd",
                operation="validate_steam_air_condensation",
                message="Steam-air condensation passport generated.",
                outputs={"artifacts": artifacts, "passport": passport, "fluent_hints": hints},
                metadata={"output_dir": str(target_dir), "case_file": str(case_file)},
            )
        else:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="validate_steam_air_condensation",
                message="Steam-air condensation passport blocked the case.",
                errors=passport.get("blocking_errors", []),
                metadata={"output_dir": str(target_dir), "case_file": str(case_file)},
            )
            result.outputs.update({"artifacts": artifacts, "passport": passport, "fluent_hints": hints})
        artifacts["status"] = str(_write_json(target_dir / "steam_air_condensation_status.json", result.to_dict()))
        return result.to_dict()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        blocked = _blocked_passport(
            case={"case_name": Path(case_file).stem if case_file else "unknown"},
            blocking_errors=[str(exc)],
            source_artifact=str(case_file),
        )
        hints = build_steam_air_fluent_hints(blocked)
        artifacts = {
            "passport": str(_write_json(target_dir / "steam_air_condensation_passport.json", blocked)),
            "fluent_hints": str(_write_json(target_dir / "steam_air_condensation_fluent_hints.json", hints)),
            "report": str(_write_text(target_dir / "steam_air_condensation_report.md", steam_air_condensation_report(blocked, hints))),
        }
        failure = AgentResult.failed(
            backend="fastcfd",
            operation="validate_steam_air_condensation",
            message="Steam-air condensation passport generation failed closed.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir), "case_file": str(case_file)},
        )
        failure.outputs.update({"artifacts": artifacts, "passport": blocked, "fluent_hints": hints})
        artifacts["status"] = str(_write_json(target_dir / "steam_air_condensation_status.json", failure.to_dict()))
        return failure.to_dict()


def build_steam_air_condensation_passport(case: dict[str, Any], *, source_artifact: str = "inline_case") -> dict[str, Any]:
    errors = _validate_case(case)
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    if errors:
        return _blocked_passport(case=case, blocking_errors=errors, source_artifact=source_artifact)

    pressure_pa = float(case["pressure_pa"])
    saturation = _estimate_saturation_temperature(pressure_pa)
    if saturation["status"] == "block":
        return _blocked_passport(
            case=case,
            blocking_errors=[saturation["note"]],
            source_artifact=source_artifact,
            computed_quantities={"pressure_pa": pressure_pa},
        )
    if saturation["status"] == "warn":
        warnings.append(saturation["note"])

    tsat = saturation["temperature_K"]
    inlet_superheat = float(case["inlet_temperature_K"]) - tsat
    wall_subcooling = tsat - float(case["wall_temperature_K"])
    thermal_depth = math.sqrt(float(case["thermal_diffusivity_m2_s"]) * float(case["time_step_s"]))
    tiny = 1.0e-30
    near_wall_ratio = float(case["near_wall_cell_length_m"]) / max(thermal_depth, tiny)
    convective_time = float(case["length_scale_m"]) / max(float(case["reference_velocity_m_s"]), 1.0e-12)
    diffusion_time = float(case["near_wall_cell_length_m"]) ** 2 / max(float(case["thermal_diffusivity_m2_s"]), tiny)
    recommended_dt = min(float(case["time_step_s"]), 0.2 * diffusion_time, 0.02 * convective_time)
    noncondensable_risk = _noncondensable_risk(float(case["air_mass_fraction"]))
    resolution_class = _resolution_class(near_wall_ratio)
    source_risk, source_score = _source_stiffness_risk(
        wall_subcooling_K=wall_subcooling,
        time_step_s=float(case["time_step_s"]),
        recommended_time_step_s=recommended_dt,
        near_wall_resolution_ratio=near_wall_ratio,
        air_mass_fraction=float(case["air_mass_fraction"]),
    )

    if inlet_superheat < -2.0:
        warnings.append("Inlet temperature is below the estimated saturation temperature; steam inlet consistency requires review.")
    if wall_subcooling <= 0.0:
        warnings.append("Wall is not below the estimated saturation temperature; condensation is unlikely in this simplified check.")
    if noncondensable_risk in {"moderate", "high"}:
        warnings.append(f"Non-condensable layer risk is {noncondensable_risk}; species transport and near-wall mass-fraction monitors are required.")
    if resolution_class in {"marginal", "poor"}:
        warnings.append(f"Near-wall thermal resolution is {resolution_class}; mesh refinement should be reviewed.")
    if recommended_dt < 0.5 * float(case["time_step_s"]):
        warnings.append("Recommended initial time step is substantially smaller than the input time step.")
    if source_risk in {"moderate", "high"}:
        warnings.append(f"Condensation source-term stiffness risk is {source_risk}; ramping and clamping are recommended.")

    blocking_errors: list[str] = []
    if source_score >= 6:
        blocking_errors.append("Source-term stiffness screening is extreme; reduce time step and refine near-wall mesh before Fluent execution.")

    computed = {
        "estimated_saturation_temperature_K": tsat,
        "saturation_estimate_method": "log-pressure interpolation over internal water saturation screening table",
        "saturation_estimate_validity_note": saturation["note"],
        "inlet_superheat_K": inlet_superheat,
        "wall_subcooling_K": wall_subcooling,
        "non_condensable_layer_risk": noncondensable_risk,
        "thermal_penetration_depth_m": thermal_depth,
        "near_wall_resolution_ratio": near_wall_ratio,
        "near_wall_resolution_class": resolution_class,
        "convective_time_scale_s": convective_time,
        "near_wall_diffusion_time_scale_s": diffusion_time,
        "recommended_time_step_s": recommended_dt,
        "source_term_stiffness_risk": source_risk,
        "source_term_stiffness_score": source_score,
    }

    checks.extend(
        [
            _check(
                "steam_air_regime_first_pass",
                "pressure_pa",
                pressure_pa,
                "Pa",
                "101325 Pa <= pressure_pa <= 2000000 Pa",
                "Pressure is inside the bounded saturation-table range for a first-pass Fluent setup screen.",
                "medium",
                source_artifact,
            ),
            _check(
                "steam_air_wall_below_saturation",
                "wall_subcooling_K",
                wall_subcooling,
                "K",
                "wall_temperature_K < estimated_saturation_temperature_K",
                "Wall is below estimated saturation temperature; near-wall condensation is physically plausible."
                if wall_subcooling > 0
                else "Wall is not below estimated saturation temperature; condensation source terms should not be enabled without review.",
                "medium",
                source_artifact,
            ),
            _check(
                "steam_air_species_consistency",
                "steam_plus_air_mass_fraction_sum",
                float(case["steam_mass_fraction"]) + float(case["air_mass_fraction"]),
                "1",
                "abs(steam_mass_fraction + air_mass_fraction - 1) <= 1e-6",
                "Steam and air mass fractions close within tolerance.",
                "high",
                source_artifact,
            ),
            _check(
                "steam_air_noncondensable_risk",
                "air_mass_fraction",
                float(case["air_mass_fraction"]),
                "1",
                "air_mass_fraction < 0.01 low, < 0.05 moderate, otherwise high",
                f"Non-condensable layer risk is {noncondensable_risk}.",
                "medium",
                source_artifact,
            ),
            _check(
                "steam_air_near_wall_resolution",
                "near_wall_resolution_ratio",
                near_wall_ratio,
                "1",
                "ratio <= 1 acceptable, <= 5 marginal, > 5 poor",
                f"Near-wall thermal layer resolution is {resolution_class}.",
                "medium",
                source_artifact,
            ),
            _check(
                "steam_air_recommended_time_step",
                "recommended_time_step_s",
                recommended_dt,
                "s",
                "min(input_dt, 0.2 * diffusion_time, 0.02 * convective_time)",
                "Recommended initial time step from near-wall diffusion and convective screening.",
                "medium",
                source_artifact,
            ),
            _check(
                "steam_air_source_stiffness_risk",
                "source_term_stiffness_risk",
                source_risk,
                "class",
                "risk increases with large subcooling, high air fraction, large time-step ratio, and poor near-wall resolution",
                f"Source-term stiffness risk is {source_risk}.",
                "medium",
                source_artifact,
            ),
        ]
    )

    status = "block" if blocking_errors else ("warn" if warnings else "pass")
    passport = {
        "schema_version": STEAM_AIR_PASSPORT_SCHEMA_VERSION,
        "case_name": str(case.get("case_name") or "steam_air_condensation_case"),
        "status": status,
        "summary": _summary(status, wall_subcooling, noncondensable_risk, source_risk),
        "inputs": case,
        "computed_quantities": computed,
        "checks": checks,
        "fluent_hints": {},
        "warnings": warnings,
        "blocking_errors": blocking_errors,
        "limitations": list(DEFAULT_LIMITATIONS),
        "metadata": {
            "source_artifact": source_artifact,
            "solver_execution": "not_attempted_passport_only",
        },
    }
    passport["fluent_hints"] = build_steam_air_fluent_hints(passport)
    return passport


def build_steam_air_fluent_hints(passport: dict[str, Any]) -> dict[str, Any]:
    computed = passport.get("computed_quantities", {})
    recommended_dt = computed.get("recommended_time_step_s")
    hints = {
        "schema_version": STEAM_AIR_FLUENT_HINTS_SCHEMA_VERSION,
        "case_name": passport.get("case_name"),
        "status": passport.get("status"),
        "recommended_physics": {
            "pressure_based_solver": True,
            "transient": True,
            "energy": True,
            "species_transport": True,
            "ideal_gas_mixture_first_pass": True,
            "solver": "pressure-based",
            "time": "transient",
            "material_model": "ideal-gas-mixture",
            "mixture_species": ["h2o", "o2", "n2"],
            "condensation_source_term": ALLOWED_CONDENSATION_MODEL,
        },
        "recommended_materials": {
            "mixture": "steam-air ideal-gas first-pass mixture",
            "species": ["h2o", "o2", "n2"],
            "latent_heat_j_kg": passport.get("inputs", {}).get("latent_heat_j_kg"),
            "review_required": ["temperature-dependent properties", "latent heat convention", "wall heat-transfer sign convention"],
        },
        "recommended_numerics": {
            "initial_discretization": "first-order-upwind",
            "later_discretization": "second-order-upwind-after-stable-warmup",
            "pressure_velocity_coupling": "coupled-or-piso-review-required",
            "source_term_ramping": True,
            "source_term_clamp": True,
        },
        "recommended_transient_controls": {
            "initial_time_step_s": recommended_dt,
            "adaptive_time_step": True,
            "max_courant_number": 1.0,
            "checkpoint_interval": "frequent during early transient",
        },
        "recommended_monitors": [
            "residuals",
            "max_temperature",
            "min_temperature",
            "max_velocity",
            "pressure_range",
            "steam_mass_fraction_min_max",
            "air_mass_fraction_min_max",
            "wall_heat_transfer_rate",
            "wall_temperature",
            "wall_adjacent_steam_mass_fraction",
            "mass_imbalance",
            "energy_imbalance",
            "source_term_integral_if_available",
        ],
        "recommended_source_term_controls": [
            "source ramp",
            "source clamp",
            "NaN guard",
            "temperature bounds",
            "species fraction bounds",
            "sign convention review",
        ],
        "warnings": list(passport.get("warnings", [])),
        "blocking_errors": list(passport.get("blocking_errors", [])),
        "limitations": list(passport.get("limitations", DEFAULT_LIMITATIONS)),
        "metadata": {
            "source_passport_schema_version": passport.get("schema_version"),
            "solver_execution": "not_attempted_hints_only",
        },
    }
    if passport.get("status") == "block":
        hints["recommended_transient_controls"]["fluent_execution"] = "blocked_until_passport_errors_are_resolved"
    return hints


def steam_air_condensation_report(passport: dict[str, Any], hints: dict[str, Any]) -> str:
    computed = passport.get("computed_quantities", {})
    inputs = passport.get("inputs", {})
    lines = [
        "# Steam-Air Condensation Physics Passport",
        "",
        f"Case name: `{passport.get('case_name')}`",
        f"Status: `{passport.get('status')}`",
        "",
        "## Input Summary",
        "",
        f"- Pressure: `{inputs.get('pressure_pa')}` Pa",
        f"- Inlet temperature: `{inputs.get('inlet_temperature_K')}` K",
        f"- Wall temperature: `{inputs.get('wall_temperature_K')}` K",
        f"- Steam mass fraction: `{inputs.get('steam_mass_fraction')}`",
        f"- Air mass fraction: `{inputs.get('air_mass_fraction')}`",
        "",
        "## Saturation Estimate",
        "",
        f"- Estimated saturation temperature: `{computed.get('estimated_saturation_temperature_K')}` K",
        f"- Method: `{computed.get('saturation_estimate_method')}`",
        f"- Note: {computed.get('saturation_estimate_validity_note')}",
        "",
        "## Wall Condensation Potential",
        "",
        f"- Inlet superheat: `{computed.get('inlet_superheat_K')}` K",
        f"- Wall subcooling: `{computed.get('wall_subcooling_K')}` K",
        "",
        "## Non-Condensable Gas Risk",
        "",
        f"- Risk: `{computed.get('non_condensable_layer_risk')}`",
        "",
        "## Thermal Penetration And Near-Wall Resolution",
        "",
        f"- Thermal penetration depth: `{computed.get('thermal_penetration_depth_m')}` m",
        f"- Near-wall resolution ratio: `{computed.get('near_wall_resolution_ratio')}`",
        f"- Resolution class: `{computed.get('near_wall_resolution_class')}`",
        "",
        "## Time-Step Recommendation",
        "",
        f"- Convective time scale: `{computed.get('convective_time_scale_s')}` s",
        f"- Near-wall diffusion time scale: `{computed.get('near_wall_diffusion_time_scale_s')}` s",
        f"- Recommended initial time step: `{computed.get('recommended_time_step_s')}` s",
        "",
        "## Source Stiffness Risk",
        "",
        f"- Risk: `{computed.get('source_term_stiffness_risk')}`",
        f"- Score: `{computed.get('source_term_stiffness_score')}`",
        "",
        "## Fluent Setup Recommendations",
        "",
        f"- Pressure-based solver: `{hints.get('recommended_physics', {}).get('pressure_based_solver')}`",
        f"- Transient: `{hints.get('recommended_physics', {}).get('transient')}`",
        f"- Energy: `{hints.get('recommended_physics', {}).get('energy')}`",
        f"- Species transport: `{hints.get('recommended_physics', {}).get('species_transport')}`",
        f"- Initial discretization: `{hints.get('recommended_numerics', {}).get('initial_discretization')}`",
        "",
        "## Warnings",
        "",
    ]
    lines.extend(f"- {item}" for item in passport.get("warnings", [])) if passport.get("warnings") else lines.append("- None")
    lines.extend(["", "## Blocking Errors", ""])
    lines.extend(f"- {item}" for item in passport.get("blocking_errors", [])) if passport.get("blocking_errors") else lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in passport.get("limitations", DEFAULT_LIMITATIONS))
    lines.extend(
        [
            "",
            "## Reviewer Checklist",
            "",
            "- Confirm the saturation estimate is adequate for the operating pressure.",
            "- Confirm wall temperature and heat-transfer sign convention.",
            "- Confirm steam/air species definitions and material properties.",
            "- Confirm near-wall mesh spacing before enabling condensation source terms.",
            "- Confirm initial time step using Fluent CFL and monitor histories.",
            "- Confirm source-term dimensions, signs, ramping, and clamping.",
            "- Confirm energy and mass imbalance monitors before execution.",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_case(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(case, dict):
        return ["Case payload must be an object."]
    dangerous = find_dangerous_keys(case)
    if dangerous:
        errors.append("Dangerous key names found: " + ", ".join(dangerous))
    if case.get("schema_version") != STEAM_AIR_CASE_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {case.get('schema_version')!r}")
    required_positive = [
        "pressure_pa",
        "inlet_temperature_K",
        "wall_temperature_K",
        "length_scale_m",
        "near_wall_cell_length_m",
        "time_step_s",
        "thermal_diffusivity_m2_s",
        "latent_heat_j_kg",
    ]
    for key in required_positive:
        try:
            if float(case.get(key)) <= 0:
                errors.append(f"{key} must be > 0.")
        except (TypeError, ValueError):
            errors.append(f"{key} must be numeric.")
    try:
        if float(case.get("reference_velocity_m_s")) < 0:
            errors.append("reference_velocity_m_s must be >= 0.")
    except (TypeError, ValueError):
        errors.append("reference_velocity_m_s must be numeric.")
    for key in ["steam_mass_fraction", "air_mass_fraction"]:
        try:
            value = float(case.get(key))
            if value < 0.0 or value > 1.0:
                errors.append(f"{key} must be between 0 and 1.")
        except (TypeError, ValueError):
            errors.append(f"{key} must be numeric.")
    try:
        total = float(case.get("steam_mass_fraction")) + float(case.get("air_mass_fraction"))
        if abs(total - 1.0) > 1.0e-6:
            errors.append("steam_mass_fraction + air_mass_fraction must equal 1 within tolerance.")
    except (TypeError, ValueError):
        pass
    if case.get("condensation_model") != ALLOWED_CONDENSATION_MODEL:
        errors.append(f"condensation_model must be {ALLOWED_CONDENSATION_MODEL!r}.")
    return errors


def _estimate_saturation_temperature(pressure_pa: float) -> dict[str, Any]:
    p_min, t_min = SATURATION_TABLE[0]
    p_max, t_max = SATURATION_TABLE[-1]
    if pressure_pa < p_min or pressure_pa > p_max:
        return {
            "status": "block",
            "temperature_K": None,
            "note": f"pressure_pa={pressure_pa} is outside the supported saturation screening table range [{p_min}, {p_max}] Pa.",
        }
    for pressure, temperature in SATURATION_TABLE:
        if abs(pressure_pa - pressure) <= 1.0e-9:
            return {
                "status": "pass",
                "temperature_K": temperature,
                "note": "Pressure exactly matched the internal saturation screening table.",
            }
    for (p0, t0), (p1, t1) in zip(SATURATION_TABLE[:-1], SATURATION_TABLE[1:]):
        if p0 <= pressure_pa <= p1:
            alpha = (math.log(pressure_pa) - math.log(p0)) / (math.log(p1) - math.log(p0))
            return {
                "status": "pass",
                "temperature_K": t0 + alpha * (t1 - t0),
                "note": "Temperature estimated by log-pressure interpolation over a bounded screening table.",
            }
    return {"status": "block", "temperature_K": None, "note": "Saturation lookup failed closed."}


def _noncondensable_risk(air_mass_fraction: float) -> str:
    if air_mass_fraction < 0.01:
        return "low"
    if air_mass_fraction < 0.05:
        return "moderate"
    return "high"


def _resolution_class(ratio: float) -> str:
    if ratio <= 1.0:
        return "acceptable"
    if ratio <= 5.0:
        return "marginal"
    return "poor"


def _source_stiffness_risk(
    *,
    wall_subcooling_K: float,
    time_step_s: float,
    recommended_time_step_s: float,
    near_wall_resolution_ratio: float,
    air_mass_fraction: float,
) -> tuple[str, int]:
    if wall_subcooling_K <= 0.0:
        return "low", 0
    score = 0
    dt_ratio = time_step_s / max(recommended_time_step_s, 1.0e-30)
    if dt_ratio > 2.0:
        score += 1
    if dt_ratio > 10.0:
        score += 1
    if wall_subcooling_K > 25.0:
        score += 1
    if wall_subcooling_K > 80.0:
        score += 1
    if air_mass_fraction >= 0.05:
        score += 1
    elif air_mass_fraction >= 0.01:
        score += 1
    if near_wall_resolution_ratio > 1.0:
        score += 1
    if near_wall_resolution_ratio > 5.0:
        score += 1
    if score <= 1:
        return "low", score
    if score <= 3:
        return "moderate", score
    return "high", score


def _check(
    evidence_id: str,
    quantity_name: str,
    quantity_value: Any,
    quantity_units: str,
    threshold_or_rule: str,
    interpretation: str,
    confidence: str,
    source_artifact: str,
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "source_module": "steam_air_condensation",
        "source_artifact": source_artifact,
        "source_schema_version": STEAM_AIR_PASSPORT_SCHEMA_VERSION,
        "source_status": "screened",
        "quantity_name": quantity_name,
        "quantity_value": quantity_value,
        "quantity_units": quantity_units,
        "threshold_or_rule": threshold_or_rule,
        "interpretation": interpretation,
        "confidence": confidence,
        "limitations": list(DEFAULT_LIMITATIONS),
    }


def _blocked_passport(
    *,
    case: dict[str, Any],
    blocking_errors: list[str],
    source_artifact: str,
    computed_quantities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": STEAM_AIR_PASSPORT_SCHEMA_VERSION,
        "case_name": str(case.get("case_name") or "steam_air_condensation_case"),
        "status": "block",
        "summary": "Steam-air condensation screening blocked this case before Fluent handoff.",
        "inputs": case,
        "computed_quantities": computed_quantities or {},
        "checks": [],
        "fluent_hints": {},
        "warnings": [],
        "blocking_errors": blocking_errors,
        "limitations": list(DEFAULT_LIMITATIONS),
        "metadata": {
            "source_artifact": source_artifact,
            "solver_execution": "blocked_before_fluent_handoff",
        },
    }


def _summary(status: str, wall_subcooling: float, noncondensable_risk: str, source_risk: str) -> str:
    return (
        f"Steam-air condensation screening status is {status}. "
        f"Wall subcooling is {wall_subcooling:.3g} K, non-condensable risk is {noncondensable_risk}, "
        f"and source-term stiffness risk is {source_risk}."
    )


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def _windows_long_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved
