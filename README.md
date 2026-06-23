# FromCAD2CFD

**FromCAD2CFD: An Agentic Automation Framework for CAD-to-CFD Workflows in
Solid-Liquid Two-Phase Flow Dynamics** is a research software project that
connects CAD preparation, meshing, fast screening, and Fluent-side workflow
management into one agent-usable pipeline.

The repository is organized around four blocks:

1. `Modeling`
2. `FastFluent`
3. `Meshing`
4. `Fluent`

It does not try to replace SolidWorks, Siemens NX, HyperMesh, or ANSYS Fluent.
It provides the automation layer that makes those tools easier to plan, audit,
and reuse.

## Choose A Starting Point

| Block | Use it for | First command |
| --- | --- | --- |
| `Modeling` | Prepare CAD geometry, repair surfaces, and build flow-domain solids. | `fromcad2cfd nx capabilities --format markdown` |
| `FastFluent` | Run low-cost CFD checks before committing to expensive Fluent runs. | `fromcad2cfd fastcfd registry --format markdown` |
| `Meshing` | Validate HyperMesh surface-meshing plans and batch-run controlled scripts. | `fromcad2cfd hypermesh-meshing locate-runtime` |
| `Fluent` | Validate solver plans, preview FastFluent patch handoff, and summarize monitor outputs. | `fromcad2cfd fluent-solver plan-v2-patch-preview-demo --output-dir sandbox/output/fluent_plan_v2_patch_preview_demo` |

## What You Can Do Today

- build or edit CFD-ready geometry through bounded SolidWorks and NX workflows;
- convert coarse mesh geometry into solid-friendly preprocessing inputs;
- run FastFluent screening before expensive Fluent work;
- run public FastFluent-native simulation validation packs with field outputs,
  convergence histories, QoIs, and passport-simulation alignment reports;
- run practical FastFluent-native heat, scalar, material-property,
  source-term, parameter-sweep, and wax application utilities;
- generate practical native setup artifacts: geometry manifests, boundary
  contracts, initial field CSVs, and native case templates;
- inspect public unstructured meshes and generate low-cost CFD evidence;
- validate HyperMesh surface-meshing plans and run controlled batch scripts;
- validate Fluent solver plans, preview FastFluent patch handoff, prepare
  advisory templates, and summarize monitor outputs after runs.

## Workflow

```text
Modeling
  -> CAD body, repaired surface, or flow-domain geometry
Meshing
  -> reviewed surface mesh and meshing evidence
FastFluent
  -> low-cost CFD evidence before expensive solving
Fluent
  -> validated solver workflow, preview-only patch handoff, and post-run summaries
```

Each block answers one practical question:

- `Modeling`: is the geometry usable?
- `Meshing`: is the discretization path under control?
- `FastFluent`: is the setup physically plausible before full solving?
- `Fluent`: is the final solver workflow correctly prepared and interpretable?

## Blocks In Detail

### Modeling

Geometry preparation and repair before meshing or solving.

- **SolidWorks**: copied-model editing, booleans, shell/thicken, fillet,
  chamfer, revolve, sweep, loft, rebuild, and export.
- **Siemens NX**: controlled journal-based modeling, transforms, booleans,
  sheet and surface operations, reverse-modeling steps, and Parasolid handoff.
- **Mesh solidification helpers**: coarse STL-to-solid preparation for reverse
  or rough imported geometry.

### FastFluent

FastFluent is the project's fast local CFD evidence layer.

- `src/fromcad2cfd_fastcfd` provides schemas, registry, physics passports,
  screening, reports, and workflow control.
- `cpp/fastfluent_core` provides the C++ numerical backend inherited into this
  project.

The current public surface includes structured and unstructured evidence
routes, QoI extraction, screening reports, VOF/turbulence/rheology support, and
evidence-to-Fluent handoff artifacts such as physics passports, Fluent setup
hints, and validated non-executing `solver_plan_patch.json` bundles.

Representative public demo:

