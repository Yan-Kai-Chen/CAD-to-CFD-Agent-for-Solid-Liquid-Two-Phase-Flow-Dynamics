# Basic Fluent Solver Plan Example

This example is a public-safe Fluent Solver planning artifact. It does not
include a private mesh, Fluent case, Fluent data file, or local ANSYS path.

Validate the plan:

```powershell
fromcad2cfd fluent-solver validate-plan --plan examples/fluent_solver/basic_air_steam_fill/solver_plan.json
```

Write an advisory PyFluent template:

```powershell
fromcad2cfd fluent-solver write-template `
  --plan examples/fluent_solver/basic_air_steam_fill/solver_plan.json `
  --output sandbox/output/basic_air_steam_fill_template.py
```

The generated template is a review artifact. Running Fluent still requires a
local ANSYS Fluent installation, license, and a real mesh supplied outside the
public repository.
