# FastFluent EvidenceBundle v3

EvidenceBundle v3 is the shared output contract for the general FastFluent
evidence layer. It standardizes how agents, reports, benchmark tools, and
Fluent handoff steps read native FastFluent outputs.

## Standard Layout

```text
output/<case_id>/
    case.json
    run_manifest.json
    validation_status.json
    mesh_manifest.json
    mesh_quality.json
    boundary_contract.json
    material_contract.json
    numerics.json
    residual_history.csv
    field_outputs/
        solution.vtu
    qoi.json
    qoi_table.csv
    fluent_hints.json
    solver_plan_patch.json
    claim_ledger.json
    limitations.md
    report.md
```

The current M1 validator requires the core files:

- `case.json`
- `run_manifest.json`
- `validation_status.json`
- `qoi.json`
- `claim_ledger.json`
- `limitations.md`
- `report.md`

Other files are optional because setup-only or passport-only routes may not
produce fields or residuals.

## Claim Ledger

Each bundle must include `claim_ledger.json` with schema version
`fastfluent_claim_ledger_v3`. The ledger records:

- `claim_level`
- `supported_claims`
- `unsupported_claims`
- `required_next_steps`

This prevents native screening outputs from being misread as final CFD
validation.

## Current CLI

```powershell
python -m fromcad2cfd fastcfd evidence validate-bundle sandbox/output/example_case
python -m fromcad2cfd fastcfd evidence summarize-bundle sandbox/output/example_case --format markdown
```

## Current Limitations

- EvidenceBundle v3 is currently a structural validator and summary layer.
- Existing FastFluent commands still write their historical artifact names.
- Future work should add adapters that convert each existing route into this
  common bundle layout.
- Fluent, PyFluent, UDF generation, and direct case editing remain outside this
  contract.
