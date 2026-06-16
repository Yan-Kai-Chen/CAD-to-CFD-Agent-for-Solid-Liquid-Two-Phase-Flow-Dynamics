# Fluent Solver Interface

The first public-safe Fluent Solver interface validates solver plans and writes
advisory PyFluent templates. The default public commands do not need a Fluent
runtime and do not store private mesh, case, data, license, or local ANSYS
installation files.

Direct Fluent execution is part of the intended agent workflow when a local
adapter is configured with an approved Fluent installation, license environment,
private mesh/case/data files, run directory, and parallel launch policy. The
portable interface keeps those machine-specific details outside public examples
while preserving the contract that a local runner can execute.

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

The MCP server exposes plan validation, monitor contract, template writing, and
resume-plan validation tools by default. Raw PyFluent, Fluent TUI, arbitrary
journals, and source-expression editing should not be exposed as uncontrolled
agent tools. Local Fluent launch belongs behind a controlled adapter that first
validates the plan, records the runtime configuration, writes monitor outputs,
and preserves restart checkpoints.

See also:

```text
docs/fluent_solver/local_execution_adapter.md
```
