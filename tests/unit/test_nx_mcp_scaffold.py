from __future__ import annotations

import json
from pathlib import Path

import fromcad2cfd_nx.paths as nx_paths
from fromcad2cfd_mcp_nx.instructions import NX_MCP_INSTRUCTIONS
from fromcad2cfd_mcp_nx.server import server_descriptor
from fromcad2cfd_mcp_nx.tools import (
    ALLOWED_TOOLS,
    DISABLED_TOOLS,
    fromcad2cfd_nx_prepare_journal_command,
    fromcad2cfd_nx_write_basic_solid_pack_job,
    fromcad2cfd_nx_write_boolean_subtract_job,
    tool_inventory,
)


def test_nx_mcp_tool_inventory_is_safe():
    inventory = tool_inventory()

    assert "fromcad2cfd_nx_tool_inventory" in inventory["allowed_tools"]
    assert "fromcad2cfd_nx_capabilities" in inventory["allowed_tools"]
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
    assert "fromcad2cfd_nx_prepare_journal_command" in inventory["allowed_tools"]
    assert "execute_python" in inventory["disabled_tools"]
    assert "fromcad2cfd_nx_safe_edit_expression" in inventory["disabled_tools"]
    assert "fromcad2cfd_nx_export_geometry" in inventory["disabled_tools"]
    assert "raw_nxopen_call" in DISABLED_TOOLS
    assert all("raw" not in tool for tool in ALLOWED_TOOLS)
    assert "fromcad2cfd_nx_safe_edit_expression" not in ALLOWED_TOOLS


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


def test_nx_mcp_server_descriptor_is_nonblocking():
    descriptor = server_descriptor()

    assert descriptor["name"] == "fromcad2cfd-nx"
    assert descriptor["transport"] == "stdio"
    assert descriptor["status"] == "ready"
    assert "fromcad2cfd_nx_write_basic_solid_pack_job" in descriptor["allowed_tools"]
    assert "execute_python" in descriptor["disabled_tools"]


def test_nx_mcp_basic_pack_handler_writes_job(tmp_path, monkeypatch):
    monkeypatch.setattr(nx_paths, "PROJECTS_ROOT", tmp_path)

    result = fromcad2cfd_nx_write_basic_solid_pack_job(project="unit_mcp_basic", model_name="unit_basic")
    job_path = Path(result["job_path"])
    payload = json.loads(job_path.read_text(encoding="utf-8"))

    assert result["status"] == "success"
    assert job_path.exists()
    assert payload["operation"] == "create_basic_solid_pack_demo"
    assert payload["model_name"] == "unit_basic"


def test_nx_mcp_copied_input_handler_never_targets_original(tmp_path, monkeypatch):
    monkeypatch.setattr(nx_paths, "PROJECTS_ROOT", tmp_path)
    source = tmp_path / "source_model.prt"
    source.write_text("placeholder", encoding="utf-8")

    result = fromcad2cfd_nx_write_boolean_subtract_job(
        input_file=str(source),
        project="unit_mcp_boolean",
        target_body_index=1,
        tool_body_indices="2",
    )
    payload = json.loads(Path(result["job_path"]).read_text(encoding="utf-8"))

    assert payload["input_file"] != str(source)
    assert Path(payload["input_file"]).exists()
    assert payload["metadata"]["original_source_file"] == str(source)
    assert payload["metadata"]["copied_input_file"] == payload["input_file"]


def test_nx_mcp_prepare_command_uses_registered_journal(tmp_path, monkeypatch):
    monkeypatch.setattr(nx_paths, "PROJECTS_ROOT", tmp_path)
    run_journal = tmp_path / "run_journal.exe"
    run_journal.write_text("placeholder", encoding="utf-8")

    result = fromcad2cfd_nx_write_basic_solid_pack_job(project="unit_mcp_prepare", model_name="unit_basic")
    command = fromcad2cfd_nx_prepare_journal_command(job_path=result["job_path"], run_journal=str(run_journal))

    assert command["status"] == "success"
    assert command["operation"] == "create_basic_solid_pack_demo"
    assert command["argv"][0] == str(run_journal)
    assert command["argv"][2] == "-args"
