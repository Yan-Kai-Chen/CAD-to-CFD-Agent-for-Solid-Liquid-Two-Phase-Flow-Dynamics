# SolidWorks Safe Model Edit

Use this skill for any SolidWorks model creation, inspection, modification, rebuild, save, or export task in this workspace.

## Scope

All work must stay under the active project workspace root:

```text
<WORKSPACE_ROOT>
```

## Mandatory Safety Rules

1. Never modify original files in any `input` or `01_input_original_models` folder.
2. Before modifying an existing model, copy it to the project output or working-copy area and edit only that copy.
3. Output filenames must include an automatic timestamp unless the path is guaranteed not to exist.
4. Before editing an existing model, scan and report features, dimensions, equations, materials, and configurations.
5. If the requested target dimension, feature, or configuration cannot be uniquely identified, stop and ask for clarification. Do not guess.
6. After every model edit, run a rebuild.
7. If rebuild fails or reports blocking errors, stop immediately and write a diagnostic report.
8. Every successful model operation must export a STEP file.
9. Every operation must generate both a Markdown report and a JSON report.
10. Tools that expose arbitrary code execution, including `execute_python`, are disabled by default. If such a tool is unavoidable, require explicit human confirmation for that specific call.

## Standard Existing-Model Edit Flow

1. Identify the input model under the project input folder.
2. Copy the model to a timestamped working/output path.
3. Open the copy in SolidWorks.
4. Scan features, dimensions, equations, materials, and configurations.
5. Resolve the requested edit target exactly.
6. Apply only the requested edit.
7. Rebuild the model.
8. Save the edited model under `05_projects\test_project\output` or the task-specific output folder.
9. Export STEP under the same output tree or an adjacent exports folder.
10. Write Markdown and JSON reports under `05_projects\test_project\reports` or the task-specific reports folder.

## Standard New-Model Flow

1. Create a new model in memory.
2. Build only the requested geometry.
3. Rebuild.
4. Save to a timestamped SolidWorks part file.
5. Export STEP.
6. Write Markdown and JSON reports with tool calls, units, dimensions, file paths, rebuild status, and export status.

## Stop Conditions

Stop the workflow and write a diagnostic report if any of these occur:

- Input model path is outside the workspace root.
- Output path would overwrite an existing file.
- A requested dimension or feature cannot be uniquely identified.
- SolidWorks COM/MCP connection fails.
- Rebuild fails.
- STEP export fails.
- The MCP server exposes unrestricted execution and cannot disable or gate it.
