# FastFluent Mesh Gateway v2

Mesh Gateway v2 is the shared mesh-entry facade for the general FastFluent
evidence layer. It does not replace the existing unstructured backend. It wraps
the mature unstructured mesh inspection route and adds a structured-grid demo
route so future CaseSpec v3 cases can use one mesh vocabulary.

## Current Commands

Inspect a public Gmsh mesh:

```powershell
python -m fromcad2cfd fastcfd mesh inspect examples/unstructured/channel2d.msh --output-dir sandbox/output/mesh_inspect
```

Generate a public structured-grid demo:

```powershell
python -m fromcad2cfd fastcfd mesh generate-structured-demo --output-dir sandbox/output/structured_mesh_demo
```

## Current Outputs

Both routes write a mesh-gateway artifact set:

- `mesh_manifest.json`
- `mesh_quality.json`
- `fv_geometry.json`
- `mesh_quality_report.md`
- `mesh.vtu`

The structured route also writes `mesh_status.json` under the
`mesh_gateway_status` artifact key. The Gmsh route
reuses the existing unstructured inspection status file.

## Design Choice

M3 is an additive facade. It reuses:

- `fromcad2cfd_fastcfd.unstructured.gmsh`
- `fromcad2cfd_fastcfd.unstructured.quality`
- `fromcad2cfd_fastcfd.unstructured.geometry`
- `fromcad2cfd_fastcfd.unstructured.vtu`

New wrapper modules live under `src/fromcad2cfd_fastcfd/mesh/` so future code
can depend on `fastcfd.mesh` without reaching directly into unstructured solver
internals.

## Current Limitations

- Mesh Gateway v2 is a pre-solver gateway and does not run a CFD solver.
- The structured route is a public rectangular smoke demo.
- The Gmsh route currently supports the existing agent-safe Gmsh v4 ASCII
  subset.
- Full production mesh audit, Fluent Meshing, HyperMesh, and volume meshing
  execution remain outside this module.