```powershell
python -m fromcad2cfd fastcfd native-simulation-validation-pack-demo --output-dir sandbox/output/fastfluent_native_simulation_validation_pack
python -m fromcad2cfd fastcfd horizontal-validation-pack-demo --output-dir sandbox/output/fastfluent_horizontal_validation_pack
python -m fromcad2cfd fastcfd steam-air-handoff-demo --output-dir sandbox/output/steam_air_handoff_demo
python -m fromcad2cfd fastcfd steam-air-v2-demo --output-dir sandbox/output/steam_air_v2_demo
python -m fromcad2cfd fastcfd solid-liquid-handoff-demo --output-dir sandbox/output/solid_liquid_suspension_demo
python -m fromcad2cfd fastcfd practical-native-demo-pack --output-dir sandbox/output/fastfluent_practical_native_demo_pack
python -m fromcad2cfd fastcfd practical-native-setup-demo --output-dir sandbox/output/fastfluent_practical_native_setup_demo
python -m fromcad2cfd fastcfd existing-passport-patch-demo --output-dir sandbox/output/fastfluent_h1_existing_patch_demo
```

The native simulation validation pack runs public FastFluent-native routes and
writes `simulation_result.json`, field outputs, convergence/history files, QoI
summaries, `simulation_manifest.json`, `simulation_summary.md`, and
passport-simulation alignment reports. The other commands write synthetic
public-safe FastFluent evidence, Fluent setup hints, solver-plan patch JSON, and
Markdown handoff reports without launching Fluent or editing Fluent case files.
The horizontal validation-pack demo remains the public regression gate for
H1-H3 setup evidence.

The practical native demo pack adds reusable native mini computations for heat
diffusion, scalar transport, material-property fields, source-term ramp/clamp
behavior, parameter sweeps, and a wax application demo. It writes CSV/JSON field
and history outputs plus a `practical_native_manifest.json` without launching
Fluent.

The practical setup demo pack writes public geometry manifests, boundary
condition contracts, initial temperature/scalar/velocity field CSVs, and
S2-compatible native case templates.

### Meshing

Meshing sits between geometry and solver execution.

- **HyperMesh meshing**: controlled local CFD surface-mesh preparation.
- **Fluent meshing handoff checks**: validation that downstream meshing starts
  from a clean enough state.

The accepted public scope today is **surface meshing**, not full production
volume meshing.

### Fluent

Fluent manages solver-side workflow logic.

- public solver-plan validation;
- preview-only Solver Plan v2 patch receiving from FastFluent
  `solver_plan_patch.json`;
- resume-plan guardrails;
- advisory PyFluent templates;
- monitor contracts and post-processing summaries;
- MCP-safe planning and post-processing surfaces.

The design separates the **portable public contract** from the
**machine-specific local adapter** that depends on licenses, ANSYS paths,
private meshes, private case/data files, and local run policies.

## First Run

### 1. Install

```powershell
python -m pip install -e ".[dev]"
python -m fromcad2cfd --version
python -m fromcad2cfd --help
```

Optional local dependencies:

- SolidWorks
- Siemens NX plus `run_journal.exe`
- FreeCAD
- Altair HyperMesh / HyperMesh CFD
- C++ build environment for real FastFluent runs
- licensed local Fluent environment

### 2. Check Available Entry Points

```powershell
python -m fromcad2cfd --help
python -m fromcad2cfd hypermesh-meshing --help
python -m fromcad2cfd fluent-solver --help
```

### 3. Run A First Command In Each Block

**Modeling**

```powershell
fromcad2cfd solidworks preflight
fromcad2cfd nx capabilities --format markdown
```

**FastFluent**

```powershell
fromcad2cfd fastcfd registry --format markdown
fromcad2cfd fastcfd unstructured inspect-mesh examples/unstructured/channel2d.msh --format json
```

**Meshing**

```powershell
fromcad2cfd hypermesh-meshing locate-runtime
fromcad2cfd hypermesh-meshing validate-plan --plan examples/hypermesh_meshing/basic_cfd_tunnel/meshing_plan.json
```

**Fluent**

