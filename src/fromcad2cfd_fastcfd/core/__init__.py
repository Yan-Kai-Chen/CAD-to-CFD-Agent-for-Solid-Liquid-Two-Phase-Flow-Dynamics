"""Core contracts for the general FastFluent evidence layer."""

from __future__ import annotations

from .case_spec import (
    CASE_SPEC_SCHEMA_VERSION,
    CaseSpecValidation,
    explain_case_spec_markdown,
    read_case_spec,
    validate_case_spec,
)
from .claim_ledger import (
    CLAIM_LEDGER_SCHEMA_VERSION,
    ClaimLedgerValidation,
    build_default_claim_ledger,
    validate_claim_ledger,
)
from .evidence_bundle import (
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
    EvidenceBundleValidation,
    summarize_evidence_bundle_markdown,
    validate_evidence_bundle,
)

__all__ = [
    "CASE_SPEC_SCHEMA_VERSION",
    "CLAIM_LEDGER_SCHEMA_VERSION",
    "EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "CaseSpecValidation",
    "ClaimLedgerValidation",
    "EvidenceBundleValidation",
    "build_default_claim_ledger",
    "explain_case_spec_markdown",
    "read_case_spec",
    "summarize_evidence_bundle_markdown",
    "validate_case_spec",
    "validate_claim_ledger",
    "validate_evidence_bundle",
]
