# FreeCAD Mesh Solidification

This workflow converts copied STL input into a coarse solid candidate through
FreeCAD/OpenCascade. It is intended for CAD-to-CFD preparation when the next
operation needs a boolean-capable body, not a high-fidelity analytic reverse
engineering model.

## Scope

The route is useful when:

- the source is an STL or faceted mesh,
- exact analytic surfaces are not required,
- the output only needs to be a solid candidate for boolean operations,
- a STEP intermediate is acceptable,
- NX can later import the STEP and save `.prt` or export `.x_t`.

The route is not intended to create:

- editable parametric feature history,
- clean analytic cylinders, fillets, or lofts,
- guaranteed low-face-count CAD,
- production-quality reverse-engineered surfaces.

## Commands

Check whether FreeCADCmd is available:

```powershell
fromcad2cfd mesh preflight
```

`FreeCADCmd.exe` is used as the stable installation locator. When the same
FreeCAD bundle contains `bin\python.exe`, execution prefers that bundled Python
interpreter because it passes job arguments reliably while still loading
FreeCAD/OpenCascade modules.

Write a job without executing it:

```powershell
fromcad2cfd mesh write-solidify-freecad-job --input-file examples\mesh\freecad_solidify\cube_ascii.stl --project mesh_solidify_cube_demo --model-name cube_solid_candidate
```

Write and execute when FreeCADCmd is available:

```powershell
fromcad2cfd mesh solidify-freecad --input-file examples\mesh\freecad_solidify\cube_ascii.stl --project mesh_solidify_cube_demo --model-name cube_solid_candidate --freecadcmd "C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe"
```

Execute an existing job:

```powershell
fromcad2cfd mesh run-solidify-freecad-job --job-file 05_projects\mesh_solidify_cube_demo\input\cube_solid_candidate_job.json
```

## Runtime Behavior

The tool:

1. copies the STL to the project runtime input folder,
2. inspects facet count and simple edge watertightness indicators,
3. writes a controlled `fromcad2cfd_mesh_job_v1` job,
4. resolves the FreeCAD runtime from `FreeCADCmd.exe`,
5. runs the standalone conversion script through the bundled FreeCAD Python
   runtime when available,
6. exports a STEP solid candidate,
7. writes JSON and Markdown reports.

If FreeCADCmd is not available, the run stops with status `blocked` and writes a
diagnostic report instead of repeatedly trying fallback commands.

## Recommended Follow-Up

After a STEP candidate is created:

1. import it into NX with `fromcad2cfd nx write-import-parasolid-job` only if it
   is already Parasolid, or add a future STEP import wrapper,
2. save the NX `.prt`,
3. inspect body counts,
4. use copied-model boolean subtract only after explicit body selection.

## Acceptance Criteria

- Original STL is never modified.
- Input is copied before processing.
- Output is labeled as a coarse solid candidate.
- Reports include copied input path, original input path, triangle count, and
  watertightness indicators.
- Missing FreeCADCmd is reported as `blocked`, not treated as success.
- The verified FreeCAD 1.1.1 portable-bundle execution mode is
  `execution_mode=bundled_python`.

## References

- FreeCAD Project. "FreeCAD 1.1.1." GitHub release, 2026.
  <https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.1>
- FreeCAD Documentation. "Start up and Configuration." FreeCAD documentation.
  <https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Start_up_and_Configuration.md>
- FreeCAD Documentation. "Mesh to Part." FreeCAD documentation.
  <https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Mesh_to_Part.md>
- Open CASCADE SAS. "Open CASCADE Technology Documentation: Overview."
  <https://dev.opencascade.org/doc/occt-6.9.1/overview/html/index.html>
- Open CASCADE SAS. "Data Exchange." Open CASCADE Technology.
  <https://dev.opencascade.org/about/data_exchange>
