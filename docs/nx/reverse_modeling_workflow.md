# NX Reverse Modeling Workflow

This document summarizes the current FromCAD2CFD NX reverse-modeling workflow.
It is written as a reproducible engineering route, not as a private model
record. Real CAD/STL/Parasolid inputs remain outside the repository.

## Scope

The workflow converts rough faceted geometry into an NX-controlled intermediate
that can be inspected and prepared for later CAD-to-CFD work.

Primary artifacts:

- NX `.prt`
- JSON report
- Markdown report

Secondary artifacts:

- Parasolid `.x_t` only when the body type supports stable export.

## Step 1: STL To Cleaned Convergent Body

Entrypoint:

```powershell
fromcad2cfd nx write-reverse-step1-stl-import-job --input-file <source.stl> --project <project_name>
```

User-taught settings:

- facet body output type: convergent
- automatic cleanup: enabled
- minimum angle for folded facets: `15.0 deg`
- minimum facet number: `100`
- STL units: millimeters

Acceptance:

- original STL preserved
- copied STL exists in runtime `input`
- `.prt` exists and is non-empty
- at least one imported body is classified as convergent
- JSON/Markdown reports exist

## Step 2: Cage From Facet Body

Entrypoint:

```powershell
fromcad2cfd nx write-reverse-step2-cage-from-facet-body-job --input-file <step1.prt> --average-size-mm 10 --project <project_name>
```

User-taught settings:

- select all convergent bodies or convergent facet regions
- average face size: `10.0 mm`
- deviation plot: disabled unless debugging

Acceptance:

- original Step 1 `.prt` preserved
- copied `.prt` exists in runtime `input`
- output `.prt` exists and is non-empty
- report records selected body count and selected facet count

Boundary:

- requires an NX build exposing `CageFromFacetBodyBuilder`
- requires the subdivision capability/license

## Step 3: XOY Bounded Plane

Entrypoint:

```powershell
fromcad2cfd nx write-reverse-step3-step4-xoz-plane-combine-job --input-file <step2_or_step3.x_t> --square-size-mm 1000 --plane-offset-z-mm 5 --project <project_name>
```

The command name still contains `xoz` for compatibility. The validated geometry
is XOY.

Geometry:

- create a new NX part
- import the copied Parasolid input
- create a `1000 mm x 1000 mm` square on XOY
- center the square at the origin
- create a bounded-plane sheet from the square boundary
- translate the sheet by `+5 mm` along global Z

Expected plane bounding box:

```text
[-500, -500, 5, 500, 500, 5]
```

## Step 4: Combine Sheets

Command family:

- `Insert > Combine > Combine`
- `NXOpen.Features.CombineSheetsBuilder`

The validated automated route uses the manual-journal-derived region-selection
pattern:

- set `BooleanRegionSelect.SelectOption.KeepOrRemove`
- notify that bodies changed
- clear previous region trackers
- keep target and tool regions
- add a target `RegionTracker` with a point selector on the XOY plane
- add a tool `RegionTracker` with a face selector on the imported sheet body
- commit `CombineSheetsBuilder`

Acceptance:

- `.prt` exists and is non-empty
- report records `step4_combine_succeeded = true`
- report records a committed `NXOpen.Features.CombineSheets` feature
- no original input is overwritten

Private local validation:

- validated on a copied private reverse-modeled Parasolid input
- accepted artifact: saved NX `.prt`
- report artifacts: JSON and Markdown
- result: `step4_combine_succeeded = true`

The private source filename, generated `.prt`, local runtime paths, and reports
are intentionally omitted from this public repository.

## Manual Journal Capture

Manual journal capture is now part of the development process for
selector-sensitive NX operations. Use it only to learn a stable NXOpen pattern
from a user-validated UI operation, then convert the pattern into a controlled
project journal.

See:

- `docs/nx/manual_journal_capture.md`
- `skills/fromcad2cfd-reverse-modeling/references/manual_journal_capture.md`

MCP must not expose:

- arbitrary NXOpen calls
- arbitrary journal playback
- journal recording
- destructive overwrite/delete operations

## Open Boundary

This workflow creates and combines reverse-modeled sheet geometry. It does not
claim automatic conversion of all faceted geometry into clean analytic CAD.
Future reverse-modeling work should add bounded, validated reconstruction steps
for analytic replacement, surface fitting, deviation measurement, and CFD-driven
feature suppression.
