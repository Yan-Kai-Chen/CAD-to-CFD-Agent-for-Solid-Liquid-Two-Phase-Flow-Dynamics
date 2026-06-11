"""Shared lightweight result conventions."""

from __future__ import annotations

from typing import Any


def ok_result(**payload: Any) -> dict[str, Any]:
    return {"status": "success", **payload}


def failed_result(message: str, **payload: Any) -> dict[str, Any]:
    return {"status": "failed", "error": message, **payload}
