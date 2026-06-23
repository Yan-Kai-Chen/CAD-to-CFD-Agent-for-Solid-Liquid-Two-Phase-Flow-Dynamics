# FastFluent Horizontal H3.5 Goal: Native Validation Pack for H1-H3

Date: 2026-06-23  
Repository: `CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics`  
Execution mode: Codex `/goal` mode  
Recommended save path: `docs/FASTFLUENT_HORIZONTAL_H3_5_VALIDATION_PACK_GOAL_20260623.md`

---

## 0. Core Position

This stage is **not** Fluent execution.

This stage is **not** PyFluent execution.

This stage is **not** UDF generation.

This stage is a FastFluent-native validation pack for the horizontal physics modules completed in H1-H3.

The goal is to prove that the H1-H3 FastFluent modules are usable, reproducible, and internally consistent through:

```text
analytical formula checks
regime-classification checks
multi-case synthetic demos
CLI artifact generation
solver_plan_patch validation
combined-patch stress tests
pytest regression tests
validation summary reports
```

FastFluent must be tested by running FastFluent code, not by launching Fluent.

---

## 1. Why This Stage Exists

H1-H3 introduced or expanded the following FastFluent horizontal capabilities:

```text
H1:
  Existing VOF / turbulence / rheology evidence -> solver_plan_patch.json

H2:
  Steam-air condensation v2 with dimensionless groups, HTC estimate,
  mass-transfer screening, and source-term checks

H3:
  Solid-liquid suspension passport with particle Reynolds number,
  Stokes number, settling, mass loading, and Fluent model recommendation
```

Before adding H4, the project needs a validation pack that answers:

```text
Do H1-H3 modules run from CLI?
Do the generated JSON artifacts exist?
Do the computed physical quantities match expected values?
Do model recommendations behave correctly across regimes?
Do generated solver_plan_patch.json files pass validation?
Do combined patches preserve evidence and handle conflicts?
Do all tests pass?
```

This is a reliability consolidation step, not an audit-only step.

---

## 2. Hard Boundary

### 2.1 Must Not Do

Do not:

```text
- Do not launch Fluent.
- Do not call PyFluent.
- Do not require a Fluent license.
- Do not read or modify Fluent case/data files.
- Do not emit arbitrary Fluent TUI commands.
- Do not emit arbitrary PyFluent commands.
- Do not generate arbitrary UDF source code.
- Do not implement a Fluent execution adapter.
- Do not implement a trust report for Fluent outputs.
- Do not implement H4 wax phase-change passport in this goal.
- Do not add OpenFOAM integration.
- Do not add GPU acceleration.
```

### 2.2 Must Do

Do:

```text
- Run FastFluent-native modules.
- Generate public synthetic cases.
- Generate passports, hints, reports, and solver_plan_patch.json files.
- Validate generated patches with the existing patch validator.
- Add numerical tests for core formulas.
- Add regime tests for model recommendations.
- Add CLI tests for demo artifact generation.
- Add combined-patch stress tests.
- Write a final validation summary.
```

---

## 3. Read First

Inspect the current repository state.

Read:

```text
README.md
ROADMAP.md
docs/architecture.md

src/fromcad2cfd_fastcfd/
src/fromcad2cfd_fastcfd/solver_plan_patch.py
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
src/fromcad2cfd_fastcfd/cli.py
src/fromcad2cfd_fastcfd/capabilities.py

src/fromcad2cfd_fastcfd/vof.py
src/fromcad2cfd_fastcfd/turbulence.py
src/fromcad2cfd_fastcfd/rheology.py
src/fromcad2cfd_fastcfd/steam_air_condensation.py
src/fromcad2cfd_fastcfd/steam_air_condensation_v2.py
src/fromcad2cfd_fastcfd/solid_liquid_suspension.py

tests/unit/
```

Also inspect H1-H3 delivery documents if present:

```text
docs/FASTFLUENT_HORIZONTAL_H1_DELIVERY_20260622.md
docs/FASTFLUENT_HORIZONTAL_H2_DELIVERY_20260623.md
docs/FASTFLUENT_HORIZONTAL_H3_DELIVERY_20260623.md
```

Create a baseline progress log:

```text
docs/FASTFLUENT_HORIZONTAL_H3_5_PROGRESS_20260623.md
```

Baseline note must include:

```text
- Available H1 modules and CLI commands.
- Available H2 modules and CLI commands.
- Available H3 modules and CLI commands.
- Existing patch compiler supported schemas.
- Existing test count before H3.5 changes.
- Initial full test command result.
```

---

