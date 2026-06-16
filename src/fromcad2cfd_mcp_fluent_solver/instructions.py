"""Safety instructions for the Fluent Solver MCP server."""

FLUENT_SOLVER_MCP_INSTRUCTIONS = """
Expose high-level Fluent Solver workflow tools.

Never expose arbitrary Python execution, raw PyFluent calls, arbitrary Fluent
TUI commands, arbitrary journal execution, raw source-expression editing,
delete operations, overwrite operations, or direct Fluent launch without a
validated plan and explicit local approval.

The public MCP surface validates solver plans, emits monitor contracts, writes
advisory PyFluent templates, validates resume plans, and can prepare controlled
local execution-adapter inputs. It must not upload or package private CAD,
mesh, `.msh.h5`, `.cas.h5`, `.dat.h5`, license, or local ANSYS installation
files.

When local Fluent execution is enabled by a private workspace adapter, the MCP
surface must keep launch, monitor, resume, and export actions bounded by the
validated plan, recorded runtime configuration, required monitor contract, and
checkpoint rules.

Resume workflows must preserve solver state from a complete checkpoint and
must not run standard initialization. For Fluent 2024 R1 adaptive resumes,
`total_time` is treated as the absolute final flow time.
"""
