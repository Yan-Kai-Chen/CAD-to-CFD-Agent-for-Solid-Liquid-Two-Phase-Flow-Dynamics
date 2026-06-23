# FastFluent Horizontal H4 Goal: Wax Rheology / Phase-Change Passport

Date: 2026-06-23  
Repository: `CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics`  
Execution mode: Codex `/goal` mode  
Recommended save path: `docs/FASTFLUENT_HORIZONTAL_H4_WAX_RHEOLOGY_PHASE_CHANGE_GOAL_20260623.md`

---

## 0. Core Position

This stage is **FastFluent physics expansion**, not ANSYS Fluent execution.

H4 should implement a new FastFluent-native physics passport for wax rheology, thermal softening, and phase-change readiness.

Do not launch Fluent.  
Do not call PyFluent.  
Do not generate executable UDF source code.  
Do not require a Fluent license.  
Do not modify Fluent case/data files.

The target workflow is:

```text
wax material / thermal case
-> wax rheology phase-change passport
-> Fluent setup hints
-> solver_plan_patch.json
-> Markdown report
-> public demo artifacts
-> tests
```

The purpose is to convert measured or assumed wax material properties into **structured CFD setup evidence**.

This H4 module should become the bridge between:

```text
wax material characterization
-> FastFluent evidence
-> downstream Fluent material / source-term setup recommendation
```

---

## 1. Why H4 Exists

Previous stages built:

```text
H1: VOF / turbulence / rheology evidence -> solver_plan_patch.json
H2: steam-air condensation v2
H3: solid-liquid suspension passport
H3.5: horizontal validation pack
S1: FastFluent-native simulation validation pack
```

Now the project should connect the dewaxing thesis material side to FastFluent.

H4 focuses on:

```text
wax rheology
thermal softening
temperature-dependent viscosity
Arrhenius viscosity
melting / phase-change interval
latent heat source stiffness
thermal diffusion time scale
Fluent material-model readiness
```

This stage should not attempt to solve the full dewaxing process.

It should answer:

```text
Is the wax solid-like, softening, or flow-dominant in the temperature range?
Is viscosity strongly temperature-sensitive?
Is the time step too large for thermal diffusion or phase-change response?
Is a temperature-dependent viscosity model required?
Is a phase-change source term likely stiff?
Which Fluent monitors should be required?
Which Fluent material/source settings require manual review?
```

---

## 2. Project-Specific Material Context

Use these as default public synthetic / thesis-inspired demo values where appropriate.

Known wax material evidence from prior project discussion:

```text
Storage modulus:
G'(20–25 °C) ≈ 1165.5 MPa
G'(70 °C) ≈ 3.89 MPa

Softening:
50% softening temperature ≈ 57.03 °C
90% softening temperature ≈ 68.32 °C
tanδ peak ≈ 66.07 °C

Representative viscosity:
η_rep(82 °C) = 0.716430 Pa·s
η_rep(85 °C) = 0.485604 Pa·s

Arrhenius viscosity:
ln η_rep(T_K) = A + B / T_K
A = -46.7601
B = 16488.4
E_a = R * B ≈ 137.092 kJ/mol
```

Important:

```text
These values may be used for public synthetic demo cases,
but the module should also support user-provided case inputs.
```

Do not hard-code the module only for one wax.

---

## 3. Hard Boundary

### 3.1 Must Not Do

Do not:

```text
- Do not launch Fluent.
- Do not call PyFluent.
- Do not require a Fluent license.
- Do not edit Fluent case/data files.
- Do not emit arbitrary Fluent TUI commands.
- Do not emit arbitrary PyFluent commands.
- Do not generate executable UDF source code.
- Do not implement a production melting/solidification solver.
- Do not implement a full dewaxing simulation.
- Do not implement ProCAST coupling.
- Do not implement OpenFOAM integration.
- Do not implement GPU acceleration.
- Do not use private experimental files unless explicitly provided.
```

### 3.2 Must Do

Do:

```text
- Implement a wax rheology / phase-change case schema.
- Implement a wax rheology / phase-change passport schema.
- Implement Fluent setup hints.
- Implement solver_plan_patch.json generation.
- Implement Markdown report generation.
- Add public synthetic demo cases.
- Add unit tests for formulas and classifications.
- Add CLI commands.
- Add documentation and delivery report.
```

---

## 4. Read First

Inspect:

