# Siemens NX Basic Modeling Capability Matrix

This matrix fixes the bounded scope for the current NX foundation layer. It is
not an unlimited modeling roadmap. A capability is considered agent-facing only
after it has a safe job builder, a controlled journal or copied-model workflow,
non-overwrite outputs, and JSON/Markdown reports.

## Completed Foundation

| Capability | Current status | Entrypoint | Validation evidence |
| --- | --- | --- | --- |
| NX preflight | Implemented | `fromcad2cfd nx preflight` | Detects `run_journal.exe`, `ugraf.exe`, and NX environment values. |
| Synthetic cylinder | Implemented | `fromcad2cfd nx write-job --recipe cylinder` | Saves `.prt`, exports `.x_t`, optional STEP path remains secondary. |
| Synthetic cylinder subtract | Implemented | `fromcad2cfd nx write-job --recipe boolean-subtract-demo` | Creates one hollow solid body through `CreateSubtractFeature`. |
| Copied-model body subtract | Implemented | `fromcad2cfd nx write-boolean-subtract-job` | Requires explicit 1-based target/tool body indices after inspection. |
| Copied-model inspection | Implemented | `fromcad2cfd nx write-inspect-job` | Reports body, face, edge, and sheet/solid classification. |
| Copied-model face thicken | Implemented | `fromcad2cfd nx write-thicken-face-job` | Extracts a selected face when requested, then thickens and validates solid output. |
| Copied-model sheet sew | Implemented | `fromcad2cfd nx write-sew-sheet-bodies-job` | Uses NX 12 `SewBuilder.Types.Sheet` with target/tool sheet bodies. |
| Basic curves and bounded plane | Implemented | `fromcad2cfd nx write-curve-surface-demo-job` | Creates line, full-circle arc, ellipse, and one bounded-plane sheet body. |
| Basic solid pack | Implemented | `fromcad2cfd nx write-basic-solid-pack-job` | Creates block, sphere, cone, boolean unite, boolean intersect, and copy-translate; validates six solid bodies and exports `.x_t`. |
| Edge/wall/trim/import pack | Implemented | `fromcad2cfd nx write-edge-wall-trim-pack-job` | Creates edge blend, chamfer, shell, shell-face, controlled tapered frustum, plane cut by cutter, Parasolid export, and Parasolid import-to-`.prt`. |
| Copied-model plane cut | Implemented | `fromcad2cfd nx write-plane-cut-body-job` | Copies an input `.prt`, selects one solid body by 1-based index, removes one side of an x/y/z plane through a generated cutter body, saves `.prt`, and exports `.x_t`. |
| Parasolid import to PRT | Implemented | `fromcad2cfd nx write-import-parasolid-job` | Imports `.x_t` or `.x_b` into a new controlled `.prt`, verifies body creation, and re-exports `.x_t`. |
| Transform/profile pack | Implemented | `fromcad2cfd nx write-transform-profile-pack-job` | Creates rotate-copy, mirror body, project curve to face, body-plane intersection curve, revolve, sweep-profile-along-path, and through-curves loft smoke geometry; validates seven solid bodies, one sheet body, and exports `.x_t`. |
| Reverse Step 1 STL to convergent PRT | Implemented | `fromcad2cfd nx write-reverse-step1-stl-import-job` | Copies STL input, imports as cleaned convergent bodies with automatic cleanup, and saves `.prt` plus JSON/Markdown reports. |
| Reverse Step 2 Cage from Facet Body | Implemented, requires NX1926+ | `fromcad2cfd nx write-reverse-step2-cage-from-facet-body-job` | Copies the Step 1 `.prt`, selects convergent bodies, runs `CageFromFacetBodyBuilder` with average size `10 mm`, and saves `.prt` plus reports; requires `nx_subdivision`. |
| Reverse Step 3/4 XOY plane combine | Implemented | `fromcad2cfd nx write-reverse-step3-step4-xoz-plane-combine-job` | Copies a Parasolid input, imports it into `.prt`, creates a 1000 mm XOY bounded-plane sheet centered at the origin, moves it +Z, and runs `CombineSheetsBuilder` with recorded keep/remove region trackers; saves `.prt` plus JSON/Markdown reports. |

## Basic NXOpen Patterns Verified Locally

Use these patterns when extending controlled journals:

