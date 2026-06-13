# FastFluent Unstructured Mesh Gateway

The unstructured mesh gateway is the first FastFluent `unstructured_fvm` layer.
It covers mesh import, topology construction, named-zone preservation,
mesh-quality diagnostics, finite-volume geometry operators, VTU preview output,
and a scalar manufactured diffusion benchmark with an explicit linear-system
layer, a manufactured Stokes momentum benchmark, and a manufactured
pressure-correction projection benchmark, a public body-fitted
obstacle-channel evidence gate, and a VOF-lite bounded alpha-transport
benchmark. It does not run a full production incompressible flow, VOF,
rheology, turbulence, Fluent, or GPU solver yet.

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

Stokes momentum benchmark:

```bash
python -m fromcad2cfd fastcfd unstructured solve-stokes examples/unstructured/channel2d.msh --manufactured-solution linear_divergence_free --pressure-gradient 0.25,-0.75 --format json
```

Pressure-correction projection benchmark:

```bash
python -m fromcad2cfd fastcfd unstructured solve-projection examples/unstructured/unit_square_4x4.msh --manufactured-solution quadratic_correction --correction-strength 1.0 --format json
```

Agent-facing iterative flow benchmark:

```bash
python -m fromcad2cfd fastcfd unstructured solve-flow-benchmark examples/unstructured/unit_square_4x4.msh --iterations 5 --linear-solver sparse-cg --format json
```

Boundary-aware channel validation:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-channel-validation examples/unstructured/unit_square_4x4.msh --pressure-drop 1.0 --linear-solver sparse-cg --format json
```

Channel convergence evidence with generated public-safe meshes:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-channel-convergence --mesh-levels 2,4,8 --format json
```

Public body-fitted obstacle-channel evidence:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-obstacle-channel --output-dir 05_projects\obstacle_channel_demo\output --format json
```

VOF-lite bounded alpha transport:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-vof-lite --output-dir 05_projects\vof_lite_demo\output --steps 20 --time-step-s 0.02 --velocity 0.1,0.0 --format json
```

Optional arguments:

```bash
--output-dir <dir>
--required-patches inlet,outlet,wall
--linear-solver sparse-cg
--linear-tolerance 1e-12
--max-linear-iterations <count>
--pressure-gradient dpdx,dpdy
--correction-strength <value>
--iterations <count>
--relaxation <value>
--nx <generated obstacle-channel cells in x>
--ny <generated obstacle-channel cells in y>
--time-step-s <VOF-lite time step>
--velocity ux,uy
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
- `linear_system.json`: U5 CSR matrix and solver metadata for scalar diffusion
  benchmark runs.
- `qoi.json`: scalar diffusion error metrics and residual metrics when the
  `solve-diffusion` gate is used.
- `residual_history.csv`: linear-solver residual trace.
- `solution.vtu`: scalar solution, exact value, and error fields.
- `stokes_qoi.json`: U6 manufactured Stokes velocity, divergence, pressure
  gradient, and residual metrics.
- `stokes_linear_systems.json`: U6 CSR matrix and solver metadata for the `u`
  and `v` momentum components.
- `stokes_solution.vtu`: velocity, exact velocity, velocity error, and
  manufactured pressure fields.
- `projection_qoi.json`: U7 pressure-correction, predicted divergence,
  corrected divergence, and velocity-error metrics.
- `projection_linear_system.json`: U7 pressure-correction Poisson matrix and
  solver metadata.
- `projection_residual_history.csv`: U7 pressure-correction linear-solver
  residual trace.
- `projection_solution.vtu`: corrected velocity, target velocity, velocity
  error, and pressure-correction fields.
- `projection_report.md`: U7 human-readable projection summary.
- `projection_status.json`: U7 agent result envelope.
- `flow_boundary_contract.json`: U9 named-patch and boundary-condition contract.
- `flow_residual_history.csv`: U8 iterative projection history with divergence,
  pressure residual, and velocity-update metrics.
- `flow_qoi.json`: U10 agent-facing benchmark QoI summary.
- `flow_solution.vtu`: final benchmark velocity, target velocity, velocity
  error, and last pressure-correction field.
- `flow_report.md`: U10 human-readable benchmark summary.
- `flow_status.json`: U10 agent result envelope.
- `unstructured_mesh_report.md`: human-readable inspection summary.
- `inspection_status.json`: agent result envelope.
- `obstacle_boundary_contract.json`: named boundary-condition contract for
  `inlet`, `outlet`, `wall`, and `obstacle_wall`.
- `obstacle_qoi.json`: public synthetic body-fitted obstacle-channel metrics,
  blockage ratio, clearance metrics, zone evidence, and Fluent setup hints.
- `obstacle_report.md`: human-readable obstacle-channel evidence summary.
- `obstacle_status.json`: agent result envelope for the obstacle evidence gate.
- `vof_lite_history.csv`: alpha mass, alpha bounds, boundary flux, and clipping
  trace for each VOF-lite transport step.
- `vof_lite_qoi.json`: bounded alpha transport metrics, CFL, phase-volume
  balance, acceptance flags, and Fluent VOF monitor hints.
- `vof_lite_alpha.vtu`: final alpha preview field.
- `vof_lite_report.md`: human-readable VOF-lite summary.
- `vof_lite_status.json`: agent result envelope for the VOF-lite gate.

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

## U4 Scalar Diffusion And U5 Linear System

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

U5 adds the explicit linear-system layer used by the scalar diffusion gate:

- dependency-free CSR sparse matrix storage,
- matrix-vector product,
- dense direct solver for reference checks,
- sparse conjugate-gradient solver for the default controlled route,
- residual convergence metadata,
- `linear_system.json` artifact.

The default CLI route uses `--linear-solver sparse-cg`. `--linear-solver
dense-direct` is kept as a small-reference path for tests and diagnostics.

This is the first PDE gate for the unstructured backend, but it is still not a
flow solver. Later incompressible-flow gates must keep their own mass-balance,
pressure-velocity coupling, and benchmark acceptance tests.

## U6 Manufactured Stokes Momentum

U6 adds a minimal momentum-equation benchmark on top of the U5 linear-system
layer. It solves two velocity-component systems with exact velocity Dirichlet
values and a known manufactured pressure gradient.

Supported manufactured solutions:

- `linear_divergence_free`: exact linear divergence-free velocity field with a
  linear manufactured pressure field. This should be near machine-zero error on
  the synthetic channel mesh.
- `pressure_driven_shear`: quadratic shear velocity with a pressure-gradient
  source term, used for refinement-sensitive velocity-error checks.

The U6 command writes `stokes_qoi.json`, `stokes_linear_systems.json`,
`stokes_residual_history.csv`, `stokes_solution.vtu`, `stokes_report.md`, and
`stokes_status.json`.

U6 does not solve pressure from a pressure-Poisson equation yet. Pressure is a
manufactured source field used to verify that pressure-gradient forcing can enter
the momentum benchmark route before a later projection or SIMPLE-like gate is
implemented.

## U7 Manufactured Pressure Projection

U7 adds the first pressure-correction benchmark. It creates a manufactured
predicted velocity with nonzero divergence, solves a pressure-correction Poisson
system, applies a velocity correction, and reports before/after divergence.

Supported manufactured solutions:

- `quadratic_correction`: quadratic pressure correction with nonzero Poisson
  source. This is the main divergence-reduction benchmark.
- `linear_correction`: linear correction with zero Poisson source, kept for
  small diagnostic checks.

The U7 command writes `projection_qoi.json`, `projection_linear_system.json`,
`projection_residual_history.csv`, `projection_solution.vtu`,
`projection_report.md`, and `projection_status.json`.

This is still a benchmark gate. The pressure correction uses exact Dirichlet
values and recovered nodal gradients. A production projection method or
SIMPLE/PISO-like solver still needs real pressure boundary-condition handling,
time stepping or pseudo-time iteration, and stronger mass-balance acceptance
tests.

## U8-U11 Iterative Flow Benchmark And Contract

U8-U11 close the current unstructured benchmark loop:

- U8 adds an iterative pressure-correction loop with residual history.
- U9 adds a boundary-condition contract for required named patches and supported
  benchmark boundary kinds.
- U10 exposes a unified agent-facing `solve-flow-benchmark` command.
- U11 updates tests, docs, public-safe examples, and milestone memory.

The flow benchmark starts from a manufactured predicted velocity, repeatedly
solves zero-Dirichlet pressure-correction systems, applies velocity correction,
and records divergence before and after each correction. The accepted evidence is
the residual history and final QoI, not a claim of production CFD validity.

The boundary contract currently supports:

- `inlet`: `velocity_dirichlet`
- `outlet`: `pressure_reference`
- `wall`: `no_slip_wall`

Missing required patches or unsupported boundary-condition kinds block solver
execution before the benchmark loop starts.

## U12-U14 Boundary-Aware Channel Validation And Convergence

U12-U14 turn the unstructured route from a manufactured benchmark loop into a
controlled physical validation case:

- U12 adds a boundary-aware Poiseuille channel kernel with named `inlet`,
  `outlet`, and `wall` patches.
- U13 compares the numerical velocity field against the analytical laminar
  channel profile.
- U14 repeats the same case across coarse, medium, and fine synthetic meshes and
  reports whether the cell-center velocity error decreases with refinement.

The channel boundary contract uses:

- `inlet`: parabolic `velocity_profile_dirichlet`
- `outlet`: `pressure_reference` with recorded analytical pressure gradient
- `wall`: `no_slip_wall`

The single-case command writes:

- `channel_boundary_contract.json`
- `channel_linear_systems.json`
- `channel_residual_history.csv`
- `channel_qoi.json`
- `channel_solution.vtu`
- `channel_report.md`
- `channel_status.json`

The convergence command writes:

- `channel_convergence.json`
- `channel_convergence_report.md`
- `channel_convergence_status.json`
- per-level channel-validation artifacts

Acceptance evidence includes linear solver convergence, velocity-profile error,
cell-divergence metrics, mass-balance flux proxy, monotonic error decrease, and
observed order estimates. The pressure field is still an analytical reference
and source term. This is a validation gate for the unstructured route, not a
general production Navier-Stokes, SIMPLE/PISO, VOF, turbulence, or Fluent
replacement solver.

## U18 Public Obstacle-Channel Evidence

U18 adds a public synthetic body-fitted obstacle-channel evidence case. If no
mesh file is provided, the command generates a rectangular channel with a
rectangular obstacle hole and preserves these physical names:

- `inlet`
- `outlet`
- `wall`
- `obstacle_wall`
- `fluid`

The gate validates mesh quality, named-zone preservation, a boundary-condition
contract, blockage ratio, top and bottom clearance, and VTU preview output. It
is designed as a public example for CAD-to-CFD obstacle boundary handoff and does
not include private device geometry.

## U19 VOF-Lite Alpha Transport

U19 adds a bounded scalar alpha-transport benchmark on top of the unstructured
mesh gateway. It initializes a simple volume-fraction column and advects alpha
with a prescribed velocity field. Acceptance checks include:

- VOF-lite Courant number within the benchmark limit,
- alpha bounded in `[0, 1]`,
- no clipping required,
- phase-volume balance accounting against boundary alpha flux,
- history CSV and final VTU preview output.

This is intentionally named VOF-lite. It is a transport sanity check for agent
decision support, not a Fluent VOF solver and not a replacement for pressure,
momentum, surface-tension, turbulence, or interface-reconstruction physics.
