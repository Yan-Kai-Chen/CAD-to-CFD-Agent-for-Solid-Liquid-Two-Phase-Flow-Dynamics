# FastFluent S2 Goal: Practical Native Function Expansion Pack

Date: 2026-06-23  
Repository: `CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics`  
Execution mode: Codex `/goal` mode  
Recommended save path: `docs/FASTFLUENT_S2_PRACTICAL_NATIVE_FUNCTION_EXPANSION_GOAL_20260623.md`

---

## 0. Core Direction

This S2 stage should **not** be limited to one small wax application.

The goal is to add a set of practical, reusable, FastFluent-native functions that make FastFluent more useful as a lightweight CFD evidence engine.

Wax / thermal / rheology should be included as one important application, but the broader goal is:

```text
FastFluent practical native utilities
+ small native simulation kernels
+ material / source / scalar-transport tools
+ parameter sweeps
+ field/QoI outputs
+ public demos
+ tests
```

This stage must still not call ANSYS Fluent.

Do not launch Fluent.  
Do not call PyFluent.  
Do not generate UDF code.  
Do not require a Fluent license.

---

## 1. Why S2 Exists

Previous stages built:

```text
H1: VOF / turbulence / rheology evidence -> solver_plan_patch.json
H2: steam-air condensation v2
H3: solid-liquid suspension passport
H3.5: horizontal validation pack
S1: FastFluent-native simulation validation pack
H4: wax rheology / phase-change passport
```

H4 added wax material setup evidence.

However, the project should not become a collection of narrow passports. FastFluent should also gain simple, robust, practical native functions that can support many cases.

S2 therefore focuses on **plain but useful FastFluent capabilities**:

```text
1D/2D heat diffusion
scalar advection-diffusion
temperature-dependent property fields
source-term ramp/clamp toy models
parameter sweeps
field export
QoI extraction
analytic benchmark comparisons
basic stability indicators
```

This makes FastFluent more than a setup advisor.

It becomes a small practical engine for quick physics screening.

---

## 2. Strategic Framing

FastFluent should be framed as:

```text
a lightweight native physics-screening and simulation-evidence layer
```

not only:

```text
a Fluent setup recommendation system
```

S2 should strengthen the native side:

```text
case input
-> lightweight native computation
-> field / history / QoI
-> stability indicators
-> benchmark comparison
-> report
```

The output should be useful even if Fluent is never run.

---

## 3. Hard Boundary

### 3.1 Do Not Do

Do not:

```text
- Do not launch ANSYS Fluent.
- Do not call PyFluent.
- Do not require a Fluent license.
- Do not edit Fluent case/data files.
- Do not emit Fluent TUI commands.
- Do not emit PyFluent commands.
- Do not generate executable UDF code.
- Do not implement a production CFD solver.
- Do not implement DEM.
- Do not implement a full DPM solver.
- Do not implement full VOF surface reconstruction.
- Do not implement GPU acceleration in this goal.
- Do not integrate OpenFOAM.
- Do not use private CAD, private mesh, or private Fluent data.
```

### 3.2 Do Implement

Implement practical native functions:

```text
- 1D heat diffusion mini solver
- 2D heat diffusion mini solver if feasible
- scalar advection-diffusion mini solver
- temperature-dependent property evaluator
- Arrhenius viscosity field evaluator
- bounded source-term toy model with ramp/clamp
- parameter sweep runner
- QoI calculator
- field/history output writer
- public demo pack
- tests and docs
```

If some native solvers already exist, reuse them instead of rewriting.

---

## 4. Read First

Inspect the current repository:

```text
README.md
ROADMAP.md
docs/architecture.md

src/fromcad2cfd_fastcfd/
src/fromcad2cfd_fastcfd/cli.py
src/fromcad2cfd_fastcfd/capabilities.py
src/fromcad2cfd_fastcfd/native_simulation_pack.py
src/fromcad2cfd_fastcfd/native_simulation_artifacts.py
src/fromcad2cfd_fastcfd/rheology.py
src/fromcad2cfd_fastcfd/wax_rheology_phase_change.py
src/fromcad2cfd_fastcfd/steam_air_condensation_v2.py
src/fromcad2cfd_fastcfd/vof.py
src/fromcad2cfd_fastcfd/turbulence.py
src/fromcad2cfd_fastcfd/unstructured/

tests/unit/
```

Also inspect S1 and H4 docs if present:

