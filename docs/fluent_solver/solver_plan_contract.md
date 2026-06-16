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
The public default path is planning-first so the same plan can be audited
without requiring a Fluent license. A local execution adapter may launch Fluent
from this plan after a local Fluent installation, license, validated mesh, run
directory, parallel policy, and operator or workflow approval are provided.

See:

```text
examples/fluent_solver/basic_air_steam_fill/solver_plan.json
```
