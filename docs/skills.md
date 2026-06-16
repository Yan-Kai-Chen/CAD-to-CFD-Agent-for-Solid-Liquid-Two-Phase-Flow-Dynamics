# Skill Suite

The framework uses project-local skills to keep CAD automation conservative and repeatable.

## Core Development

- `skills/fromcad2cfd-agent-development`
- `skills/fromcad2cfd-solidworks-safe-edit`
- `skills/fromcad2cfd-nx-safe-edit`

## NX Modeling

- `skills/fromcad2cfd-nx-solid-modeling`
  - Use for primitives, transforms, booleans, flow-domain solids, fillet, chamfer, draft, shell, thicken, revolve, sweep, and loft planning.
- `skills/fromcad2cfd-nx-surface-repair`
  - Use for sheet bodies, surface healing, sew or stitch workflows, localized face repair, offset, thicken, and sheet-to-solid conversion.
- `skills/fromcad2cfd-reverse-modeling`
  - Use for rough imported geometry, STL or faceted input, analytic reconstruction, surface fitting, segmentation, and user-taught reverse-modeling methods.

## CFD Workflow

- `skills/fromcad2cfd-fluent-meshing`
- `skills/fromcad2cfd-fluent-solver`
  - Use for public-safe Fluent Solver plan validation, monitor contracts, PyFluent template generation, and resume guardrails.
- `skills/fromcad2cfd-postprocessing`
  - Use for Fluent monitor parsing, pressure/temperature/species/wall-heat summaries, timestamped video planning, and fluid-load proxy interpretation.

## Runtime Policy

- Keep private CAD models out of the repository.
- Use ignored runtime folders for generated geometry and reports.
- Prefer `.prt` plus `.x_t` for NX geometry outputs.
- Treat STEP as optional unless a workflow explicitly requires it.
