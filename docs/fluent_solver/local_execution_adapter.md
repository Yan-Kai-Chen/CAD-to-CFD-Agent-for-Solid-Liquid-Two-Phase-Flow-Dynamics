# Local Fluent Execution Adapter

The Fluent execution adapter is the machine-specific bridge between the
portable FromCAD2CFD agent workflow and a licensed local ANSYS Fluent runtime.

It is not a replacement for Fluent. It is an agent-controlled runtime boundary
that turns a validated solver plan into a reproducible local run package,
launches Fluent when the environment is configured, monitors progress, and
keeps enough artifacts for resume and post-processing.

## Design Position

FromCAD2CFD separates Fluent automation into two layers:

- `Portable workflow contract`
  Solver plans, monitor contracts, resume rules, source-term definitions,
  post-processing plans, and public examples that can be reviewed without a
  Fluent installation.
- `Local execution adapter`
  Machine-specific launch and runtime behavior: Fluent executable path,
  license environment, MPI/core count, mesh/case/data inputs, journals,
  PyFluent scripts, run directories, autosaves, and rendered exports.

This separation lets the public repository remain reproducible while still
leaving direct Fluent solving inside the intended agent workflow.

## Adapter Responsibilities

A local Fluent execution adapter should:

- validate the solver plan before launch;
- resolve the local Fluent executable or PyFluent launch route;
- verify that required mesh/case/data inputs exist in the private workspace;
- create a run directory and run manifest;
- record Fluent version, core count, dimensionality, precision, and launch
  arguments;
- write or select the journal/PyFluent driver from the validated plan;
- start Fluent with the requested parallel policy;
- keep required report monitors active;
- preserve autosaves and restart checkpoints;
- support resume from a complete checkpoint without standard initialization;
- export monitor files and post-processing-ready manifests;
- fail closed when required inputs, monitors, or checkpoints are missing.

## Minimum Runtime Configuration

A private workspace adapter should require explicit local configuration such as:

```yaml
fluent:
  executable: "path/to/fluent.exe"
  version_hint: "2024R1"
  precision: "double"
  dimension: "3d"
  cores: 32
  launcher: "fluent"
workspace:
  run_root: "sandbox/runs"
  allow_private_inputs: true
execution:
  default_mode: "dry_run"
  require_plan_validation: true
  require_monitor_contract: true
  require_checkpoint_for_resume: true
```

The public repository should not ship real private values for these fields.
Examples should use placeholders or synthetic files only.

## Agent Workflow

Typical execution flow:

1. Build or load a Fluent solver plan.
2. Validate the plan with `fromcad2cfd fluent-solver validate-plan`.
3. Generate an advisory PyFluent or journal template.
4. Resolve the local adapter configuration.
5. Create a run manifest under the local run directory.
6. Launch Fluent or perform a dry run, depending on adapter mode.
7. Monitor physical time, time step size, residual/convergence indicators,
   global pressure/temperature/species metrics, wall heat, wall pressure, and
   wall shear.
8. Save checkpoints and autosaves.
9. Resume from complete checkpoints when interrupted.
10. Hand monitor files and manifests to the post-processing layer.

## Safety Boundary

The adapter should not expose arbitrary Fluent console access as a general MCP
tool. High-level agent commands should map to bounded actions:

- `prepare_run`
- `launch_run`
- `monitor_run`
- `pause_or_stop_run`
- `resume_run`
- `export_postprocessing_inputs`

Raw Fluent TUI, arbitrary journals, unrestricted source-expression editing, and
interactive GUI manipulation should remain local development techniques unless
they are wrapped in reviewed, bounded adapter actions.

## Public Versus Private Artifacts

The public repository may include:

- schemas,
- synthetic solver plans,
- adapter configuration examples,
- monitor contracts,
- generated template examples,
- documentation and tests.

The public repository must not include:

- private `.msh.h5`, `.cas.h5`, or `.dat.h5` files,
- proprietary geometry,
- license files,
- local ANSYS installation paths,
- real project run directories,
- generated private images or videos.

## Roadmap

The adapter roadmap is:

- dry-run manifest generation;
- local Fluent executable discovery;
- controlled PyFluent launch;
- controlled Fluent journal launch;
- checkpoint validation and resume;
- live monitor tailing;
- run package manifest generation;
- post-processing export hooks;
- MCP wrapper for bounded local execution actions.
