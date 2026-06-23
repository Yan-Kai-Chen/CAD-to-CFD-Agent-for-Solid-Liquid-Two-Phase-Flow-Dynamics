# FastFluent Horizontal H4 Wax Rheology / Phase-Change Delivery

Date: 2026-06-23

## Goal Summary

H4 implements a wax rheology and phase-change readiness route for FastFluent.
It gives the agent a bounded engineering-evidence artifact before downstream
Fluent setup: material-property recommendation, source-term review hints,
monitor requirements, and a non-executing solver-plan patch.

## What Was Implemented

- Wax rheology / phase-change case schema.
- Wax rheology / phase-change passport schema.
- Wax rheology / phase-change Fluent hints schema.
- Arrhenius viscosity formula checks.
- Softening transition classification.
- Storage-modulus drop evidence.
- Thermal diffusivity, cell diffusion-time, and thermal time-step checks.
- Stefan-number and latent-heat energy-scale checks.
- Phase-change stiffness classification.
- Conservative material-model recommendation.
- Conservative transient time-step recommendation.
- Solver-plan patch integration.
- Hint-only warning patch integration.
- Public CLI demo and staged CLI commands.
- Unit tests for formulas, classifications, patch generation, safety, and CLI.

## Files Changed

- `src/fromcad2cfd_fastcfd/wax_rheology_phase_change.py`
- `src/fromcad2cfd_fastcfd/fluent_patch_compiler.py`
- `src/fromcad2cfd_fastcfd/cli.py`
- `src/fromcad2cfd_fastcfd/capabilities.py`
- `src/fromcad2cfd_fastcfd/__init__.py`
- `tests/unit/test_fastcfd_wax_rheology_phase_change.py`
- `tests/unit/test_fastcfd_wax_rheology_patch_compiler.py`
- `tests/unit/test_fastcfd_wax_rheology_cli.py`
- `docs/FASTFLUENT_HORIZONTAL_H4_WAX_RHEOLOGY_PHASE_CHANGE_GOAL_20260623.md`
- `docs/FASTFLUENT_HORIZONTAL_H4_WAX_RHEOLOGY_PHASE_CHANGE_PROGRESS_20260623.md`
- `docs/FASTFLUENT_HORIZONTAL_H4_WAX_RHEOLOGY_PHASE_CHANGE_DELIVERY_20260623.md`
- `docs/fastcfd/quickstart.md`
- `docs/index.md`

## New Schema Versions

- `fromcad2cfd_fastfluent_wax_rheology_phase_change_case_v1`
- `fromcad2cfd_fastfluent_wax_rheology_phase_change_passport_v1`
- `fromcad2cfd_fastfluent_wax_rheology_phase_change_fluent_hints_v1`

## New CLI Commands

```powershell
python -m fromcad2cfd fastcfd write-wax-rheology-demo --output-dir sandbox/output/wax_rheology_phase_change_demo
python -m fromcad2cfd fastcfd validate-wax-rheology-phase-change --case sandbox/output/wax_rheology_phase_change_demo/wax_rheology_phase_change_case.json --output-dir sandbox/output/wax_rheology_phase_change_demo/passport
python -m fromcad2cfd fastcfd wax-rheology-handoff-demo --output-dir sandbox/output/wax_rheology_phase_change_demo --format markdown
```

The generic compiler also supports the new passport:

```powershell
python -m fromcad2cfd fastcfd compile-fluent-patch --input sandbox/output/wax_rheology_phase_change_demo/passport/wax_rheology_phase_change_passport.json --output sandbox/output/wax_rheology_phase_change_demo/solver_plan_patch.json
```

## Demo Artifacts

Verified output:

```text
sandbox/output/wax_rheology_phase_change_demo/
  wax_rheology_phase_change_case.json
  passport/
    wax_rheology_phase_change_passport.json
    wax_rheology_phase_change_fluent_hints.json
    wax_rheology_phase_change_report.md
  solver_plan_patch.json
  solver_plan_patch_report.md
```

Observed demo status:

- Demo status: `success`
- Passport status: `warn`
- Material model recommendation: `arrhenius_viscosity`
- Patch status: `warn`
- Patch operations: `23`
- Evidence records: `11`

## Formula Tests

The H4 test pack verifies:

- Arrhenius viscosity at minimum, maximum, and reference temperature.
- Activation energy from Arrhenius `B * R`.
- Viscosity ratio over the temperature range.
- Thermal diffusivity and cell diffusion time.
- Thermal time-step ratio.
- Storage-modulus drop ratio.
- Softening heating time.
- Stefan number.
- Latent-heat energy density and source power scale.
- Recommended first-pass time step.

## Classification Tests

The H4 test pack verifies:

- `solid_like`, `softening_transition`, `crosses_softening_transition`,
  `flow_dominant`, and `unknown` softening regimes.
- `low`, `moderate`, `high`, and `extreme` viscosity sensitivity classes.
- `inside_fit_range`, `partly_outside_fit_range`, `outside_fit_range`, and
  `unknown` viscosity fit-range statuses.
- `low`, `moderate`, `high`, and `extreme` phase-change stiffness classes.

## Patch Validation Results

- Wax passport compiles into a valid `solver_plan_patch.json`.
- Generic `compile-fluent-patch` auto-detects the wax passport schema.
- Wax hint-only artifacts compile into warning-only patches.
- Blocked wax passports compile into block patches.
- Patch validation passes.
- Generated JSON contains no `udf_code`, `source_code`, or `raw_pyfluent`.

## Test Results

Targeted H4 / rheology / phase-change / patch-compiler filter:

```powershell
python -m pytest -q tests -k "wax or rheology or phase_change or patch_compiler"
```

Result:

```text
27 passed, 263 deselected in 0.82s
```

Full repository test suite:

```powershell
python -m pytest -q
```

Result:

```text
290 passed in 9.00s
```

## Known Limitations

- No Fluent execution.
- No PyFluent execution.
- No Fluent case/data editing.
- No raw Fluent TUI generation.
- No executable UDF generation.
- No production wax phase-change solver.
- No final dewaxing accuracy validation.
- No ProCAST, OpenFOAM, or GPU backend.
- Public synthetic material values only.

## Explicit Statement: Fluent Was Not Launched

Fluent was not launched. H4 generated FastFluent wax rheology / phase-change
evidence, Fluent setup hints, and non-executing `solver_plan_patch.json`
artifacts only.

## Recommended Next Goal

The next goal should connect H1-H4 evidence to the S1 native simulation
validation pack and public documentation, then decide whether to add one more
bounded wax-specific native simulation smoke case or pause for real Fluent
server-side validation.
