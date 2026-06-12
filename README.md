# FromCAD2CFD

**FromCAD2CFD: A CAD-to-CFD Agentic Automation Framework for Solid-Liquid Two-Phase Flow Dynamics** is an early-stage research framework for automating CAD geometry preparation, CFD domain construction, and repeatable preprocessing handoff for solid-liquid two-phase flow studies.

The project is currently a **multi-CAD modeling and geometry-preparation alpha**. It contains a working SolidWorks automation layer, a shared CAD backend contract, and a Siemens NX controlled-journal backend for advanced solid modeling, surface preparation, and reverse-modeling research.

It is not yet a production CFD pipeline. Fluent Meshing, Fluent Solver setup, and post-processing are roadmap modules.

## Current Scope

| Area | Status | Notes |
| --- | --- | --- |
| Common CAD backend contract | Working local abstraction | Shared result, recipe, inspection, export, and registry structures. |
| SolidWorks backend | Working alpha | Uses `pywin32`/COM for controlled geometry creation, copied-model editing, STEP export, and reports. |
| Siemens NX backend | Controlled-journal backend | Uses validated job JSON plus NXOpen journals through `run_journal.exe`. |
| Siemens NX MCP surface | Runnable stdio server | Exposes high-level safe tools for capability reporting, preflight, job writing, and command preparation. |
| Fluent Meshing | Planned | Interface boundary only. |
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
fromcad2cfd nx write-edge-wall-trim-pack-job --project nx_edge_wall_trim_demo
fromcad2cfd nx write-transform-profile-pack-job --project nx_transform_profile_demo
```

Public examples are under [examples/nx](examples/nx). They use only synthetic geometry or placeholder input paths.

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

Current local validation: `54 passed`.

## Roadmap

- `v0.1`: SolidWorks automation alpha.
- `v0.2`: CAD backend abstraction and Siemens NX controlled-journal backend.
- `v0.3`: release hardening, public synthetic end-to-end demos, richer inspection, and broader MCP integration tests.
- `v0.4`: Fluent Meshing prototype.
- `v0.5`: Fluent Solver setup and post-processing prototypes.
- `v1.0`: full CAD-to-CFD closed-loop workflow.

## Citation

If you use this project in academic work, cite it using [CITATION.cff](CITATION.cff).
