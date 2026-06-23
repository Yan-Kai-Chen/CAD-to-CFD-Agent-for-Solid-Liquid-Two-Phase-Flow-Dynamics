# FastFluent Result Pack Compiler

Result Pack Compiler is the agent-facing packaging layer. It consumes either
an M8 `controlled_run.json` or a native FastFluent result such as `status.json`,
`case_status.json`, `qs_summary.json`, or `mo_summary.json`, then writes a
compact package for downstream agent decisions.

It labels evidence explicitly:

- `no_solver_evidence`: dry-run only; useful for workflow review, not physics.
- `workflow_fixture`: deterministic mock route; useful for plumbing checks, not
  numerical CFD claims.
- `native_advisory`: reviewed native evidence; still not final Fluent
  validation.
- `degraded_native_advisory`: native evidence completed but quality is warning;
  use for screening only before repair or Fluent handoff.
- `blocked_native_advisory`: native evidence failed or should not be trusted.

## Public Demo

```powershell
python -m fromcad2cfd fastcfd result-pack demo --output-dir sandbox/output/result_pack_demo
```

The demo builds the public M8 dry-run package and compiles:

```text
demo_status.json
r/
    result_pack.json
    decision_brief.md
    artifact_index.json
    agent_handoff.json
```

## Compile From Existing Controlled Run

```powershell
python -m fromcad2cfd fastcfd result-pack compile sandbox/output/controlled_runner_demo/x --output-dir sandbox/output/result_pack
python -m fromcad2cfd fastcfd result-pack validate sandbox/output/result_pack
```

## Compile From Native Result

```powershell
python -m fromcad2cfd fastcfd result-pack compile-native sandbox/output/steady/status.json --output-dir sandbox/output/native_result_pack
python -m fromcad2cfd fastcfd result-pack compile-native sandbox/output/quasi_steady_motion/qs_summary.json --output-dir sandbox/output/quasi_result_pack
python -m fromcad2cfd fastcfd result-pack compile-native sandbox/output/moving_obstacle_demo/mo_summary.json --output-dir sandbox/output/moving_obstacle_result_pack
python -m fromcad2cfd fastcfd result-pack validate sandbox/output/native_result_pack
```

Native compilation writes:

```text
result_pack.json
native_result_summary.json
decision_brief.md
artifact_index.json
agent_handoff.json
```

The pack preserves both execution `status` and solver-quality
`quality_status`. A route can complete with `status=success` while still
returning `quality_status=warning`; in that case the pack recommends
screening-only use and repair before Fluent handoff.

## Boundary

Result Pack v1 is valid for agent workflow control. It does not certify final
CFD correctness and must not be treated as a Fluent replacement.
