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

The turbulence route validates setup readiness for a first Fluent RANS setup. It
does not solve turbulence.

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

## Environment Preflight

```powershell
python -m fromcad2cfd fastcfd preflight
```

Set one of these variables before real FastFluent backend work:

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
python -m fromcad2cfd fastcfd run-fastfluent-cavity2d-job --job-file <job.json> --source-root <FastFluent source root>
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
python -m fromcad2cfd fastcfd run-fastfluent-job --job-file <channel_job.json> --source-root <FastFluent source root>

python -m fromcad2cfd fastcfd write-obstacle2d-job --project fastcfd_obstacle2d_real --model-name fastcfd_obstacle2d_real --obstacle circle --total-steps 100 --output-interval 50
python -m fromcad2cfd fastcfd run-fastfluent-job --job-file <obstacle_job.json> --source-root <FastFluent source root>
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