```text
docs/FASTFLUENT_S1_NATIVE_SIMULATION_DELIVERY_20260623.md
docs/FASTFLUENT_HORIZONTAL_H4_WAX_RHEOLOGY_PHASE_CHANGE_DELIVERY_20260623.md
```

Create progress log:

```text
docs/FASTFLUENT_S2_PRACTICAL_NATIVE_FUNCTION_EXPANSION_PROGRESS_20260623.md
```

Baseline note must include:

```text
- Current native simulation pack capabilities.
- Current wax/rheology capabilities.
- Existing scalar/heat/field output utilities.
- Existing CLI commands.
- Existing tests before S2.
```

---

## 5. Main Deliverables

S2 has nine deliverables:

```text
Deliverable A: Practical Native Artifact Contract
Deliverable B: Heat Diffusion Utilities
Deliverable C: Scalar Advection-Diffusion Utilities
Deliverable D: Material Property Field Utilities
Deliverable E: Bounded Source-Term Toy Model
Deliverable F: Parameter Sweep Runner
Deliverable G: Practical Demo Pack CLI
Deliverable H: Tests
Deliverable I: Documentation and Delivery Report
```

---

# Deliverable A: Practical Native Artifact Contract

## A.1 Purpose

Define or extend a simple artifact contract for practical native FastFluent computations.

Suggested module:

```text
src/fromcad2cfd_fastcfd/practical_native_artifacts.py
```

If `native_simulation_artifacts.py` already exists and is suitable, reuse it.

---

## A.2 Artifact Types

Support these artifact categories:

```text
field_output
history_output
qoi_summary
stability_summary
benchmark_comparison
parameter_sweep_summary
```

Standard output files:

```text
input_case.json
field_output.csv or field_output.vtu
history.csv
qoi_summary.json
stability_summary.json
simulation_result.json
simulation_summary.md
```

---

## A.3 Schema

Use schema version:

```text
fromcad2cfd_fastfluent_practical_native_result_v1
```

Top-level `simulation_result.json` fields:

```text
schema_version
case_id
case_name
module
kernel
status
input_summary
grid_summary
time_summary
stability_summary
qoi_summary
field_outputs
history_outputs
benchmark_comparison
warnings
blocking_errors
limitations
metadata
```

Allowed status:

```text
pass
warn
block
failed
unavailable
```

---

# Deliverable B: Heat Diffusion Utilities

## B.1 Purpose

Implement simple, robust heat diffusion mini solvers that are useful beyond wax.

Suggested module:

```text
src/fromcad2cfd_fastcfd/practical_heat_diffusion.py
```

If similar utilities already exist, reuse and extend them.

---

## B.2 1D Heat Diffusion

Implement a 1D transient heat diffusion solver:

```text
∂T/∂t = α ∂²T/∂x²
```

Supported boundary conditions for v1:

```text
fixed_temperature_left
fixed_temperature_right
insulated_left
insulated_right
```

Suggested numerical method:

```text
explicit finite difference with stability check
```

or reuse existing stable method if present.

Required stability indicator:

```text
Fourier number Fo = alpha * dt / dx^2
```

For explicit scheme:

```text
Fo <= 0.5 recommended
```

Outputs:

```text
temperature_history.csv
temperature_field_final.csv
qoi_summary.json
stability_summary.json
simulation_summary.md
```

QoIs:

```text
max_temperature
min_temperature
mean_temperature
thermal_front_position
energy_proxy
```

Validation:

```text
- stable Fo case passes
- unstable Fo case warns or blocks
- all values finite
```

---

## B.3 1D Analytical Comparison

If feasible, add simple analytical or reference comparison for semi-infinite slab or fixed-end diffusion.

If not feasible, use a manufactured reference or expected trend.

Output:

```text
benchmark_comparison:
  l2_error
  max_error
  reference_type
```

Do not fake analytical accuracy.

---

## B.4 2D Heat Diffusion

Implement a minimal 2D heat diffusion case if feasible:

```text
∂T/∂t = α(∂²T/∂x² + ∂²T/∂y²)
```

Supported case:

```text
heated wall or hot spot diffusion
```

Outputs:

```text
temperature_field.csv
temperature_history.csv
qoi_summary.json
field_summary.json
```

For explicit 2D scheme, check:

```text
Fo_x + Fo_y <= 0.5
```

