# Dewaxing Agent Project Overview

Status: `active case-study guide`

The dewaxing application is the complex case study that follows the compact
Agent benchmark ladder.

Working paper title:

```text
An Agent Framework for FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dynamics
```

## Contribution

The case study shows how the Agent uses FastFluent reduced-order calculations
to organize a complex solid-liquid dewaxing workflow before final Fluent-grade
validation. The Agent produces traceable artifacts: native evidence packs,
candidate iteration records, validation and sensitivity summaries, paper tables
and figures, and a Fluent-facing guidance pack.

## Position After The Benchmark Ladder

The benchmark ladder answers whether the Agent framework has general CFD
workflow breadth. The dewaxing case answers whether that framework can handle a
complex engineering application with phase change, heat dose, steam impact,
risk-window selection, and Fluent-facing validation targets.

```text
4 public CFD capability checks
  -> dewaxing-inspired steam-impact bridge
  -> full dewaxing Agent case study
  -> FastFluent-to-Fluent guidance
```

## Public Route

Public readers should start from these assets:

- `docs/agent_benchmark_ladder/README.md`
- `docs/dewaxing_agent/README.md`
- `examples/postprocessing/dewaxing_result_pack/`
- `src/fromcad2cfd_fastcfd/dewaxing_application.py`

The local real evidence packs can be used by project maintainers, but public
tests and public examples must use generated outputs or sanitized fixtures.

## Direction Rule

```text
Agent/FastFluent guidance first; Fluent confirmation second.
```

Completed Fluent evidence is retrospective confirmation or a later validation
layer. It must not be described as the source that selected the FastFluent
process partitions.
