# FastFluent Horizontal H2 Steam-Air Condensation v2 Delivery

Date: 2026-06-23

## Delivered Capability

H2 adds a richer steam-air condensation evidence route for FastFluent. It
creates v2 case, passport, Fluent hints, solver-plan patch, and Markdown report
artifacts that can be reviewed before any future Fluent execution adapter is
allowed to consume them.

## Main Files

- `src/fromcad2cfd_fastcfd/steam_air_condensation_v2.py`
- `src/fromcad2cfd_fastcfd/fluent_patch_compiler.py`
- `src/fromcad2cfd_fastcfd/cli.py`
- `src/fromcad2cfd_fastcfd/capabilities.py`
- `src/fromcad2cfd_fastcfd/__init__.py`
- `tests/unit/test_fastcfd_steam_air_condensation_v2.py`

## CLI

```powershell
python -m fromcad2cfd fastcfd steam-air-v2-demo --output-dir sandbox/output/steam_air_v2_demo --format markdown
```

Optional staged commands:

```powershell
python -m fromcad2cfd fastcfd write-steam-air-v2-demo --output-dir sandbox/output/steam_air_v2_case
python -m fromcad2cfd fastcfd validate-steam-air-condensation-v2 --case sandbox/output/steam_air_v2_case/steam_air_condensation_case_v2.json --output-dir sandbox/output/steam_air_v2_passport
python -m fromcad2cfd fastcfd compile-fluent-patch --input sandbox/output/steam_air_v2_passport/steam_air_condensation_passport_v2.json --output sandbox/output/steam_air_v2_passport/solver_plan_patch.json
```

## Demo Artifacts

Verified demo directory:

```text
sandbox/output/steam_air_v2_demo/
```

Observed status:

- Demo status: `success`
- Passport status: `warn`
- Patch status: `warn`
- Patch operations: `27`
- Evidence records: `11`

The warning is expected because the public demo has high non-condensable layer
risk. It should proceed only as a reviewed setup recommendation, not as an
unconditional Fluent execution instruction.

## Known Limitations

- No Fluent execution.
- No PyFluent execution.
- No Fluent case/data editing.
- No UDF generation.
- No film-condensation solver.
- No final heat-transfer or mass-transfer validation.
- No GPU acceleration.

## Tests

Focused H2 and patch-compiler tests:

```powershell
python -m pytest -q tests -k "steam_air_condensation_v2 or steam_air or condensation or patch_compiler"
```

Result:

```text
34 passed, 217 deselected in 0.73s
```

Full repository test suite:

```powershell
python -m pytest -q
```

Result:

```text
251 passed in 6.18s
```

## Recommended Next Goal

H3 should implement the solid-liquid suspension passport:

- particle Reynolds number,
- Stokes number,
- settling velocity,
- residence time,
- DPM vs Mixture vs Eulerian recommendation,
- solver-plan patch integration.
