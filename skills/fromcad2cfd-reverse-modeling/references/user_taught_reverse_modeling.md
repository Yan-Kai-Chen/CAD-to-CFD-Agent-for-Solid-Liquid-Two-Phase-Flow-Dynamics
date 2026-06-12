# User-Taught Reverse Modeling Procedures

This file is reserved for project-specific reverse-modeling methods taught by the user.

## Step 1: Import STL as a Cleaned Convergent Body

Geometry type:

- STL or faceted mesh input.

Intended use:

- Convert a raw STL import into an NX convergent body as the first reverse-modeling preparation step.
- Preserve the original STL and work on a copied input file.

Exact steps:

1. Create a new NX millimeter part.
2. Import the STL file.
3. Set facet body output type to `Convergent`.
4. Enable automatic cleanup.
5. Set minimum angle for folded facets to `15.0` degrees.
6. Set minimum facet number to `100`.
7. Set STL file units to `Millimeters`.
8. Keep the information window disabled unless debugging.
9. Save the imported NX part as `.prt`.
10. Classify body count, convergent state, bounding box, and facet count.

NX operation route:

- Use `work_part.FacetedBodies.CreateSTLImportBuilder()`.
- Set `FacetBodyType = NXOpen.Facet.STLImportBuilder.FacetBodyTypes.Psm`.
- Local NX 12 probing confirmed that `FacetBodyTypes.Psm` produces `IsConvergentBody = True`; this maps to the UI option `Convergent`.
- Set `CleanUp = True`.
- Set `MinimumAngleFoldedFacets = 15.0`.
- Set `MinimumFacetNumber = 100`.
- Set `STLFileUnits = NXOpen.Facet.STLImportBuilder.STLFileUnitsTypes.Millimeters`.
- Set `ShowInformationWindow = False`.

Acceptance criteria:

- Original STL remains unchanged.
- Copied input STL exists in the project runtime `input` folder.
- NX `.prt` exists and is non-empty.
- At least one body exists after import.
- At least one body reports `IsConvergentBody = True`.
- JSON and Markdown reports record input paths, import parameters, body classification, bounding boxes, and facet counts.

Failure modes:

- The STL path is missing or not `.stl`.
- NX creates no bodies.
- NX imports a facet/JT/NX facet body instead of a convergent body.
- The input is too damaged for automatic cleanup to import.
- Parasolid `.x_t` export may fail or be incomplete for convergent bodies; treat `.prt` as the primary Step 1 artifact.

Private validation summary:

- Validated locally on a large private STL-derived research geometry.
- The original STL was preserved, a copied input was used, and the accepted
  artifact was a saved NX `.prt` plus JSON/Markdown reports.
- The private source filename, local output paths, and generated model files are
  intentionally omitted from this public repository.
- Parasolid export can fail for convergent bodies; keep `.prt` as the Step 1
  artifact when that occurs.

## Step 2: Create a Subdivision Cage from Convergent Facet Bodies

Geometry type:

- NX `.prt` created by Step 1, containing convergent bodies imported from STL.

Intended use:

- Convert cleaned convergent/faceted regions into an NX subdivision cage as the next reverse-modeling preparation step.
- Preserve the Step 1 `.prt` and work on a copied input file.

Exact steps:

1. Open the accepted Step 1 `.prt`.
2. Enter the NX Creative Modeling / subdivision task environment.
3. Run `Cage from Facet Body`.
4. Select all convergent bodies or all convergent facet regions.
5. Set face size average size to `10.0 mm`.
6. Keep deviation plot disabled unless debugging.
7. Confirm and wait for the subdivision body creation to complete.
8. Save the resulting `.prt`.
9. Classify selected body count, facet count, and subdivision body count.

NX operation route:

- Use a newer NX build that exposes `NXOpen.Features.Subdivision.CageFromFacetBodyBuilder` (created in NX1926).
- Enter with `session.SubdivisionTaskEnvironment.Enter()` before creating the builder and exit with `session.SubdivisionTaskEnvironment.Exit()` after commit.
- Create the builder with `work_part.SubdivisionBodies.CreateCageFromFacetBodyBuilder()`.
- Set `AverageSize.Value = 10.0`.
- Populate `FacetRegion` with `work_part.FacetSelectionRuleFactory.CreateRuleBodyFacets(...)`.
- The operation requires the `nx_subdivision` license.

Acceptance criteria:

- Original Step 1 `.prt` remains unchanged.
- Copied input `.prt` exists in the project runtime `input` folder.
- Output `.prt` exists and is non-empty.
- At least one convergent body is selected.
- The journal reports selected body count, selected facet count, pre/post subdivision body count, and the builder route used.
- JSON and Markdown reports are written.

Failure modes:

- The active NX installation is older than NX1926 and does not expose `CageFromFacetBodyBuilder`.
- The `nx_subdivision` license is unavailable.
- The Step 1 `.prt` contains no convergent bodies.
- NX cannot create body facet selection rules from the selected bodies.
- Creation may take a long time for large STL-derived parts; do not repeatedly rerun without reading the first diagnostic report.

Private validation summary:

- Validated locally on the copied Step 1 `.prt` from the same private research
  geometry.
