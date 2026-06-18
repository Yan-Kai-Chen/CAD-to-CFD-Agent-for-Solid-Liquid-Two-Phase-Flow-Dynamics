# HyperMesh Meshing Module

Public-safe HyperMesh CFD meshing workflow helpers.

Implemented scope:

- validate HyperMesh CFD meshing plan JSON files;
- locate local HyperMesh / HyperWorks runtimes;
- generate advisory HyperMesh Python templates;
- generate advisory HyperMesh Tcl templates;
- define the contract for controlled local meshing adapters.

Public safety boundary:

- do not commit private CAD, STL, `.hm`, `.msh`, `.cas`, or license files;
- do not expose arbitrary Tcl or Python execution as uncontrolled agent tools;
- direct HyperMesh launch belongs behind a validated plan and local adapter;
- preserve Fluent boundary-zone names and quality reports as first-class
  artifacts.
