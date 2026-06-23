"""Compile FastFluent evidence artifacts into solver-plan patch bundles."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .solver_plan_patch import (
    PatchEvidence,
    PatchOperation,
    SolverPlanPatch,
    SOLVER_PLAN_PATCH_SCHEMA_VERSION,
    validate_solver_plan_patch,
    write_solver_plan_patch_json,
    write_solver_plan_patch_report,
)
from .steam_air_condensation import (
    STEAM_AIR_PASSPORT_SCHEMA_VERSION,
    validate_steam_air_condensation_case_file,
    write_demo_steam_air_case,
)
from .steam_air_condensation_v2 import (
    STEAM_AIR_V2_FLUENT_HINTS_SCHEMA_VERSION,
    STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION,
)
from .vof import VOF_HINTS_SCHEMA_VERSION, VOF_PASSPORT_SCHEMA_VERSION, build_vof_physics_passport, demo_vof_case
from .turbulence import (
    TURBULENCE_HINTS_SCHEMA_VERSION,
    TURBULENCE_PASSPORT_SCHEMA_VERSION,
    build_turbulence_passport,
    demo_turbulence_case,
)
from .rheology import (
    RHEOLOGY_HINTS_SCHEMA_VERSION,
    RHEOLOGY_PASSPORT_SCHEMA_VERSION,
    build_rheology_passport,
    demo_rheology_case,
)
from .solid_liquid_suspension import SOLID_LIQUID_HINTS_SCHEMA_VERSION, SOLID_LIQUID_PASSPORT_SCHEMA_VERSION
from .wax_rheology_phase_change import (
    WAX_RHEOLOGY_HINTS_SCHEMA_VERSION,
    WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION,
    compile_wax_rheology_phase_change_patch,
)


SEVERITY = {"pass": 0, "warn": 1, "block": 2}


def compile_solver_plan_patch_from_passport(passport: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Dispatch a supported FastFluent passport into a solver-plan patch."""

    payload, source_artifact = _load_payload(passport)
    payload = _extract_supported_payload(payload)
    schema = payload.get("schema_version")
    if schema == STEAM_AIR_PASSPORT_SCHEMA_VERSION:
        return compile_solver_plan_patch_from_steam_air_passport(payload, source_artifact=source_artifact)
    if schema == STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION:
        return compile_solver_plan_patch_from_steam_air_v2_passport(payload, source_artifact=source_artifact)
    if schema == VOF_PASSPORT_SCHEMA_VERSION:
        return compile_vof_patch_from_artifact(payload, source_artifact=source_artifact)
    if schema == TURBULENCE_PASSPORT_SCHEMA_VERSION:
        return compile_turbulence_patch_from_artifact(payload, source_artifact=source_artifact)
    if schema == RHEOLOGY_PASSPORT_SCHEMA_VERSION:
        return compile_rheology_patch_from_artifact(payload, source_artifact=source_artifact)
    if schema == SOLID_LIQUID_PASSPORT_SCHEMA_VERSION:
        return compile_solid_liquid_patch_from_artifact(payload, source_artifact=source_artifact)
    if schema == WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION:
        return compile_wax_rheology_phase_change_patch(payload, source_artifact=source_artifact)
    if schema in {
        STEAM_AIR_V2_FLUENT_HINTS_SCHEMA_VERSION,
        VOF_HINTS_SCHEMA_VERSION,
        TURBULENCE_HINTS_SCHEMA_VERSION,
        RHEOLOGY_HINTS_SCHEMA_VERSION,
        SOLID_LIQUID_HINTS_SCHEMA_VERSION,
        WAX_RHEOLOGY_HINTS_SCHEMA_VERSION,
    }:
        return _compile_hint_only_patch(payload, source_artifact=source_artifact)
    return _unsupported_passport_patch(payload, source_artifact=source_artifact)


def compile_solver_plan_patch_from_hint_artifacts(evidence_files: list[str | Path]) -> dict[str, Any]:
    """Compile supported evidence artifacts, then merge them into one patch."""

    patches = [compile_solver_plan_patch_from_passport(path) for path in evidence_files]
    return merge_solver_plan_patches(patches)


def compile_vof_patch_from_artifact(
    artifact: str | Path | dict[str, Any],
    *,
    source_artifact: str | None = None,
) -> dict[str, Any]:
    """Compile an existing VOF passport into a non-executing solver-plan patch."""

    payload, loaded_artifact = _load_payload(artifact)
    payload = _extract_supported_payload(payload)
    artifact_path = source_artifact or loaded_artifact
    if payload.get("schema_version") != VOF_PASSPORT_SCHEMA_VERSION:
        return _unsupported_passport_patch(payload, source_artifact=artifact_path)
    status = _passport_status(payload)
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    warnings = list(payload.get("warnings", []))
    blocking_errors = list(payload.get("blocking_errors", []))
    limitations = list(payload.get("limitations", []))
    evidence = _vof_evidence(payload, artifact_path, status)
    evidence_ids = {item.evidence_id for item in evidence}

    if status == "block":
        return _blocked_patch_from_evidence(
            payload,
            evidence,
            source_artifact=artifact_path,
            compiler="vof",
            warnings=warnings,
            blocking_errors=blocking_errors or ["VOF passport blocked Fluent handoff."],
            limitations=limitations,
        )

    operations: list[PatchOperation] = [
        PatchOperation("replace", "/physics/time", "transient", "VOF interface tracking requires a transient first-pass setup.", ["vof_time_step_restriction"], "high", []),
        PatchOperation("replace", "/physics/multiphase/enabled", True, "VOF passport recommends multiphase tracking.", ["vof_regime_numbers"], "high", []),
        PatchOperation("replace", "/physics/multiphase/model", "vof", "Existing VOF passport targets immiscible interface tracking.", ["vof_regime_numbers"], "high", []),
        PatchOperation("replace", "/transient/adaptive_time_step/enabled", True, "VOF passport recommends conservative transient time-step control.", ["vof_time_step_restriction"], "medium", []),
        PatchOperation("replace", "/numerics/initial_discretization", "first-order-upwind", "Use first-order warm-up before sharper interface schemes are trusted.", ["vof_time_step_restriction"], "medium", []),
        PatchOperation(
            "replace",
            "/numerics/later_discretization",
            "second-order-upwind-after-stable-warmup",
            "Use higher-order discretization only after stable VOF monitor histories.",
            ["vof_time_step_restriction"],
            "medium",
            [],
        ),
    ]
    if checks.get("surface_tension_n_m") is not None:
        operations.extend(
            [
                PatchOperation("replace", "/physics/surface_tension/enabled", True, "VOF passport contains surface-tension evidence.", ["vof_surface_tension_importance"], "medium", []),
                PatchOperation(
                    "replace",
                    "/physics/surface_tension/value_N_m",
                    checks.get("surface_tension_n_m"),
                    "Preserve the VOF passport surface-tension value for reviewer setup.",
                    ["vof_surface_tension_importance"],
                    "medium",
                    [],
                ),
            ]
        )
    recommended_dt = _min_positive(checks.get("recommended_time_step_s_by_courant"), checks.get("capillary_time_step_s_advisory"))
    if recommended_dt is not None:
        operations.append(
            PatchOperation(
                "replace",
                "/transient/initial_time_step_s",
                recommended_dt,
                "Recommended VOF time step from Courant and capillary restrictions.",
                ["vof_time_step_restriction"],
                "medium",
                ["Final Fluent time step still requires CFL monitor review."],
            )
        )
    operations.extend(_vof_monitor_and_output_patches(evidence_ids))
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or "vof_patch_case"),
        status="warn" if status == "warn" or warnings else "pass",
        summary="Existing FastFluent VOF evidence compiled into a non-executing Fluent solver-plan patch.",
        evidence=evidence,
        patches=operations,
        warnings=warnings,
        blocking_errors=[],
        limitations=limitations + ["This patch recommends VOF setup fields only; it does not execute Fluent or solve VOF."],
        metadata={"source_artifact": artifact_path, "compiler": "vof"},
    )
    return patch.to_dict()


