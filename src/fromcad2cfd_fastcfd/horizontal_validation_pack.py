"""Public H1-H3 FastFluent horizontal validation pack.

The validation pack generates synthetic, public-safe cases across existing
VOF, turbulence, rheology, steam-air v2, and solid-liquid passports. It writes
agent-reviewable Fluent solver-plan patch artifacts, but it never launches
Fluent and never edits Fluent case/data files.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable

from fromcad2cfd_cad import AgentResult

from .fluent_patch_compiler import (
    compile_solver_plan_patch_from_passport,
    merge_solver_plan_patches,
    write_solver_plan_patch_bundle,
)
from .rheology import (
    RheologyCase,
    build_rheology_fluent_setup_hints,
    build_rheology_passport,
)
from .solid_liquid_suspension import (
    build_solid_liquid_fluent_hints,
    build_solid_liquid_suspension_passport,
    demo_solid_liquid_suspension_case,
    solid_liquid_suspension_report,
)
from .solver_plan_patch import find_dangerous_keys, validate_solver_plan_patch
from .steam_air_condensation_v2 import (
    build_steam_air_condensation_passport_v2,
    build_steam_air_fluent_hints_v2,
    demo_steam_air_condensation_case_v2,
    steam_air_condensation_report_v2,
)
from .turbulence import (
    TurbulenceCase,
    build_turbulence_fluent_setup_hints,
    build_turbulence_passport,
    demo_turbulence_case,
)
from .vof import (
    VOFCase,
    VOFPhase,
    build_vof_fluent_setup_hints,
    build_vof_physics_passport,
    demo_vof_case,
)


VALIDATION_PACK_SCHEMA_VERSION = "fromcad2cfd_fastfluent_horizontal_validation_pack_v1"
EVIDENCE_REQUIRED_PREFIXES = (
    "/physics",
    "/materials",
    "/numerics",
    "/transient",
    "/monitors",
    "/source_terms",
    "/acceptance_criteria",
)
LIMITATIONS = [
    "The validation pack uses synthetic public cases only.",
    "The validation pack checks FastFluent passports, Fluent setup hints, and non-executing solver-plan patches.",
    "No Fluent, PyFluent, raw Fluent TUI, UDF, case/data editing, or production CFD validation is performed.",
    "The cases are intended for agent workflow validation and engineering setup review, not final CFD accuracy claims.",
]


@dataclass(frozen=True)
class ValidationCaseSpec:
    case_id: str
    module: str
    case_name: str
    expected_status: str
    builder: Callable[[], dict[str, Any] | VOFCase | TurbulenceCase | RheologyCase]


def create_validation_case_registry() -> list[ValidationCaseSpec]:
    """Return the bounded H1-H3 synthetic validation cases."""

    return [
        ValidationCaseSpec("vof_case_01_gravity_dominant", "vof", "VOF gravity-dominant water-air interface", "pass", _vof_gravity_case),
        ValidationCaseSpec("vof_case_02_capillary_dominant", "vof", "VOF capillary-dominant small interface", "warn", _vof_capillary_case),
        ValidationCaseSpec("vof_case_03_high_density_ratio", "vof", "VOF high density ratio interface", "warn", _vof_high_density_ratio_case),
        ValidationCaseSpec("vof_case_04_high_cfl_block", "vof", "VOF high Courant block case", "block", _vof_high_cfl_case),
        ValidationCaseSpec("turbulence_case_01_laminar_channel", "turbulence", "Laminar channel turbulence passport", "pass", _turbulence_laminar_case),
        ValidationCaseSpec("turbulence_case_02_transitional_channel", "turbulence", "Transitional channel turbulence review", "warn", _turbulence_transition_case),
        ValidationCaseSpec("turbulence_case_03_high_re_sst", "turbulence", "High Reynolds SST setup passport", "pass", _turbulence_high_re_case),
        ValidationCaseSpec("turbulence_case_04_yplus_review", "turbulence", "Near-wall y-plus review case", "warn", _turbulence_yplus_case),
        ValidationCaseSpec("rheology_case_01_newtonian", "rheology", "Newtonian material passport", "pass", _rheology_newtonian_case),
        ValidationCaseSpec("rheology_case_02_power_law_thinning", "rheology", "Power-law shear-thinning passport", "pass", _rheology_power_law_case),
        ValidationCaseSpec("rheology_case_03_carreau_yasuda", "rheology", "Carreau-Yasuda viscosity passport", "pass", _rheology_carreau_case),
        ValidationCaseSpec("rheology_case_04_large_viscosity_ratio", "rheology", "Large viscosity-ratio rheology review", "warn", _rheology_high_ratio_case),
        ValidationCaseSpec("steam_air_case_01_baseline", "steam_air_v2", "Steam-air wall-condensation baseline", "warn", _steam_air_baseline_case),
        ValidationCaseSpec("steam_air_case_02_warm_wall", "steam_air_v2", "Steam-air warm-wall condensation review", "warn", _steam_air_warm_wall_case),
        ValidationCaseSpec("steam_air_case_03_noncondensable_risk", "steam_air_v2", "Steam-air high non-condensable risk", "warn", _steam_air_noncondensable_case),
        ValidationCaseSpec("steam_air_case_04_source_stiffness", "steam_air_v2", "Steam-air source stiffness review", "warn", _steam_air_source_stiffness_case),
        ValidationCaseSpec("steam_air_case_05_turbulent_thermal", "steam_air_v2", "Steam-air turbulent thermal transport case", "warn", _steam_air_turbulent_case),
        ValidationCaseSpec("solid_liquid_case_01_dilute_dpm", "solid_liquid", "Dilute DPM solid-liquid suspension", "warn", _solid_liquid_dilute_case),
        ValidationCaseSpec("solid_liquid_case_02_two_way_loading", "solid_liquid", "Two-way loading solid-liquid suspension", "warn", _solid_liquid_two_way_case),
        ValidationCaseSpec("solid_liquid_case_03_mixture_model", "solid_liquid", "Moderate volume-fraction mixture model", "warn", _solid_liquid_mixture_case),
        ValidationCaseSpec("solid_liquid_case_04_dense_eulerian", "solid_liquid", "Dense Eulerian multiphase review", "warn", _solid_liquid_dense_case),
        ValidationCaseSpec("solid_liquid_case_05_time_step_risk", "solid_liquid", "Particle time-step risk review", "warn", _solid_liquid_time_step_case),
        ValidationCaseSpec("solid_liquid_case_06_cell_particle_block", "solid_liquid", "Cell-particle inconsistency block", "block", _solid_liquid_cell_particle_block_case),
    ]


def run_horizontal_validation_pack(output_dir: str | Path) -> dict[str, Any]:
    """Generate the H1-H3 validation pack tree and return a result payload."""

    root = Path(output_dir)
    _mkdir(root)

    case_results: list[dict[str, Any]] = []
    patches: dict[str, dict[str, Any]] = {}
    for spec in create_validation_case_registry():
        case_dir = root / f"{spec.module}_cases" / spec.case_id
        result = _run_single_case(spec, case_dir, root)
        case_results.append(result)
        patches[spec.case_id] = result["patch"]

    combined_results = _run_combined_cases(root, patches)
    case_results.extend(combined_results)

    manifest = _build_manifest(root, case_results)
    summary = _validation_summary_markdown(manifest)
    manifest_path = _write_json(root / "validation_manifest.json", manifest)
    summary_path = _write_text(root / "validation_summary.md", summary)

    result_status = "success" if manifest["test_status_summary"]["blocking_case_count"] == 0 else "partial"
    result = AgentResult.success(
        backend="fastcfd",
        operation="horizontal_validation_pack_demo",
        message="FastFluent H1-H3 horizontal validation pack generated.",
        outputs={
            "artifacts": {
                "validation_manifest": str(manifest_path),
                "validation_summary": str(summary_path),
            },
            "manifest": manifest,
            "solver_execution": "not_attempted_validation_pack_only",
        },
        metadata={"output_dir": str(root), "fluent_launched": False},
    )
    if result_status == "partial":
        result.status = "partial"
        result.message = "FastFluent H1-H3 validation pack generated with blocked review cases."
    return result.to_dict()


def _run_single_case(spec: ValidationCaseSpec, case_dir: Path, root: Path) -> dict[str, Any]:
    _mkdir(case_dir)
    case_payload = spec.builder()
    case_dict = _case_to_dict(case_payload)
    input_path = _write_json(case_dir / "input_case.json", case_dict)

    passport, hints, report_text, key_quantities = _build_case_artifacts(spec.module, case_payload, str(input_path))
    passport_path = _write_json(case_dir / "passport.json", passport)
    hints_path = _write_json(case_dir / "fluent_hints.json", hints)
    report_path = _write_text(case_dir / "case_summary.md", _case_summary_markdown(spec, passport, hints, report_text))

    patch = compile_solver_plan_patch_from_passport(passport_path)
    patch_result = write_solver_plan_patch_bundle(patch, output=case_dir / "solver_plan_patch.json")
    written_patch = patch_result["outputs"]["patch"]
    patch_validation = validate_solver_plan_patch(written_patch)
    contract_errors = _patch_contract_errors(written_patch)
    dangerous_findings = _artifact_dangerous_findings(case_dict, passport, hints, written_patch)
    patch_valid = patch_validation.passed and not contract_errors and not dangerous_findings

    actual_status = _case_status(written_patch, patch_validation, contract_errors, dangerous_findings)
    artifact_paths = {
        "input_case": _relative(input_path, root),
        "passport": _relative(passport_path, root),
        "fluent_hints": _relative(hints_path, root),
        "case_summary": _relative(report_path, root),
        "solver_plan_patch": _relative(case_dir / "solver_plan_patch.json", root),
        "solver_plan_patch_report": _relative(case_dir / "solver_plan_patch_report.md", root),
    }
    return {
        "case_id": spec.case_id,
        "module": spec.module,
        "case_name": spec.case_name,
        "expected_status": spec.expected_status,
        "actual_status": actual_status,
        "artifact_paths": artifact_paths,
        "patch_valid": patch_valid,
        "patch_validation": patch_validation.to_dict(),
        "contract_errors": contract_errors,
        "dangerous_key_findings": dangerous_findings,
        "warnings": sorted(set(list(written_patch.get("warnings", [])) + list(passport.get("warnings", [])))),
        "blocking_errors": sorted(set(list(written_patch.get("blocking_errors", [])) + list(passport.get("blocking_errors", [])) + contract_errors)),
        "key_quantities": key_quantities,
        "patch": written_patch,
    }


def _run_combined_cases(root: Path, patches: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    combined_specs = [
        (
            "combined_case_01_vof_turbulence",
            "Combined VOF and turbulence patch",
            "pass",
            [patches["vof_case_01_gravity_dominant"], patches["turbulence_case_03_high_re_sst"]],
        ),
        (
            "combined_case_02_solid_liquid_turbulence",
            "Combined solid-liquid and turbulence patch",
            "warn",
            [patches["solid_liquid_case_01_dilute_dpm"], patches["turbulence_case_03_high_re_sst"]],
        ),
        (
            "combined_case_03_steam_air_rheology",
            "Combined steam-air v2 and rheology patch",
            "warn",
            [patches["steam_air_case_01_baseline"], patches["rheology_case_03_carreau_yasuda"]],
        ),
        (
            "combined_case_04_conflict_review",
            "Combined turbulence conflict review patch",
            "warn",
            _conflict_patch_pair(patches["turbulence_case_03_high_re_sst"]),
        ),
    ]
    results = []
    for case_id, case_name, expected_status, inputs in combined_specs:
        case_dir = root / "combined_patch_cases" / case_id
        _mkdir(case_dir)
        merged = merge_solver_plan_patches(inputs)
        patch_result = write_solver_plan_patch_bundle(merged, output=case_dir / "combined_solver_plan_patch.json")
        written_patch = patch_result["outputs"]["patch"]
        validation = validate_solver_plan_patch(written_patch)
        contract_errors = _patch_contract_errors(written_patch)
        dangerous_findings = find_dangerous_keys(written_patch)
        conflict_summary = {
            "schema_version": "fromcad2cfd_fastfluent_combined_patch_conflict_summary_v1",
            "case_id": case_id,
            "patch_status": written_patch.get("status"),
            "patch_valid": validation.passed and not contract_errors and not dangerous_findings,
            "warning_count": len(written_patch.get("warnings", [])),
            "conflict_warnings": [item for item in written_patch.get("warnings", []) if "Conflicting replace patch" in item],
            "blocking_errors": list(written_patch.get("blocking_errors", [])) + contract_errors,
            "fluent_launched": False,
        }
        summary_path = _write_json(case_dir / "conflict_summary.json", conflict_summary)
        _write_text(case_dir / "case_summary.md", _combined_case_summary(case_name, written_patch, conflict_summary))
        results.append(
            {
                "case_id": case_id,
                "module": "combined_patches",
                "case_name": case_name,
                "expected_status": expected_status,
                "actual_status": _case_status(written_patch, validation, contract_errors, dangerous_findings),
                "artifact_paths": {
                    "combined_solver_plan_patch": _relative(case_dir / "combined_solver_plan_patch.json", root),
                    "combined_solver_plan_patch_report": _relative(case_dir / "combined_solver_plan_patch_report.md", root),
                    "conflict_summary": _relative(summary_path, root),
                    "case_summary": _relative(case_dir / "case_summary.md", root),
                },
                "patch_valid": validation.passed and not contract_errors and not dangerous_findings,
                "patch_validation": validation.to_dict(),
                "contract_errors": contract_errors,
                "dangerous_key_findings": dangerous_findings,
                "warnings": list(written_patch.get("warnings", [])),
                "blocking_errors": list(written_patch.get("blocking_errors", [])) + contract_errors,
                "key_quantities": {
                    "merge_count": written_patch.get("metadata", {}).get("merge_count"),
                    "patch_count": len(written_patch.get("patches", [])),
                    "evidence_count": len(written_patch.get("evidence", [])),
                    "conflict_warning_count": len(conflict_summary["conflict_warnings"]),
                },
                "patch": written_patch,
            }
        )
    return results


def _build_case_artifacts(
    module: str,
    case_payload: dict[str, Any] | VOFCase | TurbulenceCase | RheologyCase,
    source_artifact: str,
) -> tuple[dict[str, Any], dict[str, Any], str, dict[str, Any]]:
    if module == "vof":
        case = case_payload
        assert isinstance(case, VOFCase)
        passport = build_vof_physics_passport(case)
        hints = build_vof_fluent_setup_hints(case, passport)
        report = _module_report(module, passport, hints)
        quantities = _select_keys(passport.get("checks", {}), ["courant_number", "bond_number", "weber_number", "density_ratio"])
        return passport, hints, report, quantities
    if module == "turbulence":
        case = case_payload
        assert isinstance(case, TurbulenceCase)
        passport = build_turbulence_passport(case)
        hints = build_turbulence_fluent_setup_hints(case, passport)
        report = _module_report(module, passport, hints)
        quantities = _select_keys(passport.get("checks", {}), ["reynolds_number", "estimated_y_plus", "target_y_plus_max"])
        quantities["flow_regime"] = passport.get("flow_regime")
        quantities["recommended_model_family"] = passport.get("recommended_model_family")
        return passport, hints, report, quantities
    if module == "rheology":
        case = case_payload
        assert isinstance(case, RheologyCase)
        passport = build_rheology_passport(case)
        hints = build_rheology_fluent_setup_hints(case, passport)
        report = _module_report(module, passport, hints)
        quantities = _select_keys(passport.get("checks", {}), ["min_apparent_viscosity_pa_s", "max_apparent_viscosity_pa_s", "viscosity_ratio", "trend"])
        return passport, hints, report, quantities
    if module == "steam_air_v2":
        case = case_payload
        assert isinstance(case, dict)
        passport = build_steam_air_condensation_passport_v2(case, source_artifact=source_artifact)
        hints = build_steam_air_fluent_hints_v2(passport)
        report = steam_air_condensation_report_v2(passport, hints)
        computed = passport.get("computed_quantities", {})
        quantities = _select_keys(
            computed,
            ["reynolds_number", "wall_subcooling_K", "mass_transfer_resistance", "source_term_stiffness_level", "estimated_htc_W_m2K"],
        )
        return passport, hints, report, quantities
    if module == "solid_liquid":
        case = case_payload
        assert isinstance(case, dict)
        passport = build_solid_liquid_suspension_passport(case, source_artifact=source_artifact)
        hints = build_solid_liquid_fluent_hints(passport)
        report = solid_liquid_suspension_report(passport, hints)
        computed = passport.get("computed_quantities", {})
        quantities = _select_keys(
            computed,
            ["recommended_model", "particle_reynolds_number", "stokes_number", "cell_particle_ratio", "particle_time_step_risk"],
        )
        return passport, hints, report, quantities
    raise ValueError(f"Unsupported validation-pack module: {module}")


def _build_manifest(root: Path, case_results: list[dict[str, Any]]) -> dict[str, Any]:
    module_counts: dict[str, int] = {}
    for result in case_results:
        module_counts[result["module"]] = module_counts.get(result["module"], 0) + 1
    status_counts: dict[str, int] = {}
    for result in case_results:
        status_counts[result["actual_status"]] = status_counts.get(result["actual_status"], 0) + 1

    artifact_index: dict[str, str] = {}
    for result in case_results:
        for name, path in result["artifact_paths"].items():
            artifact_index[f"{result['case_id']}:{name}"] = path

    validation_errors = [
        {"case_id": result["case_id"], "errors": result["contract_errors"] + result["dangerous_key_findings"]}
        for result in case_results
        if result["contract_errors"] or result["dangerous_key_findings"]
    ]
    case_index = [
        {key: result[key] for key in [
            "case_id",
            "module",
            "case_name",
            "expected_status",
            "actual_status",
            "artifact_paths",
            "patch_valid",
            "warnings",
            "blocking_errors",
            "key_quantities",
        ]}
        for result in case_results
    ]
    return {
        "schema_version": VALIDATION_PACK_SCHEMA_VERSION,
        "created_by": "fromcad2cfd_fastfluent",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(case_results),
        "module_counts": module_counts,
        "case_index": case_index,
        "artifact_index": artifact_index,
        "test_status_summary": {
            "actual_status_counts": status_counts,
            "valid_patch_count": sum(1 for result in case_results if result["patch_valid"]),
            "invalid_patch_count": sum(1 for result in case_results if not result["patch_valid"]),
            "warning_case_count": sum(1 for result in case_results if result["warnings"]),
            "blocking_case_count": sum(1 for result in case_results if result["blocking_errors"]),
            "validation_error_count": len(validation_errors),
            "validation_errors": validation_errors,
        },
        "limitations": list(LIMITATIONS),
        "metadata": {
            "output_dir": str(root),
            "fluent_launched": False,
            "case_generation": "synthetic_public_safe",
            "minimum_required_case_count": 27,
        },
    }


def _validation_summary_markdown(manifest: dict[str, Any]) -> str:
    status = manifest["test_status_summary"]
    lines = [
        "# FastFluent Horizontal H3.5 Validation Pack",
        "",
        "This validation pack covers H1-H3 FastFluent horizontal capabilities with synthetic public cases.",
        "",
        "## Overall Status",
        "",
        f"- Case count: `{manifest['case_count']}`",
        f"- Valid patches: `{status['valid_patch_count']}`",
        f"- Invalid patches: `{status['invalid_patch_count']}`",
        f"- Warning cases: `{status['warning_case_count']}`",
        f"- Blocking review cases: `{status['blocking_case_count']}`",
        f"- Fluent launched: `False`",
        "",
        "## Module Counts",
        "",
        "| Module | Count |",
        "| --- | ---: |",
    ]
    for module, count in sorted(manifest["module_counts"].items()):
        lines.append(f"| `{module}` | {count} |")

    lines.extend(["", "## Case Index", "", "| Case ID | Module | Expected | Actual | Patch valid | Warnings | Blocking errors |", "| --- | --- | --- | --- | --- | ---: | ---: |"])
    for case in manifest["case_index"]:
        lines.append(
            f"| `{case['case_id']}` | `{case['module']}` | `{case['expected_status']}` | `{case['actual_status']}` | "
            f"`{case['patch_valid']}` | {len(case['warnings'])} | {len(case['blocking_errors'])} |"
        )

    combined = [case for case in manifest["case_index"] if case["module"] == "combined_patches"]
    lines.extend(["", "## Combined Patch Summary", "", "| Case ID | Patch count | Evidence count | Conflict warnings |", "| --- | ---: | ---: | ---: |"])
    for case in combined:
        quantities = case.get("key_quantities", {})
        lines.append(
            f"| `{case['case_id']}` | {quantities.get('patch_count')} | {quantities.get('evidence_count')} | {quantities.get('conflict_warning_count')} |"
        )

    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in manifest["limitations"])
    lines.extend(
        [
            "",
            "## Explicit Fluent Boundary",
            "",
            "Fluent was not launched. This pack generated setup evidence, setup hints, and non-executing solver-plan patches only.",
            "",
        ]
    )
    return "\n".join(lines)


def _case_summary_markdown(spec: ValidationCaseSpec, passport: dict[str, Any], hints: dict[str, Any], report_text: str) -> str:
    lines = [
        f"# {spec.case_name}",
        "",
        f"- Case ID: `{spec.case_id}`",
        f"- Module: `{spec.module}`",
        f"- Expected status: `{spec.expected_status}`",
        f"- Passport status: `{passport.get('status')}`",
        f"- Hints status: `{hints.get('status')}`",
        f"- Fluent launched: `False`",
        "",
        "## Module Report",
        "",
        report_text,
        "",
    ]
    return "\n".join(lines)


def _combined_case_summary(case_name: str, patch: dict[str, Any], conflict_summary: dict[str, Any]) -> str:
    lines = [
        f"# {case_name}",
        "",
        f"- Patch status: `{patch.get('status')}`",
        f"- Patch count: `{len(patch.get('patches', []))}`",
        f"- Evidence count: `{len(patch.get('evidence', []))}`",
        f"- Conflict warnings: `{len(conflict_summary.get('conflict_warnings', []))}`",
        f"- Fluent launched: `False`",
        "",
        "## Warnings",
        "",
    ]
    lines.extend(f"- {item}" for item in patch.get("warnings", [])) if patch.get("warnings") else lines.append("- None")
    lines.extend(["", "## Blocking Errors", ""])
    lines.extend(f"- {item}" for item in patch.get("blocking_errors", [])) if patch.get("blocking_errors") else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _module_report(module: str, passport: dict[str, Any], hints: dict[str, Any]) -> str:
    if module == "vof":
        checks = passport.get("checks", {})
        return "\n".join(
            [
                "### VOF Checks",
                "",
                f"- Courant number: `{checks.get('courant_number')}`",
                f"- Bond number: `{checks.get('bond_number')}`",
                f"- Weber number: `{checks.get('weber_number')}`",
                f"- Density ratio: `{checks.get('density_ratio')}`",
            ]
        )
    if module == "turbulence":
        checks = passport.get("checks", {})
        return "\n".join(
            [
                "### Turbulence Checks",
                "",
                f"- Reynolds number: `{checks.get('reynolds_number')}`",
                f"- Flow regime: `{passport.get('flow_regime')}`",
                f"- Estimated y-plus: `{checks.get('estimated_y_plus')}`",
                f"- Recommended model family: `{passport.get('recommended_model_family')}`",
            ]
        )
    if module == "rheology":
        checks = passport.get("checks", {})
        return "\n".join(
            [
                "### Rheology Checks",
                "",
                f"- Trend: `{checks.get('trend')}`",
                f"- Min apparent viscosity: `{checks.get('min_apparent_viscosity_pa_s')}`",
                f"- Max apparent viscosity: `{checks.get('max_apparent_viscosity_pa_s')}`",
                f"- Viscosity ratio: `{checks.get('viscosity_ratio')}`",
            ]
        )
    return json.dumps({"passport_status": passport.get("status"), "hints_status": hints.get("status")}, ensure_ascii=True, indent=2)


def _patch_contract_errors(patch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for index, operation in enumerate(patch.get("patches", [])):
        path = str(operation.get("path", ""))
        if any(path == prefix or path.startswith(prefix + "/") for prefix in EVIDENCE_REQUIRED_PREFIXES):
            if operation.get("op") not in {"warn", "block"} and not operation.get("evidence_refs"):
                errors.append(f"Patch operation {index} at {path} requires evidence_refs for validation-pack acceptance.")
    return errors


def _artifact_dangerous_findings(*artifacts: Any) -> list[str]:
    findings: list[str] = []
    for index, artifact in enumerate(artifacts):
        findings.extend(f"artifact[{index}]{path[1:]}" for path in find_dangerous_keys(artifact))
    return findings


def _case_status(
    patch: dict[str, Any],
    validation: Any,
    contract_errors: list[str],
    dangerous_findings: list[str],
) -> str:
    if not validation.passed or contract_errors or dangerous_findings:
        return "block"
    status = str(patch.get("status", "block"))
    return status if status in {"pass", "warn", "block"} else "block"


def _conflict_patch_pair(base_patch: dict[str, Any]) -> list[dict[str, Any]]:
    first = deepcopy(base_patch)
    second = deepcopy(base_patch)
    second["case_name"] = str(second.get("case_name", "turbulence_conflict")) + "_conflicting_laminar_review"
    second["status"] = "warn"
    second["warnings"] = sorted(set(second.get("warnings", []) + ["Synthetic validation-pack conflict case."]))
    for operation in second.get("patches", []):
        if operation.get("op") == "replace" and operation.get("path") == "/physics/turbulence/model":
            operation["value"] = "laminar"
            operation["reason"] = "Synthetic validation-pack conflict branch for merge-warning coverage."
            break
    return [first, second]


def _case_to_dict(case_payload: dict[str, Any] | VOFCase | TurbulenceCase | RheologyCase) -> dict[str, Any]:
    if hasattr(case_payload, "to_dict"):
        return case_payload.to_dict()  # type: ignore[no-any-return]
    return dict(case_payload)


def _select_keys(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys if key in payload}


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    _mkdir(path.parent)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    return path


def _write_text(path: Path, text: str) -> Path:
    _mkdir(path.parent)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _mkdir(path: Path) -> None:
    os.makedirs(_windows_long_path(path), exist_ok=True)


def _windows_long_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _vof_gravity_case() -> VOFCase:
    case = demo_vof_case(case_name="h35_vof_gravity_dominant")
    return VOFCase(
        case_name=case.case_name,
        domain={"dimension": 2, "length_scale_mm": 100.0, "cell_length_mm": 1.0, "expected_interface_cells": 1.0},
        phases=case.phases,
        surface_tension_n_m=0.01,
        gravity_m_s2=(0.0, -9.81, 0.0),
        reference_velocity_m_s=0.2,
        time_step_s=0.001,
        interface=case.interface,
        metadata={"public_safe": True, "purpose": "gravity-dominant VOF validation-pack case"},
    )


def _vof_capillary_case() -> VOFCase:
    case = demo_vof_case(case_name="h35_vof_capillary_dominant")
    return VOFCase(
        case_name=case.case_name,
        domain={"dimension": 2, "length_scale_mm": 1.0, "cell_length_mm": 0.05, "expected_interface_cells": 0.75},
        phases=case.phases,
        surface_tension_n_m=0.072,
        gravity_m_s2=(0.0, -9.81, 0.0),
        reference_velocity_m_s=0.05,
        time_step_s=5.0e-4,
        interface={"initialization": "small_slug", "capturing": "geometric_reconstruction", "interface_thickness_cells": 0.75},
        metadata={"public_safe": True, "purpose": "capillary VOF validation-pack case"},
    )


def _vof_high_density_ratio_case() -> VOFCase:
    water = VOFPhase("water", "primary_liquid", 998.2, 1.003e-3, 0.5)
    light_gas = VOFPhase("light_gas", "secondary_gas", 0.2, 1.0e-5, 0.5)
    return VOFCase(
        case_name="h35_vof_high_density_ratio",
        domain={"dimension": 2, "length_scale_mm": 50.0, "cell_length_mm": 0.5, "expected_interface_cells": 1.0},
        phases=[water, light_gas],
        surface_tension_n_m=0.05,
        gravity_m_s2=(0.0, -9.81, 0.0),
        reference_velocity_m_s=0.1,
        time_step_s=0.001,
        interface={"initialization": "stratified", "capturing": "geometric_reconstruction", "interface_thickness_cells": 1.0},
        metadata={"public_safe": True, "purpose": "high density-ratio VOF validation-pack case"},
    )


def _vof_high_cfl_case() -> VOFCase:
    case = demo_vof_case(case_name="h35_vof_high_cfl_block")
    return VOFCase(
        case_name=case.case_name,
        domain={"dimension": 2, "length_scale_mm": 50.0, "cell_length_mm": 1.0, "expected_interface_cells": 1.0},
        phases=case.phases,
        surface_tension_n_m=0.072,
        gravity_m_s2=(0.0, -9.81, 0.0),
        reference_velocity_m_s=0.5,
        time_step_s=0.003,
        interface=case.interface,
        metadata={"public_safe": True, "purpose": "VOF Courant block validation-pack case"},
    )


def _turbulence_laminar_case() -> TurbulenceCase:
    return TurbulenceCase(
        case_name="h35_turbulence_laminar_channel",
        domain={"geometry_kind": "internal_channel", "length_scale_mm": 40.0, "hydraulic_diameter_mm": 40.0, "target_y_plus_min": 0.5, "target_y_plus_max": 2.0},
        fluid={"name": "water", "density_kg_m3": 998.2, "dynamic_viscosity_pa_s": 1.003e-3},
        reference_velocity_m_s=0.01,
        model_intent="laminar",
        turbulence_intensity_percent=None,
        first_cell_height_mm=None,
        wall_treatment="laminar",
        metadata={"public_safe": True, "purpose": "laminar turbulence validation-pack case"},
    )


def _turbulence_transition_case() -> TurbulenceCase:
    return TurbulenceCase(
        case_name="h35_turbulence_transitional_channel",
        domain={"geometry_kind": "internal_channel", "length_scale_mm": 40.0, "hydraulic_diameter_mm": 40.0, "target_y_plus_min": 0.5, "target_y_plus_max": 2.0},
        fluid={"name": "water", "density_kg_m3": 998.2, "dynamic_viscosity_pa_s": 1.003e-3},
        reference_velocity_m_s=0.08,
        model_intent="rans_sst",
        turbulence_intensity_percent=5.0,
        first_cell_height_mm=0.02,
        wall_treatment="low_re_sst",
        metadata={"public_safe": True, "purpose": "transitional turbulence validation-pack case"},
    )


def _turbulence_high_re_case() -> TurbulenceCase:
    case = demo_turbulence_case(case_name="h35_turbulence_high_re_sst")
    return TurbulenceCase(
        case_name=case.case_name,
        domain=case.domain,
        fluid=case.fluid,
        reference_velocity_m_s=2.0,
        model_intent="rans_sst",
        turbulence_intensity_percent=5.0,
        first_cell_height_mm=0.01,
        wall_treatment="low_re_sst",
        metadata={"public_safe": True, "purpose": "high-Re SST validation-pack case"},
    )


def _turbulence_yplus_case() -> TurbulenceCase:
    case = demo_turbulence_case(case_name="h35_turbulence_yplus_review")
    return TurbulenceCase(
        case_name=case.case_name,
        domain=case.domain,
        fluid=case.fluid,
        reference_velocity_m_s=0.5,
        model_intent="rans_sst",
        turbulence_intensity_percent=5.0,
        first_cell_height_mm=0.5,
        wall_treatment="low_re_sst",
        metadata={"public_safe": True, "purpose": "y-plus review validation-pack case"},
    )


def _rheology_newtonian_case() -> RheologyCase:
    return RheologyCase(
        case_name="h35_rheology_newtonian",
        model="newtonian",
        parameters={"dynamic_viscosity_pa_s": 0.001},
        shear_rate_range_1_s=(1.0, 1000.0),
        sample_count=9,
        density_kg_m3=998.2,
        temperature_k=298.15,
        metadata={"public_safe": True, "purpose": "Newtonian rheology validation-pack case"},
    )


def _rheology_power_law_case() -> RheologyCase:
    return RheologyCase(
        case_name="h35_rheology_power_law_thinning",
        model="power_law",
        parameters={"consistency_pa_s_n": 0.35, "flow_behavior_index": 0.65, "min_viscosity_pa_s": 0.01, "max_viscosity_pa_s": 10.0},
        shear_rate_range_1_s=(0.1, 1000.0),
        sample_count=13,
        density_kg_m3=1030.0,
        temperature_k=298.15,
        metadata={"public_safe": True, "purpose": "power-law rheology validation-pack case"},
    )


def _rheology_carreau_case() -> RheologyCase:
    return RheologyCase(
        case_name="h35_rheology_carreau_yasuda",
        model="carreau_yasuda",
        parameters={
            "zero_shear_viscosity_pa_s": 4.0,
            "infinite_shear_viscosity_pa_s": 0.02,
            "time_constant_s": 1.2,
            "power_index": 0.45,
            "transition_index": 2.0,
        },
        shear_rate_range_1_s=(0.1, 500.0),
        sample_count=11,
        density_kg_m3=1050.0,
        temperature_k=298.15,
        metadata={"public_safe": True, "purpose": "Carreau-Yasuda rheology validation-pack case"},
    )


def _rheology_high_ratio_case() -> RheologyCase:
    return RheologyCase(
        case_name="h35_rheology_large_viscosity_ratio",
        model="power_law",
        parameters={"consistency_pa_s_n": 10.0, "flow_behavior_index": 0.15, "min_viscosity_pa_s": 1.0e-5, "max_viscosity_pa_s": 1.0e5},
        shear_rate_range_1_s=(1.0e-3, 1.0e5),
        sample_count=13,
        density_kg_m3=1200.0,
        temperature_k=298.15,
        metadata={"public_safe": True, "purpose": "large viscosity-ratio rheology validation-pack case"},
    )


def _steam_air_baseline_case() -> dict[str, Any]:
    return demo_steam_air_condensation_case_v2(case_name="h35_steam_air_baseline")


def _steam_air_warm_wall_case() -> dict[str, Any]:
    case = demo_steam_air_condensation_case_v2(case_name="h35_steam_air_warm_wall")
    case["wall_temperature_K"] = 500.0
    return case


def _steam_air_noncondensable_case() -> dict[str, Any]:
    case = demo_steam_air_condensation_case_v2(case_name="h35_steam_air_noncondensable_risk")
    case["steam_mass_fraction"] = 0.70
    case["air_mass_fraction"] = 0.30
    return case


def _steam_air_source_stiffness_case() -> dict[str, Any]:
    case = demo_steam_air_condensation_case_v2(case_name="h35_steam_air_source_stiffness")
    case["time_step_s"] = 0.02
    return case


def _steam_air_turbulent_case() -> dict[str, Any]:
    case = demo_steam_air_condensation_case_v2(case_name="h35_steam_air_turbulent_thermal")
    case["reference_velocity_m_s"] = 60.0
    case["near_wall_cell_length_m"] = 0.001
    return case


def _solid_liquid_dilute_case() -> dict[str, Any]:
    return demo_solid_liquid_suspension_case(case_name="h35_solid_liquid_dilute_dpm")


def _solid_liquid_two_way_case() -> dict[str, Any]:
    case = demo_solid_liquid_suspension_case(case_name="h35_solid_liquid_two_way_loading")
    case["particle_density_kg_m3"] = 40000.0
    return case


def _solid_liquid_mixture_case() -> dict[str, Any]:
    case = demo_solid_liquid_suspension_case(case_name="h35_solid_liquid_mixture_model")
    case["solid_volume_fraction"] = 0.03
    case["relative_velocity_m_s"] = 0.01
    return case


def _solid_liquid_dense_case() -> dict[str, Any]:
    case = demo_solid_liquid_suspension_case(case_name="h35_solid_liquid_dense_eulerian")
    case["solid_volume_fraction"] = 0.15
    return case


def _solid_liquid_time_step_case() -> dict[str, Any]:
    case = demo_solid_liquid_suspension_case(case_name="h35_solid_liquid_time_step_risk")
    case["time_step_s"] = 0.01
    return case


def _solid_liquid_cell_particle_block_case() -> dict[str, Any]:
    case = demo_solid_liquid_suspension_case(case_name="h35_solid_liquid_cell_particle_block")
    case["cell_size_m"] = 10.0e-6
    return case
