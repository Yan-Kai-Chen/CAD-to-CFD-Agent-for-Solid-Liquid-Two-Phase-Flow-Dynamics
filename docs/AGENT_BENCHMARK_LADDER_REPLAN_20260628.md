# Agent Benchmark Ladder Replan

Date: 2026-06-28

This document updates the project memory after deciding to add a compact
benchmark ladder before the dewaxing application. The goal is to make the paper
look like an Agent framework for complex CFD workflows, not a one-off private
dewaxing post-processing exercise.

## Updated Paper Positioning

Final working title:

```text
An Agent Framework for FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dynamics
```

Superseded earlier title option:

```text
An Agent Framework for FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dewaxing Dynamics
```

The final title keeps the paper broad enough for the benchmark ladder and the
dewaxing application while avoiding a single-case-only title.

## New Central Logic

The project should now be presented as:

```text
standard benchmark ladder
    -> Agent workflow reliability and CFD capability checks
    -> FastFluent process partitioning and candidate screening
    -> Fluent-facing handoff and retrospective confirmation
    -> complex solid-liquid dewaxing application
```

This is stronger than a dewaxing-only story because it answers a likely review
question:

```text
Is this Agent framework general enough to support CFD workflows, or was it only
tuned to one private dewaxing example?
```

## Benchmark Strategy

Use a `4+1` benchmark ladder.

The first four cases are compact, public-facing CFD capability benchmarks. They
should not dominate the paper. Their purpose is to prove that the Agent
workflow can build, run, validate, and hand off standard CFD evidence before the
specialized dewaxing case.

The fifth case is the bridge into the real application.

| order | benchmark | role | main check | paper role |
| --- | --- | --- | --- | --- |
| 1 | Internal pipe/channel flow | basic flow and boundary verification | inlet/outlet/wall setup, pressure drop, velocity profile | general capability benchmark |
| 2 | Backward-facing step | separated-flow verification | separation, recirculation, mesh/time sensitivity | general capability benchmark |
| 3 | Heated channel / conjugate heat-transfer toy case | thermal coupling verification | heat boundary, heat dose, solid-fluid or wall thermal interface | general capability benchmark |
| 4 | Cavity / enclosure flow | closed-domain flow verification | recirculation structure, bounded-domain stability | general capability benchmark |
| 5 | Dewaxing-inspired steam impact case | application-driving benchmark | steam impact, heat dose, wall response, early shock partition | transition to dewaxing case study |

## Why This Is Useful

This plan improves the project in three ways:

1. It makes the Agent framework credible beyond a single engineering case.
2. It gives GitHub readers a public, reproducible path before the private local
   dewaxing evidence.
3. It creates a clean paper structure:

```text
Agent architecture
    -> benchmark ladder
    -> dewaxing application
    -> FastFluent-to-Fluent guidance pack
```

## Benchmark Definition Template

Each benchmark should eventually have:

- case name;
- physical purpose;
- Agent role;
- FastFluent route;
- expected outputs;
- Fluent-facing handoff;
- QoIs;
- acceptance checks;
- public fixture status;
- paper placement.

Use this table for initial planning:

| field | required content |
| --- | --- |
| Physics target | what fluid/thermal behavior the benchmark checks |
| Agent task | what the Agent decides, compiles, screens, or reports |
| FastFluent evidence | native solver output, Result Pack, figures, tables |
| Fluent-facing handoff | what would be given to Fluent or compared to Fluent |
| QoIs | measurable outputs, not vague claims |
| Current status | implemented, partial, planned, or not started |
| Paper placement | main text, supplement, or GitHub-only |

## Benchmark 1: Internal Pipe Or Channel Flow

Purpose:

- Check basic incompressible or weakly compressible flow setup.
- Validate wall/inlet/outlet handling.
- Demonstrate that the Agent can extract pressure-drop and velocity-profile
  evidence.

Suggested QoIs:

- pressure drop;
- mean velocity;
- centerline or cross-section velocity profile;
- mass-balance residual;
- mesh/time-step sensitivity label.

Likely existing assets:

- `examples/fastcfd/channel2d_scene`
- `examples/unstructured/channel2d.msh`
- unstructured channel validation tools.

Current status:

```text
partial existing assets, needs benchmark packaging
```

## Benchmark 2: Backward-Facing Step

Purpose:

- Check separated-flow handling.
- Show that the Agent can identify recirculation and mesh sensitivity.

Suggested QoIs:

- reattachment length or proxy;
- recirculation-zone area;
- wall shear sign change;
- pressure recovery;
- grid sensitivity.

Current status:

