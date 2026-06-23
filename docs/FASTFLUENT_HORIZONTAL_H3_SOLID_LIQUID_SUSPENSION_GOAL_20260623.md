# FastFluent Horizontal H3 Goal: Solid-Liquid Suspension Passport

Date: 2026-06-23  
Repository: `CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics`  
Execution mode: Codex `/goal` mode  
Recommended save path: `docs/FASTFLUENT_HORIZONTAL_H3_SOLID_LIQUID_SUSPENSION_GOAL_20260623.md`

---

## 0. Core Answer: Are We Modifying Fluent In This Stage?

No.

This H3 stage should **not** modify ANSYS Fluent itself, should **not** launch Fluent, and should **not** generate executable PyFluent or UDF code.

This stage should create new project code inside FastFluent / FastCFD:

```text
src/fromcad2cfd_fastcfd/solid_liquid_suspension.py
```

and extend the existing Fluent-facing handoff layer:

```text
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
src/fromcad2cfd_fastcfd/cli.py
src/fromcad2cfd_fastcfd/capabilities.py
```

The output should remain a planning artifact:

```text
solid_liquid_suspension_passport.json
solid_liquid_suspension_fluent_hints.json
solver_plan_patch.json
report.md
```

The purpose is to let FastFluent recommend whether downstream Fluent should use:

```text
DPM
Mixture model
Eulerian multiphase
Eulerian granular review
```

based on explicit, low-cost physical evidence.

This is still a FastFluent physics expansion stage, not a Fluent execution stage.

---

## 1. H3 Objective

Implement a new FastFluent physics passport for solid-liquid suspension readiness.

The target workflow is:

```text
solid-liquid synthetic case
-> solid-liquid suspension passport
-> Fluent setup hints
-> solver_plan_patch.json
-> Markdown report
-> public demo
-> tests
```

This module should estimate particle-flow regime, sedimentation tendency, coupling strength, and model suitability before expensive Fluent setup.

The module should answer:

```text
Are particles dilute or dense?
Do particles follow the liquid flow?
Is settling important?
Is one-way DPM enough?
Is two-way coupled DPM needed?
Is Mixture model more suitable?
Is Eulerian multiphase review required?
Are particle time scales too stiff for the proposed time step?
Which monitors should Fluent track?
```

---

## 2. Strategic Context

Previous milestones:

```text
H0: FastFluent evidence-to-Fluent handoff
H1: Existing VOF / turbulence / rheology passport patch compiler expansion
H2: Steam-air condensation v2
```

H3 now enters the main project title direction:

```text
Solid-Liquid Two-Phase Flow Dynamics
```

This passport should become one of the central open-source examples in the repository.

It should not be framed as a full multiphase solver.

It should be framed as:

```text
a solid-liquid setup-readiness and Fluent model-selection evidence engine
```

---

## 3. Hard Scope Boundary

### 3.1 Implement

Implement:

```text
1. Solid-liquid suspension case schema.
2. Solid-liquid suspension passport schema.
3. Solid-liquid Fluent hints schema.
4. Physical regime calculations.
5. Fluent model recommendation logic.
6. solver_plan_patch.json compiler support.
7. Public demo artifacts.
8. CLI commands.
9. Unit tests.
10. Documentation.
```

### 3.2 Do Not Implement

Do not implement:

```text
- Fluent execution.
- PyFluent execution.
- Fluent TUI execution.
- Fluent case/data editing.
- Arbitrary UDF generation.
- Particle tracking solver.
- CFD-resolved particle motion.
- DEM coupling.
- Dense granular solver.
- OpenFOAM integration.
- GPU acceleration.
- Full Eulerian multiphase solver.
- Full Lagrangian DPM trajectory integrator.
```

This passport is a readiness gate and setup evidence generator.

---

## 4. Read First

Inspect current modules:

```text
README.md
ROADMAP.md
docs/architecture.md

src/fromcad2cfd_fastcfd/
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
src/fromcad2cfd_fastcfd/solver_plan_patch.py
src/fromcad2cfd_fastcfd/cli.py
src/fromcad2cfd_fastcfd/capabilities.py

src/fromcad2cfd_fastcfd/vof.py
src/fromcad2cfd_fastcfd/turbulence.py
src/fromcad2cfd_fastcfd/rheology.py
src/fromcad2cfd_fastcfd/steam_air_condensation.py
src/fromcad2cfd_fastcfd/steam_air_condensation_v2.py  # if exists

tests/unit/
```

If Fluent Solver Plan v2 receiver exists, inspect:

```text
src/fromcad2cfd_fluent_solver/solver_plan_v2.py
src/fromcad2cfd_fluent_solver/patch_preview.py
```

Append baseline status to:

```text
docs/FASTFLUENT_HORIZONTAL_H3_PROGRESS_20260623.md
```

Baseline note must include:

```text
- Existing solver_plan_patch contract status.
- Existing patch compiler status.
- Existing CLI pattern.
- Existing FastFluent passport style.
- Existing tests relevant to H1/H2.
- Initial test result.
```

---

# Deliverable A: Solid-Liquid Suspension Schemas

## A.1 Suggested Module

Create:

```text
src/fromcad2cfd_fastcfd/solid_liquid_suspension.py
```

If project style prefers multiple small modules, only split if necessary. Avoid unnecessary file sprawl.

---

## A.2 Schema Versions

Use:

```text
fromcad2cfd_fastfluent_solid_liquid_suspension_case_v1
fromcad2cfd_fastfluent_solid_liquid_suspension_passport_v1
fromcad2cfd_fastfluent_solid_liquid_suspension_fluent_hints_v1
```

---

## A.3 Input Case Fields

The input case should contain:

```text
schema_version
case_name

fluid_density_kg_m3
fluid_dynamic_viscosity_Pa_s
fluid_kinematic_viscosity_m2_s optional

particle_density_kg_m3
particle_diameter_m
particle_sphericity optional

solid_volume_fraction
reference_velocity_m_s
relative_velocity_m_s optional
length_scale_m
domain_height_m optional
gravity_m_s2
cell_size_m
time_step_s

coupling_preference optional
domain_orientation optional
units
metadata
```

Recommended optional fields:

```text
particle_size_distribution
wall_interaction_relevance
erosion_or_impact_relevance
thermal_coupling_relevance
```

Do not require optional fields for the v1 demo.

---

## A.4 Validation Rules

Validate:

```text
fluid_density_kg_m3 > 0
fluid_dynamic_viscosity_Pa_s > 0
particle_density_kg_m3 > 0
particle_diameter_m > 0
0 <= solid_volume_fraction <= 0.64
reference_velocity_m_s >= 0
length_scale_m > 0
gravity_m_s2 >= 0
cell_size_m > 0
time_step_s > 0
```

If `relative_velocity_m_s` is absent, use a conservative estimate:

```text
relative_velocity_m_s = max(reference_velocity_m_s, settling_velocity_estimate)
```

but explicitly record that it is estimated.

Reject dangerous keys recursively:

```text
shell
command
cmd
executable
subprocess
python
python_code
source_code
cpp_code
c_code
udf_code
delete
remove_file
raw_tui
raw_pyfluent
journal
system
eval
exec
```

---

# Deliverable B: Core Physical Calculations

## B.1 Particle Reynolds Number

Compute:

```text
Re_p = rho_f * U_rel * d_p / mu_f
```

Classification:

```text
Re_p < 1:
  Stokes drag regime

1 <= Re_p < 1000:
  transitional particle drag regime

Re_p >= 1000:
  inertial / high-Re particle drag regime
```

Output:

```text
particle_reynolds_number
particle_drag_regime
```

---

## B.2 Particle Relaxation Time

For low-Re first-pass estimate:

```text
tau_p = rho_p * d_p^2 / (18 * mu_f)
```

If particle Reynolds number is not in Stokes regime, still output the Stokes estimate but mark:

