# FastFluent S1 Goal: Native Simulation Validation Pack

Date: 2026-06-23  
Repository: `CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics`  
Execution mode: Codex `/goal` mode  
Recommended save path: `docs/FASTFLUENT_S1_NATIVE_SIMULATION_VALIDATION_PACK_GOAL_20260623.md`

---

## 0. Core Position

This stage is **FastFluent-native simulation validation**.

It must run FastFluent / FastCFD native numerical routes where available.

It must **not** run ANSYS Fluent.

It must **not** call PyFluent.

It must **not** require a Fluent license.

It must **not** modify Fluent case/data files.

The purpose is to move the project beyond:

```text
passport
-> fluent_hints
-> solver_plan_patch.json
```

and prove that FastFluent can also produce:

```text
native simulation result
-> convergence history
-> field output
-> QoI summary
-> simulation manifest
-> simulation summary report
```

This stage should use existing FastFluent / FastCFD numerical backends as much as possible. Do not rewrite a production CFD solver.

---

## 1. Background

H1-H3.5 established the horizontal FastFluent evidence layer:

```text
H1:
  VOF / turbulence / rheology evidence -> solver_plan_patch.json

H2:
  steam-air condensation v2 passport

H3:
  solid-liquid suspension passport

H3.5:
  horizontal validation pack with synthetic passport cases and patch validation
```

Those stages validated setup evidence, model recommendations, and Fluent-facing patch generation.

S1 now validates native simulation capability.

The central question is:

```text
Can FastFluent itself run small, public, reproducible simulation cases and output field-level evidence?
```

This is still not Fluent execution.

---

## 2. Target Workflow

The target S1 workflow is:

```text
native simulation case
-> FastFluent/FastCFD backend run
-> convergence or residual history
-> field output
-> QoI extraction
-> simulation_result.json
-> simulation_summary.md
-> validation manifest
```

For selected cases, connect simulation evidence back to existing passports:

```text
VOF passport
-> VOF-lite alpha transport simulation

turbulence passport
-> turbulence ladder / channel model comparison

rheology passport
-> rheology simulation gap or simple material-property benchmark

steam-air v2 passport
-> heat/mass-transfer simulation gap report

solid-liquid passport
-> particle-model simulation gap report
```

The result should be an honest map of:

```text
which FastFluent passports already have native field-simulation support
which passports are currently setup-evidence only
which numerical routes should be implemented next
```

---

## 3. Hard Boundary

### 3.1 Do Not Do

Do not:

```text
- Do not launch ANSYS Fluent.
- Do not call PyFluent.
- Do not require a Fluent license.
- Do not read or modify Fluent case/data files.
- Do not emit arbitrary Fluent TUI commands.
- Do not emit arbitrary PyFluent commands.
- Do not generate arbitrary UDF source code.
- Do not implement Fluent execution adapter.
- Do not implement OpenFOAM integration.
- Do not implement a production multiphase solver.
- Do not implement a full DPM solver.
- Do not implement DEM coupling.
- Do not implement GPU acceleration in this goal.
- Do not use private CAD, private mesh, or private Fluent data.
```

### 3.2 Must Do

Do:

```text
- Run FastFluent-native or FastCFD-native numerical routes.
- Generate public synthetic simulation cases.
- Export convergence/residual histories where available.
- Export field data where available.
- Extract quantities of interest.
- Generate a simulation manifest.
- Generate a simulation summary report.
- Add tests for simulation outputs and artifact contracts.
- Fail closed if a backend is unavailable.
```

If a backend is not available, record it as unavailable. Do not fake simulation output.

---

## 4. Read First

Inspect the current repository before editing.

Read:

```text
README.md
ROADMAP.md
docs/architecture.md

src/fromcad2cfd_fastcfd/
src/fromcad2cfd_fastcfd/cli.py
src/fromcad2cfd_fastcfd/capabilities.py
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
src/fromcad2cfd_fastcfd/solver_plan_patch.py

src/fromcad2cfd_fastcfd/unstructured/
src/fromcad2cfd_fastcfd/vof.py
src/fromcad2cfd_fastcfd/turbulence.py
src/fromcad2cfd_fastcfd/rheology.py
src/fromcad2cfd_fastcfd/steam_air_condensation.py
src/fromcad2cfd_fastcfd/steam_air_condensation_v2.py
src/fromcad2cfd_fastcfd/solid_liquid_suspension.py

examples/
tests/unit/
tests/
```

