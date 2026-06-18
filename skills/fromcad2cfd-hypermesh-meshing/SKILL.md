---
name: fromcad2cfd-hypermesh-meshing
description: Public-safe HyperMesh CFD meshing setup and local execution-adapter preparation for FromCAD2CFD. Use when validating HyperMesh meshing plans, preserving Fluent boundary-zone names, generating advisory Python/Tcl templates, locating HyperMesh runtimes, or preparing controlled local HyperMesh batch meshing without exposing private geometry or raw scripts.
---

# FromCAD2CFD HyperMesh Meshing

Use this skill for HyperMesh CFD meshing plan validation and controlled
local execution-adapter preparation.

## Rules

- Do not commit private CAD, STL, `.hm`, `.msh`, `.cas`, license files, or local Altair paths.
- Use relative paths under `sandbox/` in public examples.
- Validate a meshing plan before generating templates.
- Preserve Fluent boundary-zone names such as `inlet`, `outlet`, `outer_wall`, and `model_wall`.
- Treat generated Python/Tcl scripts as review artifacts unless a local operator or configured workflow explicitly approves execution.
- Do not expose arbitrary Tcl, arbitrary Python, GUI command injection, or raw HyperMesh commands as uncontrolled MCP tools.
- Route direct HyperMesh launch through a local adapter that records runtime configuration, validates the plan, writes quality reports, and preserves run manifests.

## Workflow

1. Create or edit a meshing plan JSON matching `fromcad2cfd_hypermesh_meshing_plan_v1`.
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

5. Keep direct HyperMesh launch outside uncontrolled public MCP tools; use a
   controlled local adapter when a licensed runtime and private geometry are
   available.

## References

- Meshing interface: `../../docs/hypermesh_meshing/interface_draft.md`
- Local adapter: `../../docs/hypermesh_meshing/local_execution_adapter.md`
