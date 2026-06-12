# A CAD-to-CFD Agentic Automation Framework for Solid-Liquid Two-Phase Flow Dynamics

**A CAD-to-CFD Agentic Automation Framework for Solid-Liquid Two-Phase Flow Dynamics** is an early-stage research and engineering framework for automating the path from CAD geometry to CFD-ready artifacts, with an explicit emphasis on geometry preparation, flow-domain construction, and repeatable preprocessing for solid-liquid two-phase flow dynamics.

The current `v0.1.0` release focuses on a SolidWorks automation alpha. Fluent Meshing, Fluent Solver setup, and CFD post-processing are included as documented roadmap modules.

## Current Status

- SolidWorks automation: working alpha
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

## Safety First

The framework follows conservative automation rules:

- Never overwrite original CAD files.
- Copy inputs to working/output folders before edits.
- Use timestamped outputs.
- Inspect models before modifying existing geometry.
- Stop if a dimension or feature cannot be uniquely identified.
- Rebuild after every geometry edit.
- Stop on rebuild failure.
- Export STEP and write reports after successful operations.

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
```

Private models should be placed only in local ignored folders such as:

```text
sandbox/input/
sandbox/output/
sandbox/reports/
```

## Roadmap

- `v0.1`: SolidWorks automation alpha.
- `v0.2`: robust safe parameter editing and richer inspection.
- `v0.3`: Fluent Meshing prototype.
- `v0.4`: Fluent Solver setup prototype.
- `v0.5`: CFD post-processing prototype.
- `v1.0`: full CAD-to-CFD closed-loop workflow.

## Private Data Policy

This repository does not include proprietary CAD models, Fluent case/data files, commercial software binaries, license files, or local absolute paths.

## Citation

If you use this project in academic work, cite it using `CITATION.cff`.
