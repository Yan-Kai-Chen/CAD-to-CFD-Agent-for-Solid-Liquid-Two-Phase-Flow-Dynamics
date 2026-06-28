# Public Asset Framework Map

This document explains how the public assets that already existed in the
GitHub repository are organized inside the current Agent framework.

The restructure does not discard the earlier public repository. It gives each
asset a clear role in the new paper-facing structure:

```text
framework base
  -> four workflow blocks
  -> Agent workflow spine
  -> benchmark ladder
  -> dewaxing case study
  -> legacy evidence and progress records
```

## Canonical Layers

| layer | purpose | canonical public entry |
| --- | --- | --- |
| Framework base | Project identity, install surface, safety policy, contribution rules, tests, and CI. | `README.md`, `pyproject.toml`, `.github/`, `configs/`, `scripts/`, `tests/` |
| Four workflow blocks | Preserve the original public FromCAD2CFD structure: Modeling, FastFluent, Meshing, and Fluent. | `docs/architecture.md`, `docs/index.md` |
| Agent workflow spine | Explain how the Agent moves through contracts, gates, evidence bundles, route plans, result packs, and decisions. | `docs/fastcfd/WORKFLOW_RUNNER.md`, `docs/fastcfd/AGENT_WORKFLOW_STATUS_AUDIT.md` |
| Benchmark ladder | Show general CFD workflow breadth before the dewaxing application. | `docs/agent_benchmark_ladder/README.md`, `examples/fastcfd/agent_benchmark_ladder/` |
| Dewaxing case study | Show complex solid-liquid dewaxing depth and FastFluent-to-Fluent paper evidence. | `docs/dewaxing_agent/README.md`, `examples/postprocessing/dewaxing_result_pack/` |
| Legacy evidence records | Preserve development history, capability snapshots, and milestone reports without making them primary navigation. | dated `docs/FASTFLUENT_*.md` and handoff documents |

## Asset Migration Matrix

| original public asset family | new framework role | action |
| --- | --- | --- |
| `README.md`, root metadata, license files, citation files | Framework base | Keep at root. Update navigation only. |
| `docs/architecture.md`, `docs/index.md` | Four workflow blocks | Keep as the main reader map. Add benchmark and dewaxing links. |
| `src/fromcad2cfd_solidworks/`, `src/fromcad2cfd_nx/`, `src/fromcad2cfd_mesh/` | Modeling block | Keep module ownership unchanged. Link as geometry preparation support. |
| `examples/solidworks/`, `examples/nx/`, `examples/mesh/` | Modeling examples | Keep as public examples. Do not move into benchmark or dewaxing case-study folders. |
| `src/fromcad2cfd_fastcfd/`, `cpp/fastfluent_core/` | FastFluent block and Agent evidence engine | Keep as the core CFD evidence layer. New dewaxing modules remain under this package for now. |
| `docs/fastcfd/CASESPEC_V3.md`, `EVIDENCE_BUNDLE_V3.md`, `FLOW_PACK_ADAPTER.md`, `ROUTE_SELECTOR.md`, `ROUTE_PLAN_COMPILER.md`, `EXECUTION_GATE.md`, `CONTROLLED_RUNNER.md`, `RESULT_PACK_COMPILER.md`, `WORKFLOW_RUNNER.md` | Agent workflow spine | Keep in `docs/fastcfd/`. Treat as method documents for both benchmark and dewaxing routes. |
| `examples/fastcfd/channel2d_scene`, `examples/unstructured/channel2d.msh`, unstructured channel utilities | Benchmark 1: internal channel flow | Reference from `docs/agent_benchmark_ladder/01_internal_pipe_or_channel_flow.md`. Package a benchmark manifest later. |
| cavity routes and `cpp/fastfluent_core` cavity examples | Benchmark 4: cavity/enclosure flow | Reference from `docs/agent_benchmark_ladder/04_cavity_or_enclosure_flow.md`. Keep source assets in place. |
| S6 transport, heat diffusion, material/source-term utilities | Benchmark 3: heated channel / CHT toy case | Reference from `docs/agent_benchmark_ladder/03_heated_channel_cht_toy_case.md`. Add a public fixture later. |
| missing backward-facing-step fixture | Benchmark 2 | Keep as `planned`. Do not fake completed numerical results. |
| `src/fromcad2cfd_fastcfd/dewaxing_*.py` | Dewaxing case study implementation | Keep flat module layout during this transition. Consider subpackage move only after import compatibility tests are added. |
| `src/fromcad2cfd_postprocessing/dewaxing_result_pack.py` and `examples/postprocessing/dewaxing_result_pack/` | Public dewaxing fixture and validation contract | Keep public-safe fixture in examples. Never require private Fluent paths in tests. |
| `docs/FASTFLUENT_*.md`, `docs/DEWAXING_*.md` | Legacy evidence and handoff records | Keep as traceable source material. Summarize into landing pages before any later archiving. |
| `sandbox/output/*`, `05_projects/*`, `06_logs/*` | Local generated evidence | Keep out of the public GitHub source tree unless a small sanitized fixture is deliberately promoted. |

## Navigation Rules

Use these rules when adding or moving public assets:

1. If the asset explains the whole project, link it from `README.md` and
   `docs/index.md`.
2. If the asset belongs to Modeling, FastFluent, Meshing, or Fluent, keep it in
   that module's existing documentation or example tree.
3. If the asset explains Agent decision logic, link it from the Agent workflow
   spine under `docs/fastcfd/`.
4. If the asset proves general CFD workflow breadth, map it into
   `docs/agent_benchmark_ladder/`.
5. If the asset supports the complex dewaxing application, map it into
   `docs/dewaxing_agent/`.
6. If the asset is historical, dated, or progress-oriented, keep it as a legacy
   evidence record and reference it from a newer landing page.
7. Do not move large generated evidence, private case/data files, private CAD,
   or machine-specific runtime outputs into the public repository.

## Acceptance Gates

A public-asset restructure is acceptable only when all of these are true:

- `README.md` exposes the four workflow blocks, benchmark ladder, and dewaxing
  case study.
- `docs/index.md` can route a new reader to framework, benchmark, and dewaxing
  material without reading dated progress files first.
- Each benchmark page states its status as `partial`, `planned`, or
  `application-driving`.
- Dewaxing pages state that FastFluent provides reduced-order guidance and that
  Fluent evidence is retrospective confirmation or later validation.
- Public commands use public fixtures or generated outputs, not private local
  paths.
- Python tests pass after the restructure.

## Current Boundary

The public GitHub repository should look like a maintainable software project
with a paper-facing Agent route. It should not look like a dump of local
simulation outputs.

The local workspace can retain large evidence packs and private Fluent results,
but the public repository keeps only source code, tests, public fixtures,
documentation, and small synthetic examples.
