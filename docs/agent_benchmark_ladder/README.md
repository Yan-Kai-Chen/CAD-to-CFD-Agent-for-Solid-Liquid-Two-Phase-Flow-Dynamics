# Agent Benchmark Ladder

This directory defines the compact benchmark ladder for the Agent
FastFluent-to-Fluent workflow. The ladder is intentionally small: it should
establish general CFD workflow credibility without taking over the dewaxing
application paper.

## Current 4+1 Ladder

| order | benchmark | role | status |
| --- | --- | --- | --- |
| 1 | Internal pipe/channel flow | inlet/outlet/wall, pressure-drop, velocity-profile check | partial |
| 2 | Backward-facing step | separation, recirculation, mesh sensitivity | planned |
| 3 | Heated channel / CHT toy case | heat boundary, heat dose, wall/solid thermal interface | partial |
| 4 | Cavity / enclosure flow | closed-domain recirculation and stability | partial |
| 5 | Dewaxing-inspired steam impact | application bridge into dewaxing | application-driving |

## How To Read This Directory

- The first four benchmarks are public capability checks.
- The fifth benchmark links the public benchmark ladder to the real dewaxing
  application.
- Placeholder pages are allowed, but they must be honest about completion
  status.
- No page in this directory should require private Fluent case/data files.

## Source Asset Mapping

The benchmark ladder reuses original public GitHub assets instead of moving
them out of their engineering modules.

| benchmark | reused public assets | current action |
| --- | --- | --- |
| Internal pipe/channel flow | `examples/fastcfd/channel2d_scene`, `examples/unstructured/channel2d.msh`, unstructured channel utilities | Package as a public benchmark route. |
| Backward-facing step | none complete yet | Keep planned until a public fixture exists. |
| Heated channel / CHT toy case | S6 transport, heat diffusion, material/source-term utilities | Package a thermal public fixture later. |
| Cavity / enclosure flow | cavity routes and `cpp/fastfluent_core` cavity examples | Package as a closed-domain benchmark route. |
| Dewaxing steam impact | dewaxing public fixture and FastFluent dewaxing modules | Bridge from benchmark ladder into case study. |

The detailed repository-wide mapping is in
`docs/public_asset_framework_map.md`.

## Related Documents

- `docs/public_asset_framework_map.md`
- `docs/AGENT_BENCHMARK_LADDER_REPLAN_20260628.md`
- `docs/dewaxing_agent/README.md`
- `docs/DEWAXING_AGENT_GITHUB_RESTRUCTURE_HANDOFF_20260628.md`

## Acceptance Rule

The benchmark ladder supports the Agent framework. It does not replace the
dewaxing application or claim final CFD validation.
