# FreeCAD Mesh Solidify Example

This example is public and synthetic. It demonstrates the coarse
mesh-to-solid route for cases where a CFD workflow needs a boolean-capable
solid candidate rather than a high-fidelity analytic reverse-engineered CAD
model.

Write the job JSON only:

```powershell
fromcad2cfd mesh solidify-freecad --input-file examples\mesh\freecad_solidify\cube_ascii.stl --project mesh_solidify_cube_demo --model-name cube_solid_candidate --no-execute
```

Execute when FreeCADCmd is available:

```powershell
fromcad2cfd mesh solidify-freecad --input-file examples\mesh\freecad_solidify\cube_ascii.stl --project mesh_solidify_cube_demo --model-name cube_solid_candidate --freecadcmd "C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe"
```

Portable FreeCAD bundles are also supported. Pass the extracted
`FreeCADCmd.exe` path; the wrapper will prefer the same bundle's
`bin\python.exe` for the actual conversion run.

Expected outputs when executed:

- copied STL input under the project runtime folder
- FreeCAD `.FCStd` candidate when enabled
- STEP solid candidate
- JSON and Markdown reports

The output is a coarse solid candidate. It is not a parametric or analytic CAD
reconstruction.