```text
drag_correction_review_required = true
```

Optional correction:

```text
Schiller-Naumann correction:
C_D = 24/Re_p * (1 + 0.15 * Re_p^0.687) for Re_p < 1000
```

Do not overcomplicate if existing project style favors minimal implementation.

Output:

```text
particle_relaxation_time_s
drag_correction_review_required
```

---

## B.3 Stokes Number

Compute:

```text
Stk = tau_p * U / L
```

Classification:

```text
Stk < 0.1:
  particles strongly follow fluid

0.1 <= Stk < 1:
  moderate particle inertia

Stk >= 1:
  strong particle inertia / trajectory decoupling
```

Output:

```text
stokes_number
particle_inertia_regime
```

---

## B.4 Settling Velocity

First-pass Stokes settling velocity:

```text
v_settle_stokes = (rho_p - rho_f) * g * d_p^2 / (18 * mu_f)
```

If `rho_p <= rho_f`, settling tendency should be zero or buoyant/rising depending on sign.

Output:

```text
settling_velocity_m_s
settling_direction
settling_regime_note
```

Classification:

```text
v_settle / U < 0.01:
  negligible settling

0.01 <= v_settle / U < 0.1:
  moderate settling

v_settle / U >= 0.1:
  strong settling
```

---

## B.5 Residence Time vs Settling Time

Compute:

```text
residence_time_s = length_scale_m / max(reference_velocity_m_s, tiny)
settling_time_s = domain_height_m / max(abs(settling_velocity_m_s), tiny)
settling_importance_ratio = residence_time_s / settling_time_s
```

Interpretation:

```text
ratio < 0.1:
  settling weak over residence time

0.1 <= ratio < 1:
  settling may be relevant

ratio >= 1:
  settling likely important
```

If domain_height_m is absent, set it equal to length_scale_m and record limitation.

---

## B.6 Solid Volume Fraction Regime

Classify:

```text
alpha_s < 1e-3:
  trace / very dilute

1e-3 <= alpha_s < 1e-2:
  dilute

1e-2 <= alpha_s < 0.1:
  moderate

0.1 <= alpha_s < 0.3:
  dense

alpha_s >= 0.3:
  very dense / granular review required
```

Output:

```text
solid_volume_fraction_regime
```

---

## B.7 Particle Loading Ratio

Estimate mass loading:

```text
mass_loading = alpha_s * rho_p / max((1 - alpha_s) * rho_f, tiny)
```

Classification:

```text
mass_loading < 0.1:
  one-way coupling may be acceptable

0.1 <= mass_loading < 1:
  two-way coupling likely relevant

mass_loading >= 1:
  strong two-way or four-way coupling review required
```

Output:

```text
particle_mass_loading
coupling_strength_regime
```

---

## B.8 Cell-Particle Size Ratio

Compute:

```text
cell_particle_ratio = cell_size_m / particle_diameter_m
```

Interpretation:

```text
cell_particle_ratio >> 1:
  particle is sub-grid; DPM or Eulerian model may be appropriate

cell_particle_ratio ~ 1:
  cell size comparable to particle; resolved or near-resolved issue, review required

cell_particle_ratio < 1:
  particle larger than cell; model setup likely inconsistent
```

Output:

```text
cell_particle_ratio
particle_resolution_warning
```

---

## B.9 Particle Time-Step Ratio

Compute:

```text
particle_time_step_ratio = time_step_s / max(tau_p, tiny)
```

Interpretation:

```text
ratio < 0.1:
  particle relaxation resolved

0.1 <= ratio < 1:
  marginal

ratio >= 1:
  particle relaxation under-resolved
```

Output:

```text
particle_time_step_risk
```

---

# Deliverable C: Fluent Model Recommendation Logic

## C.1 Supported Recommendations

Output one of:

```text
dpm_one_way
dpm_two_way
mixture_model
eulerian_multiphase_review
eulerian_granular_review
review_required
```

---

## C.2 Suggested Decision Logic

Use conservative first-pass logic.

