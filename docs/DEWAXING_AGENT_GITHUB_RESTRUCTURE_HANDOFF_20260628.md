# Agent Benchmark And Dewaxing GitHub Restructure Handoff

Date: 2026-06-28

This document is written for the next Codex session that will help restructure
the GitHub project. It should be treated as the current project brief, not as a
final paper draft.

Important update: the project is no longer framed as a dewaxing-only case. The
current plan is a compact Agent benchmark ladder followed by the complex
solid-liquid dewaxing application.

## Final Working Paper Title

Current final working title after the benchmark-ladder replan:

```text
An Agent Framework for FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dynamics
```

Superseded narrower fallback title:

```text
An Agent Framework for FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dewaxing Dynamics
```

Why this title is preferred:

- It directly emphasizes `Agent` as the core method.
- It preserves the correct workflow direction: `FastFluent-to-Fluent`.
- It creates room for standard benchmark evidence.
- It anchors the paper in a complex fluid mechanics application:
  solid-liquid phase-change dewaxing.
- It avoids overclaiming full autonomy or Fluent replacement.

## Core Thesis

The project is not simply a Fluent post-processing study, and it should not be
presented as a single private dewaxing example.

The intended scientific and engineering story is:

```text
Agent framework is checked on a compact CFD benchmark ladder
    -> Agent + FastFluent computes reduced-order dewaxing evidence
    -> Agent partitions the complex dewaxing process into actionable blocks
    -> Agent ranks parameters and candidate assumptions
    -> Agent produces a Fluent-facing validation plan
    -> completed Fluent results retrospectively confirm that the selected
       windows and quantities are physically meaningful
```

Do not reverse this logic. Completed Fluent results are not the reason the
FastFluent partitions were selected. They are used as retrospective confirmation
because the Fluent calculations were already completed locally.

## Non-Negotiable Boundaries

- Do not run ANSYS Fluent.
- Do not call PyFluent.
- Do not compile UDFs.
- Do not edit Fluent case/data files.
- Do not present FastFluent as a replacement for final Fluent validation.
- Do not convert pressure-risk or shell-stress proxies into calibrated crack
  probability.
- Do not claim accepted reduced-order edits are measured physical geometry or
  material changes unless independent evidence is added.
- Do not expose private local Fluent case/data files in the public GitHub repo.

FastFluent-native reduced-order calculations can still be used or rerun if
needed, but the immediate restructure task should focus on organization,
documentation, reproducibility, and paper-facing assets.

## Benchmark Ladder Replan

Adopt a `4+1` benchmark ladder.

| order | benchmark | role | current status |
| --- | --- | --- | --- |
| 1 | Internal pipe/channel flow | basic boundary, pressure-drop, velocity-profile check | partial existing assets |
| 2 | Backward-facing step | separation, recirculation, mesh sensitivity | planned |
| 3 | Heated channel / CHT toy case | heat boundary, heat dose, solid-wall thermal interface | partial existing assets |
| 4 | Cavity / enclosure flow | closed-domain recirculation and stability | partial existing assets |
| 5 | Dewaxing-inspired steam impact | application-driving bridge to the dewaxing case | strong local evidence, public packaging needed |

The first four benchmarks establish general CFD workflow credibility. They
should be compact and public-facing. The fifth benchmark is the transition into
the real dewaxing application.

Primary memory document:

```text
docs/AGENT_BENCHMARK_LADDER_REPLAN_20260628.md
```

## Current Evidence State

### Completed Fluent Bridge Evidence

Local source:

```text
D:/CYK2/Fluent/10_Results/32Dewaxing_AgentBridge_W6EarlyShockFullCycle/01_agent_result_pack/dewaxing_result_status.json
```

Key values:

| item | value |
| --- | --- |
| Early stage | `0-4.1 s` |
| Early cases | `6` |
| Max early crack-driving index over 3.6 MPa | `0.014666` |
| Max heat dose | `31.602 kJ/m2` |
| Max shell mean rise | `1.804 C` |
| Max impact impulse | `27.911 N s` |
| Full cycle | `0-420 s` |
| First full melt | `409.0 s` |
| Latest average liquid fraction | `0.997398` |
| Dominant risk window | `100.7 s` |
| Peak effective pressure | `4.465776 MPa` |
| Peak wall VM P99.5 | `42.451535 MPa` |
| Late pressure/stress drop | `94.19%` |

