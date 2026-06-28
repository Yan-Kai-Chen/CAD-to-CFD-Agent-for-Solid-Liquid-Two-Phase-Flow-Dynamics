# Agent Benchmark Ladder Examples

This tree is the public example scaffold for the Agent benchmark ladder.

The directories are placeholders until each benchmark has a public fixture,
commands, and expected outputs.

| directory | benchmark | status |
| --- | --- | --- |
| `01_internal_pipe_or_channel_flow` | internal pipe/channel flow | partial |
| `02_backward_facing_step` | backward-facing step | planned |
| `03_heated_channel_cht_toy_case` | heated channel / CHT toy case | partial |
| `04_cavity_or_enclosure_flow` | cavity / enclosure flow | partial |
| `05_dewaxing_steam_impact_case` | dewaxing-inspired steam impact | application-driving |

Do not place private Fluent case/data files in this tree.

## How Existing Public Examples Are Reused

This tree is a reader-facing scaffold. The original public assets remain in
their engineering locations:

- channel and unstructured mesh assets stay under `examples/fastcfd/` and
  `examples/unstructured/`;
- cavity and C++ numerical assets stay under `cpp/fastfluent_core/`;
- thermal transport utilities stay under `src/fromcad2cfd_fastcfd/`;
- dewaxing public fixture data stays under
  `examples/postprocessing/dewaxing_result_pack/`.

Benchmark README files should point to those assets and add only
benchmark-specific manifests, commands, and expected-output notes when each
case is promoted from placeholder to runnable public benchmark.
