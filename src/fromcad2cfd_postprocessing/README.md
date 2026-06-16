# Post-processing Module

Public-safe Fluent postprocessing helpers.

Implemented scope:

- parse Fluent report-monitor files;
- summarize global pressure, temperature, velocity, species, and inlet-flow metrics;
- summarize wall heat, wall-adjacent temperature, wall pressure, and wall shear;
- write JSON and Markdown reports;
- create video frame plans from autosave file names;
- provide a safe MCP wrapper for monitor parsing and summaries.

Out of scope for this public module:

- direct Fluent GUI automation;
- arbitrary shell or ffmpeg execution;
- committing private case/data files;
- claiming solid structural stress from Fluent pressure or wall shear.