### DPM one-way

Recommend if:

```text
solid_volume_fraction < 1e-3
mass_loading < 0.1
Stk not extremely high
cell_particle_ratio sufficiently large
```

### DPM two-way

Recommend if:

```text
solid_volume_fraction < 1e-2
0.1 <= mass_loading < 1
particles remain sub-grid
```

### Mixture model

Recommend if:

```text
1e-2 <= solid_volume_fraction < 0.1
Stk < 1
settling not dominant or moderate
```

### Eulerian multiphase review

Recommend if:

```text
solid_volume_fraction >= 0.1
or mass_loading >= 1
or strong phase coupling expected
```

### Eulerian granular review

Recommend if:

```text
solid_volume_fraction >= 0.3
```

### Review required

Use if:

```text
conflicting indicators exist
missing critical inputs
cell_particle_ratio inconsistent
particle_time_step_risk high
```

---

## C.3 Required Warnings

Generate warnings for:

```text
high particle Reynolds number
non-Stokes drag regime
large Stokes number
strong settling
high mass loading
dense concentration
particle larger than or comparable to cell size
time step too large relative to particle relaxation
uncertain model recommendation
```

---

# Deliverable D: Fluent Hints

Generate:

```text
solid_liquid_suspension_fluent_hints.json
```

Top-level fields:

```text
schema_version
case_name
status
recommended_model
recommended_physics
recommended_materials
recommended_numerics
recommended_transient_controls
recommended_monitors
recommended_postprocessing
warnings
blocking_errors
limitations
metadata
```

## D.1 Recommended Physics

Possible outputs:

```json
{
  "multiphase": true,
  "recommended_model": "dpm_one_way",
  "continuous_phase": "liquid",
  "dispersed_phase": "solid_particles",
  "gravity": true,
  "particle_wall_interaction_review_required": true
}
```

## D.2 Recommended Monitors

Include:

```text
solid_volume_fraction_bounds
particle_mass_balance
continuous_phase_mass_balance
particle_residence_time
particle_velocity_range
settling_indicator
pressure_drop
wall_impact_if_available
erosion_indicator_if_relevant
```

## D.3 Recommended Numerics

Include:

```text
first_order_warmup
bounded volume fraction
time step limited by particle relaxation if transient
frequent checkpoint during first-pass run
```

---

# Deliverable E: Solver Plan Patch Integration

Extend:

```text
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
```

to support:

```text
fromcad2cfd_fastfluent_solid_liquid_suspension_passport_v1
```

## E.1 Patch Operations

Generate patches where evidence supports them:

```text
/physics/multiphase/enabled = true
/physics/multiphase/model = <recommended_model>
/physics/gravity/enabled = true
/materials/phases/continuous = "liquid"
/materials/phases/dispersed = "solid_particles"
/monitors/global += solid_volume_fraction_bounds
/monitors/global += particle_mass_balance
/monitors/global += continuous_phase_mass_balance
/monitors/global += particle_velocity_range
/monitors/global += settling_indicator
/monitors/wall += particle_wall_impact_if_available
/transient/initial_time_step_s = <recommended_dt if available>
/postprocessing/required_outputs += particle_phase_summary
/acceptance_criteria/bounded_solid_volume_fraction = true
/acceptance_criteria/particle_mass_balance_required = true
```

If the recommended model is `review_required`, use:

```text
/physics/multiphase/model = "review-required"
```

Do not overclaim.

---

## E.2 Evidence IDs

Suggested evidence IDs:

```text
solid_liquid_particle_reynolds
solid_liquid_stokes_number
solid_liquid_settling_velocity
solid_liquid_volume_fraction_regime
solid_liquid_mass_loading
solid_liquid_cell_particle_ratio
solid_liquid_time_step_ratio
solid_liquid_model_recommendation
solid_liquid_monitor_requirements
```

Every patch must include evidence refs.

---

## E.3 Patch Validation

Generated `solver_plan_patch.json` must pass the existing validator.

Do not weaken the validator.

