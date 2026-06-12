# Manual Journal Capture Reference

Manual journal capture is the project-approved way to learn NXOpen behavior
from a user-validated UI operation when official examples or headers do not
show the required selector sequence.

Use it only as a development aid. Do not expose journal recording or arbitrary
journal playback as an MCP tool.

## Required Route

1. Work on a copied or disposable NX part.
2. Start standard journal recording:
   `Tools > Journal > Record`.
3. In Chinese UI, this is the normal operation-record command, not movie,
   macro, or automated-test recording.
4. Save the captured file under `05_projects/nx_journal_capture/input/`.
5. Perform one target UI operation only.
6. Stop recording immediately:
   `Tools > Journal > Stop Recording`.
7. Preserve the captured file as local evidence.
8. Translate the stable API pattern into a controlled project journal.
9. Validate with generated `.prt`, JSON report, Markdown report, and body or
   feature counts.
10. Write a project memory note after validation.

## What To Extract

Extract:

- builder class,
- command family,
- body, face, edge, curve, or region selectors,
- selection intent rules,
- operation mode flags,
- commit call,
- validation behavior.

Do not copy:

- private model paths,
- object identifiers as hard-coded production selectors,
- display-only interactions,
- view rotations,
- arbitrary post-processing operations.

## Validated CombineSheets Example

The recorded Step 4 CombineSheets workflow showed that body selection was not
enough. The controlled journal had to reproduce the region-selection stage:

- set `BooleanRegionSelect.SelectOption.KeepOrRemove`,
- notify that bodies changed,
- clear existing region trackers,
- keep target and tool regions,
- add a target region tracker using a point on the XOY plane,
- add a tool region tracker using a face from the imported sheet body,
- commit `CombineSheetsBuilder`.

This is now the preferred development pattern for future selector-sensitive NX
commands.
