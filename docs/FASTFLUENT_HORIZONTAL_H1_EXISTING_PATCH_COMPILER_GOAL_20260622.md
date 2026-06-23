# FastFluent Horizontal H1 Goal: Existing Passport Patch Compiler Expansion

Date: 2026-06-22  
Repository: `CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics`  
Execution mode: Codex `/goal` mode  
Recommended save path: `docs/FASTFLUENT_HORIZONTAL_H1_EXISTING_PATCH_COMPILER_GOAL_20260622.md`

---

## 0. Goal Summary

Expand the existing FastFluent evidence-to-Fluent handoff workflow by connecting existing FastCFD / FastFluent physics passports and hint artifacts into the already implemented `solver_plan_patch.json` contract.

This is the first horizontal FastFluent expansion step.

The target workflow is:

```text
existing VOF / turbulence / rheology evidence
-> passport or hint artifact
-> fluent_patch_compiler.py
-> validated solver_plan_patch.json
-> Markdown patch report
-> tests and public demo artifacts
```

This goal should **not** create a new major physics model.

This goal should **not** implement Fluent execution.

This goal should **not** continue expanding audit infrastructure.

The purpose is to make existing FastFluent physical evidence useful for downstream Fluent setup planning.

---

## 1. Strategic Context

The project has already completed the first FastFluent evidence-to-Fluent handoff vertical slice for steam-air wall condensation:

```text
steam-air demo case
-> steam-air condensation physics passport
-> Fluent setup hints
-> validated solver_plan_patch.json
-> Markdown handoff reports
```

Now FastFluent should move from a single steam-air vertical slice to a broader horizontal physics evidence layer.

The first horizontal step is to connect existing evidence modules:

```text
VOF
turbulence
rheology
```

to the common patch artifact:

```text
solver_plan_patch.json
```

The key principle:

```text
Every physical recommendation must be evidence-backed and machine-readable.
```

Do not output only natural-language hints.

Do not make unsupported claims of CFD validation.

---

## 2. Hard Scope Boundary

### 2.1 Implement Only These

Implement:

```text
1. Existing VOF evidence -> solver_plan_patch.json.
2. Existing turbulence evidence -> solver_plan_patch.json.
3. Existing rheology evidence -> solver_plan_patch.json.
4. Merge support for mixed existing-passport patches.
5. Public synthetic demos.
6. Unit tests.
7. Documentation and delivery report.
```

### 2.2 Do Not Implement

Do not implement:

```text
- New steam-air condensation v2.
- New solid-liquid suspension passport.
- New wax phase-change passport.
- New mesh-physics readiness passport unless a minimal existing mesh-quality artifact is already present and easy to connect.
- Fluent execution.
- PyFluent execution.
- Fluent case/data editing.
- UDF generation.
- UDF compilation.
- OpenFOAM integration.
- GPU acceleration.
- Production multiphase solver.
- Full Navier-Stokes solver rewrite.
- New Fluent Solver Plan v2 audit/report expansion beyond what is needed to consume patches.
```

This goal is strictly about **using existing FastFluent evidence** to generate standardized Fluent-facing patches.

---

## 3. Read First

Before editing, inspect the current implementation.

Read:

```text
README.md
ROADMAP.md
docs/architecture.md

src/fromcad2cfd_fastcfd/
src/fromcad2cfd_fastcfd/vof.py
src/fromcad2cfd_fastcfd/turbulence.py
src/fromcad2cfd_fastcfd/rheology.py
src/fromcad2cfd_fastcfd/fluent_hints.py
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
src/fromcad2cfd_fastcfd/solver_plan_patch.py
src/fromcad2cfd_fastcfd/steam_air_condensation.py
src/fromcad2cfd_fastcfd/cli.py
src/fromcad2cfd_fastcfd/capabilities.py
src/fromcad2cfd_fastcfd/unstructured/

tests/unit/test_fastcfd_solver_plan_patch.py
tests/unit/test_fastcfd_fluent_patch_compiler.py
tests/unit/test_fastcfd_steam_air_condensation.py
tests/unit/test_fastcfd_steam_air_cli.py
```

