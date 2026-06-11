from __future__ import annotations

from typing import Any

from .errors import SolidWorksOperationError


def rebuild_document(doc: Any) -> dict[str, object]:
    attempts: list[dict[str, object]] = []

    for name, call in [
        ("ForceRebuild3", lambda: doc.ForceRebuild3(False)),
        ("EditRebuild3", lambda: doc.EditRebuild3()),
    ]:
        try:
            value = call()
            attempts.append({"method": name, "success": bool(value), "raw": str(value)})
            if bool(value):
                return {"success": True, "method": name, "attempts": attempts}
        except Exception as exc:
            attempts.append({"method": name, "success": False, "error": f"{type(exc).__name__}: {exc}"})

    raise SolidWorksOperationError(f"Rebuild failed: {attempts}")