- Block: `work_part.Features.CreateBlockFeatureBuilder(NXOpen.Features.Feature.Null)` plus `SetOriginAndLengths(...)`.
- Sphere: `CreateSphereBuilder(NXOpen.Features.Sphere.Null)`, `builder.Type = NXOpen.Features.SphereBuilder.Types.CenterPointAndDiameter`, `builder.CenterPoint = point`.
- Cone: `CreateConeBuilder(NXOpen.Features.Cone.Null)`, `builder.Type = NXOpen.Features.ConeBuilder.Types.DiametersAndHeight`, `builder.Axis = axis`.
- Boolean unite/intersect: `CreateUniteFeature(...)` and `CreateIntersectFeature(...)` with explicit target/tool bodies.
- Copy-translate: `work_part.BaseFeatures.CreateMoveObjectBuilder(NXOpen.Features.MoveObject.Null)`, `MoveObjectResultOptions.CopyOriginal`, `ModlMotion.Options.DeltaXyz`.
- Edge blend: `CreateEdgeBlendBuilder(NXOpen.Features.Feature.Null)` plus `AddChainset(...)`.
- Chamfer: `CreateChamferBuilder(NXOpen.Features.Feature.Null)`, `OffsetAndAngle`, and a `SmartCollector`.
- Shell: `CreateShellBuilder(NXOpen.Features.Feature.Null)`, explicit `Body`, `SetDefaultThickness(...)`, and `RemovedFacesCollector`.
- Shell face: `CreateShellFaceBuilder(NXOpen.Features.ShellFace.Null)` plus an explicit face rule and thickness expression.
- Plane cut: create a bounded cutter block on one side of an x/y/z plane, then use `CreateSubtractFeature(...)`.
- Parasolid import: `work_part.ImportManager.CreateParasolidImporter()`, set `FileName`, commit, then validate imported bodies.
- Rotate-copy: `work_part.BaseFeatures.CreateMoveObjectBuilder(NXOpen.Features.MoveObject.Null)`, `MoveObjectResultOptions.CopyOriginal`, `ModlMotion.Options.Angle`, and an explicit angular axis.
- Mirror body: create a datum plane through `DatumPlaneBuilder.CommitFeature()`, extract the committed datum entity with `GetEntities()`, then set `MirrorBodyBuilder.Plane`.
- Project curve to face: use `NXOpen.UF.CurveProj_Struct`, initialize with `UFSession.Curve.InitProjCurvesData(...)`, then call `CreateProjCurves(...)` with explicit curve and face tags.
- Intersection curve: create a datum plane, then use `UFSession.Curve.CreateIntObject(...)` against explicit body and datum tags.
- Revolve profile: use `UFSession.Modl.CreateRevolution(...)` with a closed profile and explicit axis point/direction.
- Sweep profile along path: use `UFSession.Modl.CreateExtrusionPath(...)` for the validated NX 12 profile-along-guide route.
- Through-curves loft: use `CreateThroughCurvesBuilder(...)` with `SectionsList.Append(section)`; current validated output is a sheet body.
- Cage from Facet Body: use `work_part.SubdivisionBodies.CreateCageFromFacetBodyBuilder()` inside `session.SubdivisionTaskEnvironment.Enter()/Exit()`, set `AverageSize.Value`, and populate `FacetRegion` with `FacetSelectionRuleFactory.CreateRuleBodyFacets(...)`.
- XOY plane combine: use four boundary lines, `CreateBoundedPlaneBuilder`, `MoveObjectBuilder.MoveOriginal`, `work_part.Features.TrimFeatureCollection.CreateCombineSheetsBuilder(...)`, and explicit `BooleanRegionSelect` keep/remove `RegionTracker` objects learned from a manual journal capture.

## Engineer-In-The-Loop Journal Capture

Manual NX journal capture is part of the development workflow for
selector-sensitive commands. It is not an agent-facing MCP tool.

Use `docs/nx/manual_journal_capture.md` when a user can complete an operation in
the UI but a controlled journal is missing the exact selector sequence. Preserve
the recorded journal under the local runtime folder, extract only stable API
patterns, then convert them into a safe job builder and controlled journal.

## Not Yet Agent-Facing

These are still important, but should be implemented as separate finite packs
because they require exact edge/face/profile selectors and stronger topology
validation:

- True DraftBody feature workflows with arbitrary face selectors.
- Copied-model rotate/mirror with arbitrary body selectors.
- User-specified project/intersection curves on real imported geometry.
- User-specified real-model revolve, sweep, through-curves, and loft profile selection.
- Downstream conversion of subdivision/convergent reverse-modeling outputs into clean analytic B-Rep.

## Acceptance Rule For New Basic Operations

Add a new NX operation only when all of the following are true:

- It has a bounded operation contract and explicit selectors.
- It has a synthetic smoke test before use on real geometry.
- It does not overwrite user inputs.
- It saves `.prt` and exports Parasolid `.x_t`.
- If the operation creates convergent or subdivision-only geometry, it saves `.prt` and explains why Parasolid `.x_t` is deferred.
- It writes JSON and Markdown reports.
- It has a clear stop condition for ambiguous body, face, edge, feature, curve, or expression matches.
