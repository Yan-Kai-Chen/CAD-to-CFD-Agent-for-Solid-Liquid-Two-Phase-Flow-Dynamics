# Fluent Solver Plan v2 Receiver + Patch Preview Goal

Date: 2026-06-22  
Repository: `CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics`  
Execution mode: Codex `/goal` mode  
Recommended save path: `docs/FLUENT_SOLVER_PLAN_V2_RECEIVER_GOAL_20260622.md`

---

## 0. Core Direction

This goal is intentionally limited.

The previous FastFluent milestone completed the evidence-to-Fluent handoff slice:

```text
steam-air demo case
-> steam-air condensation physics passport
-> Fluent setup hints
-> validated solver_plan_patch.json
-> Markdown handoff reports
```

The next step is to build the **minimum downstream receiver** for this patch.

The target workflow is:

```text
base_solver_plan_v2.json
+ solver_plan_patch.json
-> patched_solver_plan_preview.json
-> patch_application_report.md
-> conflict_report.json
-> before_after_diff.md
-> reviewer_checklist.md
```

This goal must not expand into Fluent execution, PyFluent execution, UDF generation, full diagnostics, or trust-report infrastructure.

This is the final minimal bridge before FastFluent horizontal expansion.

---

## 1. Strategic Purpose

The project now has FastFluent evidence artifacts, especially:

```text
solver_plan_patch.json
```

But there is not yet a canonical downstream Fluent solver plan that can receive and preview the patch.

Without this receiver, future FastFluent horizontal expansion will create many independent passport outputs without a unified Fluent-facing destination.

Therefore, this goal should implement:

```text
Fluent Solver Plan v2 schema
+ safe patch preview
+ conflict detection
+ human-readable review report
```

After this goal is complete, development should move into FastFluent horizontal physics expansion.

---

## 2. Hard Scope Boundary

### 2.1 Implement Only These

Implement:

```text
1. Fluent Solver Plan v2 schema and validator.
2. A public synthetic base solver plan example.
3. Patch application preview from solver_plan_patch.json.
4. Before/after diff report.
5. Conflict report.
6. Reviewer checklist.
7. Tests and docs.
```

### 2.2 Do Not Implement

Do not implement:

```text
- Fluent launch.
- PyFluent local execution.
- Arbitrary Fluent TUI commands.
- Arbitrary PyFluent commands.
- UDF generation.
- UDF compilation.
- Fluent case/data editing.
- Runtime diagnostics.
- Automatic recovery loop.
- Trust report.
- GPU acceleration.
- OpenFOAM integration.
- New physical passports in this goal.
```

This goal is a receiver and preview layer only.

---

## 3. Read First

Before editing, inspect:

```text
README.md
ROADMAP.md
docs/architecture.md

src/fromcad2cfd_fastcfd/solver_plan_patch.py
src/fromcad2cfd_fastcfd/fluent_patch_compiler.py
src/fromcad2cfd_fastcfd/steam_air_condensation.py
src/fromcad2cfd_fastcfd/cli.py
src/fromcad2cfd_fastcfd/capabilities.py

src/fromcad2cfd_fluent_solver/
src/fromcad2cfd_fluent_solver/schemas.py
src/fromcad2cfd_fluent_solver/monitor_contract.py
src/fromcad2cfd_mcp_fluent_solver/

tests/unit/test_fastcfd_solver_plan_patch.py
tests/unit/test_fastcfd_fluent_patch_compiler.py
tests/unit/test_fastcfd_steam_air_condensation.py
tests/unit/test_fastcfd_steam_air_cli.py
```

Append a short baseline note to:

```text
docs/FLUENT_SOLVER_PLAN_V2_RECEIVER_PROGRESS_20260622.md
```

Baseline note must include:

```text
- Existing FastFluent patch schema location.
- Existing Fluent solver schema status.
- Existing CLI commands.
- Existing tests relevant to patch generation.
- Initial test command result.
```

