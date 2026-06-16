# Fluent Solver Roadmap

Implemented first:

- Public-safe Fluent Solver plan schema.
- Solver plan validation CLI.
- Required global and wall monitor contract.
- Advisory PyFluent template generation.
- Resume-plan validation guardrails.
- Safe Fluent Solver MCP inventory and wrapper.
- Public synthetic solver plan example.

Next:

- Richer boundary-condition schema coverage.
- Material-library contract.
- Source-term model registry with documented parameters.
- Local PyFluent/Fluent execution adapter with explicit runtime configuration,
  checkpoint handling, and monitor supervision.
- Fluent case/data verification helpers for private workspaces.
- Formal run package manifest generation.
