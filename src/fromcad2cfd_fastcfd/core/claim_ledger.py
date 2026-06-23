"""Claim ledger v3 for bounded FastFluent evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CLAIM_LEDGER_SCHEMA_VERSION = "fastfluent_claim_ledger_v3"

ALLOWED_CLAIM_LEVELS = {
    "setup_only",
    "screening",
    "native_evidence",
    "fluent_aligned",
    "engineering_candidate",
}


@dataclass(frozen=True)
class ClaimLedgerValidation:
    """Validation result for a claim ledger."""

    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fastfluent_claim_ledger_validation_v1",
            "status": self.status,
            "passed": self.passed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def build_default_claim_ledger(
    *,
    claim_level: str,
    supported_claims: list[str] | None = None,
    unsupported_claims: list[str] | None = None,
    required_next_steps: list[str] | None = None,
) -> dict[str, Any]:
    """Build a conservative claim ledger for an evidence bundle."""

    return {
        "schema_version": CLAIM_LEDGER_SCHEMA_VERSION,
        "claim_level": claim_level,
        "supported_claims": supported_claims or [],
        "unsupported_claims": unsupported_claims
        or [
            "This result is not a production CFD replacement.",
            "This result is not final engineering sign-off.",
        ],
        "required_next_steps": required_next_steps or ["Review the evidence bundle before any Fluent handoff."],
    }


def validate_claim_ledger(payload: dict[str, Any]) -> ClaimLedgerValidation:
    """Validate a claim ledger using conservative, machine-readable checks."""

    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(payload, dict):
        return ClaimLedgerValidation(status="failed", errors=["Claim ledger must be a JSON object."])
    if payload.get("schema_version") != CLAIM_LEDGER_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {payload.get('schema_version')!r}")
    if payload.get("claim_level") not in ALLOWED_CLAIM_LEVELS:
        errors.append(f"claim_level must be one of {sorted(ALLOWED_CLAIM_LEVELS)}.")
    for key in ("supported_claims", "unsupported_claims", "required_next_steps"):
        value = payload.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            errors.append(f"{key} must be a list of non-empty strings.")
    if not payload.get("unsupported_claims"):
        warnings.append("unsupported_claims is empty; bounded FastFluent evidence should state what it does not prove.")
    if payload.get("claim_level") in {"native_evidence", "fluent_aligned", "engineering_candidate"} and not payload.get("supported_claims"):
        warnings.append("supported_claims is empty for a non-setup claim level.")
    return ClaimLedgerValidation(status="failed" if errors else "passed", errors=errors, warnings=warnings)