---

## 4. Main Deliverables

This goal has five deliverables.

```text
Deliverable A: Fluent Solver Plan v2 Schema
Deliverable B: Safe Patch Application Preview
Deliverable C: CLI Integration
Deliverable D: Tests
Deliverable E: Documentation
```

---

# Deliverable A: Fluent Solver Plan v2 Schema

## A.1 Purpose

Create a canonical downstream Fluent solver plan schema that can receive FastFluent `solver_plan_patch.json`.

Suggested module:

```text
src/fromcad2cfd_fluent_solver/solver_plan_v2.py
```

If the existing `schemas.py` should remain the public entry point, either:

```text
- add v2 functionality there with clean separation; or
- create solver_plan_v2.py and re-export stable functions from schemas.py.
```

Do not break existing Fluent solver APIs.

---

## A.2 Schema Version

Use:

```text
fromcad2cfd_fluent_solver_plan_v2
```

---

## A.3 Top-Level Fields

The top-level plan should include:

```text
schema_version
case_name
status
runtime
mesh
physics
materials
boundaries
numerics
initialization
transient
monitors
source_terms
autosave
postprocessing
acceptance_criteria
recovery_policy
warnings
blocking_errors
limitations
metadata
```

Allowed status:

```text
draft
ready_for_review
approved_for_template_generation
blocked
```

For this goal, the system should mostly create:

```text
ready_for_review
```

Do not auto-approve for execution.

---

## A.4 Runtime Section

Suggested fields:

```json
{
  "fluent_version": "review-required",
  "dimension": "3d",
  "precision": "double",
  "processor_count": 1,
  "mode": "solver",
  "execution_policy": "preview_only",
  "working_directory_policy": "relative_or_configured_only"
}
```

Validation:

```text
- dimension must be 2d or 3d.
- precision must be single or double.
- processor_count must be positive.
- execution_policy must remain preview_only in this goal.
```

---

## A.5 Mesh Section

Suggested fields:

```json
{
  "mesh_file": null,
  "mesh_source": "review-required",
  "cell_zones": [],
  "face_zones": [],
  "named_zone_contract": [],
  "mesh_quality_requirements": {
    "max_skewness": 0.95,
    "min_orthogonal_quality": 0.01,
    "negative_volume_allowed": false
  }
}
```

Validation:

```text
- No absolute private path should be required.
- Mesh may remain null for public preview examples.
- If named zones are provided, each must have name, type, and role.
```

---

## A.6 Physics Section

Suggested fields:

```json
{
  "solver": {
    "type": "pressure-based"
  },
  "time": "transient",
  "energy": {
    "enabled": false
  },
  "species_transport": {
    "enabled": false,
    "species": []
  },
  "multiphase": {
    "enabled": false,
    "model": null
  },
  "turbulence": {
    "model": "laminar",
    "near_wall_treatment": "review-required"
  },
  "material_model": "review-required",
  "mixture": {
    "species": []
  }
}
```

Validation:

```text
- solver.type must be pressure-based or density-based.
- time must be steady or transient.
- energy.enabled must be boolean.
- species_transport.enabled must be boolean.
- mixture.species must be a list.
- if species_transport.enabled is true, mixture.species must not be empty.
```

---

## A.7 Materials Section

Suggested fields:

```json
{
  "materials": [],
  "mixtures": [],
  "property_models": []
}
```

For this goal, do not require fully detailed Fluent material cards. Keep this schema reviewable but not execution-ready.

Validation:

```text
- Materials may be incomplete but must be explicitly marked review-required.
- No executable code is allowed.
```

---

## A.8 Boundaries Section

Suggested fields:

```json
{
  "boundary_conditions": [],
  "required_boundary_roles": [
    "inlet",
    "outlet",
    "wall"
  ],
  "unresolved_boundaries": []
}
```

Boundary condition object should support:

