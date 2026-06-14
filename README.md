# FromCAD2CFD

**FromCAD2CFD: An Agentic Automation Framework for CAD-to-CFD Workflows in
Solid-Liquid Two-Phase Flow Dynamics** is a research framework for making CAD
preparation, preliminary CFD screening, and Fluent-oriented handoff more
repeatable and agent-readable.

The project is not intended to replace professional CAD systems or ANSYS
Fluent. Its purpose is to provide a controlled automation layer that can:

- prepare and inspect CAD geometry through bounded operations,
- generate reproducible flow-domain and preprocessing artifacts,
- run fast preliminary CFD checks before expensive Fluent workflows,
- record decisions as JSON and Markdown reports that an AI agent can audit.

## Core Capabilities

### CAD Geometry Automation

FromCAD2CFD provides safe wrappers around CAD operations used repeatedly in
CAD-to-CFD preprocessing.

- **SolidWorks**: controlled COM-based model creation, copied-model editing,
  dimension-safe modification, boolean operations, shell/thicken, fillet,
  chamfer, sweep, loft, revolve, STEP export, and reports.
- **Siemens NX**: controlled NXOpen journal workflows for primitive modeling,
  transforms, boolean operations, Parasolid import, sheet/surface operations,
  trimming, plane cuts, fluid-domain construction, and bounded reverse-modeling
  steps.
- **Mesh solidification helper**: optional FreeCAD/OpenCascade route for coarse
  STL-to-solid candidate generation when a boolean-capable solid is more useful
  than a high-fidelity analytic reconstruction.

CAD automation is intentionally conservative: original models are copied before
editing, ambiguous selectors stop the workflow, and every operation is expected
to produce machine-readable reports.

### FastCFD / FastFluent Agentic CFD Layer

FastCFD / FastFluent is the project CFD pillar. It combines an agent-facing
control layer with a lightweight solver evidence layer so geometry and physics
choices can be checked before high-fidelity Fluent validation.

It currently includes:

- validated job and scene schemas,
- a registry of allowed case templates and solver routes,
- physics passports for single-phase, VOF setup, turbulence setup, and
  non-Newtonian rheology,
- controlled mock and real FastFluent backend execution,
- field-derived QoI, prediction reports, parameter screening, and pilot
  decision artifacts,
- Gmsh-based unstructured mesh import, named-zone preservation, mesh-quality
  gates, finite-volume geometry, and public benchmark cases,
- controlled unstructured evidence routes for scalar diffusion, Stokes-style
  momentum, pressure projection, steady incompressible channel flow,
  obstacle-channel checks, VOF-lite alpha transport, and bounded turbulence
  model comparisons,
- a vendored C++ FastFluent solver core under
  [`cpp/fastfluent_core`](cpp/fastfluent_core).

The output is preliminary engineering evidence: it helps decide whether a CAD
domain, mesh, boundary setup, or physics assumption is plausible enough to move
toward Fluent. It is not presented as final CFD validation.

### Agent Safety And Traceability

The public workflow is built around bounded commands rather than arbitrary code
execution. The framework emphasizes:

- explicit input/output paths,
- no overwrite of original CAD or mesh inputs,
- validated schemas before execution,
- fail-closed physics and mesh gates,
- JSON/Markdown reports for agent reasoning,
- public synthetic examples instead of private research geometry.

## Architecture

```text
AI agent
  -> skills, policies, and MCP-safe tool surfaces
    -> CAD geometry automation
      -> SolidWorks backend
      -> Siemens NX backend
      -> mesh solidification helper
    -> FastCFD / FastFluent agentic CFD layer
      -> scene and job validation
      -> physics passports
      -> structured FastFluent backend
      -> unstructured finite-volume evidence backend
      -> prediction, QoI, and Fluent setup hints
    -> Fluent Meshing / Solver handoff boundaries
      -> preflight reports and future automation interfaces
```

See [docs/architecture.md](docs/architecture.md) for the longer architecture
note.

## Repository Layout

```text
src/fromcad2cfd/                 Root CLI

src/fromcad2cfd_cad/             Shared CAD backend contract
src/fromcad2cfd_solidworks/      SolidWorks automation backend
src/fromcad2cfd_nx/              Siemens NX controlled-journal backend
src/fromcad2cfd_mcp_nx/          Safe NX MCP stdio server
src/fromcad2cfd_mesh/            Mesh inspection and solidification helper

src/fromcad2cfd_fastcfd/         FastCFD / FastFluent agentic CFD layer
src/fromcad2cfd_fluent_meshing/  Fluent Meshing preflight boundary

cpp/fastfluent_core/             C++ FastFluent solver core
docs/                            Architecture and workflow documentation
examples/                        Public synthetic examples
skills/                          Codex skill definitions
tests/                           Unit tests
```

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

