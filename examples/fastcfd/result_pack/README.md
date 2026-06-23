# Result Pack Demo

This public example exercises the M9 Result Pack Compiler:

```powershell
python -m fromcad2cfd fastcfd result-pack demo --output-dir sandbox/output/result_pack_demo
```

The demo compiles an agent-facing decision package from a dry-run Controlled
Runner output.

```text
demo_status.json
r/
    result_pack.json
    decision_brief.md
    artifact_index.json
    agent_handoff.json
```
