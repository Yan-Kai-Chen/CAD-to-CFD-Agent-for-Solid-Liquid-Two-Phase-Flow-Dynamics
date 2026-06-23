# FastCFD Quickstart

FastCFD is the FromCAD2CFD preliminary CFD prediction and physics-screening
layer. It is designed to run cheap, bounded FastFluent-derived tests before
high-fidelity Fluent validation. It is not a Fluent replacement and its reports
must remain evidence-led.

## Capability Inventory

```powershell
python -m fromcad2cfd fastcfd capabilities --format markdown
```

## Source-Of-Truth Registry

The registry is the bounded list of case templates, lattice sets, boundary
types, and collision models that an agent is allowed to use.

```powershell
python -m fromcad2cfd fastcfd registry --format markdown
```

## Unstructured Mesh Gateway

The first `unstructured_fvm` gate imports and audits a public-safe Gmsh v4 ASCII
mesh before any solver execution:

```powershell
python -m fromcad2cfd fastcfd unstructured inspect-mesh examples/unstructured/channel2d.msh --format json
```

It writes `mesh_manifest.json`, `mesh_quality.json`, `fv_geometry.json`,
`mesh.vtu`, `unstructured_mesh_report.md`, and `inspection_status.json`. This
is a mesh and finite-volume geometry gateway only; the unstructured flow solver
is a later gate.

The first PDE gate is a scalar manufactured diffusion benchmark. U5 adds the
controlled linear-system layer behind this command: CSR sparse assembly,
`sparse-cg` as the default solver, and `dense-direct` as a reference route.

```powershell
python -m fromcad2cfd fastcfd unstructured solve-diffusion examples/unstructured/channel2d.msh --manufactured-solution linear --linear-solver sparse-cg --format json
```

It writes `linear_system.json`, `solution.vtu`, `residual_history.csv`,
`qoi.json`, `scalar_diffusion_report.md`, and `diffusion_status.json`.

For a public 3D tetra smoke benchmark, use the generated unit-cube tetra mesh:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-tetra-diffusion --output-dir 05_projects\tetra_diffusion_demo\output --format json
```

This writes `unit_cube_tetra.msh`, `mesh_manifest.json`, `mesh_quality.json`,
`fv_geometry.json`, `linear_system.json`, `solution.vtu`, `qoi.json`, and
`diffusion_status.json`. It validates 3D tetra topology and scalar P1 assembly
only; it is not a 3D Navier-Stokes, VOF, turbulence, Fluent, or GPU solver.

The first momentum benchmark is manufactured Stokes:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-stokes examples/unstructured/channel2d.msh --manufactured-solution linear_divergence_free --pressure-gradient 0.25,-0.75 --linear-solver sparse-cg --format json
```

It writes `stokes_linear_systems.json`, `stokes_residual_history.csv`,
`stokes_qoi.json`, `stokes_solution.vtu`, `stokes_report.md`, and
`stokes_status.json`. Pressure is still a manufactured source field here; this
is not a pressure-Poisson or production Navier-Stokes solver yet.

The first pressure-correction benchmark is manufactured projection:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-projection examples/unstructured/unit_square_4x4.msh --manufactured-solution quadratic_correction --correction-strength 1.0 --linear-solver sparse-cg --format json
```

It writes `projection_linear_system.json`, `projection_residual_history.csv`,
`projection_qoi.json`, `projection_solution.vtu`, `projection_report.md`, and
`projection_status.json`. This reports predicted and corrected divergence, but
still uses manufactured pressure-correction boundary values.

The current agent-facing unstructured benchmark loop is:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-flow-benchmark examples/unstructured/unit_square_4x4.msh --iterations 5 --linear-solver sparse-cg --format json
```

It validates the mesh, boundary-condition contract, iterative pressure
correction, residual history, and final QoI. It writes
`flow_boundary_contract.json`, `flow_residual_history.csv`, `flow_qoi.json`,
`flow_solution.vtu`, `flow_report.md`, and `flow_status.json`.

