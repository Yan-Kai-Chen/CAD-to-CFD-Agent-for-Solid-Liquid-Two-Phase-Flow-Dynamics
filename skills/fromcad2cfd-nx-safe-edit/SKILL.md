# FromCAD2CFD NX Safe Edit

Use this skill when editing Siemens NX models through the FromCAD2CFD NX
backend or NX MCP wrapper.

## Mandatory Rules

- Never modify an original input model in place.
- Copy the input model to a controlled output directory before editing.
- Never overwrite existing outputs.
- Inspect expressions, bodies, features, and units before editing.
- Match expression names exactly.
- Stop if an expression cannot be uniquely identified.
- Regenerate the model after each edit.
- Stop if regeneration fails.
- Export STEP or Parasolid after successful edits.
- Generate JSON and Markdown reports.
- Do not expose arbitrary Python execution.
- Do not expose raw NXOpen calls.
- Do not run arbitrary journals.
- Do not record journals through an agent tool.
- Do not delete files.

## Preferred Workflow

1. Run NX preflight.
2. Validate the input file path and extension.
3. Copy the input file into an output folder.
4. Run inspection on the copied model.
5. Select exactly one expression by exact name.
6. Record the old value and requested new value.
7. Apply the expression change through a controlled journal job.
8. Regenerate and validate the model.
9. Export STEP or Parasolid.
10. Write reports and return an `AgentResult`.

## Failure Policy

Stop immediately when:

- NX is not detected.
- `run_journal.exe` is unavailable.
- The input file is outside the allowed workspace.
- The target expression is ambiguous or missing.
- Regeneration fails.
- Export fails.
