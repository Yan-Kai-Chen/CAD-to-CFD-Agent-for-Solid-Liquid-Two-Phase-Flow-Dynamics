---
name: fromcad2cfd-hypermesh-meshing
description: Public-safe HyperMesh CFD two-dimensional surface-meshing setup and local execution-adapter preparation for FromCAD2CFD. Use when validating HyperMesh surface-meshing plans, preserving Fluent boundary-zone names, generating advisory Python/Tcl templates, locating HyperMesh runtimes, or preparing controlled local HyperMesh batch surface meshing without exposing private geometry or raw scripts.
---

# FromCAD2CFD HyperMesh Meshing

Use this skill for HyperMesh CFD surface-meshing plan validation and controlled
local execution-adapter preparation.

## Rules

- Do not commit private CAD, STL, `.hm`, `.msh`, `.cas`, license files, or local Altair paths.
- Use relative paths under `sandbox/` in public examples.
- Validate a meshing plan before generating templates.
- Inspect the imported geometry bounding box before choosing mesh sizes; HyperMesh model units may be meters even when engineering intent is expressed in millimeters.
- Preserve Fluent boundary-zone names such as `inlet`, `outlet`, `outer_wall`, and `model_wall`.
- Stop the HyperMesh workflow at the accepted two-dimensional surface mesh.
- Do not create tetra, prism, hexcore, boundary-layer volume mesh, or any other three-dimensional mesh inside HyperMesh.
- Treat generated Python/Tcl scripts as review artifacts unless a local operator or configured workflow explicitly approves execution.
- Do not expose arbitrary Tcl, arbitrary Python, GUI command injection, or raw HyperMesh commands as uncontrolled MCP tools.
- Route direct HyperMesh launch through a local adapter that records runtime configuration, validates the plan, writes quality reports, and preserves run manifests.

## Workflow

1. Create or edit a surface-meshing plan JSON matching `fromcad2cfd_hypermesh_surface_meshing_plan_v1`.
2. Validate it:

```powershell
fromcad2cfd hypermesh-meshing validate-plan --plan examples/hypermesh_meshing/basic_cfd_tunnel/meshing_plan.json
```

3. Locate the local runtime:

```powershell
fromcad2cfd hypermesh-meshing locate-runtime
```

4. Generate advisory templates:

```powershell
fromcad2cfd hypermesh-meshing write-python-template --plan <plan.json> --output sandbox/output/hm_template.py
fromcad2cfd hypermesh-meshing write-tcl-template --plan <plan.json> --output sandbox/output/hm_template.tcl
```

5. For local runtime verification, write and run the controlled smoke script:

```powershell
fromcad2cfd hypermesh-meshing write-smoke-tcl --output sandbox/output/hm_smoke.tcl --hm-output sandbox/output/hm_smoke.hm
fromcad2cfd hypermesh-meshing run-tcl-template --script sandbox/output/hm_smoke.tcl --log sandbox/output/hm_smoke.log --manifest sandbox/output/hm_smoke_manifest.json
```

6. For private geometry on a licensed workstation, write and run the controlled
   surface-only pipeline:

```powershell
fromcad2cfd hypermesh-meshing write-surface-mesh-tcl --geometry-input <model.x_t> --output sandbox/output/hm_surface.tcl --hm-output sandbox/output/hm_surface.hm --target-size-m 0.02
fromcad2cfd hypermesh-meshing run-tcl-template --script sandbox/output/hm_surface.tcl --log sandbox/output/hm_surface.log --manifest sandbox/output/hm_surface_manifest.json
fromcad2cfd hypermesh-meshing parse-surface-mesh-log --log sandbox/output/hm_surface.log --json-report sandbox/output/hm_surface_report.json --markdown-report sandbox/output/hm_surface_report.md
```

7. Keep direct HyperMesh launch outside uncontrolled public MCP tools; use a
   controlled local adapter when a licensed runtime and private geometry are
   available.

## Meshing Checks

- After import, report entity counts for components, solids, surfaces, lines, nodes, and elements.
- Report the bounding box and convert plan mesh sizes into the detected model unit before meshing.
- For low-level Tcl surface meshing, use `*interactiveremeshsurf` to set element size and keep `*set_meshfaceparams` parameters in their documented order; do not pass the element size as the shape-type argument.
- After surface meshing, record face errors, final element count, node count, and duplicate element count. Add deeper GUI-calibrated surface checks only after confirming that they do not create a HyperMesh 3D volume mesh.
- Treat `volume_mesh` and `boundary_layer` keys as downstream Fluent-side concerns when they appear in legacy plans.

## Runtime Evidence

Treat a HyperMesh batch run as successful only when the manifest shows complete
FromCAD2CFD markers and expected non-empty output files. Record the process exit
code, but do not rely on it alone.

HyperMesh 2024 batch can return process exit code `1` even after a generated
script reaches its expected end marker and writes valid output. Prefer the
manifest status, marker completion, declared output checks, and quality reports
over raw exit code alone.

## References

- Meshing interface: `../../docs/hypermesh_meshing/interface_draft.md`
- Local adapter: `../../docs/hypermesh_meshing/local_execution_adapter.md`