def compile_turbulence_patch_from_artifact(
    artifact: str | Path | dict[str, Any],
    *,
    source_artifact: str | None = None,
) -> dict[str, Any]:
    """Compile an existing turbulence passport into a non-executing solver-plan patch."""

    payload, loaded_artifact = _load_payload(artifact)
    payload = _extract_supported_payload(payload)
    artifact_path = source_artifact or loaded_artifact
    if payload.get("schema_version") != TURBULENCE_PASSPORT_SCHEMA_VERSION:
        return _unsupported_passport_patch(payload, source_artifact=artifact_path)
    status = _passport_status(payload)
    warnings = list(payload.get("warnings", []))
    blocking_errors = list(payload.get("blocking_errors", []))
    limitations = list(payload.get("limitations", []))
    evidence = _turbulence_evidence(payload, artifact_path, status)

    if status == "block":
        return _blocked_patch_from_evidence(
            payload,
            evidence,
            source_artifact=artifact_path,
            compiler="turbulence",
            warnings=warnings,
            blocking_errors=blocking_errors or ["Turbulence passport blocked Fluent handoff."],
            limitations=limitations,
        )

    model = _turbulence_model_recommendation(payload)
    operations: list[PatchOperation] = [
        PatchOperation("replace", "/physics/turbulence/model", model, "Turbulence passport model recommendation for reviewer setup.", ["turbulence_model_recommendation"], "medium", []),
        PatchOperation(
            "replace",
            "/physics/turbulence/near_wall_treatment",
            _near_wall_treatment(payload),
            "Near-wall treatment remains evidence-backed and reviewer-confirmed.",
            ["turbulence_y_plus_estimate"],
            "medium",
            [],
        ),
        PatchOperation("replace", "/numerics/initial_discretization", "first-order-upwind", "Use first-order warm-up for turbulence setup stability.", ["turbulence_reynolds_regime"], "medium", []),
        PatchOperation(
            "replace",
            "/numerics/later_discretization",
            "second-order-upwind-after-stable-warmup",
            "Use higher-order schemes only after stable turbulence monitor histories.",
            ["turbulence_reynolds_regime"],
            "medium",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "wall_y_plus", "quantity": "y_plus", "reduction": "min_max", "required": True},
            "Turbulence passport requires y-plus review.",
            ["turbulence_y_plus_estimate"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/wall",
            {"name": "wall_shear_stress", "quantity": "wall_shear_stress", "reduction": "min_max", "required": True},
            "Turbulence wall behavior requires wall shear stress monitoring.",
            ["turbulence_wall_monitor_requirements"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/wall",
            {"name": "skin_friction_coefficient_if_available", "quantity": "skin_friction_coefficient", "reduction": "surface_average", "required": False},
            "Skin-friction coefficient is useful when Fluent exposes the report definition.",
            ["turbulence_wall_monitor_requirements"],
            "medium",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/acceptance_criteria",
            {"name": "y_plus_review_required", "rule": "near-wall y-plus must be reviewed against the selected turbulence model", "required": True},
            "Turbulence model selection depends on near-wall resolution.",
            ["turbulence_y_plus_estimate"],
            "high",
            [],
        ),
    ]
    target_y_plus = _target_y_plus(payload)
    if target_y_plus:
        operations.append(
            PatchOperation(
                "replace",
                "/mesh/near_wall/target_y_plus",
                target_y_plus,
                "Preserve turbulence passport target y-plus range.",
                ["turbulence_y_plus_estimate"],
                "medium",
                [],
            )
        )
    if payload.get("flow_regime") == "transitional":
        warnings.append("Turbulence regime is transitional; patch uses review-required model instead of forcing a RANS model.")
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or "turbulence_patch_case"),
        status="warn" if status == "warn" or warnings else "pass",
        summary="Existing FastFluent turbulence evidence compiled into a non-executing Fluent solver-plan patch.",
        evidence=evidence,
        patches=operations,
        warnings=warnings,
        blocking_errors=[],
        limitations=limitations + ["This patch recommends turbulence setup fields only; it is not a production turbulence validation."],
        metadata={"source_artifact": artifact_path, "compiler": "turbulence"},
    )
    return patch.to_dict()


def compile_rheology_patch_from_artifact(
    artifact: str | Path | dict[str, Any],
    *,
    source_artifact: str | None = None,
) -> dict[str, Any]:
    """Compile an existing rheology passport into a non-executing solver-plan patch."""

    payload, loaded_artifact = _load_payload(artifact)
    payload = _extract_supported_payload(payload)
    artifact_path = source_artifact or loaded_artifact
    if payload.get("schema_version") != RHEOLOGY_PASSPORT_SCHEMA_VERSION:
        return _unsupported_passport_patch(payload, source_artifact=artifact_path)
    status = _passport_status(payload)
    warnings = list(payload.get("warnings", []))
    blocking_errors = list(payload.get("blocking_errors", []))
    limitations = list(payload.get("limitations", []))
    evidence = _rheology_evidence(payload, artifact_path, status)

    if status == "block":
        return _blocked_patch_from_evidence(
            payload,
            evidence,
            source_artifact=artifact_path,
            compiler="rheology",
            warnings=warnings,
            blocking_errors=blocking_errors or ["Rheology passport blocked Fluent handoff."],
            limitations=limitations,
        )

    operations: list[PatchOperation] = []
    model = str(payload.get("model") or "review-required")
    if model != "newtonian":
        operations.extend(
            [
                PatchOperation(
                    "append_unique",
                    "/materials/property_models",
                    {"name": "non_newtonian_viscosity", "model": model, "review_required": True},
                    "Rheology passport detected a non-Newtonian material model.",
                    ["rheology_non_newtonian_status", "rheology_viscosity_model"],
                    "high",
                    ["No UDF or executable material code is generated."],
                ),
                PatchOperation(
                    "replace",
                    "/physics/material_model",
                    "non-newtonian-review-required",
                    "Fluent material model requires reviewer confirmation for non-Newtonian viscosity.",
                    ["rheology_viscosity_model"],
                    "medium",
                    ["No Fluent material card is emitted in this goal."],
                ),
            ]
        )
    else:
        operations.append(
            PatchOperation(
                "append_unique",
                "/materials/property_models",
                {"name": "constant_viscosity", "review_required": True},
                "Rheology passport detected Newtonian material behavior.",
                ["rheology_viscosity_model"],
                "medium",
                [],
            )
        )
    operations.extend(
        [
            PatchOperation(
                "append_unique",
                "/monitors/global",
                {"name": "viscosity_min_max", "quantity": "dynamic_viscosity", "reduction": "min_max", "required": True},
                "Rheology passport requires viscosity bounds to be monitored.",
                ["rheology_viscosity_range"],
                "high",
                [],
            ),
            PatchOperation(
                "append_unique",
                "/acceptance_criteria",
                {"name": "bounded_viscosity_range", "rule": "dynamic viscosity remains finite and inside reviewed bounds", "required": True},
                "Rheology passport provides finite positive viscosity range evidence.",
                ["rheology_viscosity_range"],
                "high",
                [],
            ),
            PatchOperation(
                "replace",
                "/numerics/source_term_controls/ramping",
                True,
                "Conservative ramping is recommended for high-contrast material-property setup.",
                ["rheology_viscosity_range"],
                "medium",
                [],
            ),
            PatchOperation(
                "replace",
                "/numerics/source_term_controls/clamp",
                True,
                "Clamp material-property related updates to avoid unbounded viscosity behavior.",
                ["rheology_viscosity_range"],
                "medium",
                [],
            ),
            PatchOperation(
                "append_unique",
                "/postprocessing/required_outputs",
                {"name": "viscosity_field_summary", "required": True},
                "Rheology passport requires viscosity-field summary review.",
                ["rheology_monitor_requirements"],
                "high",
                [],
            ),
        ]
    )
    if payload.get("temperature_k") is not None:
        operations.append(
            PatchOperation(
                "append_unique",
                "/monitors/global",
                {"name": "temperature_min_max", "quantity": "temperature", "reduction": "min_max", "required": True},
                "Temperature monitor is included because the rheology artifact records a reference temperature.",
                ["rheology_viscosity_model"],
                "medium",
                [],
            )
        )
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    if checks.get("viscosity_ratio") and float(checks["viscosity_ratio"]) > 1000.0:
        warnings.append("Rheology viscosity ratio is large; reviewer should confirm Fluent material-property stability.")
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or "rheology_patch_case"),
        status="warn" if status == "warn" or warnings else "pass",
        summary="Existing FastFluent rheology evidence compiled into a non-executing Fluent solver-plan patch.",
        evidence=evidence,
        patches=operations,
        warnings=warnings,
        blocking_errors=[],
        limitations=limitations + ["This patch recommends material-property setup fields only; it does not generate UDF code."],
        metadata={"source_artifact": artifact_path, "compiler": "rheology"},
    )
    return patch.to_dict()


