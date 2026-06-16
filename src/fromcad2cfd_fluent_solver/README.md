# Fluent Solver Module

Public-safe Fluent Solver planning helpers.

Implemented scope:

- validate Fluent Solver plan JSON files;
- expose the required global and wall monitor contract;
- generate advisory PyFluent setup templates;
- validate resume plans and checkpoint guardrails;
- provide a safe MCP wrapper for the same high-level operations.

Out of scope for this public module:

- committing private mesh, case, or data files;
- direct Fluent launch by default;
- raw PyFluent, TUI, or journal execution;
- raw source-expression editing.