Search for existing native backends and runners related to:

```text
cavity2d
channel2d
obstacle2d
Poiseuille
steady incompressible
projection
FVM
unstructured
VOF-lite
alpha transport
k-epsilon
SST
turbulence ladder
VTK
VTU
```

Create a baseline progress log:

```text
docs/FASTFLUENT_S1_NATIVE_SIMULATION_PROGRESS_20260623.md
```

Baseline note must include:

```text
- Existing structured FastFluent backend status.
- Existing unstructured FVM backend status.
- Existing VOF-lite / alpha transport status.
- Existing turbulence ladder status.
- Existing field export status.
- Existing CLI status.
- Initial full test result.
```

---

## 5. Main Deliverables

S1 has eight deliverables:

```text
Deliverable A: Native Simulation Artifact Contract
Deliverable B: Native Simulation Runner / Registry
Deliverable C: Structured Backend Simulation Cases
Deliverable D: Unstructured FVM Simulation Cases
Deliverable E: Passport-Simulation Alignment Reports
Deliverable F: CLI Integration
Deliverable G: Tests
Deliverable H: Documentation and Delivery Report
```

---

# Deliverable A: Native Simulation Artifact Contract

## A.1 Purpose

Define a consistent artifact contract for FastFluent-native simulation runs.

Suggested module:

```text
src/fromcad2cfd_fastcfd/native_simulation_artifacts.py
```

If an existing artifact contract exists, reuse it and extend minimally.

---

## A.2 Simulation Result Schema

Use schema version:

```text
fromcad2cfd_fastfluent_native_simulation_result_v1
```

Each case should generate:

```text
simulation_result.json
```

Top-level fields:

```text
schema_version
case_id
case_name
module
backend
backend_status
status
input_summary
runtime_summary
mesh_summary
numerics_summary
convergence_summary
qoi_summary
field_outputs
warnings
blocking_errors
limitations
metadata
```

Allowed status values:

```text
pass
warn
block
unavailable
```

Allowed backend_status values:

```text
available
unavailable
failed
skipped
```

---

## A.3 Runtime Summary

Include where available:

```text
start_time
end_time
elapsed_s
iteration_count
time_step_count
final_residual
residual_drop
exit_reason
```

If unavailable, record:

```text
not_available
```

Do not fabricate values.

---

## A.4 Mesh Summary

Include where available:

```text
mesh_type
dimension
cell_count
node_count
face_count
min_cell_size
max_cell_size
mesh_quality_summary
boundary_zone_summary
```

---

## A.5 Convergence Summary

Include where available:

```text
residual_history_path
final_residuals
residual_drop_orders
steady_or_transient
converged
convergence_warnings
```

Output residual/convergence history as:

```text
convergence_history.csv
```

or the closest existing format.

---

## A.6 QoI Summary

Each case should include relevant quantities of interest.

Examples:

```text
max_velocity
mean_velocity
pressure_drop_proxy
mass_balance_proxy
divergence_norm
l2_error
max_error
alpha_min
alpha_max
alpha_mass
eddy_viscosity_min
eddy_viscosity_max
wall_y_plus_proxy
wake_indicator
recirculation_proxy
```

Do not require all QoIs for all cases.

---

## A.7 Field Outputs

Record field output files:

```text
field_output.vtu
field_output.vtk
field_output.csv
field_summary.json
```

At least three S1 cases should produce field output.

If the backend cannot produce field output, record that limitation.

---

# Deliverable B: Native Simulation Runner / Registry

## B.1 Purpose

Create a registry-driven S1 runner that can execute public native simulation cases.

Suggested module:

```text
src/fromcad2cfd_fastcfd/native_simulation_pack.py
```

Suggested functions:

```python
create_native_simulation_case_registry() -> list[dict]
run_native_simulation_case(case_spec: dict, output_dir: Path) -> dict
run_native_simulation_validation_pack(output_dir: Path) -> dict
write_simulation_manifest(result: dict, path: Path) -> None
write_simulation_summary(result: dict, path: Path) -> None
```