```text
name
role
type
zone_name
settings
review_status
```

Validation:

```text
- Every boundary condition must have name, role, type, zone_name.
- settings must not contain dangerous keys.
- unresolved_boundaries should trigger warning.
```

---

## A.9 Numerics Section

Suggested fields:

```json
{
  "pressure_velocity_coupling": "review-required",
  "initial_discretization": "first-order-upwind",
  "later_discretization": "second-order-upwind-after-stable-warmup",
  "gradient": "least-squares-cell-based",
  "under_relaxation": {},
  "source_term_controls": {
    "ramping": false,
    "clamp": false,
    "nan_guard": true
  }
}
```

Validation:

```text
- Initial discretization should be allowlisted.
- Source-term controls must be booleans.
- No raw solver command strings.
```

---

## A.10 Initialization Section

Suggested fields:

```json
{
  "method": "hybrid-or-review-required",
  "initial_fields": {},
  "patch_initialization": [],
  "review_required": true
}
```

---

## A.11 Transient Section

Suggested fields:

```json
{
  "initial_time_step_s": null,
  "adaptive_time_step": {
    "enabled": false,
    "max_courant_number": null
  },
  "total_time_s": null,
  "max_time_steps": null,
  "checkpoint_policy": "review-required"
}
```

Validation:

```text
- if time is transient, initial_time_step_s should be positive or warning.
- max_courant_number must be positive if provided.
```

---

## A.12 Monitors Section

Suggested fields:

```json
{
  "global": [],
  "wall": [],
  "residuals": {
    "enabled": true,
    "targets": {}
  },
  "mass_balance": {
    "enabled": false
  },
  "energy_balance": {
    "enabled": false
  }
}
```

Monitor object should support:

```text
name
quantity
reduction
zone
required
reason
```

Validation:

```text
- Each monitor must have name and quantity.
- Required monitors should be listed in reviewer checklist.
```

---

## A.13 Source Terms Section

Suggested fields:

```json
{
  "terms": [],
  "source_term_policy": {
    "allow_arbitrary_code": false,
    "allow_arbitrary_udf": false,
    "review_required": true
  }
}
```

Validation:

```text
- Arbitrary code is forbidden.
- Source term models may be named but not executable.
- Any source term should include units, sign convention, clamp/ramp recommendation if available.
```

---

## A.14 Autosave Section

Suggested fields:

```json
{
  "enabled": true,
  "case_interval": "review-required",
  "data_interval": "review-required",
  "checkpoint_on_warning": true
}
```

---

## A.15 Postprocessing Section

Suggested fields:

```json
{
  "required_outputs": [],
  "report_definitions": [],
  "export_policy": "preview_only"
}
```

---

## A.16 Acceptance Criteria Section

Suggested fields:

```json
{
  "residual_drop_orders": "review-required",
  "mass_imbalance_max": "review-required",
  "energy_imbalance_max": "review-required",
  "bounded_temperature_range_K": "review-required",
  "bounded_species_fraction": true,
  "monitor_plateau_required": true
}
```

---

## A.17 Recovery Policy Section

Suggested fields:

```json
{
  "enabled": false,
  "policy": "not_implemented_in_this_goal",
  "allowed_actions": []
}
```

Do not implement recovery in this goal.

---

## A.18 Dangerous Key Rejection

Reuse or mirror the dangerous-key rejection logic from the FastFluent patch layer.

Reject recursively:

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

This should apply to:

```text
solver_plan_v2.json
patch values
preview output
boundary settings
source term settings
metadata where relevant
```

---

## A.19 Required Functions

Implement:

```text
create_minimal_solver_plan_v2(case_name: str) -> dict
validate_solver_plan_v2(plan: dict) -> ValidationResult
write_solver_plan_v2_json(plan: dict, path: Path) -> None
write_solver_plan_v2_report(plan: dict, path: Path) -> None
```

