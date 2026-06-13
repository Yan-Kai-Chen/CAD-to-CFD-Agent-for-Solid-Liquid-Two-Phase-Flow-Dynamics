"""Non-Newtonian rheology passport and shear-rate benchmark."""

from __future__ import annotations

from dataclasses import dataclass, field
import csv
import json
import math
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .paths import unique_path


RHEOLOGY_CASE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_rheology_case_v1"
RHEOLOGY_PASSPORT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_rheology_passport_v1"
RHEOLOGY_HINTS_SCHEMA_VERSION = "fromcad2cfd_fastfluent_rheology_fluent_hints_v1"

SUPPORTED_RHEOLOGY_MODELS = {"newtonian", "power_law", "carreau_yasuda"}


@dataclass(frozen=True)
class RheologyCase:
    case_name: str
    model: str
    parameters: dict[str, Any]
    shear_rate_range_1_s: tuple[float, float]
    sample_count: int = 9
    density_kg_m3: float | None = None
    temperature_k: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = RHEOLOGY_CASE_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RheologyCase":
        rate_range = payload["shear_rate_range_1_s"]
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            case_name=str(payload["case_name"]),
            model=str(payload["model"]),
            parameters=dict(payload.get("parameters") or {}),
            shear_rate_range_1_s=(float(rate_range[0]), float(rate_range[1])),
            sample_count=int(payload.get("sample_count", 9)),
            density_kg_m3=None if payload.get("density_kg_m3") is None else float(payload["density_kg_m3"]),
            temperature_k=None if payload.get("temperature_k") is None else float(payload["temperature_k"]),
            metadata=dict(payload.get("metadata") or {}),
        )

    def validate_schema(self) -> None:
        if self.schema_version != RHEOLOGY_CASE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported rheology case schema: {self.schema_version}")
        if self.model not in SUPPORTED_RHEOLOGY_MODELS:
            raise ValueError(f"Unsupported rheology model: {self.model}")
        if not self.case_name or any(ch in self.case_name for ch in "\\/:*?\"<>|"):
            raise ValueError("Rheology case_name must be non-empty and filesystem-safe.")
        min_rate, max_rate = self.shear_rate_range_1_s
        if min_rate <= 0 or max_rate <= 0 or max_rate <= min_rate:
            raise ValueError("shear_rate_range_1_s must be positive and increasing.")
        if self.sample_count < 3:
            raise ValueError("Rheology sample_count must be at least 3.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_name": self.case_name,
            "model": self.model,
            "parameters": self.parameters,
            "shear_rate_range_1_s": list(self.shear_rate_range_1_s),
            "sample_count": self.sample_count,
            "density_kg_m3": self.density_kg_m3,
            "temperature_k": self.temperature_k,
            "metadata": self.metadata,
        }


def demo_rheology_case(*, case_name: str = "public_power_law_shear_thinning_passport") -> RheologyCase:
    return RheologyCase(
        case_name=case_name,
        model="power_law",
        parameters={"consistency_pa_s_n": 0.35, "flow_behavior_index": 0.65, "min_viscosity_pa_s": 0.01, "max_viscosity_pa_s": 10.0},
        shear_rate_range_1_s=(0.1, 1000.0),
        sample_count=13,
        density_kg_m3=1030.0,
        temperature_k=298.15,
        metadata={"public_safe": True, "purpose": "non-Newtonian shear-rate benchmark smoke case"},
    )


def write_demo_rheology_case(
    *,
    output_dir: str | Path | None = None,
    case_name: str = "public_power_law_shear_thinning_passport",
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / case_name / "input")
    target_dir.mkdir(parents=True, exist_ok=True)
    case = demo_rheology_case(case_name=case_name)
    case_path = target_dir / "rheology_case.json"
    _write_json(case_path, case.to_dict())
    return {"case_file": str(case_path), "case": case.to_dict()}


def read_rheology_case(path: str | Path) -> RheologyCase:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    _assert_no_dangerous_keys(payload)
    case = RheologyCase.from_dict(payload)
    case.validate_schema()
    return case


