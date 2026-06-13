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

The inspection command only imports and audits mesh topology. It does not
execute a solver.

Run the scalar diffusion benchmark with the U5 linear-system layer:

```bash
python -m fromcad2cfd fastcfd unstructured solve-diffusion examples/unstructured/channel2d.msh --manufactured-solution linear --linear-solver sparse-cg --format json
```

This writes `linear_system.json`, `solution.vtu`, `residual_history.csv`,
`qoi.json`, `scalar_diffusion_report.md`, and `diffusion_status.json`. It is a
manufactured scalar benchmark with CSR sparse matrix metadata, not an
incompressible-flow solver.

Run the manufactured Stokes momentum benchmark:

```bash
python -m fromcad2cfd fastcfd unstructured solve-stokes examples/unstructured/channel2d.msh --manufactured-solution linear_divergence_free --pressure-gradient 0.25,-0.75 --linear-solver sparse-cg --format json
```

This writes `stokes_linear_systems.json`, `stokes_residual_history.csv`,
`stokes_qoi.json`, `stokes_solution.vtu`, `stokes_report.md`, and
`stokes_status.json`. It validates pressure-gradient momentum forcing and
divergence metrics on a manufactured benchmark; it is not a full pressure-solve
or Navier-Stokes route.

Run the manufactured pressure-projection benchmark:

```bash
python -m fromcad2cfd fastcfd unstructured solve-projection examples/unstructured/unit_square_4x4.msh --manufactured-solution quadratic_correction --correction-strength 1.0 --linear-solver sparse-cg --format json
```

This writes `projection_linear_system.json`, `projection_residual_history.csv`,
`projection_qoi.json`, `projection_solution.vtu`, `projection_report.md`, and
`projection_status.json`. It is a pressure-correction benchmark with
before/after divergence evidence, not a production pressure solver.

Run the current agent-facing iterative flow benchmark:

```bash
python -m fromcad2cfd fastcfd unstructured solve-flow-benchmark examples/unstructured/unit_square_4x4.msh --iterations 5 --linear-solver sparse-cg --format json
```

This writes `flow_boundary_contract.json`, `flow_residual_history.csv`,
`flow_qoi.json`, `flow_solution.vtu`, `flow_report.md`, and
`flow_status.json`. It is the current U8-U11 benchmark loop and validates
mass-balance reduction evidence, not production CFD behavior.

Run the boundary-aware Poiseuille channel validation:

```bash
python -m fromcad2cfd fastcfd unstructured solve-channel-validation examples/unstructured/unit_square_4x4.msh --pressure-drop 1.0 --linear-solver sparse-cg --format json
```

This writes `channel_boundary_contract.json`, `channel_linear_systems.json`,
`channel_residual_history.csv`, `channel_qoi.json`, `channel_solution.vtu`,
`channel_report.md`, and `channel_status.json`. It validates a controlled
laminar channel profile and records outlet pressure-reference evidence; it is
not a general Navier-Stokes solver.

Run the generated-mesh convergence evidence gate:

```bash
python -m fromcad2cfd fastcfd unstructured solve-channel-convergence --mesh-levels 2,4,8 --format json
```

This generates public-safe synthetic unit-square channel meshes in the selected
output directory and writes `channel_convergence.json`,
`channel_convergence_report.md`, and per-level validation artifacts.

Run the public body-fitted obstacle-channel evidence gate:

```bash
python -m fromcad2cfd fastcfd unstructured solve-obstacle-channel --format json
```

If no mesh file is provided, this generates a synthetic rectangular
obstacle-channel mesh in the output directory. It preserves `inlet`, `outlet`,
`wall`, `obstacle_wall`, and `fluid` zones and writes `obstacle_qoi.json`,
`obstacle_report.md`, and `obstacle_status.json`.

Run the VOF-lite bounded alpha-transport benchmark:

```bash
python -m fromcad2cfd fastcfd unstructured solve-vof-lite --steps 20 --time-step-s 0.02 --velocity 0.1,0.0 --format json
```

This writes `vof_lite_history.csv`, `vof_lite_qoi.json`,
`vof_lite_alpha.vtu`, `vof_lite_report.md`, and `vof_lite_status.json`. It is
a bounded scalar transport sanity check, not a Fluent VOF solver.
