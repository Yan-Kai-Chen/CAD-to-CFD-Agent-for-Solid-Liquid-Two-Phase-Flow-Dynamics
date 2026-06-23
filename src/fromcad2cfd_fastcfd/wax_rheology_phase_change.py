"""Wax rheology and phase-change readiness passport for FastFluent.

This module converts wax material and thermal properties into structured setup
evidence for later Fluent review. It does not execute Fluent, call PyFluent,
generate UDF source, or solve a production phase-change/dewaxing model.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .paths import unique_path
from .solver_plan_patch import PatchEvidence, PatchOperation, SolverPlanPatch, find_dangerous_keys


WAX_RHEOLOGY_CASE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_wax_rheology_phase_change_case_v1"
WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_wax_rheology_phase_change_passport_v1"
WAX_RHEOLOGY_HINTS_SCHEMA_VERSION = "fromcad2cfd_fastfluent_wax_rheology_phase_change_fluent_hints_v1"

SUPPORTED_VISCOSITY_MODELS = {"constant", "arrhenius", "review-required"}
SUPPORTED_PHASE_CHANGE_MODELS = {"none", "effective_heat_capacity_review", "enthalpy_porosity_review", "source_term_review"}
GAS_CONSTANT_J_MOL_K = 8.314462618
TINY = 1.0e-30

LIMITATIONS = [
    "This passport is an engineering readiness gate.",
    "It is not a production phase-change solver.",
    "It does not validate final dewaxing behavior.",
    "It does not replace Fluent or ProCAST.",
    "It does not generate executable UDF code.",
    "It does not launch Fluent or modify Fluent case/data files.",
]


def create_demo_wax_rheology_case(case_name: str = "wax_arrhenius_softening_demo") -> dict[str, Any]:
    """Return a public synthetic wax case inspired by thesis-side values."""

    return {
        "schema_version": WAX_RHEOLOGY_CASE_SCHEMA_VERSION,
        "case_name": case_name,
        "temperature_min_K": 353.15,
        "temperature_max_K": 373.15,
        "reference_temperature_K": 355.15,
        "softening_temperature_50_K": 330.18,
        "softening_temperature_90_K": 341.47,
        "tan_delta_peak_temperature_K": 339.22,
        "storage_modulus_low_temp_Pa": 1.1655e9,
        "storage_modulus_high_temp_Pa": 3.89e6,
        "storage_modulus_low_temp_K": 298.15,
        "storage_modulus_high_temp_K": 343.15,
        "viscosity_model": "arrhenius",
        "arrhenius_A": -46.7601,
        "arrhenius_B_K": 16488.4,
        "density_solid_kg_m3": 900.0,
        "density_liquid_kg_m3": 780.0,
        "specific_heat_J_kgK": 2200.0,
        "thermal_conductivity_W_mK": 0.25,
        "latent_heat_J_kg": 200000.0,
        "melting_temperature_min_K": 330.15,
        "melting_temperature_max_K": 345.15,
        "length_scale_m": 0.01,
        "cell_size_m": 0.0005,
        "time_step_s": 0.01,
        "heating_rate_K_s": 2.0,
        "phase_change_model": "source_term_review",
        "units": {
            "temperature": "K",
            "viscosity": "Pa*s",
            "density": "kg/m^3",
            "specific_heat": "J/(kg*K)",
            "thermal_conductivity": "W/(m*K)",
            "latent_heat": "J/kg",
            "length": "m",
            "time": "s",
        },
        "metadata": {
            "public_safe": True,
            "purpose": "public synthetic wax rheology and phase-change readiness demo",
            "material_constants_are_demo_values": True,
        },
    }


def write_demo_wax_rheology_case(
    *,
    output_dir: str | Path | None = None,
    case_name: str = "wax_arrhenius_softening_demo",
) -> dict[str, Any]:
    target = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "wax_rheology_phase_change_demo")
    _ensure_dir(target)
    case = create_demo_wax_rheology_case(case_name=case_name)
    case_file = _write_json(target / "wax_rheology_phase_change_case.json", case)
    result = AgentResult.success(
        backend="fastcfd",
        operation="write_wax_rheology_demo",
        message="Public wax rheology / phase-change demo case written.",
        outputs={"case_file": str(case_file), "case": case},
        metadata={"output_dir": str(target), "fluent_launched": False},
    )
    return result.to_dict()


def read_wax_rheology_phase_change_case(path: str | Path) -> dict[str, Any]:
    with open(_windows_long_path(Path(path)), "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_wax_rheology_case(case: dict[str, Any]) -> dict[str, Any]:
    """Validate a wax case and return a fail-closed validation artifact."""

    errors = _validate_case_payload(case)
    return {
        "status": "block" if errors else "pass",
        "passed": not errors,
        "errors": errors,
        "warnings": [],
    }


def validate_wax_rheology_phase_change_case_file(
    case_file: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    target = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "wax_rheology_phase_change_demo" / "passport")
    _ensure_dir(target)
    try:
        case_path = Path(case_file)
        case = read_wax_rheology_phase_change_case(case_path)
        passport = build_wax_rheology_phase_change_passport(case, source_artifact=str(case_path))
        hints = build_wax_rheology_phase_change_fluent_hints(passport)
        artifacts = {
            "passport": str(_write_json(target / "wax_rheology_phase_change_passport.json", passport)),
            "fluent_hints": str(_write_json(target / "wax_rheology_phase_change_fluent_hints.json", hints)),
            "report": str(_write_text(target / "wax_rheology_phase_change_report.md", wax_rheology_phase_change_report(passport, hints))),
        }
        if passport["status"] in {"pass", "warn"}:
            result = AgentResult.success(
                backend="fastcfd",
                operation="validate_wax_rheology_phase_change",
                message="Wax rheology / phase-change passport generated.",
                outputs={"artifacts": artifacts, "passport": passport, "fluent_hints": hints},
                metadata={"output_dir": str(target), "case_file": str(case_file), "fluent_launched": False},
            )
        else:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="validate_wax_rheology_phase_change",
                message="Wax rheology / phase-change passport blocked the case.",
                errors=passport.get("blocking_errors", []),
                metadata={"output_dir": str(target), "case_file": str(case_file), "fluent_launched": False},
            )
            result.outputs.update({"artifacts": artifacts, "passport": passport, "fluent_hints": hints})
        return result.to_dict()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        blocked = _blocked_passport(
            case={"case_name": Path(case_file).stem if case_file else "unknown"},
            blocking_errors=[str(exc)],
            source_artifact=str(case_file),
        )
        hints = build_wax_rheology_phase_change_fluent_hints(blocked)
        artifacts = {
            "passport": str(_write_json(target / "wax_rheology_phase_change_passport.json", blocked)),
            "fluent_hints": str(_write_json(target / "wax_rheology_phase_change_fluent_hints.json", hints)),
            "report": str(_write_text(target / "wax_rheology_phase_change_report.md", wax_rheology_phase_change_report(blocked, hints))),
        }
        failure = AgentResult.failed(
            backend="fastcfd",
            operation="validate_wax_rheology_phase_change",
            message="Wax rheology / phase-change passport generation failed closed.",
            errors=[str(exc)],
            metadata={"output_dir": str(target), "case_file": str(case_file), "fluent_launched": False},
        )
        failure.outputs.update({"artifacts": artifacts, "passport": blocked, "fluent_hints": hints})
        return failure.to_dict()


def build_wax_rheology_phase_change_passport(case: dict[str, Any], *, source_artifact: str = "inline_case") -> dict[str, Any]:
    errors = _validate_case_payload(case)
    if errors:
        return _blocked_passport(case=case, blocking_errors=errors, source_artifact=source_artifact)

    try:
        computed = compute_wax_rheology_phase_change_quantities(case)
    except (OverflowError, ValueError) as exc:
        return _blocked_passport(case=case, blocking_errors=[str(exc)], source_artifact=source_artifact)

    warnings, blocking_errors = _risk_messages(case, computed)
    status = "block" if blocking_errors else ("warn" if warnings else "pass")
    checks = _build_checks(case, computed, source_artifact, status)
    passport = {
        "schema_version": WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION,
        "case_name": str(case.get("case_name") or "wax_rheology_phase_change_case"),
        "status": status,
        "summary": _summary(status, computed),
        "inputs": case,
        "computed_quantities": computed,
        "checks": checks,
        "fluent_hints": {},
        "warnings": warnings,
        "blocking_errors": blocking_errors,
        "limitations": list(LIMITATIONS),
        "metadata": {
            "source_artifact": source_artifact,
            "solver_execution": "not_attempted_passport_only",
            "fluent_launched": False,
        },
    }
    passport["fluent_hints"] = build_wax_rheology_phase_change_fluent_hints(passport)
    return passport


def compute_wax_rheology_phase_change_quantities(case: dict[str, Any]) -> dict[str, Any]:
    """Compute wax viscosity, softening, thermal, and phase-change evidence."""

    temperature_min = float(case["temperature_min_K"])
    temperature_max = float(case["temperature_max_K"])
    reference_temperature = float(case.get("reference_temperature_K") or 0.5 * (temperature_min + temperature_max))
    viscosity = _viscosity_summary(case, temperature_min, temperature_max, reference_temperature)
    softening = _softening_summary(case, temperature_min, temperature_max)
    storage = _storage_modulus_summary(case)
    thermal = _thermal_summary(case)
    heating = _heating_summary(case, softening, thermal)
    phase = _phase_change_summary(case, thermal, heating)
    sensitivity = classify_viscosity_sensitivity(float(viscosity["eta_ratio_over_range"]))
    phase_risk = classify_phase_change_stiffness(thermal, phase, case)
    recommendation = recommend_material_model(case, computed_stub={"viscosity": viscosity, "softening": softening, "phase_change": phase, "phase_change_stiffness_risk": phase_risk})
    recommended_dt = recommended_time_step(case, thermal, heating)
    return {
        "arrhenius": viscosity,
        "softening": softening,
        "storage_modulus": storage,
        "thermal": thermal,
        "heating": heating,
        "phase_change": phase | {"phase_change_stiffness_risk": phase_risk},
        "recommendation": {
            "material_model_recommendation": recommendation,
            "recommended_time_step_s": recommended_dt,
            "viscosity_temperature_sensitivity_risk": sensitivity,
        },
    }


def build_wax_rheology_phase_change_fluent_hints(passport: dict[str, Any]) -> dict[str, Any]:
    computed = passport.get("computed_quantities", {})
    recommendation = computed.get("recommendation", {})
    phase = computed.get("phase_change", {})
    thermal = computed.get("thermal", {})
    model = recommendation.get("material_model_recommendation", "blocked_invalid_material_data")
    risky_phase = phase.get("phase_change_stiffness_risk") in {"moderate", "high", "extreme"}
    hints = {
        "schema_version": WAX_RHEOLOGY_HINTS_SCHEMA_VERSION,
        "case_name": passport.get("case_name"),
        "status": "blocked" if passport.get("status") == "block" else "ready_with_warnings" if passport.get("status") == "warn" else "ready",
        "recommended_material_model": model,
        "recommended_physics": {
            "energy": True,
            "material_model": model,
            "phase_change_model": passport.get("inputs", {}).get("phase_change_model", "none"),
            "requires_manual_source_review": passport.get("inputs", {}).get("phase_change_model") != "none",
            "temperature_dependent_viscosity": model in {"arrhenius_viscosity", "temperature_dependent_viscosity", "softening_transition_review", "phase_change_review_required"},
        },
        "recommended_materials": {
            "solid_density_kg_m3": passport.get("inputs", {}).get("density_solid_kg_m3"),
            "liquid_density_kg_m3": passport.get("inputs", {}).get("density_liquid_kg_m3"),
            "specific_heat_J_kgK": passport.get("inputs", {}).get("specific_heat_J_kgK"),
            "thermal_conductivity_W_mK": passport.get("inputs", {}).get("thermal_conductivity_W_mK"),
            "latent_heat_J_kg": passport.get("inputs", {}).get("latent_heat_J_kg"),
        },
        "recommended_numerics": {
            "source_term_ramping": True,
            "source_term_clamp": True,
            "nan_guard": True,
            "temperature_bounds_required": True,
            "viscosity_bounds_required": True,
            "first_order_warmup": True,
            "source_term_stiffness_risk": phase.get("phase_change_stiffness_risk", "not_available"),
        },
        "recommended_transient_controls": {
            "initial_time_step_s": recommendation.get("recommended_time_step_s"),
            "adaptive_time_step": risky_phase or thermal.get("thermal_time_step_status") in {"marginal", "under_resolved"},
            "checkpoint_during_softening_or_phase_change": True,
            "thermal_time_step_ratio": thermal.get("thermal_time_step_ratio"),
        },
        "recommended_monitors": [
            "temperature_min_max",
            "viscosity_min_max",
            "liquid_fraction_bounds_if_available",
            "phase_change_source_integral_if_available",
            "energy_balance",
            "max_temperature",
            "min_temperature",
            "thermal_diffusion_time_step_indicator",
        ],
        "recommended_source_term_controls": [
            "source_ramping",
            "source_clamp",
            "temperature_bounds",
            "NaN_guard",
            "latent_heat_unit_check",
            "source_sign_convention_review",
        ],
        "recommended_postprocessing": [
            "viscosity_field_summary",
            "temperature_field_summary",
            "liquid_fraction_summary_if_available",
            "phase_change_source_integral_history_if_available",
        ],
        "hints": [
            {
                "category": "energy_equation",
                "recommendation": "Enable the energy equation for wax softening and phase-change review.",
                "evidence": ["wax_thermal_diffusion_time", "wax_phase_change_energy_scale"],
            },
            {
                "category": "temperature_dependent_viscosity",
                "recommendation": "Review temperature-dependent wax viscosity before Fluent material setup.",
                "evidence": ["wax_arrhenius_viscosity", "wax_viscosity_range", "wax_viscosity_sensitivity"],
            },
            {
                "category": "phase_change_source_review",
                "recommendation": "Review latent-heat source-term sign, units, ramping, clamps, and monitors before Fluent execution.",
                "evidence": ["wax_phase_change_energy_scale", "wax_phase_change_stiffness"],
            },
            {
                "category": "monitor_requirements",
                "recommendation": "Require temperature, viscosity, energy-balance, and source-integral monitors for the first handoff run.",
                "evidence": ["wax_monitor_requirements"],
            },
        ],
        "warnings": list(passport.get("warnings", [])),
        "blocking_errors": list(passport.get("blocking_errors", [])),
        "limitations": list(passport.get("limitations", LIMITATIONS)),
        "metadata": {
            "source_passport_schema_version": passport.get("schema_version"),
            "solver_execution": "not_attempted_hints_only",
            "fluent_launched": False,
        },
    }
    return hints


def compile_wax_rheology_phase_change_patch(
    artifact: str | Path | dict[str, Any],
    *,
    source_artifact: str | None = None,
) -> dict[str, Any]:
    """Compile a wax passport into a validated non-executing solver-plan patch."""

    payload, loaded_artifact = _load_payload(artifact)
    source = source_artifact or loaded_artifact
    if payload.get("schema_version") != WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION:
        return _unsupported_wax_patch(payload, source_artifact=source)
    status = _passport_status(payload)
    evidence = _wax_evidence(payload, source, status)
    evidence_ids = {item.evidence_id for item in evidence}
    warnings = list(payload.get("warnings", []))
    blocking_errors = list(payload.get("blocking_errors", []))
    limitations = list(payload.get("limitations", []))
    if status == "block":
        return _blocked_patch(payload, evidence, source_artifact=source, warnings=warnings, blocking_errors=blocking_errors, limitations=limitations)

    computed = payload.get("computed_quantities", {})
    recommendation = computed.get("recommendation", {})
    phase = computed.get("phase_change", {})
    inputs = payload.get("inputs", {})
    model = recommendation.get("material_model_recommendation", "phase_change_review_required")
    recommended_dt = recommendation.get("recommended_time_step_s")
    temperature_range = [inputs.get("temperature_min_K"), inputs.get("temperature_max_K")]
    operations = [
        PatchOperation("replace", "/physics/energy/enabled", True, "Wax thermal softening and phase-change readiness require the energy equation.", ["wax_thermal_diffusion_time"], "high", []),
        PatchOperation("replace", "/physics/material_model", model, "Wax material model recommendation from rheology and softening evidence.", ["wax_material_model_recommendation"], "high", ["Reviewer must confirm the final Fluent material setup."]),
        PatchOperation("append_unique", "/materials/property_models", {"name": "temperature_dependent_viscosity", "review_required": True}, "Wax viscosity is temperature-sensitive or must be bounded during review.", ["wax_viscosity_range", "wax_viscosity_sensitivity"], "high", []),
        PatchOperation("append_unique", "/materials/property_models", {"name": "arrhenius_viscosity", "review_required": True}, "Arrhenius viscosity evidence is available for this wax case.", ["wax_arrhenius_viscosity"], "high", ["No executable UDF code is generated."]),
        PatchOperation("append_unique", "/materials/property_models", {"name": "phase_change_review", "model": inputs.get("phase_change_model"), "review_required": True}, "Latent heat and melting interval require phase-change setup review.", ["wax_phase_change_energy_scale", "wax_phase_change_stiffness"], "medium", []),
        PatchOperation("replace", "/source_terms/phase_change/model", "review-required", "Phase-change source-term implementation must be reviewed before Fluent use.", ["wax_phase_change_stiffness", "wax_phase_change_energy_scale"], "high", ["H4 does not implement a phase-change source term."]),
        PatchOperation("replace", "/numerics/source_term_controls/ramping", True, "Source ramping is recommended for latent heat and stiff material-property changes.", ["wax_phase_change_stiffness"], "high", []),
        PatchOperation("replace", "/numerics/source_term_controls/clamp", True, "Source and viscosity clamps are required before downstream Fluent use.", ["wax_phase_change_stiffness", "wax_viscosity_range"], "high", []),
        PatchOperation("replace", "/numerics/source_term_controls/nan_guard", True, "NaN guards are required for temperature-dependent viscosity and source terms.", ["wax_phase_change_stiffness", "wax_viscosity_range"], "high", []),
        PatchOperation("replace", "/transient/initial_time_step_s", recommended_dt, "Recommended initial time step from thermal diffusion and heating interval evidence.", ["wax_recommended_time_step", "wax_thermal_diffusion_time"], "high", []),
        PatchOperation("replace", "/acceptance_criteria/bounded_temperature_range_K", temperature_range, "Temperature must remain within reviewed wax material bounds.", ["wax_material_model_recommendation"], "medium", []),
        PatchOperation("replace", "/acceptance_criteria/bounded_viscosity_range", True, "Viscosity field must remain finite and inside reviewed bounds.", ["wax_viscosity_range"], "high", []),
        PatchOperation("append_unique", "/postprocessing/required_outputs", {"name": "viscosity_field_summary", "required": True}, "Wax passport requires viscosity field summary review.", ["wax_monitor_requirements"], "high", []),
        PatchOperation("append_unique", "/postprocessing/required_outputs", {"name": "temperature_field_summary", "required": True}, "Wax passport requires temperature field summary review.", ["wax_monitor_requirements"], "high", []),
    ]
    if phase.get("stefan_number") is not None:
        operations.append(
            PatchOperation("append_unique", "/acceptance_criteria", {"name": "phase_change_energy_balance_review", "required": True}, "Latent heat evidence requires energy-balance review.", ["wax_phase_change_energy_scale"], "high", [])
        )
    operations.extend(_wax_monitor_patches(evidence_ids))
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or "wax_rheology_phase_change_patch_case"),
        status="warn" if status == "warn" or warnings else "pass",
        summary="Wax rheology / phase-change passport compiled into a non-executing Fluent solver-plan patch.",
        evidence=evidence,
        patches=operations,
        warnings=warnings,
        blocking_errors=[],
        limitations=limitations + ["This patch recommends wax material and source-term review settings only; it does not execute Fluent or generate UDF code."],
        metadata={"source_artifact": source, "compiler": "wax_rheology_phase_change", "fluent_launched": False},
    )
    return patch.to_dict()


def write_wax_rheology_phase_change_bundle(case: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    target = Path(output_dir)
    _ensure_dir(target)
    passport_dir = target / "passport"
    _ensure_dir(passport_dir)
    case_file = _write_json(target / "wax_rheology_phase_change_case.json", case)
    passport = build_wax_rheology_phase_change_passport(case, source_artifact=str(case_file))
    hints = build_wax_rheology_phase_change_fluent_hints(passport)
    artifacts = {
        "case_file": str(case_file),
        "passport": str(_write_json(passport_dir / "wax_rheology_phase_change_passport.json", passport)),
        "fluent_hints": str(_write_json(passport_dir / "wax_rheology_phase_change_fluent_hints.json", hints)),
        "report": str(_write_text(passport_dir / "wax_rheology_phase_change_report.md", wax_rheology_phase_change_report(passport, hints))),
    }
    return {"artifacts": artifacts, "passport": passport, "fluent_hints": hints}


def run_wax_rheology_handoff_demo(*, output_dir: str | Path) -> dict[str, Any]:
    target = Path(output_dir)
    _ensure_dir(target)
    case = create_demo_wax_rheology_case()
    bundle = write_wax_rheology_phase_change_bundle(case, target)

    from .fluent_patch_compiler import compile_solver_plan_patch_from_passport, write_solver_plan_patch_bundle

    patch = compile_solver_plan_patch_from_passport(bundle["artifacts"]["passport"])
    patch_result = write_solver_plan_patch_bundle(patch, output=target / "solver_plan_patch.json")
    artifacts = dict(bundle["artifacts"])
    artifacts.update(
        {
            "solver_plan_patch": patch_result["outputs"]["artifacts"]["solver_plan_patch"],
            "solver_plan_patch_report": patch_result["outputs"]["artifacts"]["solver_plan_patch_report"],
        }
    )
    result = AgentResult.success(
        backend="fastcfd",
        operation="wax_rheology_handoff_demo",
        message="Wax rheology / phase-change handoff demo generated.",
        outputs={
            "artifacts": artifacts,
            "passport": bundle["passport"],
            "fluent_hints": bundle["fluent_hints"],
            "patch": patch,
            "patch_result": patch_result,
        },
        metadata={"output_dir": str(target), "patch_status": patch.get("status"), "fluent_launched": False},
    )
    if patch_result.get("status") != "success":
        result.status = "partial"
        result.message = "Wax rheology / phase-change demo generated, but the solver-plan patch is blocked."
    return result.to_dict()


def write_wax_rheology_phase_change_report(passport: dict[str, Any], path: str | Path) -> Path:
    hints = build_wax_rheology_phase_change_fluent_hints(passport)
    return _write_text(Path(path), wax_rheology_phase_change_report(passport, hints))


def wax_rheology_phase_change_report(passport: dict[str, Any], hints: dict[str, Any]) -> str:
    inputs = passport.get("inputs", {})
    computed = passport.get("computed_quantities", {})
    arr = computed.get("arrhenius", {})
    soft = computed.get("softening", {})
    storage = computed.get("storage_modulus", {})
    thermal = computed.get("thermal", {})
    phase = computed.get("phase_change", {})
    recommendation = computed.get("recommendation", {})
    lines = [
        "# Wax Rheology / Phase-Change Passport",
        "",
        f"Case name: `{passport.get('case_name')}`",
        f"Status: `{passport.get('status')}`",
        "",
        "## Case Summary",
        "",
        str(passport.get("summary") or ""),
        "",
        "## Input Material Properties",
        "",
        f"- Temperature range: `{inputs.get('temperature_min_K')}` to `{inputs.get('temperature_max_K')}` K",
        f"- Viscosity model: `{inputs.get('viscosity_model')}`",
        f"- Density solid: `{inputs.get('density_solid_kg_m3')}` kg/m^3",
        f"- Density liquid: `{inputs.get('density_liquid_kg_m3')}` kg/m^3",
        f"- Specific heat: `{inputs.get('specific_heat_J_kgK')}` J/(kg*K)",
        f"- Thermal conductivity: `{inputs.get('thermal_conductivity_W_mK')}` W/(m*K)",
        f"- Latent heat: `{inputs.get('latent_heat_J_kg')}` J/kg",
        "",
        "## Arrhenius Viscosity Calculation",
        "",
        f"- Eta at Tmin: `{arr.get('eta_at_temperature_min_Pa_s')}` Pa*s",
        f"- Eta at Tmax: `{arr.get('eta_at_temperature_max_Pa_s')}` Pa*s",
        f"- Eta at reference temperature: `{arr.get('eta_at_reference_temperature_Pa_s')}` Pa*s",
        f"- Viscosity ratio: `{arr.get('eta_ratio_over_range')}`",
        f"- Activation energy: `{arr.get('activation_energy_kJ_mol')}` kJ/mol",
        f"- Fit range status: `{arr.get('viscosity_fit_range_status')}`",
        "",
        "## Softening Regime",
        "",
        f"- Softening regime: `{soft.get('softening_regime')}`",
        f"- Softening transition overlap: `{soft.get('softening_transition_overlap_K')}` K",
        f"- tan delta peak: `{inputs.get('tan_delta_peak_temperature_K')}` K",
        "",
        "## Storage Modulus Drop",
        "",
        f"- Drop ratio: `{storage.get('storage_modulus_drop_ratio')}`",
        f"- log10 drop: `{storage.get('log10_storage_modulus_drop')}`",
        f"- Mechanical softening strength: `{storage.get('mechanical_softening_strength')}`",
        "",
        "## Thermal Diffusion Time Scale",
        "",
        f"- Thermal diffusivity: `{thermal.get('thermal_diffusivity_m2_s')}` m^2/s",
        f"- Domain diffusion time: `{thermal.get('domain_diffusion_time_s')}` s",
        f"- Cell diffusion time: `{thermal.get('cell_diffusion_time_s')}` s",
        f"- Thermal time-step ratio: `{thermal.get('thermal_time_step_ratio')}`",
        f"- Thermal time-step status: `{thermal.get('thermal_time_step_status')}`",
        "",
        "## Stefan Number",
        "",
        f"- Stefan number: `{phase.get('stefan_number')}`",
        f"- Stefan interpretation: `{phase.get('stefan_interpretation')}`",
        "",
        "## Phase-Change Energy Scale",
        "",
        f"- Energy density: `{phase.get('phase_change_energy_density_J_m3')}` J/m^3",
        f"- Power density scale: `{phase.get('phase_change_power_density_scale_W_m3')}` W/m^3",
        f"- Source-term stiffness risk: `{phase.get('phase_change_stiffness_risk')}`",
        "",
        "## Recommended Fluent Material Model",
        "",
        f"- Material recommendation: `{recommendation.get('material_model_recommendation')}`",
        f"- Recommended initial time step: `{recommendation.get('recommended_time_step_s')}` s",
        f"- Viscosity sensitivity risk: `{recommendation.get('viscosity_temperature_sensitivity_risk')}`",
        "",
        "## Recommended Monitors",
        "",
    ]
    lines.extend(f"- `{item}`" for item in hints.get("recommended_monitors", []))
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in passport.get("warnings", [])) if passport.get("warnings") else lines.append("- None")
    lines.extend(["", "## Blocking Errors", ""])
    lines.extend(f"- {item}" for item in passport.get("blocking_errors", [])) if passport.get("blocking_errors") else lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in passport.get("limitations", LIMITATIONS))
    lines.extend(
        [
            "",
            "## Reviewer Checklist",
            "",
            "- Confirm wax density and thermal properties.",
            "- Confirm Arrhenius viscosity fit range.",
            "- Confirm whether DMA softening temperatures apply to this wax batch.",
            "- Confirm latent heat and melting interval.",
            "- Confirm whether phase change should be modeled with effective heat capacity or source term.",
            "- Confirm source-term sign convention before Fluent use.",
            "- Confirm source ramp and clamp before Fluent use.",
            "- Confirm temperature bounds and viscosity bounds.",
            "- Confirm time step during softening and phase-change interval.",
            "- Confirm this artifact has not launched Fluent.",
            "",
        ]
    )
    return "\n".join(lines)


def arrhenius_viscosity_pa_s(temperature_K: float, A: float, B_K: float) -> float:
    eta = math.exp(float(A) + float(B_K) / float(temperature_K))
    if not math.isfinite(eta) or eta <= 0.0:
        raise ValueError("Arrhenius viscosity must be finite and positive.")
    return eta


def classify_softening_regime(temperature_min_K: float, temperature_max_K: float, softening_50_K: float | None, softening_90_K: float | None) -> str:
    if softening_50_K is None or softening_90_K is None:
        return "unknown"
    if temperature_max_K < softening_50_K:
        return "solid_like"
    if temperature_min_K > softening_90_K:
        return "flow_dominant"
    if temperature_min_K < softening_50_K and temperature_max_K > softening_90_K:
        return "crosses_softening_transition"
    return "softening_transition"


def classify_viscosity_sensitivity(eta_ratio: float) -> str:
    if eta_ratio <= 10.0:
        return "low"
    if eta_ratio <= 100.0:
        return "moderate"
    if eta_ratio <= 10000.0:
        return "high"
    return "extreme"


def classify_fit_range(temperature_min_K: float, temperature_max_K: float, fit_min_K: float | None, fit_max_K: float | None) -> str:
    if fit_min_K is None or fit_max_K is None:
        return "unknown"
    if temperature_min_K >= fit_min_K and temperature_max_K <= fit_max_K:
        return "inside_fit_range"
    if temperature_max_K < fit_min_K or temperature_min_K > fit_max_K:
        return "outside_fit_range"
    return "partly_outside_fit_range"


def classify_phase_change_stiffness(thermal: dict[str, Any], phase: dict[str, Any], case: dict[str, Any]) -> str:
    if case.get("phase_change_model") == "none" or phase.get("stefan_number") is None:
        return "low"
    ratio = float(thermal.get("thermal_time_step_ratio") or 0.0)
    ste = float(phase.get("stefan_number") or 0.0)
    power = float(phase.get("phase_change_power_density_scale_W_m3") or 0.0)
    interval = _optional_interval_width(case.get("melting_temperature_min_K"), case.get("melting_temperature_max_K"))
    score = 0
    if ratio >= 1.0:
        score += 2
    elif ratio >= 0.1:
        score += 1
    if ste < 0.1:
        score += 2
    elif ste < 0.5:
        score += 1
    if power > 1.0e11:
        score += 2
    elif power > 1.0e9:
        score += 1
    if interval is not None and interval < 2.0:
        score += 1
    if score >= 5:
        return "extreme"
    if score >= 3:
        return "high"
    if score >= 1:
        return "moderate"
    return "low"


def recommend_material_model(case: dict[str, Any], *, computed_stub: dict[str, Any] | None = None) -> str:
    if _validate_case_payload(case):
        return "blocked_invalid_material_data"
    if str(case.get("viscosity_model")) == "arrhenius":
        return "arrhenius_viscosity"
    soft = computed_stub.get("softening", {}) if computed_stub else {}
    if soft.get("softening_regime") in {"crosses_softening_transition", "softening_transition"}:
        return "softening_transition_review"
    if str(case.get("phase_change_model")) != "none":
        return "phase_change_review_required"
    if str(case.get("viscosity_model")) == "constant":
        return "constant_viscosity"
    return "temperature_dependent_viscosity"


def recommended_time_step(case: dict[str, Any], thermal: dict[str, Any], heating: dict[str, Any]) -> float:
    candidates = [float(case["time_step_s"]), 0.2 * float(thermal["cell_diffusion_time_s"])]
    for key in ["melting_heating_time_s", "softening_heating_time_s"]:
        value = heating.get(key)
        if value is not None and value != "not_available":
            candidates.append(0.1 * float(value))
    return max(min(value for value in candidates if value > 0.0), TINY)


def _viscosity_summary(case: dict[str, Any], temperature_min: float, temperature_max: float, reference_temperature: float) -> dict[str, Any]:
    model = str(case["viscosity_model"])
    if model == "constant":
        eta = float(case["reference_viscosity_Pa_s"])
        if eta <= 0 or not math.isfinite(eta):
            raise ValueError("reference_viscosity_Pa_s must be finite and positive.")
        eta_min = eta_max = eta_ref = eta
        activation = case.get("activation_energy_J_mol")
    elif model == "arrhenius":
        A = float(case["arrhenius_A"])
        B = float(case["arrhenius_B_K"])
        eta_min_temp = arrhenius_viscosity_pa_s(temperature_min, A, B)
        eta_max_temp = arrhenius_viscosity_pa_s(temperature_max, A, B)
        eta_ref = arrhenius_viscosity_pa_s(reference_temperature, A, B)
        eta_min = min(eta_min_temp, eta_max_temp)
        eta_max = max(eta_min_temp, eta_max_temp)
        activation = float(case.get("activation_energy_J_mol") or GAS_CONSTANT_J_MOL_K * B)
    else:
        eta = float(case.get("reference_viscosity_Pa_s") or 1.0)
        eta_min = eta_max = eta_ref = eta
        activation = case.get("activation_energy_J_mol")
    if eta_min <= 0.0 or not all(math.isfinite(value) and value > 0.0 for value in [eta_min, eta_max, eta_ref]):
        raise ValueError("Wax viscosity values must be finite and positive.")
    ratio = eta_max / max(eta_min, TINY)
    fit_status = classify_fit_range(
        temperature_min,
        temperature_max,
        _optional_float(case.get("viscosity_fit_temperature_min_K")),
        _optional_float(case.get("viscosity_fit_temperature_max_K")),
    )
    return {
        "viscosity_model": model,
        "eta_at_temperature_min_Pa_s": eta_min_temp if model == "arrhenius" else eta_min,
        "eta_at_temperature_max_Pa_s": eta_max_temp if model == "arrhenius" else eta_max,
        "eta_at_reference_temperature_Pa_s": eta_ref,
        "eta_min_over_range_Pa_s": eta_min,
        "eta_max_over_range_Pa_s": eta_max,
        "eta_ratio_over_range": ratio,
        "activation_energy_J_mol": activation,
        "activation_energy_kJ_mol": None if activation is None else float(activation) / 1000.0,
        "viscosity_fit_range_status": fit_status,
    }


def _softening_summary(case: dict[str, Any], temperature_min: float, temperature_max: float) -> dict[str, Any]:
    s50 = _optional_float(case.get("softening_temperature_50_K"))
    s90 = _optional_float(case.get("softening_temperature_90_K"))
    regime = classify_softening_regime(temperature_min, temperature_max, s50, s90)
    overlap = "not_available"
    if s50 is not None and s90 is not None:
        overlap = max(0.0, min(temperature_max, s90) - max(temperature_min, s50))
    return {
        "softening_regime": regime,
        "softening_transition_overlap_K": overlap,
        "softening_temperature_50_K": s50,
        "softening_temperature_90_K": s90,
        "tan_delta_peak_temperature_K": _optional_float(case.get("tan_delta_peak_temperature_K")),
    }


def _storage_modulus_summary(case: dict[str, Any]) -> dict[str, Any]:
    low = _optional_float(case.get("storage_modulus_low_temp_Pa"))
    high = _optional_float(case.get("storage_modulus_high_temp_Pa"))
    if low is None or high is None:
        return {"storage_modulus_drop_ratio": "not_available", "log10_storage_modulus_drop": "not_available", "mechanical_softening_strength": "unknown"}
    ratio = low / max(high, TINY)
    if ratio < 10.0:
        strength = "weak"
    elif ratio < 100.0:
        strength = "moderate"
    else:
        strength = "strong"
    return {
        "storage_modulus_low_temp_Pa": low,
        "storage_modulus_high_temp_Pa": high,
        "storage_modulus_drop_ratio": ratio,
        "log10_storage_modulus_drop": math.log10(max(ratio, TINY)),
        "mechanical_softening_strength": strength,
    }


def _thermal_summary(case: dict[str, Any]) -> dict[str, Any]:
    alpha = _optional_float(case.get("thermal_diffusivity_m2_s"))
    if alpha is None:
        alpha = float(case["thermal_conductivity_W_mK"]) / (float(case["density_solid_kg_m3"]) * float(case["specific_heat_J_kgK"]))
    domain_time = float(case["length_scale_m"]) ** 2 / alpha
    cell_time = float(case["cell_size_m"]) ** 2 / alpha
    ratio = float(case["time_step_s"]) / max(cell_time, TINY)
    if ratio < 0.1:
        status = "resolved"
    elif ratio < 1.0:
        status = "marginal"
    else:
        status = "under_resolved"
    return {
        "thermal_diffusivity_m2_s": alpha,
        "domain_diffusion_time_s": domain_time,
        "cell_diffusion_time_s": cell_time,
        "thermal_time_step_ratio": ratio,
        "thermal_time_step_status": status,
    }


def _heating_summary(case: dict[str, Any], softening: dict[str, Any], thermal: dict[str, Any]) -> dict[str, Any]:
    rate = _optional_float(case.get("heating_rate_K_s"))
    if rate is None or rate <= 0.0:
        return {
            "heating_rate_K_s": rate,
            "softening_heating_time_s": "not_available",
            "melting_heating_time_s": "not_available",
            "heating_vs_diffusion_ratio": "not_available",
        }
    s50 = softening.get("softening_temperature_50_K")
    s90 = softening.get("softening_temperature_90_K")
    softening_time = None if s50 is None or s90 is None else max(0.0, float(s90) - float(s50)) / rate
    melting_width = _optional_interval_width(case.get("melting_temperature_min_K"), case.get("melting_temperature_max_K"))
    melting_time = None if melting_width is None else max(0.0, melting_width) / rate
    reference_time = melting_time if melting_time is not None else softening_time
    return {
        "heating_rate_K_s": rate,
        "softening_heating_time_s": softening_time if softening_time is not None else "not_available",
        "melting_heating_time_s": melting_time if melting_time is not None else "not_available",
        "heating_vs_diffusion_ratio": "not_available" if reference_time is None else reference_time / max(float(thermal["cell_diffusion_time_s"]), TINY),
    }


def _phase_change_summary(case: dict[str, Any], thermal: dict[str, Any], heating: dict[str, Any]) -> dict[str, Any]:
    latent = _optional_float(case.get("latent_heat_J_kg"))
    if latent is None:
        return {
            "stefan_number": None,
            "stefan_interpretation": "not_available",
            "phase_change_energy_density_J_m3": None,
            "phase_change_power_density_scale_W_m3": None,
        }
    delta_t = max(float(case["temperature_max_K"]) - float(case["temperature_min_K"]), TINY)
    ste = float(case["specific_heat_J_kgK"]) * delta_t / latent
    if ste < 0.1:
        interpretation = "latent_heat_dominates"
    elif ste > 1.0:
        interpretation = "sensible_heat_dominates"
    else:
        interpretation = "mixed_latent_and_sensible_heat"
    energy_density = float(case["density_solid_kg_m3"]) * latent
    power_density = energy_density / max(float(case["time_step_s"]), TINY)
    return {
        "stefan_number": ste,
        "stefan_interpretation": interpretation,
        "phase_change_energy_density_J_m3": energy_density,
        "phase_change_power_density_scale_W_m3": power_density,
    }


def _risk_messages(case: dict[str, Any], computed: dict[str, Any]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    blocking_errors: list[str] = []
    arr = computed["arrhenius"]
    soft = computed["softening"]
    thermal = computed["thermal"]
    phase = computed["phase_change"]
    rec = computed["recommendation"]
    if soft.get("softening_regime") in {"crosses_softening_transition", "softening_transition"}:
        warnings.append("Temperature range crosses or touches the wax softening transition.")
    if rec.get("viscosity_temperature_sensitivity_risk") in {"high", "extreme"}:
        warnings.append(f"Wax viscosity temperature sensitivity is {rec['viscosity_temperature_sensitivity_risk']}.")
    if thermal.get("thermal_time_step_status") in {"marginal", "under_resolved"}:
        warnings.append(f"Thermal time-step status is {thermal['thermal_time_step_status']}.")
    if phase.get("phase_change_stiffness_risk") in {"moderate", "high"}:
        warnings.append(f"Phase-change stiffness risk is {phase['phase_change_stiffness_risk']}.")
    if phase.get("phase_change_stiffness_risk") == "extreme":
        blocking_errors.append("Phase-change stiffness risk is extreme for the declared time step and source-term review.")
    if arr.get("viscosity_fit_range_status") in {"unknown", "partly_outside_fit_range"}:
        warnings.append(f"Viscosity fit range status is {arr.get('viscosity_fit_range_status')}.")
    if arr.get("viscosity_fit_range_status") == "outside_fit_range":
        blocking_errors.append("Temperature range is outside the provided viscosity fit range.")
    if case.get("latent_heat_J_kg") is not None and case.get("phase_change_model") != "none":
        warnings.append("Latent heat is present; phase-change source-term implementation requires manual review.")
    return warnings, blocking_errors


def _build_checks(case: dict[str, Any], computed: dict[str, Any], source_artifact: str, status: str) -> list[dict[str, Any]]:
    return [
        _check("wax_arrhenius_viscosity", "arrhenius_viscosity", computed["arrhenius"], "Pa*s", "ln(eta)=A+B/T", "Temperature-dependent viscosity evidence computed over the operating range.", "high", source_artifact, status),
        _check("wax_viscosity_range", "eta_ratio_over_range", computed["arrhenius"]["eta_ratio_over_range"], "1", "finite positive viscosity over temperature range", "Wax viscosity range supports bounded material-property review.", "high", source_artifact, status),
        _check("wax_viscosity_sensitivity", "viscosity_temperature_sensitivity_risk", computed["recommendation"]["viscosity_temperature_sensitivity_risk"], "class", "ratio thresholds: 10, 100, 10000", "Viscosity sensitivity risk controls transient and monitor requirements.", "high", source_artifact, status),
        _check("wax_softening_regime", "softening_regime", computed["softening"]["softening_regime"], "class", "softening 50/90 temperature overlap", "Wax softening regime determines material-model review need.", "high", source_artifact, status),
        _check("wax_storage_modulus_drop", "storage_modulus_drop_ratio", computed["storage_modulus"].get("storage_modulus_drop_ratio"), "1", "G_low / G_high", "Storage-modulus drop quantifies mechanical softening strength.", "medium", source_artifact, status),
        _check("wax_thermal_diffusion_time", "thermal_time_step_ratio", computed["thermal"]["thermal_time_step_ratio"], "1", "dt / cell_diffusion_time", "Thermal diffusion evidence controls time-step review.", "high", source_artifact, status),
        _check("wax_phase_change_energy_scale", "phase_change_energy_density_J_m3", computed["phase_change"].get("phase_change_energy_density_J_m3"), "J/m^3", "rho_solid * latent_heat", "Latent heat energy scale supports source-term review.", "high", source_artifact, status),
        _check("wax_phase_change_stiffness", "phase_change_stiffness_risk", computed["phase_change"].get("phase_change_stiffness_risk"), "class", "thermal dt ratio, Stefan number, source power scale, melting interval", "Source-term stiffness risk controls ramping, clamps, and review gates.", "high", source_artifact, status),
        _check("wax_recommended_time_step", "recommended_time_step_s", computed["recommendation"].get("recommended_time_step_s"), "s", "min(input dt, 0.2*cell thermal diffusion time, heating interval fractions)", "Recommended first-pass time step for Fluent review.", "high", source_artifact, status),
        _check("wax_material_model_recommendation", "material_model_recommendation", computed["recommendation"].get("material_model_recommendation"), "class", "viscosity model, softening, phase-change status", "Material model recommendation remains review-required before Fluent use.", "high", source_artifact, status),
        _check("wax_monitor_requirements", "recommended_monitors", ["temperature_min_max", "viscosity_min_max", "energy_balance", "phase_change_source_integral_if_available"], "list", "review", "Wax setup requires thermal, viscosity, and source-term monitors.", "high", source_artifact, status),
    ]


def _wax_evidence(payload: dict[str, Any], source_artifact: str, status: str) -> list[PatchEvidence]:
    evidence: list[PatchEvidence] = []
    for check in payload.get("checks", []):
        evidence.append(
            PatchEvidence(
                evidence_id=str(check.get("evidence_id")),
                source_module=str(check.get("source_module") or "fromcad2cfd_fastcfd.wax_rheology_phase_change"),
                source_artifact=source_artifact,
                source_schema_version=str(check.get("source_schema_version") or WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION),
                source_status=status,
                quantity_name=str(check.get("quantity_name") or "unknown"),
                quantity_value=check.get("quantity_value"),
                quantity_units=str(check.get("quantity_units") or ""),
                threshold_or_rule=str(check.get("threshold_or_rule") or ""),
                interpretation=str(check.get("interpretation") or ""),
                confidence=str(check.get("confidence") or "medium"),
                limitations=list(check.get("limitations", LIMITATIONS)),
            )
        )
    return evidence


def _wax_monitor_patches(evidence_ids: set[str]) -> list[PatchOperation]:
    refs = ["wax_monitor_requirements"] if "wax_monitor_requirements" in evidence_ids else []
    return [
        PatchOperation("append_unique", "/monitors/global", {"name": "temperature_min_max", "quantity": "temperature", "reduction": "min_max", "required": True}, "Wax thermal setup requires temperature bounds.", refs or ["wax_thermal_diffusion_time"], "high", []),
        PatchOperation("append_unique", "/monitors/global", {"name": "viscosity_min_max", "quantity": "dynamic_viscosity", "reduction": "min_max", "required": True}, "Wax rheology setup requires viscosity bounds.", refs or ["wax_viscosity_range"], "high", []),
        PatchOperation("append_unique", "/monitors/global", {"name": "max_temperature", "quantity": "temperature", "reduction": "max", "required": True}, "Maximum temperature must be checked against material fit range.", ["wax_material_model_recommendation"], "high", []),
        PatchOperation("append_unique", "/monitors/global", {"name": "min_temperature", "quantity": "temperature", "reduction": "min", "required": True}, "Minimum temperature must be checked against material fit range.", ["wax_material_model_recommendation"], "high", []),
        PatchOperation("append_unique", "/monitors/global", {"name": "energy_balance", "quantity": "energy_balance", "reduction": "imbalance", "required": True}, "Wax phase-change setup requires energy balance monitoring.", ["wax_phase_change_energy_scale"], "high", []),
        PatchOperation("append_unique", "/monitors/global", {"name": "thermal_diffusion_time_step_indicator", "quantity": "thermal_time_step_ratio", "reduction": "max", "required": True}, "Thermal time-step ratio should be reviewed during early runs.", ["wax_thermal_diffusion_time"], "high", []),
        PatchOperation("append_unique", "/monitors/global", {"name": "liquid_fraction_bounds_if_available", "quantity": "liquid_fraction", "reduction": "min_max", "required": False}, "Liquid-fraction bounds are required if a Fluent phase-change model is enabled.", ["wax_phase_change_stiffness"], "medium", []),
        PatchOperation("append_unique", "/monitors/global", {"name": "phase_change_source_integral_if_available", "quantity": "phase_change_source", "reduction": "integral", "required": False}, "Phase-change source integral should be monitored if a source term is implemented.", ["wax_phase_change_stiffness"], "medium", []),
    ]


def _validate_case_payload(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(case, dict):
        return ["Case payload must be an object."]
    dangerous = find_dangerous_keys(case)
    if dangerous:
        errors.append("Dangerous key names found: " + ", ".join(dangerous))
    if case.get("schema_version") != WAX_RHEOLOGY_CASE_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {case.get('schema_version')!r}")
    for key in [
        "temperature_min_K",
        "temperature_max_K",
        "density_solid_kg_m3",
        "specific_heat_J_kgK",
        "thermal_conductivity_W_mK",
        "length_scale_m",
        "cell_size_m",
        "time_step_s",
    ]:
        _require_positive(case, key, errors)
    try:
        if float(case.get("temperature_max_K")) <= float(case.get("temperature_min_K")):
            errors.append("temperature_max_K must be greater than temperature_min_K.")
    except (TypeError, ValueError):
        pass
    if case.get("density_liquid_kg_m3") is not None:
        _require_positive(case, "density_liquid_kg_m3", errors)
    if case.get("thermal_diffusivity_m2_s") is not None:
        _require_positive(case, "thermal_diffusivity_m2_s", errors)
    if case.get("latent_heat_J_kg") is not None:
        _require_positive(case, "latent_heat_J_kg", errors)
    model = str(case.get("viscosity_model"))
    if model not in SUPPORTED_VISCOSITY_MODELS:
        errors.append(f"Unsupported viscosity_model: {model!r}.")
    if model == "arrhenius":
        for key in ["arrhenius_A", "arrhenius_B_K"]:
            if case.get(key) is None:
                errors.append(f"{key} is required for arrhenius viscosity.")
    if model == "constant":
        _require_positive(case, "reference_viscosity_Pa_s", errors)
    phase_model = str(case.get("phase_change_model"))
    if phase_model not in SUPPORTED_PHASE_CHANGE_MODELS:
        errors.append(f"Unsupported phase_change_model: {phase_model!r}.")
    _check_order(case, "softening_temperature_50_K", "softening_temperature_90_K", errors)
    _check_order(case, "melting_temperature_min_K", "melting_temperature_max_K", errors)
    _check_order(case, "viscosity_fit_temperature_min_K", "viscosity_fit_temperature_max_K", errors)
    return errors


def _require_positive(case: dict[str, Any], key: str, errors: list[str]) -> None:
    try:
        if float(case.get(key)) <= 0.0:
            errors.append(f"{key} must be > 0.")
    except (TypeError, ValueError):
        errors.append(f"{key} must be numeric.")


def _check_order(case: dict[str, Any], low_key: str, high_key: str, errors: list[str]) -> None:
    low = case.get(low_key)
    high = case.get(high_key)
    if low is None or high is None:
        return
    try:
        if float(high) < float(low):
            errors.append(f"{high_key} must be >= {low_key}.")
    except (TypeError, ValueError):
        errors.append(f"{low_key} and {high_key} must be numeric when provided.")


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_interval_width(min_value: Any, max_value: Any) -> float | None:
    if min_value is None or max_value is None:
        return None
    return float(max_value) - float(min_value)


def _check(
    evidence_id: str,
    quantity_name: str,
    quantity_value: Any,
    quantity_units: str,
    threshold_or_rule: str,
    interpretation: str,
    confidence: str,
    source_artifact: str,
    status: str,
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "source_module": "fromcad2cfd_fastcfd.wax_rheology_phase_change",
        "source_artifact": source_artifact,
        "source_schema_version": WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION,
        "source_status": status,
        "quantity_name": quantity_name,
        "quantity_value": quantity_value,
        "quantity_units": quantity_units,
        "threshold_or_rule": threshold_or_rule,
        "interpretation": interpretation,
        "confidence": confidence,
        "limitations": list(LIMITATIONS),
    }


def _summary(status: str, computed: dict[str, Any]) -> str:
    return (
        f"Wax H4 status is {status}. "
        f"Material recommendation is {computed['recommendation'].get('material_model_recommendation')}; "
        f"softening regime is {computed['softening'].get('softening_regime')}; "
        f"viscosity sensitivity is {computed['recommendation'].get('viscosity_temperature_sensitivity_risk')}; "
        f"phase-change stiffness risk is {computed['phase_change'].get('phase_change_stiffness_risk')}."
    )


def _blocked_passport(*, case: dict[str, Any], blocking_errors: list[str], source_artifact: str) -> dict[str, Any]:
    return {
        "schema_version": WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION,
        "case_name": str(case.get("case_name") or "wax_rheology_phase_change_case"),
        "status": "block",
        "summary": "Wax rheology / phase-change screening blocked this case before Fluent handoff.",
        "inputs": case,
        "computed_quantities": {},
        "checks": [],
        "fluent_hints": {},
        "warnings": [],
        "blocking_errors": blocking_errors,
        "limitations": list(LIMITATIONS),
        "metadata": {"source_artifact": source_artifact, "solver_execution": "blocked_before_fluent_handoff", "fluent_launched": False},
    }


def _load_payload(item: str | Path | dict[str, Any]) -> tuple[dict[str, Any], str]:
    if isinstance(item, dict):
        return item, "inline_artifact"
    path = Path(item)
    with open(_windows_long_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle), str(path)


def _passport_status(payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "").lower()
    if status in {"pass", "passed", "ready"}:
        return "pass"
    if status in {"warn", "warning", "ready_with_warnings"}:
        return "warn"
    return "block"


def _blocked_patch(payload: dict[str, Any], evidence: list[PatchEvidence], *, source_artifact: str, warnings: list[str], blocking_errors: list[str], limitations: list[str]) -> dict[str, Any]:
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or "wax_blocked_patch_case"),
        status="block",
        summary="FastFluent wax rheology / phase-change evidence blocked Fluent handoff.",
        evidence=evidence,
        patches=[
            PatchOperation(
                "block",
                "/runtime/fluent_execution_allowed",
                False,
                "Wax rheology / phase-change passport reported blocking errors.",
                [item.evidence_id for item in evidence],
                "high",
                ["Resolve wax material blocking errors before Fluent setup planning."],
            )
        ],
        warnings=warnings,
        blocking_errors=blocking_errors,
        limitations=limitations,
        metadata={"source_artifact": source_artifact, "compiler": "wax_rheology_phase_change", "fluent_launched": False},
    )
    return patch.to_dict()


def _unsupported_wax_patch(payload: dict[str, Any], *, source_artifact: str) -> dict[str, Any]:
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or "unsupported_wax_passport"),
        status="block",
        summary="Unsupported wax evidence schema for solver-plan patch compilation.",
        evidence=[],
        patches=[
            PatchOperation("block", "/runtime/fluent_execution_allowed", False, "Unsupported wax evidence schema.", [], "high", ["Use the H4 wax passport schema."])
        ],
        warnings=[],
        blocking_errors=[f"Unsupported evidence schema: {payload.get('schema_version')!r}"],
        limitations=["The wax patch compiler is intentionally fail-closed for unsupported schemas."],
        metadata={"source_artifact": source_artifact, "compiler": "wax_rheology_phase_change"},
    )
    return patch.to_dict()


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
