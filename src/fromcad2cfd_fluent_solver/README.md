# Fluent Solver Module

Public-safe Fluent Solver workflow helpers.

Implemented scope:

- validate Fluent Solver plan JSON files;
- expose the required global and wall monitor contract;
- generate advisory PyFluent setup templates;
- validate resume plans and checkpoint guardrails;
- define the contract used by controlled local Fluent execution adapters;
- provide a safe MCP wrapper for the same high-level operations.

Public safety boundary:

- committing private mesh, case, or data files;
- direct Fluent launch without a validated plan and configured local adapter;
- raw PyFluent, TUI, or journal execution as uncontrolled agent tools;
- raw source-expression editing outside reviewed workflow actions.
