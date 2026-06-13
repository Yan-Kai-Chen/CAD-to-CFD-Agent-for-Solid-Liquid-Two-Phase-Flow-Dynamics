# FromCAD2CFD

**FromCAD2CFD: A CAD-to-CFD Agentic Automation Framework for Solid-Liquid Two-Phase Flow Dynamics** is an early-stage research framework for automating CAD geometry preparation, CFD domain construction, and repeatable preprocessing handoff for solid-liquid two-phase flow studies.

The project is currently a **multi-CAD modeling and geometry-preparation alpha**. It contains a working SolidWorks automation layer, a shared CAD backend contract, a Siemens NX controlled-journal backend for advanced solid modeling, an experimental mesh-to-solid route for coarse reverse-modeling candidates, and a new FastCFD foundation for advisory pilot-flow workflows.

It is not yet a production CFD pipeline. The current Fluent Meshing work is a planning gate only; full Fluent Meshing execution, Fluent Solver setup, and post-processing remain roadmap modules.

## Current Scope

| Area | Status | Notes |
| --- | --- | --- |
| Common CAD backend contract | Working local abstraction | Shared result, recipe, inspection, export, and registry structures. |
| SolidWorks backend | Working alpha | Uses `pywin32`/COM for controlled geometry creation, copied-model editing, STEP export, and reports. |
| Siemens NX backend | Controlled-journal backend | Uses validated job JSON plus NXOpen journals through `run_journal.exe`. |
| Siemens NX MCP surface | Runnable stdio server | Exposes high-level safe tools for capability reporting, preflight, job writing, and command preparation. |
| Mesh solidification | Experimental | Uses copied STL input plus optional FreeCAD/OpenCascade execution to create coarse STEP solid candidates. |
| FastCFD / FastFluent integration | Foundation | Defines agent-safe schemas, source-of-truth registry, semantic scene compiler, physics passport, preflight, deterministic mock workflow, controlled real `cavity2d`, `channel2d`, and `obstacle2d` backends, native run summaries, field-derived QoI parsing, lattice-domain trust scoring, and pilot-decision artifacts. |
| Fluent Meshing | Planning gate | Reads FastCFD pilot evidence and writes a pre-meshing gate report before future Fluent automation. |
| Fluent Solver | Planned | Interface boundary only. |
| Post-processing | Planned | Interface boundary only. |

## Why This Exists

CAD-to-CFD workflows often fail before meshing starts: imported geometry is rough, CAD edits are not reproducible, flow domains are rebuilt manually, and geometry decisions are not captured in reports. This project experiments with a safer agentic layer that:

- copies input models before editing,
- uses bounded CAD operations instead of arbitrary code execution,
- records JSON and Markdown reports,
- separates private research geometry from public code,
- keeps CAD-native artifacts and CFD handoff formats traceable.

## Architecture

```text
Skills and policies
  -> MCP-safe tool surface
    -> common CAD backend contract
      -> SolidWorks COM backend
      -> Siemens NX controlled-journal backend
      -> mesh solidification helper
      -> FastCFD advisory pilot-flow layer
        -> Fluent Meshing preflight gate
          -> reports and CFD handoff metadata
```

See [docs/architecture.md](docs/architecture.md) and [docs/cad_backend.md](docs/cad_backend.md).

## Modeling Capabilities

### SolidWorks

The SolidWorks alpha supports:

- preflight through `pywin32`,
- controlled cylinder and plan-based geometry creation,
- extrude, cut, boolean combine, move/copy, fillet, chamfer, shell, thicken, sweep, loft, and revolve workflows,
- safe copied-model parameter editing by exact dimension name,
- STEP export and JSON/Markdown reports,
- CFD-oriented template plans.

### Siemens NX

The NX backend supports controlled job generation and validated NXOpen journal families for:

- synthetic public-safe geometry jobs,
- cylindrical CFD fluid-domain construction demos,
- basic solid modeling packs,
- edge/wall/trim/import packs,
- transform/profile packs,
- copied-model inspection,
- copied-model boolean subtract,
- copied-model axis-aligned plane cut,
- Parasolid import to `.prt`,
- face thicken,
- sheet sew,
- basic curves and bounded-plane surfaces,
- STL-to-convergent reverse-modeling Step 1,
- Cage from Facet Body reverse-modeling Step 2,
- XOY bounded-plane and CombineSheets reverse-modeling Step 3/4.

Print the machine-readable NX capability inventory:

```powershell
fromcad2cfd nx capabilities
fromcad2cfd nx capabilities --format markdown
```

The current NX MCP package exposes a runnable stdio server. It does not expose raw NXOpen calls, arbitrary Python execution, arbitrary journal replay, file deletion, or overwrite operations. NX journal execution is prepared as an explicit command and remains outside automatic tool execution.