The first boundary-aware physical validation case is the controlled Poiseuille
channel route:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-channel-validation examples/unstructured/unit_square_4x4.msh --pressure-drop 1.0 --linear-solver sparse-cg --format json
```

It validates named `inlet`, `outlet`, and `wall` patches, applies a parabolic
channel velocity profile, records the outlet pressure reference and analytical
pressure gradient, solves the controlled Stokes channel benchmark, and writes
`channel_boundary_contract.json`, `channel_linear_systems.json`,
`channel_residual_history.csv`, `channel_qoi.json`, `channel_solution.vtu`,
`channel_report.md`, and `channel_status.json`.

For mesh-sensitivity evidence, run the convergence gate. If no mesh files are
provided, it generates public-safe synthetic unit-square channel meshes in the
output directory:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-channel-convergence --mesh-levels 2,4,8 --format json
```

It writes `channel_convergence.json`, `channel_convergence_report.md`, and
per-level channel-validation artifacts. This is the current U14 evidence route
for checking whether the unstructured solver path behaves consistently as mesh
resolution increases.

The simplified turbulent-channel benchmark keeps turbulence solving present in
the local FastFluent stack without claiming a production RANS model:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-turbulent-channel --output-dir 05_projects\turbulent_channel_demo\output --iterations 8 --format json
```

It generates a public-safe channel mesh when no mesh is supplied, validates
`inlet`, `outlet`, and `wall` patches, solves an iterative pressure-driven
channel with a Prandtl mixing-length algebraic eddy-viscosity closure, and
writes `turbulent_channel_qoi.json`, `turbulent_channel_iterations.csv`,
`turbulent_channel_solution.vtu`, `turbulent_channel_report.md`, and
`turbulent_channel_status.json`. This is a zero-equation benchmark for
engineering evidence; it is not k-epsilon, SST, DES, LES, or a Fluent
replacement.

The stronger two-equation turbulence benchmark solves streamwise momentum plus
k and epsilon transport with standard k-epsilon constants:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-kepsilon-channel --output-dir 05_projects\kepsilon_channel_demo\output --iterations 8 --format json
```

It writes `kepsilon_qoi.json`, `kepsilon_iterations.csv`,
`kepsilon_solution.vtu`, `kepsilon_report.md`, and `kepsilon_status.json`.
The QoI includes positive k and epsilon checks, turbulence production,
`mu_t / mu`, residuals for the momentum, k, and epsilon systems, and Fluent
RANS setup hints. This is stronger than the algebraic eddy-viscosity benchmark
because k and epsilon are solved fields, but it is still a bounded benchmark,
not a production SIMPLE/PISO, SST, DES, LES, wall-function validation, or
Fluent replacement.

The pressure-corrected k-epsilon route adds a pressure-correction step inside
the same outer turbulence loop:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-kepsilon-pressure-channel --output-dir 05_projects\pressure_kepsilon_channel_demo\output --iterations 8 --format json
```

It writes `pressure_kepsilon_qoi.json`,
`pressure_kepsilon_iterations.csv`, `pressure_kepsilon_solution.vtu`,
`pressure_kepsilon_report.md`, and `pressure_kepsilon_status.json`. The QoI
records momentum prediction, pressure-correction residuals, divergence monitors,
k and epsilon transport residuals, eddy-viscosity ratios, and Fluent setup
hints. This is the strongest local pressure-velocity-coupled turbulence
evidence in the public stack. It is still bounded and does not claim production
SIMPLE/PISO, Fluent, SST, DES, LES, or wall-function validation.

The bounded Menter k-omega SST route adds a near-wall-oriented two-equation
RANS benchmark with SST blending functions:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-sst-channel --output-dir 05_projects\sst_channel_demo\output --iterations 8 --format json
```

