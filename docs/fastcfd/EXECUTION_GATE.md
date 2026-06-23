# FastFluent Execution Gate

Execution Gate is the M7 dry-run audit layer. It reads an M6 Route Plan and
writes an execution package for review before any controlled solver run.

It does not run FastFluent, Fluent, PyFluent, UDFs, shell scripts, or arbitrary
Python code.

## Public Demo

```powershell
python -m fromcad2cfd fastcfd execution-gate demo --output-dir sandbox/output/execution_gate_demo
```

The demo builds a public route plan and audits it. It writes:

```text
demo_status.json
f/
s/
p/
g/
    execution_gate.json
    dry_run_ledger.json
    preflight.json
    runbook.md
```

## Audit An Existing Route Plan

```powershell
python -m fromcad2cfd fastcfd execution-gate audit sandbox/output/route_plan_demo/p --output-dir sandbox/output/execution_gate
python -m fromcad2cfd fastcfd execution-gate validate sandbox/output/execution_gate
```

The input can be either a directory containing `route_plan.json` or the file
itself.

## What It Checks

- route-plan structural validation
- approval-gate status
- materialized job existence
- existing FastCFD physics-passport validation
- optional FastFluent source/build preflight
- commands that may be run later only after explicit approval

## Output Semantics

- `ready_for_approval`: artifacts are structurally ready; commands are still not
  executed.
- `review_only`: the route is reviewable but not executable through the current
  gate.
- `blocked`: at least one blocking error exists.

## Boundary

Execution Gate v1 is dry-run only. Commands are copied into `runbook.md` and
`dry_run_ledger.json`, but the gate never runs them.
