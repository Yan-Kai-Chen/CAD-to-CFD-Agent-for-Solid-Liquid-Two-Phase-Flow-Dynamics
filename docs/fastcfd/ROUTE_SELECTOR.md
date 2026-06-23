# FastFluent Route Selector

Route Selector is the M5 decision layer for the general FastFluent workflow.
It reads a Flow Pack and recommends the next controlled route.

The selector does not execute solvers, edit Fluent cases, call PyFluent, run
UDFs, or run arbitrary scripts. It writes reviewable route-selection artifacts
only.

## Inputs

The selector expects a Flow Pack directory created by M4:

```powershell
python -m fromcad2cfd fastcfd flow-pack build-demo --output-dir sandbox/output/flow_pack_demo
```

Then select the next route:

```powershell
python -m fromcad2cfd fastcfd route-selector select sandbox/output/flow_pack_demo --output-dir sandbox/output/route_selection
```

## Public Demo

```powershell
python -m fromcad2cfd fastcfd route-selector demo --output-dir sandbox/output/route_selector_demo
```

The demo builds a public channel-flow Flow Pack and recommends the bounded
structured FastFluent route.

## Output Artifacts

```text
route_selection.json
route_selection_report.md
route_catalog.json
```

`route_selection.json` includes:

- recommended route
- confidence
- rationale
- recommended commands
- alternatives
- rejected routes
- evidence summary
- agent next actions
- explicit execution boundary

## Current Route Catalog

- `fix_setup_contracts`
- `complete_mesh_gateway`
- `native_fastfluent_structured`
- `unstructured_fvm_evidence`
- `physics_passport_review`
- `fluent_planning_preview`
- `manual_review`

## Decision Boundaries

Route Selector recommends the immediate next safe workflow step. It does not
claim that a final CFD validation has been completed.

For example:

- a valid structured channel-flow Flow Pack can route to
  `native_fastfluent_structured`
- a valid unstructured flow Flow Pack can route to `unstructured_fvm_evidence`
- a VOF, turbulence, rheology, thermal, scalar, porous, or particle case can
  route to `physics_passport_review`
- an invalid setup routes to `fix_setup_contracts`
- a setup missing mesh evidence routes to `complete_mesh_gateway`

## Current Limitations

- Route Selector v1 is rule-based.
- It does not auto-generate complete solver cases from every CaseSpec family.
- It does not run the recommended route.
- Route confidence is a workflow-confidence label, not a physical-validation
  metric.