def run_rheology_benchmark_file(
    case_file: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    case_path = Path(case_file)
    target_dir = Path(output_dir) if output_dir else unique_path(case_path.parent / f"{case_path.stem}_rheology_benchmark")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        case = read_rheology_case(case_path)
        passport = build_rheology_passport(case)
        hints = build_rheology_fluent_setup_hints(case, passport)
        artifacts = {
            "rheology_case_copy": str(_write_json(target_dir / "rheology_case.json", case.to_dict())),
            "rheology_passport": str(_write_json(target_dir / "rheology_passport.json", passport)),
            "rheology_curve_csv": str(_write_curve_csv(target_dir / "rheology_curve.csv", passport["samples"])),
            "rheology_fluent_setup_hints": str(_write_json(target_dir / "rheology_fluent_setup_hints.json", hints)),
            "rheology_report": str(_write_text(target_dir / "rheology_report.md", _rheology_markdown(passport, hints))),
        }
        status = "success" if passport["status"] != "failed" else "failed"
        if status == "success":
            result = AgentResult.success(
                backend="fastcfd",
                operation="run_rheology_benchmark",
                message="Rheology passport and shear-rate benchmark completed.",
                outputs={
                    "artifacts": artifacts,
                    "passport": passport,
                    "fluent_hints": hints,
                    "solver_execution": "not_attempted_rheology_passport_only",
                },
                metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
            )
        else:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="run_rheology_benchmark",
                message="Rheology benchmark failed and blocked downstream setup hints.",
                errors=passport["blocking_errors"],
                metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
            )
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "passport": passport,
                    "fluent_hints": hints,
                    "solver_execution": "blocked_by_rheology_passport",
                }
            )
        artifacts["rheology_status"] = str(_write_json(target_dir / "rheology_status.json", result.to_dict()))
        return result.to_dict()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        failure = AgentResult.failed(
            backend="fastcfd",
            operation="run_rheology_benchmark",
            message="Rheology benchmark failed before validation completion.",
            errors=[str(exc)],
            metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"rheology_status": str(target_dir / "rheology_status.json")}
        _write_json(target_dir / "rheology_status.json", failure.to_dict())
        return failure.to_dict()


def build_rheology_passport(case: RheologyCase) -> dict[str, Any]:
    case.validate_schema()
    errors: list[str] = []
    warnings: list[str] = []
    remediation: list[str] = []
    _validate_model_parameters(case, errors)
    rates = _logspace(case.shear_rate_range_1_s[0], case.shear_rate_range_1_s[1], case.sample_count)
    samples = []
    for rate in rates:
        viscosity = _apparent_viscosity(case, rate)
        stress = viscosity * rate
        samples.append({"shear_rate_1_s": rate, "apparent_viscosity_pa_s": viscosity, "shear_stress_pa": stress})
        if not math.isfinite(viscosity) or viscosity <= 0:
            errors.append(f"Non-positive or non-finite apparent viscosity at shear_rate={rate}.")
        if not math.isfinite(stress) or stress < 0:
            errors.append(f"Invalid shear stress at shear_rate={rate}.")
    viscosities = [sample["apparent_viscosity_pa_s"] for sample in samples]
    min_viscosity = min(viscosities)
    max_viscosity = max(viscosities)
    viscosity_ratio = max_viscosity / min_viscosity if min_viscosity > 0 else math.inf
    trend = _trend(viscosities)
    if viscosity_ratio > 1.0e5:
        warnings.append(f"Viscosity ratio across the benchmark is very large: {viscosity_ratio:.6g}.")
        remediation.append("Consider viscosity bounds or a narrower validated shear-rate range for Fluent stability.")
    expected = _expected_trend(case)
    if expected != "constant" and trend != expected:
        warnings.append(f"Apparent viscosity trend `{trend}` does not match expected `{expected}` for the selected model.")
    if case.model == "power_law":
        n = float(case.parameters["flow_behavior_index"])
        if n <= 0 or n > 2.0:
            errors.append("Power-law flow_behavior_index must be in the interval (0, 2].")
    status = "failed" if errors else ("warning" if warnings else "passed")
    return {
        "schema_version": RHEOLOGY_PASSPORT_SCHEMA_VERSION,
        "status": status,
        "case_name": case.case_name,
        "model": case.model,
        "parameters": dict(case.parameters),
        "density_kg_m3": case.density_kg_m3,
        "temperature_k": case.temperature_k,
        "shear_rate_range_1_s": list(case.shear_rate_range_1_s),
        "sample_count": len(samples),
        "samples": samples,
        "checks": {
            "min_apparent_viscosity_pa_s": min_viscosity,
            "max_apparent_viscosity_pa_s": max_viscosity,
            "viscosity_ratio": viscosity_ratio,
            "trend": trend,
            "expected_trend": expected,
            "finite_positive_viscosity": not errors,
        },
        "warnings": warnings,
        "blocking_errors": errors,
        "remediation_suggestions": remediation,
        "limitations": [
            "This is a rheology passport and shear-rate benchmark, not a non-Newtonian CFD solver.",
            "The benchmark checks material-model behavior before Fluent setup.",
            "Temperature dependence is recorded only as metadata unless the model parameters encode it.",
        ],
    }


