# Fluent Solver Plan Contract

## Solver Plan v2 Preview Receiver

Schema version:

```text
fromcad2cfd_fluent_solver_plan_v2
```

Purpose:

```text
base_solver_plan_v2.json
+ solver_plan_patch.json
-> patched_solver_plan_preview.json
-> patch_application_report.md
-> conflict_report.json
-> before_after_diff.md
-> reviewer_checklist.md
```

Solver Plan v2 is a preview-only downstream receiver for FastFluent
`solver_plan_patch.json` artifacts. It allows an agent to inspect how
FastFluent evidence changes Fluent-facing setup intent without launching
Fluent, writing raw PyFluent or TUI commands, generating UDFs, or editing
Fluent case/data files.

Public commands:

```text
fromcad2cfd fluent-solver write-plan-v2-demo --output-dir sandbox/output/fluent_plan_v2_demo
fromcad2cfd fluent-solver preview-patch --base-plan sandbox/output/fluent_plan_v2_demo/base_solver_plan_v2.json --patch sandbox/output/steam_air_demo/solver_plan_patch.json --output-dir sandbox/output/fluent_plan_v2_demo/preview
fromcad2cfd fluent-solver plan-v2-patch-preview-demo --output-dir sandbox/output/fluent_plan_v2_patch_preview_demo
```

The v2 validator enforces:

- schema version and required top-level fields;
- `runtime.execution_policy = preview_only`;
- bounded runtime, mesh, physics, material, boundary, numerics, transient,
  monitor, source-term, postprocessing, and recovery-policy sections;
- recursive dangerous-key rejection for raw commands, code, UDFs, journals,
  shells, subprocesses, and eval/exec-style keys;
- fail-closed patch preview when paths, values, evidence, or plan validation
  are unsafe.

## Solver Plan v1 Validation And Advisory Template

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