ValidationResult should include:

```text
is_valid
status
warnings
blocking_errors
normalized_plan
```

---

# Deliverable B: Safe Patch Application Preview

## B.1 Purpose

Implement a safe preview function that applies a FastFluent `solver_plan_patch.json` to a Fluent Solver Plan v2 object without executing Fluent.

Suggested module:

```text
src/fromcad2cfd_fluent_solver/patch_preview.py
```

---

## B.2 Inputs

Input 1:

```text
base_solver_plan_v2.json
```

Input 2:

```text
solver_plan_patch.json
```

---

## B.3 Outputs

Required outputs:

```text
patched_solver_plan_preview.json
patch_application_report.md
conflict_report.json
before_after_diff.md
reviewer_checklist.md
```

---

## B.4 Supported Patch Operations

Support only the operations already defined by the FastFluent patch contract:

```text
add
replace
append_unique
warn
block
```

Interpretation:

```text
replace:
  replace value at a valid existing or creatable path.

add:
  add value at a valid path if missing.

append_unique:
  append to a list if not already present.

warn:
  add warning to preview report.

block:
  add blocking error and mark preview blocked.
```

If uncertain, block.

---

## B.5 Path Handling

Implement safe path traversal for slash paths like:

```text
/physics/energy/enabled
/transient/initial_time_step_s
/monitors/global
/source_terms/terms
```

Requirements:

```text
- Reject path traversal attempts.
- Reject empty unsafe path components.
- Reject paths outside Solver Plan v2 top-level allowlist.
- Do not allow modification of schema_version unless explicitly allowed.
- Do not allow modification of execution_policy away from preview_only in this goal.
```

Allowed top-level path prefixes:

```text
/runtime
/mesh
/physics
/materials
/boundaries
/numerics
/initialization
/transient
/monitors
/source_terms
/autosave
/postprocessing
/acceptance_criteria
/recovery_policy
/warnings
/blocking_errors
/limitations
/metadata
```

---

## B.6 Conflict Detection

Detect conflicts:

```text
- Two replace patches targeting the same path with different values.
- Patch attempts to modify preview-only execution policy.
- Patch attempts to add dangerous keys.
- Patch refers to unsupported path.
- Patch evidence is missing or invalid according to solver_plan_patch validator.
- Patched plan fails solver_plan_v2 validator.
```

Conflict report should include:

```text
conflict_id
severity
path
message
patch_indices
recommended_resolution
```

Severity:

```text
info
warn
block
```

---

## B.7 Before/After Diff

Generate a Markdown diff report:

```text
before_after_diff.md
```

It should include:

```text
- Changed paths
- Old value
- New value
- Patch reason
- Evidence references
```

Do not output excessive full JSON unless needed.

---

## B.8 Patch Application Report

Generate:

```text
patch_application_report.md
```

It should include:

```text
- Case name
- Base solver plan status
- Patch status
- Preview status
- Number of patches applied
- Number of warnings
- Number of conflicts
- Number of blocking errors
- Patch operations table
- Evidence summary
- Conflict summary
- Limitations
```

---

## B.9 Reviewer Checklist

Generate:

```text
reviewer_checklist.md
```

Checklist sections:

```text
## Physics
- Confirm solver type.
- Confirm transient or steady assumption.
- Confirm energy equation requirement.
- Confirm species transport requirement.
- Confirm multiphase model decision.
- Confirm turbulence model decision.

## Materials
- Confirm material property models.
- Confirm mixture species.
- Confirm density model.
- Confirm viscosity and thermal property assumptions.

## Boundaries
- Confirm inlet type and values.
- Confirm outlet type and backflow settings.
- Confirm wall thermal boundary condition.
- Confirm named zones.

## Numerics
- Confirm first-order warm-up.
- Confirm later second-order transition.
- Confirm pressure-velocity coupling.
- Confirm source ramp and clamp.

## Transient Controls
- Confirm initial time step.
- Confirm adaptive time stepping.
- Confirm total simulated time.
- Confirm checkpoint policy.

## Monitors
- Confirm residual targets.
- Confirm max/min temperature monitors.
- Confirm species bound monitors.
- Confirm wall heat transfer monitor.
- Confirm mass and energy balance monitors.

## Source Terms
- Confirm source term dimensions.
- Confirm sign convention.
- Confirm bounds and NaN guard.
- Confirm UDF or built-in model strategy.

## Execution Readiness
- Confirm mesh quality.
- Confirm no unresolved boundary zones.
- Confirm acceptance criteria.
- Confirm this preview has not executed Fluent.
```

