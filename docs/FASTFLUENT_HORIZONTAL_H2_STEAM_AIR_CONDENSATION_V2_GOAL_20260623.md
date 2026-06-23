# FastFluent Horizontal H2 Goal: Steam-Air Condensation v2

Date: 2026-06-23

## Objective

Upgrade the existing steam-air condensation passport from a basic readiness gate into a richer engineering evidence module.

Current v1:
- saturation temperature estimate
- wall subcooling
- non-condensable gas risk
- thermal penetration depth
- near-wall resolution ratio
- time-step recommendation
- source stiffness risk

H2 adds:
- Reynolds number
- Prandtl number
- Peclet number
- Jakob number
- Stefan number
- HTC estimate
- Nusselt estimate
- mass-transfer resistance estimate
- stronger Fluent patch recommendations

Do NOT implement:
- Fluent execution
- UDF generation
- full condensation solver
- GPU acceleration

---

## Deliverable A: v2 Schemas

Create:

- fromcad2cfd_fastfluent_steam_air_condensation_case_v2
- fromcad2cfd_fastfluent_steam_air_condensation_passport_v2
- fromcad2cfd_fastfluent_steam_air_condensation_fluent_hints_v2

Suggested module:

src/fromcad2cfd_fastcfd/steam_air_condensation_v2.py

---

## Deliverable B: Dimensionless Groups

### Reynolds Number
Re = rho * U * L / mu

Output:
- reynolds_number
- flow_regime

### Prandtl Number
Pr = mu * cp / k

### Peclet Number
Pe = Re * Pr

### Jakob Number
Ja = cp * (Tsat - Twall) / latent_heat

### Stefan Number
Ste = cp * deltaT / latent_heat

---

## Deliverable C: Heat Transfer Estimate

Add:

- estimated_nusselt_number
- estimated_htc_W_m2K
- estimated_heat_flux_W_m2
- estimated_heat_transfer_rate_W

All correlations must store:
- correlation_name
- validity_range
- limitations

---

## Deliverable D: Non-Condensable Resistance

Compute:

- schmidt_number
- sherwood_number
- mass_transfer_coefficient

Output:

- non_condensable_layer_risk
- mass_transfer_resistance

Classification:
- low
- moderate
- high

---

## Deliverable E: Source-Term Checks

Validate:

- kg/(m^3*s)
- W/m^3
- latent heat consistency
- sign convention

Output:

- source_term_dimension_check
- source_term_sign_check
- source_term_stiffness_level

Patch recommendations:

- source ramping
- source clamp
- temperature bounds
- species bounds
- source integral monitor

---

## Deliverable F: Fluent Patch Expansion

Support:

- /physics/energy
- /physics/species_transport
- /physics/turbulence
- /transient
- /source_terms
- /monitors
- /postprocessing

New monitors:

- wall_heat_transfer_rate
- wall_temperature
- steam_mass_fraction
- air_mass_fraction
- max_temperature
- energy_balance
- source_term_integral

---

## Deliverable G: Public Demo

Generate:

sandbox/output/steam_air_v2_demo/

Artifacts:

- steam_air_condensation_case_v2.json
- steam_air_condensation_passport_v2.json
- steam_air_condensation_fluent_hints_v2.json
- solver_plan_patch.json
- steam_air_condensation_report_v2.md

---

## Tests

Add:

tests/unit/test_fastcfd_steam_air_condensation_v2.py

Required:

- valid case passes
- invalid species fractions fail
- Reynolds verified
- Prandtl verified
- Jakob verified
- patch generation verified
- demo generation verified

Run:

python -m pytest -q

---

## Acceptance Criteria

1. v2 schema exists
2. new dimensionless groups implemented
3. HTC estimate implemented
4. mass-transfer resistance estimate implemented
5. source dimensional checks implemented
6. patch output expanded
7. demo generated
8. tests pass
9. docs updated

---

## Next Goal

H3: Solid-Liquid Suspension Passport

Focus:
- particle Reynolds number
- Stokes number
- settling velocity
- residence time
- DPM vs Mixture vs Eulerian recommendation
- solver_plan_patch integration