If 2D is too much, implement a clean 1D-only path and document 2D as next work. But attempt 2D if straightforward.

---

# Deliverable C: Scalar Advection-Diffusion Utilities

## C.1 Purpose

Add a general scalar transport mini kernel useful for:

```text
temperature proxy
concentration proxy
VOF-lite alpha proxy
species diffusion proxy
```

Suggested module:

```text
src/fromcad2cfd_fastcfd/practical_scalar_transport.py
```

---

## C.2 1D Scalar Advection-Diffusion

Equation:

```text
∂φ/∂t + u ∂φ/∂x = D ∂²φ/∂x²
```

Supported v1 method:

```text
upwind advection + explicit diffusion
```

Stability indicators:

```text
CFL = |u| dt / dx
Diffusion number = D dt / dx^2
```

Recommended:

```text
CFL <= 1
Diffusion number <= 0.5
```

Outputs:

```text
scalar_history.csv
scalar_field_final.csv
boundedness_summary.json
qoi_summary.json
```

QoIs:

```text
phi_min
phi_max
phi_mass_initial
phi_mass_final
phi_mass_relative_change
boundedness_violation_count
front_position
```

---

## C.3 Bounded Scalar Mode

Support optional clamping for bounded variables:

```text
bounded_min = 0
bounded_max = 1
```

This is useful for:

```text
VOF-lite alpha
species mass fraction proxy
liquid fraction proxy
```

Compare:

```text
without_clamp
with_clamp
```

Do not claim this is a full VOF solver.

---

# Deliverable D: Material Property Field Utilities

## D.1 Purpose

Add practical material property evaluators and field generators.

Suggested module:

```text
src/fromcad2cfd_fastcfd/practical_material_properties.py
```

---

## D.2 Arrhenius Viscosity Field

Support:

```text
eta(T) = exp(A + B / T)
```

Inputs:

```text
temperature_field
arrhenius_A
arrhenius_B_K
temperature_min_K
temperature_max_K
```

Outputs:

```text
viscosity_field.csv
viscosity_min
viscosity_max
viscosity_ratio
viscosity_gradient_proxy
warnings
```

Use this to make wax H4 more practical, but keep the utility general.

---

## D.3 Constant and Piecewise Property Fields

Support simple models:

```text
constant
linear
piecewise_linear
arrhenius
```

Properties:

```text
viscosity
density
thermal_conductivity
specific_heat
diffusivity
```

Only implement what is safe and straightforward.

---

## D.4 Property Range Checks

Compute:

```text
property_min
property_max
property_ratio
nonfinite_count
negative_value_count
outside_fit_range_count
```

Output:

```text
property_field_summary.json
```

---

# Deliverable E: Bounded Source-Term Toy Model

## E.1 Purpose

Add a simple source-term toy model to test ramping, clamping, and stiffness.

Suggested module:

```text
src/fromcad2cfd_fastcfd/practical_source_terms.py
```

This is not a UDF generator.

This is not Fluent source code.

It is a native numerical toy model.

---

## E.2 Source-Term ODE / Cell Model

Implement a single-cell or 1D source update:

```text
dT/dt = S(T, t) / (rho cp)
```

Support source modes:

```text
constant_source
temperature_window_source
phase_change_interval_source
```

Controls:

```text
ramp_enabled
ramp_time_s
clamp_enabled
source_min
source_max
temperature_min
temperature_max
nan_guard
```

Outputs:

```text
temperature_history.csv
source_history.csv
stability_summary.json
qoi_summary.json
```

Compare:

```text
no_ramp_no_clamp
with_ramp_and_clamp
```

QoIs:

```text
max_temperature
overshoot
source_integral
nonfinite_count
stability_flag
```

---

## E.3 Phase-Change Toy Mode

Implement a simple latent-heat interval source proxy:

```text
source active when T is inside melting interval
```

Do not claim physical completeness.

Use it only to test:

```text
source stiffness
ramp
clamp
time step sensitivity
```

---

# Deliverable F: Parameter Sweep Runner

## F.1 Purpose

Add a generic lightweight sweep runner that can run repeated practical native cases.

Suggested module:

```text
src/fromcad2cfd_fastcfd/practical_sweep.py
```

---

## F.2 Supported Sweeps

Support at least:

```text
time_step_s sweep
cell_size_m sweep
thermal_diffusivity sweep
Arrhenius_B_K sweep
latent_heat sweep
source_strength sweep
velocity sweep for scalar transport
```