The runner should use existing backends where possible.

Do not implement a large new solver.

---

## B.2 Backend Availability

Each backend must be checked before use.

Examples:

```text
structured_cpp_backend_available
unstructured_fvm_backend_available
vof_lite_backend_available
turbulence_ladder_available
```

If a backend is unavailable:

```text
- mark affected case status as unavailable
- write a clear reason
- do not fake result files
- continue remaining cases where possible
```

---

## B.3 Minimum Actual Simulation Requirement

S1 is not complete unless at least five native simulation cases actually run.

Prefer these as minimum actual cases:

```text
1. unstructured Poiseuille channel
2. steady incompressible channel
3. obstacle-channel evidence
4. VOF-lite alpha transport
5. turbulence ladder or structured channel/cavity
```

If fewer than five can run due to missing backends, do not mark the goal complete. Instead, document blockers.

---

# Deliverable C: Structured Backend Simulation Cases

## C.1 Purpose

Validate structured FastFluent backend capability if available.

Potential cases:

```text
cavity2d
channel2d
obstacle2d
```

If structured C++ backend is unavailable, record status and continue with unstructured cases.

---

## C.2 Case S1-A1: Cavity2D Reynolds Sweep

Directory:

```text
structured_cases/cavity2d_re_sweep/
```

Suggested subcases:

```text
Re_low
Re_mid
Re_high
```

Expected outputs:

```text
simulation_result.json
convergence_history.csv
field_summary.json
simulation_summary.md
field_output if available
```

QoIs:

```text
max_velocity
mean_velocity
center_velocity_proxy
vortex_strength_proxy
residual_drop
```

Validation:

```text
- results are finite
- residual history exists if backend supports it
- Re sweep produces distinguishable QoI trends
```

---

## C.3 Case S1-A2: Channel2D Velocity / Grid Sweep

Directory:

```text
structured_cases/channel2d_velocity_grid_sweep/
```

Suggested variables:

```text
velocity: low / base / high
grid: coarse / medium / fine
```

QoIs:

```text
mean_velocity
max_velocity
pressure_drop_proxy
mass_balance_proxy
grid_sensitivity_metric
```

Validation:

```text
- velocity trend is monotonic where expected
- grid changes produce finite output
- summary table is generated
```

---

## C.4 Case S1-A3: Obstacle2D Shape Comparison

Directory:

```text
structured_cases/obstacle2d_shape_comparison/
```

Suggested subcases:

```text
circle obstacle
rectangle obstacle
small blockage
medium blockage
```

QoIs:

```text
wake_indicator
recirculation_proxy
max_velocity
pressure_drop_proxy
```

Validation:

```text
- obstacle shape changes flow fingerprint
- field output or field summary exists
```

---

# Deliverable D: Unstructured FVM Simulation Cases

These should be prioritized because they are usually easier to run in public CI and do not require a compiled C++ backend.

---

## D.1 Case S1-B1: Poiseuille Channel Convergence

Directory:

```text
unstructured_cases/poiseuille_channel_convergence/
```

Purpose:

```text
Validate unstructured FVM with a channel-flow benchmark.
```

Suggested subcases:

```text
coarse
medium
fine
```

Expected outputs:

```text
simulation_result.json
convergence_history.csv
field_output.vtu
error_summary.json
simulation_summary.md
```

QoIs:

```text
l2_error
max_error
centerline_velocity_error
residual_drop
cell_count
```

Validation:

```text
- L2 error is finite.
- mesh refinement does not make the solution obviously worse without warning.
- field output exists.
```

If there is an existing analytical Poiseuille comparison, use it.

---

## D.2 Case S1-B2: Steady Incompressible Channel

Directory:

```text
unstructured_cases/steady_incompressible_channel/
```

Purpose:

```text
Validate steady incompressible solver route.
```

Expected outputs:

```text
velocity field
pressure field
residual history
divergence metric
mass balance proxy
VTU output if available
```

QoIs:

```text
divergence_norm
mass_balance_proxy
max_velocity
mean_velocity
pressure_drop_proxy
```