If a Fluent Solver Plan v2 receiver already exists, also inspect:

```text
src/fromcad2cfd_fluent_solver/solver_plan_v2.py
src/fromcad2cfd_fluent_solver/patch_preview.py
tests/unit/test_fluent_solver_plan_v2.py
tests/unit/test_fluent_solver_patch_preview.py
```

Append a baseline note to:

```text
docs/FASTFLUENT_HORIZONTAL_H1_PROGRESS_20260622.md
```

The baseline note must include:

```text
- Existing VOF artifact schema or available functions.
- Existing turbulence artifact schema or available functions.
- Existing rheology artifact schema or available functions.
- Existing solver_plan_patch contract status.
- Existing fluent_patch_compiler supported inputs.
- Initial test command result.
```

---

## 4. Main Deliverables

This goal has six deliverables.

```text
Deliverable A: Evidence Adapter Inventory
Deliverable B: VOF Patch Adapter
Deliverable C: Turbulence Patch Adapter
Deliverable D: Rheology Patch Adapter
Deliverable E: CLI / Demo Integration
Deliverable F: Tests and Documentation
```

---

# Deliverable A: Evidence Adapter Inventory

## A.1 Purpose

Create a clear inventory of which existing FastFluent artifacts can already be converted into `solver_plan_patch.json`.

Suggested output file:

```text
docs/FASTFLUENT_HORIZONTAL_H1_EVIDENCE_ADAPTER_INVENTORY_20260622.md
```

It should list:

```text
VOF:
  existing module
  existing public functions
  existing artifact schema
  available calculated quantities
  available Fluent hints
  adapter status

Turbulence:
  existing module
  existing public functions
  existing artifact schema
  available calculated quantities
  available Fluent hints
  adapter status

Rheology:
  existing module
  existing public functions
  existing artifact schema
  available calculated quantities
  available Fluent hints
  adapter status
```

If a module does not currently have a stable passport schema, do not invent a large new framework. Add a minimal adapter from the existing structured result or hint artifact.

---

## A.2 Adapter Design Rule

Each adapter should produce:

```text
PatchEvidence[]
PatchOperation[]
SolverPlanPatch
```

Each patch operation must preserve evidence.

No patch operation should be generated without evidence.

If evidence is incomplete, generate a warning or block operation rather than a confident physics patch.

---

# Deliverable B: VOF Patch Adapter

## B.1 Purpose

Connect existing VOF evidence or hints to `solver_plan_patch.json`.

Preferred implementation location:

```text
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
```

If cleaner, add a small helper module:

```text
src/fromcad2cfd_fastcfd/vof_patch_adapter.py
```

But avoid unnecessary file sprawl.

---

## B.2 Supported Input

Use the current existing VOF API and artifacts found in:

```text
src/fromcad2cfd_fastcfd/vof.py
```

If an existing VOF passport exists, support it.

If only a structured result or Fluent hints object exists, support that.

The adapter should accept either:

```text
- a dict loaded from a VOF passport or hint JSON; or
- an existing internal structured result object converted to dict.
```

---

## B.3 VOF Evidence To Preserve

Preserve available evidence such as:

```text
density_liquid
density_gas
viscosity_liquid
viscosity_gas
surface_tension
velocity_scale
length_scale
gravity
cell_size
time_step
Re
We
Ca
Bo
Fr
density_ratio
viscosity_ratio
CFL
capillary_time_scale
gravity_time_scale
recommended_time_step
VOF suitability status
limitations
```

Only preserve evidence that is actually available from the current implementation.

Do not fabricate missing values.

---

## B.4 VOF Patch Operations

Generate patches where supported by evidence:

