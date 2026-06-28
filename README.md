# An Agent Framework for FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dynamics

This repository is the public software workspace for **An Agent Framework for
FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dynamics**.

The implementation package remains `fromcad2cfd`: a research software project
for building auditable, agent-assisted workflows around CAD preparation,
meshing, fast CFD evidence, Fluent setup planning, and post-run interpretation.

The project is designed for engineering workflows where an AI agent should not
blindly operate CAD or CFD software. Instead, each step writes explicit inputs,
checks, reports, and decision artifacts that can be reviewed before moving to a
more expensive or higher-risk stage.

## Scope

FromCAD2CFD currently contains four public workflow blocks.

| Block | Role | Main output |
| --- | --- | --- |
| `Modeling` | Prepare and repair CAD geometry through bounded SolidWorks, NX, and mesh-solidification workflows. | CAD-ready solids, surface repair records, and export reports. |
| `FastFluent` | Run fast native CFD evidence before committing to full Fluent workflows. | Physics passports, QoIs, Result Packs, and agent decisions. |
| `Meshing` | Validate meshing plans and controlled local meshing adapters. | Mesh preflight reports and adapter-safe plans. |
| `Fluent` | Prepare, validate, and summarize Fluent-side workflows. | Solver-plan checks, patch previews, monitor summaries, and handoff reports. |

This repository does not replace SolidWorks, Siemens NX, HyperMesh, or ANSYS
Fluent. It provides a reproducible automation layer around them.

## Public Asset Organization

The public repository is now organized around three reader paths:

| reader path | entry point | purpose |
| --- | --- | --- |
| Engineering workflow | [Architecture](docs/architecture.md) | Understand the four workflow blocks: `Modeling`, `FastFluent`, `Meshing`, and `Fluent`. |
| Agent framework validation | [Agent benchmark ladder](docs/agent_benchmark_ladder/README.md) | See how existing public CFD assets are mapped into a compact `4+1` benchmark ladder. |
| Paper case study | [Dewaxing Agent case study](docs/dewaxing_agent/README.md) | Follow the complex solid-liquid dewaxing route from FastFluent guidance to Fluent-facing evidence. |

The asset mapping rules are recorded in
[Public asset framework map](docs/public_asset_framework_map.md). That document
explains how original public GitHub assets are retained, indexed, and assigned
to the current framework without turning the repository into a local-output
dump.

## Why This Project Exists

CAD-to-CFD work often fails because geometry, meshing, solver setup, and
post-processing are handled as separate manual steps. FromCAD2CFD makes those
steps machine-readable and agent-operable:

- CAD edits are performed on copied files, never on originals.
- Geometry and mesh gates produce JSON and Markdown evidence.
- FastFluent provides low-cost native simulation evidence before Fluent runs.
- Fluent setup is treated as a validated contract, not an uncontrolled script.
- Public examples avoid private CAD models, case files, and licensed assets.

## Recommended First Run

```powershell
python -m pip install -e ".[dev]"
python -m fromcad2cfd --version
python -m fromcad2cfd --help
```

Run the current FastFluent agent workflow demo:

```powershell
python -m fromcad2cfd fastcfd workflow demo `
  --output-dir sandbox/output/fastfluent_s7_workflow_demo `
  --mode native_advisory `
  --format markdown
