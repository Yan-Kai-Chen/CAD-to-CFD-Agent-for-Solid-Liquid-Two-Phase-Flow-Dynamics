"""Backend-neutral CAD data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


ResultStatus = Literal["success", "failed", "partial", "skipped"]


@dataclass
class AgentResult:
    """Serializable result envelope shared by CAD backends."""

    status: ResultStatus
    backend: str
    operation: str
    message: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    reports: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        *,
        backend: str,
        operation: str,
        message: str = "",
        outputs: dict[str, Any] | None = None,
        reports: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "AgentResult":
        return cls(
            status="success",
            backend=backend,
            operation=operation,
            message=message,
            outputs=outputs or {},
            reports=reports or {},
            metadata=metadata or {},
        )

    @classmethod
    def failed(
        cls,
        *,
        backend: str,
        operation: str,
        message: str,
        errors: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "AgentResult":
        return cls(
            status="failed",
            backend=backend,
            operation=operation,
            message=message,
            errors=errors or [message],
            metadata=metadata or {},
        )

    @property
    def ok(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "backend": self.backend,
            "operation": self.operation,
            "message": self.message,
            "outputs": self.outputs,
            "reports": self.reports,
            "errors": self.errors,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class GeometryRecipe:
    """Backend-neutral geometry creation request."""

    recipe_name: str
    model_name: str
    parameters_mm: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def require_parameter_mm(self, name: str) -> float:
        try:
            return self.parameters_mm[name]
        except KeyError as exc:
            raise ValueError(f"Missing required geometry parameter: {name}") from exc


@dataclass(frozen=True)
class ParameterEditRequest:
    """Safe parameter edit request shared by SolidWorks and NX."""

    input_file: str
    parameter_name: str
    value_mm: float
    output_dir: str
    model_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelInspection:
    """Backend-neutral inspection summary."""

    backend: str
    input_file: str
    features: list[dict[str, Any]] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    configurations: list[str] = field(default_factory=list)
    bodies: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "input_file": self.input_file,
            "features": self.features,
            "parameters": self.parameters,
            "configurations": self.configurations,
            "bodies": self.bodies,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ExportManifest:
    """CAD export metadata needed by CFD handoff layers."""

    backend: str
    source_model: str
    exported_file: str
    format: str
    units: str = "mm"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def exported_path(self) -> Path:
        return Path(self.exported_file)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "source_model": self.source_model,
            "exported_file": self.exported_file,
            "format": self.format,
            "units": self.units,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class CADBackendCapabilities:
    """Declared capabilities for backend discovery and MCP tool exposure."""

    backend: str
    status: str
    native_formats: tuple[str, ...] = ()
    export_formats: tuple[str, ...] = ("STEP",)
    supports_parameter_editing: bool = False
    supports_batch_runner: bool = False
    supports_interactive_session: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "status": self.status,
            "native_formats": list(self.native_formats),
            "export_formats": list(self.export_formats),
            "supports_parameter_editing": self.supports_parameter_editing,
            "supports_batch_runner": self.supports_batch_runner,
            "supports_interactive_session": self.supports_interactive_session,
            "notes": self.notes,
        }