If a desired patch path is not allowed, either:

```text
1. use the closest existing allowed path; or
2. add a minimal safe allowed path only if consistent with the existing patch contract.
```

Do not add broad unsafe path permissions.

---

# Deliverable F: CLI Integration

Extend FastCFD CLI.

Preferred commands:

```bash
python -m fromcad2cfd fastcfd write-solid-liquid-demo \
  --output-dir sandbox/output/solid_liquid_suspension_demo
```

Writes:

```text
solid_liquid_suspension_case.json
```

---

```bash
python -m fromcad2cfd fastcfd validate-solid-liquid-suspension \
  --case sandbox/output/solid_liquid_suspension_demo/solid_liquid_suspension_case.json \
  --output-dir sandbox/output/solid_liquid_suspension_demo/passport
```

Writes:

```text
solid_liquid_suspension_passport.json
solid_liquid_suspension_fluent_hints.json
solid_liquid_suspension_report.md
```

---

```bash
python -m fromcad2cfd fastcfd solid-liquid-handoff-demo \
  --output-dir sandbox/output/solid_liquid_suspension_demo
```

Runs the full chain:

```text
case -> passport -> hints -> solver_plan_patch.json -> report
```

If `compile-fluent-patch` already supports auto-detection, make sure it supports the new solid-liquid passport.

---

# Deliverable G: Public Demo

Create public synthetic demo:

```text
sandbox/output/solid_liquid_suspension_demo/
```

Expected artifacts:

```text
sandbox/output/solid_liquid_suspension_demo/
├── solid_liquid_suspension_case.json
├── passport/
│   ├── solid_liquid_suspension_passport.json
│   ├── solid_liquid_suspension_fluent_hints.json
│   └── solid_liquid_suspension_report.md
├── solver_plan_patch.json
└── solver_plan_patch_report.md
```

Use a public synthetic case only.

Suggested demo case:

```text
water + silica particles
fluid_density_kg_m3 = 998
fluid_dynamic_viscosity_Pa_s = 0.001
particle_density_kg_m3 = 2650
particle_diameter_m = 50e-6
solid_volume_fraction = 0.005
reference_velocity_m_s = 0.5
length_scale_m = 0.05
domain_height_m = 0.02
gravity_m_s2 = 9.81
cell_size_m = 1e-3
time_step_s = 1e-4
```

This should likely produce:

```text
dilute or moderate suspension
DPM two-way or mixture-model review depending thresholds
settling warning if relevant
particle time-scale warning if relevant
```

Do not force a desired model if the physics indicates review.

---

# Deliverable H: Tests

Add:

```text
tests/unit/test_fastcfd_solid_liquid_suspension.py
tests/unit/test_fastcfd_solid_liquid_patch_compiler.py
tests/unit/test_fastcfd_solid_liquid_cli.py
```

Consolidate if repository style prefers fewer files.

## H.1 Required Physics Tests

Test:

```text
valid demo case produces pass or warn passport
invalid negative particle diameter fails closed
invalid solid volume fraction fails closed
particle Reynolds number calculation
Stokes number calculation
settling velocity calculation
mass loading calculation
cell-particle ratio calculation
time-step ratio calculation
```

## H.2 Required Recommendation Tests

Test:

```text
dilute low-loading case recommends dpm_one_way or appropriate review
dilute moderate mass-loading case recommends dpm_two_way or review
moderate volume fraction case recommends mixture_model or review
dense case recommends eulerian_multiphase_review
very dense case recommends eulerian_granular_review
inconsistent cell-particle ratio produces warning or block
large time step produces warning
```

## H.3 Required Patch Tests

Test:

```text
solid-liquid passport compiles into valid solver_plan_patch.json
model recommendation patch includes evidence
monitor patches include evidence
unsupported or blocked passport fails closed
no executable code is emitted
```

## H.4 Required CLI Tests

Test:

```text
write-solid-liquid-demo writes case file
validate-solid-liquid-suspension writes passport, hints, report
solid-liquid-handoff-demo writes full artifact chain
compile-fluent-patch auto-detects solid-liquid passport if supported
```

