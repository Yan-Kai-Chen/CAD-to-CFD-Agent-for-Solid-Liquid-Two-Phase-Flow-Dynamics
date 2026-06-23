# FastFluent Horizontal H3.5 Validation Pack Delivery

Date: 2026-06-23

## Goal Summary

H3.5 delivers a FastFluent-native validation pack for H1-H3. It validates the
current horizontal evidence chain with public synthetic cases before any real
Fluent execution is attempted.

## What Was Implemented

- Public H1-H3 validation-pack runner.
- H1 cases for VOF, turbulence, and rheology passports.
- H2 cases for steam-air condensation v2 passports.
- H3 cases for solid-liquid suspension passports.
- Combined solver-plan patch cases for merge and conflict-report coverage.
- Validation manifest and Markdown summary output.
- CLI entry point.
- Unit tests for registry coverage, generated tree, expected block cases, CLI
  JSON output, and CLI Markdown output.
- Windows long-path-safe writing for validation-pack artifacts.

## Files Changed

- `src/fromcad2cfd_fastcfd/horizontal_validation_pack.py`
- `src/fromcad2cfd_fastcfd/cli.py`
- `tests/unit/test_fastfluent_horizontal_validation_pack.py`
- `docs/FASTFLUENT_HORIZONTAL_H3_5_VALIDATION_PACK_GOAL_20260623.md`
- `docs/FASTFLUENT_HORIZONTAL_H3_5_PROGRESS_20260623.md`
- `docs/FASTFLUENT_HORIZONTAL_H3_5_DELIVERY_20260623.md`
- `docs/index.md`
- `README.md`

## New CLI Command

```powershell
python -m fromcad2cfd fastcfd horizontal-validation-pack-demo --output-dir sandbox/output/fastfluent_horizontal_validation_pack
```

Markdown form:

```powershell
python -m fromcad2cfd fastcfd horizontal-validation-pack-demo --output-dir sandbox/output/fastfluent_horizontal_validation_pack --format markdown
```

## Validation Pack Path

```text
sandbox/output/fastfluent_horizontal_validation_pack
```

Top-level artifacts:

```text
validation_manifest.json
validation_summary.md
```

## Generated Cases

| Module | Count |
| --- | ---: |
| `vof` | 4 |
| `turbulence` | 4 |
| `rheology` | 4 |
| `steam_air_v2` | 5 |
| `solid_liquid` | 6 |
| `combined_patches` | 4 |

Total cases: `27`.

## Patch Validation Results

- Valid solver-plan patches: `27`
- Invalid solver-plan patches: `0`
- Blocking review cases: `2`
- Intentional block cases:
  - `vof_case_04_high_cfl_block`
  - `solid_liquid_case_06_cell_particle_block`
- Fluent launched: `False`

The CLI status is `partial` because the validation pack deliberately includes
blocked safety-gate cases. Patch schema validation still passed for all 27
cases.

## Test Results

Validation-pack unit tests:

```powershell
python -m pytest -q tests/unit/test_fastfluent_horizontal_validation_pack.py
```

Result:

```text
5 passed in 0.79s
```

Targeted H1-H3/H3.5 test filter:

```powershell
python -m pytest -q tests -k "vof or turbulence or rheology or steam_air or solid_liquid or validation_pack or patch_compiler"
```

Result:

```text
67 passed, 204 deselected in 2.85s
```

Full repository test suite:

```powershell
python -m pytest -q
```

Result:

```text
271 passed in 6.88s
```

## Known Limitations

- No Fluent execution.
- No PyFluent execution.
- No Fluent case/data editing.
- No raw Fluent TUI generation.
- No UDF generation.
- No production CFD accuracy validation.
- Synthetic cases only.
- The current deeply nested Windows development path can require long-path
  literal reads for manual inspection outside the validation-pack writer.

## Explicit Statement: Fluent Was Not Launched

Fluent was not launched. H3.5 generated FastFluent evidence, Fluent setup hints,
and non-executing `solver_plan_patch.json` artifacts only.

## Recommended Next Goal

H4 should focus on material and phase-change physics that strengthen the
horizontal-pipe research direction, while keeping the H3.5 validation pack as
the public regression gate for H1-H3 setup evidence.
