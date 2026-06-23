# FastFluent Controlled Runner

Controlled Runner is the M8 post-gate execution bookkeeping layer. It consumes
an M7 `execution_gate.json` and writes an auditable execution ledger.

Controlled Runner v1 intentionally does not launch Fluent and does not execute
real FastFluent. It supports:

- `dry_run`: record the command ledger and transcript without solver execution.
- `mock`: execute an existing deterministic mock backend job only when the gate
  references `backend="mock"` and an explicit `approval_id` is provided.

## Public Demo

```powershell
python -m fromcad2cfd fastcfd controlled-runner demo --output-dir sandbox/output/controlled_runner_demo
```

The demo builds the public M7 gate and records an M8 dry-run ledger:

```text
demo_status.json
f/
s/
p/
g/
x/
    controlled_run.json
    command_ledger.json
    execution_transcript.md
```

## Run From Existing Execution Gate

```powershell
python -m fromcad2cfd fastcfd controlled-runner run sandbox/output/execution_gate_demo/g --output-dir sandbox/output/controlled_run
python -m fromcad2cfd fastcfd controlled-runner validate sandbox/output/controlled_run
```

## Boundary

- Real FastFluent execution is blocked in v1.
- Fluent launch is blocked in v1.
- Arbitrary code execution is blocked.
- Real solver execution requires a future explicit adapter and approval route.
