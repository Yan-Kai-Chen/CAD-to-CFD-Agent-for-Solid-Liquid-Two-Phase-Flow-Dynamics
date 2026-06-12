# Common CAD Backend Contract

The common CAD backend layer defines the minimum contract that SolidWorks, Siemens NX, and future CAD integrations must follow before their outputs are handed to Fluent-oriented workflows.

The layer is implemented in `fromcad2cfd_cad`.

## Purpose

The framework should not require Fluent Meshing, Fluent Solver setup, or post-processing modules to know whether geometry came from SolidWorks or NX. CAD-specific automation should produce the same kind of export metadata, reports, and safety outcomes.

```text
Agent request
  -> Common CAD backend contract
      -> SolidWorks backend
      -> NX backend
  -> STEP or Parasolid export
  -> CFD handoff metadata
  -> Fluent Meshing / Solver / Post-processing
```

## Required Backend Methods

Each CAD backend must implement:

- `preflight`
- `create_test_geometry`
- `inspect_model`
- `copy_model_for_edit`
- `edit_parameter_by_exact_name`
- `rebuild_and_validate`
- `export_geometry`
- `write_report`

These methods are intentionally high-level. The MCP layer should expose safe workflow tools, not raw CAD API calls.

## Shared Data Structures

- `AgentResult`: common serializable result envelope.
- `GeometryRecipe`: backend-neutral geometry creation request.
- `ParameterEditRequest`: safe parameter edit request.
- `ModelInspection`: feature, parameter, body, and configuration summary.
- `ExportManifest`: CAD export metadata for CFD handoff.
- `CADBackendCapabilities`: capability declaration for backend discovery and MCP tool planning.

## Export Policy

Preferred CFD handoff formats are:

- `STEP`
- `PARASOLID`

Other formats such as `IGES` and `STL` may be useful for inspection or fallback workflows, but they are not the default target for solid-liquid two-phase flow CFD preparation.

## Safety Expectations

Backends must preserve the framework safety policy:

- Do not modify original input files in place.
- Copy inputs before editing.
- Use unique output paths.
- Inspect model structure before modifying existing geometry.
- Stop if a parameter cannot be uniquely identified.
- Rebuild after edits.
- Stop on rebuild failure.
- Export a CFD handoff file and write JSON/Markdown reports.

## CLI

```powershell
fromcad2cfd cad contract
fromcad2cfd cad normalize-format step
fromcad2cfd cad list-registered
```

`list-registered` reports only backends registered in the current Python process. The SolidWorks and NX backend packages may register factories later, but the common layer does not import CAD-specific packages by default.