def build_rheology_fluent_setup_hints(case: RheologyCase, passport: dict[str, Any]) -> dict[str, Any]:
    checks = passport["checks"]
    failed = passport["status"] == "failed"
    material_model = {
        "newtonian": "constant viscosity",
        "power_law": "non-Newtonian power-law viscosity",
        "carreau_yasuda": "Carreau-Yasuda non-Newtonian viscosity",
    }[case.model]
    hints = [
        {
            "category": "material_viscosity_model",
            "recommendation": f"Use Fluent {material_model} with the passport parameters as the first material setup.",
            "evidence": [f"model={case.model}", f"trend={checks['trend']}", f"viscosity_ratio={checks['viscosity_ratio']}"],
            "blocked": failed,
        },
        {
            "category": "shear_rate_range",
            "recommendation": "Verify expected shear-rate range in Fluent monitors before trusting a production run.",
            "evidence": [f"range={passport['shear_rate_range_1_s']}", f"sample_count={passport['sample_count']}"],
            "blocked": failed,
        },
        {
            "category": "numerical_stability",
            "recommendation": "Use conservative initialization and bounded viscosity values when the viscosity ratio is high.",
            "evidence": [
                f"min_mu={checks['min_apparent_viscosity_pa_s']}",
                f"max_mu={checks['max_apparent_viscosity_pa_s']}",
            ],
            "blocked": failed,
        },
    ]
    return {
        "schema_version": RHEOLOGY_HINTS_SCHEMA_VERSION,
        "status": "blocked" if failed else "ready_with_warnings" if passport["status"] == "warning" else "ready",
        "case_name": case.case_name,
        "hints": hints,
        "blocking_errors": list(passport["blocking_errors"]),
        "warnings": list(passport["warnings"]),
        "limitations": ["Hints are material setup guidance and are not non-Newtonian CFD results."],
    }


def _validate_model_parameters(case: RheologyCase, errors: list[str]) -> None:
    params = case.parameters
    if case.model == "newtonian":
        _positive_param(params, "dynamic_viscosity_pa_s", errors)
    elif case.model == "power_law":
        _positive_param(params, "consistency_pa_s_n", errors)
        _positive_param(params, "flow_behavior_index", errors)
        if "min_viscosity_pa_s" in params:
            _positive_param(params, "min_viscosity_pa_s", errors)
        if "max_viscosity_pa_s" in params:
            _positive_param(params, "max_viscosity_pa_s", errors)
        if params.get("min_viscosity_pa_s") and params.get("max_viscosity_pa_s"):
            if float(params["max_viscosity_pa_s"]) <= float(params["min_viscosity_pa_s"]):
                errors.append("max_viscosity_pa_s must be greater than min_viscosity_pa_s.")
    elif case.model == "carreau_yasuda":
        for key in ["zero_shear_viscosity_pa_s", "infinite_shear_viscosity_pa_s", "time_constant_s", "power_index", "transition_index"]:
            _positive_param(params, key, errors)


