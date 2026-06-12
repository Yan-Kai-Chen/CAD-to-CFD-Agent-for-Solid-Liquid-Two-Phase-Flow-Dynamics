from __future__ import annotations

from fromcad2cfd_mcp_nx.instructions import NX_MCP_INSTRUCTIONS
from fromcad2cfd_mcp_nx.tools import ALLOWED_TOOLS, DISABLED_TOOLS, tool_inventory


def test_nx_mcp_tool_inventory_is_safe():
    inventory = tool_inventory()

    assert "fromcad2cfd_nx_preflight" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_solid_modeling_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_basic_solid_pack_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_edge_wall_trim_pack_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_boolean_subtract_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_plane_cut_body_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_import_parasolid_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_surface_inspection_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_thicken_face_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_sew_sheet_bodies_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_curve_surface_demo_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_transform_profile_pack_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_reverse_step1_stl_import_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_reverse_step2_cage_from_facet_body_job" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_write_reverse_step3_step4_xoz_plane_combine_job" in inventory["allowed_tools"]
    assert "execute_python" in inventory["disabled_tools"]
    assert "raw_nxopen_call" in DISABLED_TOOLS
    assert all("raw" not in tool for tool in ALLOWED_TOOLS)


def test_nx_mcp_instructions_disable_arbitrary_execution():
    assert "arbitrary Python execution" in NX_MCP_INSTRUCTIONS
    assert "raw NXOpen calls" in NX_MCP_INSTRUCTIONS
    assert "Parasolid `.x_t`" in NX_MCP_INSTRUCTIONS
    assert "STEP only when explicitly requested" in NX_MCP_INSTRUCTIONS
    assert "copied-model plane cut" in NX_MCP_INSTRUCTIONS
    assert "transform/profile pack" in NX_MCP_INSTRUCTIONS
    assert "cleaned convergent body" in NX_MCP_INSTRUCTIONS
    assert "Cage from Facet Body" in NX_MCP_INSTRUCTIONS
    assert "XOY plane combine" in NX_MCP_INSTRUCTIONS
    assert "journal recording" in NX_MCP_INSTRUCTIONS
    assert "Do not expose" in NX_MCP_INSTRUCTIONS
