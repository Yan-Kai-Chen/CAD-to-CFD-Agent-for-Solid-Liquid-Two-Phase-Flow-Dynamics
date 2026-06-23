# FastFluent Horizontal H1 Evidence Adapter Inventory

Date: 2026-06-22

This inventory records which existing FastFluent evidence artifacts can now be
compiled into Fluent-facing `solver_plan_patch.json` bundles.

## Adapter Matrix

| Evidence source | Input schema | Compiler | Patch scope | Stop boundary |
| --- | --- | --- | --- | --- |
| VOF physics passport | `fromcad2cfd_fastfluent_vof_physics_passport_v1` | `compile_vof_patch_from_artifact` | transient VOF setup, surface tension, adaptive time step, Courant and interface monitors, phase-volume outputs | Does not solve VOF or reconstruct interfaces in Fluent |
| VOF Fluent hints | `fromcad2cfd_fastfluent_vof_fluent_hints_v1` | `compile_solver_plan_patch_from_passport` hint-only dispatch | review-gated hint evidence | Does not synthesize new physics beyond hints |
| Turbulence passport | `fromcad2cfd_fastfluent_turbulence_passport_v1` | `compile_turbulence_patch_from_artifact` | viscous-model family, near-wall treatment, target y-plus, wall monitors | Does not validate production RANS, DES, LES, or Fluent wall functions |
| Turbulence Fluent hints | `fromcad2cfd_fastfluent_turbulence_hints_v1` | `compile_solver_plan_patch_from_passport` hint-only dispatch | review-gated hint evidence | Does not force a final model when evidence is transitional |
| Rheology passport | `fromcad2cfd_fastfluent_rheology_passport_v1` | `compile_rheology_patch_from_artifact` | material viscosity model intent, viscosity range monitoring, source-term controls | Does not generate UDF code or run non-Newtonian CFD |
| Rheology Fluent hints | `fromcad2cfd_fastfluent_rheology_hints_v1` | `compile_solver_plan_patch_from_passport` hint-only dispatch | review-gated hint evidence | Does not create custom material functions |

## Evidence Records Emitted

VOF adapter:

- `vof_regime_numbers`
- `vof_time_step_restriction`
- `vof_density_viscosity_ratio`
- `vof_surface_tension_importance`
- `vof_monitor_requirements`

Turbulence adapter:

- `turbulence_reynolds_regime`
- `turbulence_y_plus_estimate`
- `turbulence_model_recommendation`
- `turbulence_wall_monitor_requirements`

Rheology adapter:

- `rheology_viscosity_model`
- `rheology_viscosity_range`
- `rheology_non_newtonian_status`
- `rheology_monitor_requirements`

## Patch Merge Behavior

`merge_solver_plan_patches` remains the combined-patch route. It:

- preserves unique evidence records,
- deduplicates identical patch operations,
- keeps `append_unique` monitor operations stable,
- emits warnings for conflicting `replace` operations,
- blocks if any input patch is blocked.

## Public Demo Artifact Tree

```text
sandbox/output/fastfluent_h1_existing_patch_demo/
  vof/
    vof_input_or_passport.json
    solver_plan_patch.json
    solver_plan_patch_report.md
  turbulence/
    turbulence_input_or_passport.json
    solver_plan_patch.json
    solver_plan_patch_report.md
  rheology/
    rheology_input_or_passport.json
    solver_plan_patch.json
    solver_plan_patch_report.md
  combined/
    combined_solver_plan_patch.json
    combined_solver_plan_patch_report.md
    conflict_summary.json
```

All artifacts are synthetic and public-safe. No private device geometry, mesh,
case, or data file is required.