Validation:

```text
- divergence metric is finite.
- mass balance proxy exists.
- field output exists if supported.
```

---

## D.3 Case S1-B3: Obstacle-Channel Evidence

Directory:

```text
unstructured_cases/obstacle_channel_evidence/
```

Purpose:

```text
Validate nontrivial unstructured geometry route.
```

Expected outputs:

```text
mesh summary
velocity field
pressure field
wake proxy
obstacle metadata
VTU output if available
```

QoIs:

```text
wake_indicator
max_velocity
pressure_drop_proxy
recirculation_proxy if available
```

Validation:

```text
- obstacle metadata is recorded.
- output is finite.
- field output or field summary exists.
```

---

## D.4 Case S1-B4: VOF-Lite Alpha Transport

Directory:

```text
unstructured_cases/vof_lite_alpha_transport/
```

Purpose:

```text
Validate bounded scalar/alpha transport as lightweight VOF evidence.
```

Expected outputs:

```text
alpha field
alpha_min_max_history.csv
alpha_mass_history.csv
field_output.vtu
simulation_result.json
```

QoIs:

```text
alpha_min
alpha_max
alpha_mass_initial
alpha_mass_final
alpha_mass_relative_change
boundedness_violation_count
```

Validation:

```text
- alpha stays within [0, 1] or violations are explicitly reported.
- alpha mass change is reported.
- high-CFL case triggers warning if included.
```

This case should connect back to VOF passport evidence.

---

## D.5 Case S1-B5: Turbulence Ladder

Directory:

```text
unstructured_cases/turbulence_ladder/
```

Purpose:

```text
Validate available turbulence evidence route.
```

Potential models:

```text
laminar
algebraic eddy viscosity
k-epsilon if available
SST if available
```

Expected outputs:

```text
model_comparison_summary.json
velocity_profile_summary.json
eddy_viscosity_summary.json
simulation_result.json
```

QoIs:

```text
eddy_viscosity_min
eddy_viscosity_max
wall_y_plus_proxy
velocity_profile_deviation
residual_drop
```

Validation:

```text
- at least two turbulence/closure modes are compared if available.
- if only one mode exists, mark limitation.
- no overclaiming of turbulence validation.
```

---

# Deliverable E: Passport-Simulation Alignment Reports

## E.1 Purpose

Connect H1-H3.5 passport evidence to S1 native simulation cases.

Create directory:

```text
passport_simulation_alignment/
```

Reports:

```text
vof_passport_vs_vof_lite.md
turbulence_passport_vs_turbulence_ladder.md
rheology_passport_simulation_gap.md
steam_air_v2_simulation_gap.md
solid_liquid_passport_simulation_gap.md
```

---

## E.2 VOF Alignment

File:

```text
passport_simulation_alignment/vof_passport_vs_vof_lite.md
```

Include:

```text
- VOF passport evidence used.
- VOF-lite simulation case used.
- Which quantities align.
- alpha boundedness results.
- limitations.
```

---

## E.3 Turbulence Alignment

File:

```text
passport_simulation_alignment/turbulence_passport_vs_turbulence_ladder.md
```

Include:

```text
- turbulence passport recommendation.
- turbulence ladder case results.
- y+ / eddy-viscosity / velocity-profile evidence.
- limitations.
```

---

## E.4 Rheology Gap Report

File:

```text
passport_simulation_alignment/rheology_passport_simulation_gap.md
```

If no native rheology field simulation exists, state:

```text
Rheology currently has setup-evidence support but no native field-simulation route in S1.
```

Recommend next:

```text
temperature-dependent viscosity channel benchmark
non-Newtonian channel benchmark
```

---

## E.5 Steam-Air v2 Gap Report

File:

```text
passport_simulation_alignment/steam_air_v2_simulation_gap.md
```

State honestly if no full steam-air condensation field simulation exists.

Recommend next:

```text
scalar heat diffusion case
1D/2D heat-transfer mini benchmark
species diffusion mini benchmark
near-wall source-term toy benchmark
```

---

## E.6 Solid-Liquid Gap Report

File:

```text
passport_simulation_alignment/solid_liquid_passport_simulation_gap.md
```

