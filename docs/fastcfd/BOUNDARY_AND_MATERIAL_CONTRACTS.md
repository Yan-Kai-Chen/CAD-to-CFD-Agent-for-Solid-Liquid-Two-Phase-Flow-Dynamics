# FastFluent Boundary And Material Contracts

This document records the M2 shared contract layer for the general FastFluent
evidence engine. The goal is to stop each physics pack from inventing its own
boundary-condition and material vocabulary.

## Unit Contract

The unit contract scans CaseSpec-style payloads for recognized unit-suffixed
quantities such as:

- `length_m`
- `height_m`
- `density_kg_m3`
- `viscosity_pa_s`
- `velocity_m_s`
- `gauge_pressure_pa`
- `time_step_s`

It returns a machine-readable report with checked quantities, warnings, and
errors. Velocity vectors are allowed to include zero or negative components
because they encode direction.

## Boundary Contract

The boundary contract validates a zone-keyed boundary map.

Supported types:

- `velocity_inlet`
- `mass_flow_inlet`
- `pressure_inlet`
- `pressure_outlet`
- `outflow`
- `wall_no_slip`
- `wall_slip`
- `symmetry`
- `periodic`
- `heat_flux_wall`
- `convective_wall`
- `temperature_wall`
- `porous_jump`
- `fan_boundary`
- `source_zone`
- `interface`
- `opening`

Current demo command:

```powershell
python -m fromcad2cfd fastcfd bc validate-demo-pack --output-dir sandbox/output/bc_demo_pack
```

This writes:

- `boundary_conditions.json`
- `boundary_contract.json`
- `boundary_validation.md`
- `fluent_boundary_hints.json`

## Material Contract

The material contract validates a CaseSpec-style material dictionary.

Supported types:

- `constant_fluid`
- `temperature_dependent_fluid`
- `ideal_gas_lite`
- `solid_thermal`
- `porous_medium`
- `non_newtonian_fluid`
- `particle_phase`
- `two_phase_pair`

Current demo command:

```powershell
python -m fromcad2cfd fastcfd materials validate-demo-pack --output-dir sandbox/output/material_demo_pack
```

This writes:

- `materials.json`
- `material_contract.json`
- `material_property_table.csv`
- `material_model_report.md`
- `fluent_material_hints.json`

## Current Limitations

- The M2 contracts are validators and report writers, not solvers.
- Detailed unit conversion is not yet implemented; the current layer checks
  recognized SI-style names and positivity rules.
- The boundary and material contracts are additive. Existing passports and
  unstructured routes are preserved until adapters migrate them to the shared
  contract layer.
- Fluent hints remain advisory and do not edit Fluent case files.
