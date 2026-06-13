# FastFluent VOF Physics Passport

The VOF gate is an agent-safe physics validation and Fluent setup-hint layer for
immiscible two-phase interface problems. It is not a VOF solver and does not
claim to replace Fluent.

## Commands

Write a public-safe demo input:

```powershell
python -m fromcad2cfd fastcfd write-vof-demo --output-dir 05_projects\vof_demo\input
```

Validate the VOF passport and write Fluent setup hints:

```powershell
python -m fromcad2cfd fastcfd validate-vof --case-file examples\fastcfd\vof_dambreak2d_passport\vof_case.json --output-dir 05_projects\vof_demo\reports --format json
```

## Input Contract

The current VOF case schema is `fromcad2cfd_fastfluent_vof_case_v1`.

Required content:

- `case_name`
- `model = vof_two_phase`
- domain length scale and cell length in `mm`
- at least two phases with density, dynamic viscosity, and initial volume
  fraction
- surface tension
- gravity vector
- reference velocity
- time step
- interface initialization metadata

The validator rejects dangerous schema keys such as `command`, `python`,
`shell`, `executable`, and `source_code`.

## Passport Checks

The VOF physics passport computes and records:

- phase density and viscosity ratios
- initial volume-fraction closure
- Reynolds number
- Weber number
- Bond number
- Capillary number
- Froude number
- VOF Courant number
- recommended time step by Courant target
- advisory capillary time step
- blocking errors, warnings, and remediation suggestions

Blocking conditions include missing/invalid physical values, volume fractions
that do not sum to one, and VOF Courant number above the accepted limit.

## Fluent Setup Hints

The setup-hint artifact recommends:

- VOF multiphase model
- transient pressure-based setup
- time-step ceiling
- geometric reconstruction or equivalent sharp-interface capturing
- near-interface and near-wall refinement
- monitoring for phase volume conservation, interface position, residuals,
  outlet backflow, and Courant number

Hints are emitted with explicit evidence from the passport. When the passport
fails, hints are marked blocked.

## Artifacts

`validate-vof` writes:

- `vof_case.json`
- `vof_physics_passport.json`
- `vof_fluent_setup_hints.json`
- `vof_report.md`
- `vof_status.json`

## Current Boundary

This gate prepares VOF setup decisions for later Fluent work. It does not run a
VOF solver, does not solve interface advection, and does not provide turbulence
model selection. Turbulence is handled by the separate turbulence passport so
VOF, near-wall resolution, and RANS setup evidence remain traceable as separate
artifacts.