It writes `sst_qoi.json`, `sst_iterations.csv`, `sst_solution.vtu`,
`sst_report.md`, and `sst_status.json`. The QoI records k and omega transport
residuals, SST F1/F2 blending fields, the eddy-viscosity limiter,
positive-field checks, turbulent-viscosity ratios, and Fluent SST setup hints.
This is now the strongest local turbulence-closure evidence in the public
stack. The pressure-corrected k-epsilon route remains the pressure-velocity
coupling evidence. Neither route is a production Fluent replacement.

For agent decision support, the turbulence ladder runs all four local
turbulence tiers on the same public channel mesh:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-turbulence-ladder --output-dir 05_projects\turbulence_ladder_demo\output --iterations 8 --format json
```

It writes `turbulence_ladder_qoi.json`,
`turbulence_ladder_report.md`, and per-tier artifacts under
`01_algebraic_eddy_viscosity`, `02_standard_kepsilon`,
`03_pressure_corrected_kepsilon`, and `04_menter_sst`. The ladder recommends the
strongest passed local evidence tier for later Fluent setup, but it remains a
bounded local evidence comparison rather than production CFD validation.

The agent-safe unstructured case runner is the preferred route when a mesh and
boundary-condition set should be described explicitly:

```powershell
python -m fromcad2cfd fastcfd unstructured write-steady-channel-case --case-file 05_projects\steady_channel_case\input\case.json --mesh-file examples\unstructured\channel2d.msh --format json
python -m fromcad2cfd fastcfd unstructured run-case 05_projects\steady_channel_case\input\case.json --output-dir 05_projects\steady_channel_case\output --format json
```

The direct controlled steady incompressible route is useful for quick public
channel checks with default inlet/outlet/wall boundary conditions:

```powershell
python -m fromcad2cfd fastcfd unstructured solve-steady-incompressible examples\unstructured\channel2d.msh --output-dir 05_projects\steady_incompressible_demo\output --iterations 8 --format json
```

For a one-command public validation sweep:

```powershell
python -m fromcad2cfd fastcfd unstructured run-benchmark-suite --output-dir 05_projects\unstructured_public_suite\output --iterations 8 --format json
```

The suite runs Poiseuille channel validation, the JSON steady incompressible
case route, public obstacle-channel evidence, VOF-lite alpha transport, and the
turbulence ladder. It is public-safe evidence, not production Fluent validation.

## S1 Native Simulation Validation Pack

The S1 pack is the current one-command native simulation validation gate. It
runs public FastFluent/FastCFD-native routes, writes a case-level
`simulation_result.json` contract, collects field outputs, extracts QoIs, and
connects native evidence back to H1-H3.5 passports.

```powershell
python -m fromcad2cfd fastcfd native-simulation-validation-pack-demo --output-dir sandbox/output/fastfluent_native_simulation_validation_pack --format markdown
```

It writes:

- `simulation_manifest.json`
- `simulation_summary.md`
- `limitations.md`
- `structured_cases/*/simulation_result.json`
- `unstructured_cases/*/simulation_result.json`
- `passport_simulation_alignment/*.md`
- backend field outputs such as `*.vtu` and residual/history `*.csv`

The S1 pack does not launch Fluent, call PyFluent, edit Fluent case/data files,
emit raw Fluent TUI, or generate UDF source. Structured C++ cases are recorded
as status-only when that optional backend is not run.

## S2 Practical Native Function Expansion Pack

The S2 pack adds small reusable native computations that are useful even before
Fluent is available: heat diffusion, scalar advection-diffusion, material
property fields, source-term ramp/clamp behavior, parameter sweeps, and a wax
application demo.

```powershell
python -m fromcad2cfd fastcfd practical-native-demo-pack --output-dir sandbox/output/fastfluent_practical_native_demo_pack --format markdown
```

It writes:

- `heat_diffusion_1d/*`
- `heat_diffusion_2d/*`
- `scalar_advection_diffusion_1d/*`
- `bounded_scalar_transport/*`
- `arrhenius_viscosity_field/*`
- `source_term_ramp_clamp/*`
- `practical_parameter_sweep/*`
- `wax_application_demo/*`
- `practical_native_manifest.json`
- `practical_native_summary.md`

S2 validates practical FastFluent-native utilities and artifact generation. It
does not launch Fluent, call PyFluent, edit Fluent case/data files, emit raw
Fluent TUI, generate UDF source, or prove high-fidelity CFD accuracy.

## Wax Rheology / Phase-Change Passport

The wax route turns public material and thermal-property inputs into a bounded
readiness passport for later Fluent review. It estimates Arrhenius viscosity,
softening behavior, thermal time scales, latent-heat energy scale,
phase-change stiffness, material-model recommendations, monitor requirements,
and a non-executing solver-plan patch.

```powershell
python -m fromcad2cfd fastcfd wax-rheology-handoff-demo --output-dir sandbox/output/wax_rheology_phase_change_demo --format markdown
```

It writes:

- `wax_rheology_phase_change_case.json`
- `passport/wax_rheology_phase_change_passport.json`
- `passport/wax_rheology_phase_change_fluent_hints.json`
- `passport/wax_rheology_phase_change_report.md`
- `solver_plan_patch.json`
- `solver_plan_patch_report.md`

This route does not launch Fluent, call PyFluent, edit Fluent case/data files,
emit raw Fluent TUI, generate UDF source, or validate final dewaxing accuracy.

## VOF Physics Passport

The VOF route validates two-phase setup readiness before any Fluent VOF run. It
does not solve VOF transport.

Write a public-safe demo case:

```powershell
python -m fromcad2cfd fastcfd write-vof-demo --output-dir 05_projects\vof_demo\input
```

Validate an existing VOF case:

```powershell
python -m fromcad2cfd fastcfd validate-vof --case-file examples\fastcfd\vof_dambreak2d_passport\vof_case.json --output-dir 05_projects\vof_demo\reports --format json
```

It writes `vof_case.json`, `vof_physics_passport.json`,
`vof_fluent_setup_hints.json`, `vof_report.md`, and `vof_status.json`.

The passport checks phase density and viscosity, volume-fraction closure,
surface tension, gravity, time step, VOF Courant number, Reynolds, Weber, Bond,
Capillary, and Froude numbers. Failed passports block downstream setup hints.

## Turbulence Passport

The turbulence passport validates setup readiness for a first Fluent RANS
setup. It complements the simplified turbulent-channel benchmark above, but it
does not itself solve turbulence.

```powershell
python -m fromcad2cfd fastcfd write-turbulence-demo --output-dir 05_projects\turbulence_demo\input
python -m fromcad2cfd fastcfd validate-turbulence --case-file 05_projects\turbulence_demo\input\turbulence_case.json --output-dir 05_projects\turbulence_demo\reports --format json
```

It writes `turbulence_case.json`, `turbulence_passport.json`,
`turbulence_fluent_setup_hints.json`, `turbulence_report.md`, and
`turbulence_status.json`. The passport checks Reynolds regime, hydraulic
diameter, model intent, turbulence intensity, estimated friction velocity,
first-cell y-plus, and near-wall target compatibility.

## Non-Newtonian Rheology Passport

The rheology route validates a material model over a declared shear-rate range.
It is a material-model benchmark, not a non-Newtonian CFD solver.

```powershell
python -m fromcad2cfd fastcfd write-rheology-demo --output-dir 05_projects\rheology_demo\input
python -m fromcad2cfd fastcfd run-rheology-benchmark --case-file 05_projects\rheology_demo\input\rheology_case.json --output-dir 05_projects\rheology_demo\reports --format json
```

It writes `rheology_case.json`, `rheology_passport.json`,
`rheology_curve.csv`, `rheology_fluent_setup_hints.json`,
`rheology_report.md`, and `rheology_status.json`. Supported setup models are
Newtonian, power-law, and Carreau-Yasuda. The benchmark checks finite positive
apparent viscosity, shear stress, viscosity ratio, and shear-thinning or
shear-thickening trend.

## Public Obstacle-Channel Evidence

The obstacle-channel route generates or inspects a public synthetic
body-fitted triangular channel mesh with `obstacle_wall` preserved as a named
patch. It is safe for public examples because it does not contain private
device geometry.

```powershell
python -m fromcad2cfd fastcfd unstructured solve-obstacle-channel --output-dir 05_projects\obstacle_channel_demo\output --format json
```

It writes `public_obstacle_channel.msh` when no mesh is provided,
`mesh_manifest.json`, `mesh_quality.json`,
`obstacle_boundary_contract.json`, `fv_geometry.json`, `mesh.vtu`,
`obstacle_qoi.json`, `obstacle_report.md`, and `obstacle_status.json`.

## VOF-Lite Alpha Transport

VOF-lite is a bounded scalar alpha-transport benchmark on an unstructured mesh.
It checks CFL, boundedness, and phase-volume accounting before a later Fluent
VOF setup. It does not solve pressure, momentum, surface tension, turbulence, or
interface reconstruction.

```powershell
python -m fromcad2cfd fastcfd unstructured solve-vof-lite --output-dir 05_projects\vof_lite_demo\output --steps 20 --time-step-s 0.02 --velocity 0.1,0.0 --format json
```

It writes `vof_lite_history.csv`, `vof_lite_qoi.json`,
`vof_lite_alpha.vtu`, `vof_lite_report.md`, and `vof_lite_status.json`.

## Evidence-Checked Fluent Hint Compiler

The hint compiler aggregates setup hints from validated evidence artifacts only.
Every compiled hint must carry explicit evidence and a source artifact path.
Missing evidence fails closed.

```powershell
python -m fromcad2cfd fastcfd compile-fluent-hints --evidence-files <vof_hints.json>,<turbulence_hints.json>,<rheology_hints.json> --output-dir 05_projects\fluent_hints_demo\reports --format json
```

It writes `fluent_setup_hints.json`,
`fluent_setup_hints_report.md`, and `fluent_setup_hints_status.json`. It does
not execute Fluent or edit Fluent case files.

## Existing Passport To Solver-Plan Patch Compiler

The patch compiler converts already validated FastFluent evidence into a
non-executing Fluent solver-plan patch. Current supported sources are
steam-air, VOF, turbulence, rheology, and their related hint-only artifacts.

```powershell
python -m fromcad2cfd fastcfd compile-fluent-patch --input <passport_or_hints.json> --output <solver_plan_patch.json> --format markdown
python -m fromcad2cfd fastcfd existing-passport-patch-demo --output-dir sandbox/output/fastfluent_h1_existing_patch_demo --format markdown
```

The public H1 demo writes VOF, turbulence, rheology, and combined
`solver_plan_patch.json` bundles with Markdown reports and a conflict summary.
It does not run Fluent, call PyFluent, edit case/data files, or generate UDF
code.

## Steam-Air Condensation v2 Evidence

The H2 steam-air route upgrades the original condensation passport with
dimensionless groups, heat-transfer estimates, non-condensable resistance,
source-term dimension checks, and expanded solver-plan patch recommendations.

```powershell
python -m fromcad2cfd fastcfd steam-air-v2-demo --output-dir sandbox/output/steam_air_v2_demo --format markdown
```

It writes `steam_air_condensation_case_v2.json`,
`steam_air_condensation_passport_v2.json`,
`steam_air_condensation_fluent_hints_v2.json`, `solver_plan_patch.json`,
`solver_plan_patch_report.md`, and `steam_air_condensation_report_v2.md`.
The route remains preview-only and does not execute Fluent or generate UDF
code.

## Solid-Liquid Suspension Evidence

The H3 solid-liquid route estimates particle-flow regime and downstream Fluent
model suitability before any Fluent setup is attempted.

```powershell
python -m fromcad2cfd fastcfd solid-liquid-handoff-demo --output-dir sandbox/output/solid_liquid_suspension_demo --format markdown
```

It writes `solid_liquid_suspension_case.json`,
`solid_liquid_suspension_passport.json`,
`solid_liquid_suspension_fluent_hints.json`, `solver_plan_patch.json`,
`solver_plan_patch_report.md`, and `solid_liquid_suspension_report.md`. The
passport reports particle Reynolds number, Stokes number, settling tendency,
mass loading, cell-particle ratio, particle time-step risk, and a conservative
DPM/Mixture/Eulerian review recommendation. It does not run Fluent, solve
particle trajectories, or generate UDF code.

## Environment Preflight

```powershell
python -m fromcad2cfd fastcfd preflight
```

The preflight command first checks the vendored C++ source tree at
`cpp/fastfluent_core`. To use another FastFluent checkout, pass `--source-root`
or set one of these variables:

- `FROMCAD2CFD_FASTFLUENT_ROOT`
- `FASTFLUENT_ROOT`

## CI-Safe Mock Demo

```powershell
python -m fromcad2cfd fastcfd mock-demo --project fastcfd_mock_cavity2d --model-name fastcfd_mock_cavity2d
```

The mock backend writes the same artifact classes expected from real FastCFD
runs:

- `generated.ini`
- `convergence.csv`
- `qoi.json`
- `physics_contract.json`
- `lattice_domain_summary.json`
- `flow_fingerprint.json`
- `fastcfd_prediction.json`
- `pilot_decision.json`
- `fluent_hints.json`
- `claim_ledger.json`
- `result_manifest.json`
- `fastcfd_report.json`
- `fastcfd_report.md`

The mock backend is deterministic and validates workflow plumbing only. It does
not produce numerical CFD evidence.

## Semantic Scene To Job

For agent workflows, prefer a semantic scene first. A scene describes the
domain, zones, obstacle intent, and physics intent. It is then validated and
compiled into a bounded `FastCFDJob`.

```powershell
python -m fromcad2cfd fastcfd write-scene --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_scene --scene-type obstacle2d --obstacle circle
python -m fromcad2cfd fastcfd validate-scene --scene-file <scene.json>
python -m fromcad2cfd fastcfd compile-scene --scene-file <scene.json> --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_job
python -m fromcad2cfd fastcfd validate-job --job-file <job.json>
python -m fromcad2cfd fastcfd run-mock-job --job-file <job.json>
```

Public examples:

- `examples/fastcfd/mock_cavity2d/job.json`
- `examples/fastcfd/channel2d_scene/scene.json`
- `examples/fastcfd/obstacle2d_scene/scene.json`

## Controlled Real Cavity2D Backend

After the local FastFluent source root is available and preflight is acceptable:

```powershell
python -m fromcad2cfd fastcfd write-cavity2d-job --project fastcfd_cavity2d_real --model-name fastcfd_cavity2d_real
python -m fromcad2cfd fastcfd run-fastfluent-cavity2d-job --job-file <job.json>
```

The command builds only the known `examples/cavity2d` target, writes a generated
`cavity2d.ini`, runs the executable in the project output directory, captures
logs, indexes VTK XML outputs, and writes the same report contract as the mock
backend.

## Controlled Real Channel2D And Obstacle2D Backends

The first inlet/outlet route uses the known FastFluent `openboundary2d` example.
The obstacle route generates a controlled local C++ variant from the channel
recipe, supports circle and rectangle recipe obstacles, and does not modify the
global FastFluent source tree.

```powershell
python -m fromcad2cfd fastcfd write-channel2d-job --project fastcfd_channel2d_real --model-name fastcfd_channel2d_real --total-steps 100 --output-interval 50
python -m fromcad2cfd fastcfd run-fastfluent-job --job-file <channel_job.json>

python -m fromcad2cfd fastcfd write-obstacle2d-job --project fastcfd_obstacle2d_real --model-name fastcfd_obstacle2d_real --obstacle circle --total-steps 100 --output-interval 50
python -m fromcad2cfd fastcfd run-fastfluent-job --job-file <obstacle_job.json>
```

Both routes write:

- generated `.ini`
- `fastfluent_native_summary.json` when the local executable has the native
  FromCAD2CFD summary hook installed
- `fastfluent_native_convergence.csv` when the local executable has the native
  residual-history hook installed
- build log
- stdout and stderr logs
- `physics_contract.json`
- `field_qoi.json`
- `lattice_domain_summary.json`
- `flow_fingerprint.json`
- `pilot_decision.json`
- `qoi.json`
- `fluent_hints.json`
- `claim_ledger.json`
- `result_manifest.json`
- Markdown and JSON reports

When real FastFluent VTK XML fields are available, `field_qoi.json` decodes the
latest field `.vti` and optional `GeoFlag` file into conservative pilot metrics:

- selected output step and grid metadata
- speed and density summaries
- centerline velocity samples
- inlet and outlet velocity profile summaries
- outlet spread and reverse-flow proxies
- obstacle wake bounding-box proxy when applicable
- near-wall and obstacle-near-field refinement hints

`flow_fingerprint.json` is a compact agent-facing subset of the same evidence.
`qoi.json`, `fluent_hints.json`, `claim_ledger.json`, and `result_manifest.json`
reference the parser status so downstream tools can distinguish parsed field
evidence from missing or failed field analysis.

## Preliminary CFD Prediction Report

Every successful mock or controlled real run writes:

- `fastcfd_prediction.json`
- `<model_name>_fastcfd_prediction.md`

The prediction report reframes available FastCFD evidence as preliminary CFD
screening rather than only as a handoff gate. It records:

- physics-screening verdict, Reynolds regime, lattice Mach estimate, tau/omega,
  and concerns,
- expected flow behavior for cavity, channel, or obstacle cases,
- numerical-quality review from residual history, field parser status, and
  lattice-domain trust,
- design implications such as outlet/domain review, wake-region optimization,
  or velocity/lattice scaling changes,
- recommended next parameter checks.

Existing output directories can be reprocessed:

```powershell
python -m fromcad2cfd fastcfd predict-from-output --fastcfd-output-dir <FastCFD output dir>
```

## Bounded Parameter Screening

Before running many solver variants, use the bounded pre-run screen. It expands
a finite set of velocity and grid-size variants, validates each physics passport,
and ranks the candidates without launching FastFluent.

```powershell
python -m fromcad2cfd fastcfd screen-parameters --job-file <job.json> --velocity-multipliers 0.5,1.0,2.0 --cell-length-multipliers 1.0,0.5 --max-variants 6
```

The output is a screening matrix with recommended and blocked variants. This is
the safe first step for simple tests such as "does the intended Reynolds regime
make sense?" or "which grid scale is worth running next?".

`lattice_domain_summary.json` records recipe-to-lattice domain checks, including
zone counts, obstacle resolution, obstacle clearance, warnings, errors, and a
bounded trust score. `pilot_decision.json` combines lattice evidence, native
residual history, and parsed field QoI into a conservative next-action status
such as `proceed_with_advisory_handoff`, `extend_pilot_before_handoff`,
`review_domain_extent`, or `revise_lattice_domain`. See
[lattice_trust_and_pilot_decision.md](lattice_trust_and_pilot_decision.md).

When present, `fastfluent_native_summary.json` is emitted directly by the
FastFluent executable and records run facts such as case type, completed steps,
grid size, physical properties, reference velocity, final residual, physical
time, and field prefix. It complements wrapper-side reports and VTK parsing.
See [native_summary_contract.md](native_summary_contract.md).

When present, `fastfluent_native_convergence.csv` is also emitted directly by
the executable and records residual history as `step,residual`. The backend
summarizes it into QoI fields such as sample count, final residual, reduction
ratio, and non-increasing fraction.

The `obstacle2d` route also writes the generated controlled C++ source and an
`obstacle_summary.json` report.
