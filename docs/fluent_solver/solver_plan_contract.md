# Fluent Solver Plan Contract

Schema version:

```text
fromcad2cfd_fluent_solver_plan_v1
```

Required top-level fields:

- `plan_name`
- `mesh_input`
- `case_output`
- `data_output`
- `physics`
- `boundaries`
- `transient`

Public mode rejects local absolute paths and known private path markers.

The first implementation validates plans and writes advisory PyFluent templates.
It intentionally does not launch Fluent directly. A production run still
requires a local Fluent installation, license, validated mesh, and operator
approval.

See:

```text
examples/fluent_solver/basic_air_steam_fill/solver_plan.json
```
