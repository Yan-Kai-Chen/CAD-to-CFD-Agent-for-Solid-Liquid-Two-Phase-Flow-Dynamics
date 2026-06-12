# Siemens NX MCP Reference

The NX MCP layer is a safe wrapper around the `fromcad2cfd_nx` backend.

Allowed tool names:

- `fromcad2cfd_nx_preflight`
- `fromcad2cfd_nx_write_geometry_job`
- `fromcad2cfd_nx_write_basic_solid_pack_job`
- `fromcad2cfd_nx_write_edge_wall_trim_pack_job`
- `fromcad2cfd_nx_write_boolean_subtract_job`
- `fromcad2cfd_nx_write_plane_cut_body_job`
- `fromcad2cfd_nx_write_import_parasolid_job`
- `fromcad2cfd_nx_write_surface_inspection_job`
- `fromcad2cfd_nx_write_thicken_face_job`
- `fromcad2cfd_nx_write_sew_sheet_bodies_job`
- `fromcad2cfd_nx_write_curve_surface_demo_job`
- `fromcad2cfd_nx_write_transform_profile_pack_job`
- `fromcad2cfd_nx_write_reverse_step1_stl_import_job`
- `fromcad2cfd_nx_write_reverse_step2_cage_from_facet_body_job`
- `fromcad2cfd_nx_write_reverse_step3_step4_xoz_plane_combine_job`
- `fromcad2cfd_nx_prepare_journal_command`
- `fromcad2cfd_nx_inspect_model`
- `fromcad2cfd_nx_safe_edit_expression`
- `fromcad2cfd_nx_export_geometry`
- `fromcad2cfd_nx_get_last_report`

Disabled tool patterns:

- `execute_python`
- `raw_nxopen_call`
- `run_arbitrary_journal`
- `record_journal`
- `delete_file`
- `overwrite_file`

The initial MCP package is a scaffold only. It documents the safe surface before
serving real MCP tools.

Agent-facing trim is currently axis-aligned plane cutting through a generated
cutter body plus subtract. True DraftBody and arbitrary face/plane trim remain
outside the default inventory until selector validation is stronger.

Agent-facing rotate, mirror, project/intersection curves, revolve, sweep, and
loft are currently exposed only through the synthetic transform/profile pack.
Real-model variants require explicit body, curve, section, guide, datum, and
face selectors before they can become copied-model tools.

Reverse-modeling Step 1 is exposed as a copied-input STL import job. It imports
STL as a cleaned convergent body with the user-taught settings: convergent
output, automatic cleanup, folded-facet angle `15.0`, minimum facet number
`100`, and millimeter STL units.

Reverse-modeling Step 2 is exposed as a copied-input Cage from Facet Body job.
It takes the accepted Step 1 `.prt`, selects all convergent bodies by default,
sets average face size to `10.0 mm`, and uses the NX1926+ subdivision builder.
It requires a newer NX installation with `nx_subdivision`; `.prt` is the
primary accepted artifact.

Reverse-modeling Step 3/4 is exposed as a copied-input XOY plane combine job.
It imports an accepted Parasolid result into a new `.prt`, creates the
1000 mm square XOY bounded-plane sheet centered at the origin, moves it by
`+5 mm` along Z, and uses `CombineSheetsBuilder` with explicit keep/remove
region trackers. The `.prt` is the primary inspection artifact; `.x_t` export
is attempted when possible. The current tool name retains `xoz` as a legacy
compatibility name.

Manual journal capture is a development aid, not an MCP tool. When a user can
complete a selector-sensitive NX command in the UI, a developer may record a
local NX journal, extract the stable NXOpen selector pattern, and convert it
into a controlled job builder. Keep `record_journal`, `run_arbitrary_journal`,
and raw NXOpen execution disabled in the MCP surface.
