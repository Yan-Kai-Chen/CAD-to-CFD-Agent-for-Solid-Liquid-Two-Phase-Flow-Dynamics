# FastFluent Unstructured Mesh Gateway

The unstructured mesh gateway is the first FastFluent `unstructured_fvm` layer.
It covers mesh import, topology construction, named-zone preservation,
mesh-quality diagnostics, finite-volume geometry operators, VTU preview output,
and a scalar manufactured diffusion benchmark. It does not run an
incompressible flow, VOF, rheology, turbulence, Fluent, or GPU solver yet.

## Why This Exists

The structured LBM backend remains useful for bounded pilot cases. Real CAD
geometry, however, needs boundary patches, named zones, and body-fitted mesh
inspection before Fluent setup. The unstructured route is therefore a separate
finite-volume backend scaffold rather than a renamed structured lattice.

## Current Command

```bash
python -m fromcad2cfd fastcfd unstructured inspect-mesh examples/unstructured/channel2d.msh --format json
```

Scalar diffusion benchmark:

```bash
python -m fromcad2cfd fastcfd unstructured solve-diffusion examples/unstructured/channel2d.msh --manufactured-solution linear --format json
```

Optional arguments:

```bash
--output-dir <dir>
--required-patches inlet,outlet,wall
--no-write-vtu
```

## Outputs

- `mesh_manifest.json`: mesh source, format, topology counts, physical names,
  cell types, boundary zones, and region zones.
- `mesh_quality.json`: pass/fail checks, blocking errors, patch coverage,
  positive area/volume checks, orphan boundary checks, nonmanifold checks, and
  lightweight quality proxies.
- `mesh.vtu`: unstructured-grid preview for visualization.
- `fv_geometry.json`: finite-volume cell/face geometry, owner-neighbour face
  topology, owner-oriented area vectors, cell measures, boundary patch maps, and
  non-orthogonality proxies.
- `qoi.json`: scalar diffusion error metrics and residual metrics when the
  `solve-diffusion` gate is used.
- `residual_history.csv`: direct-solve residual before and after solution.
- `solution.vtu`: scalar solution, exact value, and error fields.
- `unstructured_mesh_report.md`: human-readable inspection summary.
- `inspection_status.json`: agent result envelope.

## Gate Rules

The gateway fails closed when:

- required patches are missing,
- region names are missing,
- cell signed area/volume is non-positive,
- boundary faces are ungrouped,
- boundary elements do not match cell boundary faces,
- nonmanifold faces are detected.

Failure means no solver execution. Later unstructured diffusion, laminar flow,
rheology, and VOF-lite gates must build on this mesh-quality artifact instead
of bypassing it.

## U3 Geometry Operators

When `mesh_quality.json` passes, the gateway writes `fv_geometry.json`. This
artifact is the handoff point for later scalar diffusion and laminar-flow gates.
It contains:

- positive cell measures,
- cell centers,
- face centers,
- owner-neighbour connectivity,
- owner-oriented area vectors,
- boundary patch to face-index mapping,
- lightweight non-orthogonality estimates.

The Python API also includes a node-based scalar gradient reconstruction helper
for manufactured-solution tests. It is used only as an operator validation tool
at this stage and is not yet the final cell-centered FVM gradient scheme.

## U4 Scalar Diffusion

The scalar diffusion gate solves a small manufactured benchmark after the mesh
quality and FV-geometry gates pass. It currently supports 2D triangular meshes
with exact Dirichlet values on all boundary nodes.

Supported manufactured solutions:

- `linear`: exact linear scalar field, zero source, expected near machine-zero
  error.
- `quadratic_bubble`: smooth bubble field with source term, used for
  mesh-refinement error checks.

The U4 gate writes `solution.vtu`, `residual_history.csv`, `qoi.json`,
`scalar_diffusion_report.md`, and `diffusion_status.json`.

This is the first PDE gate for the unstructured backend, but it is still not a
flow solver. Later incompressible-flow gates must keep their own mass-balance,
pressure-velocity coupling, and benchmark acceptance tests.
