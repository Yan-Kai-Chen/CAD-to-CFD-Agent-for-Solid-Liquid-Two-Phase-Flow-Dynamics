# Solver Plan Contract

Required fields:

- `schema_version`: `fromcad2cfd_fluent_solver_plan_v1`.
- `plan_name`: public-safe identifier.
- `mesh_input`, `case_output`, `data_output`: relative public paths by default.
- `physics`: solver family, transient state, energy, species, turbulence, density.
- `boundaries`: zone-name keyed boundary settings.
- `transient`: fixed or adaptive time stepping.

Optional fields:

- `materials`
- `autosave`
- `monitors`
- `source_terms`
- `execution`

Public mode rejects absolute paths and local machine markers. Use
`--allow-absolute` only for private local validation.

Source terms should reference named public source models such as
`equivalent_condensation_mass_energy_v1` or
`near_wall_limited_condensation_v1`. Do not place raw Fluent expression strings
in public solver plans.
