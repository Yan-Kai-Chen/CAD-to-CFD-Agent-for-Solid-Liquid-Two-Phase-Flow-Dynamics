# FastFluent Physics Passports And Fluent Hints

This document summarizes the agent-facing physics gates that prepare evidence
for later Fluent work. These gates are not Fluent solvers and do not edit Fluent
case/data files.

## Implemented Gates

| Gate | Command | Role |
| --- | --- | --- |
| VOF physics passport | `fromcad2cfd fastcfd validate-vof` | Checks two-phase setup readiness, dimensionless groups, VOF Courant number, and Fluent VOF hints. |
| Turbulence passport | `fromcad2cfd fastcfd validate-turbulence` | Checks Reynolds regime, hydraulic diameter, turbulence intensity, first-cell y-plus, near-wall target, and Fluent viscous-model hints. |
| Rheology passport | `fromcad2cfd fastcfd run-rheology-benchmark` | Checks Newtonian, power-law, or Carreau-Yasuda material behavior over a shear-rate range. |
| Public obstacle-channel evidence | `fromcad2cfd fastcfd unstructured solve-obstacle-channel` | Generates or inspects a public body-fitted obstacle-channel mesh with named obstacle wall evidence. |
| VOF-lite alpha transport | `fromcad2cfd fastcfd unstructured solve-vof-lite` | Runs a bounded scalar alpha-transport benchmark with CFL and phase-volume-balance evidence. |
| Fluent hint compiler | `fromcad2cfd fastcfd compile-fluent-hints` | Aggregates setup hints only when every hint has explicit evidence and source-artifact traceability. |

## Evidence Rule

Every Fluent setup hint must carry:

- a `category`,
- a human-readable `recommendation`,
- a non-empty `evidence` list,
- a `source_artifact` path after compilation.

The compiler fails closed if evidence files are missing, hints are absent, or a
hint does not include evidence. This keeps downstream agent decisions
traceable and prevents unsupported Fluent setup instructions from being treated
as validated output.

## Engineering Role

The implemented gates can support early engineering decisions such as:

- whether a laminar, RANS, VOF, or non-Newtonian Fluent setup is plausible,
- whether near-wall mesh planning is compatible with the intended turbulence
  model,
- whether a material model behaves reasonably over the expected shear-rate
  range,
- whether public unstructured examples preserve CAD-to-CFD boundary zones,
- whether a simple alpha transport check remains bounded before Fluent VOF
  setup.

These gates are designed to make the agent's pre-Fluent recommendations
auditable. The roadmap beyond this layer is production Fluent Meshing,
production Fluent Solver automation, production turbulence validation,
production multiphase validation, verified non-Newtonian CFD, and GPU
acceleration.
