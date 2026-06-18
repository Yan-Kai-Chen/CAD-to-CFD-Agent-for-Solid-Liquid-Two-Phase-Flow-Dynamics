"""Safety instructions for the HyperMesh Meshing MCP server."""

HYPERMESH_MESHING_MCP_INSTRUCTIONS = """
Expose high-level HyperMesh CFD meshing workflow tools.

Never expose arbitrary Python execution, arbitrary Tcl execution, unrestricted
GUI command injection, delete operations, overwrite operations, or direct
HyperMesh launch without a validated meshing plan and explicit local adapter.

The public MCP surface validates meshing plans, locates local HyperMesh
runtimes, writes advisory Python/Tcl templates, and prepares controlled local
adapter inputs. It must not upload or package private CAD, STL, `.hm`, `.msh`,
`.cas`, license, or local Altair installation files.

Meshing workflows must preserve CFD boundary-zone names, write quality reports,
and fail closed when import, boundary assignment, boundary-layer generation,
volume meshing, Fluent export, or Fluent mesh check evidence is missing.
"""
