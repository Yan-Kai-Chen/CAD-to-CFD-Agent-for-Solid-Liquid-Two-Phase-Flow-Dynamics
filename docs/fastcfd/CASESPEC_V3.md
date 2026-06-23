# FastFluent CaseSpec v3

CaseSpec v3 is the shared input contract for the general FastFluent evidence
layer. It is designed to give agents one bounded way to describe CFD screening,
native evidence, and Fluent handoff requests.

## Role

CaseSpec v3 does not replace the older route-specific job files yet. It is an
additive facade used to normalize future FastFluent cases before dispatching to
structured, unstructured, physics-passport, sweep, or handoff routes.

## Required Top-Level Fields

- `schema_version`: must be `fastfluent_case_spec_v3`
- `case_id`: filesystem-safe case identifier
- `case_type`: namespaced case type, such as `flow.steady_incompressible`
- `claim_level`: one of `setup_only`, `screening`, `native_evidence`,
  `fluent_aligned`, or `engineering_candidate`
- `geometry`: source, dimension, parameters, and zones
- `mesh`: mesh source and quality gates
- `materials`: material definitions
- `boundary_conditions`: zone-keyed boundary condition definitions
- `numerics`: time mode, solver family, iteration or time-step controls
- `qoi_targets`: requested quantities of interest
- `handoff`: optional Fluent hint or solver-plan patch options

## Safety Rules

CaseSpec v3 rejects dangerous key names such as raw commands, source code,
shell execution, PyFluent snippets, Fluent TUI text, UDF code, or file deletion
requests. It is a declarative case contract, not an execution script.

## Current CLI

```powershell
python -m fromcad2cfd fastcfd validate-case examples/fastcfd/casespec_v3/channel_flow_case.json
python -m fromcad2cfd fastcfd explain-case examples/fastcfd/casespec_v3/channel_flow_case.json --format markdown
```

With an output directory:

```powershell
python -m fromcad2cfd fastcfd validate-case examples/fastcfd/casespec_v3/channel_flow_case.json --output-dir sandbox/output/casespec_v3_demo
```

This writes:

- `case_validation.json`
- `case_summary.md`
- `unsupported_features.json`
- `claim_level.json`

## Current Limitations

- CaseSpec v3 currently validates and explains cases; it does not yet dispatch
  every old FastFluent route.
- The current material and boundary validation is intentionally conservative.
- Detailed unit conversion belongs to the next M2 unit, boundary, and material
  contract layer.
- Mesh Gateway v2 will later make structured and unstructured mesh validation
  share one vocabulary.
