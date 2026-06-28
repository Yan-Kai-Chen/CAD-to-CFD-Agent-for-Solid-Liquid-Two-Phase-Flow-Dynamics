# Dewaxing Agent Project Tree

Status: `active restructure scaffold`

This page records the intended documentation and artifact tree for the dewaxing
case study. It is a scaffold for GitHub restructuring.

## Documentation Tree

```text
docs/dewaxing_agent/
  README.md
  00_project_tree.md
  01_project_overview.md
  02_evidence_inventory.md
  03_fastfluent_native_solver.md
  04_agent_iteration.md
  05_validation_and_sensitivity.md
  06_fastfluent_to_fluent_guidance.md
  07_paper_figures_and_tables.md
  08_limitations_and_claim_boundaries.md
```

## Existing Source Documents To Consolidate

```text
docs/FASTFLUENT_DEWAXING_NATIVE_SOLVER_PROGRESS_20260627.md
docs/DEWAXING_FASTFLUENT_TO_FLUENT_ASSET_INVENTORY_20260628.md
docs/DEWAXING_AGENT_GITHUB_RESTRUCTURE_HANDOFF_20260628.md
docs/fastcfd/DEWAXING_APPLICATION_BRIDGE.md
```

## Current Real Output Trees

```text
sandbox/output/dewaxing_native_study_real
sandbox/output/dewaxing_native_validation_pack_real
sandbox/output/dewaxing_agent_iteration_pack_real
sandbox/output/dewaxing_paper_evidence_pack_real
sandbox/output/dewaxing_fluent_guidance_pack_real
```

## Public Fixture Tree

```text
examples/postprocessing/dewaxing_result_pack
```

## Public Source And Test Tree

```text
src/fromcad2cfd_fastcfd/dewaxing_native_solver.py
src/fromcad2cfd_fastcfd/dewaxing_native_study.py
src/fromcad2cfd_fastcfd/dewaxing_native_validation_pack.py
src/fromcad2cfd_fastcfd/dewaxing_agent_iteration_pack.py
src/fromcad2cfd_fastcfd/dewaxing_paper_evidence_pack.py
src/fromcad2cfd_fastcfd/dewaxing_fluent_guidance_pack.py
src/fromcad2cfd_fastcfd/dewaxing_application.py
src/fromcad2cfd_postprocessing/dewaxing_result_pack.py
tests/unit/test_fastcfd_dewaxing_*.py
```

These files stay in their current module locations during this restructure.
The case-study documentation references them instead of moving them into a
paper-only tree.

## Required Consistency Rule

Every page should preserve this direction:

```text
Agent/FastFluent guidance first; Fluent confirmation second.
```

The completed Fluent bridge should never be described as the source that chose
FastFluent partitions.
