from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import require_under_workspace, unique_path


def write_json_report(path: Path, data: dict[str, Any]) -> Path:
    path = unique_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def write_markdown_report(path: Path, data: dict[str, Any]) -> Path:
    path = unique_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = require_under_workspace(path)

    lines = [
        f"# {data.get('title', 'SolidWorks Agent Report')}",
        "",
        f"Timestamp: `{data.get('timestamp')}`",
        f"Status: `{data.get('status')}`",
        "",
    ]

    summary = data.get("summary")
    if summary:
        lines.extend(["## Summary", ""])
        if isinstance(summary, list):
            lines.extend([f"- {item}" for item in summary])
        else:
            lines.append(str(summary))
        lines.append("")

    outputs = data.get("outputs") or {}
    if outputs:
        lines.extend(["## Outputs", ""])
        for key, value in outputs.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")

    steps = data.get("steps") or []
    if steps:
        lines.extend(["## Steps", ""])
        for step in steps:
            lines.append(f"### {step.get('name', 'step')}")
            lines.append("")
            lines.append(f"- Success: `{step.get('success')}`")
            if step.get("message"):
                lines.append(f"- Message: {step['message']}")
            details = step.get("details")
            if details is not None:
                lines.extend(["", "```json", json.dumps(details, ensure_ascii=False, indent=2), "```"])
            lines.append("")

    error = data.get("error")
    if error:
        lines.extend(["## Error", "", "```text", str(error), "```", ""])

    path.write_text("\n".join(lines), encoding="utf-8")
    return path

