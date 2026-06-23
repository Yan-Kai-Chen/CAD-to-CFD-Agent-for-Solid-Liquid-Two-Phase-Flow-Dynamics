# FastFluent Horizontal H4 Wax Rheology / Phase-Change Progress

Date: 2026-06-23

## Scope

H4 adds an agent-safe wax rheology and phase-change evidence layer for
FastFluent. It converts a public synthetic wax material case into a readiness
passport, Fluent setup hints, and a non-executing solver-plan patch.

## Acceptance Gates

- A wax case schema is available for public demo data.
- A wax passport schema computes rheology, softening, thermal diffusion, and
  phase-change evidence.
- Fluent hints remain advisory and do not launch Fluent.
- The generic solver-plan patch compiler auto-detects the wax passport.
- The patch compiler remains fail-closed and rejects unsafe executable payloads.
- CLI commands can write a demo case, validate a case, generate a handoff demo,
  and compile a solver-plan patch.
- Tests cover formulas, classification logic, patch validation, CLI routes, and
  non-execution boundaries.

## Implemented

- `src/fromcad2cfd_fastcfd/wax_rheology_phase_change.py`
  - Wax case, passport, and Fluent hints schemas.
  - Arrhenius viscosity evidence.
  - Softening-window classification.
  - Storage-modulus drop evidence.
  - Thermal diffusivity and cell diffusion-time evidence.
  - Stefan-number and latent-heat energy-scale evidence.
  - Phase-change stiffness classification.
  - Recommended first-pass time-step estimate.
  - Markdown report and public handoff demo.
- `src/fromcad2cfd_fastcfd/fluent_patch_compiler.py`
  - Wax passport auto-detection.
  - Wax hint-only artifact support through warning patches.
- `src/fromcad2cfd_fastcfd/cli.py`
  - `write-wax-rheology-demo`
  - `validate-wax-rheology-phase-change`
  - `wax-rheology-handoff-demo`
- `src/fromcad2cfd_fastcfd/capabilities.py`
  - Wax capabilities in the FastFluent inventory.
- `src/fromcad2cfd_fastcfd/__init__.py`
  - Public exports for wax helpers.

## Demo Result

Command:

```powershell
python -B -m fromcad2cfd fastcfd wax-rheology-handoff-demo --output-dir sandbox/output/wax_rheology_phase_change_demo --format markdown
```

Observed result:

```text
Status: success
Passport status: warn
Material model recommendation: arrhenius_viscosity
Patch status: warn
Patch count: 23
Evidence count: 11
```

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

## Boundaries

- Fluent was not launched.
- PyFluent was not called.
- No Fluent case or data files were modified.
- No Fluent TUI journal was generated.
- No executable UDF source was generated.
- The output is setup evidence and solver-plan advice, not production wax
  phase-change CFD validation.