## 4. H3.5 Main Deliverables

This goal has seven deliverables:

```text
Deliverable A: Validation Pack CLI
Deliverable B: H1 Multi-Case Validation
Deliverable C: H2 Multi-Case Validation
Deliverable D: H3 Multi-Case Validation
Deliverable E: Combined Patch Stress Tests
Deliverable F: Regression Tests
Deliverable G: Documentation and Final Validation Summary
```

---

# Deliverable A: Validation Pack CLI

## A.1 Purpose

Add a single CLI command that generates a full FastFluent horizontal validation pack.

Preferred command:

```bash
python -m fromcad2cfd fastcfd horizontal-validation-pack-demo \
  --output-dir sandbox/output/fastfluent_horizontal_validation_pack
```

This command should run only FastFluent-native code.

It should generate public synthetic cases for:

```text
VOF
turbulence
rheology
steam-air condensation v2
solid-liquid suspension
combined patches
```

No Fluent execution is allowed.

---

## A.2 Expected Output Tree

The command should generate:

```text
sandbox/output/fastfluent_horizontal_validation_pack/
├── vof_cases/
│   ├── vof_case_01_gravity_dominant/
│   ├── vof_case_02_capillary_dominant/
│   ├── vof_case_03_high_density_ratio/
│   └── vof_case_04_high_cfl_risk/
├── turbulence_cases/
│   ├── turbulence_case_01_laminar/
│   ├── turbulence_case_02_transition/
│   ├── turbulence_case_03_high_re/
│   └── turbulence_case_04_yplus_mismatch/
├── rheology_cases/
│   ├── rheology_case_01_constant_viscosity/
│   ├── rheology_case_02_arrhenius_sensitive/
│   ├── rheology_case_03_non_newtonian_review/
│   └── rheology_case_04_out_of_fit_range/
├── steam_air_v2_cases/
│   ├── steam_air_case_01_saturated_cold_wall/
│   ├── steam_air_case_02_hot_wall_no_condensation/
│   ├── steam_air_case_03_high_noncondensable/
│   ├── steam_air_case_04_large_dt_stiff_source/
│   └── steam_air_case_05_high_re_impact/
├── solid_liquid_cases/
│   ├── solid_liquid_case_01_dilute_low_loading/
│   ├── solid_liquid_case_02_dilute_moderate_loading/
│   ├── solid_liquid_case_03_moderate_volume_fraction/
│   ├── solid_liquid_case_04_dense_suspension/
│   ├── solid_liquid_case_05_granular_review/
│   └── solid_liquid_case_06_particle_cell_mismatch/
├── combined_patch_cases/
│   ├── combined_case_01_vof_turbulence/
│   ├── combined_case_02_solid_liquid_turbulence/
│   ├── combined_case_03_steam_air_rheology/
│   └── combined_case_04_conflict_stress/
├── validation_manifest.json
└── validation_summary.md
```

Each individual case directory should contain, when supported:

```text
input_case.json
passport.json
fluent_hints.json
solver_plan_patch.json
solver_plan_patch_report.md
case_summary.md
```

If a module does not produce a passport but produces a structured hint or evidence artifact, use the existing supported artifact name and document it clearly.

---

## A.3 Validation Manifest

Create:

```text
validation_manifest.json
```

It should include:

```text
schema_version
created_by
generated_at
case_count
module_counts
case_index
artifact_index
test_status_summary
limitations
metadata
```

Each case entry should include:

```text
case_id
module
case_name
expected_status
actual_status
artifact_paths
patch_valid
warnings
blocking_errors
key_quantities
```

---

## A.4 Validation Summary

Create:

```text
validation_summary.md
```

It should include:

```text
- Overall status.
- Number of generated cases.
- Number of valid patches.
- Number of warning cases.
- Number of blocked cases.
- Per-module summary table.
- Per-case summary table.
- Combined patch summary.
- Known limitations.
- Explicit statement: Fluent was not launched and is not required for this validation pack.
```

---

# Deliverable B: H1 Multi-Case Validation

H1 covers:

```text
VOF
turbulence
rheology
```

The goal is to test existing H1 patch-adapter behavior across multiple physical regimes.

---

## B.1 VOF Cases

Generate at least four VOF validation cases.

### VOF Case 01: Gravity-Dominant

Purpose:

```text
Test gravity-dominated two-phase setup.
```

Expected behavior:

```text
- VOF model recommended.
- Gravity enabled or warning that gravity is important.
- Volume fraction monitor recommended.
- Phase mass conservation monitor recommended.
```

Suggested physical regime:

```text
low Weber number or high Bond number
moderate density contrast
moderate time step
```

### VOF Case 02: Capillary-Dominant

Purpose:

```text
Test surface-tension-dominated time-step restriction.
```

Expected behavior:

```text
- Surface tension enabled if evidence supports it.
- Capillary time-step warning or smaller recommended dt.
- Interface-related monitor recommendations.
```

### VOF Case 03: High Density Ratio

Purpose:

```text
Test density-ratio warning.
```

Expected behavior:

```text
- High density ratio warning.
- VOF patch remains valid.
- Patch evidence references density-ratio evidence.
```

### VOF Case 04: High CFL Risk

Purpose:

```text
Test time-step / CFL warning.
```

Expected behavior:

```text
- transient warning.
- recommended dt if supported.
- Courant monitor recommended.
```

---

## B.2 Turbulence Cases

Generate at least four turbulence validation cases.

### Turbulence Case 01: Laminar

Expected behavior:

```text
- Low Re.
- laminar model recommended or turbulence disabled.
- No overconfident turbulence model patch.
```

### Turbulence Case 02: Transition

Expected behavior:

```text
- Transitional Re.
- review-required or warning.
- No overconfident SST/k-epsilon recommendation.
```

### Turbulence Case 03: High-Re Turbulent

Expected behavior:

```text
- High Re.
- SST or k-epsilon review recommendation.
- Wall shear / y+ monitor recommended if supported.
```

### Turbulence Case 04: y+ Mismatch

Expected behavior:

```text
- y+ or near-wall warning.
- Recommended model is not overconfident if near-wall support is missing.
```

---

## B.3 Rheology Cases

Generate at least four rheology validation cases.

### Rheology Case 01: Constant Viscosity

Expected behavior:

```text
- Low-risk material model.
- Viscosity monitor optional or recommended.
- Patch valid.
```

### Rheology Case 02: Arrhenius-Sensitive

Expected behavior:

```text
- Temperature-sensitive viscosity warning.
- Viscosity min/max monitor recommended.
- Temperature min/max monitor recommended.
```

### Rheology Case 03: Non-Newtonian Review

Expected behavior:

```text
- non-newtonian-review-required or equivalent warning.
- No UDF source code generated.
- Material model patch remains review-safe.
```

### Rheology Case 04: Out-of-Fit-Range

Expected behavior:

```text
- warning or block.
- patch does not overclaim material model validity.
```

---

# Deliverable C: H2 Multi-Case Validation

H2 covers steam-air condensation v2.

Generate at least five cases.

---

## C.1 Steam-Air Case 01: Near-Saturated Steam + Cold Wall

Expected behavior:

```text
- Condensation plausible.
- Positive wall subcooling.
- Source-term controls recommended.
- Wall heat transfer monitor recommended.
```

Validate:

```text
Re, Pr, Pe, Ja, Ste
HTC estimate
heat flux estimate
patch validity
```

---

## C.2 Steam-Air Case 02: Hot Wall / No Condensation

Expected behavior:

```text
- Wall temperature above saturation.
- No-condensation or weak-condensation warning.
- Source term either not recommended or marked review-required.
```

---

## C.3 Steam-Air Case 03: High Non-Condensable Gas

Expected behavior:

```text
- High non-condensable resistance.
- Species transport recommended.
- Near-wall steam fraction monitor recommended.
```

---

## C.4 Steam-Air Case 04: Large Time Step / Stiff Source

Expected behavior:

```text
- Source stiffness warning or block.
- Smaller recommended dt.
- Ramp and clamp recommended.
- max temperature monitor recommended.
```

---

## C.5 Steam-Air Case 05: High-Re Steam Impact

Expected behavior:

```text
- High Reynolds number.
- Turbulence review or model recommendation.
- High velocity / pressure / wall heat monitor recommendations.
```

---

# Deliverable D: H3 Multi-Case Validation

H3 covers solid-liquid suspension.

Generate at least six cases.

---

## D.1 Solid-Liquid Case 01: Very Dilute + Low Loading

Expected behavior:

```text
- dpm_one_way or appropriate low-coupling recommendation.
- Low mass loading.
- Low or moderate Stokes number.
```

---

## D.2 Solid-Liquid Case 02: Dilute + Moderate Loading

Expected behavior:

```text
- dpm_two_way or review-required.
- Mass loading warning if applicable.
```

---

## D.3 Solid-Liquid Case 03: Moderate Volume Fraction

Expected behavior:

```text
- mixture_model or review-required.
- Solid volume fraction monitor recommended.
```

---