---

## F.3 Outputs

Write:

```text
sweep_summary.csv
sweep_manifest.json
risk_map.json
recommended_dt_table.csv
```

Each sweep row should include:

```text
case_id
parameter_values
status
key_qoi
stability_flags
warnings
blocking_errors
```

---

# Deliverable G: Practical Demo Pack CLI

## G.1 Main CLI

Add:

```bash
python -m fromcad2cfd fastcfd practical-native-demo-pack \
  --output-dir sandbox/output/fastfluent_practical_native_demo_pack
```

This should generate:

```text
heat_diffusion_1d
heat_diffusion_2d_or_unavailable
scalar_advection_diffusion_1d
bounded_scalar_transport
arrhenius_viscosity_field
source_term_ramp_clamp
practical_parameter_sweep
wax_application_demo
```

No Fluent execution.

---

## G.2 Expected Output Tree

```text
sandbox/output/fastfluent_practical_native_demo_pack/
├── heat_diffusion_1d/
│   ├── input_case.json
│   ├── temperature_history.csv
│   ├── temperature_field_final.csv
│   ├── qoi_summary.json
│   ├── stability_summary.json
│   └── simulation_summary.md
├── heat_diffusion_2d/
│   ├── input_case.json
│   ├── temperature_field.csv
│   ├── qoi_summary.json
│   └── simulation_summary.md
├── scalar_advection_diffusion_1d/
│   ├── input_case.json
│   ├── scalar_history.csv
│   ├── scalar_field_final.csv
│   ├── qoi_summary.json
│   └── simulation_summary.md
├── bounded_scalar_transport/
│   ├── without_clamp/
│   ├── with_clamp/
│   └── comparison_summary.json
├── arrhenius_viscosity_field/
│   ├── input_case.json
│   ├── viscosity_field.csv
│   ├── property_field_summary.json
│   └── simulation_summary.md
├── source_term_ramp_clamp/
│   ├── no_ramp_no_clamp/
│   ├── with_ramp_and_clamp/
│   └── comparison_summary.json
├── practical_parameter_sweep/
│   ├── sweep_summary.csv
│   ├── sweep_manifest.json
│   ├── risk_map.json
│   └── recommended_dt_table.csv
├── wax_application_demo/
│   ├── input_case.json
│   ├── temperature_history.csv
│   ├── viscosity_field.csv
│   ├── source_history.csv
│   ├── qoi_summary.json
│   └── simulation_summary.md
├── practical_native_manifest.json
└── practical_native_summary.md
```

---

## G.3 Wax Application Demo

Use wax/H4 values as one practical application, not the only purpose.

Demo should combine:

```text
1D heat diffusion
Arrhenius viscosity field
source-term ramp/clamp toy model
time-step sweep
```

Output:

```text
wax_application_demo/simulation_summary.md
```

This summary should explicitly say:

```text
This is a FastFluent-native practical mini simulation.
It does not replace Fluent or ProCAST.
It is intended to screen time step, material-property sensitivity, and source-term stiffness.
```

---

# Deliverable H: Tests

## H.1 Suggested Test Files

Add tests:

```text
tests/unit/test_fastcfd_practical_heat_diffusion.py
tests/unit/test_fastcfd_practical_scalar_transport.py
tests/unit/test_fastcfd_practical_material_properties.py
tests/unit/test_fastcfd_practical_source_terms.py
tests/unit/test_fastcfd_practical_sweep.py
tests/unit/test_fastcfd_practical_native_cli.py
```

Consolidate if repository style prefers fewer files.

---

## H.2 Heat Diffusion Tests

Test:

```text
stable 1D heat diffusion produces finite field
unstable Fo warns or blocks
fixed boundary conditions are applied
temperature remains finite
energy proxy is reported
2D heat diffusion if implemented
```

---

## H.3 Scalar Transport Tests

Test:

```text
CFL calculation
diffusion number calculation
bounded scalar clamp
mass change reported
front position reported
unstable CFL warns or blocks
```

---

## H.4 Material Property Tests

Test:

```text
Arrhenius viscosity calculation
constant property field
piecewise or linear property if implemented
property range checks
nonfinite detection
outside fit range detection if supported
```

---

## H.5 Source-Term Tests

Test:

```text
constant source update
phase-change interval source activation
ramp reduces overshoot or source jump
clamp bounds source or temperature
NaN guard works
source integral reported
```

