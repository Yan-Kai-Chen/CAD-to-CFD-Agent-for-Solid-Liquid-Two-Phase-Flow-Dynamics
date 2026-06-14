# FastFluent Unstructured Mesh Gateway

The unstructured mesh gateway is the first FastFluent `unstructured_fvm` layer.
It covers mesh import, topology construction, named-zone preservation,
mesh-quality diagnostics, finite-volume geometry operators, VTU preview output,
and a scalar manufactured diffusion benchmark with an explicit linear-system
layer for both 2D triangle and 3D tetra simplex cells, a manufactured Stokes
momentum benchmark, and a manufactured pressure-correction projection
benchmark, a public body-fitted obstacle-channel evidence gate, a VOF-lite
bounded alpha-transport benchmark, a simplified algebraic eddy-viscosity
turbulent-channel benchmark, and a bounded standard k-epsilon turbulent-channel
benchmark, a pressure-corrected k-epsilon benchmark, and a Menter k-omega SST
benchmark, plus a turbulence ladder that compares all four local turbulence
evidence tiers. It now also includes an agent-safe JSON case runner, a
controlled steady incompressible pressure-correction route, a public benchmark
suite, and a public 3D tetra smoke benchmark. It does not run a full production
3D incompressible flow, production VOF, rheology, production turbulence, Fluent,
or GPU solver yet.

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

3D tetra scalar diffusion smoke benchmark:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-tetra-diffusion --output-dir 05_projects\tetra_diffusion_demo\output --format json
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

Simplified algebraic eddy-viscosity turbulent channel:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-turbulent-channel --output-dir 05_projects\turbulent_channel_demo\output --iterations 8 --format json
```

Bounded standard k-epsilon turbulent channel:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-kepsilon-channel --output-dir 05_projects\kepsilon_channel_demo\output --iterations 8 --format json
```

Pressure-corrected k-epsilon channel:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-kepsilon-pressure-channel --output-dir 05_projects\pressure_kepsilon_channel_demo\output --iterations 8 --format json
```

Menter k-omega SST channel:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-sst-channel --output-dir 05_projects\sst_channel_demo\output --iterations 8 --format json
```

Turbulence evidence ladder:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-turbulence-ladder --output-dir 05_projects\turbulence_ladder_demo\output --iterations 8 --format json
```

Agent-safe steady incompressible case JSON:

```powershell
python -m fromcad2cfd fastcfd unstructured write-steady-channel-case --case-file 05_projects\steady_channel_case\input\case.json --mesh-file examples\unstructured\channel2d.msh --format json
python -m fromcad2cfd fastcfd unstructured run-case 05_projects\steady_channel_case\input\case.json --output-dir 05_projects\steady_channel_case\output --format json
```

Direct controlled steady incompressible route:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-steady-incompressible examples\unstructured\channel2d.msh --output-dir 05_projects\steady_incompressible_demo\output --iterations 8 --format json
```

Public benchmark suite:

