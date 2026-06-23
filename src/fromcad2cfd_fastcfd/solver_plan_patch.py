"""Agent-safe FastFluent to Fluent solver-plan patch contract.

This module defines a non-executing patch artifact. It can recommend future
Fluent solver-plan changes, but it never launches Fluent, emits raw TUI, or
stores arbitrary executable code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any


SOLVER_PLAN_PATCH_SCHEMA_VERSION = "fromcad2cfd_fastfluent_solver_plan_patch_v1"

ALLOWED_PATCH_OPS = {"add", "replace", "append_unique", "warn", "block"}
ALLOWED_STATUS = {"pass", "warn", "block"}
ALLOWED_PATCH_PREFIXES = (
    "/runtime",
    "/mesh",
    "/physics",
    "/materials",
    "/boundaries",
    "/numerics",
    "/initialization",
    "/transient",
    "/monitors",
    "/source_terms",
    "/postprocessing",
    "/acceptance_criteria",
)
EVIDENCE_REQUIRED_PREFIXES = (
    "/physics",
    "/numerics",
    "/transient",
    "/monitors",
    "/source_terms",
)
DANGEROUS_KEYS = {
    "shell",
    "command",
    "cmd",
    "executable",
    "subprocess",
    "python",
    "python_code",
    "source_code",
    "cpp_code",
    "c_code",
    "udf_code",
    "delete",
    "remove_file",
    "raw_tui",
    "raw_pyfluent",
    "journal",
    "system",
    "eval",
    "exec",
}


@dataclass(frozen=True)
class PatchEvidence:
    evidence_id: str
    source_module: str
    source_artifact: str
    source_schema_version: str
    source_status: str
    quantity_name: str
    quantity_value: Any
    quantity_units: str
    threshold_or_rule: str
    interpretation: str
    confidence: str
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_module": self.source_module,
            "source_artifact": self.source_artifact,
            "source_schema_version": self.source_schema_version,
            "source_status": self.source_status,
            "quantity_name": self.quantity_name,
            "quantity_value": self.quantity_value,
            "quantity_units": self.quantity_units,
            "threshold_or_rule": self.threshold_or_rule,
            "interpretation": self.interpretation,
            "confidence": self.confidence,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class PatchOperation:
    op: str
    path: str
    value: Any
    reason: str
    evidence_refs: list[str] = field(default_factory=list)
    confidence: str = "medium"
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "path": self.path,
            "value": self.value,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class SolverPlanPatch:
    case_name: str
    status: str
    summary: str
    evidence: list[PatchEvidence | dict[str, Any]]
    patches: list[PatchOperation | dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_by: str = "fromcad2cfd_fastfluent"
    schema_version: str = SOLVER_PLAN_PATCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_name": self.case_name,
            "created_by": self.created_by,
            "status": self.status,
            "summary": self.summary,
            "evidence": [item.to_dict() if hasattr(item, "to_dict") else dict(item) for item in self.evidence],
            "patches": [item.to_dict() if hasattr(item, "to_dict") else dict(item) for item in self.patches],
            "warnings": list(self.warnings),
            "blocking_errors": list(self.blocking_errors),
            "limitations": list(self.limitations),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class PatchValidationResult:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_patch_count: int = 0
    checked_evidence_count: int = 0

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "checked_patch_count": self.checked_patch_count,
            "checked_evidence_count": self.checked_evidence_count,
        }


def find_dangerous_keys(obj: Any, path: str = "$") -> list[str]:
    """Return recursive locations whose key names are unsafe for agent artifacts."""

    findings: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key)
            key_lower = key_text.lower()
            next_path = f"{path}.{key_text}"
            if key_lower in DANGEROUS_KEYS:
                findings.append(next_path)
            findings.extend(find_dangerous_keys(value, next_path))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            findings.extend(find_dangerous_keys(value, f"{path}[{index}]"))
    return findings


def validate_solver_plan_patch(patch: dict[str, Any]) -> PatchValidationResult:
    """Validate a solver-plan patch artifact using fail-closed rules."""

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(patch, dict):
        return PatchValidationResult(status="failed", errors=["Patch payload must be a JSON object."])

    dangerous = find_dangerous_keys(patch)
    if dangerous:
        errors.append("Dangerous key names found: " + ", ".join(dangerous))

    if patch.get("schema_version") != SOLVER_PLAN_PATCH_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {patch.get('schema_version')!r}")

    status = patch.get("status")
    if status not in ALLOWED_STATUS:
        errors.append(f"Unsupported patch status: {status!r}")

    evidence = patch.get("evidence")
    if not isinstance(evidence, list):
        errors.append("evidence must be a list.")
        evidence = []
    patches = patch.get("patches")
    if not isinstance(patches, list):
        errors.append("patches must be a list.")
        patches = []

    evidence_ids: set[str] = set()
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"Evidence item {index} must be an object.")
            continue
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append(f"Evidence item {index} is missing evidence_id.")
        else:
            if evidence_id in evidence_ids:
                warnings.append(f"Duplicate evidence_id: {evidence_id}")
            evidence_ids.add(evidence_id)
        for field_name in [
            "source_module",
            "source_artifact",
            "source_schema_version",
            "source_status",
            "quantity_name",
            "threshold_or_rule",
            "interpretation",
            "confidence",
        ]:
            if field_name not in item:
                errors.append(f"Evidence item {index} is missing {field_name}.")

    if not patches and status != "block":
        errors.append("patches must not be empty unless status is block.")
    if not patches and status == "block" and not patch.get("blocking_errors"):
        errors.append("A block patch with no operations must include blocking_errors.")

    for index, operation in enumerate(patches):
        if not isinstance(operation, dict):
            errors.append(f"Patch operation {index} must be an object.")
            continue
        op = operation.get("op")
        if op not in ALLOWED_PATCH_OPS:
            errors.append(f"Patch operation {index} has unsupported op: {op!r}")
        path = operation.get("path")
        if not isinstance(path, str) or not path:
            errors.append(f"Patch operation {index} is missing path.")
            continue
        if not _path_is_allowed(path):
            errors.append(f"Patch operation {index} path is outside allowlist: {path}")
        evidence_refs = operation.get("evidence_refs", [])
        if evidence_refs is None:
            evidence_refs = []
        if not isinstance(evidence_refs, list):
            errors.append(f"Patch operation {index} evidence_refs must be a list.")
            evidence_refs = []
        missing_refs = [ref for ref in evidence_refs if ref not in evidence_ids]
        if missing_refs:
            errors.append(f"Patch operation {index} references missing evidence: {missing_refs}")
        if _path_requires_evidence(path) and op not in {"block", "warn"} and not evidence_refs:
            errors.append(f"Patch operation {index} at {path} requires evidence_refs.")
        if _path_requires_evidence(path) and op in {"block", "warn"} and not evidence_refs and evidence_ids:
            warnings.append(f"Patch operation {index} at {path} should include evidence_refs.")
        for field_name in ["reason", "confidence", "limitations"]:
            if field_name not in operation:
                errors.append(f"Patch operation {index} is missing {field_name}.")

    blocking_errors = patch.get("blocking_errors", [])
    if status == "block" and not blocking_errors:
        warnings.append("Patch status is block but blocking_errors is empty.")
    if status in {"pass", "warn"} and blocking_errors:
        errors.append("Non-block patch status must not include blocking_errors.")

    return PatchValidationResult(
        status="failed" if errors else "passed",
        errors=errors,
        warnings=warnings,
        checked_patch_count=len(patches),
        checked_evidence_count=len(evidence),
    )


def write_solver_plan_patch_json(patch: SolverPlanPatch | dict[str, Any], output_path: str | Path) -> Path:
    payload = patch.to_dict() if hasattr(patch, "to_dict") else dict(patch)
    validation = validate_solver_plan_patch(payload)
    if not validation.passed:
        raise ValueError("Invalid solver plan patch: " + "; ".join(validation.errors))
    path = Path(output_path)
    os.makedirs(_windows_long_path(path.parent), exist_ok=True)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    return path


def write_solver_plan_patch_report(patch: SolverPlanPatch | dict[str, Any], output_path: str | Path) -> Path:
    payload = patch.to_dict() if hasattr(patch, "to_dict") else dict(patch)
    validation = validate_solver_plan_patch(payload)
    path = Path(output_path)
    os.makedirs(_windows_long_path(path.parent), exist_ok=True)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(_solver_plan_patch_markdown(payload, validation))
    return path


def _path_is_allowed(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in ALLOWED_PATCH_PREFIXES)


def _path_requires_evidence(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in EVIDENCE_REQUIRED_PREFIXES)


def _solver_plan_patch_markdown(patch: dict[str, Any], validation: PatchValidationResult) -> str:
    lines = [
        "# FastFluent Solver Plan Patch Report",
        "",
        f"Case name: `{patch.get('case_name')}`",
        f"Status: `{patch.get('status')}`",
        f"Validation: `{validation.status}`",
        "",
        "## Summary",
        "",
        str(patch.get("summary") or ""),
        "",
        "## Patch Operations",
        "",
        "| # | Op | Path | Evidence | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for index, operation in enumerate(patch.get("patches", []), start=1):
        refs = ", ".join(operation.get("evidence_refs") or [])
        lines.append(
            f"| {index} | `{operation.get('op')}` | `{operation.get('path')}` | `{refs}` | {_escape_table(str(operation.get('reason') or ''))} |"
        )
    lines.extend(["", "## Evidence", "", "| Evidence ID | Quantity | Value | Rule | Interpretation |", "| --- | --- | --- | --- | --- |"])
    for item in patch.get("evidence", []):
        lines.append(
            f"| `{item.get('evidence_id')}` | `{item.get('quantity_name')}` | `{item.get('quantity_value')} {item.get('quantity_units', '')}` | "
            f"{_escape_table(str(item.get('threshold_or_rule') or ''))} | {_escape_table(str(item.get('interpretation') or ''))} |"
        )
    lines.extend(["", "## Warnings", ""])
    if patch.get("warnings", []):
        lines.extend(f"- {item}" for item in patch.get("warnings", []))
    else:
        lines.append("- None")
    if validation.warnings:
        lines.extend(f"- Validation warning: {item}" for item in validation.warnings)
    lines.extend(["", "## Blocking Errors", ""])
    blocking = list(patch.get("blocking_errors", [])) + [f"Validation error: {item}" for item in validation.errors]
    lines.extend(f"- {item}" for item in blocking) if blocking else lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    if patch.get("limitations", []):
        lines.extend(f"- {item}" for item in patch.get("limitations", []))
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Reviewer Checklist",
            "",
            "- Confirm Fluent model selection.",
            "- Confirm material properties.",
            "- Confirm boundary conditions.",
            "- Confirm time step.",
            "- Confirm monitor definitions.",
            "- Confirm source term dimensions and signs.",
            "- Confirm mesh quality before execution.",
            "",
        ]
    )
    return "\n".join(lines)


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _windows_long_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved
