# Dewaxing Evidence Inventory

Status: `active evidence index`

This page separates public assets from local real evidence.

## Public Assets

- public fixture `examples/postprocessing/dewaxing_result_pack`
- public code under `src/fromcad2cfd_fastcfd/dewaxing_*.py`
- public validator `src/fromcad2cfd_postprocessing/dewaxing_result_pack.py`
- public tests `tests/unit/test_fastcfd_dewaxing_*.py`

These are the assets a public GitHub reader can inspect or run without private
Fluent case/data files.

## Local Real Evidence Families

Project maintainers can regenerate or inspect local real evidence under these
workspace-relative output families:

- `sandbox/output/dewaxing_native_study_real`
- `sandbox/output/dewaxing_native_validation_pack_real`
- `sandbox/output/dewaxing_agent_iteration_pack_real`
- `sandbox/output/dewaxing_paper_evidence_pack_real`
- `sandbox/output/dewaxing_fluent_guidance_pack_real`

These are local evidence records, not required public inputs.

## Evidence Roles

| evidence family | role in the case study |
| --- | --- |
| native study | Runs reduced-order variants and ranks process assumptions. |
| native validation pack | Checks grid and time-step sensitivity before trusting candidate guidance. |
| Agent iteration pack | Records proposals, rejected unstable candidates, and the accepted stable candidate. |
| paper evidence pack | Converts validated evidence into tables, figures, captions, and draft text. |
| Fluent guidance pack | Produces process partitions, Fluent validation targets, and handoff briefs. |
| public fixture | Lets public tests validate the result-pack contract without private data. |

Do not make private local Fluent files required public inputs.
