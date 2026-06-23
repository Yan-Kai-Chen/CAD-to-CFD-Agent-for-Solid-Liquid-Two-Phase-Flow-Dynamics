from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.flow_pack import build_flow_pack
from fromcad2cfd_fastcfd.route_selector import route_catalog, run_route_selector_demo, select_route


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CASE = REPO_ROOT / "examples" / "fastcfd" / "casespec_v3" / "channel_flow_case.json"


def test_route_selector_recommends_structured_native_route(tmp_path):
    flow_pack_dir = tmp_path / "flow_pack"
    build_flow_pack(EXAMPLE_CASE, output_dir=flow_pack_dir, mesh_mode="structured-demo")

    selection = select_route(flow_pack_dir, output_dir=tmp_path / "route")

    assert selection["status"] == "success"
    assert selection["recommended_route"] == "native_fastfluent_structured"
    assert selection["confidence"] == "high"
    assert selection["execution_boundary"]["selector_executes_solver"] is False
    assert Path(selection["artifacts"]["route_selection"]).exists()


def test_route_selector_recommends_mesh_completion_for_partial_flow_pack(tmp_path):
    flow_pack_dir = tmp_path / "flow_pack"
    flow_pack = build_flow_pack(EXAMPLE_CASE, output_dir=flow_pack_dir, mesh_mode="none")

    selection = select_route(flow_pack_dir)

    assert flow_pack["status"] == "partial"
    assert selection["recommended_route"] == "complete_mesh_gateway"
    assert any("mesh" in item.lower() for item in selection["rationale"])


def test_route_selector_recommends_physics_passport_for_specialized_case(tmp_path):
    case_payload = json.loads(EXAMPLE_CASE.read_text(encoding="utf-8"))
    case_payload["case_id"] = "turbulence_route_demo"
    case_payload["case_type"] = "turbulence.channel_setup"
    case_path = tmp_path / "turbulence_case.json"
    case_path.write_text(json.dumps(case_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    flow_pack_dir = tmp_path / "flow_pack"
    build_flow_pack(case_path, output_dir=flow_pack_dir, mesh_mode="structured-demo")

    selection = select_route(flow_pack_dir)

    assert selection["recommended_route"] == "physics_passport_review"
    assert selection["confidence"] == "medium"


def test_route_selector_catalog_contains_disabled_routes():
    catalog = route_catalog()

    assert catalog["schema_version"] == "fastfluent_route_catalog_v1"
    assert "native_fastfluent_structured" in catalog["routes"]
    assert "raw_fluent_launch" in catalog["disabled_routes"]


def test_route_selector_cli_demo_and_select(tmp_path, capsys):
    demo_dir = tmp_path / "demo"

    demo_exit = fastcfd_main(["route-selector", "demo", "--output-dir", str(demo_dir), "--format", "json"])
    demo_payload = json.loads(capsys.readouterr().out)
    select_exit = fastcfd_main(
        [
            "route-selector",
            "select",
            str(demo_dir / "f"),
            "--output-dir",
            str(tmp_path / "selection"),
            "--format",
            "json",
        ]
    )
    select_payload = json.loads(capsys.readouterr().out)
    catalog_exit = fastcfd_main(["route-selector", "catalog", "--format", "json"])
    catalog_payload = json.loads(capsys.readouterr().out)

    assert demo_exit == 0
    assert demo_payload["outputs"]["recommended_route"] == "native_fastfluent_structured"
    assert select_exit == 0
    assert select_payload["recommended_route"] == "native_fastfluent_structured"
    assert catalog_exit == 0
    assert "route_selector" not in catalog_payload["routes"]
    assert (demo_dir / "s" / "route_selection_report.md").exists()