def compile_solid_liquid_patch_from_artifact(
    artifact: str | Path | dict[str, Any],
    *,
    source_artifact: str | None = None,
) -> dict[str, Any]:
    """Compile a solid-liquid suspension passport into a solver-plan patch."""

    payload, loaded_artifact = _load_payload(artifact)
    payload = _extract_supported_payload(payload)
    artifact_path = source_artifact or loaded_artifact
    if payload.get("schema_version") != SOLID_LIQUID_PASSPORT_SCHEMA_VERSION:
        return _unsupported_passport_patch(payload, source_artifact=artifact_path)
    status = _passport_status(payload)
    warnings = list(payload.get("warnings", []))
    blocking_errors = list(payload.get("blocking_errors", []))
    limitations = list(payload.get("limitations", []))
    evidence = [_evidence_from_check(check, source_artifact=artifact_path, source_status=status) for check in payload.get("checks", [])]
    evidence_ids = {item.evidence_id for item in evidence}

    if status == "block":
        return _blocked_patch_from_evidence(
            payload,
            evidence,
            source_artifact=artifact_path,
            compiler="solid_liquid_suspension",
            warnings=warnings,
            blocking_errors=blocking_errors or ["Solid-liquid suspension passport blocked Fluent handoff."],
            limitations=limitations,
        )

    computed = payload.get("computed_quantities", {}) if isinstance(payload.get("computed_quantities"), dict) else {}
    recommended_model = str(computed.get("recommended_model") or "review_required")
    if recommended_model == "review_required":
        patch_model = "review-required"
    else:
        patch_model = recommended_model
    operations: list[PatchOperation] = [
        PatchOperation(
            "replace",
            "/physics/multiphase/enabled",
            True,
            "Solid-liquid suspension evidence requires a multiphase setup review.",
            ["solid_liquid_model_recommendation", "solid_liquid_volume_fraction_regime"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/physics/multiphase/model",
            patch_model,
            "Solid-liquid suspension passport recommends a Fluent multiphase model class.",
            ["solid_liquid_model_recommendation"],
            "medium",
            ["This is a setup recommendation only; it does not execute Fluent."],
        ),
        PatchOperation(
            "replace",
            "/physics/gravity/enabled",
            True,
            "Settling evidence requires gravity to be explicitly reviewed.",
            ["solid_liquid_settling_velocity"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/materials/phases/continuous",
            "liquid",
            "Solid-liquid suspension case defines the liquid as continuous phase.",
            ["solid_liquid_model_recommendation"],
            "medium",
            [],
        ),
        PatchOperation(
            "replace",
            "/materials/phases/dispersed",
            "solid_particles",
            "Solid-liquid suspension case defines particles as dispersed phase.",
            ["solid_liquid_model_recommendation"],
            "medium",
            [],
        ),
        PatchOperation(
            "replace",
            "/transient/initial_time_step_s",
            computed.get("recommended_time_step_s"),
            "Initial time step is limited by particle relaxation and cell convection scales.",
            ["solid_liquid_time_step_ratio", "solid_liquid_cell_particle_ratio"],
            "medium",
            ["Final Fluent time step must be checked against particle and continuous-phase monitor histories."],
        ),
    ]
    operations.extend(_solid_liquid_monitor_patches(evidence_ids))
    operations.extend(_solid_liquid_postprocessing_patches())
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or "solid_liquid_suspension_case"),
        status="warn" if status == "warn" or warnings else "pass",
        summary="FastFluent solid-liquid suspension passport compiled into a non-executing Fluent solver-plan patch.",
        evidence=evidence,
        patches=operations,
        warnings=warnings,
        blocking_errors=[],
        limitations=limitations
        + [
            "This patch recommends Fluent setup fields only; it does not execute Fluent, track particles, or solve multiphase CFD.",
            "DPM, Mixture, and Eulerian recommendations require reviewer confirmation against the final mesh and particle distribution.",
        ],
        metadata={"source_artifact": artifact_path, "compiler": "solid_liquid_suspension"},
    )
    return patch.to_dict()


def compile_solver_plan_patch_from_steam_air_passport(
    passport: str | Path | dict[str, Any],
    *,
    source_artifact: str | None = None,
) -> dict[str, Any]:
    payload, loaded_artifact = _load_payload(passport)
    artifact = source_artifact or loaded_artifact
    case_name = str(payload.get("case_name") or "steam_air_condensation_case")
    status = payload.get("status") if payload.get("status") in SEVERITY else "block"
    evidence = [_evidence_from_check(check, source_artifact=artifact, source_status=str(status)) for check in payload.get("checks", [])]
    warnings = list(payload.get("warnings", []))
    blocking_errors = list(payload.get("blocking_errors", []))
    limitations = list(payload.get("limitations", []))

    if status == "block":
        patch = SolverPlanPatch(
            case_name=case_name,
            status="block",
            summary="FastFluent steam-air passport blocked Fluent handoff.",
            evidence=evidence,
            patches=[
                PatchOperation(
                    op="block",
                    path="/runtime/fluent_execution_allowed",
                    value=False,
                    reason="Steam-air condensation passport reported blocking errors.",
                    evidence_refs=[item.evidence_id for item in evidence],
                    confidence="high",
                    limitations=["Resolve passport blocking errors before generating executable Fluent setup."],
                )
            ],
            warnings=warnings,
            blocking_errors=blocking_errors or ["Unsupported or blocked steam-air passport."],
            limitations=limitations,
            metadata={"source_passport": artifact, "compiler": "steam_air_condensation"},
        )
        return patch.to_dict()

    computed = payload.get("computed_quantities", {})
    patches: list[PatchOperation] = [
        PatchOperation(
            op="replace",
            path="/physics/solver/type",
            value="pressure-based",
            reason="Recommended first-pass Fluent solver type for low-Mach transient steam-air thermal flow.",
            evidence_refs=["steam_air_regime_first_pass"],
            confidence="medium",
            limitations=["Compressibility and high-Mach effects are not assessed by this passport."],
        ),
        PatchOperation(
            op="replace",
            path="/physics/time",
            value="transient",
            reason="Condensation source terms and wall thermal response require transient review.",
            evidence_refs=["steam_air_recommended_time_step"],
            confidence="high",
            limitations=[],
        ),
        PatchOperation(
            op="replace",
            path="/physics/energy/enabled",
            value=True,
            reason="Wall condensation and latent heat screening require energy transport.",
            evidence_refs=["steam_air_wall_below_saturation"],
            confidence="high",
            limitations=[],
        ),
        PatchOperation(
            op="replace",
            path="/physics/species_transport/enabled",
            value=True,
            reason="Steam-air mixture and non-condensable gas risk require species tracking.",
            evidence_refs=["steam_air_species_consistency", "steam_air_noncondensable_risk"],
            confidence="high",
            limitations=[],
        ),
        PatchOperation(
            op="replace",
            path="/physics/material_model",
            value="ideal-gas-mixture",
            reason="Use a simple reviewable steam-air mixture model for first-pass setup.",
            evidence_refs=["steam_air_species_consistency"],
            confidence="medium",
            limitations=["Temperature-dependent material properties must be reviewed in Fluent."],
        ),
        PatchOperation(
            op="replace",
            path="/physics/mixture/species",
            value=["h2o", "o2", "n2"],
            reason="Steam-air case requires steam plus non-condensable air species.",
            evidence_refs=["steam_air_species_consistency", "steam_air_noncondensable_risk"],
            confidence="medium",
            limitations=["Air is represented by O2/N2 species for setup planning."],
        ),
        PatchOperation(
            op="replace",
            path="/transient/initial_time_step_s",
            value=computed.get("recommended_time_step_s"),
            reason="Recommended time step from near-wall thermal diffusion and source stiffness screening.",
            evidence_refs=["steam_air_recommended_time_step"],
            confidence="medium",
            limitations=["Final time step must be checked against Fluent CFL and monitor histories."],
        ),
        PatchOperation(
            op="replace",
            path="/transient/adaptive_time_step/enabled",
            value=True,
            reason="Early transient condensation should be monitored with conservative adaptive stepping.",
            evidence_refs=["steam_air_recommended_time_step", "steam_air_source_stiffness_risk"],
            confidence="medium",
            limitations=[],
        ),
        PatchOperation(
            op="replace",
            path="/numerics/initial_discretization",
            value="first-order-upwind",
            reason="Use first-order warm-up before higher-order discretization in a stiff condensation start.",
            evidence_refs=["steam_air_source_stiffness_risk"],
            confidence="medium",
            limitations=["Switch to higher-order schemes only after stable monitor histories."],
        ),
        PatchOperation(
            op="replace",
            path="/numerics/source_term_controls/ramping",
            value=True,
            reason="Condensation source-term stiffness screening recommends source ramping.",
            evidence_refs=["steam_air_source_stiffness_risk"],
            confidence="high",
            limitations=[],
        ),
        PatchOperation(
            op="replace",
            path="/numerics/source_term_controls/clamp",
            value=True,
            reason="Condensation source-term stiffness screening recommends source clamps and bounds.",
            evidence_refs=["steam_air_source_stiffness_risk"],
            confidence="high",
            limitations=[],
        ),
        PatchOperation(
            op="replace",
            path="/source_terms/condensation/model",
            value="near_wall_limited_engineering",
            reason="The passport only supports the near-wall limited engineering condensation source model.",
            evidence_refs=["steam_air_wall_below_saturation", "steam_air_source_stiffness_risk"],
            confidence="medium",
            limitations=["This recommendation does not generate or execute UDF source code."],
        ),
    ]
    patches.extend(_monitor_patches())
    patches.extend(_postprocessing_and_acceptance_patches())

    patch = SolverPlanPatch(
        case_name=case_name,
        status="warn" if status == "warn" or warnings else "pass",
        summary="FastFluent steam-air passport compiled into a non-executing Fluent solver-plan patch.",
        evidence=evidence,
        patches=patches,
        warnings=warnings,
        blocking_errors=[],
        limitations=limitations
        + [
            "This patch recommends Fluent solver-plan fields only; it does not edit Fluent files or execute Fluent.",
            "Reviewer approval is required before any future Fluent execution adapter consumes this patch.",
        ],
        metadata={
            "source_passport": artifact,
            "compiler": "steam_air_condensation",
            "schema_version": SOLVER_PLAN_PATCH_SCHEMA_VERSION,
        },
    )
    return patch.to_dict()