```text
/physics/multiphase/enabled = true
/physics/multiphase/model = "vof"
/physics/surface_tension/enabled = true
/physics/surface_tension/value_N_m = <surface_tension if available>
/transient/initial_time_step_s = <recommended_time_step if available>
/transient/adaptive_time_step/enabled = true
/numerics/initial_discretization = "first-order-upwind"
/n numerics/later_discretization = "second-order-upwind-after-stable-warmup"
/monitors/global += volume_fraction_bounds
/monitors/global += courant_number
/monitors/global += phase_mass_conservation
/postprocessing/required_outputs += phase_volume_history
/acceptance_criteria/bounded_volume_fraction = true
```

Correct typo requirement:

```text
Use /numerics/later_discretization, not /n numerics/later_discretization.
```

---

## B.5 VOF Warnings

Generate warnings if evidence indicates:

```text
- high CFL
- very high density ratio
- very high viscosity ratio
- strong capillary time-step restriction
- interface likely under-resolved
- missing surface tension while VOF is recommended
- VOF model recommendation is uncertain
```

If the current VOF evidence cannot support a particular warning, document it as a limitation rather than inventing it.

---

## B.6 VOF Acceptance Criteria

At minimum:

```text
- VOF patch generation creates a valid solver_plan_patch.json.
- Every physics, transient, numerics, monitor, and acceptance criteria patch has evidence refs.
- append_unique monitor patches deduplicate correctly.
- VOF public demo artifact can be generated.
```

---

# Deliverable C: Turbulence Patch Adapter

## C.1 Purpose

Connect existing turbulence evidence or hints to `solver_plan_patch.json`.

Preferred implementation location:

```text
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
```

If cleaner, add:

```text
src/fromcad2cfd_fastcfd/turbulence_patch_adapter.py
```

---

## C.2 Supported Input

Use current existing turbulence API and artifacts from:

```text
src/fromcad2cfd_fastcfd/turbulence.py
```

Support the existing turbulence passport or structured result if available.

---

## C.3 Turbulence Evidence To Preserve

Preserve available evidence such as:

```text
Re
velocity_scale
length_scale
density
viscosity
hydraulic_diameter
turbulence_intensity
estimated_y_plus
first_cell_height
boundary_layer_resolution_status
recommended_turbulence_model
near_wall_treatment_recommendation
limitations
```

Do not fabricate missing values.

---

## C.4 Turbulence Patch Operations

Generate patches where supported by evidence:

```text
/physics/turbulence/model = "laminar" | "k-omega-sst" | "realizable-k-epsilon" | "review-required"
/physics/turbulence/near_wall_treatment = <recommendation>
/mesh/near_wall/target_y_plus = <target if available>
/monitors/global += wall_y_plus
/monitors/wall += wall_shear_stress
/monitors/wall += skin_friction_coefficient_if_available
/numerics/initial_discretization = "first-order-upwind"
/numerics/later_discretization = "second-order-upwind-after-stable-warmup"
/acceptance_criteria/y_plus_review_required = true
```

If the turbulence recommendation is uncertain, do not force a model. Use:

```text
/physics/turbulence/model = "review-required"
```

with a warning and evidence.

---

## C.5 Turbulence Warnings

Generate warnings if:

```text
- Re is in transition regime.
- y+ is inconsistent with the recommended model.
- first cell height is missing but SST is recommended.
- turbulence intensity is missing or out of typical range.
- laminar recommendation is uncertain.
```

---

## C.6 Turbulence Acceptance Criteria

At minimum:

```text
- Turbulence patch generation creates a valid solver_plan_patch.json.
- Model recommendation patch includes evidence.
- y+ monitor patch includes evidence.
- Uncertain turbulence regime produces warning or review-required model rather than overconfident patch.
```

---

# Deliverable D: Rheology Patch Adapter

## D.1 Purpose

Connect existing rheology evidence or hints to `solver_plan_patch.json`.

Preferred implementation location:

```text
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
```

If cleaner, add:

```text
src/fromcad2cfd_fastcfd/rheology_patch_adapter.py
```