### Mesh Solidification

The mesh helper supports a coarse STL-to-solid candidate route:

- copy STL inputs before processing,
- inspect STL facet count and simple watertightness indicators,
- write controlled FreeCAD/OpenCascade solidification jobs,
- locate FreeCAD through `FreeCADCmd.exe` and execute with the bundled FreeCAD Python runtime when available,
- export STEP solid candidates and JSON/Markdown reports.

This route is useful when CFD preprocessing needs a boolean-capable coarse solid. It does not claim parametric, analytic, or high-accuracy reverse engineering.

### FastCFD / FastFluent

The FastCFD foundation prepares the internal FastFluent solver for agent-native
use. The first batch adds:

- `fromcad2cfd fastcfd` CLI routing,
- validated `FastCFDJob` and `FastCFDScene` contracts,
- a machine-readable source-of-truth registry for allowed case templates,
- semantic scene validation and scene-to-job compilation,
- mandatory physics passport validation before mock or controlled real runs,
- optional FastFluent source/build preflight,
- deterministic `cavity2d` mock workflow,
- controlled real `cavity2d`, `channel2d`, and `obstacle2d` execution against the local FastFluent source,
- native executable summaries and residual-history CSVs when source hooks are installed,
- VTK XML field parsing for speed, density, centerline, outlet, wake, and refinement proxy metrics,
- recipe-derived lattice-domain trust summaries,
- bounded pilot-decision artifacts for deciding whether to proceed, extend the pilot, review domain extent, or revise the recipe domain,
- `generated.ini`, QoI, physics contract, flow fingerprint, Fluent hints, claim ledger, result manifest, and reports.

The mock backend validates workflow plumbing only. Real FastFluent source
field-derived metrics are advisory pilot evidence only. Real FastFluent source
refactoring will continue to target the same artifact contract and remain
bounded to allowed case templates before broader solver integration.

Agent workflows should prefer the semantic scene route:

```powershell
fromcad2cfd fastcfd registry --format markdown
fromcad2cfd fastcfd write-scene --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_scene --scene-type obstacle2d --obstacle circle
fromcad2cfd fastcfd validate-scene --scene-file <scene.json>
fromcad2cfd fastcfd compile-scene --scene-file <scene.json> --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_job
fromcad2cfd fastcfd run-mock-job --job-file <job.json>
```

FastCFD details are documented in [docs/fastcfd/quickstart.md](docs/fastcfd/quickstart.md)
and [docs/fastcfd/native_summary_contract.md](docs/fastcfd/native_summary_contract.md).
The lattice trust and pilot-decision artifacts are documented in
[docs/fastcfd/lattice_trust_and_pilot_decision.md](docs/fastcfd/lattice_trust_and_pilot_decision.md).

## Installation

From a local checkout:

```powershell
python -m pip install -e ".[dev]"
```

After installation:

```powershell
fromcad2cfd --version
fromcad2cfd --help
```

On Windows user installs, the Python user `Scripts` directory may not be on
`PATH`. The module form works without relying on console script discovery:

```powershell
python -m fromcad2cfd --version
python -m fromcad2cfd --help
```

For source-tree smoke checks without installing:

```powershell
$env:PYTHONPATH="src"
python -m fromcad2cfd --help
python -m fromcad2cfd nx capabilities --format markdown
```

Optional SolidWorks environment variables:

```powershell
$env:SOLIDWORKS_EXE="C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe"
$env:SOLIDWORKS_TEMPLATE_DIR="C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates"
```

Siemens NX journal execution requires a local NX installation with `run_journal.exe`.

Optional FreeCAD mesh solidification requires `FreeCADCmd.exe`. Set:

```powershell
$env:FREECADCMD_EXE="C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe"
```

For portable FreeCAD bundles, pass the extracted `FreeCADCmd.exe` path with
`--freecadcmd`. The runtime wrapper uses this path to locate the same bundle's
`bin\python.exe`, which is the verified execution mode for FreeCAD 1.1.1.

## Quickstart

Common contract:

```powershell
fromcad2cfd cad contract
```

SolidWorks:

```powershell
fromcad2cfd solidworks preflight
fromcad2cfd solidworks create-cylinder --radius-mm 10 --height-mm 20
```

Siemens NX:

```powershell
fromcad2cfd nx preflight
fromcad2cfd nx capabilities --format markdown
fromcad2cfd nx write-basic-solid-pack-job --project nx_basic_solid_pack_demo
fromcad2cfd nx write-fluid-domain-demo-job --project nx_fluid_domain_cylinder_demo
fromcad2cfd nx write-edge-wall-trim-pack-job --project nx_edge_wall_trim_demo
fromcad2cfd nx write-transform-profile-pack-job --project nx_transform_profile_demo
```

Mesh solidification:

```powershell
fromcad2cfd mesh preflight
fromcad2cfd mesh solidify-freecad --input-file examples\mesh\freecad_solidify\cube_ascii.stl --project mesh_solidify_cube_demo --model-name cube_solid_candidate --no-execute
```

FastCFD:

```powershell
fromcad2cfd fastcfd capabilities --format markdown
fromcad2cfd fastcfd registry --format markdown
fromcad2cfd fastcfd preflight
fromcad2cfd fastcfd mock-demo --project fastcfd_mock_cavity2d --model-name fastcfd_mock_cavity2d
fromcad2cfd fastcfd write-scene --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_scene --scene-type obstacle2d --obstacle circle
fromcad2cfd fastcfd write-channel2d-job --project fastcfd_channel2d_real --model-name fastcfd_channel2d_real
fromcad2cfd fastcfd write-obstacle2d-job --project fastcfd_obstacle2d_real --model-name fastcfd_obstacle2d_real --obstacle circle
```

Fluent Meshing preflight gate:

```powershell
fromcad2cfd fluent-meshing preflight-gate --fastcfd-output-dir <FastCFD output dir>
```

Public examples are under [examples](examples). They use only synthetic geometry or placeholder input paths.

NX MCP server:

```powershell
python -m pip install -e ".[mcp]"
python -m fromcad2cfd_mcp_nx.server --describe
python -m fromcad2cfd_mcp_nx.server --list-tools
python -m fromcad2cfd_mcp_nx.server
```

Project-level Codex configuration example:

```text
configs/codex/nx_mcp_config.example.toml
```

## Reverse Modeling

The NX reverse-modeling workflow is documented as a bounded, user-taught process:

1. Import STL as cleaned convergent bodies.
2. Create a cage/subdivision representation from convergent bodies.
3. Import accepted Parasolid output, create an XOY bounded-plane sheet, move it in +Z, and run CombineSheets with recorded region trackers.

See [docs/nx/reverse_modeling_workflow.md](docs/nx/reverse_modeling_workflow.md).

This workflow does not claim automatic conversion of arbitrary faceted geometry into perfect analytic CAD.

The alternative FreeCAD/OpenCascade route is documented in [docs/mesh/freecad_solidify.md](docs/mesh/freecad_solidify.md). It is a coarse mesh-to-solid candidate path for workflows where boolean operations matter more than analytic surface fidelity.

## Safety Rules

- Never overwrite original CAD files.
- Copy inputs before editing.
- Use timestamped or unique output paths.
- Inspect models before modifying existing geometry.
- Stop on ambiguous body, face, feature, or dimension selectors.
- Rebuild or update after geometry edits.
- Stop on rebuild/update failure.
- Save CAD-native artifacts and export supported CFD handoff formats.
- Write JSON and Markdown reports.
- Do not expose arbitrary code execution as an agent tool.

## Private Data Policy

This repository must not include proprietary CAD models, research device geometry, STL/Parasolid/NX/SolidWorks outputs, Fluent case/data files, license files, or local absolute paths.

Keep private models and generated artifacts only in ignored local folders such as:

```text
sandbox/input/
sandbox/output/
sandbox/reports/
05_projects/
06_logs/
```

## Repository Layout

```text
src/fromcad2cfd/              Root CLI
src/fromcad2cfd_cad/          Common CAD backend contract
src/fromcad2cfd_solidworks/   SolidWorks automation backend
src/fromcad2cfd_nx/           Siemens NX controlled-journal backend
src/fromcad2cfd_mcp_nx/       Safe NX MCP stdio server
src/fromcad2cfd_mesh/         Mesh inspection and FreeCAD solidification helper
src/fromcad2cfd_fastcfd/        FastCFD/FastFluent advisory pilot-flow layer
src/fromcad2cfd_fluent_meshing/ Fluent Meshing planning gate
docs/                         Architecture and workflow documentation
skills/                       Codex skill definitions
examples/                     Public synthetic examples
tests/                        Unit tests
```

## Development Checks

```powershell
python -m compileall src tests
python -m pytest
```

Current local validation: see the latest run summary in project reports or release notes.

## Roadmap

- `v0.1`: SolidWorks automation alpha.
- `v0.2`: CAD backend abstraction and Siemens NX controlled-journal backend.
- `v0.3`: release hardening, public synthetic end-to-end demos, richer inspection, and broader MCP integration tests.
- `v0.4`: Fluent Meshing prototype.
- `v0.5`: Fluent Solver setup and post-processing prototypes.
- `v1.0`: full CAD-to-CFD closed-loop workflow.

## Citation

If you use this project in academic work, cite it using [CITATION.cff](CITATION.cff).
Technical references for FreeCAD, Open CASCADE Technology, and mesh-to-Part
conversion are listed in [docs/references.md](docs/references.md).
