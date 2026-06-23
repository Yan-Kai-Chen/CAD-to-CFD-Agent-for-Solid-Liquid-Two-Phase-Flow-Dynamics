# FastFluent Horizontal H2 Steam-Air Condensation v2 Evidence Inventory

Date: 2026-06-23

## Evidence Matrix

| Evidence ID | Quantity | Purpose |
| --- | --- | --- |
| `steam_air_v2_reynolds_number` | Reynolds number and flow regime | Select laminar/review-required turbulence setup intent. |
| `steam_air_v2_prandtl_number` | Prandtl number | Thermal transport scale for setup review. |
| `steam_air_v2_peclet_number` | Peclet number | Convective thermal transport indicator. |
| `steam_air_v2_jakob_number` | Jakob number | Sensible-to-latent heat scale for condensation screening. |
| `steam_air_v2_stefan_number` | Stefan number | Wall subcooling and latent-heat source scale. |
| `steam_air_v2_heat_transfer_estimate` | Nu, HTC, heat flux, heat-transfer rate | Wall heat-transfer monitor and output planning. |
| `steam_air_v2_mass_transfer_resistance` | Sc, Sh, mass-transfer coefficient, resistance | Non-condensable layer risk and species monitor planning. |
| `steam_air_v2_source_term_dimension_check` | Mass and energy source dimensions | Source-term activation guard. |
| `steam_air_v2_source_term_sign_check` | Steam sink and energy release signs | Source sign convention guard. |
| `steam_air_v2_source_term_stiffness` | Source stiffness ratio and level | Time-step, ramping, and clamp planning. |
| `steam_air_v2_species_consistency` | Steam plus air mass-fraction closure | Species transport and species-bound monitor guard. |

## Patch Coverage

The v2 passport compiler expands recommendations under these allowlisted
solver-plan paths:

- `/physics/energy`
- `/physics/species_transport`
- `/physics/turbulence`
- `/physics/material_model`
- `/physics/mixture/species`
- `/transient`
- `/source_terms/condensation`
- `/monitors/global`
- `/monitors/wall`
- `/postprocessing/required_outputs`
- `/acceptance_criteria`

## Required Monitors

H2 adds or reinforces:

- `wall_heat_transfer_rate`
- `wall_temperature`
- `steam_mass_fraction`
- `air_mass_fraction`
- `max_temperature`
- `energy_balance`
- `source_term_integral`

## Correlation Metadata

Each heat-transfer and mass-transfer estimate stores:

- `correlation_name`
- `validity_range`
- `limitations`

The correlations are setup-scale estimates only. They are not final
correlation validation for a private device geometry.

## Public Demo Artifact Tree

```text
sandbox/output/steam_air_v2_demo/
  steam_air_condensation_case_v2.json
  steam_air_condensation_passport_v2.json
  steam_air_condensation_fluent_hints_v2.json
  solver_plan_patch.json
  solver_plan_patch_report.md
  steam_air_condensation_report_v2.md
```