---

## H.6 Sweep Tests

Test:

```text
time-step sweep writes summary
risk map generated
recommended dt table generated
at least one unstable case is marked warn/block
```

---

## H.7 CLI Tests

Test:

```text
python -m fromcad2cfd fastcfd practical-native-demo-pack --output-dir <tmpdir>
```

Assert:

```text
output directory exists
manifest exists
summary exists
minimum subcase directories exist
CSV outputs exist
JSON summaries exist
no Fluent artifacts are required
```

---

## H.8 Required Test Commands

Run:

```bash
python -m pytest -q
```

Run targeted:

```bash
python -m pytest -q tests -k "practical or heat_diffusion or scalar_transport or material_properties or source_terms or sweep"
```

Document unrelated failures if any.

---

# Deliverable I: Documentation

## I.1 Progress Log

Create:

```text
docs/FASTFLUENT_S2_PRACTICAL_NATIVE_FUNCTION_EXPANSION_PROGRESS_20260623.md
```

Append after checkpoints.

---

## I.2 Delivery Report

Create:

```text
docs/FASTFLUENT_S2_PRACTICAL_NATIVE_FUNCTION_EXPANSION_DELIVERY_20260623.md
```

Must include:

```text
- Goal summary
- Why S2 expands practical FastFluent functions beyond wax
- Files changed
- New modules
- New CLI commands
- Demo pack output
- Test commands and results
- Known limitations
- Explicit statement that Fluent was not launched
- Recommended next goal
```

---

## I.3 Practical Native Summary

Create:

```text
sandbox/output/fastfluent_practical_native_demo_pack/practical_native_summary.md
```

Include:

```text
- Overall result
- Heat diffusion utilities
- Scalar transport utilities
- Material property utilities
- Source-term toy model
- Parameter sweep
- Wax application demo
- What S2 proves
- What S2 does not prove
```

The "does not prove" section must state:

```text
S2 does not prove high-fidelity CFD accuracy.
S2 does not replace Fluent or ProCAST.
S2 validates practical FastFluent-native utilities and artifact generation.
```

---

# Acceptance Criteria

S2 is complete only if all are true:

```text
1. At least four practical native modules or extensions are implemented.
2. 1D heat diffusion demo runs.
3. Scalar advection-diffusion or bounded scalar transport demo runs.
4. Arrhenius viscosity/property field demo runs.
5. Source-term ramp/clamp demo runs.
6. Parameter sweep demo runs.
7. Wax application demo runs as one combined practical case.
8. practical-native-demo-pack CLI exists.
9. practical_native_manifest.json exists.
10. practical_native_summary.md exists.
11. CSV/JSON outputs are generated.
12. Tests pass.
13. Delivery report is written.
14. Delivery report explicitly says Fluent was not launched.
```

Do not mark S2 complete if:

```text
- only wax-specific code is added.
- only reports are generated without running native functions.
- no CSV/JSON outputs exist.
- tests are not run.
- Fluent is launched.
```

---

# Explicit Stop Boundary

After S2, stop.

Do not start Fluent execution in this goal.

Do not implement:

```text
F1 PyFluent template generator
F2 local Fluent execution adapter
UDF lifecycle
OpenFOAM integration
GPU acceleration
```

Recommended next goal depends on project priority:

```text
Option A:
F1 Controlled PyFluent Template Generator
if the team wants to begin the Fluent execution chain.

Option B:
S3 Practical Native Geometry / Boundary Condition Utilities
if the team wants to keep improving FastFluent-native usability before Fluent.
```

Recommended default next goal:

```text
S3 Practical Native Geometry / Boundary Condition Utilities
```

Reason:

```text
The user's intent is to make FastFluent more practically useful, not merely a collection of narrow applications.
S3 should improve geometry-independent setup tools, boundary-condition builders,
field initialization utilities, and case templating for native FastFluent runs.
```

---

# Final Response Format Required From Codex

When finished, respond with:

```text
## FastFluent S2 Practical Native Function Expansion Delivery Summary

### Implemented

### Files changed

### New CLI commands

### Demo pack path

### Practical functions added

### CSV/JSON outputs

### Test results

### Known limitations

### Explicit statement: Fluent was not launched

### Recommended next goal
```

Be precise.

Do not claim Fluent execution.

Do not claim final high-fidelity CFD validation.
