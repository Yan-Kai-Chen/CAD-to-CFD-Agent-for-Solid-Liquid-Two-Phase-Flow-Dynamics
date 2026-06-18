# Basic HyperMesh CFD Tunnel Example

This public-safe example defines the contract for a HyperMesh CFD meshing run.
It does not include private CAD or generated mesh files.

Validate the plan:

```powershell
fromcad2cfd hypermesh-meshing validate-plan --plan examples/hypermesh_meshing/basic_cfd_tunnel/meshing_plan.json
```

Write advisory templates:

```powershell
fromcad2cfd hypermesh-meshing write-python-template `
  --plan examples/hypermesh_meshing/basic_cfd_tunnel/meshing_plan.json `
  --output sandbox/output/basic_cfd_tunnel_hm_template.py

fromcad2cfd hypermesh-meshing write-tcl-template `
  --plan examples/hypermesh_meshing/basic_cfd_tunnel/meshing_plan.json `
  --output sandbox/output/basic_cfd_tunnel_hm_template.tcl
```

The production adapter should replace template TODO blocks with recorded and
reviewed HyperMesh CFD Python/Tcl operations.
