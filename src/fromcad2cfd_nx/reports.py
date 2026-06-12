"""Report writers for NX backend results."""

from __future__ import annotations

import json
from pathlib import Path

from fromcad2cfd_cad import AgentResult

from .paths import project_reports_dir, timestamp, unique_path


def write_result_reports(result: AgentResult, *, project: str = "nx_test_project") -> dict[str, str]:
    report_dir = project_reports_dir(project)
    base = f"nx_{result.operation}_{timestamp()}"
    json_path = unique_path(report_dir / f"{base}.json")
    md_path = unique_path(report_dir / f"{base}.md")
    json_path.write_text(json.dumps(result.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(_result_markdown(result), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _result_markdown(result: AgentResult) -> str:
    lines = [
        "# Siemens NX Backend Result",
        "",
        f"Status: `{result.status}`",
        f"Operation: `{result.operation}`",
        f"Message: {result.message}",
        "",
        "## Outputs",
        "",
    ]
    if result.outputs:
        for key, value in result.outputs.items():
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- None")
    lines.extend(["", "## Errors", ""])
    if result.errors:
        lines.extend([f"- {error}" for error in result.errors])
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)
