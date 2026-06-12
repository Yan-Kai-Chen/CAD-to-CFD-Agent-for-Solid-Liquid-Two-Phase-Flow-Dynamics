# NX Surface Repair Contract

Use this contract before attempting surface healing, sewing, stitching, thickening, or sheet-to-solid conversion.

## Required Inspection Data

- Source file path and copied working file path.
- Unit system.
- Body count by type:
  - solid body,
  - sheet body,
  - facet body,
  - convergent body,
  - unknown body.
- Face count and edge count when available.
- Open edge or naked edge count when available.
- Bounding box.
- Known warnings from NX import or update.

## Repair Categories

### Sew or Stitch Sheets

Use when open sheets should form one closed shell.

Inputs:

- one target sheet body selector,
- one or more tool sheet body selectors,
- gap tolerance,
- expected solid or sheet output,
- expected body count.

Acceptance:

- Open edges are reduced or eliminated.
- Body count is expected.
- If solid output is required, the final body is a solid.
- If the job expects closed sheets, remaining sheet body count is zero or explicitly reported.

NX 12 implementation note:

- Use `SewBuilder.Types.Sheet` with one target sheet body and the remaining sheet bodies as tools.
- Validate the result by body type, not by the builder type name, because closed sheets may become a solid even when the builder type is `Sheet`.

### Heal Local Defects

Use when a few faces are damaged or missing.

Inputs:

- defective face selectors,
- boundary loop selectors,
- replacement method,
- expected continuity level.

Acceptance:

- Replacement faces follow the intended boundary.
- Local repair does not distort unrelated geometry.
- Update succeeds without hidden warnings.

### Offset or Thicken

Use when sheet surfaces need physical thickness or when CFD preprocessing needs a solid shell.

Inputs:

- sheet body selector,
- thickness or offset value,
- direction rule,
- cap rule,
- expected solid or sheet output.

Acceptance:

- Thickness is positive.
- The output state matches the request.
- Self-intersections are absent or reported as failure.

### Simplify or Merge Faces

Use only after inspection proves the faces are imported B-Rep fragments rather than essential design detail.

Inputs:

- candidate face group,
- target analytic type if known,
- allowed deviation tolerance.

Acceptance:

- Important ridges, ribs, holes, and interfaces are preserved.
- Deviation is recorded.
- The output is more suitable for meshing than the input.

## CFD Readiness Checks

Accept repaired geometry for CFD preparation only when:

- The fluid-solid interface is clear.
- No open boundaries remain unless intentionally treated as inlets, outlets, or symmetry planes.
- Tiny sliver faces and non-manifold regions are either removed or listed as manual review items.
- `.prt` and `.x_t` are written successfully.

## Stop Conditions

Stop when:

- NX cannot classify the geometry.
- A sew operation changes scale or deletes major regions.
- A surface operation cannot prove body identity after update.
- The result remains heavily faceted and should be passed to reverse modeling instead.
