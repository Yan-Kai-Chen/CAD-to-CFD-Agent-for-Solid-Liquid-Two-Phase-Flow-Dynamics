# Execution Gate Demo

This public example exercises the M7 Execution Gate:

```powershell
python -m fromcad2cfd fastcfd execution-gate demo --output-dir sandbox/output/execution_gate_demo
```

The demo creates a public route plan, audits it in dry-run mode, and writes:

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

Execution Gate does not run the commands in the runbook. They are preserved for
explicit review and later approval.
