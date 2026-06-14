# Architecture

The framework is organized as a safety-first CAD-to-CFD automation stack with
two independent first-class pillars: CAD geometry automation and FastCFD /
FastFluent preliminary CFD screening.

```text
Skills and policies
  -> MCP-safe tool surface
    -> CAD geometry automation pillar
      -> backend-neutral CAD contract
      -> CAD-specific backends
        -> controlled CAD runtime adapters
          -> geometry reports and CFD handoff metadata
    -> FastCFD preliminary CFD prediction and physics-screening layer
      -> structured LBM pilot templates
      -> unstructured FVM mesh gateway
      -> scalar diffusion benchmark gate
      -> controlled sparse linear-system gate
      -> manufactured Stokes momentum benchmark gate
      -> manufactured pressure-correction projection gate
      -> iterative projection-flow benchmark gate
      -> named boundary-condition contract gate
      -> boundary-aware Poiseuille channel-validation gate
      -> channel mesh-convergence evidence gate
      -> VOF two-phase physics-passport and setup-hint gate
      -> turbulence setup-passport and setup-hint gate
      -> non-Newtonian rheology passport and shear-rate benchmark gate
      -> public body-fitted obstacle-channel evidence gate
      -> VOF-lite alpha-transport benchmark gate
      -> algebraic eddy-viscosity turbulent-channel benchmark gate
      -> standard k-epsilon turbulent-channel benchmark gate
      -> pressure-corrected k-epsilon benchmark gate
      -> Menter k-omega SST benchmark gate
      -> turbulence evidence ladder
      -> JSON unstructured case runner
      -> controlled steady incompressible pressure-correction route
      -> public unstructured benchmark suite
      -> evidence-checked Fluent setup hint compiler
      -> physics passport, field QoI, prediction reports, parameter screening
      -> Fluent Meshing preflight gate
        -> meshing-preparation reports and handoff hints
```

## CAD Backend Topology

```text
fromcad2cfd CLI / MCP

CAD geometry pillar
  -> fromcad2cfd_cad common contract
      -> fromcad2cfd_solidworks
          -> pywin32 / SolidWorks COM
      -> fromcad2cfd_nx
          -> validated job JSON
          -> run_journal.exe
          -> NXOpen Python journals
      -> fromcad2cfd_mesh
          -> STL inspection
          -> FreeCAD/OpenCascade coarse solidification

FastCFD / CFD screening pillar
  -> cpp/fastfluent_core
      -> C++ FastFluent / FreeLB-derived solver core
      -> LBM, CA, free-surface, non-Newtonian, examples, and benchmarks
  -> fromcad2cfd_fastcfd
      -> semantic scene registry
      -> physics passport
      -> mock and controlled FastFluent backends using the vendored C++ source root by default
      -> unstructured_fvm Gmsh import, named-zone preservation, mesh-quality gate, boundary contract, FV geometry, 2D triangle and 3D tetra scalar diffusion, CSR linear systems, manufactured Stokes momentum, pressure projection, iterative flow benchmark, boundary-aware channel validation, convergence evidence, public obstacle-channel evidence, VOF-lite alpha transport, algebraic eddy-viscosity turbulent-channel benchmark, standard k-epsilon turbulent-channel benchmark, pressure-corrected k-epsilon benchmark, Menter k-omega SST benchmark, JSON case runner, controlled steady incompressible pressure-correction route, public benchmark suite, turbulence evidence ladder, and VTU preview
      -> VOF, turbulence, and rheology passports plus Fluent setup hints
      -> evidence-checked Fluent hint compiler
      -> field QoI, lattice trust, prediction, parameter screening, and pilot decision artifacts
  -> fromcad2cfd_fluent_meshing
      -> FastCFD evidence preflight gate

Shared reporting
  -> JSON report
  -> Markdown report
  -> CAD handoff artifact or CFD screening artifact
```

The common CAD contract lets Fluent-oriented modules consume geometry outputs
without knowing whether a model was created or repaired in SolidWorks, Siemens
NX, or a coarse mesh-to-solid helper.

