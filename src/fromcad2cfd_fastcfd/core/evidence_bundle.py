"""EvidenceBundle v3 validation for FastFluent outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .claim_ledger import validate_claim_ledger


EVIDENCE_BUNDLE_SCHEMA_VERSION = "fastfluent_evidence_bundle_v3"

REQUIRED_FILES = (
    "case.json",
    "run_manifest.json",
    "validation_status.json",
    "qoi.json",
    "claim_ledger.json",
    "limitations.md",
    "report.md",
)
OPTIONAL_FILES = (
    "mesh_manifest.json",
    "mesh_quality.json",
    "boundary_contract.json",
    "material_contract.json",
    "numerics.json",
    "residual_history.csv",
    "qoi_table.csv",
    "fluent_hints.json",
    "solver_plan_patch.json",
)
OPTIONAL_DIRS = ("field_outputs",)


@dataclass(frozen=True)
class EvidenceBundleValidation:
    """Validation result for an EvidenceBundle v3 output directory."""

    status: str
    bundle_dir: str
    present_files: list[str] = field(default_factory=list)
    missing_required_files: list[str] = field(default_factory=list)
    present_optional_files: list[str] = field(default_factory=list)
    present_optional_dirs: list[str] = field(default_factory=list)
    json_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fastfluent_evidence_bundle_validation_v1",
            "status": self.status,
            "passed": self.passed,
            "bundle_schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "bundle_dir": self.bundle_dir,
            "present_files": list(self.present_files),
            "missing_required_files": list(self.missing_required_files),
            "present_optional_files": list(self.present_optional_files),
            "present_optional_dirs": list(self.present_optional_dirs),
            "json_errors": list(self.json_errors),
            "warnings": list(self.warnings),
        }


def validate_evidence_bundle(bundle_dir: str | Path) -> EvidenceBundleValidation:
    """Validate the structural completeness of a FastFluent EvidenceBundle v3."""

    root = Path(bundle_dir)
    present_files: list[str] = []
    missing: list[str] = []
    optional_present: list[str] = []
    optional_dirs: list[str] = []
    json_errors: list[str] = []
    warnings: list[str] = []

    if not root.exists() or not root.is_dir():
        return EvidenceBundleValidation(status="failed", bundle_dir=str(root), missing_required_files=list(REQUIRED_FILES))

    for filename in REQUIRED_FILES:
        path = root / filename
        if path.is_file():
            present_files.append(filename)
        else:
            missing.append(filename)
    for filename in OPTIONAL_FILES:
        if (root / filename).is_file():
            optional_present.append(filename)
    for dirname in OPTIONAL_DIRS:
        if (root / dirname).is_dir():
            optional_dirs.append(dirname)

    for filename in [*present_files, *optional_present]:
        if filename.endswith(".json"):
            try:
                json.loads((root / filename).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                json_errors.append(f"{filename}: {exc}")

    claim_path = root / "claim_ledger.json"
    if claim_path.is_file():
        try:
            claim_validation = validate_claim_ledger(json.loads(claim_path.read_text(encoding="utf-8")))
            if not claim_validation.passed:
                json_errors.extend(f"claim_ledger.json: {item}" for item in claim_validation.errors)
            warnings.extend(f"claim_ledger.json: {item}" for item in claim_validation.warnings)
        except (OSError, json.JSONDecodeError) as exc:
            json_errors.append(f"claim_ledger.json: {exc}")

    if "field_outputs" not in optional_dirs:
        warnings.append("field_outputs directory is absent; this is acceptable for setup-only bundles.")
    if "residual_history.csv" not in optional_present:
        warnings.append("residual_history.csv is absent; convergence evidence may be limited.")
    if "fluent_hints.json" not in optional_present:
        warnings.append("fluent_hints.json is absent; Fluent handoff evidence may be limited.")

    status = "failed" if missing or json_errors else "passed"
    return EvidenceBundleValidation(
        status=status,
        bundle_dir=str(root),
        present_files=present_files,
        missing_required_files=missing,
        present_optional_files=optional_present,
        present_optional_dirs=optional_dirs,
        json_errors=json_errors,
        warnings=warnings,
    )


def summarize_evidence_bundle_markdown(bundle_dir: str | Path, validation: EvidenceBundleValidation | None = None) -> str:
    """Render a concise Markdown summary for an EvidenceBundle v3 directory."""

    root = Path(bundle_dir)
    validation = validation or validate_evidence_bundle(root)
    case_payload = _read_json_if_present(root / "case.json")
    run_manifest = _read_json_if_present(root / "run_manifest.json")
    qoi = _read_json_if_present(root / "qoi.json")
    claim_ledger = _read_json_if_present(root / "claim_ledger.json")

    lines = [
        "# FastFluent EvidenceBundle v3 Summary",
        "",
        f"- Bundle directory: `{root}`",
        f"- Validation: `{validation.status}`",
        f"- Case ID: `{case_payload.get('case_id')}`",
        f"- Case type: `{case_payload.get('case_type')}`",
        f"- Run status: `{run_manifest.get('status')}`",
        f"- Claim level: `{claim_ledger.get('claim_level')}`",
        "",
        "## Files",
        "",
        f"- Required present: `{', '.join(validation.present_files) or 'none'}`",
        f"- Required missing: `{', '.join(validation.missing_required_files) or 'none'}`",
        f"- Optional present: `{', '.join(validation.present_optional_files) or 'none'}`",
        f"- Optional directories: `{', '.join(validation.present_optional_dirs) or 'none'}`",
        "",
        "## QoI",
        "",
    ]
    metrics = qoi.get("metrics") if isinstance(qoi.get("metrics"), dict) else qoi
    if metrics:
        for key, value in sorted(metrics.items()):
            if isinstance(value, (str, int, float, bool)) or value is None:
                lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- None")
    lines.extend(["", "## Supported Claims", ""])
    supported = claim_ledger.get("supported_claims") if isinstance(claim_ledger.get("supported_claims"), list) else []
    lines.extend(f"- {item}" for item in supported) if supported else lines.append("- None")
    lines.extend(["", "## Unsupported Claims", ""])
    unsupported = claim_ledger.get("unsupported_claims") if isinstance(claim_ledger.get("unsupported_claims"), list) else []
    lines.extend(f"- {item}" for item in unsupported) if unsupported else lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in validation.warnings) if validation.warnings else lines.append("- None")
    lines.extend(["", "## Errors", ""])
    errors = [*validation.missing_required_files, *validation.json_errors]
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