```text
README.md
ROADMAP.md
docs/architecture.md

src/fromcad2cfd_fastcfd/
src/fromcad2cfd_fastcfd/rheology.py
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
src/fromcad2cfd_fastcfd/solver_plan_patch.py
src/fromcad2cfd_fastcfd/cli.py
src/fromcad2cfd_fastcfd/capabilities.py

src/fromcad2cfd_fastcfd/steam_air_condensation_v2.py
src/fromcad2cfd_fastcfd/solid_liquid_suspension.py
src/fromcad2cfd_fastcfd/native_simulation_pack.py  # if exists

tests/unit/
docs/FASTFLUENT_HORIZONTAL_H1_DELIVERY_20260622.md
docs/FASTFLUENT_HORIZONTAL_H2_STEAM_AIR_CONDENSATION_V2_DELIVERY_20260623.md
docs/FASTFLUENT_HORIZONTAL_H3_DELIVERY_20260623.md
docs/FASTFLUENT_HORIZONTAL_H3_5_DELIVERY_20260623.md
docs/FASTFLUENT_S1_NATIVE_SIMULATION_DELIVERY_20260623.md
```

Create progress log:

```text
docs/FASTFLUENT_HORIZONTAL_H4_WAX_RHEOLOGY_PHASE_CHANGE_PROGRESS_20260623.md
```

Baseline note must include:

```text
- Existing rheology module capabilities.
- Existing patch compiler support for rheology.
- Existing solver_plan_patch contract status.
- Existing CLI pattern.
- Existing native simulation pack status.
- Initial test command result.
```

---

## 5. Main Deliverables

H4 has eight deliverables:

```text
Deliverable A: Wax Rheology / Phase-Change Schemas
Deliverable B: Core Material and Thermal Calculations
Deliverable C: Regime Classification and Risk Logic
Deliverable D: Fluent Hints
Deliverable E: Solver Plan Patch Integration
Deliverable F: CLI and Public Demo
Deliverable G: Tests
Deliverable H: Documentation and Delivery Report
```

---

# Deliverable A: Wax Rheology / Phase-Change Schemas

## A.1 Suggested Module

Create:

```text
src/fromcad2cfd_fastcfd/wax_rheology_phase_change.py
```

If project style strongly favors extending `rheology.py`, do so only if separation remains clear. Preferred: new dedicated module.

---

## A.2 Schema Versions

Use:

```text
fromcad2cfd_fastfluent_wax_rheology_phase_change_case_v1
fromcad2cfd_fastfluent_wax_rheology_phase_change_passport_v1
fromcad2cfd_fastfluent_wax_rheology_phase_change_fluent_hints_v1
```

---

## A.3 Input Case Fields

Input case should contain:

```text
schema_version
case_name

temperature_min_K
temperature_max_K
reference_temperature_K optional

softening_temperature_50_K
softening_temperature_90_K
tan_delta_peak_temperature_K optional

storage_modulus_low_temp_Pa optional
storage_modulus_high_temp_Pa optional
storage_modulus_low_temp_K optional
storage_modulus_high_temp_K optional

viscosity_model
arrhenius_A optional
arrhenius_B_K optional
activation_energy_J_mol optional

reference_viscosity_Pa_s optional
reference_viscosity_temperature_K optional

viscosity_fit_temperature_min_K optional
viscosity_fit_temperature_max_K optional

density_solid_kg_m3
density_liquid_kg_m3 optional
specific_heat_J_kgK
thermal_conductivity_W_mK
thermal_diffusivity_m2_s optional

latent_heat_J_kg optional
melting_temperature_min_K optional
melting_temperature_max_K optional

length_scale_m
cell_size_m
time_step_s
heating_rate_K_s optional

phase_change_model
units
metadata
```

Allowed viscosity models for v1:

```text
constant
arrhenius
review-required
```

Optional future models:

```text
carreau-yasuda
cross
power-law
herschel-bulkley
```

Do not implement optional models unless already easy and supported by existing rheology module.

Allowed phase_change_model for v1:

```text
none
effective_heat_capacity_review
enthalpy_porosity_review
source_term_review
```

Do not implement a full phase-change solver.

---

## A.4 Validation Rules

Validate:

```text
temperature_min_K > 0
temperature_max_K > temperature_min_K
length_scale_m > 0
cell_size_m > 0
time_step_s > 0
density_solid_kg_m3 > 0
specific_heat_J_kgK > 0
thermal_conductivity_W_mK > 0
if thermal_diffusivity_m2_s is provided: > 0
if latent_heat_J_kg is provided: > 0
if viscosity_model == arrhenius: arrhenius_A and arrhenius_B_K must exist
if softening temperatures are provided: softening_temperature_90_K >= softening_temperature_50_K
if melting interval is provided: melting_temperature_max_K >= melting_temperature_min_K
```

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

If invalid, fail closed with blocked passport when possible.

---

# Deliverable B: Core Material and Thermal Calculations

## B.1 Arrhenius Viscosity

For viscosity model:

```text
ln(eta) = A + B / T
eta(T) = exp(A + B / T)
```

Compute at minimum:

```text
eta_at_temperature_min_Pa_s
eta_at_temperature_max_Pa_s
eta_at_reference_temperature_Pa_s
eta_min_over_range_Pa_s
eta_max_over_range_Pa_s
eta_ratio_over_range
```

Use Kelvin.

If `activation_energy_J_mol` is absent but `arrhenius_B_K` exists, compute:

```text
E_a = R * B
```

Use:

```text
R = 8.314462618 J/(mol*K)
```

Output:

```text
activation_energy_J_mol
activation_energy_kJ_mol
```

Validation:

```text
eta must be finite and positive.
if eta_ratio_over_range is very large, warn.
```

---

## B.2 Constant Viscosity

If viscosity model is constant, use:

```text
reference_viscosity_Pa_s
```

Output:

```text
eta_min_over_range_Pa_s = reference_viscosity_Pa_s
eta_max_over_range_Pa_s = reference_viscosity_Pa_s
eta_ratio_over_range = 1
```

---

## B.3 Temperature Fit Range Check

If viscosity fit temperature bounds exist, check:

```text
temperature_min_K >= viscosity_fit_temperature_min_K
temperature_max_K <= viscosity_fit_temperature_max_K
```

Output:

```text
viscosity_fit_range_status
```

Status:

```text
inside_fit_range
partly_outside_fit_range
outside_fit_range
unknown
```

---

## B.4 Softening Regime

Use softening temperatures to classify the operating temperature range.

Regimes:

```text
solid_like
softening_transition
flow_dominant
crosses_softening_transition
unknown
```

Suggested logic:

```text
if temperature_max_K < softening_temperature_50_K:
  solid_like

elif temperature_min_K > softening_temperature_90_K:
  flow_dominant

elif temperature_min_K <= softening_temperature_90_K and temperature_max_K >= softening_temperature_50_K:
  crosses_softening_transition

else:
  softening_transition
```

Output:

```text
softening_regime
softening_transition_overlap_K
```

---

## B.5 Storage Modulus Drop

If storage modulus low/high values are provided, compute:

```text
storage_modulus_drop_ratio = G_low / G_high
log10_storage_modulus_drop
```

Output:

```text
storage_modulus_drop_ratio
mechanical_softening_strength
```

Classification:

```text
drop_ratio < 10:
  weak

10 <= drop_ratio < 100:
  moderate

drop_ratio >= 100:
  strong
```

---

## B.6 Thermal Diffusion Time Scale

If `thermal_diffusivity_m2_s` is absent, compute:

```text
alpha = k / (rho * cp)
```

Use `density_solid_kg_m3` as first-pass density.

Compute:

```text
domain_diffusion_time_s = length_scale_m^2 / alpha
cell_diffusion_time_s = cell_size_m^2 / alpha
thermal_time_step_ratio = time_step_s / cell_diffusion_time_s
```

Classification:

```text
thermal_time_step_ratio < 0.1:
  resolved

0.1 <= ratio < 1:
  marginal

ratio >= 1:
  under_resolved
```

---

## B.7 Heating Time Scale

If heating_rate_K_s is provided:

```text
heating_time_to_cross_softening_s = (softening_temperature_90_K - softening_temperature_50_K) / heating_rate_K_s
```

If melting interval is provided:

```text
heating_time_to_cross_melting_s = (melting_temperature_max_K - melting_temperature_min_K) / heating_rate_K_s
```

Output:

```text
softening_heating_time_s
melting_heating_time_s
heating_vs_diffusion_ratio
```

---

## B.8 Stefan Number

If latent heat exists:

```text
Ste = cp * deltaT / latent_heat
```

Use:

```text
deltaT = max(temperature_max_K - temperature_min_K, tiny)
```

Output:

```text
stefan_number
```

Interpretation:

```text
small Ste:
  latent heat dominates

large Ste:
  sensible heat dominates
```

---

## B.9 Phase-Change Energy Scale

If latent heat exists, compute:

```text
phase_change_energy_density_J_m3 = density_solid_kg_m3 * latent_heat_J_kg
phase_change_power_density_scale_W_m3 = phase_change_energy_density_J_m3 / max(time_step_s, tiny)
```

Output:

```text
phase_change_energy_density_J_m3
phase_change_power_density_scale_W_m3
```

Classification:

```text
phase_change_power_density_scale_W_m3 very large:
  source-term stiffness risk high
```

Use conservative thresholds and document them. If uncertain, warn.

---

## B.10 Recommended Time Step

Recommend:

```text
recommended_time_step_s = min(
  input_time_step_s,
  0.2 * cell_diffusion_time_s
)
```

If latent heat and heating rate exist, also consider:

```text
0.1 * melting_heating_time_s
0.1 * softening_heating_time_s
```

Do not return zero or negative values.

---

# Deliverable C: Regime Classification and Risk Logic

## C.1 Viscosity Sensitivity Risk

Use `eta_ratio_over_range`.

Suggested classification:

```text
eta_ratio <= 10:
  low

10 < eta_ratio <= 100:
  moderate

100 < eta_ratio <= 10000:
  high

eta_ratio > 10000:
  extreme
```

Output:

```text
viscosity_temperature_sensitivity_risk
```

---

## C.2 Phase-Change Stiffness Risk

Use:

```text
thermal_time_step_ratio
Ste
phase_change_power_density_scale_W_m3
melting interval width
time_step_s
```

Output:

```text
phase_change_stiffness_risk
```

Classification:

```text
low
moderate
high
extreme
```

Set `warn` for high.  
Set `block` for extreme if source-term review is required and time step is clearly unsafe.

---

## C.3 Material Model Recommendation

Output one of:

```text
constant_viscosity
temperature_dependent_viscosity
arrhenius_viscosity
softening_transition_review
phase_change_review_required
blocked_invalid_material_data
```

Logic:

```text
if invalid input:
  blocked_invalid_material_data

elif viscosity_model == arrhenius:
  arrhenius_viscosity

elif softening range overlaps operating range:
  softening_transition_review

elif phase_change_model != none:
  phase_change_review_required

elif viscosity_model == constant:
  constant_viscosity

else:
  temperature_dependent_viscosity or review-required
```

Do not overclaim a Fluent-ready source model.

---

## C.4 Status Logic

Start with:

```text
status = pass
```

Set `warn` if:

```text
- temperature range crosses softening transition
- viscosity sensitivity is high
- thermal time step is marginal
- phase-change stiffness is moderate or high
- fit range is unknown or partly outside
- latent heat exists but phase-change model is review-required
```

Set `block` if:

```text
- input validation fails
- dangerous keys found
- viscosity values are non-finite or non-positive
- phase-change stiffness is extreme
- temperature range is far outside provided fit range
```

---

# Deliverable D: Fluent Hints

Generate:

```text
wax_rheology_phase_change_fluent_hints.json
```

Top-level fields:

```text
schema_version
case_name
status
recommended_material_model
recommended_physics
recommended_materials
recommended_numerics
recommended_transient_controls
recommended_monitors
recommended_source_term_controls
recommended_postprocessing
warnings
blocking_errors
limitations
metadata
```

## D.1 Recommended Physics

Include:

```text
energy equation enabled
temperature-dependent viscosity if needed
phase-change source-term review if latent heat is present
solid/liquid material property review
```

Example:

```json
{
  "energy": true,
  "material_model": "arrhenius_viscosity",
  "phase_change_model": "source_term_review",
  "requires_manual_source_review": true
}
```

---

## D.2 Recommended Monitors

Include:

```text
temperature_min_max
viscosity_min_max
liquid_fraction_bounds_if_available
phase_change_source_integral_if_available
energy_balance
max_temperature
min_temperature
thermal_diffusion_time_step_indicator
```

---

## D.3 Recommended Source-Term Controls

Include:

```text
source ramping
source clamp
temperature bounds
NaN guard
latent heat unit check
source sign convention review
```

---

## D.4 Recommended Transient Controls