```

The S7 workflow writes staged setup artifacts, optional native advisory
evidence, a Result Pack, `workflow_manifest.json`, and `agent_decision.json`.
It does not launch Fluent.

## Current Capabilities

### Modeling

The modeling layer focuses on safe CAD preparation rather than uncontrolled
model editing.

- SolidWorks workflow rules for copied-model editing, rebuild checks, export,
  and reporting.
- NX controlled-journal scaffolds for primitives, transforms, booleans,
  surface operations, sheet/solid handling, and reverse-modeling workflows.
- FreeCAD-oriented mesh-solidification references for public STL-to-solid
  preprocessing routes.
- Common CAD backend abstractions for later tool-specific extension.

Useful commands:

```powershell
python -m fromcad2cfd solidworks preflight
python -m fromcad2cfd nx capabilities --format markdown
python -m fromcad2cfd cad list-registered
```

### FastFluent

FastFluent is the native fast-CFD evidence layer. It combines Python workflow
contracts with a C++ numerical core under `cpp/fastfluent_core`.

The current public FastFluent stack includes:

- CaseSpec v3 setup contracts.
- Evidence Bundle v3.
- boundary and material contracts.
- mesh gateway validation.
- Flow Pack generation.
- Route Selector and Route Plan compilation.
- Execution Gate and Controlled Runner.
- S6 unified scalar-transport evidence.
- S7 workflow runner with final `agent_decision.json`.
- Agent benchmark ladder scaffold with four public capability benchmarks plus
  one dewaxing-inspired application bridge.
- FastFluent-native reduced-order dewaxing solver with temperature and
  liquid-fraction fields, melt timing, risk proxy, and Result Pack output.
- FastFluent-native dewaxing parameter study with variant ranking,
  sensitivity summaries, and `dewaxing_guidance.json`.
- FastFluent-native dewaxing validation pack with grid/time-step checks,
  paper tables, and `agent_validation_decision.json`.
- FastFluent-native dewaxing Agent iteration pack with multi-round candidate
  proposals, stability rejection, and accepted-candidate decision traces.
- Dewaxing paper evidence compiler with manuscript tables, SVG figures,
  draft results text, and application claim guidance.
- FastFluent-to-Fluent dewaxing guidance compiler with process partitions,
  Fluent validation targets, parameter priorities, and handoff briefs.
- Dewaxing application bridge with H4 wax handoff, native dewaxing evidence,
  S6 auxiliary proxy evidence, and existing dewaxing Result Pack validation.
- unstructured mesh import, quality gates, finite-volume geometry, and public
  benchmark routes.
- advisory VOF-lite, turbulence, rheology, phase-change, and motion-related
  setup/evidence contracts.

Useful commands:

```powershell
python -m fromcad2cfd fastcfd workflow demo --output-dir sandbox/output/s7_demo --mode native_advisory
python -m fromcad2cfd fastcfd registry --format markdown
python -m fromcad2cfd fastcfd unstructured inspect-mesh examples/unstructured/channel2d.msh --format json
python -m fromcad2cfd fastcfd transport demo --output-dir sandbox/output/s6_transport_alpha --quantity alpha
python -m fromcad2cfd fastcfd run-dewaxing-native-solver --output-dir sandbox/output/dewaxing_native_solver --format markdown
python -m fromcad2cfd fastcfd run-dewaxing-native-study --output-dir sandbox/output/dewaxing_native_study --format markdown
python -m fromcad2cfd fastcfd run-dewaxing-agent-iteration-pack --output-dir sandbox/output/dewaxing_agent_iteration_pack --format markdown
python -m fromcad2cfd fastcfd run-dewaxing-native-validation-pack --output-dir sandbox/output/dewaxing_native_validation_pack --profile standard --format markdown
python -m fromcad2cfd fastcfd compile-dewaxing-paper-evidence-pack --validation-pack sandbox/output/dewaxing_native_validation_pack --iteration-pack sandbox/output/dewaxing_agent_iteration_pack --output-dir sandbox/output/dewaxing_paper_evidence_pack --format markdown
python -m fromcad2cfd fastcfd compile-dewaxing-fluent-guidance-pack --study-pack sandbox/output/dewaxing_native_study --validation-pack sandbox/output/dewaxing_native_validation_pack --iteration-pack sandbox/output/dewaxing_agent_iteration_pack --fluent-bridge-pack examples/postprocessing/dewaxing_result_pack --output-dir sandbox/output/dewaxing_fluent_guidance_pack --format markdown
python -m fromcad2cfd fastcfd dewaxing-application-demo --output-dir sandbox/output/dewaxing_application_bridge --format markdown
```

FastFluent is intended for fast setup validation and engineering evidence. It
is not presented as a production replacement for Fluent.

The current paper-facing Agent route is organized as a compact benchmark ladder
followed by the dewaxing application:

- [Agent benchmark ladder](docs/agent_benchmark_ladder/README.md)
- [Dewaxing Agent case study](docs/dewaxing_agent/README.md)

### Meshing

The meshing layer currently emphasizes planning, preflight checks, and
controlled adapters.

- HyperMesh CFD surface-mesh plan validation.
- HyperMesh local runtime discovery and controlled batch script support.
- Fluent Meshing preflight checks for downstream solver readiness.

Useful commands:

```powershell
python -m fromcad2cfd hypermesh-meshing locate-runtime
python -m fromcad2cfd hypermesh-meshing validate-plan --plan examples/hypermesh_meshing/basic_cfd_tunnel/meshing_plan.json
python -m fromcad2cfd fluent-meshing preflight-gate --fastcfd-output-dir sandbox/output/fastfluent_s7_workflow_demo
```

### Fluent

The Fluent layer is a public-safe planning and reporting interface. On machines
without Fluent, it still validates solver plans, previews handoff patches, and
summarizes exported monitor data.

Current public surfaces:

- Solver Plan validation.
- FastFluent-to-Fluent patch preview.
- resume-plan guardrails.
- advisory PyFluent templates.
- monitor-contract parsing and post-processing summaries.
- MCP-safe planning and post-processing servers.

Useful commands:

```powershell
python -m fromcad2cfd fluent-solver validate-plan --plan examples/fluent_solver/basic_air_steam_fill/solver_plan.json
python -m fromcad2cfd fluent-solver plan-v2-patch-preview-demo --output-dir sandbox/output/fluent_plan_v2_patch_preview_demo
python -m fromcad2cfd post summarize-run `
  --global-monitor examples/postprocessing/basic_monitor_summary/global_monitors.out `
  --wall-monitor examples/postprocessing/basic_monitor_summary/wall_exposure_indicators.out `
  --output-dir sandbox/reports/basic_monitor_summary `
  --model-name basic_monitor_summary
