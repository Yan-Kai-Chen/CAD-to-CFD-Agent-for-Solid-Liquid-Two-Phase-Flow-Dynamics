---
name: fromcad2cfd-nx-surface-repair
description: Controlled Siemens NX surface and sheet-body repair workflows for FromCAD2CFD. Use when imported CAD contains sheet bodies, open surfaces, gaps, bad faces, unsewn boundaries, facet-like faces, rough imported surfaces, or when a workflow needs surface healing, sewing, stitching, trimming, untrimming, face replacement, surface offset, thicken, or sheet-to-solid conversion before CFD meshing.
---

# FromCAD2CFD NX Surface Repair

Use this skill when geometry quality, not primitive creation, is the main problem.

## Mandatory Rules

- Never smooth or merge surfaces blindly.
- Classify the geometry before repair: solid body, sheet body, facet body, convergent body, or imported B-Rep.
- Preserve a copy of the pre-repair model.
- Record gaps, naked edges, self-intersections, face count, body count, and units before editing.
- Use controlled NX journals or approved MCP tools only.
- Stop if the repair target cannot be uniquely selected.
- Stop if sewing or healing creates non-manifold or unexpected bodies.
- Export `.prt` and `.x_t` after successful repair.
- Write JSON and Markdown reports.

## Workflow

1. Inspect the copied model.
2. Classify bodies and failure modes.
3. Choose the lowest-risk repair path:
   - stitch/sew existing sheets,
   - heal gaps or bad faces,
   - replace localized defective faces,
   - thicken a closed sheet,
   - reconstruct larger regions through reverse modeling.
4. Run a small controlled repair job.
5. Rebuild/update the model.
6. Validate solid/sheet state, body count, and export artifacts.
7. Record unresolved defects and recommended manual review items.

For operation-level contracts and stop conditions, read `references/surface_repair_contract.md`.

For planned curve and freeform-surface operation families, read `references/curve_surface_operation_map.md`.

## Implemented Entrypoints

Use only these controlled entrypoints for the currently implemented NX surface and sheet workflows:

- `fromcad2cfd nx write-inspect-job --input-file <model>`: write a copied model inspection job.
- `fromcad2cfd nx write-thicken-face-job --input-file <source-prt> --body-index <n> --face-index <n> --thickness-mm <value>`: write a copied-model face thicken job.
- `fromcad2cfd nx write-sew-sheet-bodies-job --input-file <source-prt> --target-sheet-body-index <n> --tool-sheet-body-indices <n[,n]> --tolerance-mm <value>`: write a copied-model sheet-body sew job.
- `fromcad2cfd nx write-curve-surface-demo-job`: write a synthetic basic-curve and bounded-plane sheet-surface smoke job.
- `src/fromcad2cfd_nx/journals/inspect_model.py`: classify bodies, faces, edges, solid/sheet/convergent/facet state, and export an inspection report.
- `src/fromcad2cfd_nx/journals/thicken_face.py`: copy an input `.prt`, optionally extract one selected face as a sheet, thicken the sheet face, save `.prt`, export `.x_t`, and write reports.
- `src/fromcad2cfd_nx/journals/sew_sheet_bodies.py`: copy an input `.prt`, select one target sheet body plus one or more tool sheet bodies by explicit 1-based body indices, sew them, save `.prt`, export `.x_t`, and write reports.
- `src/fromcad2cfd_nx/journals/create_curve_surface_demo.py`: create line, full-circle arc, ellipse, and a bounded-plane sheet surface from four closed boundary lines, then save `.prt`, export `.x_t`, and write reports.

For NX 12, direct thickening of a face on an existing solid may fail with `Cannot apply Thicken`. The stable local route is:

1. Use `ExtractFaceBuilder` with property assignments: `Type = Face`, `FaceOption = SingleFace`, `ParentPart = WorkPart`, `SurfaceType = SameAsOriginal`, `HideOriginal = False`, then add the selected face to `ObjectToExtract`.
2. Use `CreateThickenBuilder(NXOpen.Features.Feature.Null)`.
3. Set `FirstOffset`, `SecondOffset`, and `Tolerance`.
4. Set `builder.BooleanOperation.Type = NXOpen.GeometricUtilities.BooleanOperation.BooleanType.Create`.
5. Add the extracted sheet face through a dumb-face selection rule and commit the feature.

The thicken path currently requires `.prt` input and explicit 1-based body and face selectors. Stop before execution when the face selector cannot be audited or when the requested thickness may self-intersect.

For NX 12 sheet-body sew, the stable local route is:

1. Use `work_part.Features.CreateSewBuilder(NXOpen.Features.Feature.Null)`.
2. Set `builder.Type = NXOpen.Features.SewBuilder.Types.Sheet`, even when the desired result is a solid from closed sheets.
3. Add exactly one target sheet body through `builder.TargetBodies.Add(target_body)`.
4. Add the remaining sheet bodies through `builder.ToolBodies.Add(tool_body)`.
5. Set a positive `Tolerance`, commit, update, then validate solid/sheet body counts.

Do not use `SewBuilder.Types.Solid` for the current sheet-to-solid path; local NX 12 probing returned `Missing target body`. A closed sheet set sewn with `Types.Sheet` produced a solid in the synthetic cylinder smoke case.

For NX 12 basic curves and bounded-plane surface creation, the stable local route is:

1. Create lines with `work_part.Curves.CreateLine(start_point, end_point)`.
2. Create a full circle as an arc with `work_part.Curves.CreateArc(center, x_direction, y_direction, radius, 0.0, 2*pi)`.
3. Create ellipses with `work_part.Curves.CreateEllipse(center, x_direction, y_direction, major_radius, minor_radius, 0.0, 2*pi)`.
4. Create a bounded plane with `work_part.Features.CreateBoundedPlaneBuilder(NXOpen.Features.BoundedPlane.Null)`.
5. Add four boundary curves to `builder.BoundingCurves` using `ScRuleFactory.CreateRuleCurveDumb([curve])` and `Section.AddToSection(...)`.
6. Commit, update, then validate one sheet body and a non-empty `.x_t` export.

## Repair Strategy

Use sewing or stitching when:

- The model is a sheet body with small gaps.
- Boundaries are intended to form one closed shell.
- The target output is a watertight solid or thickened body.

Use localized face repair when:

- A few faces are damaged, missing, or too fragmented.
- The surrounding boundaries are clear and stable.
- Replacing the face is less risky than global smoothing.

Use reverse modeling when:

- The model is faceted or triangulated.
- The surface contains many artificial mesh edges.
- Analytic cylinders, planes, fillets, or ruled surfaces are visually obvious but not represented as clean B-Rep.

## Validation

Accept repair only when:

- The repaired body type matches the intended target.
- Open edges are eliminated or explicitly reported.
- Body count is expected.
- No known repair warning is hidden.
- `.prt` and `.x_t` exist and are non-empty.

Reject or stop when:

- Sewing produces extra bodies unexpectedly.
- A global operation changes important geometry scale or shape.
- The model remains faceted and unsuitable for CFD meshing.
- The operation cannot prove that the output is watertight when watertightness is required.
