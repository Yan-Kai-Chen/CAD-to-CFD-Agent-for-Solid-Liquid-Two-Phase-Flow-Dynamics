"""NX journal result parsing helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult


def parse_result_file(path: str | Path) -> AgentResult:
    result_path = Path(path)
    payload: dict[str, Any] = json.loads(result_path.read_text(encoding="utf-8"))
    return AgentResult(
        status=payload.get("status", "failed"),
        backend="nx",
        operation=str(payload.get("operation") or "journal"),
        message=str(payload.get("message") or ""),
        outputs=payload.get("outputs") or {},
        reports=payload.get("reports") or {},
        errors=payload.get("errors") or [],
        metadata=payload.get("metadata") or {},
    )