def _positive_param(params: dict[str, Any], key: str, errors: list[str]) -> float:
    try:
        value = float(params[key])
    except KeyError:
        errors.append(f"Missing rheology parameter: {key}.")
        return 1.0
    except (TypeError, ValueError):
        errors.append(f"Rheology parameter must be numeric: {key}.")
        return 1.0
    if value <= 0:
        errors.append(f"Rheology parameter must be positive: {key}.")
        return 1.0
    return value


def _apparent_viscosity(case: RheologyCase, shear_rate: float) -> float:
    params = case.parameters
    if case.model == "newtonian":
        return float(params["dynamic_viscosity_pa_s"])
    if case.model == "power_law":
        consistency = float(params["consistency_pa_s_n"])
        n = float(params["flow_behavior_index"])
        viscosity = consistency * shear_rate ** (n - 1.0)
        if "min_viscosity_pa_s" in params:
            viscosity = max(float(params["min_viscosity_pa_s"]), viscosity)
        if "max_viscosity_pa_s" in params:
            viscosity = min(float(params["max_viscosity_pa_s"]), viscosity)
        return viscosity
    if case.model == "carreau_yasuda":
        mu0 = float(params["zero_shear_viscosity_pa_s"])
        mu_inf = float(params["infinite_shear_viscosity_pa_s"])
        time_constant = float(params["time_constant_s"])
        n = float(params["power_index"])
        a = float(params["transition_index"])
        return mu_inf + (mu0 - mu_inf) * (1.0 + (time_constant * shear_rate) ** a) ** ((n - 1.0) / a)
    raise ValueError(f"Unsupported rheology model: {case.model}")


def _expected_trend(case: RheologyCase) -> str:
    if case.model == "newtonian":
        return "constant"
    if case.model == "power_law":
        n = float(case.parameters["flow_behavior_index"])
        if n < 1.0:
            return "shear_thinning"
        if n > 1.0:
            return "shear_thickening"
        return "constant"
    if case.model == "carreau_yasuda":
        return "shear_thinning" if float(case.parameters["power_index"]) < 1.0 else "constant_or_thickening"
    return "unknown"


def _trend(values: list[float]) -> str:
    tolerance = 1.0e-12
    decreases = all(values[index + 1] <= values[index] + tolerance for index in range(len(values) - 1))
    increases = all(values[index + 1] + tolerance >= values[index] for index in range(len(values) - 1))
    if decreases and not increases:
        return "shear_thinning"
    if increases and not decreases:
        return "shear_thickening"
    if max(values) - min(values) <= tolerance * max(1.0, max(values)):
        return "constant"
    return "non_monotone"


def _logspace(min_value: float, max_value: float, count: int) -> list[float]:
    log_min = math.log10(min_value)
    log_max = math.log10(max_value)
    if count == 1:
        return [min_value]
    return [10 ** (log_min + (log_max - log_min) * index / (count - 1)) for index in range(count)]


def _write_curve_csv(path: Path, samples: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["shear_rate_1_s", "apparent_viscosity_pa_s", "shear_stress_pa"])
        writer.writeheader()
        writer.writerows(samples)
    return path


def _assert_no_dangerous_keys(value: Any, *, path: str = "$") -> None:
    dangerous = {"argv", "command", "command_line", "cpp_code", "delete", "executable", "python", "shell", "source_code"}
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in dangerous:
                raise ValueError(f"Dangerous rheology schema key is not allowed at {path}.{key}: {key}")
            _assert_no_dangerous_keys(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_dangerous_keys(item, path=f"{path}[{index}]")


def _rheology_markdown(passport: dict[str, Any], hints: dict[str, Any]) -> str:
    checks = passport["checks"]
    lines = [
        "# FastFluent Rheology Passport",
        "",
        f"Status: `{passport['status']}`",
        f"Model: `{passport['model']}`",
        f"Trend: `{checks['trend']}`",
        "",
        "## Checks",
        "",
        f"- Min apparent viscosity: `{checks['min_apparent_viscosity_pa_s']}`",
        f"- Max apparent viscosity: `{checks['max_apparent_viscosity_pa_s']}`",
        f"- Viscosity ratio: `{checks['viscosity_ratio']}`",
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
