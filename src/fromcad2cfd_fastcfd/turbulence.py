"""Turbulence passport and Fluent setup hints for FastFluent workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .paths import unique_path


TURBULENCE_CASE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_turbulence_case_v1"
TURBULENCE_PASSPORT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_turbulence_passport_v1"
TURBULENCE_HINTS_SCHEMA_VERSION = "fromcad2cfd_fastfluent_turbulence_fluent_hints_v1"

SUPPORTED_MODEL_INTENTS = {"laminar", "rans_k_epsilon", "rans_sst", "rans_realizable_k_epsilon"}


@dataclass(frozen=True)
class TurbulenceCase:
    case_name: str
    domain: dict[str, Any]
    fluid: dict[str, Any]
    reference_velocity_m_s: float
    model_intent: str = "rans_sst"
    turbulence_intensity_percent: float | None = None
    first_cell_height_mm: float | None = None
    wall_treatment: str = "automatic"
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = TURBULENCE_CASE_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TurbulenceCase":
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            case_name=str(payload["case_name"]),
            domain=dict(payload["domain"]),
            fluid=dict(payload["fluid"]),
            reference_velocity_m_s=float(payload["reference_velocity_m_s"]),
            model_intent=str(payload.get("model_intent", "rans_sst")),
            turbulence_intensity_percent=(
                None if payload.get("turbulence_intensity_percent") is None else float(payload["turbulence_intensity_percent"])
            ),
            first_cell_height_mm=None if payload.get("first_cell_height_mm") is None else float(payload["first_cell_height_mm"]),
            wall_treatment=str(payload.get("wall_treatment", "automatic")),
            metadata=dict(payload.get("metadata") or {}),
        )

    def validate_schema(self) -> None:
        if self.schema_version != TURBULENCE_CASE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported turbulence case schema: {self.schema_version}")
        if not self.case_name or any(ch in self.case_name for ch in "\\/:*?\"<>|"):
            raise ValueError("Turbulence case_name must be non-empty and filesystem-safe.")
        if self.model_intent not in SUPPORTED_MODEL_INTENTS:
            raise ValueError(f"Unsupported turbulence model_intent: {self.model_intent}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_name": self.case_name,
            "domain": self.domain,
            "fluid": self.fluid,
            "reference_velocity_m_s": self.reference_velocity_m_s,
            "model_intent": self.model_intent,
            "turbulence_intensity_percent": self.turbulence_intensity_percent,
            "first_cell_height_mm": self.first_cell_height_mm,
            "wall_treatment": self.wall_treatment,
            "metadata": self.metadata,
        }


def demo_turbulence_case(*, case_name: str = "public_channel2d_turbulence_passport") -> TurbulenceCase:
    return TurbulenceCase(
        case_name=case_name,
        domain={
            "geometry_kind": "internal_channel",
            "length_scale_mm": 40.0,
            "hydraulic_diameter_mm": 40.0,
            "target_y_plus_min": 0.5,
            "target_y_plus_max": 2.0,
        },
        fluid={"name": "water", "density_kg_m3": 998.2, "dynamic_viscosity_pa_s": 1.003e-3},
        reference_velocity_m_s=0.5,
        model_intent="rans_sst",
        turbulence_intensity_percent=5.0,
        first_cell_height_mm=0.01,
        wall_treatment="low_re_sst",
        metadata={"public_safe": True, "purpose": "turbulence setup passport smoke case"},
    )


def write_demo_turbulence_case(
    *,
    output_dir: str | Path | None = None,
    case_name: str = "public_channel2d_turbulence_passport",
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / case_name / "input")
    target_dir.mkdir(parents=True, exist_ok=True)
    case = demo_turbulence_case(case_name=case_name)
    case_path = target_dir / "turbulence_case.json"
    _write_json(case_path, case.to_dict())
    return {"case_file": str(case_path), "case": case.to_dict()}


def read_turbulence_case(path: str | Path) -> TurbulenceCase:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    _assert_no_dangerous_keys(payload)
    case = TurbulenceCase.from_dict(payload)
    case.validate_schema()
    return case


def validate_turbulence_case_file(
    case_file: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    case_path = Path(case_file)
    target_dir = Path(output_dir) if output_dir else unique_path(case_path.parent / f"{case_path.stem}_turbulence_passport")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        case = read_turbulence_case(case_path)
        passport = build_turbulence_passport(case)
        hints = build_turbulence_fluent_setup_hints(case, passport)
        artifacts = {
            "turbulence_case_copy": str(_write_json(target_dir / "turbulence_case.json", case.to_dict())),
            "turbulence_passport": str(_write_json(target_dir / "turbulence_passport.json", passport)),
            "turbulence_fluent_setup_hints": str(_write_json(target_dir / "turbulence_fluent_setup_hints.json", hints)),
            "turbulence_report": str(_write_text(target_dir / "turbulence_report.md", _turbulence_markdown(passport, hints))),
        }
        status = "success" if passport["status"] != "failed" else "failed"
        if status == "success":
            result = AgentResult.success(
                backend="fastcfd",
                operation="validate_turbulence_passport",
                message="Turbulence passport completed.",
                outputs={
                    "artifacts": artifacts,
                    "passport": passport,
                    "fluent_hints": hints,
                    "solver_execution": "not_attempted_turbulence_passport_only",
                },
                metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
            )
        else:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="validate_turbulence_passport",
                message="Turbulence passport failed and blocked downstream setup hints.",
                errors=passport["blocking_errors"],
                metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
            )
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "passport": passport,
                    "fluent_hints": hints,
                    "solver_execution": "blocked_by_turbulence_passport",
                }
            )
        artifacts["turbulence_status"] = str(_write_json(target_dir / "turbulence_status.json", result.to_dict()))
        return result.to_dict()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        failure = AgentResult.failed(
            backend="fastcfd",
            operation="validate_turbulence_passport",
            message="Turbulence passport failed before validation completion.",
            errors=[str(exc)],
            metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"turbulence_status": str(target_dir / "turbulence_status.json")}
        _write_json(target_dir / "turbulence_status.json", failure.to_dict())
        return failure.to_dict()


def build_turbulence_passport(case: TurbulenceCase) -> dict[str, Any]:
    case.validate_schema()
    errors: list[str] = []
    warnings: list[str] = []
    remediation: list[str] = []

    density = _positive(case.fluid.get("density_kg_m3"), "fluid.density_kg_m3", errors)
    viscosity = _positive(case.fluid.get("dynamic_viscosity_pa_s"), "fluid.dynamic_viscosity_pa_s", errors)
    velocity = _positive(case.reference_velocity_m_s, "reference_velocity_m_s", errors)
    length_scale_m = _positive(case.domain.get("length_scale_mm"), "domain.length_scale_mm", errors) / 1000.0
    hydraulic_diameter_m = _positive(case.domain.get("hydraulic_diameter_mm", case.domain.get("length_scale_mm")), "domain.hydraulic_diameter_mm", errors) / 1000.0
    first_cell_height_m = (
        None if case.first_cell_height_mm is None else _positive(case.first_cell_height_mm, "first_cell_height_mm", errors) / 1000.0
    )
    turbulence_intensity = case.turbulence_intensity_percent
    if turbulence_intensity is not None and not (0.0 < turbulence_intensity <= 30.0):
        errors.append("turbulence_intensity_percent must be in the interval (0, 30].")
    reynolds = density * velocity * hydraulic_diameter_m / viscosity
    estimated_friction_factor = _estimate_friction_factor(reynolds)
    friction_velocity = velocity * math.sqrt(estimated_friction_factor / 8.0)
    estimated_y_plus = density * friction_velocity * first_cell_height_m / viscosity if first_cell_height_m is not None else None
    target_y_min = float(case.domain.get("target_y_plus_min", 0.5 if case.model_intent == "rans_sst" else 30.0))
    target_y_max = float(case.domain.get("target_y_plus_max", 2.0 if case.model_intent == "rans_sst" else 300.0))
    regime = _flow_regime(reynolds)
    recommended_model = _recommended_model(reynolds)
    turbulent_kinetic_energy = None
    turbulence_length_scale_m = 0.07 * hydraulic_diameter_m
    dissipation_rate = None
    specific_dissipation_rate = None
    if turbulence_intensity is not None:
        intensity = turbulence_intensity / 100.0
        turbulent_kinetic_energy = 1.5 * (velocity * intensity) ** 2
        if turbulence_length_scale_m > 0 and turbulent_kinetic_energy > 0:
            c_mu = 0.09
            dissipation_rate = (c_mu**0.75) * (turbulent_kinetic_energy**1.5) / turbulence_length_scale_m
            specific_dissipation_rate = math.sqrt(turbulent_kinetic_energy) / ((c_mu**0.25) * turbulence_length_scale_m)
    if reynolds < 2300 and case.model_intent != "laminar":
        warnings.append(f"Reynolds number is laminar-range ({reynolds:.6g}); RANS may be unnecessary for the first Fluent setup.")
    if reynolds >= 4000 and case.model_intent == "laminar":
        warnings.append(f"Reynolds number is turbulent-range ({reynolds:.6g}); laminar setup is likely insufficient.")
        remediation.append("Use a RANS turbulence passport before high-fidelity Fluent setup.")
    if case.model_intent == "rans_sst" and first_cell_height_m is None:
        warnings.append("First-cell height is missing; y-plus cannot be checked for SST near-wall setup.")
        remediation.append("Provide first_cell_height_mm or compute it from the CAD/mesh plan.")
    if estimated_y_plus is not None:
        if estimated_y_plus < target_y_min:
            warnings.append(f"Estimated y-plus is below target: {estimated_y_plus:.6g} < {target_y_min:.6g}.")
        if estimated_y_plus > target_y_max:
            warnings.append(f"Estimated y-plus is above target: {estimated_y_plus:.6g} > {target_y_max:.6g}.")
            remediation.append("Reduce first_cell_height_mm or choose a wall-function strategy with a compatible y-plus target.")
        if estimated_y_plus > 500.0:
            errors.append(f"Estimated y-plus is outside the accepted screening range: {estimated_y_plus:.6g}.")
    if not errors and case.model_intent.startswith("rans") and turbulence_intensity is None:
        warnings.append("Turbulence intensity is missing; Fluent inlet turbulence initialization cannot be fully specified.")
        remediation.append("Provide turbulence_intensity_percent or measured inlet turbulence data.")
    status = "failed" if errors else ("warning" if warnings else "passed")
    return {
        "schema_version": TURBULENCE_PASSPORT_SCHEMA_VERSION,
        "status": status,
        "case_name": case.case_name,
        "model_intent": case.model_intent,
        "recommended_model_family": recommended_model,
        "flow_regime": regime,
        "checks": {
            "density_kg_m3": density,
            "dynamic_viscosity_pa_s": viscosity,
            "reference_velocity_m_s": velocity,
            "length_scale_m": length_scale_m,
            "hydraulic_diameter_m": hydraulic_diameter_m,
            "reynolds_number": reynolds,
            "estimated_friction_factor": estimated_friction_factor,
            "estimated_friction_velocity_m_s": friction_velocity,
            "first_cell_height_m": first_cell_height_m,
            "estimated_y_plus": estimated_y_plus,
            "target_y_plus_min": target_y_min,
            "target_y_plus_max": target_y_max,
            "turbulence_intensity_percent": turbulence_intensity,
            "turbulent_kinetic_energy_m2_s2": turbulent_kinetic_energy,
            "turbulence_length_scale_m": turbulence_length_scale_m,
            "dissipation_rate_m2_s3": dissipation_rate,
            "specific_dissipation_rate_1_s": specific_dissipation_rate,
        },
        "warnings": warnings,
        "blocking_errors": errors,
        "remediation_suggestions": remediation,
        "limitations": [
            "This is a turbulence setup passport and not a turbulence solver.",
            "The y-plus estimate is a first-order engineering screening value.",
            "FastFluent does not replace Fluent turbulence validation.",
        ],
    }


def build_turbulence_fluent_setup_hints(case: TurbulenceCase, passport: dict[str, Any]) -> dict[str, Any]:
    checks = passport.get("checks", {})
    failed = passport.get("status") == "failed"
    model = "SST k-omega" if case.model_intent == "rans_sst" else "realizable k-epsilon" if "epsilon" in case.model_intent else "laminar"
    hints = [
        {
            "category": "viscous_model",
            "recommendation": f"Use Fluent {model} for the first setup." if model != "laminar" else "Use laminar only if the Reynolds regime remains laminar.",
            "evidence": [f"Re={checks.get('reynolds_number')}", f"model_intent={case.model_intent}", f"regime={passport.get('flow_regime')}"],
            "blocked": failed,
        },
        {
            "category": "near_wall_resolution",
            "recommendation": "Check first-layer height against the target y-plus before meshing in Fluent.",
            "evidence": [
                f"estimated_y_plus={checks.get('estimated_y_plus')}",
                f"target_y_plus=[{checks.get('target_y_plus_min')}, {checks.get('target_y_plus_max')}]",
            ],
            "blocked": failed,
        },
        {
            "category": "inlet_turbulence_initialization",
            "recommendation": "Initialize inlet turbulence from intensity and hydraulic diameter/length scale.",
            "evidence": [
                f"turbulence_intensity_percent={checks.get('turbulence_intensity_percent')}",
                f"turbulent_kinetic_energy={checks.get('turbulent_kinetic_energy_m2_s2')}",
                f"turbulence_length_scale_m={checks.get('turbulence_length_scale_m')}",
            ],
            "blocked": failed,
        },
    ]
    return {
        "schema_version": TURBULENCE_HINTS_SCHEMA_VERSION,
        "status": "blocked" if failed else "ready_with_warnings" if passport.get("status") == "warning" else "ready",
        "case_name": case.case_name,
        "hints": hints,
        "blocking_errors": list(passport.get("blocking_errors", [])),
        "warnings": list(passport.get("warnings", [])),
        "limitations": ["Hints are Fluent setup guidance and are not turbulence solver results."],
    }


def _estimate_friction_factor(reynolds: float) -> float:
    if reynolds <= 0:
        return 0.02
    if reynolds < 2300:
        return 64.0 / reynolds
    return 0.3164 / (reynolds**0.25)


def _flow_regime(reynolds: float) -> str:
    if reynolds < 2300:
        return "laminar"
    if reynolds < 4000:
        return "transitional"
    return "turbulent"


def _recommended_model(reynolds: float) -> str:
    if reynolds < 2300:
        return "laminar"
    if reynolds < 4000:
        return "transitional_review"
    return "rans_sst_or_realizable_k_epsilon"


def _positive(value: Any, name: str, errors: list[str]) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"Turbulence value must be numeric: {name}.")
        return 1.0
    if number <= 0:
        errors.append(f"Turbulence value must be positive: {name}.")
        return 1.0
    return number


def _assert_no_dangerous_keys(value: Any, *, path: str = "$") -> None:
    dangerous = {"argv", "command", "command_line", "cpp_code", "delete", "executable", "python", "shell", "source_code"}
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in dangerous:
                raise ValueError(f"Dangerous turbulence schema key is not allowed at {path}.{key}: {key}")
            _assert_no_dangerous_keys(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_dangerous_keys(item, path=f"{path}[{index}]")


def _turbulence_markdown(passport: dict[str, Any], hints: dict[str, Any]) -> str:
    checks = passport["checks"]
    lines = [
        "# FastFluent Turbulence Passport",
        "",
        f"Status: `{passport['status']}`",
        f"Flow regime: `{passport['flow_regime']}`",
        f"Recommended model family: `{passport['recommended_model_family']}`",
        "",
        "## Checks",
        "",
        f"- Reynolds number: `{checks['reynolds_number']}`",
        f"- Estimated y-plus: `{checks['estimated_y_plus']}`",
        f"- Turbulence intensity percent: `{checks['turbulence_intensity_percent']}`",
        "",
        "## Fluent Hints",
        "",
    ]
    lines.extend(f"- `{hint['category']}`: {hint['recommendation']}" for hint in hints["hints"])
    if passport["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in passport["warnings"])
    if passport["blocking_errors"]:
        lines.extend(["", "## Blocking Errors", ""])
        lines.extend(f"- {error}" for error in passport["blocking_errors"])
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