def compile_solver_plan_patch_from_steam_air_v2_passport(
    passport: str | Path | dict[str, Any],
    *,
    source_artifact: str | None = None,
) -> dict[str, Any]:
    payload, loaded_artifact = _load_payload(passport)
    artifact = source_artifact or loaded_artifact
    case_name = str(payload.get("case_name") or "steam_air_condensation_v2_case")
    status = payload.get("status") if payload.get("status") in SEVERITY else "block"
    evidence = [_evidence_from_check(check, source_artifact=artifact, source_status=str(status)) for check in payload.get("checks", [])]
    warnings = list(payload.get("warnings", []))
    blocking_errors = list(payload.get("blocking_errors", []))
    limitations = list(payload.get("limitations", []))

    if status == "block":
        patch = SolverPlanPatch(
            case_name=case_name,
            status="block",
            summary="FastFluent steam-air v2 passport blocked Fluent handoff.",
            evidence=evidence,
            patches=[
                PatchOperation(
                    op="block",
                    path="/runtime/fluent_execution_allowed",
                    value=False,
                    reason="Steam-air v2 passport reported blocking errors.",
                    evidence_refs=[item.evidence_id for item in evidence],
                    confidence="high",
                    limitations=["Resolve passport blocking errors before generating executable Fluent setup."],
                )
            ],
            warnings=warnings,
            blocking_errors=blocking_errors or ["Unsupported or blocked steam-air v2 passport."],
            limitations=limitations,
            metadata={"source_passport": artifact, "compiler": "steam_air_condensation_v2"},
        )
        return patch.to_dict()

    computed = payload.get("computed_quantities", {})
    source_controls = computed.get("source_term_controls", {}) if isinstance(computed.get("source_term_controls"), dict) else {}
    flow_regime = str(computed.get("flow_regime") or "review-required")
    turbulence_model = "laminar" if flow_regime == "laminar" else ("k-omega-sst-review-required" if flow_regime == "turbulent" else "transition-review-required")
    operations: list[PatchOperation] = [
        PatchOperation(
            "replace",
            "/physics/solver/type",
            "pressure-based",
            "Steam-air v2 remains a low-Mach pressure-based Fluent setup recommendation.",
            ["steam_air_v2_reynolds_number"],
            "medium",
            ["Compressibility and high-Mach effects are not validated by this passport."],
        ),
        PatchOperation(
            "replace",
            "/physics/time",
            "transient",
            "Condensation source terms, heat transfer, and species boundary-layer response require transient review.",
            ["steam_air_v2_source_term_stiffness"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/physics/energy/enabled",
            True,
            "Latent heat and HTC estimates require energy transport in the downstream Fluent setup.",
            ["steam_air_v2_heat_transfer_estimate", "steam_air_v2_source_term_dimension_check"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/physics/species_transport/enabled",
            True,
            "Steam-air condensation v2 requires steam and non-condensable air species tracking.",
            ["steam_air_v2_species_consistency", "steam_air_v2_mass_transfer_resistance"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/physics/turbulence/model",
            turbulence_model,
            "Reynolds-number screening sets a reviewer-owned turbulence model recommendation.",
            ["steam_air_v2_reynolds_number"],
            "medium",
            ["The final turbulence model still requires Fluent mesh and y-plus review."],
        ),
        PatchOperation(
            "replace",
            "/physics/material_model",
            "ideal-gas-mixture",
            "Use a reviewable ideal-gas steam-air mixture for first-pass setup.",
            ["steam_air_v2_species_consistency"],
            "medium",
            ["Temperature-dependent material properties must be reviewed in Fluent."],
        ),
        PatchOperation(
            "replace",
            "/physics/mixture/species",
            ["h2o", "o2", "n2"],
            "Steam-air v2 keeps steam and air species explicit for monitor and balance checks.",
            ["steam_air_v2_species_consistency"],
            "medium",
            ["Air is represented by O2/N2 species for setup planning."],
        ),
        PatchOperation(
            "replace",
            "/transient/initial_time_step_s",
            computed.get("recommended_time_step_s"),
            "Recommended time step comes from near-wall diffusion and source-stiffness screening.",
            ["steam_air_v2_source_term_stiffness"],
            "medium",
            ["Final Fluent time step must be checked against CFL and monitor histories."],
        ),
        PatchOperation(
            "replace",
            "/transient/adaptive_time_step/enabled",
            True,
            "Adaptive time stepping is recommended while condensation source terms are stabilized.",
            ["steam_air_v2_source_term_stiffness"],
            "medium",
            [],
        ),
        PatchOperation(
            "replace",
            "/source_terms/condensation/model",
            "near_wall_limited_engineering",
            "The passport supports only the bounded near-wall engineering condensation source model.",
            ["steam_air_v2_source_term_dimension_check", "steam_air_v2_source_term_sign_check"],
            "medium",
            ["This recommendation does not generate or execute UDF source code."],
        ),
        PatchOperation(
            "replace",
            "/source_terms/condensation/ramping",
            True,
            "Source ramping is required for condensation source-term stiffness control.",
            ["steam_air_v2_source_term_stiffness"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/source_terms/condensation/clamp",
            True,
            "Source clamping is required to protect temperature and species bounds.",
            ["steam_air_v2_source_term_stiffness", "steam_air_v2_source_term_sign_check"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/source_terms/condensation/temperature_bounds_K",
            source_controls.get("temperature_bounds_K", {"min": 250.0, "max": 800.0, "review_required": True}),
            "Temperature bounds are required before source-term activation.",
            ["steam_air_v2_source_term_stiffness"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/source_terms/condensation/species_bounds",
            source_controls.get("species_bounds", {"min": 0.0, "max": 1.0, "review_required": True}),
            "Species bounds are required before source-term activation.",
            ["steam_air_v2_species_consistency", "steam_air_v2_source_term_sign_check"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/source_terms/condensation/latent_heat_j_kg",
            payload.get("inputs", {}).get("latent_heat_j_kg"),
            "Preserve latent heat used in v2 source consistency screening.",
            ["steam_air_v2_source_term_dimension_check"],
            "medium",
            [],
        ),
    ]
    operations.extend(_steam_air_v2_monitor_patches())
    operations.extend(_steam_air_v2_postprocessing_patches())
    patch = SolverPlanPatch(
        case_name=case_name,
        status="warn" if status == "warn" or warnings else "pass",
        summary="FastFluent steam-air v2 passport compiled into a non-executing Fluent solver-plan patch.",
        evidence=evidence,
        patches=operations,
        warnings=warnings,
        blocking_errors=[],
        limitations=limitations
        + [
            "This v2 patch recommends Fluent solver-plan fields only; it does not edit Fluent files or execute Fluent.",
            "Heat-transfer, mass-transfer, and source-term recommendations are advisory and require Fluent-side review.",
        ],
        metadata={"source_passport": artifact, "compiler": "steam_air_condensation_v2", "schema_version": SOLVER_PLAN_PATCH_SCHEMA_VERSION},
    )
    return patch.to_dict()


def merge_solver_plan_patches(patches: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge patch bundles while preserving evidence and conflict warnings."""

    if not patches:
        return _unsupported_passport_patch({"case_name": "empty_merge"}, source_artifact="inline")

    evidence_by_id: dict[str, dict[str, Any]] = {}
    operations: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocking_errors: list[str] = []
    limitations: list[str] = []
    status = "pass"
    case_name = patches[0].get("case_name", "merged_solver_plan_patch")

    replace_by_path: dict[str, dict[str, Any]] = {}
    append_seen: set[str] = set()

    for patch in patches:
        status = _max_status(status, str(patch.get("status", "block")))
        warnings.extend(patch.get("warnings", []))
        blocking_errors.extend(patch.get("blocking_errors", []))
        limitations.extend(patch.get("limitations", []))
        for item in patch.get("evidence", []):
            evidence_id = item.get("evidence_id")
            if evidence_id:
                evidence_by_id.setdefault(evidence_id, item)
        for operation in patch.get("patches", []):
            op = operation.get("op")
            path = operation.get("path")
            if op == "append_unique":
                key = json.dumps([path, operation.get("value")], sort_keys=True)
                if key in append_seen:
                    continue
                append_seen.add(key)
                operations.append(dict(operation))
                continue
            if op == "replace" and path:
                current = replace_by_path.get(path)
                if current is None:
                    replace_by_path[path] = dict(operation)
                    operations.append(replace_by_path[path])
                    continue
                if current.get("value") == operation.get("value"):
                    refs = sorted(set(current.get("evidence_refs", [])) | set(operation.get("evidence_refs", [])))
                    current["evidence_refs"] = refs
                else:
                    status = _max_status(status, "warn")
                    warnings.append(f"Conflicting replace patch for {path}: {current.get('value')!r} vs {operation.get('value')!r}")
                continue
            operations.append(dict(operation))

    if blocking_errors:
        status = _max_status(status, "block")

    merged = {
        "schema_version": SOLVER_PLAN_PATCH_SCHEMA_VERSION,
        "case_name": case_name,
        "created_by": "fromcad2cfd_fastfluent",
        "status": status,
        "summary": "Merged FastFluent solver-plan patch bundle.",
        "evidence": list(evidence_by_id.values()),
        "patches": operations,
        "warnings": sorted(set(warnings)),
        "blocking_errors": sorted(set(blocking_errors)),
        "limitations": sorted(set(limitations)),
        "metadata": {"merge_count": len(patches)},
    }
    validation = validate_solver_plan_patch(merged)
    if not validation.passed:
        merged["status"] = "block"
        merged["blocking_errors"] = sorted(set(merged["blocking_errors"] + validation.errors))
    return merged


def write_solver_plan_patch_bundle(
    patch: dict[str, Any],
    *,
    output: str | Path,
) -> dict[str, Any]:
    output_path = Path(output)
    report_path = output_path.with_name(output_path.stem + "_report.md")
    validation = validate_solver_plan_patch(patch)
    if validation.passed:
        json_path = write_solver_plan_patch_json(patch, output_path)
    else:
        patch = dict(patch)
        patch["status"] = "block"
        patch["blocking_errors"] = sorted(set(list(patch.get("blocking_errors", [])) + validation.errors))
        json_path = write_solver_plan_patch_json(patch, output_path)
        validation = validate_solver_plan_patch(patch)
    report = write_solver_plan_patch_report(patch, report_path)
    result_status = "success" if validation.passed and patch.get("status") != "block" else "failed"
    if result_status == "success":
        result = AgentResult.success(
            backend="fastcfd",
            operation="compile_fluent_patch",
            message="Solver plan patch bundle written.",
            outputs={"artifacts": {"solver_plan_patch": str(json_path), "solver_plan_patch_report": str(report)}, "patch": patch, "validation": validation.to_dict()},
            metadata={"output": str(output_path)},
        )
    else:
        result = AgentResult.failed(
            backend="fastcfd",
            operation="compile_fluent_patch",
            message="Solver plan patch bundle was written with blocked status.",
            errors=patch.get("blocking_errors", []),
            metadata={"output": str(output_path)},
        )
        result.outputs.update({"artifacts": {"solver_plan_patch": str(json_path), "solver_plan_patch_report": str(report)}, "patch": patch, "validation": validation.to_dict()})
    return result.to_dict()


def run_steam_air_handoff_demo(*, output_dir: str | Path) -> dict[str, Any]:
    """Run the public demo pipeline from case file to solver-plan patch."""

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    case_result = write_demo_steam_air_case(output_dir=target)
    case_file = case_result["outputs"]["case_file"]
    passport_dir = target / "passport"
    passport_result = validate_steam_air_condensation_case_file(case_file, output_dir=passport_dir)
    passport_file = passport_result["outputs"]["artifacts"]["passport"]
    patch = compile_solver_plan_patch_from_passport(passport_file)
    patch_result = write_solver_plan_patch_bundle(patch, output=target / "solver_plan_patch.json")
    status = "success" if patch_result.get("status") == "success" else "failed"
    result = AgentResult.success(
        backend="fastcfd",
        operation="steam_air_handoff_demo",
        message="Steam-air handoff demo generated.",
        outputs={
            "case_result": case_result,
            "passport_result": passport_result,
            "patch_result": patch_result,
            "artifacts": {
                "case_file": case_file,
                "passport": passport_file,
                "fluent_hints": passport_result["outputs"]["artifacts"]["fluent_hints"],
                "passport_report": passport_result["outputs"]["artifacts"]["report"],
                "solver_plan_patch": patch_result["outputs"]["artifacts"]["solver_plan_patch"],
                "solver_plan_patch_report": patch_result["outputs"]["artifacts"]["solver_plan_patch_report"],
            },
        },
        metadata={"output_dir": str(target), "final_patch_status": patch.get("status")},
    )
    if status != "success":
        result.status = "partial"
        result.message = "Steam-air handoff demo generated, but the solver-plan patch is blocked."
    return result.to_dict()


def run_existing_passport_patch_demo(*, output_dir: str | Path) -> dict[str, Any]:
    """Run the H1 public demo for existing VOF, turbulence, and rheology passports."""

    target = Path(output_dir)
    _ensure_dir(target)

    vof_result = _run_single_existing_demo(
        target / "vof",
        input_name="vof_input_or_passport.json",
        passport_payload=build_vof_physics_passport(demo_vof_case(case_name="h1_public_vof_patch_demo")),
    )
    turbulence_result = _run_single_existing_demo(
        target / "turbulence",
        input_name="turbulence_input_or_passport.json",
        passport_payload=build_turbulence_passport(demo_turbulence_case(case_name="h1_public_turbulence_patch_demo")),
    )
    rheology_result = _run_single_existing_demo(
        target / "rheology",
        input_name="rheology_input_or_passport.json",
        passport_payload=build_rheology_passport(demo_rheology_case(case_name="h1_public_rheology_patch_demo")),
    )

    patches = [vof_result["patch"], turbulence_result["patch"], rheology_result["patch"]]
    combined = merge_solver_plan_patches(patches)
    combined_dir = target / "combined"
    _ensure_dir(combined_dir)
    combined_patch = write_solver_plan_patch_bundle(combined, output=combined_dir / "combined_solver_plan_patch.json")
    conflict_summary = {
        "schema_version": "fromcad2cfd_fastfluent_h1_conflict_summary_v1",
        "status": combined.get("status"),
        "warning_count": len(combined.get("warnings", [])),
        "blocking_error_count": len(combined.get("blocking_errors", [])),
        "conflict_warnings": [item for item in combined.get("warnings", []) if "Conflicting replace patch" in item],
        "evidence_count": len(combined.get("evidence", [])),
        "patch_count": len(combined.get("patches", [])),
    }
    _write_json(combined_dir / "conflict_summary.json", conflict_summary)

    status = "success" if all(item["result"].get("status") == "success" for item in [vof_result, turbulence_result, rheology_result]) else "partial"
    if combined.get("status") == "block":
        status = "failed"
    result = AgentResult.success(
        backend="fastcfd",
        operation="existing_passport_patch_demo",
        message="Existing VOF, turbulence, and rheology passports compiled into solver-plan patches.",
        outputs={
            "artifacts": {
                "vof_solver_plan_patch": vof_result["result"]["outputs"]["artifacts"]["solver_plan_patch"],
                "turbulence_solver_plan_patch": turbulence_result["result"]["outputs"]["artifacts"]["solver_plan_patch"],
                "rheology_solver_plan_patch": rheology_result["result"]["outputs"]["artifacts"]["solver_plan_patch"],
                "combined_solver_plan_patch": combined_patch["outputs"]["artifacts"]["solver_plan_patch"],
                "combined_solver_plan_patch_report": combined_patch["outputs"]["artifacts"]["solver_plan_patch_report"],
                "conflict_summary": str(combined_dir / "conflict_summary.json"),
            },
            "vof": vof_result["result"],
            "turbulence": turbulence_result["result"],
            "rheology": rheology_result["result"],
            "combined": combined_patch,
            "conflict_summary": conflict_summary,
        },
        metadata={"output_dir": str(target), "solver_execution": "not_attempted_patch_demo_only"},
    )
    result.status = status
    return result.to_dict()


def _run_single_existing_demo(
    output_dir: Path,
    *,
    input_name: str,
    passport_payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_dir(output_dir)
    _write_json(output_dir / input_name, passport_payload)
    patch = compile_solver_plan_patch_from_passport(passport_payload)
    patch_result = write_solver_plan_patch_bundle(patch, output=output_dir / "solver_plan_patch.json")
    return {"passport": passport_payload, "patch": patch, "result": patch_result}


def _load_payload(item: str | Path | dict[str, Any]) -> tuple[dict[str, Any], str]:
    if isinstance(item, dict):
        return item, "inline_artifact"
    path = Path(item)
    with open(_windows_long_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle), str(path)


def _extract_supported_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract a known passport/hints object from direct or nested result artifacts."""

    schema = payload.get("schema_version")
    if schema in {
        STEAM_AIR_PASSPORT_SCHEMA_VERSION,
        STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION,
        STEAM_AIR_V2_FLUENT_HINTS_SCHEMA_VERSION,
        VOF_PASSPORT_SCHEMA_VERSION,
        VOF_HINTS_SCHEMA_VERSION,
        TURBULENCE_PASSPORT_SCHEMA_VERSION,
        TURBULENCE_HINTS_SCHEMA_VERSION,
        RHEOLOGY_PASSPORT_SCHEMA_VERSION,
        RHEOLOGY_HINTS_SCHEMA_VERSION,
        SOLID_LIQUID_PASSPORT_SCHEMA_VERSION,
        SOLID_LIQUID_HINTS_SCHEMA_VERSION,
        WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION,
        WAX_RHEOLOGY_HINTS_SCHEMA_VERSION,
    }:
        return payload
    outputs = payload.get("outputs")
    if isinstance(outputs, dict):
        for key in ("passport", "fluent_hints", "compiled_hints", "qoi"):
            item = outputs.get(key)
            if isinstance(item, dict):
                extracted = _extract_supported_payload(item)
                if extracted is not item or extracted.get("schema_version") in {
                    STEAM_AIR_PASSPORT_SCHEMA_VERSION,
                    STEAM_AIR_V2_PASSPORT_SCHEMA_VERSION,
                    STEAM_AIR_V2_FLUENT_HINTS_SCHEMA_VERSION,
                    VOF_PASSPORT_SCHEMA_VERSION,
                    VOF_HINTS_SCHEMA_VERSION,
                    TURBULENCE_PASSPORT_SCHEMA_VERSION,
                    TURBULENCE_HINTS_SCHEMA_VERSION,
                    RHEOLOGY_PASSPORT_SCHEMA_VERSION,
                    RHEOLOGY_HINTS_SCHEMA_VERSION,
                    SOLID_LIQUID_PASSPORT_SCHEMA_VERSION,
                    SOLID_LIQUID_HINTS_SCHEMA_VERSION,
                    WAX_RHEOLOGY_PASSPORT_SCHEMA_VERSION,
                    WAX_RHEOLOGY_HINTS_SCHEMA_VERSION,
                }:
                    return extracted
    for key in ("passport", "fluent_hints", "compiled_hints", "qoi"):
        item = payload.get(key)
        if isinstance(item, dict):
            extracted = _extract_supported_payload(item)
            if extracted is not item or extracted.get("schema_version"):
                return extracted
    return payload


def _passport_status(payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "").lower()
    if status in {"passed", "pass", "ready"}:
        return "pass"
    if status in {"warning", "warn", "ready_with_warnings"}:
        return "warn"
    if status in {"failed", "fail", "blocked", "block"}:
        return "block"
    return "block"


def _vof_evidence(payload: dict[str, Any], source_artifact: str, status: str) -> list[PatchEvidence]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    return [
        PatchEvidence(
            "vof_regime_numbers",
            "fromcad2cfd_fastcfd.vof",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "dimensionless_groups",
            {
                "reynolds_number": checks.get("reynolds_number"),
                "weber_number": checks.get("weber_number"),
                "bond_number": checks.get("bond_number"),
                "capillary_number": checks.get("capillary_number"),
                "froude_number": checks.get("froude_number"),
            },
            "mixed",
            "VOF setup uses dimensionless screening values from the existing passport.",
            "VOF interface tracking and transient setup are review-required.",
            "medium",
            list(payload.get("limitations", [])),
        ),
        PatchEvidence(
            "vof_time_step_restriction",
            "fromcad2cfd_fastcfd.vof",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "time_step_restriction",
            {
                "courant_number": checks.get("courant_number"),
                "recommended_time_step_s_by_courant": checks.get("recommended_time_step_s_by_courant"),
                "capillary_time_step_s_advisory": checks.get("capillary_time_step_s_advisory"),
            },
            "s",
            "Courant and capillary advisory limits bound the preview time-step recommendation.",
            "Use conservative transient stepping before high-fidelity Fluent validation.",
            "medium",
            [],
        ),
        PatchEvidence(
            "vof_density_viscosity_ratio",
            "fromcad2cfd_fastcfd.vof",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "density_viscosity_ratio",
            {"density_ratio": checks.get("density_ratio"), "viscosity_ratio": checks.get("viscosity_ratio")},
            "ratio",
            "Density and viscosity ratios indicate VOF stiffness and monitoring needs.",
            "High ratios require reviewer-owned stability checks.",
            "medium",
            [],
        ),
        PatchEvidence(
            "vof_surface_tension_importance",
            "fromcad2cfd_fastcfd.vof",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "surface_tension",
            checks.get("surface_tension_n_m"),
            "N/m",
            "Surface tension value is available from the existing VOF passport.",
            "Preserve surface tension as a reviewed setup value; do not execute Fluent.",
            "medium",
            [],
        ),
        PatchEvidence(
            "vof_monitor_requirements",
            "fromcad2cfd_fastcfd.vof",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "vof_monitor_requirements",
            ["volume_fraction_bounds", "courant_number", "phase_mass_conservation"],
            "review",
            "VOF monitor requirements come from the existing VOF setup-hint route.",
            "Monitors are requested as reviewable solver-plan fields only.",
            "high",
            [],
        ),
    ]


def _turbulence_evidence(payload: dict[str, Any], source_artifact: str, status: str) -> list[PatchEvidence]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    return [
        PatchEvidence(
            "turbulence_reynolds_regime",
            "fromcad2cfd_fastcfd.turbulence",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "reynolds_regime",
            {"reynolds_number": checks.get("reynolds_number"), "flow_regime": payload.get("flow_regime")},
            "review",
            "Turbulence setup recommendation is tied to Reynolds-regime screening.",
            "Regime classification is an engineering pre-check, not final validation.",
            "medium",
            list(payload.get("limitations", [])),
        ),
        PatchEvidence(
            "turbulence_y_plus_estimate",
            "fromcad2cfd_fastcfd.turbulence",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "estimated_y_plus",
            {
                "estimated_y_plus": checks.get("estimated_y_plus"),
                "target_y_plus_min": checks.get("target_y_plus_min"),
                "target_y_plus_max": checks.get("target_y_plus_max"),
            },
            "1",
            "Near-wall treatment depends on y-plus screening from the existing passport.",
            "The y-plus estimate must be confirmed with the final mesh.",
            "medium",
            [],
        ),
        PatchEvidence(
            "turbulence_model_recommendation",
            "fromcad2cfd_fastcfd.turbulence",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "recommended_model_family",
            {"model_intent": payload.get("model_intent"), "recommended_model_family": payload.get("recommended_model_family")},
            "review",
            "Model recommendation is preserved from the turbulence passport.",
            "Transitional or uncertain regimes are not overclaimed.",
            "medium",
            [],
        ),
        PatchEvidence(
            "turbulence_wall_monitor_requirements",
            "fromcad2cfd_fastcfd.turbulence",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "wall_monitor_requirements",
            ["wall_y_plus", "wall_shear_stress", "skin_friction_coefficient_if_available"],
            "review",
            "Wall monitors are needed for turbulence setup review.",
            "Monitor availability depends on the final Fluent setup.",
            "high",
            [],
        ),
    ]


def _rheology_evidence(payload: dict[str, Any], source_artifact: str, status: str) -> list[PatchEvidence]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    return [
        PatchEvidence(
            "rheology_viscosity_model",
            "fromcad2cfd_fastcfd.rheology",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "viscosity_model",
            {"model": payload.get("model"), "parameters": payload.get("parameters")},
            "review",
            "Material-property model evidence is preserved from the rheology passport.",
            "No executable UDF or material code is generated.",
            "medium",
            list(payload.get("limitations", [])),
        ),
        PatchEvidence(
            "rheology_viscosity_range",
            "fromcad2cfd_fastcfd.rheology",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "viscosity_range",
            {
                "min_apparent_viscosity_pa_s": checks.get("min_apparent_viscosity_pa_s"),
                "max_apparent_viscosity_pa_s": checks.get("max_apparent_viscosity_pa_s"),
                "viscosity_ratio": checks.get("viscosity_ratio"),
            },
            "Pa*s",
            "Viscosity range evidence supports bounded material-property review.",
            "Large viscosity contrast may require conservative Fluent setup.",
            "medium",
            [],
        ),
        PatchEvidence(
            "rheology_non_newtonian_status",
            "fromcad2cfd_fastcfd.rheology",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "non_newtonian_status",
            {"model": payload.get("model"), "trend": checks.get("trend"), "expected_trend": checks.get("expected_trend")},
            "review",
            "Non-Newtonian behavior is inferred from the existing rheology passport.",
            "Reviewer must choose the final Fluent material-property implementation.",
            "medium",
            [],
        ),
        PatchEvidence(
            "rheology_monitor_requirements",
            "fromcad2cfd_fastcfd.rheology",
            source_artifact,
            str(payload.get("schema_version")),
            status,
            "rheology_monitor_requirements",
            ["viscosity_min_max", "temperature_min_max_if_available", "viscosity_field_summary"],
            "review",
            "Rheology setup needs material-property monitor and output review.",
            "Monitor availability depends on the final Fluent setup.",
            "high",
            [],
        ),
    ]


def _vof_monitor_and_output_patches(evidence_ids: set[str]) -> list[PatchOperation]:
    refs = ["vof_monitor_requirements"] if "vof_monitor_requirements" in evidence_ids else []
    return [
        PatchOperation("append_unique", "/monitors/global", {"name": "volume_fraction_bounds", "quantity": "volume_fraction", "reduction": "min_max", "required": True}, "VOF setup requires bounded volume-fraction monitoring.", refs, "high", []),
        PatchOperation("append_unique", "/monitors/global", {"name": "courant_number", "quantity": "courant_number", "reduction": "max", "required": True}, "VOF setup requires Courant-number monitoring.", ["vof_time_step_restriction"], "high", []),
        PatchOperation("append_unique", "/monitors/global", {"name": "phase_mass_conservation", "quantity": "phase_mass", "reduction": "balance", "required": True}, "VOF setup requires phase mass-conservation monitoring.", refs, "high", []),
        PatchOperation("append_unique", "/postprocessing/required_outputs", {"name": "phase_volume_history", "required": True}, "VOF setup requires phase-volume history output.", refs, "high", []),
        PatchOperation("append_unique", "/acceptance_criteria", {"name": "bounded_volume_fraction", "rule": "volume fraction remains inside [0, 1]", "required": True}, "VOF runs must reject unbounded phase fraction.", refs, "high", []),
    ]


def _turbulence_model_recommendation(payload: dict[str, Any]) -> str:
    if payload.get("flow_regime") == "transitional" or payload.get("recommended_model_family") == "transitional_review":
        return "review-required"
    intent = str(payload.get("model_intent") or "")
    if intent == "laminar":
        return "laminar"
    if intent == "rans_sst":
        return "k-omega-sst"
    if intent in {"rans_realizable_k_epsilon", "rans_k_epsilon"}:
        return "realizable-k-epsilon"
    family = str(payload.get("recommended_model_family") or "")
    if "sst" in family:
        return "k-omega-sst"
    if "epsilon" in family:
        return "realizable-k-epsilon"
    return "review-required"


def _near_wall_treatment(payload: dict[str, Any]) -> str:
    if payload.get("flow_regime") == "transitional":
        return "review-required"
    if str(payload.get("model_intent")) == "rans_sst":
        return "low-re-sst-review"
    return "review-required"


def _target_y_plus(payload: dict[str, Any]) -> dict[str, Any] | None:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    min_value = checks.get("target_y_plus_min")
    max_value = checks.get("target_y_plus_max")
    if min_value is None and max_value is None:
        return None
    return {"min": min_value, "max": max_value, "review_required": True}


def _blocked_patch_from_evidence(
    payload: dict[str, Any],
    evidence: list[PatchEvidence],
    *,
    source_artifact: str,
    compiler: str,
    warnings: list[str],
    blocking_errors: list[str],
    limitations: list[str],
) -> dict[str, Any]:
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or f"{compiler}_blocked_patch_case"),
        status="block",
        summary=f"FastFluent {compiler} evidence blocked Fluent handoff.",
        evidence=evidence,
        patches=[
            PatchOperation(
                "block",
                "/runtime/fluent_execution_allowed",
                False,
                f"{compiler} passport reported blocking errors.",
                [item.evidence_id for item in evidence],
                "high",
                ["Resolve evidence blocking errors before Fluent setup planning."],
            )
        ],
        warnings=warnings,
        blocking_errors=blocking_errors,
        limitations=limitations,
        metadata={"source_artifact": source_artifact, "compiler": compiler},
    )
    return patch.to_dict()


def _compile_hint_only_patch(payload: dict[str, Any], *, source_artifact: str) -> dict[str, Any]:
    schema = str(payload.get("schema_version"))
    status = _passport_status(payload)
    hints = payload.get("hints", []) if isinstance(payload.get("hints"), list) else []
    evidence: list[PatchEvidence] = []
    operations: list[PatchOperation] = []
    for index, hint in enumerate(hints):
        evidence_id = f"hint_only_{index}"
        evidence.append(
            PatchEvidence(
                evidence_id,
                "fromcad2cfd_fastcfd.fluent_hints",
                source_artifact,
                schema,
                status,
                str(hint.get("category") or "hint"),
                hint.get("evidence", []),
                "review",
                str(hint.get("recommendation") or "Existing Fluent setup hint."),
                "Hint-only artifacts do not contain enough structured evidence for confident field patches.",
                "low",
                list(payload.get("limitations", [])),
            )
        )
        operations.append(
            PatchOperation(
                "warn",
                "/physics/solver/type",
                "review-required",
                f"Hint-only artifact requires reviewer interpretation: {hint.get('category')}",
                [evidence_id],
                "low",
                ["Compile the corresponding passport when machine-readable values are required."],
            )
        )
    if not operations:
        return _unsupported_passport_patch(payload, source_artifact=source_artifact)
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or "hint_only_patch_case"),
        status="warn",
        summary="Hint-only FastFluent artifact converted to reviewer warnings without confident setup patches.",
        evidence=evidence,
        patches=operations,
        warnings=list(payload.get("warnings", [])) + ["Hint-only patch contains warning operations only."],
        blocking_errors=[],
        limitations=list(payload.get("limitations", [])) + ["No physics field is confidently patched from hint-only input."],
        metadata={"source_artifact": source_artifact, "compiler": "hint_only"},
    )
    return patch.to_dict()


def _min_positive(*values: Any) -> float | None:
    positives = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            positives.append(number)
    return min(positives) if positives else None


def _evidence_from_check(check: dict[str, Any], *, source_artifact: str, source_status: str) -> PatchEvidence:
    return PatchEvidence(
        evidence_id=str(check.get("evidence_id")),
        source_module=str(check.get("source_module") or "unknown"),
        source_artifact=source_artifact,
        source_schema_version=str(check.get("source_schema_version") or STEAM_AIR_PASSPORT_SCHEMA_VERSION),
        source_status=source_status,
        quantity_name=str(check.get("quantity_name") or "unknown"),
        quantity_value=check.get("quantity_value"),
        quantity_units=str(check.get("quantity_units") or ""),
        threshold_or_rule=str(check.get("threshold_or_rule") or ""),
        interpretation=str(check.get("interpretation") or ""),
        confidence=str(check.get("confidence") or "medium"),
        limitations=list(check.get("limitations", [])),
    )


def _monitor_patches() -> list[PatchOperation]:
    global_monitors = [
        {"name": "residuals", "quantity": "solver_residuals", "required": True},
        {"name": "max_temperature", "quantity": "temperature", "reduction": "max", "required": True},
        {"name": "min_temperature", "quantity": "temperature", "reduction": "min", "required": True},
        {"name": "max_velocity", "quantity": "velocity_magnitude", "reduction": "max", "required": True},
        {"name": "pressure_range", "quantity": "pressure", "reduction": "min_max", "required": True},
        {"name": "mass_imbalance", "quantity": "mass_flux", "reduction": "imbalance", "required": True},
        {"name": "energy_imbalance", "quantity": "energy_flux", "reduction": "imbalance", "required": True},
        {"name": "source_term_integral_if_available", "quantity": "condensation_source", "reduction": "integral", "required": False},
    ]
    wall_monitors = [
        {"name": "wall_heat_transfer_rate", "quantity": "wall_heat_flux", "required": True},
        {"name": "wall_temperature", "quantity": "wall_temperature", "required": True},
        {"name": "wall_adjacent_steam_mass_fraction", "quantity": "h2o_mass_fraction_near_wall", "required": True},
        {"name": "steam_mass_fraction_min_max", "quantity": "h2o_mass_fraction", "reduction": "min_max", "required": True},
        {"name": "air_mass_fraction_min_max", "quantity": "air_mass_fraction", "reduction": "min_max", "required": True},
    ]
    patches: list[PatchOperation] = []
    for monitor in global_monitors:
        patches.append(
            PatchOperation(
                op="append_unique",
                path="/monitors/global",
                value=monitor,
                reason=f"Required monitor for steam-air condensation handoff: {monitor['name']}.",
                evidence_refs=["steam_air_source_stiffness_risk", "steam_air_recommended_time_step"],
                confidence="high",
                limitations=[],
            )
        )
    for monitor in wall_monitors:
        patches.append(
            PatchOperation(
                op="append_unique",
                path="/monitors/wall",
                value=monitor,
                reason=f"Required wall monitor for steam-air condensation handoff: {monitor['name']}.",
                evidence_refs=["steam_air_wall_below_saturation", "steam_air_noncondensable_risk"],
                confidence="high",
                limitations=[],
            )
        )
    return patches


def _postprocessing_and_acceptance_patches() -> list[PatchOperation]:
    return [
        PatchOperation(
            op="append_unique",
            path="/postprocessing/required_outputs",
            value={"name": "temperature_species_wall_monitor_bundle", "required": True},
            reason="Steam-air condensation review requires coupled thermal, species, and wall monitor outputs.",
            evidence_refs=["steam_air_wall_below_saturation", "steam_air_noncondensable_risk"],
            confidence="high",
            limitations=[],
        ),
        PatchOperation(
            op="append_unique",
            path="/acceptance_criteria",
            value={"name": "bounded_temperature_and_species", "rule": "temperature finite, species fractions bounded in [0, 1]"},
            reason="Early condensation runs must fail closed on unphysical temperature or species values.",
            evidence_refs=["steam_air_source_stiffness_risk", "steam_air_species_consistency"],
            confidence="high",
            limitations=[],
        ),
        PatchOperation(
            op="append_unique",
            path="/acceptance_criteria",
            value={"name": "mass_energy_imbalance_review", "rule": "mass and energy imbalance monitors reviewed before continuing"},
            reason="Condensation source terms couple mass and energy balances.",
            evidence_refs=["steam_air_source_stiffness_risk"],
            confidence="high",
            limitations=[],
        ),
    ]


def _steam_air_v2_monitor_patches() -> list[PatchOperation]:
    return [
        PatchOperation(
            "append_unique",
            "/monitors/wall",
            {"name": "wall_heat_transfer_rate", "quantity": "wall_heat_transfer_rate", "reduction": "integral", "required": True},
            "Steam-air v2 requires wall heat-transfer-rate monitoring.",
            ["steam_air_v2_heat_transfer_estimate"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/wall",
            {"name": "wall_temperature", "quantity": "wall_temperature", "reduction": "min_max", "required": True},
            "Steam-air v2 requires wall temperature monitoring.",
            ["steam_air_v2_heat_transfer_estimate"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "steam_mass_fraction", "quantity": "h2o_mass_fraction", "reduction": "min_max", "required": True},
            "Steam-air v2 requires steam mass-fraction bounds.",
            ["steam_air_v2_species_consistency", "steam_air_v2_mass_transfer_resistance"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "air_mass_fraction", "quantity": "air_mass_fraction", "reduction": "min_max", "required": True},
            "Steam-air v2 requires air mass-fraction bounds.",
            ["steam_air_v2_species_consistency", "steam_air_v2_mass_transfer_resistance"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "max_temperature", "quantity": "temperature", "reduction": "max", "required": True},
            "Steam-air v2 source-term activation requires maximum-temperature monitoring.",
            ["steam_air_v2_source_term_stiffness"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "energy_balance", "quantity": "energy_balance", "reduction": "imbalance", "required": True},
            "Latent heat source terms require energy balance monitoring.",
            ["steam_air_v2_source_term_dimension_check"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "source_term_integral", "quantity": "condensation_source", "reduction": "integral", "required": True},
            "Source integral monitoring is required for condensation source review.",
            ["steam_air_v2_source_term_dimension_check", "steam_air_v2_source_term_sign_check"],
            "high",
            [],
        ),
    ]


def _steam_air_v2_postprocessing_patches() -> list[PatchOperation]:
    return [
        PatchOperation(
            "append_unique",
            "/postprocessing/required_outputs",
            {"name": "wall_heat_flux_summary", "required": True},
            "HTC and heat-flux estimates require wall heat-flux summary output.",
            ["steam_air_v2_heat_transfer_estimate"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/postprocessing/required_outputs",
            {"name": "species_boundary_layer_summary", "required": True},
            "Mass-transfer resistance evidence requires species boundary-layer review.",
            ["steam_air_v2_mass_transfer_resistance"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/postprocessing/required_outputs",
            {"name": "condensation_source_integral_history", "required": True},
            "Condensation source integral history is required for source-term review.",
            ["steam_air_v2_source_term_dimension_check", "steam_air_v2_source_term_sign_check"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/acceptance_criteria",
            {"name": "bounded_temperature_and_species_v2", "rule": "temperature finite and species fractions bounded in [0, 1]", "required": True},
            "Steam-air v2 must fail closed on unphysical temperature or species values.",
            ["steam_air_v2_source_term_stiffness", "steam_air_v2_species_consistency"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/acceptance_criteria",
            {"name": "source_integral_and_energy_balance_review", "rule": "source integral and energy balance monitors reviewed before continuing", "required": True},
            "Condensation source terms couple mass and energy balances.",
            ["steam_air_v2_source_term_dimension_check", "steam_air_v2_source_term_stiffness"],
            "high",
            [],
        ),
    ]


def _solid_liquid_monitor_patches(evidence_ids: set[str]) -> list[PatchOperation]:
    refs = ["solid_liquid_monitor_requirements"] if "solid_liquid_monitor_requirements" in evidence_ids else []
    return [
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "solid_volume_fraction_bounds", "quantity": "solid_volume_fraction", "reduction": "min_max", "required": True},
            "Solid-liquid setup requires bounded solid volume-fraction monitoring.",
            ["solid_liquid_volume_fraction_regime"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "particle_mass_balance", "quantity": "particle_mass", "reduction": "balance", "required": True},
            "Particle mass balance is required for solid-liquid setup review.",
            refs or ["solid_liquid_mass_loading"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "continuous_phase_mass_balance", "quantity": "continuous_phase_mass", "reduction": "balance", "required": True},
            "Continuous phase mass balance is required when particle phase is enabled.",
            refs or ["solid_liquid_mass_loading"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "particle_velocity_range", "quantity": "particle_velocity", "reduction": "min_max", "required": True},
            "Particle velocity range helps detect particle response and trajectory risk.",
            ["solid_liquid_stokes_number"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "settling_indicator", "quantity": "particle_vertical_flux", "reduction": "surface_or_volume_integral", "required": True},
            "Settling evidence requires a downstream settling indicator.",
            ["solid_liquid_settling_velocity"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/global",
            {"name": "pressure_drop", "quantity": "pressure_drop", "reduction": "inlet_outlet", "required": True},
            "Pressure drop is a basic suspension-flow response monitor.",
            ["solid_liquid_model_recommendation"],
            "medium",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/wall",
            {"name": "particle_wall_impact_if_available", "quantity": "particle_wall_impact", "reduction": "count_or_flux", "required": False},
            "Wall impact is requested when Fluent exposes a compatible particle-wall report.",
            ["solid_liquid_stokes_number", "solid_liquid_settling_velocity"],
            "medium",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/monitors/wall",
            {"name": "erosion_indicator_if_relevant", "quantity": "erosion_rate", "reduction": "max", "required": False},
            "Erosion is optional and should only be enabled when the case marks impact relevance.",
            ["solid_liquid_monitor_requirements"],
            "low",
            [],
        ),
    ]


def _solid_liquid_postprocessing_patches() -> list[PatchOperation]:
    return [
        PatchOperation(
            "append_unique",
            "/postprocessing/required_outputs",
            {"name": "particle_phase_summary", "required": True},
            "Solid-liquid handoff requires a particle-phase summary output.",
            ["solid_liquid_model_recommendation", "solid_liquid_monitor_requirements"],
            "high",
            [],
        ),
        PatchOperation(
            "append_unique",
            "/postprocessing/required_outputs",
            {"name": "settling_vs_residence_summary", "required": True},
            "Settling and residence-time evidence should be checked after first-pass runs.",
            ["solid_liquid_settling_velocity"],
            "medium",
            [],
        ),
        PatchOperation(
            "replace",
            "/acceptance_criteria/bounded_solid_volume_fraction",
            True,
            "Solid volume fraction must remain physically bounded.",
            ["solid_liquid_volume_fraction_regime"],
            "high",
            [],
        ),
        PatchOperation(
            "replace",
            "/acceptance_criteria/particle_mass_balance_required",
            True,
            "Particle mass balance must be reviewed before continuing.",
            ["solid_liquid_mass_loading", "solid_liquid_monitor_requirements"],
            "high",
            [],
        ),
    ]


def _unsupported_passport_patch(payload: dict[str, Any], *, source_artifact: str) -> dict[str, Any]:
    patch = SolverPlanPatch(
        case_name=str(payload.get("case_name") or "unsupported_fastfluent_passport"),
        status="block",
        summary="Unsupported FastFluent evidence schema for solver-plan patch compilation.",
        evidence=[],
        patches=[
            PatchOperation(
                op="block",
                path="/runtime/fluent_execution_allowed",
                value=False,
                reason="Unsupported FastFluent evidence schema.",
                evidence_refs=[],
                confidence="high",
                limitations=["Supported schemas are steam-air v1/v2, VOF, turbulence, rheology, solid-liquid suspension, wax rheology / phase-change, and related hint-only artifacts."],
            )
        ],
        warnings=[],
        blocking_errors=[f"Unsupported evidence schema: {payload.get('schema_version')!r}"],
        limitations=["The compiler is intentionally fail-closed for unsupported evidence schemas."],
        metadata={"source_artifact": source_artifact},
    )
    return patch.to_dict()


def _max_status(left: str, right: str) -> str:
    left = left if left in SEVERITY else "block"
    right = right if right in SEVERITY else "block"
    return left if SEVERITY[left] >= SEVERITY[right] else right


def _windows_long_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    _ensure_dir(path.parent)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    return path


def _ensure_dir(path: Path) -> None:
    os.makedirs(_windows_long_path(path), exist_ok=True)