State honestly if no native DPM/Mixture/Eulerian simulation exists.

Recommend next:

```text
settling ODE benchmark
passive particle relaxation benchmark
1D concentration settling toy model
```

Do not pretend a full solid-liquid solver exists.

---

# Deliverable F: CLI Integration

## F.1 Main CLI Command

Add:

```bash
python -m fromcad2cfd fastcfd native-simulation-validation-pack-demo \
  --output-dir sandbox/output/fastfluent_native_simulation_validation_pack
```

This command should:

```text
1. check backend availability
2. run available native simulation cases
3. write case outputs
4. write simulation_manifest.json
5. write simulation_summary.md
6. write alignment reports
```

---

## F.2 Optional Subcommands

Add only if easy and consistent with project CLI style:

```bash
python -m fromcad2cfd fastcfd run-structured-native-pack \
  --output-dir sandbox/output/fastfluent_native_simulation_validation_pack/structured_cases

python -m fromcad2cfd fastcfd run-unstructured-native-pack \
  --output-dir sandbox/output/fastfluent_native_simulation_validation_pack/unstructured_cases
```

---

## F.3 Capabilities Output

Update capabilities to include:

```text
native_simulation_validation_pack
structured_fastfluent_backend_status
unstructured_fvm_simulation_pack
vof_lite_alpha_transport_simulation
turbulence_ladder_simulation
passport_simulation_alignment
```

Do not claim Fluent execution.

---

# Deliverable G: Tests

## G.1 Suggested Test Files

Add tests consistent with repository style:

```text
tests/unit/test_fastcfd_native_simulation_artifacts.py
tests/unit/test_fastcfd_native_simulation_pack.py
tests/unit/test_fastcfd_native_simulation_cli.py
```

If repository style prefers fewer files, consolidate.

---

## G.2 Artifact Contract Tests

Test:

```text
- simulation_result.json schema contains required top-level fields.
- unavailable backend result is recorded correctly.
- field_outputs list is valid.
- qoi_summary is a dictionary.
- warnings/blocking_errors are lists.
```

---

## G.3 Native Pack Tests

Test:

```text
- native simulation case registry is non-empty.
- at least five runnable or expected simulation cases are registered.
- run_native_simulation_validation_pack writes simulation_manifest.json.
- run_native_simulation_validation_pack writes simulation_summary.md.
- unavailable backends do not crash the full pack.
```

---

## G.4 Simulation Output Tests

Where available, test:

```text
- Poiseuille case produces finite error metrics.
- steady channel produces finite velocity or divergence metrics.
- VOF-lite produces alpha_min and alpha_max.
- turbulence ladder produces model comparison summary.
```

Only test outputs supported by existing backend.

---

## G.5 CLI Tests

Test:

```text
python -m fromcad2cfd fastcfd native-simulation-validation-pack-demo --output-dir <tmpdir>
```

Assert:

```text
- command exits successfully or fails with documented backend blocker.
- output directory exists.
- simulation_manifest.json exists.
- simulation_summary.md exists.
- at least five actual simulation cases run, unless test is intentionally checking unavailable mode.
```

---

## G.6 Required Test Commands

Run:

```bash
python -m pytest -q
```

Run targeted tests:

```bash
python -m pytest -q tests -k "native_simulation or unstructured or vof_lite or turbulence_ladder or poiseuille"
```

If unrelated pre-existing failures occur, document:

```text
- failing test name
- failure message
- why unrelated
- whether new tests passed
```

---

# Deliverable H: Documentation

## H.1 Progress Log

Create:

```text
docs/FASTFLUENT_S1_NATIVE_SIMULATION_PROGRESS_20260623.md
```

Append after each checkpoint:

```text
## Checkpoint N - <timestamp>

### Files changed

### Commands run

### Results

### Issues found

### Next action
```

---

## H.2 Delivery Report

Create:

```text
docs/FASTFLUENT_S1_NATIVE_SIMULATION_DELIVERY_20260623.md
```

It must include:

