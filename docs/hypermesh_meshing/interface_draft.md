# HyperMesh Meshing Interface

The HyperMesh meshing layer defines the agent-facing contract for creating
CFD-ready meshes through local Altair HyperMesh / HyperMesh CFD.

The public default commands validate plans, locate local runtimes, and generate
advisory Python/Tcl templates. Direct meshing execution belongs behind a
configured local adapter with a licensed HyperMesh runtime, private geometry,
run directory, quality thresholds, and export policy.

Implemented commands:

```text
fromcad2cfd hypermesh-meshing locate-runtime
fromcad2cfd hypermesh-meshing validate-plan --plan <meshing_plan.json>
fromcad2cfd hypermesh-meshing write-python-template --plan <meshing_plan.json> --output <template.py>
fromcad2cfd hypermesh-meshing write-tcl-template --plan <meshing_plan.json> --output <template.tcl>
```

MCP entry point:

```powershell
fromcad2cfd-hypermesh-meshing-mcp --describe
fromcad2cfd-hypermesh-meshing-mcp --list-tools
```

The adapter should preserve Fluent boundary-zone names, generate boundary-layer
controls where required, export Fluent-compatible mesh files, and write
machine-readable quality reports before the Fluent solver setup is allowed to
continue.