## D.4 Solid-Liquid Case 04: Dense Suspension

Expected behavior:

```text
- eulerian_multiphase_review.
- Dense concentration warning.
```

---

## D.5 Solid-Liquid Case 05: Very Dense / Granular Review

Expected behavior:

```text
- eulerian_granular_review.
- Strong warning or block depending thresholds.
```

---

## D.6 Solid-Liquid Case 06: Particle-Cell Mismatch

Expected behavior:

```text
- cell-particle ratio warning or block.
- Do not overclaim DPM or mixture-model suitability.
```

---

# Deliverable E: Combined Patch Stress Tests

## E.1 Purpose

Validate that patches from different FastFluent modules can be merged without losing evidence or producing silent conflicts.

---

## E.2 Combined Cases

Generate at least four combined cases.

### Combined Case 01: VOF + Turbulence

Expected:

```text
- Multiphase patch and turbulence patch coexist.
- Duplicate monitor entries deduplicated.
- Evidence preserved.
```

### Combined Case 02: Solid-Liquid + Turbulence

Expected:

```text
- Solid-liquid model recommendation coexists with turbulence recommendation.
- y+ / wall shear monitors coexist with particle monitors.
```

### Combined Case 03: Steam-Air + Rheology

Expected:

```text
- Thermal/source-term controls coexist with material-property monitors.
- Temperature monitor deduplicated if repeated.
```

### Combined Case 04: Conflict Stress

Create a controlled synthetic conflict, such as:

```text
one patch recommends laminar
another patch recommends k-omega-sst
```

Expected:

```text
- conflict warning or block generated.
- no silent overwrite.
- conflict_summary.json or equivalent section produced.
```

---

## E.3 Combined Patch Outputs

Each combined case should include:

```text
combined_solver_plan_patch.json
combined_solver_plan_patch_report.md
conflict_summary.json
```

Each combined patch must pass the patch validator unless intentionally blocked.

If intentionally blocked, the block must be documented and expected.

---

# Deliverable F: Regression Tests

Add tests that verify H1-H3 behavior is stable.

Suggested test file:

```text
tests/unit/test_fastfluent_horizontal_validation_pack.py
```

Additional test files may be added if needed.

---

## F.1 Required Formula Tests

Verify numerical formulas where applicable.

### Solid-Liquid

Test:

```text
particle Reynolds number
particle relaxation time
Stokes number
settling velocity
mass loading
cell-particle ratio
particle time-step ratio
```

### Steam-Air v2

Test:

```text
Re
Pr
Pe
Ja
Ste
HTC estimate structure
mass-transfer resistance classification
source-term dimension check
```

### VOF / Turbulence / Rheology

If existing formulas are available, verify:

```text
VOF dimensionless groups
CFL or time-step warning
turbulence Re classification
y+ warning
rheology viscosity ratio or Arrhenius estimate
```

Only test formulas actually implemented.

Do not fabricate unavailable fields.

---

## F.2 Required Artifact Tests

For the validation pack demo:

```text
- validation_manifest.json exists.
- validation_summary.md exists.
- every case directory exists.
- every generated solver_plan_patch.json is valid or intentionally blocked.
- every patch operation has evidence refs when required by the patch contract.
- no generated artifact contains dangerous keys.
```

---

## F.3 Required CLI Tests

Test:

```text
python -m fromcad2cfd fastcfd horizontal-validation-pack-demo --output-dir <tmpdir>
```

Assert:

```text
- command exits successfully.
- expected directories are created.
- manifest exists.
- summary exists.
- minimum case count is met.
```

---

## F.4 Required Regression Commands

Run:

```bash
python -m pytest -q
```

Run targeted tests:

```bash
python -m pytest -q tests -k "vof or turbulence or rheology or steam_air or solid_liquid or validation_pack or patch_compiler"
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

# Deliverable G: Documentation

## G.1 Progress Log

Create:

```text
docs/FASTFLUENT_HORIZONTAL_H3_5_PROGRESS_20260623.md
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

## G.2 Delivery Report

Create:

```text
docs/FASTFLUENT_HORIZONTAL_H3_5_DELIVERY_20260623.md
```

It must include:

```text
- Goal summary.
- Why this stage validates FastFluent without Fluent execution.
- Files changed.
- New CLI commands.
- Generated validation pack path.
- Number of generated cases.
- Per-module case count.
- Test commands and results.
- Patch validation results.
- Known limitations.
- Explicit statement that Fluent was not launched.
- Recommended next goal.
```

---

## G.3 Validation Summary

Create:

```text
sandbox/output/fastfluent_horizontal_validation_pack/validation_summary.md
```

It should be a readable report that can be used in README or thesis discussion.

Include:

```text
- Overall validation conclusion.
- H1 VOF/turbulence/rheology summary.
- H2 steam-air v2 summary.
- H3 solid-liquid summary.
- Combined patch stress-test summary.
- What this validation proves.
- What this validation does not prove.
```

The "does not prove" section must say:

```text
This validation pack does not prove high-fidelity Fluent accuracy.
It validates FastFluent-native physical screening, artifact generation,
patch compilation, and regression behavior.
```

---

# Implementation Notes

## 1. Do Not Overbuild

This goal should mostly use existing modules and add validation cases.

Avoid rewriting H1-H3 modules unless a bug is found.

If a bug is found, fix it narrowly and add a regression test.

---

## 2. Keep Synthetic Cases Simple

Use public synthetic cases only.

Do not use private CAD, private meshes, private Fluent cases, or proprietary results.

---

## 3. Manifest-Driven Design

Prefer creating a central registry for validation cases, for example:

```text
src/fromcad2cfd_fastcfd/horizontal_validation_pack.py
```

Suggested functions:

```python
create_validation_case_registry() -> list[dict]
run_horizontal_validation_pack(output_dir: Path) -> dict
write_validation_manifest(result: dict, output_path: Path) -> None
write_validation_summary(result: dict, output_path: Path) -> None
```

CLI should call `run_horizontal_validation_pack`.

---

## 4. Minimum Case Count

The validation pack should include at least:

```text
VOF: 4 cases
Turbulence: 4 cases
Rheology: 4 cases
Steam-air v2: 5 cases
Solid-liquid: 6 cases
Combined patches: 4 cases
```

Minimum total:

```text
27 cases
```

If a module cannot support all cases due to missing H1-H3 functionality, document the limitation and implement the maximum supported cases. Do not fake results.

---

## 5. Status Handling

Each case should have:

```text
expected_status
actual_status
status_match
warnings
blocking_errors
```

Status values:

```text
pass
warn
block
```

If expected and actual status do not match, the validation summary should flag the case.

---

## 6. Patch Validation

For each generated patch:

```text
validate_solver_plan_patch(patch) must be called.
```

Record:

```text
patch_valid
patch_status
patch_operation_count
evidence_count
warnings
blocking_errors
```

---

## 7. Evidence Requirements

Every patch operation in these groups must have evidence refs:

```text
physics
materials
numerics
transient
monitors
source_terms
acceptance_criteria
```

If an operation lacks evidence refs, the validation pack should mark the case invalid.

---

# Acceptance Criteria

H3.5 is complete only if all are true:

```text
1. horizontal-validation-pack-demo CLI exists.
2. validation pack generates at least the required case directories or documents unsupported cases.
3. validation_manifest.json exists.
4. validation_summary.md exists.
5. H1 VOF / turbulence / rheology cases are generated.
6. H2 steam-air v2 cases are generated.
7. H3 solid-liquid cases are generated.
8. Combined patch stress cases are generated.
9. All generated patches validate or are intentionally blocked with documented reasons.
10. Formula/regime tests pass.
11. CLI tests pass.
12. Full pytest passes, or unrelated pre-existing failures are documented.
13. Delivery report is written.
14. Delivery report explicitly states Fluent was not launched and is not required.
```

Do not mark complete if:

```text
- only documents are generated without running FastFluent modules.
- CLI demo does not run.
- patches are not validated.
- tests are not run.
- missing artifacts are ignored.
- Fluent is launched.
```

---

# Explicit Stop Boundary

After H3.5, stop.

Do not start H4 inside this goal.

Do not implement:

```text
wax rheology / phase-change passport
Fluent execution adapter
PyFluent template generator
UDF lifecycle
trust report
OpenFOAM integration
```

Recommended next goal:

```text
H4: Wax Rheology / Phase-Change Passport
```

Reason:

```text
H4 directly connects measured wax material characterization to FastFluent evidence,
Fluent material-model recommendations, phase-change readiness, and the dewaxing thesis direction.
```

---

# Final Response Format Required From Codex

When finished, respond with:

```text
## FastFluent Horizontal H3.5 Delivery Summary

### Implemented

### Files changed

### New CLI commands

### Validation pack path

### Generated cases

### Patch validation results

### Test results

### Known limitations

### Explicit statement: Fluent was not launched

### Recommended next goal
```

Be precise.

Do not claim Fluent execution.

Do not claim high-fidelity CFD validation.

Do not claim final Fluent accuracy.