---

## D.2 Supported Input

Use current existing rheology API and artifacts from:

```text
src/fromcad2cfd_fastcfd/rheology.py
```

Support existing rheology passport, structured result, or Fluent hints if available.

---

## D.3 Rheology Evidence To Preserve

Preserve available evidence such as:

```text
viscosity_model
temperature_range
viscosity_range
viscosity_ratio
arrhenius_A
arrhenius_B
activation_energy
shear_rate_range
power_law_index
carreau_parameters
thermal_sensitivity
apparent_Re_range
non_newtonian_status
limitations
```

Only preserve available fields.

Do not fabricate missing values.

---

## D.4 Rheology Patch Operations

Generate patches where supported by evidence:

```text
/materials/property_models += temperature_dependent_viscosity
/materials/property_models += non_newtonian_viscosity
/physics/material_model = "temperature-dependent-viscosity" | "non-newtonian-review-required"
/monitors/global += viscosity_min_max
/monitors/global += temperature_min_max
/acceptance_criteria/bounded_viscosity_range = true
/numerics/source_term_controls/ramping = true
/numerics/source_term_controls/clamp = true
/postprocessing/required_outputs += viscosity_field_summary
```

If the current rheology artifact supports Arrhenius viscosity, include evidence and hints for:

```text
/materials/property_models += arrhenius_viscosity
```

But do not generate executable UDF code.

---

## D.5 Rheology Warnings

Generate warnings if:

```text
- viscosity ratio is very large.
- strong temperature sensitivity exists.
- non-Newtonian behavior is detected but Fluent model is not resolved.
- viscosity bounds are missing.
- temperature range is outside fitted model range.
- source-term or material-property stiffness risk is high.
```

---

## D.6 Rheology Acceptance Criteria

At minimum:

```text
- Rheology patch generation creates a valid solver_plan_patch.json.
- Viscosity monitor patches include evidence.
- Material-model patches include evidence.
- No arbitrary UDF source code is generated.
```

---

# Deliverable E: CLI / Demo Integration

## E.1 CLI Commands

Extend the existing FastCFD CLI without breaking current commands.

Preferred new commands:

```bash
python -m fromcad2cfd fastcfd existing-passport-patch-demo \
  --output-dir sandbox/output/fastfluent_h1_existing_patch_demo
```

This should generate a public synthetic demo bundle for:

```text
VOF
turbulence
rheology
combined
```

Expected output:

```text
sandbox/output/fastfluent_h1_existing_patch_demo/
├── vof/
│   ├── vof_input_or_passport.json
│   ├── solver_plan_patch.json
│   └── solver_plan_patch_report.md
├── turbulence/
│   ├── turbulence_input_or_passport.json
│   ├── solver_plan_patch.json
│   └── solver_plan_patch_report.md
├── rheology/
│   ├── rheology_input_or_passport.json
│   ├── solver_plan_patch.json
│   └── solver_plan_patch_report.md
└── combined/
    ├── combined_solver_plan_patch.json
    ├── combined_solver_plan_patch_report.md
    └── conflict_summary.json
```

If the repository style prefers separate commands, add:

```bash
python -m fromcad2cfd fastcfd vof-patch-demo --output-dir ...
python -m fromcad2cfd fastcfd turbulence-patch-demo --output-dir ...
python -m fromcad2cfd fastcfd rheology-patch-demo --output-dir ...
```

But one combined demo command is preferred for this goal.

---

## E.2 Patch Compiler CLI

Extend existing patch compiler CLI if present.

It should support:

```bash
python -m fromcad2cfd fastcfd compile-fluent-patch \
  --input <passport_or_hint.json> \
  --output <solver_plan_patch.json>
```

The compiler should auto-detect supported schema types:

```text
steam-air condensation passport
VOF passport or hint artifact
turbulence passport or hint artifact
rheology passport or hint artifact
```

If the input schema is unsupported, fail closed with a clear error.

