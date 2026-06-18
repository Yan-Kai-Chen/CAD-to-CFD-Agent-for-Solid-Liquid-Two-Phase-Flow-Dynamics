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
fromcad2cfd hypermesh-meshing write-smoke-tcl --output <smoke.tcl> --hm-output <smoke.hm>
fromcad2cfd hypermesh-meshing run-tcl-template --script <generated.tcl> --log <run.log> --manifest <manifest.json>
fromcad2cfd hypermesh-meshing parse-hmbatch-log --log <run.log>
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

## Batch Smoke Test

The first controlled local execution path uses `hmbatch.exe -tcl` with a
FromCAD2CFD-generated smoke script. The smoke script creates a small meshed
block and writes a `.hm` file. This is not a production CFD tunnel mesh; it is
the acceptance test that proves the agent can drive HyperMesh batch mode and
collect run evidence.

HyperMesh 2024 may return process exit code `1` even when the generated script
reaches its expected end marker and writes the output `.hm` file. The adapter
therefore treats the following evidence as authoritative:

- FromCAD2CFD begin/end markers in the hmbatch log;
- declared output paths in the log;
- non-empty generated output files;
- HyperMesh version text in the log;
- later production quality reports and Fluent mesh-check output.

The process exit code is still recorded in the manifest, but it is not the only
pass/fail signal.
