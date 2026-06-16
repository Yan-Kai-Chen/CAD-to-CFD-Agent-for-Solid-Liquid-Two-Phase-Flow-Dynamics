---
name: fromcad2cfd-fluent-solver
description: Public-safe Fluent Solver setup planning for FromCAD2CFD. Use when validating Fluent solver plans, designing transient controls, defining monitor contracts, generating advisory PyFluent templates, or preparing resume plans without exposing private mesh/case/data files or launching raw Fluent commands.
---

# FromCAD2CFD Fluent Solver

Use this skill for public-safe Fluent Solver setup planning.

## Rules

- Do not commit private geometry, `.msh.h5`, `.cas.h5`, `.dat.h5`, license files, or local ANSYS paths.
- Use relative paths under `sandbox/` in public examples.
- Validate a solver plan before generating templates.
- Treat generated PyFluent scripts as review artifacts unless a local operator explicitly approves execution.
- Do not expose raw PyFluent, Fluent TUI, arbitrary journals, or raw source-expression editing as MCP tools.
- For resumes, read a complete checkpoint and do not run standard initialization.
- For Fluent 2024 R1 adaptive resumes, set `total_time` to the absolute target flow time.

## Workflow

1. Create or edit a solver plan JSON matching `fromcad2cfd_fluent_solver_plan_v1`.
2. Validate it:

```powershell
fromcad2cfd fluent-solver validate-plan --plan examples/fluent_solver/basic_air_steam_fill/solver_plan.json
```

3. Inspect the monitor contract:

```powershell
fromcad2cfd fluent-solver monitor-contract
```

4. Generate a PyFluent template only after validation:

```powershell
fromcad2cfd fluent-solver write-template --plan <plan.json> --output sandbox/output/template.py
```

5. Keep direct Fluent launch outside the public MCP surface.

## References

- Solver plan fields: `references/solver_plan_contract.md`
- Runtime and resume guardrails: `references/transient_and_resume_guardrails.md`