The FastCFD / FastFluent pillar is separate from CAD modeling. It includes the
vendored C++ FastFluent core under `cpp/fastfluent_core` plus the Python
agent-facing validation and orchestration layer under `src/fromcad2cfd_fastcfd`.
The Python layer uses bounded scene, job, and physics contracts to run low-cost
preliminary CFD screens, extract field-derived QoI, issue prediction reports,
rank simple parameter variants, and prepare evidence for later Fluent work. Its
current unstructured route is an engineering validation and evidence layer: it
imports Gmsh v4 ASCII meshes, preserves physical names, writes mesh-quality
reports, builds finite-volume geometry operators, assembles CSR linear systems,
solves 2D triangle and 3D tetra scalar manufactured diffusion, runs Stokes and
pressure-projection benchmarks, produces VTU previews, and adds boundary-aware
Poiseuille channel validation,
mesh-convergence evidence, public body-fitted obstacle-channel evidence,
VOF-lite alpha-transport evidence, a simplified algebraic eddy-viscosity
turbulent-channel solve, a bounded standard k-epsilon two-equation channel
benchmark, a pressure-corrected k-epsilon benchmark, a Menter k-omega SST
benchmark, a JSON case runner, a controlled steady incompressible
pressure-correction route, and a public benchmark suite for agent setup
decisions.

The VOF, turbulence, and rheology gates validate setup inputs and Fluent-facing
hints with explicit evidence. Production Fluent Meshing, production Fluent
Solver automation, production-grade general unstructured Navier-Stokes,
turbulence/multiphase/non-Newtonian coupling, GPU acceleration, and
post-processing remain roadmap modules.

## Modules

- `fromcad2cfd_core`: shared schemas, safety helpers, units, and result conventions.
- `fromcad2cfd_cad`: common CAD backend contract, result envelopes, export metadata, and backend registry.
- `fromcad2cfd_solidworks`: SolidWorks automation through pywin32/COM.
- `fromcad2cfd_mcp_solidworks`: future MCP wrapper for safe SolidWorks tools.
- `fromcad2cfd_nx`: Siemens NX backend based on validated NXOpen journal jobs.
- `fromcad2cfd_mcp_nx`: safe Siemens NX stdio MCP server with high-level job builders.
- `fromcad2cfd_mesh`: mesh inspection and optional FreeCAD/OpenCascade coarse solidification.
- `cpp/fastfluent_core`: vendored C++ FastFluent / FreeLB-derived solver core with GPLv3 license, examples, benchmarks, LBM/CA/free-surface/non-Newtonian components, and Makefile-based builds.
- `fromcad2cfd_fastcfd`: preliminary FastCFD/FastFluent CFD prediction and physics-screening workflows with validation gates, structured pilot cases, VOF/turbulence/rheology setup-passport tooling, evidence-checked Fluent hint compilation, and the first unstructured mesh, boundary-contract, geometry, 2D triangle and 3D tetra scalar diffusion, linear-system, Stokes momentum, pressure-projection, iterative flow benchmark, boundary-aware channel validation, channel-convergence, public obstacle-channel, VOF-lite alpha-transport, algebraic eddy-viscosity turbulent-channel, standard k-epsilon turbulent-channel, pressure-corrected k-epsilon, Menter k-omega SST, JSON case-runner, controlled steady incompressible, public benchmark-suite, and turbulence-ladder gates.
- `fromcad2cfd_fluent_meshing`: Fluent Meshing planning gate; full Fluent execution remains planned.
- `fromcad2cfd_fluent_solver`: Fluent Solver roadmap module.
- `fromcad2cfd_postprocessing`: CFD post-processing roadmap module.

## Safety Boundary

The MCP layer must expose high-level workflow tools, not raw CAD APIs. Backends
must preserve the same safety contract:

- copy inputs before edits,
- never overwrite source CAD,
- use timestamped or unique outputs,
- inspect before modification,
- stop on ambiguous selectors,
- rebuild or update after operations,
- save native CAD artifacts,
- export supported CFD handoff formats,
- write JSON and Markdown reports.

Manual NX journal capture is a development technique for learning UI-derived
selector patterns. It is not an agent-facing execution surface.

## Current Boundary

The public alpha includes a working SolidWorks automation layer, a
backend-neutral CAD contract, a locally validated Siemens NX controlled-journal
backend, a mesh solidification helper, a FastCFD/FastFluent preliminary CFD
screening layer, an unstructured mesh evidence layer, physics passports, and a
Fluent Meshing preflight gate. Full Fluent Meshing execution, production Fluent
Solver automation, GPU acceleration, and post-processing remain roadmap
modules.

The repository intentionally excludes private CAD, STL, Parasolid, NX `.prt`,
Fluent case/data files, generated runtime outputs, and local absolute paths.
