"""Fluent report monitor parsing utilities."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


MONITOR_PARSE_SCHEMA_VERSION = "fromcad2cfd_fluent_monitor_parse_v1"
NUMBER_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[Ee][-+]?\d+)?")


def parse_monitor_file(
    path: str | Path,
    *,
    min_columns: int = 2,
    column_names: list[str] | None = None,
    include_rows: bool = True,
) -> dict[str, Any]:
    source = Path(path)
    lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    detected_columns = column_names or _detect_columns(lines)
    rows: list[list[float]] = []
    for line in lines:
        values = [float(match.group(0)) for match in NUMBER_RE.finditer(line)]
        if len(values) >= min_columns:
            rows.append(values)
    first = rows[0] if rows else None
    last = rows[-1] if rows else None
    payload: dict[str, Any] = {
        "schema_version": MONITOR_PARSE_SCHEMA_VERSION,
        "status": "parsed" if rows else "empty",
        "path": str(source),
        "column_names": detected_columns,
        "row_count": len(rows),
        "first_row": _row_object(first, detected_columns),
        "last_row": _row_object(last, detected_columns),
    }
    if include_rows:
        payload["rows"] = [_row_object(row, detected_columns) for row in rows]
    return payload


def _detect_columns(lines: list[str]) -> list[str]:
    for line in lines:
        if line.strip().startswith("(") and '"' in line:
            names = re.findall(r'"([^"]+)"', line)
            if names:
                return names
    return []


def _row_object(row: list[float] | None, column_names: list[str]) -> dict[str, float] | list[float] | None:
    if row is None:
        return None
    if column_names and len(column_names) <= len(row):
        return {name: row[index] for index, name in enumerate(column_names)}
    return list(row)