```

Server-side Fluent launch and supervision are intentionally separated from the
portable public contract because they depend on licensed installations, machine
paths, private meshes, case/data files, and local run policies.

## Repository Layout

```text
src/
  fromcad2cfd/                    # top-level CLI
  fromcad2cfd_fastcfd/            # FastFluent/FastCFD workflow and evidence layer
  fromcad2cfd_solidworks/         # SolidWorks automation surface
  fromcad2cfd_nx/                 # Siemens NX automation surface
  fromcad2cfd_hypermesh_meshing/  # HyperMesh meshing interface
  fromcad2cfd_fluent_solver/      # Fluent solver planning interface
  fromcad2cfd_postprocessing/     # monitor parsing and summaries
  fromcad2cfd_mcp_*/              # MCP server entrypoints
cpp/
  fastfluent_core/                # C++ FastFluent numerical core
docs/
  fastcfd/                        # FastFluent contracts and workflow docs
  agent_benchmark_ladder/         # public Agent CFD benchmark ladder
  dewaxing_agent/                 # paper-facing dewaxing Agent case study
  nx/                             # NX workflow docs
  solidworks/                     # SolidWorks workflow docs
examples/
  fastcfd/                        # public FastFluent workflow examples
  fastcfd/agent_benchmark_ladder/ # benchmark ladder example scaffold
  unstructured/                   # public mesh examples
  fluent_solver/                  # public solver-plan examples
tests/
  unit/                           # Python unit tests
```

## Documentation

Start here:

- [Architecture](docs/architecture.md)
- [Documentation index](docs/index.md)
- [Public asset framework map](docs/public_asset_framework_map.md)
- [Agent benchmark ladder](docs/agent_benchmark_ladder/README.md)
- [Dewaxing Agent case study](docs/dewaxing_agent/README.md)
- [FastFluent quickstart](docs/fastcfd/quickstart.md)
- [FastFluent S7 workflow runner](docs/fastcfd/WORKFLOW_RUNNER.md)
- [FastFluent server Codex deployment runbook](docs/fastcfd/SERVER_CODEX_DEPLOYMENT_RUNBOOK.md)
- [FastFluent current capability snapshot](docs/fastcfd/CURRENT_CAPABILITY_SNAPSHOT.md)
- [FastFluent agent workflow status audit](docs/fastcfd/AGENT_WORKFLOW_STATUS_AUDIT.md)
- [NX quickstart](docs/nx/quickstart.md)
- [SolidWorks quickstart](docs/solidworks/quickstart.md)
- [HyperMesh meshing interface](docs/hypermesh_meshing/interface_draft.md)
- [Fluent solver interface](docs/fluent_solver/interface_draft.md)
- [Post-processing interface](docs/postprocessing/interface_draft.md)

## Validation

Run the Python test suite:

```powershell
python -m pytest
```

Run the FastFluent-focused public suite:

```powershell
$files = Get-ChildItem -Path tests\unit -Filter 'test_fastcfd*.py' | ForEach-Object { $_.FullName }
python -m pytest $files -q
```

The current FastFluent suite covers the S7 workflow runner, route selection,
execution gates, controlled runner, result packs, transport coupling, mesh
gateway, unstructured routes, and solver capability matrix.

### Latest Public Validation Snapshot

The latest local Python validation run on 2026-06-28 passed:

- Full Python suite: `424 passed`.
- Public asset/title focused suite: `5 passed`.
- Dewaxing focused suite: `24 passed` when run with the public asset framework
  checks.
- Wheel build: `fromcad2cfd-0.2.0-py3-none-any.whl` built successfully through
  a short-path `subst` workspace.
- Real local dewaxing validation pack: `10` native cases, `20,525,400`
  cell-time steps, and quality status `passed`.
- Real local dewaxing Agent iteration pack: `46` native solver runs,
  `80,140,200` cell-time steps, accepted `path106_initial6` after rejecting
  five fitted candidates during stability review.
- Real local dewaxing paper evidence pack: generated manuscript sections, six
  tables, seven SVG figures, and Agent iteration claim guidance.
- Real local FastFluent-to-Fluent guidance pack: generated five process
  partitions, seven Fluent validation targets, four handoff tables, a workflow
  figure, and paper outline/methods/results guidance sections.

Earlier public Fluent bridge smokes with Ansys `mixing_elbow.msh.h5` and
`nozzle_3d.msh.h5` were run on ANSYS Fluent 2024 R1 with public Ansys example
data.

## Public Data Policy

The public repository must not contain:

- private CAD geometry;
- proprietary SolidWorks/NX/Parasolid exports;
- private STL or mesh files;
- Fluent case/data files;
- license files;
- machine-specific absolute paths;
- generated local solver outputs.

The repository keeps only public examples, synthetic fixtures, source code,
tests, and documentation.

## Licensing

The Python framework is published under the root Apache-2.0 license.

The C++ FastFluent core retains its original GPLv3 license; see
[`cpp/fastfluent_core/LICENSE`](cpp/fastfluent_core/LICENSE).

## Citation

If you use this project in academic work, cite it using
[CITATION.cff](CITATION.cff).
