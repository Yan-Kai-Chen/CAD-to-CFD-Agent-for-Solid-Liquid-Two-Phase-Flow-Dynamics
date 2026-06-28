# FastFluent-To-Fluent Dewaxing Guidance

Status: `active guidance guide`

The guidance pack converts FastFluent reduced-order evidence into a
Fluent-facing validation plan. It is a handoff and prioritization artifact, not
a Fluent launch script.

## Implementation Assets

- `src/fromcad2cfd_fastcfd/dewaxing_fluent_guidance_pack.py`
- `tests/unit/test_fastcfd_dewaxing_fluent_guidance_pack.py`

## Core Outputs

- five process partitions;
- seven Fluent validation targets;
- parameter-priority table;
- reusable asset map;
- workflow figure;
- Fluent handoff brief.

The existing Fluent bridge must be described as retrospective confirmation only.

## Public Command

Use generated public outputs and the sanitized fixture:

```powershell
python -m fromcad2cfd fastcfd compile-dewaxing-fluent-guidance-pack `
  --study-pack sandbox/output/dewaxing_native_study `
  --validation-pack sandbox/output/dewaxing_native_validation_pack `
  --iteration-pack sandbox/output/dewaxing_agent_iteration_pack `
  --fluent-bridge-pack examples/postprocessing/dewaxing_result_pack `
  --output-dir sandbox/output/dewaxing_fluent_guidance_pack `
  --format markdown
```

## Direction Rule

```text
FastFluent computation -> guidance synthesis -> Fluent-facing plan -> paper evidence
```

The bottom confirmation lane can mention existing Fluent evidence, but it must
remain retrospective confirmation and must not feed back into FastFluent
partition selection.
