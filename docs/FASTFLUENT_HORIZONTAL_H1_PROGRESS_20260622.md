# FastFluent Horizontal H1 Progress Log

Date: 2026-06-22

## Goal

Horizontal H1 connects existing FastFluent evidence artifacts to the Fluent
Solver Plan v2 handoff path without adding new physics solvers or launching
Fluent. The target is to compile already implemented VOF, turbulence, and
rheology passports into reviewed, non-executing `solver_plan_patch.json`
bundles.

## Baseline

Relevant infrastructure already existed before H1:

- Solver-plan patch contract and validator.
- Steam-air condensation passport to solver-plan patch compiler.
- Solver Plan v2 preview receiver in the Fluent-side package.
- VOF, turbulence, and rheology passport or hint artifacts.
- Patch merge logic with evidence preservation and conflict warnings.

Baseline targeted tests:

```powershell
python -m pytest -q tests/unit/test_fastcfd_solver_plan_patch.py tests/unit/test_fastcfd_fluent_patch_compiler.py tests/unit/test_fastcfd_steam_air_condensation.py tests/unit/test_fastcfd_steam_air_cli.py tests/unit/test_fluent_solver_patch_preview.py -p no:cacheprovider
```

Result:

```text
30 passed in 0.28s
```

## Implemented

- Added VOF passport to solver-plan patch compilation.
- Added turbulence passport to solver-plan patch compilation.
- Added rheology passport to solver-plan patch compilation.
- Extended the generic passport dispatcher to auto-detect supported H1
  schemas.
- Added hint-only dispatch for supported H1 Fluent hint schemas.
- Added a public combined H1 demo command:

```powershell
python -m fromcad2cfd fastcfd existing-passport-patch-demo --output-dir sandbox/output/fastfluent_h1_existing_patch_demo
```

- Added capability inventory entries for H1 patch compiler routes.
- Exported the new compiler functions from `fromcad2cfd_fastcfd`.
- Added tests for direct compilers, auto-detection, merge behavior, conflict
  warnings, CLI demo output, and unsupported-schema fail-closed behavior.

## Artifact Writer Notes

The local Windows repository path is long. During implementation, ordinary
relative Python paths and selected directory creation calls could fail near the
Windows path-length limit. The H1 demo uses long-path-safe writers for the new
patch artifacts, and the demo itself writes in-memory public passports instead
of relying on older module-specific demo writers.

## Demo Verification

Command:

```powershell
python -m fromcad2cfd fastcfd existing-passport-patch-demo --output-dir sandbox/output/fastfluent_h1_existing_patch_demo_check --format markdown
```

Result:

```text
Status: success
Combined patch status: warn
Combined evidence count: 13
Combined patch count: 29
```

Patch summary:

| Patch | Status | Patch operations | Evidence records | Warnings |
| --- | --- | ---: | ---: | ---: |
| VOF | pass | 14 | 5 | 0 |
| Turbulence | warn | 9 | 4 | 1 |
| Rheology | pass | 8 | 4 | 0 |
| Combined | warn | 29 | 13 | 1 |

The combined warning is expected: the demo turbulence passport is intentionally
review-sensitive and should not silently force a final production turbulence
setup.

## Current Stop Boundary

H1 stops at artifact compilation and preview handoff. It does not:

- execute Fluent,
- edit Fluent case or data files,
- call PyFluent,
- generate UDF source,
- introduce new VOF, turbulence, or rheology physics solvers.

## Final Verification

H1-related test filter:

```powershell
python -m pytest -q tests -k "vof or turbulence or rheology or existing_passport or patch_compiler"
```

Result:

```text
27 passed, 213 deselected in 2.11s
```

Full repository test suite:

```powershell
python -m pytest -q
```

Result:

```text
240 passed in 6.20s
```
