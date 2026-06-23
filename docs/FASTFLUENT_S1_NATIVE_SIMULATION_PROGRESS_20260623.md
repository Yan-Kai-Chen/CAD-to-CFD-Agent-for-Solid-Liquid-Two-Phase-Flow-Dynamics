# FastFluent S1 Native Simulation Progress Log

Date: 2026-06-23

## Baseline - 2026-06-23

### Files changed

- None at baseline.

### Commands run

```powershell
python -m pytest -q
```

### Results

- Initial full test result before S1 edits: `271 passed in 7.27s`.

### Issues found

- Existing structured FastFluent backend status: optional C++ route is present in project scope but not used as the S1 public-native validation requirement.
- Existing unstructured FVM backend status: available with channel validation, convergence, steady incompressible, scalar diffusion, obstacle evidence, VOF-lite alpha transport, and turbulence ladder routes.
- Existing VOF-lite / alpha transport status: available and writes history, QoI JSON, Markdown, and VTU alpha output.
- Existing turbulence ladder status: available as a bounded closure-comparison evidence route; individual tiers may warn or fail acceptance tolerance.
- Existing field export status: VTU field outputs are available from unstructured backends.
- Existing CLI status: no top-level S1 native simulation validation pack command existed.

### Next action

- Add a uniform native simulation artifact contract and registry-driven S1 runner.

## Checkpoint 1 - 2026-06-23

### Files changed

- `src/fromcad2cfd_fastcfd/native_simulation_artifacts.py`
- `src/fromcad2cfd_fastcfd/native_simulation_pack.py`

### Commands run

```powershell
python -B -c "import ast, pathlib; files=['src/fromcad2cfd_fastcfd/native_simulation_artifacts.py','src/fromcad2cfd_fastcfd/native_simulation_pack.py']; [ast.parse(pathlib.Path(f).read_text(encoding='utf-8'), filename=f) for f in files]; print('ast ok')"
python -B -c "from fromcad2cfd_fastcfd.native_simulation_pack import create_native_simulation_case_registry; r=create_native_simulation_case_registry(); print(len(r)); print([x.case_id for x in r])"
```

### Results

- AST parse passed.
- Registry contains 9 S1 cases:
  - 3 structured backend-status records.
  - 6 public native/unstructured routes.

### Issues found

- A direct `py_compile` attempt triggered a Windows pycache path issue in the deep repository path. The source was checked with AST parsing instead.

### Next action

- Add CLI, capabilities, tests, and long-path-safe output handling.

## Checkpoint 2 - 2026-06-23

### Files changed

- `src/fromcad2cfd_fastcfd/cli.py`
- `src/fromcad2cfd_fastcfd/capabilities.py`
- `src/fromcad2cfd_fastcfd/__init__.py`
- `tests/unit/test_fastcfd_native_simulation_artifacts.py`
- `tests/unit/test_fastcfd_native_simulation_pack.py`
- `tests/unit/test_fastcfd_native_simulation_cli.py`

### Commands run

```powershell
python -B -m fromcad2cfd fastcfd native-simulation-validation-pack-demo --output-dir sandbox/output/fastfluent_native_simulation_validation_pack --format markdown
python -m pytest -q tests/unit/test_fastcfd_native_simulation_artifacts.py tests/unit/test_fastcfd_native_simulation_pack.py tests/unit/test_fastcfd_native_simulation_cli.py
```

### Results

- First CLI attempt reached the S1 runner but exposed Windows long-path issues.
- Unit tests passed after long-path-safe writing and scanning were added:
  - `7 passed in 1.99s`.

### Issues found

- `Path.mkdir`, `Path.write_text`, `Path.rglob`, and normal `Path.exists` missed or failed on the deep `sandbox/output/fastfluent_native_simulation_validation_pack` tree.
- S1 writer and scanner were updated to use extended Windows paths where needed.
- Turbulence ladder generated closure-comparison artifacts but some tiers did not meet bounded acceptance tolerance; this is now recorded as `warn`, not production turbulence validation.

### Next action

- Run the real S1 output pack and write docs.

## Checkpoint 3 - 2026-06-23

### Files changed

- `docs/FASTFLUENT_S1_NATIVE_SIMULATION_VALIDATION_PACK_GOAL_20260623.md`
- `docs/FASTFLUENT_S1_NATIVE_SIMULATION_PROGRESS_20260623.md`
- `docs/FASTFLUENT_S1_NATIVE_SIMULATION_DELIVERY_20260623.md`
- `README.md`
- `docs/index.md`
- `docs/fastcfd/quickstart.md`
- `01_memory/20260623_fastfluent_s1_native_simulation_validation_pack_milestone.md`

### Commands run

```powershell
python -B -m fromcad2cfd fastcfd native-simulation-validation-pack-demo --output-dir sandbox/output/fastfluent_native_simulation_validation_pack --format markdown
python -m pytest -q tests -k "native_simulation or unstructured or vof_lite or turbulence_ladder or poiseuille"
python -m pytest -q
```

### Results

- S1 CLI result:
  - Status: `success`
  - Case count: `9`
  - Actual native simulation cases: `6`
  - Field-output cases: `6`
  - Convergence/history cases: `6`
  - Model-comparison cases: `2`
  - S1 complete: `True`
  - Fluent launched: `False`
- Targeted tests: `63 passed, 215 deselected in 8.53s`.
- Full tests: `278 passed in 8.70s`.

### Issues found

- Structured C++ cases are recorded as unavailable/status-only in this S1 pack. No fake structured field output is generated.
- Obstacle-channel evidence remains a geometry/mesh evidence route, not a solved obstacle-flow momentum route.
- Turbulence ladder is a bounded closure-comparison route with warning-level tolerance limitations.

### Next action

- Stop at S1. Recommended next goal: H4 wax rheology / phase-change passport.