---

## B.10 Required Functions

Implement:

```text
apply_solver_plan_patch_preview(base_plan: dict, patch: dict) -> PatchPreviewResult
write_patch_preview_bundle(result: PatchPreviewResult, output_dir: Path) -> None
write_patch_application_report(...)
write_conflict_report(...)
write_before_after_diff(...)
write_reviewer_checklist(...)
```

PatchPreviewResult should include:

```text
preview_status
base_plan
patch
patched_plan
applied_operations
skipped_operations
warnings
blocking_errors
conflicts
changed_paths
```

---

# Deliverable C: CLI Integration

## C.1 Suggested CLI Location

Update existing Fluent solver CLI if present. If not present, add a safe subcommand through the existing project CLI.

Preferred commands:

```bash
python -m fromcad2cfd fluent-solver write-plan-v2-demo   --output-dir sandbox/output/fluent_plan_v2_demo
```

Writes:

```text
sandbox/output/fluent_plan_v2_demo/base_solver_plan_v2.json
sandbox/output/fluent_plan_v2_demo/base_solver_plan_v2_report.md
```

---

```bash
python -m fromcad2cfd fluent-solver preview-patch   --base-plan sandbox/output/fluent_plan_v2_demo/base_solver_plan_v2.json   --patch sandbox/output/steam_air_demo/solver_plan_patch.json   --output-dir sandbox/output/fluent_plan_v2_demo/preview
```

Writes:

```text
sandbox/output/fluent_plan_v2_demo/preview/patched_solver_plan_preview.json
sandbox/output/fluent_plan_v2_demo/preview/patch_application_report.md
sandbox/output/fluent_plan_v2_demo/preview/conflict_report.json
sandbox/output/fluent_plan_v2_demo/preview/before_after_diff.md
sandbox/output/fluent_plan_v2_demo/preview/reviewer_checklist.md
```

Optional convenience command:

```bash
python -m fromcad2cfd fluent-solver plan-v2-patch-preview-demo   --patch sandbox/output/steam_air_demo/solver_plan_patch.json   --output-dir sandbox/output/fluent_plan_v2_patch_preview_demo
```

This should:

```text
create base solver plan v2
load patch
apply preview
write preview bundle
```

---

## C.2 Do Not Require FastFluent Demo To Already Exist

If `solver_plan_patch.json` is not provided, the convenience demo may create a small synthetic safe patch internally, or clearly instruct the user to run the FastFluent steam-air handoff demo first.

Preferred behavior:

```text
- If --patch is provided, use it.
- If --patch is omitted, write a small public synthetic patch and preview it.
```

---

## C.3 Capabilities Output

Update relevant capabilities output to include:

```text
fluent_solver_plan_v2
fluent_solver_patch_preview
fluent_solver_reviewer_checklist
```

Do not claim Fluent execution.

---

# Deliverable D: Tests

## D.1 Suggested Test Files

Add tests consistent with repository style:

```text
tests/unit/test_fluent_solver_plan_v2.py
tests/unit/test_fluent_solver_patch_preview.py
tests/unit/test_fluent_solver_plan_v2_cli.py
```

---

## D.2 Required Tests For Solver Plan v2

Test:

