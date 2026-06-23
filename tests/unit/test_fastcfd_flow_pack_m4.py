from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.core.evidence_bundle import validate_evidence_bundle
from fromcad2cfd_fastcfd.flow_pack import build_flow_pack, export_flow_pack_evidence_bundle, validate_flow_pack


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CASE = REPO_ROOT / "examples" / "fastcfd" / "casespec_v3" / "channel_flow_case.json"


def test_flow_pack_builds_setup_package(tmp_path):
    result = build_flow_pack(EXAMPLE_CASE, output_dir=tmp_path / "flow_pack", mesh_mode="structured-demo")

    assert result["schema_version"] == "fastfluent_flow_pack_v1"
    assert result["status"] == "success"
    assert result["solver_execution"] == "not_attempted"
    assert Path(result["artifacts"]["flow_pack"]).exists()
    assert Path(result["artifacts"]["mesh_manifest"]).exists()
    assert Path(result["artifacts"]["mesh_quality"]).exists()
    assert result["readiness_gate"]["ready_for_solver_setup"] is True


def test_flow_pack_validation_checks_required_artifacts(tmp_path):
    build_flow_pack(EXAMPLE_CASE, output_dir=tmp_path / "flow_pack", mesh_mode="structured-demo")

    validation = validate_flow_pack(tmp_path / "flow_pack")

    assert validation["passed"]
    assert validation["flow_pack_status"] == "success"
    assert validation["errors"] == []


def test_flow_pack_export_evidence_bundle(tmp_path):
    build_flow_pack(EXAMPLE_CASE, output_dir=tmp_path / "flow_pack", mesh_mode="structured-demo")

    result = export_flow_pack_evidence_bundle(tmp_path / "flow_pack", output_dir=tmp_path / "bundle")
    validation = validate_evidence_bundle(tmp_path / "bundle")
    claim_ledger = json.loads((tmp_path / "bundle" / "claim_ledger.json").read_text(encoding="utf-8"))
    qoi = json.loads((tmp_path / "bundle" / "qoi.json").read_text(encoding="utf-8"))

    assert result["status"] == "success"
    assert validation.passed
    assert claim_ledger["claim_level"] == "setup_only"
    assert qoi["status"] == "not_computed"
    assert (tmp_path / "bundle" / "mesh_manifest.json").exists()
    assert (tmp_path / "bundle" / "fluent_hints.json").exists()


def test_flow_pack_cli_routes(tmp_path, capsys):
    flow_pack_dir = tmp_path / "flow_pack"
    bundle_dir = tmp_path / "bundle"

    build_exit = fastcfd_main(["flow-pack", "build-demo", "--output-dir", str(flow_pack_dir), "--format", "json"])
    build_payload = json.loads(capsys.readouterr().out)
    validate_exit = fastcfd_main(["flow-pack", "validate", str(flow_pack_dir), "--format", "json"])
    validate_payload = json.loads(capsys.readouterr().out)
    export_exit = fastcfd_main(
        [
            "flow-pack",
            "export-evidence-bundle",
            str(flow_pack_dir),
            "--output-dir",
            str(bundle_dir),
            "--format",
            "json",
        ]
    )
    export_payload = json.loads(capsys.readouterr().out)

    assert build_exit == 0
    assert build_payload["status"] == "success"
    assert validate_exit == 0
    assert validate_payload["passed"]
    assert export_exit == 0
    assert export_payload["status"] == "success"
    assert (bundle_dir / "evidence_bundle_summary.md").exists()
