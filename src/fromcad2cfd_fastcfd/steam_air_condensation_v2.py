"""Steam-air wall-condensation v2 evidence passport for FastFluent.

This module provides engineering evidence for Fluent setup planning. It does
not solve condensation, execute Fluent, generate UDF code, or edit case/data
files.
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
from .steam_air_condensation import ALLOWED_CONDENSATION_MODEL, DEFAULT_LIMITATIONS, _estimate_saturation_temperature


STEAM_AIR_V2_CASE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_steam_air_condensation_case_v2"
STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_steam_air_condensation_passport_v2"
STEAM_AIR_V2_FLUENT_HINTS_SCHEMA_VERSION = "fromcad2cfd_fastfluent_steam_air_condensation_fluent_hints_v2"

V2_LIMITATIONS = DEFAULT_LIMITATIONS + [
    "Heat-transfer and mass-transfer estimates are engineering correlations for setup planning only.",
    "The v2 passport does not model condensation-film growth, interfacial transport, or wall-function behavior.",
    "Source-term checks validate dimensions, signs, and stiffness indicators; they do not create executable Fluent source terms.",
]


def demo_steam_air_condensation_case_v2(case_name: str = "steam_air_wall_condensation_v2_demo") -> dict[str, Any]:
    return {
        "schema_version": STEAM_AIR_V2_CASE_SCHEMA_VERSION,
        "case_name": case_name,
        "pressure_pa": 700000.0,
        "inlet_temperature_K": 438.0,
        "wall_temperature_K": 363.0,
        "steam_mass_fraction": 0.92,
        "air_mass_fraction": 0.08,
        "reference_velocity_m_s": 12.0,
        "length_scale_m": 0.05,
        "hydraulic_diameter_m": 0.05,
        "near_wall_cell_length_m": 0.0005,
        "time_step_s": 0.0005,
        "mixture_density_kg_m3": 3.8,
        "mixture_dynamic_viscosity_pa_s": 1.6e-5,
        "mixture_specific_heat_j_kg_k": 2100.0,
        "mixture_thermal_conductivity_w_m_k": 0.042,
        "steam_air_mass_diffusivity_m2_s": 2.0e-5,
        "thermal_diffusivity_m2_s": 2.0e-5,
        "latent_heat_j_kg": 2257000.0,
        "heat_transfer_area_m2": 0.02,
        "condensation_control_volume_m3": 1.0e-4,
        "condensation_model": ALLOWED_CONDENSATION_MODEL,
        "source_terms": {
            "condensation_mass_source_kg_m3_s": 1.5,
            "latent_energy_source_w_m3": 3385500.0,
            "steam_species_source_sign": "negative",
            "energy_source_sign": "positive",
        },
        "units": {
            "pressure": "Pa",
            "temperature": "K",
            "length": "m",
            "time": "s",
            "mass_source": "kg/(m^3*s)",
            "energy_source": "W/m^3",
        },
        "metadata": {
            "purpose": "public synthetic steam-air condensation v2 evidence demo",
        },
    }


def write_demo_steam_air_v2_case(
    *,
    output_dir: str | Path | None = None,
    case_name: str = "steam_air_wall_condensation_v2_demo",
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "steam_air_v2_demo" / "input")
    _ensure_dir(target_dir)
    case = demo_steam_air_condensation_case_v2(case_name=case_name)
    case_file = _write_json(target_dir / "steam_air_condensation_case_v2.json", case)
    result = AgentResult.success(
        backend="fastcfd",
        operation="write_steam_air_v2_demo",
        message="Public steam-air condensation v2 demo case written.",
        outputs={"case_file": str(case_file), "case": case},
        metadata={"output_dir": str(target_dir)},
    )
    return result.to_dict()


def read_steam_air_condensation_case_v2(path: str | Path) -> dict[str, Any]:
    with open(_windows_long_path(Path(path)), "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_steam_air_condensation_v2_case_file(
    case_file: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "steam_air_condensation_v2" / "passport")
    _ensure_dir(target_dir)
    try:
        case_path = Path(case_file)
        case = read_steam_air_condensation_case_v2(case_path)
        passport = build_steam_air_condensation_passport_v2(case, source_artifact=str(case_path))
        hints = build_steam_air_fluent_hints_v2(passport)
        artifacts = {
            "passport": str(_write_json(target_dir / "steam_air_condensation_passport_v2.json", passport)),
            "fluent_hints": str(_write_json(target_dir / "steam_air_condensation_fluent_hints_v2.json", hints)),
            "report": str(_write_text(target_dir / "steam_air_condensation_report_v2.md", steam_air_condensation_report_v2(passport, hints))),
        }
        result_status = "success" if passport["status"] in {"pass", "warn"} else "failed"
        if result_status == "success":
            result = AgentResult.success(
                backend="fastcfd",
                operation="validate_steam_air_condensation_v2",
                message="Steam-air condensation v2 passport generated.",
                outputs={"artifacts": artifacts, "passport": passport, "fluent_hints": hints},
                metadata={"output_dir": str(target_dir), "case_file": str(case_file)},
            )
        else:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="validate_steam_air_condensation_v2",
                message="Steam-air condensation v2 passport blocked the case.",
                errors=passport.get("blocking_errors", []),
                metadata={"output_dir": str(target_dir), "case_file": str(case_file)},
            )
            result.outputs.update({"artifacts": artifacts, "passport": passport, "fluent_hints": hints})
        return result.to_dict()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        blocked = _blocked_passport_v2(
            case={"case_name": Path(case_file).stem if case_file else "unknown"},
            blocking_errors=[str(exc)],
            source_artifact=str(case_file),
        )
        hints = build_steam_air_fluent_hints_v2(blocked)
        artifacts = {
            "passport": str(_write_json(target_dir / "steam_air_condensation_passport_v2.json", blocked)),
            "fluent_hints": str(_write_json(target_dir / "steam_air_condensation_fluent_hints_v2.json", hints)),
            "report": str(_write_text(target_dir / "steam_air_condensation_report_v2.md", steam_air_condensation_report_v2(blocked, hints))),
        }
        failure = AgentResult.failed(
            backend="fastcfd",
            operation="validate_steam_air_condensation_v2",
            message="Steam-air condensation v2 passport generation failed closed.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir), "case_file": str(case_file)},
        )
        failure.outputs.update({"artifacts": artifacts, "passport": blocked, "fluent_hints": hints})
        return failure.to_dict()


def run_steam_air_v2_demo(*, output_dir: str | Path) -> dict[str, Any]:
    target = Path(output_dir)
    _ensure_dir(target)
    case = demo_steam_air_condensation_case_v2()
    case_file = _write_json(target / "steam_air_condensation_case_v2.json", case)
    passport = build_steam_air_condensation_passport_v2(case, source_artifact=str(case_file))
    hints = build_steam_air_fluent_hints_v2(passport)
    passport_file = _write_json(target / "steam_air_condensation_passport_v2.json", passport)
    hints_file = _write_json(target / "steam_air_condensation_fluent_hints_v2.json", hints)
    report_file = _write_text(target / "steam_air_condensation_report_v2.md", steam_air_condensation_report_v2(passport, hints))

    from .fluent_patch_compiler import compile_solver_plan_patch_from_passport, write_solver_plan_patch_bundle

    patch = compile_solver_plan_patch_from_passport(passport)
    patch_result = write_solver_plan_patch_bundle(patch, output=target / "solver_plan_patch.json")
    artifacts = {
        "case_file": str(case_file),
        "passport": str(passport_file),
        "fluent_hints": str(hints_file),
        "solver_plan_patch": patch_result["outputs"]["artifacts"]["solver_plan_patch"],
        "solver_plan_patch_report": patch_result["outputs"]["artifacts"]["solver_plan_patch_report"],
        "report": str(report_file),
    }
    result = AgentResult.success(
        backend="fastcfd",
        operation="steam_air_v2_demo",
        message="Steam-air condensation v2 demo generated.",
        outputs={"artifacts": artifacts, "passport": passport, "fluent_hints": hints, "patch": patch, "patch_result": patch_result},
        metadata={"output_dir": str(target), "patch_status": patch.get("status")},
    )
    if patch_result.get("status") != "success":
        result.status = "partial"
        result.message = "Steam-air v2 demo generated, but the solver-plan patch is blocked."
    return result.to_dict()


def build_steam_air_condensation_passport_v2(case: dict[str, Any], *, source_artifact: str = "inline_case") -> dict[str, Any]:
    errors = _validate_case_v2(case)
    if errors:
        return _blocked_passport_v2(case=case, blocking_errors=errors, source_artifact=source_artifact)

    pressure_pa = float(case["pressure_pa"])
    saturation = _estimate_saturation_temperature(pressure_pa)
    if saturation["status"] == "block":
        return _blocked_passport_v2(
            case=case,
            blocking_errors=[saturation["note"]],
            source_artifact=source_artifact,
            computed_quantities={"pressure_pa": pressure_pa},
        )

    warnings: list[str] = []
    if saturation["status"] == "warn":
        warnings.append(saturation["note"])

    tsat = float(saturation["temperature_K"])
    wall_temperature = float(case["wall_temperature_K"])
    inlet_temperature = float(case["inlet_temperature_K"])
    wall_subcooling = tsat - wall_temperature
    delta_t = max(wall_subcooling, 0.0)
    rho = float(case["mixture_density_kg_m3"])
    velocity = float(case["reference_velocity_m_s"])
    length = float(case["length_scale_m"])
    hydraulic_diameter = float(case["hydraulic_diameter_m"])
    mu = float(case["mixture_dynamic_viscosity_pa_s"])
    cp = float(case["mixture_specific_heat_j_kg_k"])
    conductivity = float(case["mixture_thermal_conductivity_w_m_k"])
    diffusivity = float(case["steam_air_mass_diffusivity_m2_s"])
    latent_heat = float(case["latent_heat_j_kg"])
    dt = float(case["time_step_s"])
    area = float(case["heat_transfer_area_m2"])
    near_wall = float(case["near_wall_cell_length_m"])
    alpha = float(case["thermal_diffusivity_m2_s"])

    reynolds = rho * velocity * hydraulic_diameter / mu
    prandtl = mu * cp / conductivity
    peclet = reynolds * prandtl
    jakob = cp * delta_t / latent_heat
    stefan = cp * delta_t / latent_heat
    flow_regime = _flow_regime(reynolds)
    heat_transfer = _heat_transfer_estimate(reynolds, prandtl, conductivity, hydraulic_diameter, delta_t, area, flow_regime)
    mass_transfer = _mass_transfer_estimate(reynolds, rho, mu, diffusivity, hydraulic_diameter, float(case["air_mass_fraction"]), flow_regime)
    source_checks = _source_term_checks(case, rho=rho, cp=cp, latent_heat=latent_heat, wall_subcooling=max(delta_t, 1.0), time_step_s=dt)
    thermal_depth = math.sqrt(alpha * dt)
    near_wall_ratio = near_wall / max(thermal_depth, 1.0e-30)
    diffusion_time = near_wall * near_wall / max(alpha, 1.0e-30)
    convective_time = length / max(velocity, 1.0e-12)
    recommended_dt = min(dt, 0.2 * diffusion_time, 0.02 * convective_time)

    if inlet_temperature < tsat - 2.0:
        warnings.append("Inlet temperature is below the estimated saturation temperature; inlet steam state requires review.")
    if wall_subcooling <= 0.0:
        warnings.append("Wall is not below the estimated saturation temperature; condensation is unlikely in this simplified check.")
    if mass_transfer["non_condensable_layer_risk"] in {"moderate", "high"}:
        warnings.append(f"Non-condensable mass-transfer resistance risk is {mass_transfer['non_condensable_layer_risk']}.")
    if source_checks["source_term_stiffness_level"] in {"moderate", "high"}:
        warnings.append(f"Condensation source-term stiffness level is {source_checks['source_term_stiffness_level']}.")
    if source_checks["latent_heat_consistency"] != "pass":
        warnings.append("Condensation mass and energy source terms do not match latent heat within tolerance.")
    if source_checks["source_term_sign_check"] != "pass":
        warnings.append("Condensation source-term sign convention requires review.")

    computed = {
        "estimated_saturation_temperature_K": tsat,
        "saturation_estimate_method": "log-pressure interpolation over internal water saturation screening table",
        "saturation_estimate_validity_note": saturation["note"],
        "inlet_superheat_K": inlet_temperature - tsat,
        "wall_subcooling_K": wall_subcooling,
        "reynolds_number": reynolds,
        "flow_regime": flow_regime,
        "prandtl_number": prandtl,
        "peclet_number": peclet,
        "jakob_number": jakob,
        "stefan_number": stefan,
        "thermal_penetration_depth_m": thermal_depth,
        "near_wall_resolution_ratio": near_wall_ratio,
        "near_wall_diffusion_time_scale_s": diffusion_time,
        "convective_time_scale_s": convective_time,
        "recommended_time_step_s": recommended_dt,
        **heat_transfer,
        **mass_transfer,
        **source_checks,
    }

    checks = _build_checks_v2(case, computed, source_artifact)
    blocking_errors: list[str] = []
    if source_checks["source_term_dimension_check"] != "pass":
        blocking_errors.append("Source-term dimensions are invalid or non-finite.")
    if source_checks["source_term_stiffness_level"] == "extreme":
        blocking_errors.append("Source-term stiffness is extreme; reduce time step or source magnitude before Fluent handoff.")
    status = "block" if blocking_errors else ("warn" if warnings else "pass")
    passport = {
        "schema_version": STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION,
        "case_name": str(case.get("case_name") or "steam_air_condensation_v2_case"),
        "status": status,
        "summary": _summary_v2(status, flow_regime, wall_subcooling, mass_transfer["non_condensable_layer_risk"], source_checks["source_term_stiffness_level"]),
        "inputs": case,
        "computed_quantities": computed,
        "correlations": {
            "heat_transfer": heat_transfer["heat_transfer_correlation"],
            "mass_transfer": mass_transfer["mass_transfer_correlation"],
        },
        "checks": checks,
        "fluent_hints": {},
        "warnings": warnings,
        "blocking_errors": blocking_errors,
        "limitations": list(V2_LIMITATIONS),
        "metadata": {"source_artifact": source_artifact, "solver_execution": "not_attempted_passport_only"},
    }
    passport["fluent_hints"] = build_steam_air_fluent_hints_v2(passport)
    return passport


def build_steam_air_fluent_hints_v2(passport: dict[str, Any]) -> dict[str, Any]:
    computed = passport.get("computed_quantities", {})
    source = computed.get("source_term_controls", {})
    turbulence_model = _recommended_turbulence_model(str(computed.get("flow_regime")))
    hints = {
        "schema_version": STEAM_AIR_V2_FLUENT_HINTS_SCHEMA_VERSION,
        "case_name": passport.get("case_name"),
        "status": passport.get("status"),
        "recommended_physics": {
            "pressure_based_solver": True,
            "transient": True,
            "energy": True,
            "species_transport": True,
            "turbulence_model": turbulence_model,
            "material_model": "ideal-gas-mixture",
            "mixture_species": ["h2o", "o2", "n2"],
            "condensation_source_term": ALLOWED_CONDENSATION_MODEL,
        },
        "recommended_transient_controls": {
            "initial_time_step_s": computed.get("recommended_time_step_s"),
            "adaptive_time_step": True,
            "max_courant_number": 1.0,
        },
        "recommended_source_term_controls": {
            "source_ramping": True,
            "source_clamp": True,
            "temperature_bounds_K": source.get("temperature_bounds_K"),
            "species_bounds": source.get("species_bounds"),
            "source_integral_monitor": True,
            "latent_heat_j_kg": passport.get("inputs", {}).get("latent_heat_j_kg"),
        },
        "recommended_monitors": [
            "wall_heat_transfer_rate",
            "wall_temperature",
            "steam_mass_fraction",
            "air_mass_fraction",
            "max_temperature",
            "energy_balance",
            "source_term_integral",
        ],
        "recommended_postprocessing": [
            "wall_heat_flux_summary",
            "species_boundary_layer_summary",
            "condensation_source_integral_history",
            "mass_energy_balance_report",
        ],
        "hints": [
            {
                "category": "steam_air_v2_physics",
                "recommendation": "Enable transient energy and species transport for steam-air condensation setup review.",
                "evidence": ["steam_air_v2_reynolds_number", "steam_air_v2_species_consistency"],
            },
            {
                "category": "steam_air_v2_heat_transfer",
                "recommendation": "Use HTC and wall heat-transfer-rate monitors as advisory setup evidence.",
                "evidence": ["steam_air_v2_heat_transfer_estimate"],
            },
            {
                "category": "steam_air_v2_mass_transfer",
                "recommendation": "Review non-condensable mass-transfer resistance and species boundary-layer outputs.",
                "evidence": ["steam_air_v2_mass_transfer_resistance"],
            },
            {
                "category": "steam_air_v2_source_terms",
                "recommendation": "Use source ramping, source clamping, temperature bounds, species bounds, and source integral monitors.",
                "evidence": ["steam_air_v2_source_term_dimension_check", "steam_air_v2_source_term_sign_check", "steam_air_v2_source_term_stiffness"],
            },
        ],
        "warnings": list(passport.get("warnings", [])),
        "blocking_errors": list(passport.get("blocking_errors", [])),
        "limitations": list(passport.get("limitations", V2_LIMITATIONS)),
        "metadata": {
            "source_passport_schema_version": passport.get("schema_version"),
            "solver_execution": "not_attempted_hints_only",
        },
    }
    if passport.get("status") == "block":
        hints["recommended_source_term_controls"]["fluent_execution"] = "blocked_until_passport_errors_are_resolved"
    return hints


def steam_air_condensation_report_v2(passport: dict[str, Any], hints: dict[str, Any]) -> str:
    computed = passport.get("computed_quantities", {})
    lines = [
        "# Steam-Air Condensation v2 Physics Passport",
        "",
        f"Case name: `{passport.get('case_name')}`",
        f"Status: `{passport.get('status')}`",
        "",
        "## Dimensionless Groups",
        "",
        f"- Reynolds number: `{computed.get('reynolds_number')}`",
        f"- Flow regime: `{computed.get('flow_regime')}`",
        f"- Prandtl number: `{computed.get('prandtl_number')}`",
        f"- Peclet number: `{computed.get('peclet_number')}`",
        f"- Jakob number: `{computed.get('jakob_number')}`",
        f"- Stefan number: `{computed.get('stefan_number')}`",
        "",
        "## Heat Transfer Estimate",
        "",
        f"- Nusselt number: `{computed.get('estimated_nusselt_number')}`",
        f"- HTC: `{computed.get('estimated_htc_W_m2K')}` W/(m^2*K)",
        f"- Heat flux: `{computed.get('estimated_heat_flux_W_m2')}` W/m^2",
        f"- Heat transfer rate: `{computed.get('estimated_heat_transfer_rate_W')}` W",
        f"- Correlation: `{computed.get('heat_transfer_correlation', {}).get('correlation_name')}`",
        "",
        "## Non-Condensable Resistance",
        "",
        f"- Schmidt number: `{computed.get('schmidt_number')}`",
        f"- Sherwood number: `{computed.get('sherwood_number')}`",
        f"- Mass-transfer coefficient: `{computed.get('mass_transfer_coefficient_m_s')}` m/s",
        f"- Mass-transfer resistance: `{computed.get('mass_transfer_resistance_s_m')}` s/m",
        f"- Layer risk: `{computed.get('non_condensable_layer_risk')}`",
        "",
        "## Source-Term Checks",
        "",
        f"- Dimension check: `{computed.get('source_term_dimension_check')}`",
        f"- Sign check: `{computed.get('source_term_sign_check')}`",
        f"- Latent heat consistency: `{computed.get('latent_heat_consistency')}`",
        f"- Source stiffness level: `{computed.get('source_term_stiffness_level')}`",
        f"- Estimated source temperature increment per step: `{computed.get('source_temperature_increment_K_per_step')}` K",
        "",
        "## Fluent Setup Recommendations",
        "",
        f"- Energy: `{hints.get('recommended_physics', {}).get('energy')}`",
        f"- Species transport: `{hints.get('recommended_physics', {}).get('species_transport')}`",
        f"- Turbulence model: `{hints.get('recommended_physics', {}).get('turbulence_model')}`",
        f"- Initial time step: `{hints.get('recommended_transient_controls', {}).get('initial_time_step_s')}` s",
        f"- Source ramping: `{hints.get('recommended_source_term_controls', {}).get('source_ramping')}`",
        f"- Source clamp: `{hints.get('recommended_source_term_controls', {}).get('source_clamp')}`",
        "",
        "## Warnings",
        "",
    ]
    lines.extend(f"- {item}" for item in passport.get("warnings", [])) if passport.get("warnings") else lines.append("- None")
    lines.extend(["", "## Blocking Errors", ""])
    lines.extend(f"- {item}" for item in passport.get("blocking_errors", [])) if passport.get("blocking_errors") else lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in passport.get("limitations", V2_LIMITATIONS))
    lines.extend(
        [
            "",
            "## Reviewer Checklist",
            "",
            "- Confirm the heat-transfer correlation is appropriate for the final geometry and flow regime.",
            "- Confirm the mass-transfer resistance estimate against the final near-wall mesh.",
            "- Confirm source-term dimensions, latent heat consistency, and sign convention.",
            "- Confirm temperature and species bounds before any executable Fluent adapter consumes the patch.",
            "- Confirm all monitors are available in the final Fluent setup.",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_case_v2(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(case, dict):
        return ["Case payload must be an object."]
    dangerous = find_dangerous_keys(case)
    if dangerous:
        errors.append("Dangerous key names found: " + ", ".join(dangerous))
    if case.get("schema_version") != STEAM_AIR_V2_CASE_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {case.get('schema_version')!r}")
    required_positive = [
        "pressure_pa",
        "inlet_temperature_K",
        "wall_temperature_K",
        "length_scale_m",
        "hydraulic_diameter_m",
        "near_wall_cell_length_m",
        "time_step_s",
        "mixture_density_kg_m3",
        "mixture_dynamic_viscosity_pa_s",
        "mixture_specific_heat_j_kg_k",
        "mixture_thermal_conductivity_w_m_k",
        "steam_air_mass_diffusivity_m2_s",
        "thermal_diffusivity_m2_s",
        "latent_heat_j_kg",
        "heat_transfer_area_m2",
        "condensation_control_volume_m3",
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
    source_terms = case.get("source_terms")
    if not isinstance(source_terms, dict):
        errors.append("source_terms must be an object.")
    else:
        for key in ["condensation_mass_source_kg_m3_s", "latent_energy_source_w_m3"]:
            try:
                value = float(source_terms.get(key))
                if value < 0.0 or not math.isfinite(value):
                    errors.append(f"source_terms.{key} must be finite and >= 0.")
            except (TypeError, ValueError):
                errors.append(f"source_terms.{key} must be numeric.")
        if source_terms.get("steam_species_source_sign") not in {"negative", "sink"}:
            errors.append("source_terms.steam_species_source_sign must be 'negative' or 'sink'.")
        if source_terms.get("energy_source_sign") not in {"positive", "release"}:
            errors.append("source_terms.energy_source_sign must be 'positive' or 'release'.")
    if case.get("condensation_model") != ALLOWED_CONDENSATION_MODEL:
        errors.append(f"condensation_model must be {ALLOWED_CONDENSATION_MODEL!r}.")
    return errors


def _build_checks_v2(case: dict[str, Any], computed: dict[str, Any], source_artifact: str) -> list[dict[str, Any]]:
    return [
        _check("steam_air_v2_reynolds_number", "reynolds_number", computed["reynolds_number"], "1", "Re = rho * U * Dh / mu", f"Flow regime classified as {computed['flow_regime']}.", "medium", source_artifact),
        _check("steam_air_v2_prandtl_number", "prandtl_number", computed["prandtl_number"], "1", "Pr = mu * cp / k", "Thermal diffusivity ratio for heat-transfer setup screening.", "medium", source_artifact),
        _check("steam_air_v2_peclet_number", "peclet_number", computed["peclet_number"], "1", "Pe = Re * Pr", "Convective thermal transport indicator.", "medium", source_artifact),
        _check("steam_air_v2_jakob_number", "jakob_number", computed["jakob_number"], "1", "Ja = cp * (Tsat - Twall) / latent_heat", "Sensible-to-latent heat scale for wall condensation screening.", "medium", source_artifact),
        _check("steam_air_v2_stefan_number", "stefan_number", computed["stefan_number"], "1", "Ste = cp * deltaT / latent_heat", "Condensation thermal driving scale for source-term review.", "medium", source_artifact),
        _check("steam_air_v2_heat_transfer_estimate", "estimated_htc_W_m2K", computed["estimated_htc_W_m2K"], "W/(m^2*K)", "Nu correlation -> h = Nu * k / Dh", "Estimated HTC is advisory for Fluent setup and monitor planning.", "low", source_artifact),
        _check("steam_air_v2_mass_transfer_resistance", "mass_transfer_resistance_s_m", computed["mass_transfer_resistance_s_m"], "s/m", "Sh correlation -> hm = Sh * D / Dh; resistance = 1 / hm", f"Non-condensable layer risk is {computed['non_condensable_layer_risk']}.", "low", source_artifact),
        _check("steam_air_v2_source_term_dimension_check", "source_term_dimension_check", computed["source_term_dimension_check"], "class", "kg/(m^3*s) and W/m^3 source values must be finite and non-negative", "Source-term dimensions are screened before any Fluent handoff.", "high", source_artifact),
        _check("steam_air_v2_source_term_sign_check", "source_term_sign_check", computed["source_term_sign_check"], "class", "steam source must be a sink; energy source must be a positive release", "Source sign convention is screened before patch generation.", "high", source_artifact),
        _check("steam_air_v2_source_term_stiffness", "source_term_stiffness_level", computed["source_term_stiffness_level"], "class", "qdot * dt / (rho * cp * max(wall_subcooling, 1 K))", "Source stiffness controls ramping, clamping, and time-step conservatism.", "medium", source_artifact),
        _check("steam_air_v2_species_consistency", "steam_plus_air_mass_fraction_sum", float(case["steam_mass_fraction"]) + float(case["air_mass_fraction"]), "1", "steam_mass_fraction + air_mass_fraction = 1", "Species closure is required for steam-air setup.", "high", source_artifact),
    ]


def _heat_transfer_estimate(reynolds: float, prandtl: float, conductivity: float, hydraulic_diameter: float, delta_t: float, area: float, flow_regime: str) -> dict[str, Any]:
    if flow_regime == "laminar":
        nusselt = 3.66
        correlation = {
            "correlation_name": "constant-wall-temperature laminar internal-flow screening",
            "validity_range": "Re < 2300, fully developed internal flow, first-pass screening only",
            "limitations": ["Entrance effects, condensation-film effects, buoyancy, and geometry-specific corrections are not included."],
        }
    elif flow_regime == "turbulent":
        nusselt = 0.023 * reynolds**0.8 * prandtl**0.4
        correlation = {
            "correlation_name": "Dittus-Boelter turbulent internal-flow screening",
            "validity_range": "Re > 10000, 0.6 < Pr < 160, smooth tube analogy",
            "limitations": ["Used only as an HTC scale estimate; not validated for final device geometry or condensation films."],
        }
    else:
        laminar_nu = 3.66
        turbulent_nu = 0.023 * max(reynolds, 1.0) ** 0.8 * prandtl**0.4
        blend = min(1.0, max(0.0, (reynolds - 2300.0) / (10000.0 - 2300.0)))
        nusselt = (1.0 - blend) * laminar_nu + blend * turbulent_nu
        correlation = {
            "correlation_name": "linear transitional blend between laminar constant Nu and Dittus-Boelter",
            "validity_range": "2300 <= Re <= 10000, advisory transition blend only",
            "limitations": ["Transitional heat transfer is uncertain; reviewer confirmation is required."],
        }
    htc = nusselt * conductivity / hydraulic_diameter
    heat_flux = htc * delta_t
    return {
        "estimated_nusselt_number": nusselt,
        "estimated_htc_W_m2K": htc,
        "estimated_heat_flux_W_m2": heat_flux,
        "estimated_heat_transfer_rate_W": heat_flux * area,
        "heat_transfer_correlation": correlation,
    }


def _mass_transfer_estimate(reynolds: float, rho: float, mu: float, diffusivity: float, hydraulic_diameter: float, air_mass_fraction: float, flow_regime: str) -> dict[str, Any]:
    schmidt = mu / max(rho * diffusivity, 1.0e-30)
    if flow_regime == "laminar":
        sherwood = 3.66
        correlation = {
            "correlation_name": "laminar constant Sherwood screening",
            "validity_range": "Re < 2300, fully developed internal-flow analogy",
            "limitations": ["Does not resolve the actual non-condensable boundary layer."],
        }
    elif flow_regime == "turbulent":
        sherwood = 0.023 * reynolds**0.83 * schmidt**0.44
        correlation = {
            "correlation_name": "Dittus-Boelter-style turbulent heat/mass-transfer analogy",
            "validity_range": "Turbulent internal-flow analogy, first-pass screening only",
            "limitations": ["Mass-transfer resistance is advisory and must be confirmed in Fluent."],
        }
    else:
        laminar_sh = 3.66
        turbulent_sh = 0.023 * max(reynolds, 1.0) ** 0.83 * schmidt**0.44
        blend = min(1.0, max(0.0, (reynolds - 2300.0) / (10000.0 - 2300.0)))
        sherwood = (1.0 - blend) * laminar_sh + blend * turbulent_sh
        correlation = {
            "correlation_name": "linear transitional Sherwood blend",
            "validity_range": "2300 <= Re <= 10000, advisory transition blend only",
            "limitations": ["Transitional mass transfer is uncertain; reviewer confirmation is required."],
        }
    coefficient = sherwood * diffusivity / hydraulic_diameter
    resistance = 1.0 / max(coefficient, 1.0e-30)
    risk = _noncondensable_resistance_risk(air_mass_fraction, resistance)
    return {
        "schmidt_number": schmidt,
        "sherwood_number": sherwood,
        "mass_transfer_coefficient_m_s": coefficient,
        "mass_transfer_resistance_s_m": resistance,
        "non_condensable_layer_risk": risk,
        "mass_transfer_resistance": risk,
        "mass_transfer_correlation": correlation,
    }


def _source_term_checks(case: dict[str, Any], *, rho: float, cp: float, latent_heat: float, wall_subcooling: float, time_step_s: float) -> dict[str, Any]:
    source_terms = case.get("source_terms", {})
    mass_source = float(source_terms.get("condensation_mass_source_kg_m3_s", 0.0))
    energy_source = float(source_terms.get("latent_energy_source_w_m3", 0.0))
    dimension_check = "pass" if math.isfinite(mass_source) and math.isfinite(energy_source) and mass_source >= 0.0 and energy_source >= 0.0 else "block"
    expected_energy = mass_source * latent_heat
    if mass_source == 0.0 and energy_source == 0.0:
        consistency = "pass"
        latent_ratio = 1.0
    else:
        latent_ratio = energy_source / max(expected_energy, 1.0e-30)
        consistency = "pass" if 0.8 <= latent_ratio <= 1.2 else "warn"
    sign_check = "pass" if source_terms.get("steam_species_source_sign") in {"negative", "sink"} and source_terms.get("energy_source_sign") in {"positive", "release"} else "warn"
    temp_increment = energy_source * time_step_s / max(rho * cp, 1.0e-30)
    stiffness_ratio = temp_increment / max(wall_subcooling, 1.0)
    if stiffness_ratio < 0.05:
        stiffness = "low"
    elif stiffness_ratio < 0.25:
        stiffness = "moderate"
    elif stiffness_ratio < 1.0:
        stiffness = "high"
    else:
        stiffness = "extreme"
    return {
        "source_term_dimension_check": dimension_check,
        "source_term_sign_check": sign_check,
        "latent_heat_consistency": consistency,
        "latent_heat_energy_ratio": latent_ratio,
        "source_temperature_increment_K_per_step": temp_increment,
        "source_stiffness_ratio": stiffness_ratio,
        "source_term_stiffness_level": stiffness,
        "source_term_controls": {
            "source_ramping": True,
            "source_clamp": True,
            "temperature_bounds_K": {"min": 250.0, "max": 800.0, "review_required": True},
            "species_bounds": {"min": 0.0, "max": 1.0, "review_required": True},
            "source_integral_monitor": True,
        },
    }


def _flow_regime(reynolds: float) -> str:
    if reynolds < 2300.0:
        return "laminar"
    if reynolds < 10000.0:
        return "transitional"
    return "turbulent"


def _recommended_turbulence_model(flow_regime: str) -> str:
    if flow_regime == "laminar":
        return "laminar"
    if flow_regime == "turbulent":
        return "k-omega-sst-review-required"
    return "transition-review-required"


def _noncondensable_resistance_risk(air_mass_fraction: float, resistance: float) -> str:
    if air_mass_fraction >= 0.05 or resistance > 500.0:
        return "high"
    if air_mass_fraction >= 0.01 or resistance > 100.0:
        return "moderate"
    return "low"


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
        "source_module": "steam_air_condensation_v2",
        "source_artifact": source_artifact,
        "source_schema_version": STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION,
        "source_status": "screened",
        "quantity_name": quantity_name,
        "quantity_value": quantity_value,
        "quantity_units": quantity_units,
        "threshold_or_rule": threshold_or_rule,
        "interpretation": interpretation,
        "confidence": confidence,
        "limitations": list(V2_LIMITATIONS),
    }


def _blocked_passport_v2(
    *,
    case: dict[str, Any],
    blocking_errors: list[str],
    source_artifact: str,
    computed_quantities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION,
        "case_name": str(case.get("case_name") or "steam_air_condensation_v2_case"),
        "status": "block",
        "summary": "Steam-air condensation v2 screening blocked this case before Fluent handoff.",
        "inputs": case,
        "computed_quantities": computed_quantities or {},
        "correlations": {},
        "checks": [],
        "fluent_hints": {},
        "warnings": [],
        "blocking_errors": blocking_errors,
        "limitations": list(V2_LIMITATIONS),
        "metadata": {"source_artifact": source_artifact, "solver_execution": "blocked_before_fluent_handoff"},
    }


def _summary_v2(status: str, flow_regime: str, wall_subcooling: float, noncondensable_risk: str, source_stiffness: str) -> str:
    return (
        f"Steam-air condensation v2 screening status is {status}. "
        f"Flow regime is {flow_regime}, wall subcooling is {wall_subcooling:.3g} K, "
        f"non-condensable resistance risk is {noncondensable_risk}, and source stiffness is {source_stiffness}."
    )


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    _ensure_dir(path.parent)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    return path


def _write_text(path: Path, text: str) -> Path:
    _ensure_dir(path.parent)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def _ensure_dir(path: Path) -> None:
    os.makedirs(_windows_long_path(path), exist_ok=True)


def _windows_long_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved
