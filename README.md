# FromCAD2CFD

**FromCAD2CFD: A CAD-to-CFD Agentic Automation Framework for Solid-Liquid Two-Phase Flow Dynamics** is an early-stage research framework for automating CAD geometry preparation, CFD domain construction, and repeatable preprocessing handoff for solid-liquid two-phase flow studies.

The project is currently a **two-pillar CAD-to-CFD alpha**:

- a CAD geometry automation pillar for SolidWorks, Siemens NX, controlled geometry repair, and mesh-to-solid preparation,
- a FastCFD / FastFluent pillar for low-cost preliminary CFD prediction, physics screening, and pre-Fluent decision support.

The current strength is not a one-click Fluent replacement. It is an
agent-readable evidence layer that makes CAD edits, unstructured mesh checks,
physics setup decisions, and Fluent handoff recommendations reproducible before
expensive high-fidelity validation.

## Engineering Strengths

- **CAD-to-CFD traceability**: CAD operations, copied-model editing, fluid-domain
  construction, mesh solidification candidates, and CFD handoff artifacts are
  reported as JSON and Markdown.
- **Safe agent execution**: the public tool surface is built around validated
  jobs, bounded commands, explicit artifacts, and fail-closed checks instead of
  arbitrary CAD, Python, C++, or solver execution.
- **Unstructured mesh readiness**: the `unstructured_fvm` route imports Gmsh
  meshes, preserves named zones, builds finite-volume geometry, validates
  boundary contracts, and runs benchmark evidence for diffusion, Stokes,
  pressure projection, 3D tetra scalar-diffusion smoke checks, channel flow,
  obstacle-channel handoff, and VOF-lite alpha transport, plus simplified
  algebraic eddy-viscosity and bounded
  standard k-epsilon, pressure-corrected k-epsilon, and Menter k-omega SST
  turbulent channel solves, JSON unstructured case execution, controlled steady
  incompressible pressure-correction cases, and a public benchmark suite for
  evidence comparison.
- **Pre-Fluent physics evidence**: VOF, turbulence, and non-Newtonian rheology
  passports generate setup checks and Fluent-facing hints with explicit
  evidence, so the agent can explain why a setting is recommended.
- **Public-safe examples**: examples are synthetic and reproducible. Private
  CAD, STL, Parasolid, NX `.prt`, Fluent case/data files, and generated runtime
  outputs are excluded from the repository.

## Current Boundary

FromCAD2CFD is an engineering research framework for reproducible CAD-to-CFD
automation and pre-Fluent evidence generation. Full Fluent Meshing execution,
production Fluent Solver setup, production-grade general unstructured
Navier-Stokes, GPU acceleration, and post-processing remain roadmap modules.

## Repository Language, Solver Core, And Licensing

This repository now contains both the **Python agent framework layer** and the
**C++ FastFluent solver core**:

- Python implements the CLI, schemas, safety gates, CAD wrappers, MCP-facing
  tool surfaces, reports, tests, and the current public unstructured benchmark
  kernels.
- C++ implements the original FastFluent / FreeLB-derived lattice Boltzmann
  solver core, examples, benchmark sources, and low-level data structures under
  [`cpp/fastfluent_core`](cpp/fastfluent_core).
- Controlled real FastFluent runs can use the vendored C++ core by default, or
  an explicit source root through `--source-root`,
  `FROMCAD2CFD_FASTFLUENT_ROOT`, or `FASTFLUENT_ROOT`.

License boundary:

- The Python agent framework is published under the root Apache-2.0 license.
- The vendored C++ FastFluent core retains its original GPLv3 license; see
  [`cpp/fastfluent_core/LICENSE`](cpp/fastfluent_core/LICENSE).

Compiled executables, object files, generated VTK outputs, Fluent case/data
files, and unreviewed CAD/STL geometry data are intentionally not committed.
This keeps the public repository source-first while avoiding accidental release
of generated artifacts or private geometry.

## Current Scope

| Area | Status | Notes |
| --- | --- | --- |
| Common CAD backend contract | Working local abstraction | Shared result, recipe, inspection, export, and registry structures. |
| SolidWorks backend | Working alpha | Uses `pywin32`/COM for controlled geometry creation, copied-model editing, STEP export, and reports. |
| Siemens NX backend | Controlled-journal backend | Uses validated job JSON plus NXOpen journals through `run_journal.exe`. |
| Siemens NX MCP surface | Runnable stdio server | Exposes high-level safe tools for capability reporting, preflight, job writing, and command preparation. |
| Mesh solidification | Experimental | Uses copied STL input plus optional FreeCAD/OpenCascade execution to create coarse STEP solid candidates. |
| FastFluent C++ core | Source-included alpha | Vendored under `cpp/fastfluent_core` with GPLv3 license, examples, benchmarks, LBM/CA/free-surface/non-Newtonian components, and Makefile-based builds. Generated executables, object files, VTK outputs, and unreviewed STL data are excluded. |
| FastCFD / FastFluent integration | Foundation | Defines agent-safe schemas, source-of-truth registry, semantic scene compiler, physics passport, preflight, deterministic mock workflow, controlled real `cavity2d`, `channel2d`, and `obstacle2d` backends, native run summaries, field-derived QoI parsing, lattice-domain trust scoring, preliminary prediction reports, bounded parameter screening, pilot-decision artifacts, VOF/turbulence/rheology passports, evidence-checked Fluent hint compilation, and `unstructured_fvm` mesh/FV-geometry, 2D triangle and 3D tetra scalar-diffusion, Stokes, projection, flow-benchmark, Poiseuille channel-validation, convergence, public body-fitted obstacle-channel, VOF-lite alpha-transport, algebraic eddy-viscosity turbulent-channel, k-epsilon turbulent-channel, pressure-corrected k-epsilon channel, Menter k-omega SST channel, JSON case runner, controlled steady incompressible solver, and public benchmark-suite gates. |
| Fluent Meshing | Planning gate | Reads FastCFD prediction and screening evidence and writes a pre-meshing gate report before future Fluent automation. |
| Fluent Solver | Planned | Interface boundary only. |
| Post-processing | Planned | Interface boundary only. |

## Development Route So Far

The project has been built in staged gates rather than as one monolithic solver:

1. **Safe CAD foundation**: established a shared CAD backend contract, result
   envelopes, safety policy, and public-safe examples.
2. **SolidWorks automation**: validated local COM access, created controlled
   model-generation and copied-model editing workflows, and added safe
   reporting/export patterns.
3. **NX automation**: added a controlled NXOpen journal backend, safe MCP
   surface, solid modeling packs, surface/sheet operations, Parasolid import,
   plane cutting, and reverse-modeling steps.
4. **Mesh solidification support**: added a FreeCAD/OpenCascade route for
   coarse STL-to-solid candidates without committing private device geometry.
5. **FastFluent C++ core publication**: added the original C++ solver core to
   `cpp/fastfluent_core` while excluding generated executables, object files,
   VTK outputs, and unreviewed geometry data.
6. **FastCFD / FastFluent foundation**: defined job/scene schemas, registry,
   physics passports, mock and controlled real backend routes, field QoI,
   lattice-domain trust, prediction reports, parameter screening, and
   pilot-decision artifacts.
7. **Unstructured FastFluent evidence stack**: added Gmsh import, named-zone
   preservation, mesh-quality gates, FV geometry, scalar diffusion, Stokes,
   projection, channel validation, convergence checks, obstacle-channel
   evidence, VOF-lite alpha transport, turbulence passports, algebraic
   eddy-viscosity, k-epsilon, pressure-corrected k-epsilon, Menter SST, a
   turbulence ladder, a JSON case runner, controlled steady incompressible
   solving, a public benchmark suite, and a 3D tetra scalar-diffusion smoke
   benchmark.
8. **Publication cleanup**: separated public reusable capabilities from private
   CAD/STL/Parasolid/NX/Fluent artifacts and documented what is implemented
   versus what remains a roadmap item.

## Why This Exists

CAD-to-CFD workflows often fail before meshing starts: imported geometry is rough, CAD edits are not reproducible, flow domains are rebuilt manually, and geometry decisions are not captured in reports. This project experiments with a safer agentic layer that:

- copies input models before editing,
- uses bounded CAD operations instead of arbitrary code execution,
- records JSON and Markdown reports,
- separates private research geometry from public code,
- keeps CAD-native artifacts and CFD handoff formats traceable,
- uses FastCFD / FastFluent as a separate preliminary CFD layer for physics screening before expensive Fluent validation.

## Architecture

```text
Skills and policies
  -> MCP-safe tool surface
    -> common CAD backend contract
      -> SolidWorks COM backend
      -> Siemens NX controlled-journal backend
      -> mesh solidification helper
    -> FastCFD / FastFluent preliminary CFD prediction layer
      -> physics screening, field QoI, parameter screening
    -> Fluent Meshing preflight gate
      -> reports and CFD handoff metadata
```

See [docs/architecture.md](docs/architecture.md) and [docs/cad_backend.md](docs/cad_backend.md).

## CAD Geometry Capabilities

### SolidWorks

The SolidWorks alpha supports:

- preflight through `pywin32`,
- controlled cylinder and plan-based geometry creation,
- extrude, cut, boolean combine, move/copy, fillet, chamfer, shell, thicken, sweep, loft, and revolve workflows,
- safe copied-model parameter editing by exact dimension name,
- STEP export and JSON/Markdown reports,
- CFD-oriented template plans.

### Siemens NX

The NX backend supports controlled job generation and validated NXOpen journal families for:

- synthetic public-safe geometry jobs,
- cylindrical CFD fluid-domain construction demos,
- basic solid modeling packs,
- edge/wall/trim/import packs,
- transform/profile packs,
- copied-model inspection,
- copied-model boolean subtract,
- copied-model axis-aligned plane cut,
- Parasolid import to `.prt`,
- face thicken,
- sheet sew,
- basic curves and bounded-plane surfaces,
- STL-to-convergent reverse-modeling Step 1,
- Cage from Facet Body reverse-modeling Step 2,
- XOY bounded-plane and CombineSheets reverse-modeling Step 3/4.

Print the machine-readable NX capability inventory:

```powershell
fromcad2cfd nx capabilities
fromcad2cfd nx capabilities --format markdown
```

The current NX MCP package exposes a runnable stdio server. It does not expose raw NXOpen calls, arbitrary Python execution, arbitrary journal replay, file deletion, or overwrite operations. NX journal execution is prepared as an explicit command and remains outside automatic tool execution.

### Mesh Solidification

The mesh helper supports a coarse STL-to-solid candidate route:

- copy STL inputs before processing,
- inspect STL facet count and simple watertightness indicators,
- write controlled FreeCAD/OpenCascade solidification jobs,
- locate FreeCAD through `FreeCADCmd.exe` and execute with the bundled FreeCAD Python runtime when available,
- export STEP solid candidates and JSON/Markdown reports.

This route is useful when CFD preprocessing needs a boolean-capable coarse solid. It does not claim parametric, analytic, or high-accuracy reverse engineering.

## FastCFD / FastFluent Preliminary CFD Layer

The FastCFD foundation prepares the internal FastFluent solver for agent-native
use as a low-cost preliminary CFD prediction and physics-screening layer before
high-fidelity Fluent validation. The first batch adds:

- `fromcad2cfd fastcfd` CLI routing,
- validated `FastCFDJob` and `FastCFDScene` contracts,
- a machine-readable source-of-truth registry for allowed case templates,
- semantic scene validation and scene-to-job compilation,
- mandatory physics passport validation before mock or controlled real runs,
- optional FastFluent source/build preflight,
- deterministic `cavity2d` mock workflow,
- controlled real `cavity2d`, `channel2d`, and `obstacle2d` execution against the local FastFluent source,
- vendored C++ FastFluent source under `cpp/fastfluent_core` for default source-root discovery,
- native executable summaries and residual-history CSVs when source hooks are installed,
- VTK XML field parsing for speed, density, centerline, outlet, wake, and refinement proxy metrics,
- recipe-derived lattice-domain trust summaries,
- preliminary CFD prediction reports with expected flow behavior, physics screening, numerical-quality review, and design implications,
- bounded pre-run parameter screening for velocity and grid sensitivity,
- bounded pilot-decision artifacts for deciding whether to proceed, extend the pilot, review domain extent, or revise the recipe domain,
- `unstructured_fvm` mesh-quality, boundary-contract, PDE benchmark, 3D tetra scalar-diffusion smoke, Poiseuille channel-validation, and convergence evidence routes,
- VOF two-phase physics passports and Fluent setup hints for preliminary multiphase setup decisions,
- turbulence passports for Reynolds-regime, near-wall y-plus, model-intent, turbulence-intensity, and Fluent viscous-model setup checks,
- non-Newtonian rheology passports with shear-rate apparent-viscosity benchmarks and Fluent material-model setup checks,
- public synthetic body-fitted obstacle-channel evidence for named-zone and obstacle-wall preservation without private geometry,
- VOF-lite alpha-transport benchmarks for bounded volume-fraction advection, CFL, and phase-volume-balance evidence,
- a simplified algebraic eddy-viscosity turbulent-channel benchmark with iterative effective-viscosity momentum solves, turbulent-viscosity ratio fields, convergence history, and VTU output,
- a bounded standard k-epsilon turbulent-channel benchmark with streamwise momentum, k transport, epsilon transport, eddy-viscosity update, turbulence production, convergence history, and VTU output,
- a bounded pressure-corrected k-epsilon channel benchmark with momentum prediction, pressure correction, k/epsilon transport, divergence monitoring, and VTU output,
- a bounded Menter k-omega SST channel benchmark with k/omega transport, SST blending functions, eddy-viscosity limiting, convergence history, and VTU output,
- a turbulence benchmark ladder that runs all four channel tiers on one public mesh and recommends the strongest passed evidence tier for later Fluent setup,
- evidence-checked Fluent setup hint compilation across validated FastCFD artifacts,
- `generated.ini`, QoI, physics contract, flow fingerprint, Fluent hints, claim ledger, result manifest, and reports.

The mock backend validates workflow plumbing only. Real FastFluent source
field-derived metrics support preliminary CFD prediction and physics screening,
but they are not final Fluent-grade validation. Real FastFluent source
refactoring will continue to target the same artifact contract and remain
bounded to allowed case templates before broader solver integration.

Agent workflows should prefer the semantic scene route:

```powershell
fromcad2cfd fastcfd registry --format markdown
fromcad2cfd fastcfd write-scene --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_scene --scene-type obstacle2d --obstacle circle
fromcad2cfd fastcfd validate-scene --scene-file <scene.json>
fromcad2cfd fastcfd compile-scene --scene-file <scene.json> --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_job
fromcad2cfd fastcfd run-mock-job --job-file <job.json>
```

FastCFD details are documented in [docs/fastcfd/quickstart.md](docs/fastcfd/quickstart.md)
and [docs/fastcfd/native_summary_contract.md](docs/fastcfd/native_summary_contract.md).
The VOF physics passport is documented in
[docs/fastcfd/vof_physics_passport.md](docs/fastcfd/vof_physics_passport.md).
The combined physics-passport and Fluent-hint boundary is documented in
[docs/fastcfd/physics_passports_and_fluent_hints.md](docs/fastcfd/physics_passports_and_fluent_hints.md).
The lattice trust and pilot-decision artifacts are documented in
[docs/fastcfd/lattice_trust_and_pilot_decision.md](docs/fastcfd/lattice_trust_and_pilot_decision.md).

## Installation

From a local checkout:

```powershell
python -m pip install -e ".[dev]"
```

After installation:

```powershell
fromcad2cfd --version
fromcad2cfd --help
```

On Windows user installs, the Python user `Scripts` directory may not be on
`PATH`. The module form works without relying on console script discovery:

```powershell
python -m fromcad2cfd --version
python -m fromcad2cfd --help
```

For source-tree smoke checks without installing:

```powershell
$env:PYTHONPATH="src"
python -m fromcad2cfd --help
python -m fromcad2cfd nx capabilities --format markdown
```

Optional SolidWorks environment variables:

```powershell
$env:SOLIDWORKS_EXE="C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe"
$env:SOLIDWORKS_TEMPLATE_DIR="C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates"
```

Siemens NX journal execution requires a local NX installation with `run_journal.exe`.

Optional FreeCAD mesh solidification requires `FreeCADCmd.exe`. Set:

```powershell
$env:FREECADCMD_EXE="C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe"
```

For portable FreeCAD bundles, pass the extracted `FreeCADCmd.exe` path with
`--freecadcmd`. The runtime wrapper uses this path to locate the same bundle's
`bin\python.exe`, which is the verified execution mode for FreeCAD 1.1.1.

## Quickstart

Common contract:

```powershell
fromcad2cfd cad contract
```

SolidWorks:

```powershell
fromcad2cfd solidworks preflight
fromcad2cfd solidworks create-cylinder --radius-mm 10 --height-mm 20
```

Siemens NX:

```powershell
fromcad2cfd nx preflight
fromcad2cfd nx capabilities --format markdown
fromcad2cfd nx write-basic-solid-pack-job --project nx_basic_solid_pack_demo
fromcad2cfd nx write-fluid-domain-demo-job --project nx_fluid_domain_cylinder_demo
fromcad2cfd nx write-edge-wall-trim-pack-job --project nx_edge_wall_trim_demo
fromcad2cfd nx write-transform-profile-pack-job --project nx_transform_profile_demo
```

Mesh solidification:

```powershell
fromcad2cfd mesh preflight
fromcad2cfd mesh solidify-freecad --input-file examples\mesh\freecad_solidify\cube_ascii.stl --project mesh_solidify_cube_demo --model-name cube_solid_candidate --no-execute
```

FastCFD:

```powershell
fromcad2cfd fastcfd capabilities --format markdown
fromcad2cfd fastcfd registry --format markdown
fromcad2cfd fastcfd preflight
fromcad2cfd fastcfd mock-demo --project fastcfd_mock_cavity2d --model-name fastcfd_mock_cavity2d
fromcad2cfd fastcfd write-scene --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_scene --scene-type obstacle2d --obstacle circle
fromcad2cfd fastcfd write-channel2d-job --project fastcfd_channel2d_real --model-name fastcfd_channel2d_real
fromcad2cfd fastcfd write-obstacle2d-job --project fastcfd_obstacle2d_real --model-name fastcfd_obstacle2d_real --obstacle circle
fromcad2cfd fastcfd unstructured inspect-mesh examples/unstructured/channel2d.msh --format json
fromcad2cfd fastcfd unstructured solve-diffusion examples/unstructured/channel2d.msh --manufactured-solution linear --linear-solver sparse-cg --format json
fromcad2cfd fastcfd unstructured solve-stokes examples/unstructured/channel2d.msh --manufactured-solution linear_divergence_free --pressure-gradient 0.25,-0.75 --linear-solver sparse-cg --format json
fromcad2cfd fastcfd unstructured solve-projection examples/unstructured/unit_square_4x4.msh --manufactured-solution quadratic_correction --correction-strength 1.0 --linear-solver sparse-cg --format json
fromcad2cfd fastcfd unstructured solve-flow-benchmark examples/unstructured/unit_square_4x4.msh --iterations 5 --linear-solver sparse-cg --format json
fromcad2cfd fastcfd unstructured solve-channel-validation examples/unstructured/unit_square_4x4.msh --pressure-drop 1.0 --linear-solver sparse-cg --format json
fromcad2cfd fastcfd unstructured solve-channel-convergence --mesh-levels 2,4,8 --format json
fromcad2cfd fastcfd unstructured solve-obstacle-channel --format json
fromcad2cfd fastcfd unstructured solve-vof-lite --steps 20 --time-step-s 0.02 --velocity 0.1,0.0 --format json
fromcad2cfd fastcfd unstructured solve-turbulent-channel --iterations 8 --format json
fromcad2cfd fastcfd unstructured solve-kepsilon-channel --iterations 8 --format json
fromcad2cfd fastcfd unstructured solve-kepsilon-pressure-channel --iterations 8 --format json
fromcad2cfd fastcfd unstructured solve-sst-channel --iterations 8 --format json
fromcad2cfd fastcfd unstructured solve-turbulence-ladder --iterations 8 --format json
fromcad2cfd fastcfd unstructured write-steady-channel-case --case-file 05_projects\steady_case\input\case.json --mesh-file examples\unstructured\channel2d.msh
fromcad2cfd fastcfd unstructured run-case 05_projects\steady_case\input\case.json --format json
fromcad2cfd fastcfd unstructured solve-steady-incompressible examples\unstructured\channel2d.msh --iterations 8 --format json
fromcad2cfd fastcfd unstructured run-benchmark-suite --iterations 8 --format json
fromcad2cfd fastcfd write-vof-demo --output-dir 05_projects\vof_demo\input
fromcad2cfd fastcfd validate-vof --case-file examples\fastcfd\vof_dambreak2d_passport\vof_case.json --output-dir 05_projects\vof_demo\reports --format json
fromcad2cfd fastcfd write-turbulence-demo --output-dir 05_projects\turbulence_demo\input
fromcad2cfd fastcfd validate-turbulence --case-file 05_projects\turbulence_demo\input\turbulence_case.json --output-dir 05_projects\turbulence_demo\reports --format json
fromcad2cfd fastcfd write-rheology-demo --output-dir 05_projects\rheology_demo\input
fromcad2cfd fastcfd run-rheology-benchmark --case-file 05_projects\rheology_demo\input\rheology_case.json --output-dir 05_projects\rheology_demo\reports --format json
fromcad2cfd fastcfd compile-fluent-hints --evidence-files <vof_hints.json>,<turbulence_hints.json>,<rheology_hints.json> --output-dir 05_projects\fluent_hints_demo\reports --format json
fromcad2cfd fastcfd predict-from-output --fastcfd-output-dir <FastCFD output dir>
fromcad2cfd fastcfd screen-parameters --job-file <job.json> --velocity-multipliers 0.5,1.0,2.0
```

Fluent Meshing preflight gate:

```powershell
fromcad2cfd fluent-meshing preflight-gate --fastcfd-output-dir <FastCFD output dir>
```

Public examples are under [examples](examples). They use only synthetic geometry or placeholder input paths.

NX MCP server:

```powershell
python -m pip install -e ".[mcp]"
python -m fromcad2cfd_mcp_nx.server --describe
python -m fromcad2cfd_mcp_nx.server --list-tools
python -m fromcad2cfd_mcp_nx.server
```

Project-level Codex configuration example:

```text
configs/codex/nx_mcp_config.example.toml
```

## Reverse Modeling

The NX reverse-modeling workflow is documented as a bounded, user-taught process:

1. Import STL as cleaned convergent bodies.
2. Create a cage/subdivision representation from convergent bodies.
3. Import accepted Parasolid output, create an XOY bounded-plane sheet, move it in +Z, and run CombineSheets with recorded region trackers.

See [docs/nx/reverse_modeling_workflow.md](docs/nx/reverse_modeling_workflow.md).

This workflow does not claim automatic conversion of arbitrary faceted geometry into perfect analytic CAD.

The alternative FreeCAD/OpenCascade route is documented in [docs/mesh/freecad_solidify.md](docs/mesh/freecad_solidify.md). It is a coarse mesh-to-solid candidate path for workflows where boolean operations matter more than analytic surface fidelity.

## Safety Rules

- Never overwrite original CAD files.
- Copy inputs before editing.
- Use timestamped or unique output paths.
- Inspect models before modifying existing geometry.
- Stop on ambiguous body, face, feature, or dimension selectors.
- Rebuild or update after geometry edits.
- Stop on rebuild/update failure.
- Save CAD-native artifacts and export supported CFD handoff formats.
- Write JSON and Markdown reports.
- Do not expose arbitrary code execution as an agent tool.

## Private Data Policy

This repository must not include proprietary CAD models, research device geometry, STL/Parasolid/NX/SolidWorks outputs, Fluent case/data files, license files, or local absolute paths.

Keep private models and generated artifacts only in ignored local folders such as:

```text
sandbox/input/
sandbox/output/
sandbox/reports/
05_projects/
06_logs/
```

## Repository Layout

```text
src/fromcad2cfd/                 Root CLI

CAD geometry pillar:
src/fromcad2cfd_cad/             Common CAD backend contract
src/fromcad2cfd_solidworks/      SolidWorks automation backend
src/fromcad2cfd_nx/              Siemens NX controlled-journal backend
src/fromcad2cfd_mcp_nx/          Safe NX MCP stdio server
src/fromcad2cfd_mesh/            Mesh inspection and FreeCAD solidification helper

FastCFD / CFD screening pillar:
src/fromcad2cfd_fastcfd/         FastCFD/FastFluent preliminary CFD screening layer
src/fromcad2cfd_fluent_meshing/  Fluent Meshing planning gate

docs/                            Architecture and workflow documentation
skills/                          Codex skill definitions
examples/                        Public synthetic examples
tests/                           Unit tests
```

## Development Checks

```powershell
python -m compileall src tests
python -m pytest
```

Current local validation: see the latest run summary in project reports or release notes.

## Roadmap

- `v0.1`: SolidWorks automation alpha.
- `v0.2`: CAD backend abstraction and Siemens NX controlled-journal backend.
- `v0.3`: release hardening, public synthetic end-to-end demos, richer inspection, and broader MCP integration tests.
- `v0.4`: Fluent Meshing prototype.
- `v0.5`: Fluent Solver setup and post-processing prototypes.
- `v1.0`: full CAD-to-CFD closed-loop workflow.

## Citation

If you use this project in academic work, cite it using [CITATION.cff](CITATION.cff).
Technical references for FreeCAD, Open CASCADE Technology, and mesh-to-Part
conversion are listed in [docs/references.md](docs/references.md).
