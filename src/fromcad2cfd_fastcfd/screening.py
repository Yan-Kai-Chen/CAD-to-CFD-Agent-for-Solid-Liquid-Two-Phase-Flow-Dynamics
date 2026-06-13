"""Bounded parameter screening utilities for FastCFD jobs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .paths import unique_path
from .physics_validator import validate_physics
from .schemas import FastCFDJob, read_job


PARAMETER_SCREENING_SCHEMA_VERSION = "fromcad2cfd_fastcfd_parameter_screening_v1"


def run_parameter_screening(
    job_file: str | Path,
    *,
    velocity_multipliers: list[float] | None = None,
    cell_length_multipliers: list[float] | None = None,
    max_variants: int = 12,
    keep_domain_size: bool = True,
    output_dir: str | Path | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Create a bounded physics-screening matrix without running the solver."""

    base_job = read_job(job_file)
    v_mults = _validated_multipliers(velocity_multipliers or [0.5, 1.0, 2.0], "velocity_multipliers")
    dx_mults = _validated_multipliers(cell_length_multipliers or [1.0], "cell_length_multipliers")
    max_variants = int(max_variants)
    if max_variants <= 0:
        raise ValueError("max_variants must be positive.")
    variants = []
    for velocity_multiplier in v_mults:
        for cell_multiplier in dx_mults:
            if len(variants) >= max_variants:
                break
            variant = _variant_job(
                base_job,
                velocity_multiplier=velocity_multiplier,
                cell_length_multiplier=cell_multiplier,
                keep_domain_size=keep_domain_size,
                index=len(variants) + 1,
            )
            contract = validate_physics(variant, profile="agent")
            variants.append(
                {
                    "variant_id": f"v{len(variants) + 1:02d}",
                    "velocity_multiplier": velocity_multiplier,
                    "cell_length_multiplier": cell_multiplier,
                    "job": variant.to_dict(),
                    "physics_contract": contract.to_dict(),
                    "screening_score": _screening_score(contract.to_dict()),
                    "screening_verdict": _screening_verdict(contract.to_dict()),
                }
            )
        if len(variants) >= max_variants:
            break
    ranked = sorted(variants, key=lambda item: item["screening_score"], reverse=True)
    report = {
        "schema_version": PARAMETER_SCREENING_SCHEMA_VERSION,
        "status": "success",
        "base_job_file": str(job_file),
        "case_type": base_job.case_type,
        "backend": base_job.backend,
        "model_name": model_name or f"{base_job.model_name}_parameter_screening",
        "keep_domain_size": keep_domain_size,
        "variant_count": len(variants),
        "max_variants": max_variants,
        "ranked_variants": ranked,
        "recommended_variants": [item for item in ranked if item["screening_verdict"] in {"recommended", "usable_with_warning"}][:3],
        "blocked_variants": [item for item in ranked if item["screening_verdict"] == "blocked"],
        "limitations": [
            "This is a bounded pre-run physics screen; it does not execute FastFluent.",
            "Use it to choose which simple FastFluent cases are worth running next.",
            "Final design decisions still require actual solver output and later high-fidelity validation.",
        ],
    }
    if output_dir is not None:
        paths = write_parameter_screening_artifacts(report, output_dir=output_dir, model_name=report["model_name"])
        report["artifacts"] = paths
    return report


