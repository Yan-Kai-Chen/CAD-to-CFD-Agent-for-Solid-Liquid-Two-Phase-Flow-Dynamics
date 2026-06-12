"""Safe Siemens NX MCP tool declarations."""

ALLOWED_TOOLS = [
    "fromcad2cfd_nx_preflight",
    "fromcad2cfd_nx_write_geometry_job",
    "fromcad2cfd_nx_write_solid_modeling_job",
    "fromcad2cfd_nx_write_basic_solid_pack_job",
    "fromcad2cfd_nx_write_edge_wall_trim_pack_job",
    "fromcad2cfd_nx_write_boolean_subtract_job",
    "fromcad2cfd_nx_write_plane_cut_body_job",
    "fromcad2cfd_nx_write_import_parasolid_job",
    "fromcad2cfd_nx_write_surface_inspection_job",
    "fromcad2cfd_nx_write_thicken_face_job",
    "fromcad2cfd_nx_write_sew_sheet_bodies_job",
    "fromcad2cfd_nx_write_curve_surface_demo_job",
    "fromcad2cfd_nx_write_transform_profile_pack_job",
    "fromcad2cfd_nx_write_reverse_step1_stl_import_job",
    "fromcad2cfd_nx_write_reverse_step2_cage_from_facet_body_job",
    "fromcad2cfd_nx_write_reverse_step3_step4_xoz_plane_combine_job",
    "fromcad2cfd_nx_prepare_journal_command",
    "fromcad2cfd_nx_inspect_model",
    "fromcad2cfd_nx_safe_edit_expression",
    "fromcad2cfd_nx_export_geometry",
    "fromcad2cfd_nx_get_last_report",
]

DISABLED_TOOLS = [
    "execute_python",
    "raw_nxopen_call",
    "run_arbitrary_journal",
    "record_journal",
    "delete_file",
    "overwrite_file",
]

TOOL_DESCRIPTIONS = {
    "fromcad2cfd_nx_preflight": "Detect NX installation and journal-runner availability without opening models.",
    "fromcad2cfd_nx_write_geometry_job": "Write a validated NX journal job JSON for controlled geometry creation.",
    "fromcad2cfd_nx_write_solid_modeling_job": "Write a validated NX journal job JSON for controlled solid modeling operations such as primitive and boolean smoke cases.",
    "fromcad2cfd_nx_write_basic_solid_pack_job": "Write a validated NX job for the basic solid-modeling capability pack: block, sphere, cone, boolean unite/intersect, and copy-translate.",
    "fromcad2cfd_nx_write_edge_wall_trim_pack_job": "Write a validated NX job for edge blend, chamfer, shell, shell-face, controlled taper/frustum, plane cut, Parasolid export, and Parasolid import coverage.",
    "fromcad2cfd_nx_write_boolean_subtract_job": "Write a copied-model NX boolean subtract job using explicit target/tool body selectors.",
    "fromcad2cfd_nx_write_plane_cut_body_job": "Write a copied-model NX plane-cut job that removes one side of an axis-aligned plane through a generated cutter body.",
    "fromcad2cfd_nx_write_import_parasolid_job": "Write a controlled NX job that imports Parasolid `.x_t` or `.x_b` into a new `.prt` and verifies re-export.",
    "fromcad2cfd_nx_write_surface_inspection_job": "Write a validated NX journal job JSON that copies and classifies a model before any surface repair.",
    "fromcad2cfd_nx_write_thicken_face_job": "Write a copied-model NX thicken job using explicit body/face selectors, with optional face extraction before thickening.",
    "fromcad2cfd_nx_write_sew_sheet_bodies_job": "Write a copied-model NX sew job using explicit sheet-body selectors and a tolerance.",
    "fromcad2cfd_nx_write_curve_surface_demo_job": "Write a synthetic NX job for basic line/arc/ellipse curves and a bounded-plane sheet surface.",
    "fromcad2cfd_nx_write_transform_profile_pack_job": "Write a validated NX job for rotate copy, mirror body, project curve, intersection curve, revolve, sweep-profile-along-path, and through-curves loft coverage.",
    "fromcad2cfd_nx_write_reverse_step1_stl_import_job": "Write a copied-input NX reverse-modeling Step 1 job that imports STL as a cleaned convergent body with user-taught facet cleanup parameters.",
    "fromcad2cfd_nx_write_reverse_step2_cage_from_facet_body_job": "Write a copied-input NX reverse-modeling Step 2 job that runs Cage from Facet Body on selected convergent bodies with an average face size.",
    "fromcad2cfd_nx_write_reverse_step3_step4_xoz_plane_combine_job": "Write a copied-input NX reverse-modeling Step 3/4 job that imports Parasolid, creates a 1000 mm XOY bounded-plane sheet at the origin, moves it +Z, and runs CombineSheets with recorded keep/remove region trackers. The xoz name is legacy-compatible.",
    "fromcad2cfd_nx_prepare_journal_command": "Prepare but do not execute a run_journal command.",
    "fromcad2cfd_nx_inspect_model": "Inspect a copied NX model through a controlled journal workflow.",
    "fromcad2cfd_nx_safe_edit_expression": "Edit one uniquely identified NX expression on a copied model.",
    "fromcad2cfd_nx_export_geometry": "Export copied NX geometry to STEP or Parasolid through a controlled job.",
    "fromcad2cfd_nx_get_last_report": "Return the most recent NX JSON/Markdown report paths.",
}


def tool_inventory() -> dict[str, object]:
    return {
        "allowed_tools": ALLOWED_TOOLS,
        "disabled_tools": DISABLED_TOOLS,
        "tool_descriptions": TOOL_DESCRIPTIONS,
    }
