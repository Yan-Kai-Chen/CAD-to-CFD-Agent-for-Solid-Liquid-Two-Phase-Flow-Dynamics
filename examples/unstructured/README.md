# Public-Safe Unstructured Mesh Examples

This folder contains minimal meshes for testing the FastFluent unstructured mesh
gateway. These files are synthetic and do not contain private device geometry.

Run:

```bash
python -m fromcad2cfd fastcfd unstructured inspect-mesh examples/unstructured/channel2d.msh --format json
```

The command writes:

- `mesh_manifest.json`
- `mesh_quality.json`
- `mesh.vtu`
- `unstructured_mesh_report.md`
- `inspection_status.json`

The current gate only imports and audits mesh topology. It does not execute a
flow solver.

Run the scalar diffusion benchmark:

```bash
python -m fromcad2cfd fastcfd unstructured solve-diffusion examples/unstructured/channel2d.msh --manufactured-solution linear --format json
```

This writes `solution.vtu`, `residual_history.csv`, `qoi.json`,
`scalar_diffusion_report.md`, and `diffusion_status.json`. It is a manufactured
scalar benchmark, not an incompressible-flow solver.