```text
planned; create public fixture and benchmark definition first
```

## Benchmark 3: Heated Channel / Conjugate Heat-Transfer Toy Case

Purpose:

- Check thermal boundary handling.
- Build a bridge toward dewaxing thermal dose, wall heating, and phase-change
  interpretation.

Suggested QoIs:

- wall heat flux;
- outlet temperature;
- heat dose;
- solid/wall temperature rise;
- energy-balance residual.

Likely existing assets:

- S6 scalar transport routes;
- wax/thermal application code;
- dewaxing early heat-dose concepts.

Current status:

```text
partial existing assets, needs benchmark packaging and public example
```

## Benchmark 4: Cavity / Enclosure Flow

Purpose:

- Check closed-domain flow behavior and bounded-domain stability.
- Provide a simple public example of recirculating flow without inlet/outlet
  ambiguity.

Suggested QoIs:

- vortex center or qualitative recirculation pattern;
- kinetic-energy trend;
- maximum velocity;
- stability flag;
- mesh sensitivity.

Likely existing assets:

- mock cavity2d;
- FastFluent cavity route.

Current status:

```text
partial existing assets, needs benchmark packaging
```

## Benchmark 5: Dewaxing-Inspired Steam Impact Case

Purpose:

- Act as the transition from generic benchmark to application-specific dewaxing.
- Demonstrate early steam impact, heat dose, wall response, and the first
  process partition before the full dewaxing case.

Suggested QoIs:

- early window: `0-4.1 s`;
- heat dose;
- shell mean temperature rise;
- impact impulse;
- crack-driving proxy;
- link to full-cycle risk window.

Existing local evidence:

- early steam-shock packages `21-31` and `34-36`;
- bridge status values in:

```text
D:/CYK2/Fluent/10_Results/32Dewaxing_AgentBridge_W6EarlyShockFullCycle/01_agent_result_pack/dewaxing_result_status.json
```

Current public fixture:

```text
examples/postprocessing/dewaxing_result_pack
```

Current status:

```text
application-driving benchmark has strong local evidence; public fixture and
paper packaging still need cleanup
```

## Updated Paper Structure

Recommended structure:

### 1. Introduction

- Need for Agent support in complex CFD workflows.
- Why direct Fluent exploration is expensive and hard to organize.
- Why standard benchmarks plus dewaxing application provide a stronger
  validation story.

### 2. Agent Framework

- Case specification.
- FastFluent native evidence.
- Result Pack and guidance artifacts.
- Fluent-facing handoff.
- Claim boundaries.

### 3. Benchmark Ladder

- Internal pipe/channel flow.
- Backward-facing step.
- Heated channel / CHT toy case.
- Cavity/enclosure flow.
- Dewaxing-inspired steam impact.

Keep this section concise. The first four can be summary tables plus one or two
figures. Do not let them consume the dewaxing contribution.

### 4. Dewaxing Application

- FastFluent-native dewaxing study.
- Grid/time-step validation.
- Agent iteration and stability rejection.
- FastFluent-to-Fluent guidance pack.
- Retrospective Fluent confirmation.

### 5. Discussion

- Generality from benchmark ladder.
- Application value from dewaxing.
- Limits of reduced-order guidance.
- Future work toward targeted new Fluent validation and experiments.

## Updated GitHub Story

The GitHub repo should expose two connected entry points:

```text
docs/agent_benchmark_ladder/README.md
docs/dewaxing_agent/README.md
```

The first proves framework breadth. The second proves complex application depth.

## Immediate Implementation Plan

Do not rush into coding all benchmarks. First build the project tree and
documentation contract.

Order:

1. Create benchmark-ladder docs.
2. Create benchmark-ladder examples tree with README placeholders.
3. Link the dewaxing application as benchmark 5.
4. Audit which of the first four benchmarks already have reusable code.
5. Implement only one missing benchmark at a time.
6. Keep public fixture data separate from local private evidence.

## Acceptance Criteria For This Replan

The replan is accepted when:

- There is a clear `4+1` benchmark ladder in docs.
- The workflow still emphasizes Agent as the framework, not a passive wrapper.
- Dewaxing remains the main complex application.
- Public GitHub users can see which benchmarks are done, partial, or planned.
- The incomplete benchmark directories exist as a project tree but do not
  falsely claim completed results.
- No new Fluent execution is required.

## Memory Update Summary

From now on, describe the project as:

```text
An Agent framework for FastFluent-to-Fluent CFD workflows, validated through a
compact benchmark ladder and demonstrated on complex solid-liquid dewaxing
dynamics.
```

Do not describe it as only a dewaxing post-processing project.