Include:

```text
initial_time_step_s = recommended_time_step_s
adaptive_time_step = true if risk is moderate/high
checkpoint during softening/phase-change interval
```

---

# Deliverable E: Solver Plan Patch Integration

Extend:

```text
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
```

to support:

```text
fromcad2cfd_fastfluent_wax_rheology_phase_change_passport_v1
```

## E.1 Patch Operations

Generate patch operations where evidence supports them:

```text
/physics/energy/enabled = true
/materials/property_models += arrhenius_viscosity
/materials/property_models += temperature_dependent_viscosity
/materials/property_models += phase_change_review
/physics/material_model = <recommendation>
/source_terms/phase_change/model = "review-required"
/numerics/source_term_controls/ramping = true
/numerics/source_term_controls/clamp = true
/numerics/source_term_controls/nan_guard = true
/transient/initial_time_step_s = <recommended_time_step_s>
/monitors/global += temperature_min_max
/monitors/global += viscosity_min_max
/monitors/global += max_temperature
/monitors/global += energy_balance
/monitors/global += phase_change_source_integral_if_available
/postprocessing/required_outputs += viscosity_field_summary
/postprocessing/required_outputs += temperature_field_summary
/acceptance_criteria/bounded_temperature_range_K = <range>
/acceptance_criteria/bounded_viscosity_range = true
```

If a path is not currently allowed by the patch contract:

```text
- use the closest existing allowed path, or
- minimally extend the allowed path list if safe and consistent.
```

Do not add broad unsafe permissions.

---

## E.2 Evidence IDs

Suggested evidence IDs:

```text
wax_arrhenius_viscosity
wax_viscosity_range
wax_viscosity_sensitivity
wax_softening_regime
wax_storage_modulus_drop
wax_thermal_diffusion_time
wax_phase_change_energy_scale
wax_phase_change_stiffness
wax_recommended_time_step
wax_material_model_recommendation
wax_monitor_requirements
```

Every physics, material, transient, monitor, source-term, postprocessing, and acceptance patch must include evidence refs.

---

## E.3 Patch Validation

Generated `solver_plan_patch.json` must pass the existing patch validator.

Do not weaken the validator.

If a generated patch fails validation, fix the patch compiler.

---

# Deliverable F: CLI and Public Demo

## F.1 CLI Commands

Add:

```bash
python -m fromcad2cfd fastcfd write-wax-rheology-demo \
  --output-dir sandbox/output/wax_rheology_phase_change_demo
```

Writes:

```text
wax_rheology_phase_change_case.json
```

---

Add:

```bash
python -m fromcad2cfd fastcfd validate-wax-rheology-phase-change \
  --case sandbox/output/wax_rheology_phase_change_demo/wax_rheology_phase_change_case.json \
  --output-dir sandbox/output/wax_rheology_phase_change_demo/passport
```

Writes:

```text
wax_rheology_phase_change_passport.json
wax_rheology_phase_change_fluent_hints.json
wax_rheology_phase_change_report.md
```

---

Add:

```bash
python -m fromcad2cfd fastcfd wax-rheology-handoff-demo \
  --output-dir sandbox/output/wax_rheology_phase_change_demo
```

Runs full chain:

```text
case
-> passport
-> hints
-> solver_plan_patch.json
-> solver_plan_patch_report.md
```

Ensure the existing generic command supports auto-detection:

```bash
python -m fromcad2cfd fastcfd compile-fluent-patch \
  --input <wax_rheology_phase_change_passport.json> \
  --output <solver_plan_patch.json>
```

---

## F.2 Public Demo Case

Use a public synthetic / thesis-inspired demo.

Suggested values:

```text
case_name = wax_arrhenius_softening_demo

temperature_min_K = 353.15        # 80 °C
temperature_max_K = 373.15        # 100 °C
reference_temperature_K = 355.15  # 82 °C

softening_temperature_50_K = 330.18  # 57.03 °C
softening_temperature_90_K = 341.47  # 68.32 °C
tan_delta_peak_temperature_K = 339.22 # 66.07 °C

storage_modulus_low_temp_Pa = 1.1655e9
storage_modulus_high_temp_Pa = 3.89e6
storage_modulus_low_temp_K = 298.15
storage_modulus_high_temp_K = 343.15

viscosity_model = arrhenius
arrhenius_A = -46.7601
arrhenius_B_K = 16488.4

density_solid_kg_m3 = 900
density_liquid_kg_m3 = 780
specific_heat_J_kgK = 2200
thermal_conductivity_W_mK = 0.25

latent_heat_J_kg = 200000
melting_temperature_min_K = 330.15
melting_temperature_max_K = 345.15

length_scale_m = 0.01
cell_size_m = 0.0005
time_step_s = 0.01
heating_rate_K_s = 2.0

phase_change_model = source_term_review
```

