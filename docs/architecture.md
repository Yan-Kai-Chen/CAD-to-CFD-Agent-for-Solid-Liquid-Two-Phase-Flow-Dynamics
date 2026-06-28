# Architecture

FromCAD2CFD is organized as a four-block CAD-to-CFD workflow with a shared
safety and reporting spine:

1. `Modeling`
2. `FastFluent`
3. `Meshing`
4. `Fluent`

These are not four disconnected modules. They are four workflow stages that an
agent can traverse with explicit plans, bounded tools, and machine-readable
artifacts.

The paper-facing restructure adds a navigation layer above the original public
assets:

```text
public repository assets
  -> framework base
  -> four workflow blocks
  -> Agent workflow spine
  -> 4+1 benchmark ladder
  -> dewaxing Agent case study
```

The detailed mapping is maintained in
`public_asset_framework_map.md`. Original public modules and examples stay in
their natural engineering locations; benchmark and dewaxing pages reference
them by role instead of duplicating or relocating everything.

## Top-Level Flow

```text
AI agent
  -> skills, policies, and MCP-safe tool surfaces
    -> Modeling
      -> SolidWorks
      -> Siemens NX
      -> mesh solidification helper
    -> FastFluent
      -> scene and job validation
      -> structured and unstructured CFD evidence
      -> physics passports and screening outputs
    -> Meshing
      -> HyperMesh surface-mesh planning and local batch adapter
      -> Fluent meshing preflight and handoff checks
    -> Fluent
      -> solver-plan validation
      -> local execution adapter contracts
      -> monitor parsing and post-run summaries
```

## Block 1: Modeling

The modeling block is responsible for creating or repairing geometry before
meshing and solving.

```text
fromcad2cfd CLI / MCP
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
```

Design intent:

- keep the CAD backend explicit;
- copy inputs before editing;
- stop on ambiguous selectors;
- export CFD-relevant artifacts instead of raw ad hoc state.

## Block 2: FastFluent

FastFluent is the project's low-cost CFD evidence engine. It exists to support
engineering decisions before expensive solver execution.

```text
FastFluent
  -> cpp/fastfluent_core
    -> C++ numerical backend
  -> fromcad2cfd_fastcfd
    -> scene registry and job schemas
    -> prediction and screening
    -> field QoI and reports
    -> physics passports
    -> Fluent setup hints and solver-plan patch bundles
    -> structured solver orchestration
    -> unstructured public benchmark routes
```

Current public unstructured scope includes:

- Gmsh import and named-zone preservation;
- mesh-quality checks and finite-volume geometry;
- scalar diffusion, Stokes, projection, and steady incompressible routes;
- obstacle-channel and channel-validation evidence;
- VOF-lite, turbulence, and rheology-related workflow support;
- steam-air condensation screening that emits a physics passport, Fluent setup
  hints, and a validated non-executing `solver_plan_patch.json` handoff bundle;
- solid-liquid suspension screening that recommends DPM, Mixture, or Eulerian
  review using explicit particle-flow evidence.

Architecturally, FastFluent is not a side note under modeling. It is a separate
decision layer between geometry preparation and high-fidelity Fluent work.

## Block 3: Meshing

The meshing block turns accepted geometry into reviewed meshing inputs and
surface-mesh artifacts.

```text
Meshing
  -> fromcad2cfd_hypermesh_meshing
    -> meshing-plan validation
    -> runtime discovery
    -> Tcl / Python template generation
    -> controlled hmbatch execution
    -> batch-log and surface-mesh parsing
  -> fromcad2cfd_fluent_meshing
    -> preflight gate
    -> handoff hints
```

Current scope is intentionally narrow:

- HyperMesh is used as a controlled **surface-meshing** route;
- Fluent meshing support in public mainline is currently a preflight and
  handoff boundary, not a full public volume-meshing automation stack.

This separation is deliberate. Surface-mesh generation, quality reporting, and
boundary naming need their own agent-facing contract before downstream volume
meshing or solver execution is allowed to continue.

## Block 4: Fluent

The Fluent block manages solver-side workflow logic.

```text
Fluent
  -> fromcad2cfd_fluent_solver
    -> solver-plan validation
    -> Solver Plan v2 patch-preview receiver
    -> resume-plan guardrails
    -> advisory PyFluent template generation
  -> fromcad2cfd_postprocessing
    -> monitor parsing
    -> summary reports
    -> video/report planning
  -> MCP wrappers
    -> bounded planning and post-processing tools
```

The key architectural distinction is:

- **portable public contracts** live in the repository;
- **machine-specific execution details** live in local adapters.

That means the public mainline can define how an agent should validate a solver
plan, prepare templates, parse monitors, and structure reports, while a local
licensed environment can bind those same contracts to actual Fluent launches,
checkpoint recovery, exports, and long-running supervision.

## Shared Safety And Reporting Spine

Every block is expected to follow the same operating rules:

- explicit input and output paths;
- no overwrite of original geometry inputs;
- unique or timestamped outputs;
- validation before execution;
- JSON and Markdown reports after execution;
- no raw arbitrary-code exposure as a public agent tool.

This common spine is what allows the project to behave like one workflow rather
than a loose collection of scripts.

## Current Boundary

Public mainline already provides:

- bounded SolidWorks and NX geometry workflows;
- mesh solidification helpers;
- FastFluent screening and public unstructured evidence routes;
- HyperMesh surface-mesh planning and controlled local batch execution;
- Fluent solver planning contracts and post-processing summaries.

Public mainline does not claim that every industrial runtime detail is portable
out of the box. Private CAD, private meshes, licensed Fluent execution, and
final production CFD validation remain environment-specific.
