# Local HyperMesh Execution Adapter

The local HyperMesh adapter is the machine-specific bridge between portable
FromCAD2CFD meshing plans and a licensed Altair HyperMesh / HyperMesh CFD
runtime.

## Preferred Runtime

Use HyperMesh CFD 2024 through `runhwx.exe` when a reviewed Python workflow is
available:

```text
runhwx.exe -client HyperWorksDesktop -plugin HyperworksCFD -profile AltairCFD -l en -b -f <script.py>
```

Use `hmbatch.exe -tcl <script.tcl>` as the fallback route for Tcl workflows.

## Adapter Responsibilities

- validate the meshing plan before launch;
- verify private geometry inputs exist locally;
- create a run manifest;
- import geometry with unit checks;
- create or map Fluent boundary-zone components;
- apply surface mesh controls;
- apply boundary-layer controls;
- create the volume mesh;
- export Fluent-compatible mesh files;
- write mesh quality reports;
- run an independent Fluent mesh import/check when available;
- fail closed when any required report is missing.

## Safety Boundary

Do not expose arbitrary HyperMesh Tcl, arbitrary HyperMesh Python, or GUI command
injection as agent tools. High-level adapter actions should be bounded:

- `prepare_meshing_run`
- `launch_meshing_run`
- `monitor_meshing_run`
- `parse_quality_report`
- `export_fluent_mesh`
- `package_meshing_run`