```powershell
fromcad2cfd fluent-solver validate-plan --plan examples/fluent_solver/basic_air_steam_fill/solver_plan.json
fromcad2cfd fluent-solver plan-v2-patch-preview-demo --output-dir sandbox/output/fluent_plan_v2_patch_preview_demo
fromcad2cfd post summarize-run `
  --global-monitor examples/postprocessing/basic_monitor_summary/global_monitors.out `
  --wall-monitor examples/postprocessing/basic_monitor_summary/wall_exposure_indicators.out `
  --output-dir sandbox/reports/basic_monitor_summary `
  --model-name basic_monitor_summary
```

## Project Map

### Modeling

- `src/fromcad2cfd_solidworks`
- `src/fromcad2cfd_nx`
- `src/fromcad2cfd_mcp_nx`
- `src/fromcad2cfd_mesh`

### FastFluent

- `src/fromcad2cfd_fastcfd`
- `cpp/fastfluent_core`
- `examples/fastcfd`
- `examples/unstructured`

### Meshing

- `src/fromcad2cfd_hypermesh_meshing`
- `src/fromcad2cfd_mcp_hypermesh_meshing`
- `src/fromcad2cfd_fluent_meshing`
- `examples/hypermesh_meshing`

### Fluent

- `src/fromcad2cfd_fluent_solver`
- `src/fromcad2cfd_postprocessing`
- `src/fromcad2cfd_mcp_fluent_solver`
- `src/fromcad2cfd_mcp_postprocessing`

## Documentation

- [Architecture](docs/architecture.md)
- [Documentation index](docs/index.md)
- [SolidWorks quickstart](docs/solidworks/quickstart.md)
- [NX quickstart](docs/nx/quickstart.md)
- [FastFluent quickstart](docs/fastcfd/quickstart.md)
- [FastFluent S1 native simulation delivery](docs/FASTFLUENT_S1_NATIVE_SIMULATION_DELIVERY_20260623.md)
- [FastFluent S2 practical native function expansion delivery](docs/FASTFLUENT_S2_PRACTICAL_NATIVE_FUNCTION_EXPANSION_DELIVERY_20260623.md)
- [FastFluent S3 practical native setup utilities delivery](docs/FASTFLUENT_S3_PRACTICAL_NATIVE_SETUP_UTILITIES_DELIVERY_20260623.md)
- [HyperMesh meshing interface](docs/hypermesh_meshing/interface_draft.md)
- [Fluent solver interface](docs/fluent_solver/interface_draft.md)
- [Post-processing interface](docs/postprocessing/interface_draft.md)

## Public Scope

Already real in public mainline:

- bounded SolidWorks and NX modeling workflows;
- mesh solidification helpers;
- FastFluent screening and public unstructured benchmark routes;
- HyperMesh surface-mesh planning and controlled local batch support;
- Fluent solver planning and post-processing summaries;
- MCP-safe tool surfaces for selected workflow stages.

Still environment-specific or intentionally outside public scope:

- private CAD models and research geometry;
- full production volume-mesh workflows;
- machine-specific Fluent launch and supervision details;
- final high-fidelity CFD validation and engineering sign-off.

## Safety

This repository must not include proprietary CAD models, private STL/Parasolid
or NX/SolidWorks outputs, Fluent case/data files, generated local meshes,
license files, or local absolute paths.

Typical ignored local folders:

```text
sandbox/input/
sandbox/output/
sandbox/reports/
05_projects/
06_logs/
```

Core rules:

- never overwrite original CAD files;
- copy inputs before editing;
- use unique or timestamped outputs;
- stop on ambiguous geometry selectors;
- validate mesh and physics gates before advancing;
- write JSON and Markdown reports.

## Licensing

The Python framework is published under the root Apache-2.0 license.

The vendored C++ FastFluent core retains its original GPLv3 license; see
[`cpp/fastfluent_core/LICENSE`](cpp/fastfluent_core/LICENSE).

## Development

```powershell
python -m compileall src tests
python -m pytest
```

## Citation

If you use this project in academic work, cite it using [CITATION.cff](CITATION.cff).