---

## E.3 Capabilities Output

Update FastCFD capabilities output to include:

```text
vof_to_solver_plan_patch
turbulence_to_solver_plan_patch
rheology_to_solver_plan_patch
existing_passport_patch_demo
```

Do not claim Fluent execution.

---

# Deliverable F: Tests and Documentation

## F.1 Suggested Test Files

Add tests consistent with repository style.

Suggested files:

```text
tests/unit/test_fastcfd_existing_passport_patch_compiler.py
tests/unit/test_fastcfd_vof_patch_adapter.py
tests/unit/test_fastcfd_turbulence_patch_adapter.py
tests/unit/test_fastcfd_rheology_patch_adapter.py
tests/unit/test_fastcfd_existing_passport_patch_cli.py
```

If fewer files fit the repository style better, consolidate them.

---

## F.2 Required Tests

### VOF Tests

```text
- VOF demo artifact compiles into valid solver_plan_patch.json.
- VOF patch includes multiphase model recommendation with evidence.
- VOF patch includes monitor recommendations with evidence.
- High CFL or strong time-step restriction produces warning if supported by existing evidence.
```

### Turbulence Tests

```text
- Turbulence demo artifact compiles into valid solver_plan_patch.json.
- Turbulence model recommendation includes evidence.
- y+ or wall monitor recommendation includes evidence if supported.
- Transition or uncertain regime does not overclaim; it produces warning or review-required.
```

### Rheology Tests

```text
- Rheology demo artifact compiles into valid solver_plan_patch.json.
- Material property model recommendation includes evidence.
- Viscosity monitor recommendation includes evidence.
- No arbitrary UDF code is emitted.
```

### Merge Tests

```text
- VOF + turbulence + rheology patches merge into one valid combined patch.
- Duplicate append_unique monitor patches are deduplicated.
- Conflicting replace patches generate warning or block status.
- All evidence is preserved.
```

### CLI Tests

```text
- existing-passport-patch-demo writes expected artifact tree.
- compile-fluent-patch auto-detects VOF, turbulence, and rheology artifacts if supported.
- unsupported schema fails closed with clear error.
```

---

## F.3 Test Commands

Run:

```bash
python -m pytest -q
```

Run targeted tests:

```bash
python -m pytest -q tests -k "vof or turbulence or rheology or existing_passport or patch_compiler"
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

## F.4 Documentation

Create:

```text
docs/FASTFLUENT_HORIZONTAL_H1_PROGRESS_20260622.md
docs/FASTFLUENT_HORIZONTAL_H1_DELIVERY_20260622.md
docs/FASTFLUENT_HORIZONTAL_H1_EVIDENCE_ADAPTER_INVENTORY_20260622.md
```

Final delivery report must include:

```text
- Goal summary.
- What was implemented.
- Files changed.
- Supported input artifact types.
- New patch compiler entrypoints.
- New CLI commands.
- Demo artifact tree.
- Test commands and results.
- Known limitations.
- What was intentionally not implemented.
- Recommended next horizontal expansion goal.
```

---

# Implementation Details

## 1. Preferred Adapter API

Implement a consistent adapter API.

Suggested functions:

```python
def compile_vof_patch_from_artifact(artifact: dict, *, source_artifact: str | None = None) -> dict:
    ...

def compile_turbulence_patch_from_artifact(artifact: dict, *, source_artifact: str | None = None) -> dict:
    ...

def compile_rheology_patch_from_artifact(artifact: dict, *, source_artifact: str | None = None) -> dict:
    ...
```

If the existing project uses dataclasses, these functions may return `SolverPlanPatch` objects before serialization.

The public interface should still be easy to use from CLI.

---

## 2. Schema Auto-Detection

Implement schema auto-detection in `fluent_patch_compiler.py`.

Suggested logic:

```text
if schema_version contains "steam_air_condensation":
  compile steam-air patch

elif schema_version contains "vof":
  compile VOF patch