def write_parameter_screening_artifacts(
    report: dict[str, Any],
    *,
    output_dir: str | Path,
    model_name: str,
) -> dict[str, str]:
    """Write parameter screening JSON and Markdown reports."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = unique_path(output / f"{model_name}.json")
    json_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    markdown_path = unique_path(output / f"{model_name}.md")
    markdown_path.write_text(parameter_screening_markdown(report), encoding="utf-8")
    return {"parameter_screening_json": str(json_path), "parameter_screening_markdown": str(markdown_path)}


def parameter_screening_markdown(report: dict[str, Any]) -> str:
    """Render a compact parameter screening report."""

    lines = [
        "# FastCFD Parameter Screening",
        "",
        f"Status: `{report.get('status')}`",
        f"Case type: `{report.get('case_type')}`",
        f"Variant count: `{report.get('variant_count')}`",
        "",
        "## Recommended Variants",
        "",
    ]
    for item in report.get("recommended_variants") or []:
        checks = item["physics_contract"]["checks"]
        lines.append(
            f"- `{item['variant_id']}` score `{item['screening_score']}`: "
            f"velocity x{item['velocity_multiplier']}, cell length x{item['cell_length_multiplier']}, "
            f"Re `{checks.get('reynolds_number')}`, Ma `{checks.get('mach_lattice_estimate')}`, "
            f"verdict `{item['screening_verdict']}`"
        )
    if not report.get("recommended_variants"):
        lines.append("- No variants passed the current physics screen.")
    lines.extend(["", "## Blocked Variants", ""])
    for item in report.get("blocked_variants") or []:
        errors = "; ".join(item["physics_contract"]["checks"].get("errors") or [])
        lines.append(f"- `{item['variant_id']}`: {errors}")
    if not report.get("blocked_variants"):
        lines.append("- None.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.get("limitations") or [])
    lines.append("")
    return "\n".join(lines)


def _variant_job(
    base_job: FastCFDJob,
    *,
    velocity_multiplier: float,
    cell_length_multiplier: float,
    keep_domain_size: bool,
    index: int,
) -> FastCFDJob:
    payload = copy.deepcopy(base_job.to_dict())
    payload["model_name"] = f"{base_job.model_name}_screen_v{index:02d}"
    payload["boundary_conditions"] = _scaled_boundary_conditions(payload["boundary_conditions"], velocity_multiplier)
    payload["dimensions"] = _scaled_dimensions(payload["dimensions"], cell_length_multiplier, keep_domain_size=keep_domain_size)
    payload["metadata"] = dict(payload.get("metadata") or {})
    payload["metadata"]["screening_variant"] = {
        "velocity_multiplier": velocity_multiplier,
        "cell_length_multiplier": cell_length_multiplier,
        "keep_domain_size": keep_domain_size,
    }
    job = FastCFDJob(
        case_type=payload["case_type"],
        backend=payload["backend"],
        output_dir=payload["output_dir"],
        model_name=payload["model_name"],
        units=payload["units"],
        dimensions=payload["dimensions"],
        physical_properties=payload["physical_properties"],
        boundary_conditions=payload["boundary_conditions"],
        solver_settings=payload["solver_settings"],
        metadata=payload["metadata"],
        schema_version=payload["schema_version"],
    )
    job.validate()
    return job


def _scaled_boundary_conditions(boundary_conditions: dict[str, Any], multiplier: float) -> dict[str, Any]:
    result = copy.deepcopy(boundary_conditions)
    for key in ("moving_wall_velocity_mm_s", "inlet_velocity_mm_s", "reference_velocity_mm_s", "u_ref_mm_s"):
        if key in result:
            result[key] = float(result[key]) * multiplier
    return result


def _scaled_dimensions(dimensions: dict[str, Any], multiplier: float, *, keep_domain_size: bool) -> dict[str, Any]:
    result = copy.deepcopy(dimensions)
    old_cell = float(result["cell_length_mm"])
    new_cell = old_cell * multiplier
    result["cell_length_mm"] = new_cell
    if keep_domain_size:
        for key in ("nx", "ny", "nz"):
            if key in result:
                physical = int(result[key]) * old_cell
                result[key] = max(2, int(round(physical / new_cell)))
    return result


def _screening_score(contract: dict[str, Any]) -> float:
    status = contract.get("status")
    if status == "failed":
        return 0.0
    score = 1.0 if status == "passed" else 0.65
    checks = contract.get("checks") if isinstance(contract.get("checks"), dict) else {}
    mach = _safe_float(checks.get("mach_lattice_estimate"))
    tau = _safe_float(checks.get("tau"))
    if mach is not None:
        score -= min(0.35, max(0.0, mach - 0.04) * 4.0)
    if tau is not None and 0.55 <= tau <= 1.2:
        score += 0.05
    return round(max(0.0, min(1.0, score)), 4)


def _screening_verdict(contract: dict[str, Any]) -> str:
    if contract.get("status") == "failed":
        return "blocked"
    if contract.get("status") == "warning":
        return "usable_with_warning"
    return "recommended"


def _validated_multipliers(values: list[float], name: str) -> list[float]:
    result = []
    for value in values:
        number = float(value)
        if number <= 0:
            raise ValueError(f"{name} must contain positive multipliers.")
        result.append(number)
    if not result:
        raise ValueError(f"{name} must not be empty.")
    return result


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
