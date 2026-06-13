"""VOF physics passport and Fluent setup hints for FastFluent workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .paths import unique_path


VOF_CASE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_vof_case_v1"
VOF_PASSPORT_SCHEMA_VERSION = "fromcad2cfd_fastfluent_vof_physics_passport_v1"
VOF_HINTS_SCHEMA_VERSION = "fromcad2cfd_fastfluent_vof_fluent_hints_v1"

COURANT_RECOMMENDED_MAX = 0.25
COURANT_WARNING_MAX = 0.50
COURANT_ACCEPTED_MAX = 1.00
VOLUME_FRACTION_TOLERANCE = 1.0e-8


@dataclass(frozen=True)
class VOFPhase:
    name: str
    role: str
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    initial_volume_fraction: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VOFPhase":
        return cls(
            name=str(payload["name"]),
            role=str(payload.get("role", "phase")),
            density_kg_m3=float(payload["density_kg_m3"]),
            dynamic_viscosity_pa_s=float(payload["dynamic_viscosity_pa_s"]),
            initial_volume_fraction=float(payload["initial_volume_fraction"]),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "density_kg_m3": self.density_kg_m3,
            "dynamic_viscosity_pa_s": self.dynamic_viscosity_pa_s,
            "initial_volume_fraction": self.initial_volume_fraction,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class VOFCase:
    case_name: str
    domain: dict[str, Any]
    phases: list[VOFPhase]
    surface_tension_n_m: float
    gravity_m_s2: tuple[float, float, float]
    reference_velocity_m_s: float
    time_step_s: float
    interface: dict[str, Any] = field(default_factory=dict)
    model: str = "vof_two_phase"
    units: dict[str, str] = field(
        default_factory=lambda: {
            "length": "mm",
            "time": "s",
            "density": "kg/m^3",
            "dynamic_viscosity": "Pa*s",
            "surface_tension": "N/m",
            "gravity": "m/s^2",
        }
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = VOF_CASE_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VOFCase":
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            case_name=str(payload["case_name"]),
            model=str(payload.get("model", "vof_two_phase")),
            units=dict(payload.get("units") or {}),
            domain=dict(payload["domain"]),
            phases=[VOFPhase.from_dict(item) for item in payload.get("phases", [])],
            surface_tension_n_m=float(payload["surface_tension_n_m"]),
            gravity_m_s2=_vector3(payload["gravity_m_s2"]),
            reference_velocity_m_s=float(payload["reference_velocity_m_s"]),
            time_step_s=float(payload["time_step_s"]),
            interface=dict(payload.get("interface") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )

    def validate_schema(self) -> None:
        if self.schema_version != VOF_CASE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported VOF case schema: {self.schema_version}")
        if self.model != "vof_two_phase":
            raise ValueError(f"Unsupported VOF model: {self.model}")
        if not self.case_name or any(ch in self.case_name for ch in "\\/:*?\"<>|"):
            raise ValueError("VOF case_name must be non-empty and filesystem-safe.")
        if len(self.phases) < 2:
            raise ValueError("VOF requires at least two phases.")
        if len({phase.name for phase in self.phases}) != len(self.phases):
            raise ValueError("VOF phase names must be unique.")
        if self.units.get("length") != "mm":
            raise ValueError("VOF domain length unit must be mm for this agent contract.")
        if self.units.get("time") != "s":
            raise ValueError("VOF time unit must be s for this agent contract.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_name": self.case_name,
            "model": self.model,
            "units": self.units,
            "domain": self.domain,
            "phases": [phase.to_dict() for phase in self.phases],
            "surface_tension_n_m": self.surface_tension_n_m,
            "gravity_m_s2": list(self.gravity_m_s2),
            "reference_velocity_m_s": self.reference_velocity_m_s,
            "time_step_s": self.time_step_s,
            "interface": self.interface,
            "metadata": self.metadata,
        }


def read_vof_case(path: str | Path) -> VOFCase:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    _assert_no_dangerous_keys(payload)
    case = VOFCase.from_dict(payload)
    case.validate_schema()
    return case


def write_demo_vof_case(
    *,
    output_dir: str | Path | None = None,
    case_name: str = "public_dambreak2d_vof_passport",
) -> dict[str, Any]:
    """Write a public-safe VOF demo case file."""

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / case_name / "input")
    target_dir.mkdir(parents=True, exist_ok=True)
    case = demo_vof_case(case_name=case_name)
    case_path = target_dir / "vof_case.json"
    case_path.write_text(json.dumps(case.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
    return {"case_file": str(case_path), "case": case.to_dict()}


def demo_vof_case(*, case_name: str = "public_dambreak2d_vof_passport") -> VOFCase:
    return VOFCase(
        case_name=case_name,
        domain={"dimension": 2, "length_scale_mm": 100.0, "cell_length_mm": 1.0, "expected_interface_cells": 1.0},
        phases=[
            VOFPhase(
                name="water",
                role="primary_liquid",
                density_kg_m3=998.2,
                dynamic_viscosity_pa_s=1.003e-3,
                initial_volume_fraction=0.50,
            ),
            VOFPhase(
                name="air",
                role="secondary_gas",
                density_kg_m3=1.225,
                dynamic_viscosity_pa_s=1.81e-5,
                initial_volume_fraction=0.50,
            ),
        ],
        surface_tension_n_m=0.072,
        gravity_m_s2=(0.0, -9.81, 0.0),
        reference_velocity_m_s=0.50,
        time_step_s=5.0e-4,
        interface={"initialization": "dam_break_column", "capturing": "geometric_reconstruction", "interface_thickness_cells": 1.0},
        metadata={"public_safe": True, "purpose": "VOF physics passport smoke case"},
    )


def validate_vof_case_file(
    case_file: str | Path,
    *,
    output_dir: str | Path | None = None,
    format_reports: bool = True,
) -> dict[str, Any]:
    """Validate a VOF case and write agent-facing artifacts."""

    case_path = Path(case_file)
    target_dir = Path(output_dir) if output_dir else unique_path(case_path.parent / f"{case_path.stem}_vof_passport")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        case = read_vof_case(case_path)
        passport = build_vof_physics_passport(case)
        hints = build_vof_fluent_setup_hints(case, passport)
        artifacts = {
            "vof_case_copy": str(_write_json(target_dir / "vof_case.json", case.to_dict())),
            "vof_physics_passport": str(_write_json(target_dir / "vof_physics_passport.json", passport)),
            "vof_fluent_setup_hints": str(_write_json(target_dir / "vof_fluent_setup_hints.json", hints)),
        }
        if format_reports:
            artifacts["vof_report"] = str(_write_text(target_dir / "vof_report.md", _vof_markdown(passport, hints)))
        status = "success" if passport["status"] != "failed" else "failed"
        if status == "success":
            result = AgentResult.success(
                backend="fastcfd",
                operation="validate_vof_physics",
                message="VOF physics passport completed.",
                outputs={"artifacts": artifacts, "passport": passport, "fluent_hints": hints, "solver_execution": "not_attempted_physics_passport_only"},
                metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
            )
        else:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="validate_vof_physics",
                message="VOF physics passport failed and blocked downstream setup hints.",
                errors=passport["blocking_errors"],
                metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
            )
            result.outputs.update(
                {
                    "artifacts": artifacts,
                    "passport": passport,
                    "fluent_hints": hints,
                    "solver_execution": "blocked_by_vof_physics_passport",
                }
            )
        artifacts["vof_status"] = str(target_dir / "vof_status.json")
        _write_json(target_dir / "vof_status.json", result.to_dict())
        return result.to_dict()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        failure = AgentResult.failed(
            backend="fastcfd",
            operation="validate_vof_physics",
            message="VOF physics passport failed before validation completion.",
            errors=[str(exc)],
            metadata={"case_file": str(case_path), "output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"vof_status": str(target_dir / "vof_status.json")}
        _write_json(target_dir / "vof_status.json", failure.to_dict())
        return failure.to_dict()


def build_vof_physics_passport(case: VOFCase) -> dict[str, Any]:
    """Build a fail-closed VOF physics passport."""

    case.validate_schema()
    errors: list[str] = []
    warnings: list[str] = []
    remediation: list[str] = []

    length_scale_m = _positive(case.domain.get("length_scale_mm"), "domain.length_scale_mm", errors) / 1000.0
    cell_length_m = _positive(case.domain.get("cell_length_mm"), "domain.cell_length_mm", errors) / 1000.0
    reference_velocity = _positive(case.reference_velocity_m_s, "reference_velocity_m_s", errors)
    time_step = _positive(case.time_step_s, "time_step_s", errors)
    surface_tension = _nonnegative(case.surface_tension_n_m, "surface_tension_n_m", errors)
    gravity_magnitude = math.sqrt(sum(component * component for component in case.gravity_m_s2))
    interface_cells = _positive(case.interface.get("interface_thickness_cells", case.domain.get("expected_interface_cells", 1.0)), "interface_thickness_cells", errors)

    phase_errors = _validate_phases(case.phases)
    errors.extend(phase_errors)
    volume_fraction_sum = sum(phase.initial_volume_fraction for phase in case.phases)
    if abs(volume_fraction_sum - 1.0) > VOLUME_FRACTION_TOLERANCE:
        errors.append(f"Initial VOF volume fractions must sum to 1.0; got {volume_fraction_sum}.")
        remediation.append("Normalize initial_volume_fraction values before enabling VOF setup.")
    if surface_tension == 0:
        warnings.append("Surface tension is zero; this is allowed only when the interface model intentionally neglects capillary effects.")
    if gravity_magnitude == 0:
        warnings.append("Gravity magnitude is zero; confirm this is intentional for the VOF case.")

    primary = _primary_phase(case.phases)
    secondary = _secondary_phase(case.phases, primary)
    rho_ref = primary.density_kg_m3
    mu_ref = primary.dynamic_viscosity_pa_s
    reynolds = rho_ref * reference_velocity * length_scale_m / mu_ref
    courant = reference_velocity * time_step / cell_length_m
    weber = rho_ref * reference_velocity * reference_velocity * length_scale_m / surface_tension if surface_tension > 0 else None
    bond = abs(primary.density_kg_m3 - secondary.density_kg_m3) * gravity_magnitude * length_scale_m * length_scale_m / surface_tension if surface_tension > 0 else None
    capillary = mu_ref * reference_velocity / surface_tension if surface_tension > 0 else None
    froude = reference_velocity / math.sqrt(gravity_magnitude * length_scale_m) if gravity_magnitude > 0 else None
    density_ratio = max(phase.density_kg_m3 for phase in case.phases) / min(phase.density_kg_m3 for phase in case.phases)
    viscosity_ratio = max(phase.dynamic_viscosity_pa_s for phase in case.phases) / min(phase.dynamic_viscosity_pa_s for phase in case.phases)
    courant_time_step_recommended = COURANT_RECOMMENDED_MAX * cell_length_m / reference_velocity
    capillary_time_step = (
        math.sqrt((primary.density_kg_m3 + secondary.density_kg_m3) * cell_length_m**3 / (4.0 * math.pi * surface_tension))
        if surface_tension > 0
        else None
    )

    if courant > COURANT_ACCEPTED_MAX:
        errors.append(f"VOF Courant number exceeds accepted limit: {courant}.")
        remediation.append(f"Reduce time_step_s to <= {courant_time_step_recommended:.6g} for the recommended Courant target.")
    elif courant > COURANT_WARNING_MAX:
        warnings.append(f"VOF Courant number exceeds warning limit: {courant}.")
        remediation.append(f"Prefer time_step_s <= {courant_time_step_recommended:.6g}.")
    elif courant > COURANT_RECOMMENDED_MAX:
        warnings.append(f"VOF Courant number exceeds recommended target: {courant}.")
    if interface_cells < 1.0:
        warnings.append("Interface thickness is below one cell; interface capturing may be under-resolved.")
    if density_ratio > 1000.0:
        warnings.append(f"Density ratio is very high: {density_ratio}. Use conservative transient settings and tight interface monitoring.")
    if viscosity_ratio > 100.0:
        warnings.append(f"Viscosity ratio is high: {viscosity_ratio}. Check phase-specific near-interface resolution.")
    if capillary_time_step is not None and time_step > capillary_time_step:
        warnings.append(f"Time step is above the capillary advisory limit: {time_step} > {capillary_time_step}.")
        remediation.append(f"Consider time_step_s <= {min(courant_time_step_recommended, capillary_time_step):.6g}.")

    status = "failed" if errors else ("warning" if warnings else "passed")
    return {
        "schema_version": VOF_PASSPORT_SCHEMA_VERSION,
        "status": status,
        "case_name": case.case_name,
        "model": case.model,
        "phase_count": len(case.phases),
        "phases": [phase.to_dict() for phase in case.phases],
        "primary_phase": primary.name,
        "secondary_reference_phase": secondary.name,
        "checks": {
            "length_scale_m": length_scale_m,
            "cell_length_m": cell_length_m,
            "reference_velocity_m_s": reference_velocity,
            "time_step_s": time_step,
            "surface_tension_n_m": surface_tension,
            "gravity_magnitude_m_s2": gravity_magnitude,
            "initial_volume_fraction_sum": volume_fraction_sum,
            "interface_thickness_cells": interface_cells,
            "courant_number": courant,
            "reynolds_number": reynolds,
            "weber_number": weber,
            "bond_number": bond,
            "capillary_number": capillary,
            "froude_number": froude,
            "density_ratio": density_ratio,
            "viscosity_ratio": viscosity_ratio,
            "recommended_time_step_s_by_courant": courant_time_step_recommended,
            "capillary_time_step_s_advisory": capillary_time_step,
        },
        "thresholds": {
            "courant_recommended_max": COURANT_RECOMMENDED_MAX,
            "courant_warning_max": COURANT_WARNING_MAX,
            "courant_accepted_max": COURANT_ACCEPTED_MAX,
            "volume_fraction_tolerance": VOLUME_FRACTION_TOLERANCE,
        },
        "warnings": warnings,
        "blocking_errors": errors,
        "remediation_suggestions": remediation,
        "limitations": [
            "This is a VOF physics passport and setup-hint gate, not a VOF solver.",
            "The passport prepares agent-safe Fluent setup decisions and does not replace Fluent validation.",
            "No turbulence model is selected here; turbulence is intentionally deferred to a later gate.",
        ],
    }


def build_vof_fluent_setup_hints(case: VOFCase, passport: dict[str, Any]) -> dict[str, Any]:
    """Translate the VOF passport into Fluent-facing setup hints."""

    checks = passport.get("checks", {})
    failed = passport.get("status") == "failed"
    recommended_dt = checks.get("recommended_time_step_s_by_courant")
    capillary_dt = checks.get("capillary_time_step_s_advisory")
    if recommended_dt is not None and capillary_dt is not None:
        recommended_dt = min(recommended_dt, capillary_dt)
    hints = [
        {
            "category": "multiphase_model",
            "recommendation": "Use Fluent VOF for immiscible two-phase interface tracking.",
            "evidence": ["model=vof_two_phase", f"phase_count={passport.get('phase_count')}"],
            "blocked": failed,
        },
        {
            "category": "solver_time_formulation",
            "recommendation": "Use transient pressure-based setup for VOF interface evolution.",
            "evidence": ["VOF interface capturing requires time-accurate transport in this passport route."],
            "blocked": failed,
        },
        {
            "category": "time_step",
            "recommendation": f"Use initial time_step_s <= {recommended_dt:.6g}." if recommended_dt else "Review time step after fixing passport inputs.",
            "evidence": [
                f"Courant={checks.get('courant_number')}",
                f"cell_length_m={checks.get('cell_length_m')}",
                f"reference_velocity_m_s={checks.get('reference_velocity_m_s')}",
            ],
            "blocked": failed,
        },
        {
            "category": "interface_capturing",
            "recommendation": "Use geometric reconstruction or an equivalent sharp-interface VOF scheme for the first Fluent setup.",
            "evidence": [f"interface={case.interface}"],
            "blocked": failed,
        },
        {
            "category": "mesh_refinement",
            "recommendation": "Refine near the initial interface, expected splash/free-surface region, walls, and outlet if reverse flow appears.",
            "evidence": [
                f"Weber={checks.get('weber_number')}",
                f"Bond={checks.get('bond_number')}",
                f"Capillary={checks.get('capillary_number')}",
            ],
            "blocked": failed,
        },
        {
            "category": "monitoring",
            "recommendation": "Monitor phase volume conservation, interface position, residuals, outlet backflow, and Courant number.",
            "evidence": ["VOF passport includes initial volume fraction and Courant gates."],
            "blocked": failed,
        },
    ]
    return {
        "schema_version": VOF_HINTS_SCHEMA_VERSION,
        "status": "blocked" if failed else "ready_with_warnings" if passport.get("status") == "warning" else "ready",
        "case_name": case.case_name,
        "hints": hints,
        "blocking_errors": list(passport.get("blocking_errors", [])),
        "warnings": list(passport.get("warnings", [])),
        "limitations": [
            "Hints are setup guidance for later Fluent work and are not solver results.",
            "Turbulence, wall functions, and y-plus strategy are deferred to the turbulence passport.",
        ],
    }


def physics_model_registry() -> dict[str, Any]:
    return {
        "schema_version": "fromcad2cfd_fastfluent_physics_model_registry_v1",
        "models": {
            "single_phase_laminar": {"status": "implemented_in_existing_fastcfd_routes", "role": "bounded single-phase pilot flow"},
            "vof_two_phase": {
                "status": "implemented_passport_and_hints",
                "role": "VOF setup readiness gate for immiscible two-phase interface problems",
                "entrypoints": ["fromcad2cfd fastcfd write-vof-demo", "fromcad2cfd fastcfd validate-vof"],
            },
            "rans_turbulence": {"status": "planned_next_gate", "role": "RANS/SST/near-wall setup passport"},
        },
        "disabled_capabilities": ["vof_solver_claim", "turbulence_solver_claim", "fluent_replacement_claim"],
    }


def _validate_phases(phases: list[VOFPhase]) -> list[str]:
    errors = []
    for phase in phases:
        if not phase.name:
            errors.append("VOF phase name must be non-empty.")
        if phase.density_kg_m3 <= 0:
            errors.append(f"Phase density must be positive: {phase.name}.")
        if phase.dynamic_viscosity_pa_s <= 0:
            errors.append(f"Phase dynamic viscosity must be positive: {phase.name}.")
        if phase.initial_volume_fraction < 0 or phase.initial_volume_fraction > 1:
            errors.append(f"Phase initial volume fraction must be in [0, 1]: {phase.name}.")
    return errors


def _primary_phase(phases: list[VOFPhase]) -> VOFPhase:
    for phase in phases:
        if phase.role == "primary_liquid":
            return phase
    return max(phases, key=lambda phase: phase.density_kg_m3)


def _secondary_phase(phases: list[VOFPhase], primary: VOFPhase) -> VOFPhase:
    for phase in phases:
        if phase.name != primary.name:
            return phase
    raise ValueError("VOF requires at least one secondary phase.")


def _positive(value: Any, name: str, errors: list[str]) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"VOF value must be numeric: {name}.")
        return 1.0
    if number <= 0:
        errors.append(f"VOF value must be positive: {name}.")
        return 1.0
    return number


def _nonnegative(value: Any, name: str, errors: list[str]) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"VOF value must be numeric: {name}.")
        return 0.0
    if number < 0:
        errors.append(f"VOF value must be non-negative: {name}.")
        return 0.0
    return number


def _vector3(value: Any) -> tuple[float, float, float]:
    if not isinstance(value, list | tuple) or len(value) != 3:
        raise ValueError("VOF gravity_m_s2 must be a 3-value vector.")
    return (float(value[0]), float(value[1]), float(value[2]))


def _assert_no_dangerous_keys(value: Any, *, path: str = "$") -> None:
    dangerous = {"argv", "command", "command_line", "cpp_code", "delete", "executable", "python", "shell", "source_code"}
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in dangerous:
                raise ValueError(f"Dangerous VOF schema key is not allowed at {path}.{key}: {key}")
            _assert_no_dangerous_keys(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_dangerous_keys(item, path=f"{path}[{index}]")


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _vof_markdown(passport: dict[str, Any], hints: dict[str, Any]) -> str:
    checks = passport["checks"]
    lines = [
        "# FastFluent VOF Physics Passport",
        "",
        f"Status: `{passport['status']}`",
        f"Case: `{passport['case_name']}`",
        "",
        "## Dimensionless Checks",
        "",
        f"- Reynolds number: `{checks['reynolds_number']}`",
        f"- Weber number: `{checks['weber_number']}`",
        f"- Bond number: `{checks['bond_number']}`",
        f"- Capillary number: `{checks['capillary_number']}`",
        f"- Froude number: `{checks['froude_number']}`",
        f"- VOF Courant number: `{checks['courant_number']}`",
        "",
        "## Fluent Setup Hints",
        "",
    ]
    lines.extend(f"- `{hint['category']}`: {hint['recommendation']}" for hint in hints["hints"])
    if passport["blocking_errors"]:
        lines.extend(["", "## Blocking Errors", ""])
        lines.extend(f"- {error}" for error in passport["blocking_errors"])
    if passport["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in passport["warnings"])
    lines.extend(["", "## Scope", "", "This is a VOF physics-passport gate and setup-hint report, not a VOF solver."])
    return "\n".join(lines) + "\n"
