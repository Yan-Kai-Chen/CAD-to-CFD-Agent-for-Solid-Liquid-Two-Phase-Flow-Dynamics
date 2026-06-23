# FastFluent S1 Native Simulation Delivery

Date: 2026-06-23

## Goal Summary

S1 validates that FastFluent can produce public, reproducible native simulation
evidence without launching ANSYS Fluent. The goal moves the project beyond
passport-to-hint-to-patch artifacts by generating native simulation results,
convergence/history files, field outputs, QoI summaries, a validation manifest,
and passport-simulation alignment reports.

## Why S1 Validates FastFluent Without Fluent Execution

The S1 pack calls existing FastFluent/FastCFD-native routes only:

- unstructured finite-volume channel convergence;
- steady incompressible channel solving;
- public body-fitted obstacle mesh evidence;
- VOF-lite bounded alpha transport;
- turbulence ladder closure comparison;
- scalar diffusion field-output smoke benchmark.

The pack writes a native simulation artifact contract for each case and records
structured C++ routes as unavailable/status-only when they are not run. It does
not call ANSYS Fluent, PyFluent, raw Fluent TUI, UDF generation, private CAD,
private mesh, or Fluent case/data files.

## Files Changed

- `src/fromcad2cfd_fastcfd/native_simulation_artifacts.py`
- `src/fromcad2cfd_fastcfd/native_simulation_pack.py`
- `src/fromcad2cfd_fastcfd/cli.py`
- `src/fromcad2cfd_fastcfd/capabilities.py`
- `src/fromcad2cfd_fastcfd/__init__.py`
- `tests/unit/test_fastcfd_native_simulation_artifacts.py`
- `tests/unit/test_fastcfd_native_simulation_pack.py`
- `tests/unit/test_fastcfd_native_simulation_cli.py`
- `docs/FASTFLUENT_S1_NATIVE_SIMULATION_VALIDATION_PACK_GOAL_20260623.md`
- `docs/FASTFLUENT_S1_NATIVE_SIMULATION_PROGRESS_20260623.md`
- `docs/FASTFLUENT_S1_NATIVE_SIMULATION_DELIVERY_20260623.md`
- `README.md`
- `docs/index.md`
- `docs/fastcfd/quickstart.md`
- `01_memory/20260623_fastfluent_s1_native_simulation_validation_pack_milestone.md`

## New Modules

### `native_simulation_artifacts.py`

Defines the case-level `simulation_result.json` contract:

- schema version: `fromcad2cfd_fastfluent_native_simulation_result_v1`;
- required fields for backend status, runtime, mesh, numerics, convergence,
  QoI, field outputs, warnings, errors, limitations, and metadata;
- validation for status values and dangerous key names;
- writer for `simulation_result.json`.

### `native_simulation_pack.py`

Defines the S1 registry and runner:

- `create_native_simulation_case_registry`;
- `run_native_simulation_case`;
- `run_native_simulation_validation_pack`;
- `write_simulation_manifest`;
- `write_simulation_summary`;
- passport-simulation alignment report writers.

The runner uses a short staging directory for backend execution and copies
artifacts back into the requested output tree with Windows long-path-safe file
handling.

## New CLI Commands

```powershell
python -m fromcad2cfd fastcfd native-simulation-validation-pack-demo --output-dir sandbox/output/fastfluent_native_simulation_validation_pack
```

Markdown output:

```powershell
python -m fromcad2cfd fastcfd native-simulation-validation-pack-demo --output-dir sandbox/output/fastfluent_native_simulation_validation_pack --format markdown
```

## Backends Detected

- Structured C++ FastFluent backend: recorded as status-only/unavailable in S1
  pack when not run.
- Unstructured FVM backend: available.
- VOF-lite alpha transport: available.
- Turbulence ladder: available as bounded closure-comparison evidence with
  warning-level tolerance limitations.
- Scalar diffusion field benchmark: available.

## Simulation Cases Run

Output root:

```text
sandbox/output/fastfluent_native_simulation_validation_pack/
```

Case status summary:

- `pass`: 5
- `warn`: 1
- `unavailable`: 3

Backend status summary:

- `available`: 6
- `unavailable`: 3

Case index:

- `structured_cases/cavity2d_re_sweep`: unavailable/status-only.
- `structured_cases/channel2d_velocity_grid_sweep`: unavailable/status-only.
- `structured_cases/obstacle2d_shape_comparison`: unavailable/status-only.
- `unstructured_cases/poiseuille_channel_convergence`: pass.
- `unstructured_cases/steady_incompressible_channel`: pass.
- `unstructured_cases/obstacle_channel_evidence`: pass.
- `unstructured_cases/vof_lite_alpha_transport`: pass.
- `unstructured_cases/turbulence_ladder`: warn; closure-comparison artifacts
  were generated, but some tiers did not meet bounded acceptance tolerance.
