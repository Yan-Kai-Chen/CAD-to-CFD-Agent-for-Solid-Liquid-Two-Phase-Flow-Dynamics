# Benchmark 5: Dewaxing-Inspired Steam Impact Case

Status: `application-driving`

## Purpose

Bridge the generic benchmark ladder into the real dewaxing application. This
case focuses on early steam impact, heat dose, wall response, and the first
process partition.

## Current QoIs

- Early time window: `0-4.1 s`.
- Heat dose.
- Shell mean temperature rise.
- Impact impulse.
- Crack-driving proxy.
- Link to full-cycle risk window.

## Existing Evidence

- Local early steam-shock Fluent packages: `21-31` and `34-36`.
- Completed Fluent bridge retained as local project evidence, not a required
  public input.
- Public fixture:

```text
examples/postprocessing/dewaxing_result_pack
```

## Missing Work

- Package a public-safe steam-impact benchmark summary.
- Link early impact evidence to the FastFluent-to-Fluent guidance figure.
- Decide whether this appears in main text as benchmark 5 or as the first
  dewaxing result subsection.

## Paper Role

Application-driving benchmark and transition to the full dewaxing case study.
