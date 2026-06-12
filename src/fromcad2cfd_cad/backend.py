"""Protocol that CAD backends must implement."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from .schemas import AgentResult, GeometryRecipe, ParameterEditRequest


@runtime_checkable
class CADBackend(Protocol):
    """Common contract for CAD automation backends.

    Backends may be COM-based, journal-based, batch-runner-based, or MCP-backed.
    The contract intentionally exposes high-level safe operations instead of raw
    CAD API calls.
    """

    name: str

    def preflight(self) -> AgentResult:
        """Check local CAD availability and backend prerequisites."""

    def create_test_geometry(self, recipe: GeometryRecipe) -> AgentResult:
        """Create a controlled test model from a backend-neutral recipe."""

    def inspect_model(self, input_file: str | Path) -> AgentResult:
        """Inspect features, parameters, configurations, bodies, and exportability."""

    def copy_model_for_edit(self, input_file: str | Path, output_dir: str | Path) -> AgentResult:
        """Copy a source model into a workspace-controlled edit/output directory."""

    def edit_parameter_by_exact_name(self, request: ParameterEditRequest) -> AgentResult:
        """Edit one uniquely identified model parameter and stop on ambiguity."""

    def rebuild_and_validate(self, model_file: str | Path) -> AgentResult:
        """Rebuild the model and return validation details."""

    def export_geometry(self, model_file: str | Path, fmt: str, output_dir: str | Path) -> AgentResult:
        """Export geometry to a CFD handoff format such as STEP or Parasolid."""

    def write_report(self, result: AgentResult) -> AgentResult:
        """Write Markdown and JSON reports for a backend operation."""
