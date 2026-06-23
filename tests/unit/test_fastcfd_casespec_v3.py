from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_fastcfd.cli import main as fastcfd_main
from fromcad2cfd_fastcfd.core.case_spec import (
    CASE_SPEC_SCHEMA_VERSION,
    explain_case_spec_markdown,
    read_case_spec,
    validate_case_spec,
)


EXAMPLE_CASE = Path("examples/fastcfd/casespec_v3/channel_flow_case.json")


def test_casespec_v3_example_validates():
    payload = read_case_spec(EXAMPLE_CASE)
    validation = validate_case_spec(payload)

    assert payload["schema_version"] == CASE_SPEC_SCHEMA_VERSION
    assert validation.passed
    assert validation.case_id == "channel_flow_demo"
    assert validation.claim_level == "native_evidence"
    assert validation.unsupported_features == []


def test_casespec_v3_explanation_mentions_core_sections():
    payload = read_case_spec(EXAMPLE_CASE)
    markdown = explain_case_spec_markdown(payload)

    assert "FastFluent CaseSpec v3 Summary" in markdown
    assert "channel_flow_demo" in markdown
    assert "Boundary Conditions" in markdown
    assert "QoI Targets" in markdown


def test_casespec_v3_rejects_dangerous_keys(tmp_path):
    payload = read_case_spec(EXAMPLE_CASE)
    payload["metadata"]["raw_pyfluent"] = "danger"
    case_path = tmp_path / "bad_case.json"
    case_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    try:
        read_case_spec(case_path)
    except ValueError as exc:
        assert "Dangerous key names" in str(exc)
    else:
        raise AssertionError("dangerous key should fail")


def test_casespec_v3_bad_numeric_value_returns_validation_error():
    payload = read_case_spec(EXAMPLE_CASE)
    payload["mesh"]["nx"] = "not-a-number"

    validation = validate_case_spec(payload)

    assert not validation.passed
    assert any("mesh.nx must be numeric" in error for error in validation.errors)


def test_casespec_v3_cli_writes_validation_artifacts(tmp_path, capsys):
    output_dir = tmp_path / "case_validation"
    exit_code = fastcfd_main(
        [
            "validate-case",
            str(EXAMPLE_CASE),
            "--output-dir",
            str(output_dir),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "passed"
    assert (output_dir / "case_validation.json").exists()
    assert (output_dir / "case_summary.md").exists()
    assert (output_dir / "unsupported_features.json").exists()
    assert (output_dir / "claim_level.json").exists()


def test_casespec_v3_cli_explain_markdown(capsys):
    exit_code = fastcfd_main(["explain-case", str(EXAMPLE_CASE), "--format", "markdown"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "FastFluent CaseSpec v3 Summary" in output
    assert "channel_flow_demo" in output
