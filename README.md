# A CAD-to-CFD Agentic Automation Framework for Solid-Liquid Two-Phase Flow Dynamics

**A CAD-to-CFD Agentic Automation Framework for Solid-Liquid Two-Phase Flow Dynamics** is an early-stage research and engineering framework for automating the path from CAD geometry to CFD-ready artifacts, with an explicit emphasis on geometry preparation, flow-domain construction, and repeatable preprocessing for solid-liquid two-phase flow dynamics.

The current `v0.2.0` development line focuses on a multi-CAD foundation:
SolidWorks automation remains the first validated CAD loop, while Siemens NX
adds a controlled NXOpen journal backend for advanced geometry preparation and
reverse-modeling research. Fluent Meshing, Fluent Solver setup, and CFD
post-processing remain documented roadmap modules.

## Current Status

- Common CAD backend contract: working local abstraction
- SolidWorks automation: working alpha
- Siemens NX backend: controlled-journal local backend
- Siemens NX MCP wrapper: safe scaffold with high-level job builders
- Fluent Meshing automation: planned
- Fluent Solver setup automation: planned
- CFD post-processing automation: planned

## What It Does

This framework is designed as a modular agentic workflow:

```text
CAD Geometry -> Geometry Cleanup -> CFD Domain Construction -> Meshing -> Solver Setup -> Post-processing -> Report
```

The SolidWorks alpha currently supports:

- SolidWorks COM preflight through `pywin32`.
- Controlled geometry creation.
- Common modeling operations including extrude, cut, boolean combine, move/copy, fillet, chamfer, shell, thicken, sweep, loft, and revolve.
- Safe copied-model editing patterns.
- STEP export after successful geometry operations.
- Markdown and JSON report generation.
- CFD-oriented geometry plan templates.
- Codex skill guidance for conservative CAD automation.

The common CAD layer now defines backend-neutral result, recipe, inspection, export, and registry contracts so SolidWorks and Siemens NX can be exposed through a shared agent workflow.

The Siemens NX backend currently supports:

- NX installation and journal-runner preflight.
- Controlled synthetic geometry jobs.
- Basic solid modeling capability packs.
- Edge, wall, trim, import, transform, and profile smoke workflows.
- Copied-model inspection, plane cut, boolean subtract, face thicken, and sheet sew jobs.
- Reverse-modeling preparation workflows for STL-to-convergent import, cage-from-facet-body, and XOY plane CombineSheets.
- Manual journal capture as a development method for selector-sensitive NX UI operations, without exposing arbitrary journal replay through MCP.
- NX `.prt`, Parasolid `.x_t` where supported, and JSON/Markdown reports.

## Safety First

The framework follows conservative automation rules:

- Never overwrite original CAD files.
- Copy inputs to working/output folders before edits.
- Use timestamped outputs.
- Inspect models before modifying existing geometry.
- Stop if a dimension or feature cannot be uniquely identified.
- Rebuild after every geometry edit.
- Stop on rebuild failure.
- Export a CFD handoff format and write reports after successful operations.
- Keep private CAD, STL, Parasolid, NX `.prt`, Fluent case/data, and generated result folders out of Git.

## Installation

```powershell
python -m pip install -e ".[dev]"
```

Optional SolidWorks path configuration:

```powershell
$env:SOLIDWORKS_EXE="C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe"
$env:SOLIDWORKS_TEMPLATE_DIR="C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates"
```

## Quickstart

```powershell
fromcad2cfd solidworks preflight
fromcad2cfd solidworks create-cylinder --radius-mm 10 --height-mm 20
fromcad2cfd cad contract
fromcad2cfd nx preflight
fromcad2cfd nx write-basic-solid-pack-job --project nx_basic_solid_pack_demo
```

Private models should be placed only in local ignored folders such as:

```text
sandbox/input/
sandbox/output/
sandbox/reports/
05_projects/
06_logs/
```

## Roadmap

- `v0.1`: SolidWorks automation alpha.
- `v0.2`: CAD backend abstraction and Siemens NX controlled-journal backend.
- `v0.3`: robust safe parameter editing, richer inspection, and public synthetic examples.
- `v0.4`: Fluent Meshing prototype.
- `v0.5`: Fluent Solver setup and CFD post-processing prototypes.
- `v1.0`: full CAD-to-CFD closed-loop workflow.

## Private Data Policy

This repository does not include proprietary CAD models, Fluent case/data files, commercial software binaries, license files, or local absolute paths.

## Citation

If you use this project in academic work, cite it using `CITATION.cff`.