Do not claim these are final measured material constants. Mark as demo values.

---

## F.3 Expected Demo Output Tree

```text
sandbox/output/wax_rheology_phase_change_demo/
├── wax_rheology_phase_change_case.json
├── passport/
│   ├── wax_rheology_phase_change_passport.json
│   ├── wax_rheology_phase_change_fluent_hints.json
│   └── wax_rheology_phase_change_report.md
├── solver_plan_patch.json
└── solver_plan_patch_report.md
```

---

# Deliverable G: Tests

## G.1 Suggested Test Files

Add:

```text
tests/unit/test_fastcfd_wax_rheology_phase_change.py
tests/unit/test_fastcfd_wax_rheology_patch_compiler.py
tests/unit/test_fastcfd_wax_rheology_cli.py
```

Consolidate if repository style prefers fewer files.

---

## G.2 Required Formula Tests

Test:

```text
Arrhenius viscosity at reference temperature
Arrhenius activation energy calculation
viscosity ratio over temperature range
thermal diffusivity calculation if alpha absent
cell diffusion time
thermal time-step ratio
storage modulus drop ratio
Stefan number
phase-change energy density
phase-change power density scale
recommended time step
```

Use numerical tolerances.

---

## G.3 Required Classification Tests

Test:

```text
solid-like regime
softening transition regime
flow-dominant regime
crosses-softening-transition regime
low/moderate/high/extreme viscosity sensitivity
low/moderate/high/extreme phase-change stiffness risk
inside / partly outside / outside viscosity fit range
```

---

## G.4 Required Patch Tests

Test:

```text
wax passport compiles into valid solver_plan_patch.json
arrhenius viscosity patch includes evidence
temperature-dependent viscosity monitor includes evidence
source-term controls include evidence
recommended time-step patch includes evidence
blocked passport fails closed or produces blocked patch
no executable UDF or raw Fluent command is emitted
```

---

## G.5 Required CLI Tests

Test:

```text
write-wax-rheology-demo writes case file
validate-wax-rheology-phase-change writes passport, hints, report
wax-rheology-handoff-demo writes full artifact chain
compile-fluent-patch auto-detects wax passport
```

---

## G.6 Required Test Commands

Run:

```bash
python -m pytest -q
```

Run targeted tests:

```bash
python -m pytest -q tests -k "wax or rheology or phase_change or patch_compiler"
```

If unrelated pre-existing failures occur, document:

```text
- failing test name
- failure message
- why unrelated
- whether new tests passed
```

Do not hide failures.

---

# Deliverable H: Documentation

## H.1 Progress Log

Create:

```text
docs/FASTFLUENT_HORIZONTAL_H4_WAX_RHEOLOGY_PHASE_CHANGE_PROGRESS_20260623.md
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
docs/FASTFLUENT_HORIZONTAL_H4_WAX_RHEOLOGY_PHASE_CHANGE_DELIVERY_20260623.md
```

It must include:

```text
- Goal summary.
- Why H4 validates wax material setup evidence without Fluent execution.
- Files changed.
- New schema versions.
- New CLI commands.
- Demo artifacts.
- Formula tests.
- Classification tests.
- Patch validation results.
- Test commands and results.
- Known limitations.
- Explicit statement that Fluent was not launched.
- Recommended next goal.
```

---

## H.3 Report Contents

`wax_rheology_phase_change_report.md` should include:

```text
Case summary
Input material properties
Arrhenius viscosity calculation
Viscosity range over temperature interval
Softening regime
Storage modulus drop
Thermal diffusion time scale
Cell diffusion time scale
Stefan number
Phase-change energy scale
Source-term stiffness risk
Recommended Fluent material model
Recommended monitors
Warnings
Blocking errors
Limitations
Reviewer checklist
```

Reviewer checklist:

```text
Confirm wax density and thermal properties.
Confirm Arrhenius viscosity fit range.
Confirm whether DMA softening temperatures apply to this wax batch.
Confirm latent heat and melting interval.
Confirm whether phase change should be modeled with effective heat capacity or source term.
Confirm source-term sign convention before Fluent use.
Confirm source ramp and clamp before Fluent use.
Confirm temperature bounds and viscosity bounds.
Confirm time step during softening and phase-change interval.
Confirm this artifact has not launched Fluent.
```

---

# Implementation Notes

## 1. Do Not Duplicate Existing Rheology Logic Unnecessarily

If `rheology.py` already contains Arrhenius or viscosity helper functions, reuse them.

If not, implement small pure functions in the new module.

Keep public functions deterministic.

---

## 2. Suggested Public API

Implement:

```python
create_demo_wax_rheology_case() -> dict
validate_wax_rheology_case(case: dict) -> ValidationResult
build_wax_rheology_phase_change_passport(case: dict) -> dict
build_wax_rheology_phase_change_fluent_hints(passport: dict) -> dict
compile_wax_rheology_phase_change_patch(passport: dict) -> dict
write_wax_rheology_phase_change_bundle(case: dict, output_dir: Path) -> dict
write_wax_rheology_phase_change_report(passport: dict, path: Path) -> None
```

Names may be adjusted to match repository style.

---

## 3. Suggested Computed Quantities Section

Passport should include:

```text
computed_quantities:
  arrhenius:
    eta_at_temperature_min_Pa_s
    eta_at_temperature_max_Pa_s
    eta_ratio_over_range
    activation_energy_kJ_mol

  softening:
    softening_regime
    softening_transition_overlap_K
    storage_modulus_drop_ratio

  thermal:
    thermal_diffusivity_m2_s
    domain_diffusion_time_s
    cell_diffusion_time_s
    thermal_time_step_ratio

  phase_change:
    stefan_number
    phase_change_energy_density_J_m3
    phase_change_power_density_scale_W_m3
    phase_change_stiffness_risk

  recommendation:
    material_model_recommendation
    recommended_time_step_s
```

---

## 4. Limitations Must Be Explicit

The report must state:

```text
This passport is an engineering readiness gate.
It is not a production phase-change solver.
It does not validate final dewaxing behavior.
It does not replace Fluent or ProCAST.
It does not generate executable UDF code.
```

---

# Acceptance Criteria

H4 is complete only if all are true:

```text
1. wax_rheology_phase_change.py exists.
2. case/passport/hints schemas exist.
3. Arrhenius viscosity calculations work.
4. softening regime classification works.
5. thermal diffusion and time-step checks work.
6. phase-change stiffness risk calculation works.
7. Fluent hints are generated.
8. solver_plan_patch integration works and passes validator.
9. CLI commands work.
10. public demo artifacts are generated.
11. formula tests pass.
12. classification tests pass.
13. patch compiler tests pass.
14. full pytest passes or unrelated failures are documented.
15. delivery report is written.
16. delivery report explicitly states Fluent was not launched.
```

Do not mark complete if:

```text
- only natural-language hints are generated.
- solver_plan_patch.json is missing.
- evidence refs are missing.
- patches fail validation.
- tests are not run.
- Fluent is launched.
- executable UDF code is generated.
```

---

# Explicit Stop Boundary

After H4, stop.

Do not start S2 inside this goal.

Do not implement:

```text
S2 wax / thermal / rheology native mini-simulation pack
Fluent execution adapter
PyFluent template generator
UDF lifecycle
ProCAST coupling
OpenFOAM integration
GPU acceleration
```

Recommended next goal:

```text
S2: Wax / Thermal / Rheology Native Mini-Simulation Pack
```

Reason:

```text
H4 produces wax material setup evidence.
S2 should then run FastFluent-native mini simulations:
1D/2D heat diffusion,
temperature-dependent viscosity channel,
non-Newtonian channel benchmark,
and phase-change source-term toy benchmark.
```

---

# Final Response Format Required From Codex

When finished, respond with:

```text
## FastFluent H4 Wax Rheology / Phase-Change Delivery Summary

### Implemented

### Files changed

### New schema versions

### New CLI commands

### Demo artifacts

### Formula tests

### Classification tests

### Patch validation results

### Test results

### Known limitations

### Explicit statement: Fluent was not launched

### Recommended next goal
```

Be precise.

Do not claim Fluent execution.

Do not claim final CFD validation.

Do not claim final dewaxing accuracy.
