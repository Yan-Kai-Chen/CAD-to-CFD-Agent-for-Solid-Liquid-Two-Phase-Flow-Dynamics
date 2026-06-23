# FastFluent Horizontal H3 Solid-Liquid Suspension Progress Log

Date: 2026-06-23

## Goal

H3 adds a solid-liquid suspension setup-readiness passport. It estimates
particle-flow regime, sedimentation tendency, coupling strength, numerical
risk, and Fluent model suitability before expensive Fluent setup.

This remains a FastFluent evidence and handoff layer. It does not execute
Fluent, generate UDF code, solve particle trajectories, run DEM, or perform
Eulerian multiphase CFD.

## Baseline

Existing before H3:

- `solver_plan_patch.json` contract and validator.
- Patch compiler with steam-air, VOF, turbulence, rheology, and steam-air v2
  support.
- FastCFD CLI patterns for `write-*`, `validate-*`, and `*-demo` commands.
- Passport style from VOF, turbulence, rheology, and steam-air modules.
- Solver Plan v2 receiver exists downstream as preview-only infrastructure.

Baseline targeted check after adding H3:

```powershell
python -m pytest -q tests/unit/test_fastcfd_solid_liquid_suspension.py tests/unit/test_fastcfd_existing_passport_patch_compiler.py tests/unit/test_fastcfd_solver_plan_patch.py -p no:cacheprovider
```

Result:

```text
31 passed in 0.36s
```

## Implemented

- Added `src/fromcad2cfd_fastcfd/solid_liquid_suspension.py`.
- Added schemas:
  - `fromcad2cfd_fastfluent_solid_liquid_suspension_case_v1`
  - `fromcad2cfd_fastfluent_solid_liquid_suspension_passport_v1`
  - `fromcad2cfd_fastfluent_solid_liquid_suspension_fluent_hints_v1`
- Added physical calculations:
  - particle Reynolds number,
  - Stokes drag / transitional / inertial drag classification,
  - particle relaxation time,
  - Stokes number,
  - settling velocity and direction,
  - residence time versus settling time,
  - solid volume-fraction regime,
  - particle mass loading,
  - cell-particle size ratio,
  - particle time-step ratio,
  - recommended initial time step.
- Added conservative Fluent model recommendation:
  - `dpm_one_way`
  - `dpm_two_way`
  - `mixture_model`
  - `eulerian_multiphase_review`
  - `eulerian_granular_review`
  - `review_required`
- Added solver-plan patch compiler support for solid-liquid passports.
- Added CLI commands:

```powershell
python -m fromcad2cfd fastcfd write-solid-liquid-demo --output-dir sandbox/output/solid_liquid_suspension_demo
python -m fromcad2cfd fastcfd validate-solid-liquid-suspension --case sandbox/output/solid_liquid_suspension_demo/solid_liquid_suspension_case.json --output-dir sandbox/output/solid_liquid_suspension_demo/passport
python -m fromcad2cfd fastcfd solid-liquid-handoff-demo --output-dir sandbox/output/solid_liquid_suspension_demo --format markdown
```

## Demo Verification

Command:

```powershell
python -m fromcad2cfd fastcfd solid-liquid-handoff-demo --output-dir sandbox/output/solid_liquid_suspension_demo --format markdown
```

Result:

```text
Status: success
Passport status: warn
Recommended model: dpm_one_way
Patch status: warn
Patch count: 18
Evidence count: 9
```

Key computed quantities:

| Quantity | Value |
| --- | ---: |
| Particle Reynolds number | 24.95 |
| Particle drag regime | transitional_particle_drag |
| Particle relaxation time | 0.00036805555555555555 s |
| Stokes number | 0.0036805555555555554 |
| Particle inertia regime | particles_strongly_follow_fluid |
| Settling velocity | 0.00225085 m/s |
| Settling regime | negligible |
| Residence time | 0.1 s |
| Settling time | 8.885532132305574 s |
| Solid volume fraction regime | dilute |
| Particle mass loading | 0.013343269453479824 |
| Coupling strength regime | one_way_may_be_acceptable |
| Cell-particle ratio | 20.0 |
| Particle time-step ratio | 0.27169811320754716 |
| Particle time-step risk | marginal |
| Recommended time step | 3.6805555555555556e-05 s |
| Recommended model | dpm_one_way |

The passport and patch are `warn` because the demo has transitional particle
drag and marginal particle time-step resolution. This is expected.

## Stop Boundary

H3 stops at case, passport, Fluent hints, solver-plan patch, report, and demo
artifact generation. It does not:

- execute Fluent,
- call PyFluent,
- edit Fluent case/data files,
- generate UDF code,
- solve particle trajectories,
- perform DEM coupling,
- implement a dense granular solver,
- implement a full Eulerian multiphase solver.

## Final Verification

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