- `unstructured_cases/scalar_diffusion_field_smoke`: pass.

Pack summary:

- Total cases: 9
- Actual native simulation/evidence cases run: 6
- Field-output cases: 6
- Convergence/history cases: 6
- Mesh/grid comparison cases: 2
- Model/closure comparison cases: 2
- S1 complete: true

## Cases Unavailable And Reasons

Structured C++ cases are recorded as unavailable because S1 prioritizes the
public native/unstructured routes and does not run the optional structured C++
backend in this validation pack. The pack does not fabricate structured field
outputs.

## Field Outputs Generated

The pack generated VTU/CSV outputs in at least these case directories:

- `unstructured_cases/poiseuille_channel_convergence/backend_raw/`
- `unstructured_cases/steady_incompressible_channel/backend_raw/`
- `unstructured_cases/obstacle_channel_evidence/backend_raw/`
- `unstructured_cases/vof_lite_alpha_transport/backend_raw/`
- `unstructured_cases/turbulence_ladder/backend_raw/`
- `unstructured_cases/scalar_diffusion_field_smoke/backend_raw/`

Examples include:

- `channel_solution.vtu`
- `steady_solution.vtu`
- `mesh.vtu`
- `vof_lite_alpha.vtu`
- `turbulent_channel_solution.vtu`
- `kepsilon_solution.vtu`
- `pressure_kepsilon_solution.vtu`
- `sst_solution.vtu`
- `solution.vtu`

## QoIs Generated

The generated QoIs include:

- Poiseuille channel: velocity L2 error, divergence, mass-balance proxy,
  residuals, observed grid-convergence order.
- Steady incompressible channel: mean/max speed, divergence, mass-flux
  relative imbalance, velocity boundary error.
- Obstacle channel evidence: blockage and clearance metrics, mesh/zone
  evidence.
- VOF-lite: alpha min/max, phase-volume balance, max Courant number, clipped
  volume.
- Turbulence ladder: closure tier comparison, selected evidence tier, per-tier
  field artifacts and warnings.
- Scalar diffusion: field error metrics, final residuals, linear-system
  metadata.

## Test Commands And Results

```powershell
python -m pytest -q tests/unit/test_fastcfd_native_simulation_artifacts.py tests/unit/test_fastcfd_native_simulation_pack.py tests/unit/test_fastcfd_native_simulation_cli.py
```

Result:

```text
7 passed in 1.99s
```

```powershell
python -m pytest -q tests -k "native_simulation or unstructured or vof_lite or turbulence_ladder or poiseuille"
```

Result:

```text
63 passed, 215 deselected in 8.53s
```

```powershell
python -m pytest -q
```

Result:

```text
278 passed in 8.70s
```

## Passport-Simulation Alignment Reports

Generated under:

```text
sandbox/output/fastfluent_native_simulation_validation_pack/passport_simulation_alignment/
```

Reports:

- `vof_passport_vs_vof_lite.md`
- `turbulence_passport_vs_turbulence_ladder.md`
- `rheology_passport_simulation_gap.md`
- `steam_air_v2_simulation_gap.md`
- `solid_liquid_passport_simulation_gap.md`

## Known Limitations

- S1 does not prove high-fidelity Fluent accuracy.
- S1 validates FastFluent-native simulation routes and artifact generation.
- S1 does not replace ANSYS Fluent for final engineering validation.
- Structured C++ FastFluent cases are status-only in this pack unless the
  optional backend is explicitly run in a later goal.
- Obstacle-channel evidence is a body-fitted geometry/mesh evidence route, not
  a solved obstacle-flow momentum route.
- VOF-lite is scalar alpha transport only.
- Turbulence ladder is a bounded local closure-comparison route, not production
  RANS, DES, or LES validation.
- Rheology, steam-air condensation v2, and solid-liquid suspension still have
  setup-evidence support but no native S1 field-simulation route.

## Explicit Statement That Fluent Was Not Launched

Fluent was not launched. PyFluent was not called. No Fluent case/data files were
read or modified. No raw Fluent TUI commands were emitted. No UDF source was
generated.

## Recommended Next Goal

H4: Wax Rheology / Phase-Change Passport.

Rationale: after S1 proves native FastFluent simulation artifact generation, H4
should connect measured wax material characterization, Arrhenius viscosity,
thermal softening, and phase-change readiness to FastFluent evidence and later
Fluent setup planning.
