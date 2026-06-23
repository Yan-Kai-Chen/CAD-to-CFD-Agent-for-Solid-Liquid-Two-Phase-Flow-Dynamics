# FastFluent Horizontal H3 Solid-Liquid Suspension Delivery

Date: 2026-06-23

## Goal Summary

H3 implements a solid-liquid suspension readiness passport for FastFluent. It
uses low-cost physical evidence to recommend a downstream Fluent multiphase
model class before any expensive Fluent setup is attempted.

## What Was Implemented

- Solid-liquid synthetic case schema.
- Solid-liquid suspension passport schema.
- Solid-liquid Fluent hints schema.
- Particle Reynolds number, relaxation time, Stokes number, settling velocity,
  residence/settling comparison, volume-fraction regime, mass loading,
  cell-particle ratio, and particle time-step risk.
- Conservative model recommendation logic.
- Solver-plan patch integration.
- Public CLI demo and staged CLI commands.
- Unit tests for physics, recommendation logic, patch generation, and CLI.

## Files Changed

- `src/fromcad2cfd_fastcfd/solid_liquid_suspension.py`
- `src/fromcad2cfd_fastcfd/fluent_patch_compiler.py`
- `src/fromcad2cfd_fastcfd/cli.py`
- `src/fromcad2cfd_fastcfd/capabilities.py`
- `src/fromcad2cfd_fastcfd/__init__.py`
- `tests/unit/test_fastcfd_solid_liquid_suspension.py`
- `docs/FASTFLUENT_HORIZONTAL_H3_PROGRESS_20260623.md`
- `docs/FASTFLUENT_HORIZONTAL_H3_DELIVERY_20260623.md`

## New Schema Versions

- `fromcad2cfd_fastfluent_solid_liquid_suspension_case_v1`
- `fromcad2cfd_fastfluent_solid_liquid_suspension_passport_v1`
- `fromcad2cfd_fastfluent_solid_liquid_suspension_fluent_hints_v1`

## New CLI Commands

```powershell
python -m fromcad2cfd fastcfd write-solid-liquid-demo --output-dir sandbox/output/solid_liquid_suspension_demo
python -m fromcad2cfd fastcfd validate-solid-liquid-suspension --case sandbox/output/solid_liquid_suspension_demo/solid_liquid_suspension_case.json --output-dir sandbox/output/solid_liquid_suspension_demo/passport
python -m fromcad2cfd fastcfd solid-liquid-handoff-demo --output-dir sandbox/output/solid_liquid_suspension_demo --format markdown
```

The generic compiler also supports the new passport:

```powershell
python -m fromcad2cfd fastcfd compile-fluent-patch --input sandbox/output/solid_liquid_suspension_demo/passport/solid_liquid_suspension_passport.json --output sandbox/output/solid_liquid_suspension_demo/solver_plan_patch.json
```

## Demo Artifacts

Verified output:

```text
sandbox/output/solid_liquid_suspension_demo/
  solid_liquid_suspension_case.json
  passport/
    solid_liquid_suspension_passport.json
    solid_liquid_suspension_fluent_hints.json
    solid_liquid_suspension_report.md
  solver_plan_patch.json
  solver_plan_patch_report.md
```

Observed demo status:

- Demo status: `success`
- Passport status: `warn`
- Recommended model: `dpm_one_way`
- Patch status: `warn`
- Patch operations: `18`
- Evidence records: `9`

## Test Commands And Results

Focused H3 and patch-contract test:

```powershell
python -m pytest -q tests/unit/test_fastcfd_solid_liquid_suspension.py tests/unit/test_fastcfd_existing_passport_patch_compiler.py tests/unit/test_fastcfd_solver_plan_patch.py -p no:cacheprovider
```

Result:

```text
31 passed in 0.36s
```

H3-related test filter:

```powershell
python -m pytest -q tests -k "solid_liquid or suspension or patch_compiler"
```

Result:

```text
28 passed, 238 deselected in 0.71s
```

Full repository test suite:

```powershell
python -m pytest -q
```

Result:

```text
266 passed in 8.84s
```

## Known Limitations

- No Fluent execution.
- No PyFluent execution.
- No Fluent case/data editing.
- No raw Fluent TUI generation.
- No arbitrary UDF generation.
- No particle trajectory solver.
- No DEM coupling.
- No dense granular solver.
- No OpenFOAM integration.
- No GPU acceleration.

## Recommended Next Goal

H4 should implement a wax rheology / phase-change passport. That route directly
connects wax material characterization to Fluent material-model and
phase-change setup evidence for the dewaxing thesis direction.
