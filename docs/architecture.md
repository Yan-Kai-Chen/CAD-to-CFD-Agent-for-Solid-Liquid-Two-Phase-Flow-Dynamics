# Architecture

The framework is organized into five layers:

```text
Skills layer -> MCP layer -> Python tool layer -> Workflow layer -> Report layer
```

## Modules

- `fromcad2cfd_core`: shared schemas, safety helpers, units, and result conventions.
- `fromcad2cfd_solidworks`: SolidWorks automation through pywin32/COM.
- `fromcad2cfd_mcp_solidworks`: future MCP wrapper for safe SolidWorks tools.
- `fromcad2cfd_fluent_meshing`: Fluent Meshing roadmap module.
- `fromcad2cfd_fluent_solver`: Fluent Solver roadmap module.
- `fromcad2cfd_postprocessing`: CFD post-processing roadmap module.

## Current Boundary

The public alpha focuses on SolidWorks automation. Fluent-related modules are placeholders and interface drafts.
