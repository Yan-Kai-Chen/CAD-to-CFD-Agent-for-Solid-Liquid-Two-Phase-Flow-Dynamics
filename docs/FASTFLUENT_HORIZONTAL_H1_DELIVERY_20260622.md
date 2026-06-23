# FastFluent Horizontal H1 Delivery

Date: 2026-06-22

## Delivered Capability

FastFluent Horizontal H1 makes existing VOF, turbulence, and rheology evidence
usable by the Fluent Solver Plan v2 preview workflow. Each source can now emit
a validated, non-executing `solver_plan_patch.json` bundle with explicit
evidence, warnings, limitations, and reviewer-facing Markdown reports.

## Main Entry Points

Python API:

- `compile_vof_patch_from_artifact`
- `compile_turbulence_patch_from_artifact`
- `compile_rheology_patch_from_artifact`
- `compile_solver_plan_patch_from_passport`
- `run_existing_passport_patch_demo`

CLI:

```powershell
python -m fromcad2cfd fastcfd compile-fluent-patch --input <passport_or_hints.json> --output <solver_plan_patch.json>
python -m fromcad2cfd fastcfd existing-passport-patch-demo --output-dir sandbox/output/fastfluent_h1_existing_patch_demo
```

## Demo Artifacts

Verified demo directory:

```text
sandbox/output/fastfluent_h1_existing_patch_demo_check/
```

The demo generated:

- VOF passport input plus `solver_plan_patch.json` and Markdown report.
- Turbulence passport input plus `solver_plan_patch.json` and Markdown report.
- Rheology passport input plus `solver_plan_patch.json` and Markdown report.
- Combined patch plus Markdown report and `conflict_summary.json`.

Observed demo status:

| Bundle | Status | Patch operations | Evidence records | Warnings |
| --- | --- | ---: | ---: | ---: |
| VOF | pass | 14 | 5 | 0 |
| Turbulence | warn | 9 | 4 | 1 |
| Rheology | pass | 8 | 4 | 0 |
| Combined | warn | 29 | 13 | 1 |

## Tests

Focused H1 and related patch-compiler tests:

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

## Known Limitations

- The patch compiler does not run Fluent.
- The patch compiler does not edit Fluent case or data files.
- The patch compiler does not call PyFluent.
- Rheology support does not generate UDF code.
- The VOF adapter does not solve pressure, momentum, surface tension, or
  interface reconstruction.
- Turbulence support records model and near-wall setup intent, but it is not a
  production RANS, DES, LES, or wall-function validation route.

## Recommended Next Horizontal Goal

H2 should extend the existing steam-air condensation work with a second
receiver-facing evidence route, while keeping the same stop boundary:
artifact generation, solver-plan patch compilation, and preview-only Fluent
solver plan application.
