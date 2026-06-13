# Architecture

The framework is organized as a multi-CAD, safety-first automation stack:

```text
Skills and policies
  -> MCP-safe tool surface
    -> backend-neutral CAD contract
      -> CAD-specific backends
        -> controlled CAD runtime adapters
          -> geometry reports and CFD handoff metadata
    -> FastCFD advisory pilot-flow layer
      -> Fluent Meshing preflight gate
        -> meshing-preparation reports and handoff hints
```

## CAD Backend Topology

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
  -> fromcad2cfd_fastcfd
      -> semantic scene registry
      -> physics passport
      -> mock and controlled FastFluent backends
      -> field QoI, lattice trust, and pilot decision artifacts
  -> fromcad2cfd_fluent_meshing
      -> FastCFD evidence preflight gate
  -> JSON report
  -> Markdown report
  -> CAD handoff artifact
```

The common CAD contract lets Fluent-oriented modules consume geometry outputs
without knowing whether a model was created or repaired in SolidWorks, Siemens
NX, or a coarse mesh-to-solid helper. FastCFD artifacts add cheap pilot-flow
evidence before downstream Fluent preparation, but they are advisory and do not
replace Fluent mesh or solver validation.

## Modules

- `fromcad2cfd_core`: shared schemas, safety helpers, units, and result conventions.
- `fromcad2cfd_cad`: common CAD backend contract, result envelopes, export metadata, and backend registry.
- `fromcad2cfd_solidworks`: SolidWorks automation through pywin32/COM.
- `fromcad2cfd_mcp_solidworks`: future MCP wrapper for safe SolidWorks tools.
- `fromcad2cfd_nx`: Siemens NX backend based on validated NXOpen journal jobs.
- `fromcad2cfd_mcp_nx`: safe Siemens NX stdio MCP server with high-level job builders.
- `fromcad2cfd_mesh`: mesh inspection and optional FreeCAD/OpenCascade coarse solidification.
- `fromcad2cfd_fastcfd`: advisory FastCFD/FastFluent pilot-flow workflows with validation gates and reports.
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
solidification helper, a FastCFD/FastFluent advisory pilot-flow layer, and a
Fluent Meshing preflight gate. Full Fluent Meshing execution, Fluent Solver, and
post-processing remain roadmap modules.

The repository intentionally excludes private CAD, STL, Parasolid, NX `.prt`,
Fluent case/data files, generated runtime outputs, and local absolute paths.
