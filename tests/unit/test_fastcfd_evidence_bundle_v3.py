from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.core.claim_ledger import CLAIM_LEDGER_SCHEMA_VERSION, build_default_claim_ledger
from fromcad2cfd_fastcfd.core.evidence_bundle import summarize_evidence_bundle_markdown, validate_evidence_bundle


def _write_minimal_bundle(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "case.json").write_text(
        json.dumps(
            {
                "schema_version": "fastfluent_case_spec_v3",
                "case_id": "bundle_demo",
                "case_type": "flow.steady_incompressible",
                "claim_level": "native_evidence",
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "run_manifest.json").write_text(
        json.dumps({"schema_version": "fastfluent_run_manifest_v1", "status": "success"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (root / "validation_status.json").write_text(
        json.dumps({"schema_version": "fastfluent_validation_status_v1", "status": "passed"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (root / "qoi.json").write_text(
        json.dumps({"schema_version": "fastfluent_qoi_v1", "metrics": {"pressure_drop_pa": 1.25}}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (root / "claim_ledger.json").write_text(
        json.dumps(
            build_default_claim_ledger(
                claim_level="native_evidence",
                supported_claims=["The case supports preliminary pressure-drop screening."],
                required_next_steps=["Run Fluent if final pressure-drop accuracy is required."],
            ),
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "limitations.md").write_text("# Limitations\n\nThis is a native evidence bundle.\n", encoding="utf-8")
    (root / "report.md").write_text("# Report\n\nBundle demo.\n", encoding="utf-8")
    return root


def test_evidence_bundle_v3_minimal_bundle_passes(tmp_path):
    bundle_dir = _write_minimal_bundle(tmp_path / "bundle")
    validation = validate_evidence_bundle(bundle_dir)

    assert validation.passed
    assert "case.json" in validation.present_files
    assert validation.missing_required_files == []
    assert validation.json_errors == []


def test_evidence_bundle_v3_missing_files_fail(tmp_path):
    bundle_dir = tmp_path / "missing_bundle"
    bundle_dir.mkdir()
    (bundle_dir / "case.json").write_text("{}", encoding="utf-8")

    validation = validate_evidence_bundle(bundle_dir)

    assert not validation.passed
    assert "run_manifest.json" in validation.missing_required_files
    assert "claim_ledger.json" in validation.missing_required_files


def test_evidence_bundle_v3_rejects_bad_claim_ledger(tmp_path):
    bundle_dir = _write_minimal_bundle(tmp_path / "bundle")
    bad_claims = json.loads((bundle_dir / "claim_ledger.json").read_text(encoding="utf-8"))
    bad_claims["schema_version"] = CLAIM_LEDGER_SCHEMA_VERSION + "_bad"
    (bundle_dir / "claim_ledger.json").write_text(json.dumps(bad_claims, ensure_ascii=True, indent=2), encoding="utf-8")

    validation = validate_evidence_bundle(bundle_dir)

    assert not validation.passed
    assert any("Unsupported schema_version" in error for error in validation.json_errors)


def test_evidence_bundle_v3_markdown_summary(tmp_path):
    bundle_dir = _write_minimal_bundle(tmp_path / "bundle")
    markdown = summarize_evidence_bundle_markdown(bundle_dir)

    assert "FastFluent EvidenceBundle v3 Summary" in markdown
    assert "bundle_demo" in markdown
    assert "pressure_drop_pa" in markdown


def test_evidence_bundle_v3_cli_routes(tmp_path, capsys):
    bundle_dir = _write_minimal_bundle(tmp_path / "bundle")

    validate_exit = fastcfd_main(["evidence", "validate-bundle", str(bundle_dir), "--format", "json"])
    validation = json.loads(capsys.readouterr().out)
    summarize_exit = fastcfd_main(["evidence", "summarize-bundle", str(bundle_dir), "--format", "markdown"])
    summary = capsys.readouterr().out

    assert validate_exit == 0
    assert validation["status"] == "passed"
    assert summarize_exit == 0
    assert "FastFluent EvidenceBundle v3 Summary" in summary