```powershell
python -m fromcad2cfd fastcfd unstructured run-benchmark-suite --output-dir 05_projects\unstructured_public_suite\output --iterations 8 --format json
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
--density <turbulent-channel density>
--molecular-viscosity <turbulent-channel molecular viscosity>
--pressure-drop <turbulent-channel pressure drop>
--kappa <mixing-length von Karman constant>
--max-mixing-length-fraction <channel-height fraction>
--turbulent-viscosity-cap-ratio <mu_t / mu cap>
--c-mu <k-epsilon C_mu>
--c-epsilon-1 <k-epsilon C_epsilon_1>
--c-epsilon-2 <k-epsilon C_epsilon_2>
--sigma-k <k diffusion turbulent Prandtl number>
--sigma-epsilon <epsilon diffusion turbulent Prandtl number>
--turbulence-intensity <k-epsilon inlet intensity>
--turbulent-length-scale-fraction <k-epsilon length scale fraction>
--pressure-relaxation <pressure-correction under-relaxation>
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
- `unit_cube_tetra.msh`: generated public 3D tetra mesh when
  `solve-tetra-diffusion` is run without an input mesh.
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
- `turbulent_boundary_contract.json`: named `inlet`, `outlet`, and `wall`
  contract for the simplified turbulent-channel benchmark.
- `turbulent_channel_qoi.json`: closure settings, Reynolds number,
  turbulent-viscosity ratio, effective-viscosity range, solver residuals,
  velocity-update metrics, acceptance flags, and Fluent turbulence hints.
- `turbulent_channel_iterations.csv`: effective-viscosity and velocity-update
  history for the algebraic eddy-viscosity iteration.
- `turbulent_channel_solution.vtu`: velocity vector plus
  `turbulent_viscosity_ratio` and `effective_viscosity` preview fields.
- `turbulent_channel_report.md`: human-readable turbulent-channel summary.
- `turbulent_channel_status.json`: agent result envelope for the turbulent
  benchmark.
- `kepsilon_boundary_contract.json`: named `inlet`, `outlet`, and `wall`
  contract for the bounded standard k-epsilon benchmark.
- `kepsilon_qoi.json`: closure constants, Reynolds number, k and epsilon
  positivity checks, production, `mu_t / mu`, linear residuals, update metrics,
  acceptance flags, and Fluent turbulence hints.
- `kepsilon_iterations.csv`: velocity, k, epsilon, effective-viscosity,
  production, and residual history for the two-equation iteration.
- `kepsilon_solution.vtu`: velocity plus k, epsilon,
  `turbulent_viscosity_ratio`, `effective_viscosity`, and production preview
  fields.
- `kepsilon_report.md`: human-readable standard k-epsilon benchmark summary.
- `kepsilon_status.json`: agent result envelope for the k-epsilon benchmark.
- `pressure_kepsilon_boundary_contract.json`: inlet velocity, outlet pressure
  reference, and wall no-slip contract for the pressure-corrected k-epsilon
  benchmark.
- `pressure_kepsilon_qoi.json`: pressure-correction residuals, divergence
  monitors, k and epsilon positivity, production, `mu_t / mu`, update metrics,
  acceptance flags, and Fluent pressure-velocity/turbulence hints.
- `pressure_kepsilon_iterations.csv`: predicted and corrected divergence,
  pressure residuals, velocity updates, k and epsilon updates, and eddy-viscosity
  history.
- `pressure_kepsilon_solution.vtu`: velocity plus pressure correction, k,
  epsilon, `turbulent_viscosity_ratio`, `effective_viscosity`, and production
  preview fields.
- `pressure_kepsilon_report.md`: human-readable pressure-corrected k-epsilon
  summary.
- `pressure_kepsilon_status.json`: agent result envelope for the
  pressure-corrected k-epsilon benchmark.
- `sst_boundary_contract.json`: named `inlet`, `outlet`, and `wall` contract
  for the bounded Menter k-omega SST benchmark.
- `sst_qoi.json`: SST constants, Reynolds number, k and omega positivity
  checks, production, F1/F2 blending metrics, `mu_t / mu`, residuals, update
  metrics, acceptance flags, and Fluent SST hints.
- `sst_iterations.csv`: velocity, k, omega, effective-viscosity, production,
  blending-function, and residual history for the SST iteration.
- `sst_solution.vtu`: velocity plus k, omega, `turbulent_viscosity_ratio`,
  `effective_viscosity`, production, F1, and F2 preview fields.
- `sst_report.md`: human-readable Menter k-omega SST benchmark summary.
- `sst_status.json`: agent result envelope for the SST benchmark.
- `turbulence_ladder_qoi.json`: per-tier status, QoI summary, key turbulence
  metrics, recommended strongest passed tier, and explicit benchmark boundary.
- `turbulence_ladder_report.md`: human-readable turbulence ladder summary.
- `turbulence_ladder_status.json`: agent result envelope for the ladder.

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

## U4 Scalar Diffusion, U5 Linear System, And U30 Tetra Smoke

The scalar diffusion gate solves a small manufactured benchmark after the mesh
quality and FV-geometry gates pass. It supports P1 triangle and tetra simplex
cells with exact Dirichlet values on all boundary nodes.

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

U30 adds a public 3D tetra smoke benchmark:

- generates a synthetic unit cube with six named surface patches
  `xmin/xmax/ymin/ymax/zmin/zmax`,
- preserves a `fluid` volume region,
- uses twelve tetrahedra connected to one interior node,
- runs the linear manufactured diffusion solve through the same CSR layer,
- writes mesh/FV-geometry/QoI/VTU artifacts for 3D topology checks.

This U30 gate proves that the backend can import, validate, and assemble a
small 3D tetra scalar problem. It is not a 3D production Navier-Stokes, VOF,
turbulence, Fluent, or GPU solver.

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

## U21 Algebraic Eddy-Viscosity Turbulent Channel

U21 adds a deliberately bounded turbulence solve to avoid leaving turbulence as
only a setup passport. The command generates a public-safe unit channel mesh
when no mesh file is supplied, validates named `inlet`, `outlet`, and `wall`
patches, and solves a pressure-driven channel with a Prandtl mixing-length
zero-equation eddy-viscosity closure:

- initialize a laminar pressure-driven channel profile,
- estimate velocity gradients on triangular cells,
- compute mixing length from the nearest wall distance,
- compute and cap `mu_t`,
- solve the variable-effective-viscosity momentum system,
- under-relax velocity and effective viscosity,
- record iteration history and acceptance metrics.

Acceptance evidence includes:

- final linear system convergence,
- nonzero turbulent-viscosity activation,
- no-slip wall preservation,
- settled velocity update,
- Reynolds number and turbulent-viscosity ratio in the QoI artifact,
- VTU output with velocity, effective viscosity, and turbulent-viscosity ratio.

This is a real iterative turbulence-closure benchmark, but it is intentionally
not a production RANS route. It is not k-epsilon, SST, DES, LES, wall-function
validation, or Fluent replacement. Its purpose is to give the agent a
reproducible local turbulence evidence gate before later Fluent setup and
validation work.

## U22 Standard k-epsilon Two-Equation Channel

U22 adds a stronger bounded turbulence route than U21. The command validates the
same public-safe channel mesh and named boundary patches, then solves:

- streamwise momentum with an effective viscosity,
- k transport with production and epsilon sink terms,
- epsilon transport with standard k-epsilon source and sink coefficients,
- eddy viscosity from `mu_t = rho * C_mu * k^2 / epsilon`.

The default closure constants are:

- `C_mu = 0.09`
- `C_epsilon_1 = 1.44`
- `C_epsilon_2 = 1.92`
- `sigma_k = 1.0`
- `sigma_epsilon = 1.3`

Acceptance evidence includes:

- final momentum, k, and epsilon linear-system convergence,
- positive k and epsilon fields,
- positive turbulence production,
- eddy viscosity above the molecular viscosity level,
- no-slip wall preservation,
- velocity, k, and epsilon update settling,
- VTU output with velocity, k, epsilon, production, effective viscosity, and
  turbulent-viscosity ratio fields.

This is a real two-equation k-epsilon benchmark gate. It is still bounded:
there is no production SIMPLE/PISO pressure-velocity coupling, no SST blending,
no DES/LES, no validated wall functions, no arbitrary engineering geometry
claim, and no Fluent replacement claim. Its role is to give the agent stronger
local turbulence evidence before deciding how to set up and validate Fluent.

## U23 Pressure-Corrected k-epsilon Channel

U23 adds the first pressure-velocity-coupled turbulence benchmark in the public
FastFluent stack. It uses the U22 k-epsilon transport loop and adds a bounded
pressure-correction monitor:

- solve streamwise momentum prediction with effective viscosity,
- compute cell divergence of the predicted velocity,
- solve a pressure-correction Poisson system,
- correct the velocity field and reapply inlet and wall constraints,
- solve k transport,
- solve epsilon transport,
- update eddy viscosity,
- record predicted and corrected divergence at every outer iteration.

The boundary contract differs from U22:

- `inlet`: velocity profile,
- `outlet`: pressure reference,
- `wall`: no-slip wall.

Acceptance evidence includes:

- momentum, pressure-correction, k, and epsilon linear-system convergence,
- positive finite k and epsilon fields,
- eddy viscosity above the molecular viscosity level,
- positive turbulence production,
- no-slip wall preservation,
- velocity, k, and epsilon update settling,
- final pressure-correction step reduces the predicted divergence,
- divergence monitor history is written.

This is the strongest local pressure-velocity-coupled turbulence benchmark in
the project. It is still not a production SIMPLE/PISO solver: divergence
metrics are benchmark monitors, not proof of global production continuity
convergence, and no Fluent, SST, DES, LES, wall-function, arbitrary-geometry, or
production-validation claim is made.

## U24 Turbulence Evidence Ladder

U24 adds an agent-facing evidence comparison layer. U25 extends the same ladder
with the SST benchmark. It runs these tiers on one shared public channel mesh:

1. algebraic eddy viscosity,
2. standard k-epsilon,
3. pressure-corrected k-epsilon,
4. Menter k-omega SST.

The ladder writes a compact summary with per-tier status, closure model, key
QoI metrics, and a recommended strongest passed tier. It is intended for agent
decision support before Fluent setup. The recommendation separates model
strength from validation: SST is the strongest local turbulence-closure tier
when it passes, while pressure-corrected k-epsilon remains the strongest
pressure-velocity-coupling evidence. The ladder does not promote local benchmark
evidence to production CFD validation.

## U25 Menter k-omega SST Channel

U25 adds a bounded near-wall-oriented RANS benchmark using the standard Menter
k-omega SST closure constants. The command validates the same public-safe
channel mesh and named boundary patches, then solves:

- streamwise momentum with an effective viscosity,
- k transport with production and SST destruction terms,
- omega transport with production, beta destruction, and cross-diffusion source
  terms,
- SST F1/F2 blending functions,
- SST eddy viscosity with the `a1` limiter.

The default closure constants are:

- `beta_star = 0.09`
- `sigma_k1 = 0.85`
- `sigma_omega1 = 0.5`
- `beta1 = 0.075`
- `sigma_k2 = 1.0`
- `sigma_omega2 = 0.856`
- `beta2 = 0.0828`
- `kappa = 0.41`
- `a1 = 0.31`

Acceptance evidence includes:

- final momentum, k, and omega linear-system convergence,
- positive finite k and omega fields,
- positive turbulence production,
- eddy viscosity above the molecular viscosity level,
- no-slip wall preservation,
- velocity, k, and omega update settling,
- F1/F2 blending-function metrics,
- VTU output with velocity, k, omega, production, effective viscosity,
  turbulent-viscosity ratio, F1, and F2 fields.

This is a real SST benchmark gate. It is still bounded: there is no production
arbitrary-geometry RANS solver, no DES/LES, no validated wall-function route,
and no Fluent replacement claim. Its role is to make the agent's local
turbulence-closure evidence stronger before deciding whether and how to set up
high-fidelity Fluent validation.

## U26 JSON Unstructured Case Runner

U26 adds the first agent-facing unstructured case file. A case JSON contains:

- `mesh_file`,
- `required_patches`,
- `physics` with density, viscosity, model, and body force,
- `boundary_conditions`,
- `solver` controls.

The runner writes `normalized_case.json`, dispatches only implemented solver
families, preserves the lower-level solver artifacts, and writes
`case_status.json`. Unsupported solver families fail closed before solver
execution.

## U27 Boundary-Condition Schema

U27 broadens the boundary-condition contract beyond the older benchmark labels.
The parser and validator now recognize:

- `velocity_inlet`,
- `velocity_dirichlet`,
- `pressure_outlet`,
- `pressure_reference`,
- `mass_flow_inlet`,
- `opening`,
- `outflow`,
- `no_slip_wall`,
- `symmetry`.

The contract validates required parameters such as inlet velocity, mass-flow
rate, optional opening pressure, and optional symmetry normals. Solver routes
still declare their own implemented subset. If a case uses a boundary kind that
the selected solver does not implement, execution fails closed.

## U28 Controlled Steady Incompressible Case

U28 adds a controlled steady incompressible pressure-correction route for public
unstructured cases:

- solve u and v velocity-component systems,
- anchor pressure correction on pressure outlet/reference patches only,
- use natural pressure-correction handling on other boundaries,
- reapply velocity Dirichlet constraints after correction,
- write divergence history, boundary mass-flux diagnostics, VTU preview, JSON
  QoI, and Markdown report.

The accepted public channel smoke has a mass-flux relative imbalance below 0.1
and reduces the divergence metric from its initial value. This is a controlled
solver route, not a production arbitrary-geometry SIMPLE/PISO implementation.

## U29 Public Benchmark Suite

U29 adds a public suite that runs the current reusable non-private evidence set:

1. Poiseuille channel validation,
2. JSON steady incompressible case,
3. body-fitted obstacle-channel evidence,
4. VOF-lite alpha transport,
5. turbulence ladder.

The suite writes `benchmark_suite_summary.json`,
`benchmark_suite_report.md`, and `benchmark_suite_status.json`. It is designed
as a public CI-style evidence bundle for the agent. It does not include private
device geometry or Fluent case/data files.
