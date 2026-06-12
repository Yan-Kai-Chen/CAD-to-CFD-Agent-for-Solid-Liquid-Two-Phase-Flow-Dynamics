# NX Curve and Surface Operation Map

Use this map to choose the next controlled NXOpen operation families for FromCAD2CFD surface repair and reverse modeling. Treat every new operation as untrusted until it passes a synthetic smoke test and writes JSON/Markdown reports.

## Source Strategy

- Prefer local NX journal recording and NXOpen introspection over web snippets.
- Use Siemens NXOpen training and documentation pages only as navigation aids for API families.
- Convert any web-derived idea into a local probe before adding it to an agent-facing tool.

## Priority 1: Inspection and Sheet Closure

Operations:

- Inspect bodies, faces, edges, sheet/solid/convergent/facet state.
- Sew or stitch selected sheet bodies.
- Detect remaining sheet bodies after sew.
- Detect open boundaries when the NXOpen API exposes them reliably.

Controlled implementation status:

- `inspect_model.py` is implemented.
- `sew_sheet_bodies.py` is implemented for explicit 1-based sheet body selectors.

## Priority 2: Offset, Extract, and Thicken

Operations:

- Extract one face or a selected face set into sheet bodies.
- Offset sheets or faces.
- Thicken sheets into solids.
- Preserve source bodies unless the job explicitly requests deletion.

Controlled implementation status:

- `thicken_face.py` is implemented for extract-face-then-thicken.
- Direct thicken on a solid face is not the default path because local NX 12 probing failed with `Cannot apply Thicken`.

## Priority 3: Curve Creation and Derived Curves

Operations to probe next:

- Create line, arc, circle, and spline curves.
- Create intersection curves from faces and datum planes.
- Project curves onto faces.
- Extract isoparametric or section curves from faces.
- Bridge or connect curves for reverse-modeling profiles.

Controlled implementation status:

- `create_curve_surface_demo.py` is implemented for line, full-circle arc, and ellipse creation.
- Spline creation is not implemented yet.

Acceptance requirements:

- Curves must be named or selected through deterministic selectors.
- Reports must record curve count, endpoints when available, and source face/body selectors.
- Curves used for downstream surfaces must be exported or saved in `.prt`.

## Priority 4: Surface Generation

Operations to probe next:

- Through curves.
- Through curve mesh.
- Swept surface.
- Ruled surface.
- Bounded plane.
- Fill surface or patch-like replacement surface.

Controlled implementation status:

- `create_curve_surface_demo.py` is implemented for a bounded plane from four closed line curves.
- Through curves and through curve mesh are not implemented yet.

Acceptance requirements:

- Input curves must be uniquely selected.
- Resulting body type must be sheet unless a solid is explicitly requested.
- Deviation or continuity assumptions must be recorded when replacing imported rough surfaces.

## Priority 5: Surface Editing and Local Repair

Operations to probe after basic surface generation:

- Trim and untrim surfaces.
- Replace face.
- Extend sheet.
- Split face.
- Delete face with heal when available.
- Simplify or merge faces only after inspection proves the operation preserves important CFD boundaries.

Acceptance requirements:

- Never run global smoothing blindly.
- Record affected face selectors and post-repair body count.
- Stop if the operation changes scale, removes ribs/holes/interfaces, or leaves non-manifold geometry.

## Priority 6: Reverse Modeling for Faceted Imports

Operations:

- Section a faceted or convergent body.
- Fit analytic primitives or spline profiles from section curves.
- Rebuild cylinders, planes, ribs, fillets, and ruled surfaces as clean B-Rep.
- Use boolean reconstruction for fluid-domain-ready solids.

Acceptance requirements:

- Record source facet body, fitted primitives, and deviation tolerance.
- Keep the faceted source as an ignored runtime artifact unless the user explicitly asks to retain it.
- Prefer `.prt` and `.x_t` outputs for downstream CFD handoff.