- The accepted Step 2 artifact was a saved NX `.prt` plus JSON/Markdown reports.
- The operation used all selected convergent bodies, average size `10.0 mm`,
  and a committed subdivision body feature.
- The private model filename, local output paths, and generated `.prt` files are
  intentionally omitted from this public repository.
- Diagnostic note: some NX subdivision collection APIs may not report body
  counts consistently; check both feature rows and active subdivision feature
  metadata.

## Step 3/4: Create an XOY Bounded Plane and Combine It with the Reverse-Modeled Body

Geometry type:

- Parasolid `.x_t` or `.x_b` exported from the accepted NX reverse-modeling result.

Intended use:

- Use a controlled sheet body as a cutting/combining surface during the reverse-modeling workflow.
- Preserve the Parasolid input and work on a copied input file.
- Produce an NX `.prt` that can be visually checked before downstream CAD-to-CFD preparation.

Exact steps:

1. Copy the accepted Parasolid input into the runtime project input folder.
2. Create a new NX millimeter part.
3. Import the copied Parasolid.
4. On the XOY plane, create a `1000 mm x 1000 mm` square centered at the origin.
5. Use the continuous boundary curves with `Surface > Bounded Plane` to create a sheet body.
6. Move the bounded-plane sheet body by `+5 mm` along the global Z axis.
7. Run `Insert > Combine > Combine`.
8. Select the imported reverse-modeled body or bodies and the moved plane sheet body.
9. Confirm the operation.
10. Save the resulting `.prt`.
11. Attempt Parasolid `.x_t` export when the output body type supports it.
12. Write JSON and Markdown reports.

NX operation route:

- Use `work_part.ImportManager.CreateParasolidImporter()` for the copied input.
- Create the square boundary with four `work_part.Curves.CreateLine(...)` curves:
  - `(-500, -500, 0)` to `(500, -500, 0)`,
  - `(500, -500, 0)` to `(500, 500, 0)`,
  - `(500, 500, 0)` to `(-500, 500, 0)`,
  - `(-500, 500, 0)` to `(-500, -500, 0)`.
- Use `work_part.Features.CreateBoundedPlaneBuilder(...)`.
- Move the sheet body with `work_part.BaseFeatures.CreateMoveObjectBuilder(...)`,
  `MoveObjectResultOptions.MoveOriginal`, and a Delta XYZ motion of `(0, 0, 5)`.
- Use `work_part.Features.TrimFeatureCollection.CreateCombineSheetsBuilder(...)`.
- Populate `CombineSheetsBuilder.Bodies` through a body selection rule.
- Use `CombineSheetsBuilder.Regions` for the region-selection state:
  - set `SelectMethod = KeepOrRemove`,
  - call `NotifyBodiesHaveChanged(...)`,
  - clear existing region trackers,
  - set target and tool keep/remove modes to `Keep`,
  - add a target region tracker with `OnTool = false` and a point selector on the XOY plane,
  - add a tool region tracker with `OnTool = true` and a face selector on each imported sheet body.
- Stop with a diagnostic report if NX cannot create valid keep/remove regions.

Acceptance criteria:

- Original Parasolid remains unchanged.
- Copied input Parasolid exists in the project runtime folder.
- Output NX `.prt` exists and is non-empty.
- The Step 3 sheet body is created from four boundary curves on XOY and moved by the requested Z offset.
- Step 4 reports whether `CombineSheetsBuilder` committed successfully.
- JSON and Markdown reports record input paths, body classification, bounding boxes, selected body count, combine attempts, and export status.

Failure modes:

- The Parasolid import creates no bodies.
- The input contains no sheet bodies and cannot participate in `CombineSheetsBuilder`.
- The moved plane does not intersect the body in a way that creates a valid NX combine region.
- NX cannot infer a keep/remove region from journal mode even though the UI can show selectable regions.
- Parasolid export may fail for mixed convergent/subdivision/sheet results; keep `.prt` as the primary inspection artifact.

Private validation summary:

- Validated locally on a copied private Parasolid export from the reverse-modeled
  NX result.
- The accepted artifact was a saved NX `.prt` plus JSON/Markdown reports.
- Result: `step4_combine_succeeded = true`; the committed feature type was
  `NXOpen.Features.CombineSheets`; the successful combine attempt was
  `recorded_keep_or_remove_regions`.
- The private source filename, local output paths, and generated model files are
  intentionally omitted from this public repository.
- Note: the file and CLI names still contain `xoz` for legacy compatibility,
  but the validated Step 3 plane is XOY.

Recorder-derived implementation note:

- Manual NX recording is a valid development aid for selector-sensitive UI workflows.
- The successful Step 4 recorder output showed that body selection alone is insufficient; NX requires explicit `RegionTracker` objects for the keep/remove region selection stage.
- The captured local C# journal was preserved under the project runtime as `05_projects\nx_journal_capture\input\manual_step4_combine_all_regions.cs`.
- Do not expose journal recording or arbitrary journal replay through MCP; convert the stable recorded pattern into controlled code.

## Update Rule

When the user teaches a new reverse-modeling method, add:

- method name,
- geometry type,
- intended use,
- exact steps,
- NX operation or external tool route,
- acceptance criteria,
- failure modes,
- validated example path if available.
