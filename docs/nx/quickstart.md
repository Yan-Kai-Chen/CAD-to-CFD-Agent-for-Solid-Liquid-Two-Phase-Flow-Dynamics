# Siemens NX Quickstart

Run local preflight without opening real models:

```powershell
fromcad2cfd nx preflight
```

Print the result without writing reports:

```powershell
fromcad2cfd nx preflight --no-report
```

Write a controlled geometry job JSON without running NX:

```powershell
fromcad2cfd nx write-job --recipe cylinder --radius-mm 10 --height-mm 20
```

Write the basic solid-modeling capability-pack job JSON without running NX:

```powershell
fromcad2cfd nx write-basic-solid-pack-job --project nx_basic_solid_pack_demo
```

This capability pack creates synthetic block, sphere, cone, boolean unite,
boolean intersect, and copy-translate geometry. It is the bounded smoke test for
basic NX solid modeling; see `docs/nx/basic_modeling_matrix.md`.

Write a synthetic cylindrical CFD fluid-domain job JSON without running NX:

```powershell
fromcad2cfd nx write-fluid-domain-demo-job --project nx_fluid_domain_cylinder_demo --domain-radius-mm 500 --domain-length-mm 1200 --obstacle-radius-mm 10 --obstacle-length-mm 1400
```

This public-safe demo creates a cylindrical computational domain and subtracts
a centered cylindrical obstacle. It is the agent-facing smoke route for
CFD-domain construction before private device geometry is introduced.

Write the edge/wall/trim/import capability-pack job JSON without running NX:

```powershell
fromcad2cfd nx write-edge-wall-trim-pack-job --project nx_edge_wall_trim_pack_demo
```

This pack covers edge blend, chamfer, shell, shell-face, controlled
tapered-frustum geometry, plane cut by generated cutter body, Parasolid export,
and Parasolid import-to-`.prt`.

Write the transform/profile capability-pack job JSON without running NX:

```powershell
fromcad2cfd nx write-transform-profile-pack-job --project nx_transform_profile_pack_demo
```

This pack covers rotate-copy, mirror body, project curve to face, body-plane
intersection curve, revolve, sweep-profile-along-path, and through-curves loft
smoke geometry.

Write the user-taught reverse-modeling Step 1 STL import job JSON:

```powershell
fromcad2cfd nx write-reverse-step1-stl-import-job --input-file sandbox\input\example_faceted_geometry.stl --project nx_reverse_step1
```

This copies the source STL into the project runtime `input` folder and prepares
a controlled NX job that imports the copied STL as a cleaned convergent body.
The primary Step 1 artifact is the saved `.prt`; Parasolid `.x_t` export is
attempted as a secondary artifact because convergent bodies may not always
serialize to Parasolid.

Write the user-taught reverse-modeling Step 2 Cage from Facet Body job JSON:

```powershell
fromcad2cfd nx write-reverse-step2-cage-from-facet-body-job --input-file sandbox\input\example_step1_convergent.prt --project nx_reverse_step2 --average-size-mm 10
```

This copies the accepted Step 1 `.prt` into the project runtime `input` folder
and prepares a controlled NX job that selects all convergent bodies by default
and creates a subdivision cage from facet regions. This journal requires a
newer NX build with `NXOpen.Features.Subdivision.CageFromFacetBodyBuilder` and
the `nx_subdivision` license. The primary Step 2 artifact is the copied and
saved `.prt`; Parasolid export is intentionally deferred until the body type
supports stable serialization.

Write the user-taught reverse-modeling Step 3/4 XOY plane combine job JSON:

```powershell
fromcad2cfd nx write-reverse-step3-step4-xoz-plane-combine-job --input-file sandbox\input\example_reverse_model.x_t --project nx_reverse_step3_step4 --square-size-mm 1000 --plane-offset-z-mm 5
```

This copies the accepted Parasolid input, imports it into a new NX `.prt`,
creates a 1000 mm square bounded-plane sheet on XOY centered at the origin,
moves that sheet by `+5 mm` along Z, and attempts `Insert > Combine > Combine`
through `CombineSheetsBuilder` with recorded keep/remove region trackers. The
`.prt` is the primary inspection artifact; Parasolid export is attempted when
the output body type supports it. The command name still contains `xoz` for
legacy compatibility; the validated geometry is XOY.

Write a copied-model plane-cut job JSON:

```powershell
fromcad2cfd nx write-plane-cut-body-job --input-file sandbox\input\example_model.prt --project nx_plane_cut --body-index 1 --plane-axis x --plane-offset-mm 0 --remove-side positive
```

Write a Parasolid import-to-PRT job JSON:

```powershell
fromcad2cfd nx write-import-parasolid-job --input-file sandbox\input\example_model.x_t --project nx_import_parasolid
```

NX geometry jobs default to Parasolid `.x_t` export because the local NX 12
runtime handles Parasolid reliably through the UF API. STEP export is optional
and should be treated as a secondary translator path.

The backend and MCP server do not execute arbitrary journals. Journal execution must be
explicitly enabled by a future controlled backend command.

For selector-sensitive NX UI workflows that are not clear from NXOpen examples,
use `docs/nx/manual_journal_capture.md` as the engineer-in-the-loop capture
playbook. Recorded journals are development evidence only; MCP must continue to
expose controlled job builders, not arbitrary recording or replay.