Use these values as retrospective high-fidelity confirmation only.

### FastFluent Native Study

Real local output:

```text
sandbox/output/dewaxing_native_study_real
```

Important files:

- `study_manifest.json`
- `variant_summary.csv`
- `variant_summary.json`
- `sensitivity_summary.json`
- `dewaxing_guidance.json`
- `study_report.md`

Current result summary:

- Native runs: `15`.
- Best reduced-order agreement case: `shell_thin`.
- Closest full-melt case: `wax_layer_thick`.
- Closest risk-window case: `baseline`.
- Lowest early shell-stress proxy: `htc_low`.
- Full-melt timing is most sensitive to `steam_boundary_temperature_K`.
- Risk-window timing is most sensitive to `initial_temperature_K`.
- Early shell-stress proxy is most sensitive to `steam_boundary_temperature_K`.

### FastFluent Native Validation

Real local output:

```text
sandbox/output/dewaxing_native_validation_pack_real
```

Important files:

- `validation_pack_manifest.json`
- `convergence_summary.csv`
- `convergence_summary.json`
- `qoi_stability.json`
- `paper_tables.md`
- `study_interpretation.md`
- `agent_validation_decision.json`

Current result summary:

- Validation cases: `10`.
- Native cell-time steps: `20,525,400`.
- Quality status: `passed`.
- Recommended target: `shell_thin`.

### FastFluent Agent Iteration

Real local output:

```text
sandbox/output/dewaxing_agent_iteration_pack_real
```

Important files:

- `agent_iteration_manifest.json`
- `candidate_summary.csv`
- `candidate_summary.json`
- `round_trace.json`
- `agent_decision.json`
- `iteration_report.md`

Current result summary:

- Rounds: `3`.
- Candidates: `16`.
- Validation targets checked: `6`.
- Native solver runs: `46`.
- Native cell-time steps: `80,140,200`.
- Best unvalidated candidate: `path110_initial8`.
- Accepted stable candidate: `path106_initial6`.
- Rejected during stability review: `5` fitted candidates.
- Accepted edits:
  - `domain.thickness_m` scale `1.06`
  - `initial.temperature_K` offset `+6.0`
- Accepted candidate current-grid values:
  - full-melt time: `386.8 s`
  - risk time: `102.21 s`
  - full-melt error: `5.428%`
  - risk-time error: `1.499%`
- Objective improvement:
  - vs baseline: `46.099%`
  - vs `shell_thin`: `34.364%`

### Paper Evidence Pack

Real local output:

```text
sandbox/output/dewaxing_paper_evidence_pack_real
```

Important artifacts:

- `paper_evidence_manifest.json`
- `agent_paper_claims.json`
- `paper_evidence_report.md`
- `sections/results_section.md`
- `sections/methods_section.md`
- `sections/figure_captions.md`
- six CSV/Markdown tables
- seven SVG figures

Figure style:

```text
nature_soft_statistical
```

Palette:

- `#6F91AA`
- `#9FB9CE`
- `#DFAFC0`
- `#B8738E`
- white background
- Arial text
- thin axes and weak pink-gray grid lines

### FastFluent-to-Fluent Guidance Pack

Real local output:

```text
sandbox/output/dewaxing_fluent_guidance_pack_real
```

Important artifacts:

- `guidance_manifest.json`
- `fluent_guidance_report.md`
- `fluent_handoff_brief.md`
- `figures/figure_01_fastfluent_guided_fluent_workflow.svg`
- `figures/figure_01_fastfluent_guided_fluent_workflow_preview.png`
- `sections/paper_outline.md`
- `sections/methods_guidance_section.md`
- `sections/results_guidance_section.md`
- `sections/workflow_figure_notes.md`
- `tables/table_01_process_partition_guidance.md`
- `tables/table_02_fluent_validation_targets.md`
- `tables/table_03_parameter_priority.md`
- `tables/table_04_existing_asset_reuse_map.md`

Current guidance summary:

- Process partitions: `5`.
- Fluent validation targets: `7`.
- Accepted candidate: `path106_initial6`.
- Figure count: `1`.
- Main workflow figure:

```text
FastFluent computation -> guidance synthesis -> Fluent-facing plan -> paper evidence
```

Bottom confirmation lane:

```text
Existing Fluent bridge: retrospective confirmation layer,
not the partition-selection source
```

## Current Code Assets

Key implementation files:

