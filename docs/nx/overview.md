# Siemens NX Backend Overview

The Siemens NX backend is planned as the second CAD backend for the framework.
It does not replace the SolidWorks backend. SolidWorks remains the first
validated automation loop, while NX targets advanced engineering CAD workflows,
expression-driven parametric modeling, Parasolid export, and controlled batch
automation through NXOpen journals.

The preferred production route is:

```text
fromcad2cfd CLI or MCP
  -> fromcad2cfd_nx job schema
  -> run_journal.exe
  -> NXOpen Python journal
  -> result.json, reports, STEP or Parasolid export
```

Community MCP projects may be useful for research and tool inventory, but the
framework should integrate stable behavior into its own `fromcad2cfd_nx`
backend and `fromcad2cfd_mcp_nx` safe stdio MCP server.

The current bounded foundation scope is tracked in
`docs/nx/basic_modeling_matrix.md`. Capabilities outside that matrix should be
added as finite packs rather than open-ended raw NXOpen access.

Current reverse-modeling work is tracked in
`docs/nx/reverse_modeling_workflow.md`. When a user-validated NX UI operation
cannot be reproduced from headers or examples alone, use
`docs/nx/manual_journal_capture.md` as the engineer-in-the-loop capture route
and then convert the recorded pattern into a controlled journal.
