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
  -> fromcad2cfd_fastcfd
      -> semantic scene registry
      -> physics passport
      -> mock and controlled FastFluent backends
      -> unstructured_fvm Gmsh import, named-zone preservation, mesh-quality gate, FV geometry, scalar diffusion, and VTU preview
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

The FastCFD / FastFluent pillar is separate from CAD modeling. It uses bounded
scene, job, and physics contracts to run low-cost preliminary CFD screens,
extract field-derived QoI, issue prediction reports, rank simple parameter
variants, and prepare evidence for later Fluent work. It does not replace Fluent
mesh or solver validation. Its current unstructured route is a mesh gateway only:
it imports Gmsh v4 ASCII meshes, preserves physical names, writes mesh-quality
reports, writes finite-volume geometry operators, and produces VTU previews
before future flow-solver work. Its first unstructured PDE gate is scalar
manufactured diffusion, not momentum or multiphase flow.

## Modules

- `fromcad2cfd_core`: shared schemas, safety helpers, units, and result conventions.
- `fromcad2cfd_cad`: common CAD backend contract, result envelopes, export metadata, and backend registry.
- `fromcad2cfd_solidworks`: SolidWorks automation through pywin32/COM.
- `fromcad2cfd_mcp_solidworks`: future MCP wrapper for safe SolidWorks tools.
- `fromcad2cfd_nx`: Siemens NX backend based on validated NXOpen journal jobs.
- `fromcad2cfd_mcp_nx`: safe Siemens NX stdio MCP server with high-level job builders.
- `fromcad2cfd_mesh`: mesh inspection and optional FreeCAD/OpenCascade coarse solidification.
- `fromcad2cfd_fastcfd`: preliminary FastCFD/FastFluent CFD prediction and physics-screening workflows with validation gates, structured pilot cases, and the first unstructured mesh gateway.
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

The public alpha includes a working SolidWorks automation layer, a backend-neutral
CAD contract, a locally validated Siemens NX controlled-journal backend, a mesh
solidification helper, a FastCFD/FastFluent preliminary CFD screening layer, and a
Fluent Meshing preflight gate. Full Fluent Meshing execution, Fluent Solver, and
post-processing remain roadmap modules.

The repository intentionally excludes private CAD, STL, Parasolid, NX `.prt`,
Fluent case/data files, generated runtime outputs, and local absolute paths.
