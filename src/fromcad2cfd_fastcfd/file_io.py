"""Small file-IO helpers for FastFluent artifact writers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from typing import Any


def write_json_file(path: str | Path, payload: Any) -> Path:
    """Write JSON while keeping manifests on normal, readable paths."""

    target = Path(path)
    ensure_dir(target.parent)
    with open(_windows_long_path(target), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2))
    return target


def write_text_file(path: str | Path, text: str) -> Path:
    """Write text artifacts safely under deep Windows project roots."""

    target = Path(path)
    ensure_dir(target.parent)
    with open(_windows_long_path(target), "w", encoding="utf-8") as handle:
        handle.write(text)
    return target


def read_json_file(path: str | Path) -> Any:
    """Read JSON through the same Windows long-path shim used for writes."""

    source = Path(path)
    with open(_windows_long_path(source), "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text_file(path: str | Path) -> str:
    """Read text through the same Windows long-path shim used for writes."""

    source = Path(path)
    with open(_windows_long_path(source), "r", encoding="utf-8") as handle:
        return handle.read()


def copy_file(source: str | Path, target: str | Path) -> Path:
    """Copy a file using extended Windows paths for actual IO."""

    destination = Path(target)
    ensure_dir(destination.parent)
    shutil.copyfile(_windows_long_path(Path(source)), _windows_long_path(destination))
    return destination


def path_is_file(path: str | Path) -> bool:
    """Return True if a path is a file, including deep Windows paths."""

    return os.path.isfile(_windows_long_path(Path(path)))


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    os.makedirs(_windows_long_path(target), exist_ok=True)
    return target


def _windows_long_path(path: Path) -> str:
    if os.name != "nt":
        return str(path.resolve())
    text = os.path.abspath(os.fspath(path))
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text