```text
- Goal summary.
- Why S1 validates FastFluent without Fluent execution.
- Files changed.
- New modules.
- New CLI commands.
- Backends detected.
- Simulation cases run.
- Cases unavailable and reasons.
- Field outputs generated.
- QoIs generated.
- Test commands and results.
- Known limitations.
- Explicit statement that Fluent was not launched.
- Recommended next goal.
```

---

## H.3 Simulation Summary

Create:

```text
sandbox/output/fastfluent_native_simulation_validation_pack/simulation_summary.md
```

Include:

```text
- Overall S1 status.
- Structured backend summary.
- Unstructured backend summary.
- VOF-lite summary.
- Turbulence ladder summary.
- Field output summary.
- QoI summary.
- Passport-simulation alignment summary.
- What S1 proves.
- What S1 does not prove.
```

The "does not prove" section must state:

```text
S1 does not prove high-fidelity Fluent accuracy.
S1 validates FastFluent-native simulation routes and artifact generation.
S1 does not replace ANSYS Fluent for final engineering validation.
```

---

# Output Directory

Expected output directory:

```text
sandbox/output/fastfluent_native_simulation_validation_pack/
```

Expected tree:

```text
fastfluent_native_simulation_validation_pack/
├── structured_cases/
│   ├── cavity2d_re_sweep/
│   ├── channel2d_velocity_grid_sweep/
│   └── obstacle2d_shape_comparison/
├── unstructured_cases/
│   ├── poiseuille_channel_convergence/
│   ├── steady_incompressible_channel/
│   ├── obstacle_channel_evidence/
│   ├── vof_lite_alpha_transport/
│   └── turbulence_ladder/
├── passport_simulation_alignment/
│   ├── vof_passport_vs_vof_lite.md
│   ├── turbulence_passport_vs_turbulence_ladder.md
│   ├── rheology_passport_simulation_gap.md
│   ├── steam_air_v2_simulation_gap.md
│   └── solid_liquid_passport_simulation_gap.md
├── simulation_manifest.json
├── simulation_summary.md
└── limitations.md
```

It is acceptable for some structured case directories to contain `backend_unavailable.md` if the backend is unavailable, but the goal is not complete unless at least five actual native simulation cases run somewhere in the pack.

---

# Acceptance Criteria

S1 is complete only if all are true:

```text
1. Native simulation artifact contract exists.
2. Native simulation pack runner exists.
3. CLI command native-simulation-validation-pack-demo exists.
4. At least five FastFluent-native simulation cases actually run.
5. simulation_manifest.json is generated.
6. simulation_summary.md is generated.
7. At least three cases generate field output or field summaries.
8. At least one case includes convergence/residual history.
9. At least one case includes mesh/grid sensitivity or convergence comparison.
10. At least one case includes model comparison or closure comparison.
11. Passport-simulation alignment reports are generated.
12. Tests pass.
13. Delivery report is written.
14. Delivery report explicitly states Fluent was not launched.
```

Do not mark S1 complete if:

```text
- only passport/hint/patch artifacts are generated.
- no native simulation case actually runs.
- no field output or field summary exists.
- no convergence or residual history exists.
- tests are not run.
- Fluent is launched.
```

---

# Explicit Stop Boundary

After S1, stop.

Do not start H4 inside this goal.

Do not implement:

```text
H4 wax rheology / phase-change passport
S2 wax simulation pack
Fluent execution adapter
PyFluent template generator
UDF lifecycle
OpenFOAM integration
GPU acceleration
```

Recommended next goal:

```text
H4: Wax Rheology / Phase-Change Passport
```

Reason:

```text
After S1 proves native FastFluent simulation routes, H4 should connect measured wax material characterization,
Arrhenius viscosity, thermal softening, and phase-change readiness to FastFluent evidence and downstream Fluent setup.
```

---

# Final Response Format Required From Codex

When finished, respond with:

```text
## FastFluent S1 Native Simulation Delivery Summary

### Implemented

### Files changed

### New CLI commands

### Backends detected

### Simulation cases run

### Field outputs

### QoI outputs

### Passport-simulation alignment reports

### Test results

### Known limitations

### Explicit statement: Fluent was not launched

### Recommended next goal
```

Be precise.

Do not claim Fluent execution.

Do not claim high-fidelity CFD validation.

Do not claim final Fluent accuracy.
