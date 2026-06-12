"""Common CAD backend interfaces for the CAD-to-CFD framework."""

from .backend import CADBackend
from .registry import BackendRegistration, BackendRegistry, registry
from .schemas import (
    AgentResult,
    CADBackendCapabilities,
    ExportManifest,
    GeometryRecipe,
    ModelInspection,
    ParameterEditRequest,
)

__all__ = [
    "AgentResult",
    "BackendRegistration",
    "BackendRegistry",
    "CADBackend",
    "CADBackendCapabilities",
    "ExportManifest",
    "GeometryRecipe",
    "ModelInspection",
    "ParameterEditRequest",
    "registry",
]
