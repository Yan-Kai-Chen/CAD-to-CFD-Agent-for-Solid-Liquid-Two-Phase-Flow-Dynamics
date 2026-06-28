from __future__ import annotations

from pathlib import Path

from fromcad2cfd_fastcfd.file_io import path_is_file, read_json_file, read_text_file
from fromcad2cfd_postprocessing.dewaxing_result_pack import validate_dewaxing_result_pack


REPO_ROOT = Path(__file__).resolve().parents[2]
FINAL_PROJECT_TITLE = "An Agent Framework for FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dynamics"


def _read(relative: str) -> str:
    return read_text_file(REPO_ROOT / relative)


def test_public_asset_framework_map_is_linked_from_primary_navigation():
    asset_map = _read("docs/public_asset_framework_map.md")
    readme = _read("README.md")
    docs_index = _read("docs/index.md")
    architecture = _read("docs/architecture.md")

    assert "framework base" in asset_map
    assert "four workflow blocks" in asset_map
    assert "Agent workflow spine" in asset_map
    assert "benchmark ladder" in asset_map
    assert "dewaxing case study" in asset_map
    assert "legacy evidence" in asset_map

    for text in (readme, docs_index, architecture):
        assert "public_asset_framework_map.md" in text


def test_final_project_title_is_used_in_public_identity_documents():
    identity_pages = [
        "README.md",
        "CITATION.cff",
        "pyproject.toml",
        "docs/dewaxing_agent/README.md",
        "docs/dewaxing_agent/01_project_overview.md",
    ]

    for relative in identity_pages:
        assert FINAL_PROJECT_TITLE in _read(relative)


def test_benchmark_ladder_scaffold_has_all_public_case_entries():
    expected = {
        "01_internal_pipe_or_channel_flow": "partial",
        "02_backward_facing_step": "planned",
        "03_heated_channel_cht_toy_case": "partial",
        "04_cavity_or_enclosure_flow": "partial",
        "05_dewaxing_steam_impact_case": "application-driving",
    }

    docs_readme = _read("docs/agent_benchmark_ladder/README.md")
    examples_readme = _read("examples/fastcfd/agent_benchmark_ladder/README.md")

    for case_dir, status in expected.items():
        docs_page = REPO_ROOT / "docs" / "agent_benchmark_ladder" / f"{case_dir}.md"
        example_page = REPO_ROOT / "examples" / "fastcfd" / "agent_benchmark_ladder" / case_dir / "README.md"
        assert path_is_file(docs_page)
        assert path_is_file(example_page)
        assert f"`{status}`" in read_text_file(docs_page)
        assert case_dir in examples_readme

    assert "Source Asset Mapping" in docs_readme
    assert "Do not place private Fluent case/data files" in examples_readme


def test_dewaxing_case_study_keeps_public_fixture_and_claim_boundary():
    dewaxing_readme = _read("docs/dewaxing_agent/README.md")
    project_tree = _read("docs/dewaxing_agent/00_project_tree.md")

    assert "Public Asset Mapping" in dewaxing_readme
    assert "FastFluent is the Agent's reduced-order guidance" in dewaxing_readme
    assert "tests/unit/test_fastcfd_dewaxing_*.py" in project_tree

    fixture_dir = REPO_ROOT / "examples" / "postprocessing" / "dewaxing_result_pack"
    validation = validate_dewaxing_result_pack(fixture_dir)
    result_pack = read_json_file(fixture_dir / "result_pack.json")

    assert validation["status"] == "passed"
    assert validation["key_metrics"]["full_melt_time_s"] == 409.0
    assert result_pack["usage_boundary"]["valid_for_final_crack_probability"] is False


def test_active_public_route_docs_do_not_require_private_absolute_paths():
    public_route_pages = [
        "README.md",
        "docs/public_asset_framework_map.md",
        "docs/agent_benchmark_ladder/README.md",
        "docs/agent_benchmark_ladder/05_dewaxing_steam_impact_case.md",
        "docs/dewaxing_agent/README.md",
        "docs/dewaxing_agent/01_project_overview.md",
        "docs/dewaxing_agent/02_evidence_inventory.md",
        "docs/dewaxing_agent/06_fastfluent_to_fluent_guidance.md",
        "docs/dewaxing_agent/07_paper_figures_and_tables.md",
    ]

    for relative in public_route_pages:
        text = _read(relative)
        assert "D:/CYK2" not in text
        assert "D:\\CYK2" not in text