elif schema_version contains "turbulence":
  compile turbulence patch

elif schema_version contains "rheology":
  compile rheology patch

else:
  fail closed with unsupported schema error
```

If existing artifacts do not have schema_version, use a conservative detector based on required keys, but document this as provisional.

---

## 3. Evidence Construction

Every patch must refer to evidence IDs.

Suggested evidence IDs:

```text
vof_regime_numbers
vof_time_step_restriction
vof_density_viscosity_ratio
vof_surface_tension_importance
vof_monitor_requirements

turbulence_reynolds_regime
turbulence_y_plus_estimate
turbulence_model_recommendation
turbulence_wall_monitor_requirements

rheology_viscosity_model
rheology_viscosity_range
rheology_temperature_sensitivity
rheology_non_newtonian_status
rheology_monitor_requirements
```

Only create an evidence record if the underlying value exists.

---

## 4. Patch Validation

Use the existing `validate_solver_plan_patch(...)` function.

Every generated patch bundle must pass validation.

If it does not pass, fix the adapter rather than weakening validation.

Do not bypass the validator.

---

## 5. Combined Patch Behavior

The combined demo should merge:

```text
VOF patch
+ turbulence patch
+ rheology patch
```

Expected merge behavior:

```text
- preserve all evidence.
- deduplicate identical append_unique monitor patches.
- merge identical replace patches.
- warn or block conflicting replace patches.
- preserve highest severity.
```

If the existing `merge_solver_plan_patches(...)` already implements this, reuse it.

Do not create a second incompatible merge function.

---

## 6. Safety Rules

The new adapters must not generate:

```text
shell commands
raw Fluent TUI
raw PyFluent commands
arbitrary Python
arbitrary C/C++ UDF code
absolute private paths
case/data edits
execution instructions
```

Allowed outputs are:

```text
JSON planning artifacts
Markdown reports
warnings
blocking errors
review-required recommendations
```

---

# Acceptance Criteria

This goal is complete only when all are true:

```text
1. VOF evidence can generate a valid solver_plan_patch.json.
2. Turbulence evidence can generate a valid solver_plan_patch.json.
3. Rheology evidence can generate a valid solver_plan_patch.json.
4. Combined VOF + turbulence + rheology patch can be generated.
5. Patch evidence is preserved.
6. Duplicate append_unique patches are deduplicated.
7. Conflicting replace patches are reported.
8. Existing steam-air patch compiler still works.
9. Existing FastCFD CLI commands still work.
10. New demo command writes public artifacts.
11. New tests pass.
12. Full test suite passes, or unrelated pre-existing failures are documented.
13. Final delivery report is written.
```

Do not mark complete if only one adapter works.

Do not mark complete if patches are generated but fail validation.

Do not mark complete if evidence references are missing.

---

# Explicit Stop Boundary

After this goal is complete, stop.

Do not start implementing:

```text
steam-air v2
solid-liquid suspension passport
wax phase-change passport
mesh-physics readiness passport
Fluent execution adapter
PyFluent template generator
UDF lifecycle
trust report
```

Those are later goals.

The immediate next horizontal goal should be one of:

```text
H2: Steam-Air Condensation v2
H3: Solid-Liquid Suspension Passport
H4: Wax Rheology Phase-Change Passport
```

Recommended next goal:

```text
H2: Steam-Air Condensation v2
```

Reason:

```text
It deepens the already completed steam-air vertical slice and is directly relevant to early steam impact, wall condensation, non-condensable gas effects, and Fluent source-term stability.
```

---

# Final Response Format Required From Codex

When finished, respond with:

```text
## FastFluent Horizontal H1 Delivery Summary

### Implemented

### Files changed

### Supported artifacts

### New CLI commands

### Demo artifacts

### Test results

### Known limitations

### Explicit stop boundary

### Recommended next horizontal goal
```

Be precise.

Do not claim Fluent execution.

Do not claim final CFD validation.
