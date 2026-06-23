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
| Algebraic eddy-viscosity turbulent channel | `fromcad2cfd fastcfd unstructured solve-turbulent-channel` | Runs a bounded pressure-driven channel benchmark with Prandtl mixing-length eddy viscosity, turbulent-viscosity ratio output, and convergence history. |
| Standard k-epsilon turbulent channel | `fromcad2cfd fastcfd unstructured solve-kepsilon-channel` | Runs a bounded two-equation k-epsilon channel benchmark with k, epsilon, production, eddy-viscosity, residual, and convergence evidence. |
| Pressure-corrected k-epsilon channel | `fromcad2cfd fastcfd unstructured solve-kepsilon-pressure-channel` | Runs a bounded pressure-correction loop with momentum prediction, pressure correction, k/epsilon transport, divergence monitors, and Fluent pressure-velocity hints. |
| Menter k-omega SST turbulent channel | `fromcad2cfd fastcfd unstructured solve-sst-channel` | Runs a bounded SST channel benchmark with k, omega, F1/F2 blending, eddy-viscosity limiter, residual, and convergence evidence. |
| Turbulence evidence ladder | `fromcad2cfd fastcfd unstructured solve-turbulence-ladder` | Runs the local algebraic, k-epsilon, pressure-corrected k-epsilon, and SST tiers and recommends the strongest passed evidence tier. |
| Unstructured case runner | `fromcad2cfd fastcfd unstructured run-case` | Runs an agent-safe JSON case with explicit mesh, physics, boundary conditions, and solver controls. |
| Public unstructured benchmark suite | `fromcad2cfd fastcfd unstructured run-benchmark-suite` | Runs the current public-safe suite across channel validation, steady case, obstacle evidence, VOF-lite, and turbulence ladder. |
| Fluent hint compiler | `fromcad2cfd fastcfd compile-fluent-hints` | Aggregates setup hints only when every hint has explicit evidence and source-artifact traceability. |
| Solver-plan patch compiler | `fromcad2cfd fastcfd compile-fluent-patch` | Converts supported evidence passports or hint artifacts into validated, non-executing Fluent `solver_plan_patch.json` bundles. |
| Existing passport patch demo | `fromcad2cfd fastcfd existing-passport-patch-demo` | Generates public VOF, turbulence, rheology, and combined solver-plan patch bundles for the Fluent Solver Plan v2 preview receiver. |
| Steam-air condensation v2 | `fromcad2cfd fastcfd steam-air-v2-demo` | Adds Reynolds, Prandtl, Peclet, Jakob, Stefan, HTC, mass-transfer resistance, and source-term checks to the steam-air patch route. |
| Solid-liquid suspension passport | `fromcad2cfd fastcfd solid-liquid-handoff-demo` | Adds particle Reynolds, Stokes number, settling, mass loading, cell-particle ratio, time-step risk, and DPM/Mixture/Eulerian model-selection evidence. |

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

The solver-plan patch compiler follows the same evidence rule. It can compile
VOF, turbulence, rheology, and steam-air passports into patch bundles, but it
does not run Fluent, edit Fluent files, call PyFluent, or generate UDF code.

## Engineering Role

The implemented gates can support early engineering decisions such as:

- whether a laminar, RANS, VOF, or non-Newtonian Fluent setup is plausible,
- whether near-wall mesh planning is compatible with the intended turbulence
  model,
- whether a material model behaves reasonably over the expected shear-rate
  range,
- whether public unstructured examples preserve CAD-to-CFD boundary zones,
- whether a simple alpha transport check remains bounded before Fluent VOF
  setup,
- whether simplified local eddy-viscosity, k-epsilon, pressure-corrected
  k-epsilon, and SST channel benchmarks activate turbulence effects, preserve
  wall constraints, and provide usable turbulence-closure evidence before later
  Fluent RANS validation,
- whether an explicit JSON case can preserve mesh, boundary-condition, solver,
  and output intent for repeatable agent execution,
- whether the public benchmark suite still passes before larger private or
  Fluent-coupled work begins.

These gates are designed to make the agent's pre-Fluent recommendations
auditable. The roadmap beyond this layer is production Fluent Meshing,
production Fluent Solver automation, production turbulence validation,
production multiphase validation, verified non-Newtonian CFD, and GPU
acceleration.