```text
src/fromcad2cfd_fastcfd/dewaxing_native_solver.py
src/fromcad2cfd_fastcfd/dewaxing_native_study.py
src/fromcad2cfd_fastcfd/dewaxing_native_validation_pack.py
src/fromcad2cfd_fastcfd/dewaxing_agent_iteration_pack.py
src/fromcad2cfd_fastcfd/dewaxing_paper_evidence_pack.py
src/fromcad2cfd_fastcfd/dewaxing_fluent_guidance_pack.py
src/fromcad2cfd_fastcfd/dewaxing_application.py
src/fromcad2cfd_fastcfd/cli.py
src/fromcad2cfd_fastcfd/__init__.py
```

Key tests:

```text
tests/unit/test_fastcfd_dewaxing_native_solver.py
tests/unit/test_fastcfd_dewaxing_native_study.py
tests/unit/test_fastcfd_dewaxing_native_validation_pack.py
tests/unit/test_fastcfd_dewaxing_agent_iteration_pack.py
tests/unit/test_fastcfd_dewaxing_paper_evidence_pack.py
tests/unit/test_fastcfd_dewaxing_fluent_guidance_pack.py
tests/unit/test_fastcfd_dewaxing_application.py
```

Current focused validation:

```powershell
$env:PYTHONPATH='src'
$files = Get-ChildItem tests\unit -Filter 'test_fastcfd_dewaxing*.py' | ForEach-Object { $_.FullName }
python -m pytest $files -q
```

Expected current result:

```text
20 passed
```

## Current CLI Commands

Run native solver:

```powershell
$env:PYTHONPATH='src'
python -m fromcad2cfd fastcfd run-dewaxing-native-solver `
  --output-dir sandbox/output/dewaxing_native_solver `
  --format markdown
```

Run native study:

```powershell
$env:PYTHONPATH='src'
python -m fromcad2cfd fastcfd run-dewaxing-native-study `
  --output-dir sandbox/output/dewaxing_native_study `
  --format markdown
```

Run Agent iteration:

```powershell
$env:PYTHONPATH='src'
python -m fromcad2cfd fastcfd run-dewaxing-agent-iteration-pack `
  --output-dir sandbox/output/dewaxing_agent_iteration_pack `
  --format markdown
```

Run native validation:

```powershell
$env:PYTHONPATH='src'
python -m fromcad2cfd fastcfd run-dewaxing-native-validation-pack `
  --output-dir sandbox/output/dewaxing_native_validation_pack `
  --profile standard `
  --format markdown
```

Compile paper evidence pack:

```powershell
$env:PYTHONPATH='src'
python -m fromcad2cfd fastcfd compile-dewaxing-paper-evidence-pack `
  --validation-pack sandbox/output/dewaxing_native_validation_pack_real `
  --iteration-pack sandbox/output/dewaxing_agent_iteration_pack_real `
  --output-dir sandbox/output/dewaxing_paper_evidence_pack_real `
  --format markdown
```

Compile FastFluent-to-Fluent guidance pack:

```powershell
$env:PYTHONPATH='src'
python -m fromcad2cfd fastcfd compile-dewaxing-fluent-guidance-pack `
  --study-pack sandbox/output/dewaxing_native_study_real `
  --validation-pack sandbox/output/dewaxing_native_validation_pack_real `
  --iteration-pack sandbox/output/dewaxing_agent_iteration_pack_real `
  --fluent-bridge-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --output-dir sandbox/output/dewaxing_fluent_guidance_pack_real `
  --manuscript-title "FastFluent-Guided Fluent Dewaxing Workflow" `
  --format markdown
```

For GitHub/public examples, do not rely on the private local Fluent bridge path.
Use `examples/postprocessing/dewaxing_result_pack` or a sanitized fixture.

## GitHub Restructure Goal

The next Codex should restructure the GitHub project so that a reader can
understand the Agent benchmark ladder and the dewaxing application workflow
without reading internal chat history or private local result folders.

The repo should communicate four layers:

1. General FromCAD2CFD / FastFluent framework.
2. Compact Agent CFD benchmark ladder.
3. Dewaxing Agent case study.
4. Paper-facing FastFluent-to-Fluent evidence chain.

## Recommended Public Project Tree

Build this tree first, even if some benchmark cases remain placeholders:

```text
docs/
  agent_benchmark_ladder/
    README.md
    01_internal_pipe_or_channel_flow.md
    02_backward_facing_step.md
    03_heated_channel_cht_toy_case.md
    04_cavity_or_enclosure_flow.md
    05_dewaxing_steam_impact_case.md
  dewaxing_agent/
    README.md
    01_project_overview.md
    02_evidence_inventory.md
    03_fastfluent_native_solver.md
    04_agent_iteration.md
    05_validation_and_sensitivity.md
    06_fastfluent_to_fluent_guidance.md
    07_paper_figures_and_tables.md
    08_limitations_and_claim_boundaries.md

