# NX Journals

This directory is reserved for NXOpen Python journals.

The scaffold does not execute arbitrary journals. Future journals should read a
validated `fromcad2cfd_nx_job_v1` JSON file and write a JSON result report.

Manual NX journal recordings may be used as local development evidence for
selector-sensitive UI workflows, but recorded journals must not become
agent-facing tools directly. Extract the stable NXOpen pattern, replace
recorded object identifiers with deterministic selectors, preserve inputs, and
wrap the result in a controlled job JSON workflow.
