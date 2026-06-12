# Reverse Modeling Contract

Use this contract when rough imported geometry must be rebuilt into cleaner CAD for CFD.

## Required Inputs

- Source geometry path.
- Copied working geometry path.
- Source type: mesh, STL, facet body, convergent body, sheet body, solid body, or imported B-Rep.
- Intended downstream use: Fluent Meshing, Fluent Solver, visualization, or CAD editing.
- Required tolerance, or a clear statement that tolerance is unknown.
- Critical features that must be preserved.

## Reconstruction Levels

### Level 0: Preserve and Inspect

Use when the user only needs classification.

Output:

- body type,
- bounding box,
- face or facet count,
- estimated problem list,
- recommended next step.

### Level 1: Repair Existing CAD

Use when geometry is B-Rep with local defects.

Output:

- repaired `.prt`,
- `.x_t`,
- defect report,
- unresolved warning list.

### Level 2: Analytic Replacement

Use when the model has recognizable engineering shapes.

Typical replacements:

- planes,
- cylinders,
- cones,
- spheres,
- rectangular ribs,
- slots,
- simple fillets,
- datum-symmetric features.

Acceptance:

- Key dimensions match the source.
- Deviation is recorded.
- CFD-relevant interfaces are preserved.

### Level 3: Freeform Surface Fit

Use when smooth surfaces cannot be represented by simple primitives.

Acceptance:

- Patch boundaries are explicit.
- Surface continuity target is recorded.
- Fitted deviation is recorded.
- The output is not falsely described as exact.

### Level 4: Hybrid Reconstruction

Use when the model combines analytic and freeform regions.

Acceptance:

- Analytic, freeform, preserved, and uncertain regions are labeled separately.
- The report states which regions are reconstructed and which are unchanged.

## Segmentation Checklist

Before rebuilding, identify:

- main axes,
- symmetry planes,
- datum origin assumptions,
- planar regions,
- cylindrical or conical regions,
- fillet-like transition regions,
- repeated features,
- small details that can be suppressed for CFD,
- details that must remain for physics.

## Validation

A reverse-modeled output is acceptable only when:

- The source and reconstructed bounding boxes are compared.
- Key dimensions are compared.
- Body count and body type are reported.
- Major deviations are documented.
- `.prt` and `.x_t` exist and are non-empty.

## Stop Conditions

Stop when:

- The tolerance requirement is unknown and shape changes would be significant.
- Critical details cannot be distinguished from mesh noise.
- The model cannot be segmented into stable reconstruction regions.
- The user has not approved simplification of CFD-irrelevant small details.
