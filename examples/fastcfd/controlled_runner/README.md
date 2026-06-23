# Controlled Runner Demo

This public example exercises the M8 Controlled Runner:

```powershell
python -m fromcad2cfd fastcfd controlled-runner demo --output-dir sandbox/output/controlled_runner_demo
```

The demo records a dry-run execution ledger from a public Execution Gate. It
does not run a real solver.

```text
demo_status.json
x/
    controlled_run.json
    command_ledger.json
    execution_transcript.md
```
