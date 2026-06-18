"""Local HyperMesh runtime discovery."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


DEFAULT_ROOTS = [
    Path(r"C:\Program Files\Altair\2024"),
    Path(r"C:\Program Files\Altair\2022"),
]


def locate_hypermesh_runtime(extra_roots: list[str] | None = None) -> dict[str, Any]:
    """Locate installed HyperMesh executables without launching a solver."""

    roots = [Path(item) for item in extra_roots or []] + _registry_roots() + DEFAULT_ROOTS
    env_root = os.environ.get("ALTAIR_HOME") or os.environ.get("HW_ROOTDIR")
    if env_root:
        roots.insert(0, Path(env_root))
    seen: set[Path] = set()
    candidates: list[dict[str, Any]] = []
    for root in roots:
        root = root.expanduser()
        if root in seen:
            continue
        seen.add(root)
        if not root.exists():
            continue
        candidates.append(_candidate_from_root(root))
    candidates.sort(key=lambda item: (_version_hint(str(item["root"])), item["status"] == "complete"), reverse=True)
    best = next((item for item in candidates if item["status"] == "complete"), None)
    return {
        "status": "found" if best else "not_found",
        "best": best,
        "candidates": candidates,
    }


def _candidate_from_root(root: Path) -> dict[str, Any]:
    hmbatch = _first_existing(
        [
            root / "hwdesktop" / "hm" / "bin" / "win64" / "hmbatch.exe",
            root / "hwdesktop" / "hw" / "bin" / "win64" / "hmbatch.exe",
        ]
    )
    hmopengl = _first_existing(
        [
            root / "hwdesktop" / "hm" / "bin" / "win64" / "hmopengl.exe",
            root / "hwdesktop" / "hw" / "bin" / "win64" / "hmopengl.exe",
        ]
    )
    runhwx = _first_existing(
        [
            root / "hwdesktop" / "hwx" / "bin" / "win64" / "runhwx.exe",
            root / "common" / "framework" / "win64" / "hwx" / "bin" / "win64" / "runhwx.exe",
        ]
    )
    return {
        "root": str(root),
        "status": "complete" if hmbatch and runhwx else "partial",
        "hmbatch": str(hmbatch) if hmbatch else None,
        "hmopengl": str(hmopengl) if hmopengl else None,
        "runhwx": str(runhwx) if runhwx else None,
        "hypermesh_cfd_arguments": "-client HyperWorksDesktop -plugin HyperworksCFD -profile AltairCFD -l en",
    }


def _first_existing(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def _version_hint(text: str) -> int:
    matches = [int(item) for item in re.findall(r"20\d{2}", text)]
    return max(matches) if matches else 0


def _registry_roots() -> list[Path]:
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:
        return []
    roots: list[Path] = []
    uninstall_roots = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for uninstall_root in uninstall_roots:
            try:
                with winreg.OpenKey(hive, uninstall_root) as root_key:
                    for index in range(winreg.QueryInfoKey(root_key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(root_key, index)
                            with winreg.OpenKey(root_key, subkey_name) as subkey:
                                name = _query_reg_string(winreg, subkey, "DisplayName")
                                install = _query_reg_string(winreg, subkey, "InstallLocation")
                        except OSError:
                            continue
                        if name and install and ("Altair" in name or "HyperMesh" in name or "HyperWorks" in name):
                            roots.append(Path(install))
            except OSError:
                continue
    return roots


def _query_reg_string(winreg: Any, key: Any, value_name: str) -> str | None:
    try:
        value, _ = winreg.QueryValueEx(key, value_name)
    except OSError:
        return None
    return str(value) if value else None