examples/
  fastcfd/
    agent_benchmark_ladder/
      README.md
      01_internal_pipe_or_channel_flow/
        README.md
      02_backward_facing_step/
        README.md
      03_heated_channel_cht_toy_case/
        README.md
      04_cavity_or_enclosure_flow/
        README.md
      05_dewaxing_steam_impact_case/
        README.md
```

The placeholder READMEs must clearly label each benchmark as `partial`,
`planned`, or `application-driving`. Do not claim that planned benchmarks have
completed numerical results.

## Recommended Restructure Plan

### Phase 1: Stabilize Project Narrative

Tasks:

- Update the README top-level description so the Agent benchmark ladder and the
  dewaxing application are visible but do not overwhelm the general project.
- Add a short "Agent Benchmark Ladder" section with:
  - the `4+1` benchmark list;
  - current completion status;
  - link to `docs/agent_benchmark_ladder/README.md`.
- Add a short "Dewaxing Agent Case Study" section with:
  - working paper title;
  - one-sentence contribution;
  - workflow figure;
  - command to regenerate the guidance pack;
  - link to detailed docs.
- Keep the central logic explicit:

```text
Agent/FastFluent guidance first; Fluent confirmation second.
```

Acceptance criteria:

- A new reader can locate both the benchmark ladder and the dewaxing Agent case
  from README in less than one minute.
- README does not claim final Fluent automation or full CFD replacement.
- The workflow figure is reachable from README or docs.

### Phase 2: Organize Benchmark Documentation

Proposed documentation structure:

```text
docs/
  agent_benchmark_ladder/
    README.md
    01_internal_pipe_or_channel_flow.md
    02_backward_facing_step.md
    03_heated_channel_cht_toy_case.md
    04_cavity_or_enclosure_flow.md
    05_dewaxing_steam_impact_case.md
```

Acceptance criteria:

- The benchmark ladder clearly states the role of each benchmark.
- Each benchmark has a current status.
- The first four benchmarks are positioned as compact public capability checks.
- The fifth benchmark is positioned as the bridge into dewaxing.

### Phase 3: Organize Dewaxing Documentation

Proposed documentation structure:

```text
docs/
  dewaxing_agent/
    README.md
    01_project_overview.md
    02_evidence_inventory.md
    03_fastfluent_native_solver.md
    04_agent_iteration.md
    05_validation_and_sensitivity.md
    06_fastfluent_to_fluent_guidance.md
    07_paper_figures_and_tables.md
    08_limitations_and_claim_boundaries.md
