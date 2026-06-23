# Fluent Solver Interface

The public-safe Fluent Solver interface validates solver plans, writes advisory
PyFluent templates, and previews FastFluent solver-plan patch handoff. The
default public commands do not need a Fluent runtime and do not store private
mesh, case, data, license, or local ANSYS installation files.

Direct Fluent execution is part of the intended agent workflow when a local
adapter is configured with an approved Fluent installation, license environment,
private mesh/case/data files, run directory, and parallel launch policy. The
portable interface keeps those machine-specific details outside public examples
while preserving the contract that a local runner can execute.

Implemented commands:

```text
fromcad2cfd fluent-solver capabilities --format json
fromcad2cfd fluent-solver validate-plan --plan <solver_plan.json>
fromcad2cfd fluent-solver monitor-contract
fromcad2cfd fluent-solver write-template --plan <solver_plan.json> --output <template.py>
fromcad2cfd fluent-solver validate-resume --plan <resume_plan.json>
fromcad2cfd fluent-solver write-plan-v2-demo --output-dir <output_dir>
fromcad2cfd fluent-solver preview-patch --base-plan <base_solver_plan_v2.json> --patch <solver_plan_patch.json> --output-dir <output_dir>
fromcad2cfd fluent-solver plan-v2-patch-preview-demo --output-dir <output_dir>
```

Example:

```powershell
fromcad2cfd fluent-solver validate-plan --plan examples/fluent_solver/basic_air_steam_fill/solver_plan.json
fromcad2cfd fluent-solver plan-v2-patch-preview-demo --output-dir sandbox/output/fluent_plan_v2_patch_preview_demo
```

The Solver Plan v2 receiver writes:

```text
base_solver_plan_v2.json
base_solver_plan_v2_report.md
patch/solver_plan_patch.json
preview/patched_solver_plan_preview.json
preview/patch_application_report.md
preview/conflict_report.json
preview/before_after_diff.md
preview/reviewer_checklist.md
```

These artifacts are review material only. They do not launch Fluent, do not
emit raw Fluent TUI or raw PyFluent calls, do not generate UDF source, and do
not modify Fluent case/data files.

MCP entry point:

```powershell
fromcad2cfd-fluent-solver-mcp --describe
fromcad2cfd-fluent-solver-mcp --list-tools
```

The MCP server exposes plan validation, monitor contract, template writing,
resume-plan validation, Solver Plan v2 demo writing, and Solver Plan v2 patch
preview tools by default. Raw PyFluent, Fluent TUI, arbitrary journals, and
source-expression editing should not be exposed as uncontrolled agent tools.
Local Fluent launch belongs behind a controlled adapter that first validates
the plan, records the runtime configuration, writes monitor outputs, and
preserves restart checkpoints.

See also:

```text
docs/fluent_solver/local_execution_adapter.md
```
