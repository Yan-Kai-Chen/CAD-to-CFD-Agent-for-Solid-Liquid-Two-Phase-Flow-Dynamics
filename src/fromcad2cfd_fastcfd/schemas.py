"""Serializable FastCFD contracts used by agent-facing tools."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .registry import CASE_REGISTRY, require_backend_for_case


FASTCFD_JOB_SCHEMA_VERSION = "fromcad2cfd_fastcfd_job_v1"
FASTCFD_SCENE_SCHEMA_VERSION = "fromcad2cfd_fastcfd_scene_v1"
FASTCFD_PHYSICS_CONTRACT_SCHEMA_VERSION = "fromcad2cfd_fastcfd_physics_contract_v1"

ALLOWED_CASE_TYPES = set(CASE_REGISTRY)
ALLOWED_BACKENDS = {"mock", "fastfluent"}
ALLOWED_LENGTH_UNITS = {"mm"}
ALLOWED_TIME_UNITS = {"s"}
ALLOWED_DENSITY_UNITS = {"g/mm^3"}
DANGEROUS_KEYS = {
    "argv",
    "command",
    "command_line",
    "cpp_code",
    "delete",
    "executable",
    "python",
    "shell",
    "source_code",
}


def _assert_no_dangerous_keys(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in DANGEROUS_KEYS:
                raise ValueError(f"Dangerous FastCFD schema key is not allowed at {path}.{key}: {key}")
            _assert_no_dangerous_keys(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_dangerous_keys(item, path=f"{path}[{index}]")


def _require_positive_number(mapping: dict[str, Any], key: str) -> float:
    try:
        value = float(mapping[key])
    except KeyError as exc:
        raise ValueError(f"Missing required FastCFD value: {key}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"FastCFD value must be numeric: {key}") from exc
    if value <= 0:
        raise ValueError(f"FastCFD value must be positive: {key}")
    return value


@dataclass(frozen=True)
class FastCFDJob:
    """Validated executable FastCFD job request."""

    case_type: str
    backend: str
    output_dir: str
    model_name: str
    dimensions: dict[str, Any] = field(default_factory=dict)
    physical_properties: dict[str, Any] = field(default_factory=dict)
    boundary_conditions: dict[str, Any] = field(default_factory=dict)
    solver_settings: dict[str, Any] = field(default_factory=dict)
    units: dict[str, str] = field(
        default_factory=lambda: {
            "length": "mm",
            "time": "s",
            "density": "g/mm^3",
            "kinematic_viscosity": "mm^2/s",
        }
    )
    schema_version: str = FASTCFD_JOB_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.schema_version != FASTCFD_JOB_SCHEMA_VERSION:
            raise ValueError(f"Unsupported FastCFD job schema: {self.schema_version}")
        if self.case_type not in ALLOWED_CASE_TYPES:
            raise ValueError(f"Unsupported FastCFD case_type: {self.case_type}")
        if self.backend not in ALLOWED_BACKENDS:
            raise ValueError(f"Unsupported FastCFD backend: {self.backend}")
        require_backend_for_case(self.case_type, self.backend)
        if self.units.get("length") not in ALLOWED_LENGTH_UNITS:
            raise ValueError("FastCFD length units must be explicit and currently only support mm.")
        if self.units.get("time") not in ALLOWED_TIME_UNITS:
            raise ValueError("FastCFD time units must be explicit and currently only support s.")
        if self.units.get("density") not in ALLOWED_DENSITY_UNITS:
            raise ValueError("FastCFD density units must be explicit and currently only support g/mm^3.")
        if not self.model_name or any(ch in self.model_name for ch in "\\/:*?\"<>|"):
            raise ValueError("FastCFD model_name must be a non-empty filesystem-safe name.")
        _assert_no_dangerous_keys(self.to_dict())
        self._validate_case()

    def _validate_case(self) -> None:
        _require_positive_number(self.dimensions, "cell_length_mm")
        _require_positive_number(self.physical_properties, "rho_ref_g_per_mm3")
        _require_positive_number(self.physical_properties, "kinematic_viscosity_mm2_s")
        total_steps = int(_require_positive_number(self.solver_settings, "total_steps"))
        output_interval = int(_require_positive_number(self.solver_settings, "output_interval"))
        if output_interval > total_steps:
            raise ValueError("FastCFD output_interval must not exceed total_steps.")
        if self.case_type in {"cavity2d", "channel2d", "obstacle2d", "dambreak2d"}:
            _require_positive_number(self.dimensions, "nx")
            _require_positive_number(self.dimensions, "ny")
        if self.case_type == "cavity2d":
            if "moving_wall_velocity_mm_s" not in self.boundary_conditions:
                raise ValueError("cavity2d requires moving_wall_velocity_mm_s.")
        if self.case_type in {"channel2d", "obstacle2d"}:
            if "inlet_velocity_mm_s" not in self.boundary_conditions:
                raise ValueError(f"{self.case_type} requires inlet_velocity_mm_s.")
            if "outlet" not in self.boundary_conditions:
                raise ValueError(f"{self.case_type} requires an outlet boundary declaration.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_type": self.case_type,
            "backend": self.backend,
            "output_dir": self.output_dir,
            "model_name": self.model_name,
            "units": self.units,
            "dimensions": self.dimensions,
            "physical_properties": self.physical_properties,
            "boundary_conditions": self.boundary_conditions,
            "solver_settings": self.solver_settings,
            "metadata": self.metadata,
        }

    def write(self, path: str | Path) -> Path:
        self.validate()
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
        return output


@dataclass(frozen=True)
class FastCFDScene:
    """Agent-native scene contract compiled into a FastCFDJob in later phases."""

    scene_type: str
    units: dict[str, str]
    geometry: dict[str, Any]
    zones: list[dict[str, Any]]
    physics_intent: dict[str, Any]
    schema_version: str = FASTCFD_SCENE_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.schema_version != FASTCFD_SCENE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported FastCFD scene schema: {self.schema_version}")
        if self.scene_type not in ALLOWED_CASE_TYPES:
            raise ValueError(f"Unsupported FastCFD scene_type: {self.scene_type}")
        if self.units.get("length") not in ALLOWED_LENGTH_UNITS:
            raise ValueError("FastCFD scene length units must be explicit and currently only support mm.")
        if not self.zones:
            raise ValueError("FastCFD scenes require at least one semantic zone.")
        _assert_no_dangerous_keys(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scene_type": self.scene_type,
            "units": self.units,
            "geometry": self.geometry,
            "zones": self.zones,
            "physics_intent": self.physics_intent,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class PhysicsContract:
    """Pre-run physics passport for an advisory FastCFD job."""

    status: str
    case_type: str
    checks: dict[str, Any]
    limitations: list[str]
    remediation_suggestions: list[str] = field(default_factory=list)
    thresholds: dict[str, Any] = field(default_factory=dict)
    validator_version: str = "fastcfd_physics_validator_v1"
    schema_version: str = FASTCFD_PHYSICS_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "validator_version": self.validator_version,
            "status": self.status,
            "case_type": self.case_type,
            "checks": self.checks,
            "thresholds": self.thresholds,
            "limitations": self.limitations,
            "remediation_suggestions": self.remediation_suggestions,
        }


@dataclass(frozen=True)
class ResultManifest:
    """Index of artifacts produced by a FastCFD run."""

    run_id: str
    status: str
    backend: str
    case_type: str
    job_path: str
    artifacts: dict[str, str]
    field_outputs: list[dict[str, Any]] = field(default_factory=list)
    parser_status: str = "not_attempted"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "backend": self.backend,
            "case_type": self.case_type,
            "job_path": self.job_path,
            "artifacts": self.artifacts,
            "field_outputs": self.field_outputs,
            "parser_status": self.parser_status,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class QoIManifest:
    """Quantities of interest and unavailable metric reasons."""

    run_id: str
    metrics: dict[str, Any]
    unavailable: dict[str, str] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "metrics": self.metrics,
            "unavailable": self.unavailable,
            "limitations": self.limitations,
        }


@dataclass(frozen=True)
class FlowFingerprint:
    """Agent-readable flow feature summary."""

    run_id: str
    metrics: dict[str, Any]
    unavailable: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "metrics": self.metrics, "unavailable": self.unavailable}


@dataclass(frozen=True)
class FluentHints:
    """Advisory Fluent setup hints backed by explicit evidence."""

    run_id: str
    hints: list[dict[str, Any]]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "hints": self.hints, "limitations": self.limitations}


@dataclass(frozen=True)
class ClaimLedger:
    """Evidence ledger preventing unsupported solver claims."""

    run_id: str
    claims: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "claims": self.claims}


def read_job(path: str | Path) -> FastCFDJob:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    _assert_no_dangerous_keys(payload)
    job = FastCFDJob(
        case_type=payload["case_type"],
        backend=payload["backend"],
        output_dir=payload["output_dir"],
        model_name=payload["model_name"],
        units=payload.get("units") or {},
        dimensions=payload.get("dimensions") or {},
        physical_properties=payload.get("physical_properties") or {},
        boundary_conditions=payload.get("boundary_conditions") or {},
        solver_settings=payload.get("solver_settings") or {},
        schema_version=payload.get("schema_version", ""),
        metadata=payload.get("metadata") or {},
    )
    job.validate()
    return job
