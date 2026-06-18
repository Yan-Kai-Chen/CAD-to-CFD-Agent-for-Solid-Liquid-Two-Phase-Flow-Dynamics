# HyperMesh Meshing Interface

The HyperMesh meshing layer defines the agent-facing contract for creating
CFD-ready two-dimensional surface meshes through local Altair HyperMesh /
HyperMesh CFD.

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
fromcad2cfd hypermesh-meshing write-surface-mesh-tcl --geometry-input <model.x_t> --output <surface.tcl> --hm-output <surface.hm> --target-size-m <size>
fromcad2cfd hypermesh-meshing run-tcl-template --script <generated.tcl> --log <run.log> --manifest <manifest.json>
fromcad2cfd hypermesh-meshing parse-hmbatch-log --log <run.log>
fromcad2cfd hypermesh-meshing parse-surface-mesh-log --log <run.log> --json-report <report.json> --markdown-report <report.md>
```

MCP entry point:

```powershell
fromcad2cfd-hypermesh-meshing-mcp --describe
fromcad2cfd-hypermesh-meshing-mcp --list-tools
```

The adapter should preserve Fluent boundary-zone names, generate only the
two-dimensional surface mesh, export the accepted surface mesh artifact, and
write machine-readable quality reports before downstream Fluent meshing or
solver setup is allowed to continue. HyperMesh is not responsible for tetra,
prism, hexcore, boundary-layer volume mesh, or any other three-dimensional
volume mesh in this workflow.

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

## Controlled Surface Pipeline

The production-oriented local path writes a constrained Tcl script with
`write-surface-mesh-tcl`, runs it through the same generated-script guard, then
parses the hmbatch log with `parse-surface-mesh-log`.

The script records:

- input geometry path and target surface element size;
- import status;
- component, solid, surface, and line counts;
- bounding boxes and extents;
- surface count before meshing;
- face error count from the surface automesh loop;
- final surface element and node counts;
- duplicate element check status, cleanup status, and final duplicate count;
- declared `.hm` output path.

The generated script deletes duplicate surface elements detected by HyperMesh,
then repeats the duplicate check. The parser returns `passed` only when markers,
declared outputs, import,
surface mesh storage, `.hm` write, nonzero elements, nonzero nodes, zero face
errors, and zero duplicate elements agree. It returns `review` when the core
output exists but face errors or duplicate elements require inspection, and
`failed` when required evidence is missing.

This command chain is surface-only. It intentionally does not create tetra,
prism, hexcore, boundary-layer volume mesh, or any other HyperMesh 3D volume
mesh.