```

Move or link from current docs:

- `docs/FASTFLUENT_DEWAXING_NATIVE_SOLVER_PROGRESS_20260627.md`
- `docs/DEWAXING_FASTFLUENT_TO_FLUENT_ASSET_INVENTORY_20260628.md`
- `docs/fastcfd/DEWAXING_APPLICATION_BRIDGE.md`
- this handoff file

Do not delete old docs until the new structure is validated. Prefer adding an
index first, then consolidate.

Acceptance criteria:

- There is a single dewaxing Agent landing page.
- Each page has a clear role and does not duplicate the same long command list.
- The project logic is consistent across all docs.

### Phase 4: Separate Public Fixtures from Private Results

Tasks:

- Audit `examples/postprocessing/dewaxing_result_pack`.
- Confirm it contains only sanitized, public-safe data.
- Add or update a README explaining that it is a fixture for public tests and
  does not expose private Fluent case/data files.
- Ensure `sandbox/output/*_real` is treated as local generated output, not a
  required committed artifact unless explicitly intended.
- Check `.gitignore` for generated outputs and private Fluent files.

Acceptance criteria:

- Public tests do not depend on `D:/CYK2/Fluent/10_Results/...`.
- The real local output paths appear only in local progress docs or handoff
  notes, not as required public inputs.
- The CLI examples have a public path variant.

### Phase 5: Refactor Code Organization Carefully

Current dewaxing modules are flat under:

```text
src/fromcad2cfd_fastcfd/
```

Potential future structure:

```text
src/fromcad2cfd_fastcfd/dewaxing/
  __init__.py
  native_solver.py
  native_study.py
  native_validation_pack.py
  agent_iteration_pack.py
  paper_evidence_pack.py
  fluent_guidance_pack.py
  application_bridge.py
```

Important caution:

- Do not move files before tests are in place and imports are mapped.
- If moving modules, preserve backwards-compatible imports from the old module
  names for at least one transition step.
- Keep CLI command names stable.

Recommended first step:

- Add a `docs/dewaxing_agent/README.md` and improve public docs before moving
  Python files.

Acceptance criteria:

- `python -m pytest tests/unit/test_fastcfd_dewaxing*.py -q` still passes.
- `fromcad2cfd_fastcfd.compile_dewaxing_fluent_guidance_pack` still imports.
- Existing CLI commands still work.

### Phase 6: Make Paper Assets Reproducible

Tasks:

- Add a reproducibility page with exact commands.
- Add a small public fixture route that regenerates:
  - paper evidence pack;
  - guidance pack;
  - workflow figure.
- Keep real local output values in a clearly marked "local evidence" section.
- Consider adding a `scripts/` or `examples/dewaxing_agent/` command wrapper
  only if it reduces confusion.

Possible public command:

```powershell
$env:PYTHONPATH='src'
python -m fromcad2cfd fastcfd compile-dewaxing-fluent-guidance-pack `
  --study-pack sandbox/output/dewaxing_native_study `
  --validation-pack sandbox/output/dewaxing_native_validation_pack `
  --iteration-pack sandbox/output/dewaxing_agent_iteration_pack `
  --fluent-bridge-pack examples/postprocessing/dewaxing_result_pack `
  --output-dir sandbox/output/dewaxing_fluent_guidance_pack `
  --format markdown
```

Acceptance criteria:

- A public user can run a lightweight version without private Fluent assets.
- A local researcher can regenerate the real evidence pack using local real
  paths.
- The workflow figure remains consistent with the guidance tables.

### Phase 7: Align Tests With The Story

Current important focused suite:

```text
20 passed
```

Keep or add tests that check:

- no Fluent launch flags remain false in compilers;
- guidance pack emits five process partitions;
- guidance pack emits seven Fluent validation targets;
- workflow figure contains the phrase `retrospective confirmation layer`;
- accepted candidate remains `path106_initial6` for the real/local evidence
  path or synthetic fixture;
- paper evidence pack emits tables and figures with `nature_soft_statistical`
  style.

Acceptance criteria:

- Tests validate the workflow direction, not just file existence.
- New tests do not require private Fluent case/data files.

## Proposed Paper Structure

Use this as the paper scaffold:

### 1. Introduction

Problem:

- Complex CFD workflows need reproducible Agent support before expensive
  high-fidelity solver use.
- Complex dewaxing involves short early steam shock, longer phase-change
  melting, drainage, pressure retention, and shell-risk response.
- Full high-fidelity exploration in Fluent is expensive and hard to organize.

Contribution:

- An Agent framework checked on a compact benchmark ladder and then applied to
  complex solid-liquid dewaxing.
- FastFluent reduced-order computation partitions the dewaxing process, ranks
  parameters, and generates a targeted Fluent validation plan.

### 2. Method

Subsections:

- Agent workflow architecture.
- Benchmark ladder design.
- FastFluent-to-Fluent handoff contract.
- FastFluent-native dewaxing reduced-order model.
- Process partitioning:
  - P1 early steam shock;
  - P2 dominant risk window;
  - P3 melt/drainage;
  - P4 full-melt completion;
  - P5 candidate handoff.
- Agent candidate iteration and stability rejection.
- FastFluent-to-Fluent guidance pack generation.

### 3. Results

Subsections:

- Agent benchmark ladder results.
- Workflow overview figure.
- Native study and sensitivity results.
- Agent iteration and accepted candidate.
- Grid/time-step sensitivity of risk-time and shell-stress proxies.
- Fluent-facing target plan.
- Retrospective confirmation with completed Fluent results.

### 4. Discussion

Emphasize:

- The innovation is not replacing Fluent.
- The innovation is making expensive Fluent validation more directed.
- The benchmark ladder supports general workflow credibility.
- The dewaxing case demonstrates complex application value.
- The Agent provides a reproducible decision trail: manifests, tables, figures,
  and claim boundaries.

### 5. Limitations

State clearly:

- FastFluent is reduced-order guidance.
- Fluent or experiments remain needed for final CFD validation.
- Current structural risk metrics are proxies, not calibrated failure
  probabilities.
- Accepted parameter edits are reduced-order assumptions, not measured physical
  changes.

## Current Figure Strategy

Use the `nature_soft_statistical` style for:

- workflow figures;
- statistical comparison figures;
- candidate ranking figures;
- stability spread figures;
- compute-load figures.

Reserve high-contrast contour palettes for:

- scalar fields;
- Fluent contours;
- temperature/liquid-fraction maps.

Current primary workflow figure:

```text
sandbox/output/dewaxing_fluent_guidance_pack_real/figures/figure_01_fastfluent_guided_fluent_workflow.svg
```

Preview:

```text
sandbox/output/dewaxing_fluent_guidance_pack_real/figures/figure_01_fastfluent_guided_fluent_workflow_preview.png
```

Design intent:

- solid arrows: Agent/FastFluent guidance direction;
- dashed bottom lane: existing Fluent retrospective confirmation;
- no upward feedback arrow from Fluent to FastFluent partition selection.

## Known Weak Points To Improve

These are the main areas where the project still needs work:

1. The public GitHub story is still spread across many progress docs.
2. The dewaxing modules are implemented but not yet organized as a clean
   case-study package.
3. Public fixtures and real local outputs need clearer separation.
4. The paper narrative still needs conversion from evidence packs into a clean
   manuscript outline with figure/table ordering.
5. The workflow figure is a strong baseline, but later paper polishing should
   refine visual spacing, labels, and journal-specific figure sizing.
6. The Agent's role should be stated as framework/decision layer, not only as
   "guided" wording.
7. The current GitHub README mentions many capabilities; the dewaxing case
   should be discoverable without making the whole project look like a single
   application-only repo.

## Immediate Next Tasks For The Next Codex

Recommended order:

1. Read this document.
2. Read:

```text
docs/AGENT_BENCHMARK_LADDER_REPLAN_20260628.md
docs/DEWAXING_FASTFLUENT_TO_FLUENT_ASSET_INVENTORY_20260628.md
docs/fastcfd/DEWAXING_APPLICATION_BRIDGE.md
src/fromcad2cfd_fastcfd/dewaxing_fluent_guidance_pack.py
tests/unit/test_fastcfd_dewaxing_fluent_guidance_pack.py
```

3. Run focused tests:

```powershell
$env:PYTHONPATH='src'
$files = Get-ChildItem tests\unit -Filter 'test_fastcfd_dewaxing*.py' | ForEach-Object { $_.FullName }
python -m pytest $files -q
```

4. Build a new docs landing page:

```text
docs/agent_benchmark_ladder/README.md
docs/dewaxing_agent/README.md
```

5. Build placeholder docs/examples tree for the five benchmarks.
6. Link the workflow figure and guidance pack from the dewaxing landing page.
7. Update top-level README with concise links to the benchmark ladder and case
   study.
8. Check that public commands use public fixtures, not private local paths.
9. Only after docs are stable, consider moving dewaxing Python modules into a
   subpackage.

## Definition Of Done For GitHub Restructure

The restructure is good enough when:

- The top-level README explains the Agent benchmark ladder and dewaxing case in
  concise sections.
- A dedicated `docs/agent_benchmark_ladder/README.md` exists.
- A dedicated `docs/dewaxing_agent/README.md` exists.
- The FastFluent-to-Fluent direction is stated consistently everywhere.
- The workflow figure is visible from the docs.
- Public commands do not require private paths.
- The focused dewaxing test suite passes.
- No Fluent run is required for any public test or documentation example.
- Claim boundaries are explicit and conservative.

## Final Reminder

The central paper message is:

```text
An Agent framework is checked through a compact CFD benchmark ladder, then uses
FastFluent reduced-order computation to make complex solid-liquid dewaxing
simulation tractable, organized, and Fluent-facing. Completed Fluent results
then confirm that the Agent-selected windows and targets correspond to
meaningful high-fidelity events.
```

Keep this sentence aligned across code, docs, README, figures, and paper drafts.
