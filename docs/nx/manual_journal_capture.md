# NX Manual Journal Capture Playbook

This playbook defines the engineer-in-the-loop fallback for NX operations whose
NXOpen API contract is unclear from documentation or local probing.

Manual journal capture is not an agent-facing MCP tool. It is a development
method used to learn the exact NXOpen calls behind a user-validated UI
workflow, then convert those calls into a controlled project journal.

## When To Use

Use manual journal capture when all of the following are true:

- The user can complete the operation successfully in the NX UI.
- The controlled journal reaches the correct command family but fails at a
  selector-sensitive step.
- Local NXOpen headers or examples do not show the missing selector pattern.
- Further parameter guessing would risk uncontrolled trial-and-error.

Do not use this path to expose arbitrary NXOpen execution, arbitrary journal
playback, or direct model edits through MCP.

## Capture Procedure

1. Open a copied or disposable NX part, never the original input.
2. Start standard NX journal recording:
   `Menu > Tools > Journal > Record`.
3. In Chinese NX UI, use:
   `Menu > Tools > Operation Record > Record`.
4. Confirm the recorder is `Record Journal`, not `Record Movie`, `Record
   Macro`, or `Record Test Case`.
5. Prefer Python if the dialog allows language selection; C# journals are also
   acceptable as source evidence.
6. Save the captured file under the local project runtime, for example:
   `05_projects/nx_journal_capture/input/`.
7. Perform only the target UI operation. Avoid view rotation, display changes,
   and unrelated saves.
8. Stop recording immediately after the operation succeeds:
   `Menu > Tools > Journal > Stop Recording`.
9. Preserve the captured journal as evidence, then extract only the stable API
   pattern into a controlled project journal.

## Sanitization Rules

- Do not commit private CAD, STL, Parasolid, `.prt`, or result reports.
- Do not commit journals that reveal private file paths or proprietary feature
  names unless they are sanitized.
- Treat recorded object identifiers as examples only. Replace them with
  deterministic selectors in controlled code.
- Keep the final MCP surface at the job-builder level.
- Keep `record_journal`, `run_arbitrary_journal`, and raw NXOpen execution in
  the disabled tool list.

## Step 4 CombineSheets Lesson

The reverse-modeling Step 4 Combine workflow proved why this playbook is
needed.

The UI command was:

- `Insert > Combine > Combine`

The initial controlled journal selected the plane sheet and imported device
sheet bodies but did not reproduce the UI's region-selection stage. NX failed
with a complete-intersection diagnostic.

A user-recorded C# journal showed the missing pattern:

- `CombineSheetsBuilder.Regions.SelectMethod = KeepOrRemove`
- `Regions.NotifyBodiesHaveChanged(...)`
- `Regions.ClearAllRegionTrackers()`
- target keep/remove mode: `Keep`
- tool keep/remove mode: `Keep`
- one target `RegionTracker` with `OnTool = false` and a point selector on the
  XOY bounded plane
- one tool `RegionTracker` with `OnTool = true` and a face selector on the
  imported sheet body
- `CombineSheetsBuilder.Commit()`

The controlled Python journal now reproduces that pattern without exposing the
recorded journal as an executable MCP action.
