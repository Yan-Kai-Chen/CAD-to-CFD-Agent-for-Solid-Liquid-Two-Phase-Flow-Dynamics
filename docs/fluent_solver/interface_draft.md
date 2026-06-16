# Fluent Solver Interface

The first public-safe Fluent Solver interface validates solver plans and writes
advisory PyFluent templates. It does not launch Fluent directly and does not
store private mesh, case, data, license, or local ANSYS installation files.

Implemented commands:

```text
fromcad2cfd fluent-solver validate-plan --plan <solver_plan.json>
fromcad2cfd fluent-solver monitor-contract
fromcad2cfd fluent-solver write-template --plan <solver_plan.json> --output <template.py>
fromcad2cfd fluent-solver validate-resume --plan <resume_plan.json>
```

Example:

```powershell
fromcad2cfd fluent-solver validate-plan --plan examples/fluent_solver/basic_air_steam_fill/solver_plan.json
```

MCP entry point:

```powershell
fromcad2cfd-fluent-solver-mcp --describe
fromcad2cfd-fluent-solver-mcp --list-tools
```

The MCP server exposes only plan validation, monitor contract, template writing,
and resume-plan validation tools. Raw PyFluent, Fluent TUI, arbitrary journals,
raw source-expression editing, and direct Fluent launch remain disabled.
