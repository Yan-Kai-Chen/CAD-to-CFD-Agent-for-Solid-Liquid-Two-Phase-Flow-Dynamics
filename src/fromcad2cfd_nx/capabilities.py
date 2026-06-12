"""Machine-readable Siemens NX capability inventory."""

from __future__ import annotations

from typing import Any


CAPABILITY_SCHEMA_VERSION = "fromcad2cfd_nx_capabilities_v1"

NX_CAPABILITIES: list[dict[str, Any]] = [
    {
        "name": "preflight",
        "category": "environment",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx preflight",
        "execution_mode": "local_check",
        "scope": "Detect NX executables, journal runner, and environment values.",
    },
    {
        "name": "synthetic_geometry",
        "category": "solid_modeling",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Create public-safe cylinder, plate-with-hole, and boolean subtract demo jobs.",
    },
    {
        "name": "basic_solid_pack",
        "category": "solid_modeling",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-basic-solid-pack-job",
        "execution_mode": "synthetic_capability_pack",
        "scope": "Block, sphere, cone, boolean unite, boolean intersect, and copy-translate.",
    },
    {
        "name": "fluid_domain_cylinder_demo",
        "category": "cfd_domain_construction",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-fluid-domain-demo-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Create a public-safe cylindrical CFD domain and subtract a centered cylindrical obstacle; saves `.prt` and exports Parasolid.",
    },
    {
        "name": "edge_wall_trim_import_pack",
        "category": "solid_modeling",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-edge-wall-trim-pack-job",
        "execution_mode": "synthetic_capability_pack",
        "scope": "Edge blend, chamfer, shell, shell-face, controlled frustum taper, plane cut, Parasolid export, and Parasolid import.",
    },
    {
        "name": "transform_profile_pack",
        "category": "solid_modeling",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-transform-profile-pack-job",
        "execution_mode": "synthetic_capability_pack",
        "scope": "Rotate-copy, mirror, project curve, intersection curve, revolve, sweep-profile-along-path, and through-curves loft smoke geometry.",
    },
    {
        "name": "copied_model_inspection",
        "category": "model_inspection",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-inspect-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Copy and classify bodies, faces, edges, sheets, and solids before editing.",
    },
    {
        "name": "copied_model_boolean_subtract",
        "category": "solid_modeling",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-boolean-subtract-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Subtract explicit tool bodies from one explicit target body after inspection.",
    },
    {
        "name": "copied_model_plane_cut",
        "category": "solid_modeling",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-plane-cut-body-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Trim one body by an axis-aligned plane using a generated cutter body.",
    },
    {
        "name": "parasolid_import",
        "category": "format_bridge",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-import-parasolid-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Import `.x_t` or `.x_b` into a controlled `.prt` and verify body creation.",
    },
    {
        "name": "face_thicken",
        "category": "surface_repair",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-thicken-face-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Extract one explicit face when requested, thicken it, and validate solid output.",
    },
    {
        "name": "sheet_sew",
        "category": "surface_repair",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-sew-sheet-bodies-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Sew explicit sheet bodies with a positive tolerance.",
    },
    {
        "name": "curve_surface_demo",
        "category": "curve_surface",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-curve-surface-demo-job",
        "execution_mode": "synthetic_capability_pack",
        "scope": "Create line, arc, ellipse, and bounded-plane sheet smoke geometry.",
    },
    {
        "name": "reverse_step1_stl_to_convergent_prt",
        "category": "reverse_modeling",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-reverse-step1-stl-import-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Copy STL, import as cleaned convergent body, save `.prt`, and report body classification.",
    },
    {
        "name": "reverse_step2_cage_from_facet_body",
        "category": "reverse_modeling",
        "status": "implemented_with_runtime_requirement",
        "entrypoint": "fromcad2cfd nx write-reverse-step2-cage-from-facet-body-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Run Cage from Facet Body on selected convergent bodies; requires NX1926+ and `nx_subdivision`.",
    },
    {
        "name": "reverse_step3_step4_xoy_plane_combine",
        "category": "reverse_modeling",
        "status": "implemented",
        "entrypoint": "fromcad2cfd nx write-reverse-step3-step4-xoz-plane-combine-job",
        "execution_mode": "controlled_journal_job",
        "scope": "Import Parasolid, create XOY bounded-plane sheet at origin, move +Z, and run CombineSheets with recorded region trackers.",
    },
    {
        "name": "nx_mcp_safe_inventory",
        "category": "mcp",
        "status": "implemented",
        "entrypoint": "python -m fromcad2cfd_mcp_nx.server",
        "execution_mode": "stdio_mcp_server",
        "scope": "Serves high-level safe NX tools for capability reporting, preflight, controlled job creation, and journal command preparation; arbitrary execution remains disabled.",
    },
]


def capability_inventory() -> dict[str, Any]:
    return {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "backend": "siemens_nx",
        "capability_count": len(NX_CAPABILITIES),
        "capabilities": [dict(item) for item in NX_CAPABILITIES],
        "boundaries": [
            "No arbitrary NXOpen execution is exposed.",
            "Real-model copied operations require explicit inspected selectors.",
            "Synthetic packs validate operation families but do not replace real-model selector contracts.",
            "The MCP server exposes only high-level safe tools and does not execute arbitrary NXOpen code or arbitrary journals.",
        ],
    }


def capability_markdown() -> str:
    inventory = capability_inventory()
    lines = [
        "# Siemens NX Capability Inventory",
        "",
        f"Schema: `{inventory['schema_version']}`",
        f"Capability count: `{inventory['capability_count']}`",
        "",
        "| Capability | Category | Status | Entrypoint |",
        "| --- | --- | --- | --- |",
    ]
    for item in inventory["capabilities"]:
        lines.append(
            f"| `{item['name']}` | `{item['category']}` | `{item['status']}` | `{item['entrypoint']}` |"
        )
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {boundary}" for boundary in inventory["boundaries"])
    return "\n".join(lines) + "\n"