If the Python user `Scripts` directory is not on `PATH`, use the module form:

```powershell
python -m fromcad2cfd --version
python -m fromcad2cfd --help
```

Optional integrations:

- SolidWorks requires a local SolidWorks installation and `pywin32`.
- Siemens NX journal execution requires `run_journal.exe`.
- FreeCAD mesh solidification requires `FreeCADCmd.exe`.
- Real FastFluent runs require a working C++ build environment; the source root
  defaults to `cpp/fastfluent_core`.

## Quickstart

### Inspect Available Capabilities

```powershell
fromcad2cfd cad contract
fromcad2cfd solidworks preflight
fromcad2cfd nx capabilities --format markdown
fromcad2cfd fastcfd capabilities --format markdown
```

### Run A Public CAD Example

```powershell
fromcad2cfd solidworks create-cylinder --radius-mm 10 --height-mm 20
fromcad2cfd nx write-basic-solid-pack-job --project nx_basic_solid_pack_demo
```

### Run A FastCFD Screening Example

```powershell
fromcad2cfd fastcfd registry --format markdown
fromcad2cfd fastcfd preflight
fromcad2cfd fastcfd mock-demo --project fastcfd_mock_cavity2d --model-name fastcfd_mock_cavity2d
```

### Inspect Or Solve A Public Unstructured Example

```powershell
fromcad2cfd fastcfd unstructured inspect-mesh examples/unstructured/channel2d.msh --format json
fromcad2cfd fastcfd unstructured run-benchmark-suite --iterations 8 --format json
```

More detailed commands are kept in the module-specific documentation:

- [SolidWorks quickstart](docs/solidworks/quickstart.md)
- [NX quickstart](docs/nx/quickstart.md)
- [FastCFD quickstart](docs/fastcfd/quickstart.md)
- [FreeCAD solidification route](docs/mesh/freecad_solidify.md)

## Public Examples

All repository examples are synthetic and public-safe. They are meant to show
the workflow contract, not to disclose private research device geometry.

Examples include:

- simple CAD geometry generation,
- NX controlled journal job generation,
- synthetic mesh solidification input,
- public Gmsh unstructured benchmark meshes,
- FastCFD / FastFluent screening and benchmark artifacts.

## Current Boundary

Implemented:

- controlled SolidWorks and NX CAD automation foundations,
- public-safe CAD and mesh examples,
- FastCFD / FastFluent job validation, physics passports, prediction reports,
  and preliminary CFD evidence routes,
- unstructured mesh import, quality checks, finite-volume geometry, and public
  benchmark workflows,
- vendored C++ FastFluent core.

Roadmap:

- broader production CAD repair coverage,
- deeper Fluent Meshing automation,
- Fluent Solver setup generation,
- richer post-processing,
- broader solver validation and performance hardening.

FromCAD2CFD should be treated as an agentic automation and preliminary
engineering-evidence framework. Production CFD conclusions still require
high-fidelity solver validation.

## Safety And Private Data Policy

This repository must not include proprietary CAD models, private STL/Parasolid
or NX/SolidWorks outputs, Fluent case/data files, license files, or local
absolute paths.

Generated or private artifacts should stay in ignored local folders such as:

```text
sandbox/input/
sandbox/output/
sandbox/reports/
05_projects/
06_logs/
```

Core safety rules:

- never overwrite original CAD files,
- copy inputs before editing,
- use unique or timestamped outputs,
- stop on ambiguous model, body, face, feature, or dimension selectors,
- validate physics and mesh gates before solver execution,
- write JSON and Markdown reports.

## Licensing

The Python agent framework is published under the root Apache-2.0 license.

The vendored C++ FastFluent core retains its original GPLv3 license; see
[`cpp/fastfluent_core/LICENSE`](cpp/fastfluent_core/LICENSE).

Compiled executables, object files, generated VTK outputs, Fluent case/data
files, and unreviewed CAD/STL geometry data are intentionally excluded.

## Development Checks

```powershell
python -m compileall src tests
python -m pytest
```

## Citation

If you use this project in academic work, cite it using
[CITATION.cff](CITATION.cff).

Technical references are listed in [docs/references.md](docs/references.md).
