# Local HyperMesh Execution Adapter

The local HyperMesh adapter is the machine-specific bridge between portable
FromCAD2CFD surface-meshing plans and a licensed Altair HyperMesh /
HyperMesh CFD runtime.

## Preferred Runtime

Use HyperMesh CFD 2024 through `runhwx.exe` when a reviewed Python workflow is
available:

```text
runhwx.exe -client HyperWorksDesktop -plugin HyperworksCFD -profile AltairCFD -l en -b -f <script.py>
```

Use `hmbatch.exe -tcl <script.tcl>` as the fallback route for Tcl workflows.
This route is already used by the controlled smoke test because it can run
without GUI interaction and can be checked through log markers and output
artifacts.

## Adapter Responsibilities

- validate the meshing plan before launch;
- verify private geometry inputs exist locally;
- create a run manifest;
- import geometry with unit checks;
- create or map Fluent boundary-zone components;
- apply surface mesh controls;
- create only the two-dimensional surface mesh;
- export the accepted surface mesh artifact;
- write mesh quality reports;
- hand off three-dimensional meshing and solver setup to the downstream Fluent
  workflow when available;
- fail closed when any required report is missing.

The adapter must not create tetra, prism, hexcore, boundary-layer volume mesh,
or any other three-dimensional mesh inside HyperMesh.

## Run Evidence

The adapter must write a manifest for every local run. At minimum it should
record:

- generated script path;
- hmbatch executable path;
- command arguments;
- process exit code;
- log path;
- FromCAD2CFD marker status;
- declared output files and sizes;
- HyperMesh version text;
- quality-report and Fluent mesh-check status when available.

Do not rely on the HyperMesh process exit code alone. In local testing,
HyperMesh 2024 returned exit code `1` after a generated smoke script reached
its expected end marker and wrote a valid `.hm` file.

## Safety Boundary

Do not expose arbitrary HyperMesh Tcl, arbitrary HyperMesh Python, or GUI command
injection as agent tools. High-level adapter actions should be bounded:

- `prepare_meshing_run`
- `launch_meshing_run`
- `monitor_meshing_run`
- `parse_quality_report`
- `export_surface_mesh`
- `package_meshing_run`
