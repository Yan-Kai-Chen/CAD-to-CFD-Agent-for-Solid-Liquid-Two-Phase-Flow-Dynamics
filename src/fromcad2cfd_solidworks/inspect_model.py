from __future__ import annotations

from typing import Any


def com_attr_or_call(obj: object, name: str) -> object:
    value = getattr(obj, name)
    if callable(value):
        return value()
    return value


def list_features(doc: Any, limit: int = 200) -> list[dict[str, object]]:
    features: list[dict[str, object]] = []
    try:
        feature = getattr(doc, "FirstFeature")
    except Exception:
        feature = None

    count = 0
    while feature is not None and count < limit:
        item: dict[str, object] = {}
        try:
            item["name"] = str(com_attr_or_call(feature, "Name"))
        except Exception:
            item["name"] = None
        try:
            item["type"] = str(com_attr_or_call(feature, "GetTypeName2"))
        except Exception:
            item["type"] = None
        try:
            suppressed = getattr(feature, "IsSuppressed2")
            item["suppressed"] = bool(suppressed(0, None)) if callable(suppressed) else None
        except Exception:
            item["suppressed"] = None
        features.append(item)
        count += 1
        try:
            feature = getattr(feature, "GetNextFeature")
        except Exception:
            break
    return features


def document_inventory(doc: Any) -> dict[str, object]:
    try:
        title = str(com_attr_or_call(doc, "GetTitle"))
    except Exception:
        title = None
    try:
        path = str(com_attr_or_call(doc, "GetPathName"))
    except Exception:
        path = None
    return {
        "title": title,
        "path": path,
        "features": list_features(doc),
    }