```text
- create_minimal_solver_plan_v2 returns valid plan.
- validator accepts valid minimal plan.
- validator rejects unsupported schema version.
- validator rejects dangerous keys.
- validator warns when transient time step is missing.
- validator rejects execution_policy other than preview_only for this goal.
- report writer creates markdown.
```

---

## D.3 Required Tests For Patch Preview

Test:

```text
- valid FastFluent patch applies to base solver plan.
- patched plan validates.
- replace operation works.
- add operation works.
- append_unique operation deduplicates monitor entries.
- warn operation adds warning.
- block operation marks preview blocked.
- unsupported path blocks.
- dangerous patch value blocks.
- conflicting replace operations generate conflict report.
- attempt to change execution_policy blocks.
- before_after_diff.md is written.
- reviewer_checklist.md is written.
```

---

## D.4 Required CLI Tests

Test:

```text
- write-plan-v2-demo writes base plan and report.
- preview-patch writes all preview artifacts.
- convenience demo writes full output bundle.
```

---

## D.5 Required Test Commands

Run:

```bash
python -m pytest -q
```

Also run targeted tests:

```bash
python -m pytest -q tests -k "solver_plan_v2 or patch_preview or fluent_solver"
```

If unrelated pre-existing tests fail, document:

```text
- failing test name
- failure message
- why unrelated
- whether new tests passed
```

---

# Deliverable E: Documentation

## E.1 Progress Log

Maintain:

```text
docs/FLUENT_SOLVER_PLAN_V2_RECEIVER_PROGRESS_20260622.md
```

Append after each major checkpoint:

```text
## Checkpoint N - <timestamp>

### Files changed

### Commands run

### Results

### Issues found

### Next action
```

---

## E.2 Final Delivery Report

Create:

```text
docs/FLUENT_SOLVER_PLAN_V2_RECEIVER_DELIVERY_20260622.md
```

Must include:

```text
- Goal summary
- What was implemented
- Files changed
- New modules
- New CLI commands
- Example commands
- Generated artifact list
- Test commands and results
- Known limitations
- Explicit stop boundary
- Recommended next work: FastFluent horizontal expansion
```

---

## E.3 Demo Artifact Tree

Expected artifact tree:

```text
sandbox/output/fluent_plan_v2_patch_preview_demo/
├── base_solver_plan_v2.json
├── base_solver_plan_v2_report.md
├── patch/
│   └── solver_plan_patch.json
└── preview/
    ├── patched_solver_plan_preview.json
    ├── patch_application_report.md
    ├── conflict_report.json
    ├── before_after_diff.md
    └── reviewer_checklist.md
```

If the demo uses an existing FastFluent patch from `sandbox/output/steam_air_demo`, document that.

---

# Implementation Notes

## 1. Keep It Minimal

This is not a large Fluent execution framework.

This is a minimal receiver:

```text
schema
validate
preview
diff
conflict report
reviewer checklist
```

Once this works, stop.

---

## 2. JSON Writing Requirements

Use:

```text
UTF-8
indent=2
sort_keys=True where useful
newline at EOF
```

---

## 3. Markdown Writing Requirements

Reports must be human-reviewable.

Use:

```text
clear headings
short tables
explicit status
explicit warnings
explicit blocking errors
explicit limitations
```

---

## 4. Safety Requirements

The entire goal must remain non-executing.

No generated artifact should be directly executable.

No field should allow arbitrary command injection.

Generated reports must state:

```text
This is a preview-only Fluent solver plan artifact. It has not launched Fluent and has not modified any Fluent case/data file.
```

---

# Acceptance Criteria

This goal is complete only when all are true:

```text
1. Fluent Solver Plan v2 schema exists.
2. Solver Plan v2 validator exists.
3. Patch preview function exists.
4. Preview can apply a valid solver_plan_patch.json.
5. Preview writes patched_solver_plan_preview.json.
6. Preview writes patch_application_report.md.
7. Preview writes conflict_report.json.
8. Preview writes before_after_diff.md.
9. Preview writes reviewer_checklist.md.
10. CLI commands are available.
11. Tests pass.
12. Documentation is written.
13. Final delivery report explicitly says the next step is FastFluent horizontal expansion.
```

Do not mark complete if the system drifts into Fluent execution or leaves the preview workflow untested.

---

# Explicit Stop Boundary

After this goal is complete, stop extending solver-plan audit infrastructure.

Do not continue adding:

```text
- more reviewer reports
- more safety wrappers
- local execution
- runtime diagnostics
- trust report
- UDF lifecycle
```

Those are future phases.

The immediate next project phase should be:

```text
FastFluent horizontal physics expansion
```

---

# Next Phase After This Goal: FastFluent Horizontal Expansion

After the receiver is complete, proceed to horizontal expansion.

Recommended order:

```text
1. Connect existing VOF passport to solver_plan_patch.json.
2. Connect existing turbulence passport to solver_plan_patch.json.
3. Connect existing rheology passport to solver_plan_patch.json.
4. Add mesh-quality passport to solver_plan_patch.json.
5. Strengthen steam-air condensation passport with dimensionless groups.
6. Add solid-liquid suspension passport.
7. Add wax rheology / melting-solidification readiness passport.
8. Add phase-change source-term dimensional checks.
9. Add unstructured heat-transfer mini benchmark evidence.
```

---

## Horizontal Expansion Issue 1: Existing Passport Patch Compiler Expansion

Goal:

```text
Extend fluent_patch_compiler.py so existing FastFluent passports can all emit solver_plan_patch.json operations.
```

Targets:

```text
VOF passport
turbulence passport
rheology passport
mesh-quality evidence
```

Expected outputs:

```text
- More patch compiler entrypoints.
- Patch evidence preserved.
- Conflicts detected.
- Tests added.
```

---

## Horizontal Expansion Issue 2: Strengthen Steam-Air Condensation Passport

Add:

```text
Reynolds number
Prandtl number
Peclet number
Jakob number
Nusselt / first-pass HTC estimate
non-condensable diffusion-layer resistance estimate
near-wall y+ or first-cell warning
latent heat source dimensional consistency check
source-term sign convention check
```

Purpose:

```text
Make the steam-air passport more physically meaningful for early steam impact and wall condensation setup decisions.
```

---

## Horizontal Expansion Issue 3: Solid-Liquid Suspension Passport

Add a new passport for solid-liquid flow readiness.

Suggested checks:

```text
particle diameter
particle density
fluid density
fluid viscosity
volume fraction
settling velocity estimate
Stokes number
particle Reynolds number
mixture density estimate
mixture viscosity warning
Eulerian vs DPM vs mixture-model recommendation
monitor recommendations
```

Output:

```text
solid_liquid_suspension_passport.json
solid_liquid_suspension_fluent_hints.json
solver_plan_patch.json
```

---

## Horizontal Expansion Issue 4: Wax Rheology / Melting-Solidification Passport

Add a passport relevant to dewaxing and wax flow.

Suggested checks:

```text
temperature range
viscosity model
Arrhenius viscosity parameters
softening temperature
melting interval
latent heat
thermal diffusivity
source-term stiffness
non-Newtonian warning
Fluent material model recommendation
monitor recommendations
```

Output:

```text
wax_rheology_phase_change_passport.json
wax_rheology_phase_change_fluent_hints.json
solver_plan_patch.json
```

---

## Final Response Format Required From Codex

When finished, respond with:

```text
## Fluent Solver Plan v2 Receiver Delivery Summary

### Implemented

### Files changed

### New CLI commands

### Demo artifacts

### Test results

### Known limitations

### Explicit stop boundary

### Next phase: FastFluent horizontal expansion
```

Be precise. Do not claim Fluent execution.
