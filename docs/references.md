# References

This project is an automation framework. The references below document external
software concepts and APIs used by the public examples and helper routes.

## FreeCAD and Mesh-to-Solid Conversion

- FreeCAD Project. "FreeCAD 1.1.1." GitHub release, 2026.
  <https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.1>
- FreeCAD Documentation. "Start up and Configuration." FreeCAD documentation.
  <https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Start_up_and_Configuration.md>
- FreeCAD Documentation. "Mesh to Part." FreeCAD documentation.
  <https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Mesh_to_Part.md>

## Open CASCADE Technology

- Open CASCADE SAS. "Open CASCADE Technology Documentation: Overview."
  <https://dev.opencascade.org/doc/occt-6.9.1/overview/html/index.html>
- Open CASCADE SAS. "Data Exchange." Open CASCADE Technology.
  <https://dev.opencascade.org/about/data_exchange>

## Notes on Use

The FreeCAD/OpenCascade mesh route in this repository is a coarse candidate
conversion path. FreeCAD's own documentation notes that mesh-to-Part conversion
can produce solids with many faces and that optimization is generally needed for
large scanned or faceted models. For this reason, the project reports mesh
counts, watertightness indicators, and downstream CAD validity checks instead of
assuming that every STL can become a clean analytic solid.
