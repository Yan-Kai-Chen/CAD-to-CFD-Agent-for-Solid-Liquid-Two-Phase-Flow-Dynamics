"""Solid-liquid suspension readiness passport for FastFluent.

This module estimates solid-liquid suspension setup risk and Fluent model
selection evidence. It does not execute Fluent, generate UDF code, or solve
particle trajectories.
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


SOLID_LIQUID_CASE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_solid_liquid_suspension_case_v1"
SOLID_LIQUID_PASSPORT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_solid_liquid_suspension_passport_v1"
SOLID_LIQUID_HINTS_SCHEMA_VERSION = "fromcad2cfd_fastfluent_solid_liquid_suspension_fluent_hints_v1"

LIMITATIONS = [
    "This passport is a setup-readiness and Fluent model-selection evidence artifact, not a particle tracking solver.",
    "Particle drag, settling, coupling, and model recommendations are first-pass engineering estimates.",
    "Final Fluent model choice still requires mesh, boundary condition, particle-size distribution, and monitor review.",
    "No Fluent execution, PyFluent execution, raw TUI, UDF generation, DEM coupling, or Eulerian multiphase solving is performed.",
]


def demo_solid_liquid_suspension_case(case_name: str = "solid_liquid_suspension_demo") -> dict[str, Any]:
    return {
        "schema_version": SOLID_LIQUID_CASE_SCHEMA_VERSION,
        "case_name": case_name,
        "fluid_density_kg_m3": 998.0,
        "fluid_dynamic_viscosity_Pa_s": 0.001,
        "particle_density_kg_m3": 2650.0,
        "particle_diameter_m": 50.0e-6,
        "particle_sphericity": 1.0,
        "solid_volume_fraction": 0.005,
        "reference_velocity_m_s": 0.5,
        "length_scale_m": 0.05,
        "domain_height_m": 0.02,
        "gravity_m_s2": 9.81,
        "cell_size_m": 1.0e-3,
        "time_step_s": 1.0e-4,
        "coupling_preference": "auto",
        "domain_orientation": "horizontal_channel",
        "particle_size_distribution": {"type": "monodisperse", "d50_m": 50.0e-6},
        "wall_interaction_relevance": True,
        "erosion_or_impact_relevance": False,
        "thermal_coupling_relevance": False,
        "units": {"density": "kg/m^3", "viscosity": "Pa*s", "length": "m", "time": "s"},
        "metadata": {"purpose": "public synthetic water-silica suspension setup-readiness demo"},
    }


def write_demo_solid_liquid_case(
    *,
    output_dir: str | Path | None = None,
    case_name: str = "solid_liquid_suspension_demo",
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "solid_liquid_suspension_demo" / "input")
    _ensure_dir(target_dir)
    case = demo_solid_liquid_suspension_case(case_name=case_name)
    case_file = _write_json(target_dir / "solid_liquid_suspension_case.json", case)
    result = AgentResult.success(
        backend="fastcfd",
        operation="write_solid_liquid_demo",
        message="Public solid-liquid suspension demo case written.",
        outputs={"case_file": str(case_file), "case": case},
        metadata={"output_dir": str(target_dir)},
    )
    return result.to_dict()


def read_solid_liquid_suspension_case(path: str | Path) -> dict[str, Any]:
    with open(_windows_long_path(Path(path)), "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_solid_liquid_suspension_case_file(
    case_file: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "solid_liquid_suspension" / "passport")
    _ensure_dir(target_dir)
    try:
        case_path = Path(case_file)
        case = read_solid_liquid_suspension_case(case_path)
        passport = build_solid_liquid_suspension_passport(case, source_artifact=str(case_path))
        hints = build_solid_liquid_fluent_hints(passport)
        artifacts = {
            "passport": str(_write_json(target_dir / "solid_liquid_suspension_passport.json", passport)),
            "fluent_hints": str(_write_json(target_dir / "solid_liquid_suspension_fluent_hints.json", hints)),
            "report": str(_write_text(target_dir / "solid_liquid_suspension_report.md", solid_liquid_suspension_report(passport, hints))),
        }
        result_status = "success" if passport["status"] in {"pass", "warn"} else "failed"
        if result_status == "success":
            result = AgentResult.success(
                backend="fastcfd",
                operation="validate_solid_liquid_suspension",
                message="Solid-liquid suspension passport generated.",
                outputs={"artifacts": artifacts, "passport": passport, "fluent_hints": hints},
                metadata={"output_dir": str(target_dir), "case_file": str(case_file)},
            )
        else:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="validate_solid_liquid_suspension",
                message="Solid-liquid suspension passport blocked the case.",
                errors=passport.get("blocking_errors", []),
                metadata={"output_dir": str(target_dir), "case_file": str(case_file)},
            )
            result.outputs.update({"artifacts": artifacts, "passport": passport, "fluent_hints": hints})
        return result.to_dict()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        blocked = _blocked_passport(
            case={"case_name": Path(case_file).stem if case_file else "unknown"},
            blocking_errors=[str(exc)],
            source_artifact=str(case_file),
        )
        hints = build_solid_liquid_fluent_hints(blocked)
        artifacts = {
            "passport": str(_write_json(target_dir / "solid_liquid_suspension_passport.json", blocked)),
            "fluent_hints": str(_write_json(target_dir / "solid_liquid_suspension_fluent_hints.json", hints)),
            "report": str(_write_text(target_dir / "solid_liquid_suspension_report.md", solid_liquid_suspension_report(blocked, hints))),
        }
        failure = AgentResult.failed(
            backend="fastcfd",
            operation="validate_solid_liquid_suspension",
            message="Solid-liquid suspension passport generation failed closed.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir), "case_file": str(case_file)},
        )
        failure.outputs.update({"artifacts": artifacts, "passport": blocked, "fluent_hints": hints})
        return failure.to_dict()


def run_solid_liquid_handoff_demo(*, output_dir: str | Path) -> dict[str, Any]:
    target = Path(output_dir)
    _ensure_dir(target)
    case_result = write_demo_solid_liquid_case(output_dir=target)
    passport_dir = target / "passport"
    passport_result = validate_solid_liquid_suspension_case_file(case_result["outputs"]["case_file"], output_dir=passport_dir)

    from .fluent_patch_compiler import compile_solver_plan_patch_from_passport, write_solver_plan_patch_bundle

    passport_file = passport_result["outputs"]["artifacts"]["passport"]
    patch = compile_solver_plan_patch_from_passport(passport_file)
    patch_result = write_solver_plan_patch_bundle(patch, output=target / "solver_plan_patch.json")
    artifacts = {
        "case_file": case_result["outputs"]["case_file"],
        "passport": passport_file,
        "fluent_hints": passport_result["outputs"]["artifacts"]["fluent_hints"],
        "report": passport_result["outputs"]["artifacts"]["report"],
        "solver_plan_patch": patch_result["outputs"]["artifacts"]["solver_plan_patch"],
        "solver_plan_patch_report": patch_result["outputs"]["artifacts"]["solver_plan_patch_report"],
    }
    result = AgentResult.success(
        backend="fastcfd",
        operation="solid_liquid_handoff_demo",
        message="Solid-liquid suspension handoff demo generated.",
        outputs={
            "case_result": case_result,
            "passport_result": passport_result,
            "patch_result": patch_result,
            "artifacts": artifacts,
            "passport": passport_result["outputs"]["passport"],
            "patch": patch,
        },
        metadata={"output_dir": str(target), "patch_status": patch.get("status")},
    )
    if patch_result.get("status") != "success":
        result.status = "partial"
        result.message = "Solid-liquid suspension demo generated, but the solver-plan patch is blocked."
    return result.to_dict()


def build_solid_liquid_suspension_passport(case: dict[str, Any], *, source_artifact: str = "inline_case") -> dict[str, Any]:
    errors = _validate_case(case)
    if errors:
        return _blocked_passport(case=case, blocking_errors=errors, source_artifact=source_artifact)

    computed = _compute_quantities(case)
    warnings = _warnings_from_computed(case, computed)
    blocking_errors: list[str] = []
    if computed["cell_particle_ratio"] < 1.0:
        blocking_errors.append("cell_particle_ratio is below 1; the mesh is inconsistent with a sub-grid particle model.")
    if computed["solid_volume_fraction"] > 0.64:
        blocking_errors.append("solid_volume_fraction is above the supported packing threshold.")

    status = "block" if blocking_errors else ("warn" if warnings else "pass")
    checks = _build_checks(case, computed, source_artifact)
    passport = {
        "schema_version": SOLID_LIQUID_PASSPORT_SCHEMA_VERSION,
        "case_name": str(case.get("case_name") or "solid_liquid_suspension_case"),
        "status": status,
        "summary": _summary(status, computed),
        "inputs": case,
        "computed_quantities": computed,
        "checks": checks,
        "fluent_hints": {},
        "warnings": warnings,
        "blocking_errors": blocking_errors,
        "limitations": list(LIMITATIONS),
        "metadata": {"source_artifact": source_artifact, "solver_execution": "not_attempted_passport_only"},
    }
    passport["fluent_hints"] = build_solid_liquid_fluent_hints(passport)
    return passport


def build_solid_liquid_fluent_hints(passport: dict[str, Any]) -> dict[str, Any]:
    computed = passport.get("computed_quantities", {})
    recommended_model = computed.get("recommended_model", "review_required")
    hints = {
        "schema_version": SOLID_LIQUID_HINTS_SCHEMA_VERSION,
        "case_name": passport.get("case_name"),
        "status": passport.get("status"),
        "recommended_model": recommended_model,
        "recommended_physics": {
            "multiphase": True,
            "recommended_model": recommended_model,
            "continuous_phase": "liquid",
            "dispersed_phase": "solid_particles",
            "gravity": True,
            "particle_wall_interaction_review_required": True,
        },
        "recommended_materials": {
            "continuous_phase": {"name": "liquid", "density_kg_m3": passport.get("inputs", {}).get("fluid_density_kg_m3")},
            "dispersed_phase": {
                "name": "solid_particles",
                "density_kg_m3": passport.get("inputs", {}).get("particle_density_kg_m3"),
                "diameter_m": passport.get("inputs", {}).get("particle_diameter_m"),
            },
        },
        "recommended_numerics": {
            "first_order_warmup": True,
            "bounded_volume_fraction": True,
            "time_step_limited_by_particle_relaxation": computed.get("particle_time_step_risk") in {"marginal", "under_resolved"},
            "frequent_checkpoint_during_first_pass": True,
        },
        "recommended_transient_controls": {
            "initial_time_step_s": computed.get("recommended_time_step_s"),
            "particle_relaxation_time_s": computed.get("particle_relaxation_time_s"),
            "particle_time_step_ratio": computed.get("particle_time_step_ratio"),
        },
        "recommended_monitors": [
            "solid_volume_fraction_bounds",
            "particle_mass_balance",
            "continuous_phase_mass_balance",
            "particle_residence_time",
            "particle_velocity_range",
            "settling_indicator",
            "pressure_drop",
            "wall_impact_if_available",
            "erosion_indicator_if_relevant",
        ],
        "recommended_postprocessing": [
            "particle_phase_summary",
            "coupling_strength_summary",
            "settling_vs_residence_summary",
            "particle_time_step_review",
        ],
        "hints": [
            {
                "category": "solid_liquid_model_selection",
                "recommendation": f"Use `{recommended_model}` as a reviewable Fluent model-selection starting point.",
                "evidence": ["solid_liquid_model_recommendation", "solid_liquid_volume_fraction_regime", "solid_liquid_mass_loading"],
            },
            {
                "category": "solid_liquid_particle_dynamics",
                "recommendation": "Review particle Reynolds number, Stokes number, and settling tendency before Fluent setup.",
                "evidence": ["solid_liquid_particle_reynolds", "solid_liquid_stokes_number", "solid_liquid_settling_velocity"],
            },
            {
                "category": "solid_liquid_numerics",
                "recommendation": "Use bounded volume fraction, conservative time step, and particle mass-balance monitors.",
                "evidence": ["solid_liquid_cell_particle_ratio", "solid_liquid_time_step_ratio", "solid_liquid_monitor_requirements"],
            },
        ],
        "warnings": list(passport.get("warnings", [])),
        "blocking_errors": list(passport.get("blocking_errors", [])),
        "limitations": list(passport.get("limitations", LIMITATIONS)),
        "metadata": {
            "source_passport_schema_version": passport.get("schema_version"),
            "solver_execution": "not_attempted_hints_only",
        },
    }
    return hints


def solid_liquid_suspension_report(passport: dict[str, Any], hints: dict[str, Any]) -> str:
    computed = passport.get("computed_quantities", {})
    inputs = passport.get("inputs", {})
    lines = [
        "# Solid-Liquid Suspension Physics Passport",
        "",
        f"Case name: `{passport.get('case_name')}`",
        f"Status: `{passport.get('status')}`",
        "",
        "## Input Properties",
        "",
        f"- Fluid density: `{inputs.get('fluid_density_kg_m3')}` kg/m^3",
        f"- Fluid dynamic viscosity: `{inputs.get('fluid_dynamic_viscosity_Pa_s')}` Pa*s",
        f"- Particle density: `{inputs.get('particle_density_kg_m3')}` kg/m^3",
        f"- Particle diameter: `{inputs.get('particle_diameter_m')}` m",
        f"- Solid volume fraction: `{inputs.get('solid_volume_fraction')}`",
        "",
        "## Particle Regime",
        "",
        f"- Particle Reynolds number: `{computed.get('particle_reynolds_number')}`",
        f"- Particle drag regime: `{computed.get('particle_drag_regime')}`",
        f"- Particle relaxation time: `{computed.get('particle_relaxation_time_s')}` s",
        f"- Stokes number: `{computed.get('stokes_number')}`",
        f"- Particle inertia regime: `{computed.get('particle_inertia_regime')}`",
        "",
        "## Settling And Residence",
        "",
        f"- Settling velocity: `{computed.get('settling_velocity_m_s')}` m/s",
        f"- Settling direction: `{computed.get('settling_direction')}`",
        f"- Settling regime: `{computed.get('settling_regime')}`",
        f"- Residence time: `{computed.get('residence_time_s')}` s",
        f"- Settling time: `{computed.get('settling_time_s')}` s",
        f"- Settling importance ratio: `{computed.get('settling_importance_ratio')}`",
        "",
        "## Coupling And Mesh",
        "",
        f"- Solid volume fraction regime: `{computed.get('solid_volume_fraction_regime')}`",
        f"- Particle mass loading: `{computed.get('particle_mass_loading')}`",
        f"- Coupling strength regime: `{computed.get('coupling_strength_regime')}`",
        f"- Cell-particle ratio: `{computed.get('cell_particle_ratio')}`",
        f"- Particle resolution warning: `{computed.get('particle_resolution_warning')}`",
        f"- Particle time-step ratio: `{computed.get('particle_time_step_ratio')}`",
        f"- Particle time-step risk: `{computed.get('particle_time_step_risk')}`",
        "",
        "## Fluent Recommendation",
        "",
        f"- Recommended model: `{hints.get('recommended_model')}`",
        f"- Recommended initial time step: `{computed.get('recommended_time_step_s')}` s",
        "",
        "## Required Monitors",
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
            "- Confirm particle size distribution.",
            "- Confirm particle density and sphericity.",
            "- Confirm solid volume fraction.",
            "- Confirm whether one-way or two-way coupling is acceptable.",
            "- Confirm wall interaction relevance.",
            "- Confirm erosion or impact relevance.",
            "- Confirm gravity direction.",
            "- Confirm whether DPM, Mixture, or Eulerian model is intended.",
            "- Confirm mesh is not pretending to resolve sub-grid particles.",
            "- Confirm time step resolves particle relaxation if transient.",
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
    if case.get("schema_version") != SOLID_LIQUID_CASE_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {case.get('schema_version')!r}")
    required_positive = [
        "fluid_density_kg_m3",
        "fluid_dynamic_viscosity_Pa_s",
        "particle_density_kg_m3",
        "particle_diameter_m",
        "length_scale_m",
        "cell_size_m",
        "time_step_s",
    ]
    for key in required_positive:
        try:
            if float(case.get(key)) <= 0.0:
                errors.append(f"{key} must be > 0.")
        except (TypeError, ValueError):
            errors.append(f"{key} must be numeric.")
    for key in ["solid_volume_fraction"]:
        try:
            value = float(case.get(key))
            if value < 0.0 or value > 0.64:
                errors.append(f"{key} must be between 0 and 0.64.")
        except (TypeError, ValueError):
            errors.append(f"{key} must be numeric.")
    for key in ["reference_velocity_m_s", "gravity_m_s2"]:
        try:
            if float(case.get(key)) < 0.0:
                errors.append(f"{key} must be >= 0.")
        except (TypeError, ValueError):
            errors.append(f"{key} must be numeric.")
    if case.get("relative_velocity_m_s") is not None:
        try:
            if float(case["relative_velocity_m_s"]) < 0.0:
                errors.append("relative_velocity_m_s must be >= 0.")
        except (TypeError, ValueError):
            errors.append("relative_velocity_m_s must be numeric.")
    if case.get("domain_height_m") is not None:
        try:
            if float(case["domain_height_m"]) <= 0.0:
                errors.append("domain_height_m must be > 0 when provided.")
        except (TypeError, ValueError):
            errors.append("domain_height_m must be numeric when provided.")
    return errors


def _compute_quantities(case: dict[str, Any]) -> dict[str, Any]:
    tiny = 1.0e-30
    rho_f = float(case["fluid_density_kg_m3"])
    mu_f = float(case["fluid_dynamic_viscosity_Pa_s"])
    rho_p = float(case["particle_density_kg_m3"])
    diameter = float(case["particle_diameter_m"])
    alpha = float(case["solid_volume_fraction"])
    velocity = float(case["reference_velocity_m_s"])
    length = float(case["length_scale_m"])
    height = float(case.get("domain_height_m") or length)
    gravity = float(case["gravity_m_s2"])
    cell_size = float(case["cell_size_m"])
    time_step = float(case["time_step_s"])
    kinematic = float(case.get("fluid_kinematic_viscosity_m2_s") or mu_f / rho_f)
    settling_velocity = (rho_p - rho_f) * gravity * diameter * diameter / (18.0 * mu_f)
    relative_estimated = case.get("relative_velocity_m_s") is None
    relative_velocity = float(case.get("relative_velocity_m_s") if case.get("relative_velocity_m_s") is not None else max(velocity, abs(settling_velocity)))
    particle_reynolds = rho_f * relative_velocity * diameter / mu_f
    tau_p = rho_p * diameter * diameter / (18.0 * mu_f)
    stokes = tau_p * velocity / max(length, tiny)
    settling_ratio = abs(settling_velocity) / max(velocity, tiny)
    residence_time = length / max(velocity, tiny)
    settling_time = height / max(abs(settling_velocity), tiny)
    settling_importance_ratio = residence_time / max(settling_time, tiny)
    mass_loading = alpha * rho_p / max((1.0 - alpha) * rho_f, tiny)
    cell_particle_ratio = cell_size / max(diameter, tiny)
    time_step_ratio = time_step / max(tau_p, tiny)
    recommended_dt = min(time_step, 0.1 * tau_p, 0.5 * cell_size / max(velocity, tiny))
    computed = {
        "fluid_kinematic_viscosity_m2_s": kinematic,
        "solid_volume_fraction": alpha,
        "relative_velocity_m_s": relative_velocity,
        "relative_velocity_estimated": relative_estimated,
        "particle_reynolds_number": particle_reynolds,
        "particle_drag_regime": _particle_drag_regime(particle_reynolds),
        "particle_relaxation_time_s": tau_p,
        "drag_correction_review_required": particle_reynolds >= 1.0,
        "drag_coefficient_schiller_naumann": _schiller_naumann_cd(particle_reynolds),
        "stokes_number": stokes,
        "particle_inertia_regime": _particle_inertia_regime(stokes),
        "settling_velocity_m_s": settling_velocity,
        "settling_direction": _settling_direction(settling_velocity),
        "settling_velocity_ratio": settling_ratio,
        "settling_regime": _settling_regime(settling_ratio),
        "settling_regime_note": _settling_note(settling_velocity),
        "domain_height_m": height,
        "domain_height_defaulted_to_length_scale": case.get("domain_height_m") is None,
        "residence_time_s": residence_time,
        "settling_time_s": settling_time,
        "settling_importance_ratio": settling_importance_ratio,
        "settling_importance": _settling_importance(settling_importance_ratio),
        "solid_volume_fraction_regime": _solid_volume_fraction_regime(alpha),
        "particle_mass_loading": mass_loading,
        "coupling_strength_regime": _coupling_strength_regime(mass_loading),
        "cell_particle_ratio": cell_particle_ratio,
        "particle_resolution_warning": _particle_resolution_warning(cell_particle_ratio),
        "particle_time_step_ratio": time_step_ratio,
        "particle_time_step_risk": _time_step_risk(time_step_ratio),
        "recommended_time_step_s": recommended_dt,
    }
    computed["recommended_model"] = _recommend_model(computed)
    computed["model_recommendation_reason"] = _model_recommendation_reason(computed)
    return computed


def _build_checks(case: dict[str, Any], computed: dict[str, Any], source_artifact: str) -> list[dict[str, Any]]:
    return [
        _check("solid_liquid_particle_reynolds", "particle_reynolds_number", computed["particle_reynolds_number"], "1", "Re_p = rho_f * U_rel * d_p / mu_f", f"Particle drag regime is {computed['particle_drag_regime']}.", "medium", source_artifact),
        _check("solid_liquid_stokes_number", "stokes_number", computed["stokes_number"], "1", "Stk = tau_p * U / L", f"Particle inertia regime is {computed['particle_inertia_regime']}.", "medium", source_artifact),
        _check("solid_liquid_settling_velocity", "settling_velocity_m_s", computed["settling_velocity_m_s"], "m/s", "v_settle = (rho_p-rho_f)*g*d_p^2/(18*mu_f)", f"Settling regime is {computed['settling_regime']}; residence comparison is {computed['settling_importance']}.", "medium", source_artifact),
        _check("solid_liquid_volume_fraction_regime", "solid_volume_fraction", computed["solid_volume_fraction"], "1", "trace/dilute/moderate/dense concentration thresholds", f"Volume fraction regime is {computed['solid_volume_fraction_regime']}.", "high", source_artifact),
        _check("solid_liquid_mass_loading", "particle_mass_loading", computed["particle_mass_loading"], "1", "alpha_s*rho_p/((1-alpha_s)*rho_f)", f"Coupling strength is {computed['coupling_strength_regime']}.", "high", source_artifact),
        _check("solid_liquid_cell_particle_ratio", "cell_particle_ratio", computed["cell_particle_ratio"], "1", "cell_size_m / particle_diameter_m", computed["particle_resolution_warning"], "high", source_artifact),
        _check("solid_liquid_time_step_ratio", "particle_time_step_ratio", computed["particle_time_step_ratio"], "1", "time_step_s / particle_relaxation_time_s", f"Particle time-step risk is {computed['particle_time_step_risk']}.", "high", source_artifact),
        _check("solid_liquid_model_recommendation", "recommended_model", computed["recommended_model"], "class", "Conservative model-selection logic from concentration, loading, Stokes number, settling, cell ratio, and time-step risk.", computed["model_recommendation_reason"], "medium", source_artifact),
        _check("solid_liquid_monitor_requirements", "required_monitors", ["solid_volume_fraction_bounds", "particle_mass_balance", "particle_velocity_range", "settling_indicator"], "review", "Solid-liquid first-pass Fluent setup must monitor bounded particle phase behavior.", "Monitor availability depends on the final Fluent setup.", "high", source_artifact),
    ]


def _warnings_from_computed(case: dict[str, Any], computed: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if computed["particle_reynolds_number"] >= 1.0:
        warnings.append("Particle Reynolds number is outside the Stokes drag regime; drag correction review is required.")
    if computed["particle_reynolds_number"] >= 1000.0:
        warnings.append("Particle Reynolds number is high; inertial drag and trajectory behavior require review.")
    if computed["stokes_number"] >= 1.0:
        warnings.append("Stokes number indicates strong particle inertia and possible trajectory decoupling.")
    elif computed["stokes_number"] >= 0.1:
        warnings.append("Stokes number indicates moderate particle inertia.")
    if computed["settling_regime"] == "strong":
        warnings.append("Settling velocity is strong relative to reference flow velocity.")
    elif computed["settling_regime"] == "moderate":
        warnings.append("Settling velocity may be relevant over the residence time.")
    if computed["coupling_strength_regime"] != "one_way_may_be_acceptable":
        warnings.append(f"Particle mass loading indicates {computed['coupling_strength_regime']}.")
    if computed["solid_volume_fraction_regime"] in {"dense", "very_dense_granular_review_required"}:
        warnings.append(f"Solid volume fraction regime is {computed['solid_volume_fraction_regime']}.")
    if computed["cell_particle_ratio"] < 5.0:
        warnings.append("Cell-particle ratio is near or below the sub-grid comfort range.")
    if computed["particle_time_step_risk"] != "resolved":
        warnings.append(f"Particle time step is {computed['particle_time_step_risk']}; smaller time step should be reviewed.")
    if computed["recommended_model"] == "review_required":
        warnings.append("Model recommendation is review_required because indicators are conflicting or numerically risky.")
    if case.get("relative_velocity_m_s") is None:
        warnings.append("relative_velocity_m_s was not provided; a conservative relative velocity estimate was used.")
    return warnings


def _recommend_model(computed: dict[str, Any]) -> str:
    alpha = computed["solid_volume_fraction"]
    loading = computed["particle_mass_loading"]
    stokes = computed["stokes_number"]
    settling = computed["settling_regime"]
    cell_ratio = computed["cell_particle_ratio"]
    time_risk = computed["particle_time_step_risk"]
    if alpha >= 0.3:
        return "eulerian_granular_review"
    if cell_ratio < 1.0:
        return "review_required"
    if alpha >= 0.1 or loading >= 1.0:
        return "eulerian_multiphase_review"
    if time_risk == "under_resolved" or cell_ratio < 3.0:
        return "review_required"
    if 0.01 <= alpha < 0.1:
        if stokes < 1.0 and settling in {"negligible", "moderate"}:
            return "mixture_model"
        return "review_required"
    if alpha < 0.01 and loading >= 0.1:
        return "dpm_two_way" if cell_ratio >= 5.0 else "review_required"
    if alpha < 0.01 and loading < 0.1 and stokes < 1.0:
        return "dpm_one_way"
    return "review_required"


def _model_recommendation_reason(computed: dict[str, Any]) -> str:
    return (
        f"recommended_model={computed['recommended_model']}; "
        f"volume_fraction={computed['solid_volume_fraction_regime']}, "
        f"mass_loading={computed['coupling_strength_regime']}, "
        f"Stk={computed['particle_inertia_regime']}, "
        f"settling={computed['settling_regime']}, "
        f"cell_ratio={computed['cell_particle_ratio']:.3g}, "
        f"time_step={computed['particle_time_step_risk']}."
    )


def _particle_drag_regime(reynolds: float) -> str:
    if reynolds < 1.0:
        return "stokes_drag"
    if reynolds < 1000.0:
        return "transitional_particle_drag"
    return "inertial_high_re_particle_drag"


def _particle_inertia_regime(stokes: float) -> str:
    if stokes < 0.1:
        return "particles_strongly_follow_fluid"
    if stokes < 1.0:
        return "moderate_particle_inertia"
    return "strong_particle_inertia_trajectory_decoupling"


def _settling_direction(velocity: float) -> str:
    if velocity > 0.0:
        return "settling"
    if velocity < 0.0:
        return "rising_or_buoyant"
    return "neutral"


def _settling_note(velocity: float) -> str:
    if velocity > 0.0:
        return "Particles are denser than the liquid and tend to settle under gravity."
    if velocity < 0.0:
        return "Particles are lighter than the liquid and tend to rise under gravity."
    return "Particle and fluid densities are balanced in this first-pass estimate."


def _settling_regime(ratio: float) -> str:
    if ratio < 0.01:
        return "negligible"
    if ratio < 0.1:
        return "moderate"
    return "strong"


def _settling_importance(ratio: float) -> str:
    if ratio < 0.1:
        return "weak_over_residence_time"
    if ratio < 1.0:
        return "may_be_relevant"
    return "likely_important"


def _solid_volume_fraction_regime(alpha: float) -> str:
    if alpha < 1.0e-3:
        return "trace_very_dilute"
    if alpha < 1.0e-2:
        return "dilute"
    if alpha < 0.1:
        return "moderate"
    if alpha < 0.3:
        return "dense"
    return "very_dense_granular_review_required"


def _coupling_strength_regime(mass_loading: float) -> str:
    if mass_loading < 0.1:
        return "one_way_may_be_acceptable"
    if mass_loading < 1.0:
        return "two_way_likely_relevant"
    return "strong_two_way_or_four_way_review_required"


def _particle_resolution_warning(ratio: float) -> str:
    if ratio < 1.0:
        return "particle_larger_than_cell_model_inconsistent"
    if ratio < 3.0:
        return "cell_size_comparable_to_particle_review_required"
    if ratio < 10.0:
        return "particle_sub_grid_but_resolution_review_required"
    return "particle_sub_grid"


def _time_step_risk(ratio: float) -> str:
    if ratio < 0.1:
        return "resolved"
    if ratio < 1.0:
        return "marginal"
    return "under_resolved"


def _schiller_naumann_cd(reynolds: float) -> float | None:
    if reynolds <= 0.0:
        return None
    if reynolds < 1000.0:
        return 24.0 / reynolds * (1.0 + 0.15 * reynolds**0.687)
    return 0.44


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
        "source_module": "solid_liquid_suspension",
        "source_artifact": source_artifact,
        "source_schema_version": SOLID_LIQUID_PASSPORT_SCHEMA_VERSION,
        "source_status": "screened",
        "quantity_name": quantity_name,
        "quantity_value": quantity_value,
        "quantity_units": quantity_units,
        "threshold_or_rule": threshold_or_rule,
        "interpretation": interpretation,
        "confidence": confidence,
        "limitations": list(LIMITATIONS),
    }


def _blocked_passport(
    *,
    case: dict[str, Any],
    blocking_errors: list[str],
    source_artifact: str,
    computed_quantities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SOLID_LIQUID_PASSPORT_SCHEMA_VERSION,
        "case_name": str(case.get("case_name") or "solid_liquid_suspension_case"),
        "status": "block",
        "summary": "Solid-liquid suspension screening blocked this case before Fluent handoff.",
        "inputs": case,
        "computed_quantities": computed_quantities or {},
        "checks": [],
        "fluent_hints": {},
        "warnings": [],
        "blocking_errors": blocking_errors,
        "limitations": list(LIMITATIONS),
        "metadata": {"source_artifact": source_artifact, "solver_execution": "blocked_before_fluent_handoff"},
    }


def _summary(status: str, computed: dict[str, Any]) -> str:
    return (
        f"Solid-liquid suspension status is {status}. "
        f"Recommended model is {computed.get('recommended_model')}, "
        f"particle Re is {computed.get('particle_reynolds_number'):.3g}, "
        f"Stokes number is {computed.get('stokes_number'):.3g}, "
        f"settling is {computed.get('settling_regime')}, and "
        f"mass loading is {computed.get('coupling_strength_regime')}."
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

