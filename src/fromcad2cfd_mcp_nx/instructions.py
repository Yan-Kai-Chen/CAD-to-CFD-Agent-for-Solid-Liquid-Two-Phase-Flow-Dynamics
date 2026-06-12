"""Safety instructions for the Siemens NX MCP server."""

NX_MCP_INSTRUCTIONS = """
Expose only high-level safe Siemens NX workflow tools.

Never expose raw NXOpen calls, arbitrary Python execution, arbitrary journal
execution, journal recording, delete operations, or overwrite operations.

Allowed solid-modeling tools must map to project journals such as the basic
solid pack, edge/wall/trim/import pack, copied-model boolean subtract,
copied-model plane cut, copied-model thicken, copied-model sew,
controlled Parasolid import, curve/surface smoke workflows, or the
transform/profile pack for rotate, mirror, project/intersection curves,
revolve, sweep-profile-along-path, and through-curves loft smoke coverage.
Reverse-modeling STL import must map to the controlled Step 1 tool that copies
the STL input, imports it as a cleaned convergent body, saves `.prt`, and writes
classification reports. Reverse-modeling Cage from Facet Body must map to the
controlled Step 2 tool that copies the Step 1 `.prt`, selects convergent bodies,
uses NX1926+ `CageFromFacetBodyBuilder`, and writes `.prt` plus reports.
Reverse-modeling Step 3/4 must map to the controlled XOY plane combine tool
that copies a Parasolid input, imports it into a new NX `.prt`, creates a
1000 mm square bounded-plane sheet on XOY centered at the origin, moves that
sheet +Z by the requested offset, and uses `CombineSheetsBuilder` with explicit
keep/remove region trackers.
Do not convert user prompts directly into raw NXOpen Python.

Every model-editing workflow must:
1. Validate the input path.
2. Copy the input model to a controlled output directory.
3. Inspect expressions and model metadata before editing.
4. Match expression names exactly.
5. Stop on ambiguity.
6. Regenerate the model after edits.
7. Stop on regeneration failure.
8. Save NX `.prt` and export Parasolid `.x_t`; export STEP only when explicitly requested.
9. Write JSON and Markdown reports.

For STL-to-convergent reverse-modeling Step 1, Parasolid export is an attempted
secondary artifact because convergent bodies may not always serialize cleanly to
Parasolid. The primary acceptance artifact is the saved NX `.prt` plus body
classification report.

For reverse-modeling Step 2 Cage from Facet Body, require a newer NX build with
`NXOpen.Features.Subdivision.CageFromFacetBodyBuilder` and the `nx_subdivision`
license. The primary acceptance artifact is the copied NX `.prt`; Parasolid
export is not mandatory until the subdivision/convergent result is converted to
a body type that supports stable Parasolid serialization.

For reverse-modeling Step 3/4 XOY plane combine, treat `.prt` as the primary
inspection artifact. Parasolid `.x_t` export should be attempted when the body
type supports it. The current command/tool names may still contain `xoz` for
legacy compatibility, but the validated geometry is XOY. A CombineSheets
failure must save the pre-combine part and write a diagnostic report instead of
repeatedly trying uncontrolled commands.

Manual NX journal recording may be used by a developer as an offline evidence
capture method when a user-validated UI operation exposes missing selector
logic. Recorded journals must be sanitized and converted into controlled
project journals before they become MCP-accessible behavior. Do not expose
recording, arbitrary journal replay, or raw NXOpen execution as tools.

True DraftBody and arbitrary-face trim operations are selector-sensitive and
must stay outside the default agent-facing tool inventory until validated.
Represent simple taper through controlled frustum/cone jobs and represent
axis-aligned body trimming through a generated cutter body plus subtract.

Arbitrary copied-model rotate/mirror, user-specified projected/intersection
curves, and real-model revolve/sweep/loft profiles require selector contracts
and must stay behind controlled job builders. The current default inventory
only exposes the synthetic transform/profile smoke pack for those families.
"""
