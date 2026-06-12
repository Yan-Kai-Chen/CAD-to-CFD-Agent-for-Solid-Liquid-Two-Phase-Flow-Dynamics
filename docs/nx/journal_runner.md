# NX Journal Runner

Siemens NX automation should use NXOpen journals as the stable local execution
foundation.

The intended runner flow is:

```text
validated job.json
  -> run_journal.exe
  -> NXOpen Python journal
  -> result.json
  -> JSON and Markdown reports
```

The current backend can detect `run_journal.exe` and prepare journal commands.
It does not execute journals by default.

Unsafe patterns are disallowed:

- Raw NXOpen calls exposed to agents
- Arbitrary Python execution
- Arbitrary journal execution
- Journal recording from agent tools
- Deleting files
- Overwriting model files
