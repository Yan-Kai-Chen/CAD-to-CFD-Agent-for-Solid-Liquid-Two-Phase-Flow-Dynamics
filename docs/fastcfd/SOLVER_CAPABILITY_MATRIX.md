# FastFluent Solver Capability Matrix

This document describes the first step of the native solver expansion track.
The matrix classifies current FastFluent solver routes by physics coverage,
mesh support, validation evidence, and workflow boundary.

```powershell
python -m fromcad2cfd fastcfd solver-capability-matrix --output-dir sandbox/output/solver_capability_matrix --format markdown
```

The command writes:

```text
solver_matrix.json
solver_matrix.md
```

## S4 Hardened Steady Base

The `unstructured_steady_incompressible` route is now the S4 hardened base for
future coupled VOF, turbulence, heat/species transport, moving-geometry
evidence, and solid-liquid suspension work. Each run exposes stable semantic
artifact keys such as `steady_hardening_summary`, while the compact on-disk
filenames are kept short for Windows path safety:

```text
bc.json
lin.json
res.csv
qoi.json
hard.json
sol.vtu
report.md
status.json
```

The hardening summary records:

- mesh-quality gate;
- boundary-contract gate;
- linear-system convergence;
- velocity boundary preservation;
- controlled divergence and mass-flux blocking gates;
- stricter advisory divergence and mass-flux warning gates;
- `passed` / `warning` / `failed` quality status;
- an agent next-action decision.

## S6 Unified Transport Coupling

The `unified_transport_coupling_core` route is now implemented as S6. It gives
VOF-lite, temperature, species, particle concentration, and wax-fraction style
checks one shared scalar-transport interface.

```powershell
python -m fromcad2cfd fastcfd transport demo --output-dir sandbox/output/s6_transport_alpha --quantity alpha
```

The route records:

- transport case schema validation;
- Courant and diffusion gates;
- boundedness and clipping audits;
- integral balance QoI;
- material-property coupling ranges;
- Result Pack compatibility through `result-pack compile-native`.

It remains a scalar evidence route and does not claim coupled pressure-momentum
or final Fluent validation.

## S7 Full Workflow Runner

The `full_workflow_case_runner` route is now implemented as S7. It orchestrates
the agent workflow from CaseSpec through Flow Pack, Route Selector, Route Plan,
Execution Gate, Controlled Runner, optional S6 native advisory evidence, Result
Pack, and `agent_decision.json`.

```powershell
python -m fromcad2cfd fastcfd workflow demo --output-dir sandbox/output/s7_workflow_demo --mode native_advisory
```

The route records:

- per-stage status;
- failure-stage stop behavior;
- review-only dry-run Result Packs;
- S6 native advisory Result Packs;
- final agent decision artifacts;
- explicit no-Fluent-launch boundary.

It is an orchestration route, not a production CFD solver.

## Boundary

The capability matrix is an engineering planning artifact. It does not claim
that FastFluent replaces Fluent. Every solver route must keep its validation
scope explicit.
