---
name: fromcad2cfd-reverse-modeling
description: Reverse-modeling workflow for FromCAD2CFD. Use when rough imported geometry, STL or faceted mesh bodies, over-fragmented B-Rep, scanned geometry, triangulated surfaces, or low-quality CAD must be rebuilt into cleaner analytic or NURBS CAD for CFD, including segmentation, primitive fitting, surface fitting, feature reconstruction, and future user-taught reverse-modeling procedures.
---

# FromCAD2CFD Reverse Modeling

Use this skill when the best answer is to rebuild clean CAD from rough geometry instead of merely healing existing faces.

## Mandatory Rules

- Preserve the original input.
- Do not promise automatic mesh-to-perfect-CAD conversion.
- Classify whether the input is mesh, facet body, convergent body, sheet body, solid body, or over-fragmented B-Rep.
- Separate visual smoothing from geometric reconstruction.
- Prefer analytic reconstruction for planes, cylinders, cones, spheres, slots, ribs, and simple fillets.
- Use surface repair only when existing surfaces are already close to clean B-Rep.
- Record every user-taught procedure in `references/user_taught_reverse_modeling.md`.
- Use `references/manual_journal_capture.md` as the engineer-in-the-loop fallback when a user-validated NX UI operation needs recorder evidence before it can become a controlled journal.
- Validate with `.prt`, body count, bounding box, and report artifacts; export `.x_t` only when the body type supports it.

## Decision Tree

Use direct repair when:

- The model is already B-Rep.
- Defects are local.
- Sewing or face repair can recover a watertight output.

Use semi-automatic surface reconstruction when:

- The model has recognizable smooth regions.
- Boundary curves can be extracted reliably.
- A fitted surface can replace many small faces.

Use manual parametric reconstruction when:

- The faceted model represents simple engineering features.
- Planes, cylinders, ribs, holes, fillets, and symmetry are clear.
- CFD meshing quality matters more than exact preservation of every small facet.

Use hybrid reconstruction when:

- Some areas are analytic and some are freeform.
- The model has critical interfaces that must be preserved but non-critical surfaces can be simplified.

## Workflow

1. Run the user-taught Step 1 STL import when the source is STL: copy the STL, create a new NX part, import as a cleaned convergent body, and save `.prt`.
2. Run the user-taught Step 2 Cage from Facet Body only when a newer NX build exposes `CageFromFacetBodyBuilder`: copy the Step 1 `.prt`, select convergent bodies, set average size, and save `.prt`.
3. Run the user-taught Step 3/4 XOY plane combine when the Step 2 result has been exported to Parasolid: copy the `.x_t`, import it into a new NX part, create the 1000 mm XOY bounded-plane sheet centered at the origin, move it +Z by the requested offset, and run Combine.
4. Inspect and classify the geometry.
5. Segment the model into planes, cylinders, cones, freeform patches, fillets, and uncertain regions.
6. Identify datums, symmetry planes, axes, and design intent.
7. Decide which regions are reconstructed, repaired, or left unchanged.
8. Rebuild a small pilot region first.
9. Compare bounding boxes, key dimensions, and body count against the source.
10. Export `.prt` and `.x_t` when the body type supports it.
11. Write a report describing deviations and unresolved regions.
12. Update project memory after a new reverse-modeling method is validated.

## Implemented Entrypoints

- `fromcad2cfd nx write-reverse-step1-stl-import-job --input-file <source.stl>`: copy the STL into the project input folder and write the Step 1 job JSON.
- `fromcad2cfd nx write-reverse-step2-cage-from-facet-body-job --input-file <step1.prt> --average-size-mm 10`: copy the accepted Step 1 PRT and write the Step 2 Cage from Facet Body job JSON.
- `fromcad2cfd nx write-reverse-step3-step4-xoz-plane-combine-job --input-file <step3_source.x_t> --square-size-mm 1000 --plane-offset-z-mm 5`: copy the accepted Parasolid, create the Step 3 XOY bounded-plane sheet, and write the Step 4 Combine job JSON. The `xoz` name is a legacy compatibility name; the validated geometry is XOY.
- `src/fromcad2cfd_nx/journals/import_stl_convergent_step1.py`: create a new millimeter NX part, import the copied STL as a cleaned convergent body, save `.prt`, attempt Parasolid export as a secondary artifact, and write JSON/Markdown reports.
- `src/fromcad2cfd_nx/journals/cage_from_facet_body_step2.py`: open a copied Step 1 `.prt`, select convergent bodies, enter the NX subdivision task environment, create a cage from facet regions, save `.prt`, and write JSON/Markdown reports.
- `src/fromcad2cfd_nx/journals/xoz_plane_combine_step3_step4.py`: import copied Parasolid into a new part, create a square XOY bounded-plane sheet, move it +Z, run CombineSheets with recorded keep/remove region trackers, save `.prt`, attempt `.x_t`, and write JSON/Markdown reports.

Read `references/reverse_modeling_contract.md` before planning a new reverse-modeling operation.
Read `references/user_taught_reverse_modeling.md` when the user has taught a project-specific method.
Read `references/manual_journal_capture.md` when a validated UI operation needs to be converted into a controlled NXOpen workflow.

## Stop Conditions

Stop and ask for review when:

- The geometry cannot be segmented into meaningful regions.
- The target accuracy tolerance is unknown and the reconstruction would change the shape.
- A fitted surface would erase functionally important details.
- The output cannot be validated against key dimensions or CFD meshing requirements.