Run:

```bash
python -m pytest -q
```

Targeted:

```bash
python -m pytest -q tests -k "solid_liquid or suspension or patch_compiler"
```

---

# Deliverable I: Documentation

Create:

```text
docs/FASTFLUENT_HORIZONTAL_H3_PROGRESS_20260623.md
docs/FASTFLUENT_HORIZONTAL_H3_DELIVERY_20260623.md
```

Update if appropriate:

```text
docs/architecture.md
README.md
```

Keep README updates concise.

Final delivery report must include:

```text
- Goal summary
- What was implemented
- Files changed
- New schema versions
- New CLI commands
- Demo artifacts
- Test commands and results
- Known limitations
- What was intentionally not implemented
- Recommended next goal
```

---

# Implementation Notes

## 1. Recommended Status Logic

Start with:

```text
status = pass
```

Set `warn` if:

```text
non-Stokes drag regime
moderate or strong settling
moderate or high mass loading
transition between model recommendations
particle time step marginal or high
cell-particle ratio near 1
```

Set `block` if:

```text
input validation fails
solid volume fraction above physical packing threshold
cell_particle_ratio < 1 with sub-grid model recommendation
dangerous keys found
unsupported schema
```

Use conservative logic.

---

## 2. Recommended Time Step

Recommend:

```text
recommended_time_step_s = min(
  input_time_step_s,
  0.1 * particle_relaxation_time_s,
  0.5 * cell_size_m / max(reference_velocity_m_s, tiny)
)
```

If this is much smaller than input time step, warn.

---

## 3. Report Contents

`solid_liquid_suspension_report.md` should include:

```text
Case summary
Input properties
Particle Reynolds number
Stokes number
Settling velocity
Residence time vs settling time
Solid volume fraction regime
Mass loading
Cell-particle ratio
Particle time-step risk
Recommended Fluent model
Required Fluent monitors
Warnings
Blocking errors
Limitations
Reviewer checklist
```

Reviewer checklist:

```text
Confirm particle size distribution.
Confirm particle density and sphericity.
Confirm solid volume fraction.
Confirm whether one-way/two-way coupling is acceptable.
Confirm wall interaction relevance.
Confirm erosion/impact relevance.
Confirm gravity direction.
Confirm whether DPM, Mixture, or Eulerian model is intended.
Confirm mesh is not pretending to resolve sub-grid particles.
Confirm time step resolves particle relaxation if transient.
```

---

# Acceptance Criteria

Complete only if:

```text
1. solid_liquid_suspension.py exists.
2. case/passport/hints schemas exist.
3. physical calculations are implemented.
4. model recommendation logic is implemented.
5. Fluent hints are generated.
6. solver_plan_patch integration works.
7. public demo artifacts are generated.
8. CLI commands work.
9. tests pass.
10. delivery report is written.
```

Do not mark complete if:

```text
- only natural-language hints are generated.
- solver_plan_patch.json is missing.
- evidence refs are missing.
- patches fail validation.
- tests are not run.
- Fluent execution is added.
```

---

# Explicit Stop Boundary

After H3, stop.

Do not start:

```text
H4 wax rheology phase-change
Fluent execution adapter
PyFluent template generator
UDF lifecycle
full DPM trajectory solver
DEM coupling
```

Recommended next goal:

```text
H4: Wax Rheology / Phase-Change Passport
```

Reason:

```text
H4 directly connects measured wax material characterization to Fluent material-model and phase-change setup evidence for the dewaxing thesis direction.
```

---

# Final Response Format Required From Codex

When finished, respond with:

```text
## FastFluent Horizontal H3 Delivery Summary

### Implemented

### Files changed

### New schema versions

### New CLI commands

### Demo artifacts

### Test results

### Known limitations

### Explicit stop boundary

### Recommended next goal
```

Be precise.

Do not claim Fluent execution.

Do not claim final CFD validation.
