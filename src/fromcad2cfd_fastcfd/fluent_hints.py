"""Evidence-checked Fluent setup hint compiler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .paths import unique_path


FLUENT_HINT_COMPILER_SCHEMA_VERSION = "fromcad2cfd_fastfluent_fluent_hint_compiler_v1"


def compile_fluent_setup_hints(
    evidence_files: list[str | Path],
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Compile Fluent setup hints from validated evidence artifacts."""

    target_dir = Path(output_dir) if output_dir else unique_path(Path("05_projects") / "fluent_hint_compiler" / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    compiled: list[dict[str, Any]] = []
    evidence_summary: list[dict[str, Any]] = []
    blocking_errors: list[str] = []
    try:
        if not evidence_files:
            raise ValueError("At least one evidence file is required.")
        for item in evidence_files:
            path = Path(item)
            if not path.exists():
                blocking_errors.append(f"Evidence file does not exist: {path}")
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            hints, schemas = _extract_hints_from_payload(payload, source_path=path)
            evidence_summary.append({"source_file": str(path), "schemas": schemas, "hint_count": len(hints)})
            if not hints:
                blocking_errors.append(f"No Fluent setup hints were found in evidence file: {path}")
            compiled.extend(hints)
        for index, hint in enumerate(compiled):
            if not hint.get("category"):
                blocking_errors.append(f"Compiled hint {index} is missing category.")
            if not hint.get("recommendation"):
                blocking_errors.append(f"Compiled hint {index} is missing recommendation.")
            evidence = hint.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                blocking_errors.append(f"Compiled hint {index} has no evidence.")
            if not hint.get("source_artifact"):
                blocking_errors.append(f"Compiled hint {index} is missing source_artifact.")
        status = "failed" if blocking_errors else "passed"
        report = {
            "schema_version": FLUENT_HINT_COMPILER_SCHEMA_VERSION,
            "status": status,
            "hint_count": len(compiled),
            "evidence_file_count": len(evidence_files),
            "evidence_summary": evidence_summary,
            "hints": compiled,
            "blocking_errors": blocking_errors,
            "acceptance": {
                "all_hints_have_evidence": not any(not hint.get("evidence") for hint in compiled),
                "at_least_one_hint": len(compiled) > 0,
                "no_missing_evidence_files": not any("does not exist" in error for error in blocking_errors),
            },
            "limitations": [
                "This compiler aggregates setup guidance from validated artifacts only.",
                "It does not execute Fluent, edit Fluent case files, or replace Fluent validation.",
            ],
        }
        artifacts = {
            "fluent_setup_hints": str(_write_json(target_dir / "fluent_setup_hints.json", report)),
            "fluent_setup_hints_report": str(_write_text(target_dir / "fluent_setup_hints_report.md", _compiler_markdown(report))),
        }
        if status == "passed":
            result = AgentResult.success(
                backend="fastcfd",
                operation="compile_fluent_setup_hints",
                message="Evidence-checked Fluent setup hints compiled.",
                outputs={"artifacts": artifacts, "compiled_hints": report, "solver_execution": "not_attempted_hint_compiler_only"},
                metadata={"output_dir": str(target_dir)},
            )
        else:
            result = AgentResult.failed(
                backend="fastcfd",
                operation="compile_fluent_setup_hints",
                message="Fluent setup hint compilation failed evidence checks.",
                errors=blocking_errors,
                metadata={"output_dir": str(target_dir)},
            )
            result.outputs.update({"artifacts": artifacts, "compiled_hints": report, "solver_execution": "blocked_by_hint_evidence_checks"})
        artifacts["fluent_setup_hints_status"] = str(_write_json(target_dir / "fluent_setup_hints_status.json", result.to_dict()))
        return result.to_dict()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failure = AgentResult.failed(
            backend="fastcfd",
            operation="compile_fluent_setup_hints",
            message="Fluent setup hint compilation failed before completion.",
            errors=[str(exc)],
            metadata={"output_dir": str(target_dir)},
        )
        failure.outputs["artifacts"] = {"fluent_setup_hints_status": str(target_dir / "fluent_setup_hints_status.json")}
        _write_json(target_dir / "fluent_setup_hints_status.json", failure.to_dict())
        return failure.to_dict()


def _extract_hints_from_payload(payload: dict[str, Any], *, source_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    schemas: list[str] = []
    hints: list[dict[str, Any]] = []

    def visit(value: Any, location: str) -> None:
        if isinstance(value, dict):
            schema = value.get("schema_version")
            if isinstance(schema, str):
                schemas.append(schema)
            if isinstance(value.get("hints"), list):
                for hint in value["hints"]:
                    if isinstance(hint, dict):
                        hints.append(_normalize_hint(hint, source_path=source_path, source_schema=schema, location=location))
            if isinstance(value.get("fluent_setup_hints"), list):
                for hint in value["fluent_setup_hints"]:
                    if isinstance(hint, dict):
                        hints.append(_normalize_hint(hint, source_path=source_path, source_schema=schema, location=location))
            outputs = value.get("outputs")
            if isinstance(outputs, dict):
                for key, item in outputs.items():
                    visit(item, f"{location}.outputs.{key}")
            for key in ["passport", "qoi", "compiled_hints", "fluent_hints"]:
                if isinstance(value.get(key), dict):
                    visit(value[key], f"{location}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{location}[{index}]")

    visit(payload, "$")
    return hints, sorted(set(schemas))


def _normalize_hint(hint: dict[str, Any], *, source_path: Path, source_schema: str | None, location: str) -> dict[str, Any]:
    evidence = hint.get("evidence", [])
    if isinstance(evidence, str):
        evidence = [evidence]
    normalized = {
        "category": hint.get("category"),
        "recommendation": hint.get("recommendation"),
        "evidence": list(evidence) if isinstance(evidence, list) else [],
        "blocked": bool(hint.get("blocked", False)),
        "source_artifact": str(source_path),
        "source_schema": source_schema,
        "source_location": location,
    }
    for key in ["priority", "notes"]:
        if key in hint:
            normalized[key] = hint[key]
    return normalized


def _compiler_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# FastFluent Fluent Setup Hints",
        "",
        f"Status: `{report['status']}`",
        f"Hint count: `{report['hint_count']}`",
        "",
        "## Hints",
        "",
    ]
    for hint in report["hints"]:
        lines.append(f"- `{hint['category']}`: {hint['recommendation']} (source: `{hint['source_schema']}`)")
    if report["blocking_errors"]:
        lines.extend(["", "## Blocking Errors", ""])
        lines.extend(f"- {error}" for error in report["blocking_errors"])
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
