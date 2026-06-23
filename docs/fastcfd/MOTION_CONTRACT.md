# FastFluent Motion Contract

The motion contract is a bounded, executable-code-free input layer for moving
boundaries, moving obstacles, and moving bodies. It gives the agent a safe way
to describe time-dependent geometry before a real dynamic-mesh, immersed-boundary,
or Fluent dynamic-mesh route is available.

This is a kinematic preflight capability. It does not solve moving-mesh CFD,
does not perform FSI coupling, and does not replace Fluent validation.

## Supported Motion Objects

Each motion object targets one named entity:

- `boundary`
- `obstacle`
- `body`

Use `target_name` for the engineering object name. Use the optional
`target_patch_name` when the actual mesh boundary patch has a different name.
For example, an obstacle can be named `cylinder_obstacle` while the mesh patch
is named `obstacle_wall`.

Supported motion kinds are:

- `stationary`
- `constant_translation`
- `sinusoidal_translation`
- `constant_rotation`
- `oscillatory_rotation`

Units are fixed:

- length: `m`
- time: `s`
- angle: `rad`

## Safety Rules

The validator fails closed when:

- a target type is unknown;
- a motion kind is unknown;
- required numeric parameters are missing;
- rotation axes are invalid;
- units are not SI;
- executable-code keys appear, including `python`, `shell`, `command`, `script`,
  `udf`, `executable`, or `subprocess`.

This keeps the motion layer as data only. User-defined functions and solver-side
code generation must be handled by a separate, explicitly approved adapter.

## CLI

Write a public demo contract:

```powershell
python -m fromcad2cfd fastcfd motion write-demo --output-dir sandbox/output/motion_demo --format json
```

Validate a motion contract:

```powershell
python -m fromcad2cfd fastcfd motion validate sandbox/output/motion_demo/motion.json --format markdown
```

Sample the motion in time:

```powershell
python -m fromcad2cfd fastcfd motion sample sandbox/output/motion_demo/motion.json --output-dir sandbox/output/motion_sample --time-step-s 0.25 --total-time-s 1.0 --format json
```

The sampler writes:

```text
motion_summary.json
motion_samples.csv
motion_report.md
```

Bind the motion contract to a Gmsh mesh and run motion-CFL gates:

```powershell
python -m fromcad2cfd fastcfd motion adapt-mesh sandbox/output/motion_demo/motion.json sandbox/output/channel.msh --output-dir sandbox/output/motion_mesh_adapter --time-step-s 0.01 --total-time-s 0.1 --format json
```

The mesh adapter writes:

```text
motion_summary.json
motion_samples.csv
motion_report.md
motion_adapter.json
motion_adapter.md
```

The adapter verifies:

- each target patch exists in the mesh;
- boundary element and node counts are nonzero;
- a mesh characteristic length can be estimated;
- the motion Courant number stays below configured thresholds;
- a solver-facing adapter payload can be written without executing code.

Run solver-dispatch preflight from a motion adapter:

```powershell
python -m fromcad2cfd fastcfd motion solver-preflight sandbox/output/motion_mesh_adapter/motion_adapter.json --output-dir sandbox/output/motion_solver_preflight --solver-family steady_incompressible --execution-mode static_grid_motion_evidence --format json
```

Attach the preflight to an unstructured case run:

```powershell
python -m fromcad2cfd fastcfd unstructured run-case sandbox/output/case.json --motion-adapter sandbox/output/motion_mesh_adapter/motion_adapter.json --motion-execution-mode static_grid_motion_evidence --output-dir sandbox/output/case_run --format json
```

`static_grid_motion_evidence` is the only execution mode that allows current
steady unstructured solvers to proceed with active motion. It records the motion
as evidence and keeps the mesh static. `require_dynamic_mesh` and
`block_on_motion` fail closed when active motion is present.

Run a quasi-steady static-grid motion sequence:

```powershell
python -m fromcad2cfd fastcfd motion quasi-steady sandbox/output/case.json sandbox/output/motion_mesh_adapter/motion_adapter.json --output-dir sandbox/output/quasi_steady_motion --format json
```

The quasi-steady route writes:

```text
qs_summary.json
qs_history.csv
qs_report.md
s000/
s001/
...
```

Each snapshot runs the bounded steady unstructured route on the same static
mesh while attaching the sampled motion evidence for that time. This is useful
for agent-side engineering screening, but it is not a dynamic-mesh calculation.
The route reports both execution `status` and solver-quality `quality_status`.
`status=success` means the sequence completed; `quality_status=warning` means
the native evidence is only suitable for screening and should be repaired before
Fluent handoff.

Run the public moving-obstacle evidence demo:

```powershell
python -m fromcad2cfd fastcfd motion moving-obstacle-demo --output-dir sandbox/output/moving_obstacle_demo --format json
```

The demo generates a public body-fitted obstacle-channel mesh, binds a
sinusoidal obstacle motion to `obstacle_wall`, runs obstacle mesh evidence, and
then runs the quasi-steady sequence. The demo intentionally keeps route
execution separate from evidence quality: a completed public route can still
return `quality_status=warning` when divergence or mass-flux balance is
marginal.

## Example Payload

```json
{
  "schema_version": "fastfluent_motion_contract_v1",
  "case_id": "public_motion_contract_demo",
  "units": {
    "length": "m",
    "time": "s",
    "angle": "rad"
  },
  "motions": [
    {
      "id": "oscillating_obstacle_x",
      "target_type": "obstacle",
      "target_name": "cylinder_obstacle",
      "target_patch_name": "obstacle_wall",
      "motion_kind": "sinusoidal_translation",
      "reference_point": [0.0, 0.0, 0.0],
      "parameters": {
        "amplitude_m": [0.02, 0.0, 0.0],
        "frequency_hz": 0.5,
        "phase_rad": 0.0
      }
    }
  ]
}
```

## Evidence Boundary

The evidence level is `kinematic_preflight_only`.

The generated evidence is useful for:

- checking whether the intended moving geometry can be represented as clean
  data;
- estimating displacement, velocity, angle, and angular velocity over a time
  window;
- handing a solver adapter a normalized time-dependent motion table.
- binding moving-boundary intent to named mesh patches before solver execution.
- blocking solver dispatch when a dynamic mesh is requested but not implemented.
- generating quasi-steady static-grid snapshots for motion-aware screening.
- reporting whether each motion snapshot is `passed`, `warning`, or `failed`
  under the S4 steady-solver hardening gates.

It is not sufficient for:

- dynamic mesh deformation;
- mesh remeshing;
- immersed-boundary coupling;
- FSI;
- final CFD validation.
