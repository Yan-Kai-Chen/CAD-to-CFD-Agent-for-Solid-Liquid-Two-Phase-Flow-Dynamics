"""FastCFD environment and FastFluent source preflight checks."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import platform
import shutil
from typing import Any

from fromcad2cfd_cad import AgentResult

from .capabilities import capability_inventory


SOURCE_ROOT_ENV_VARS = ("FROMCAD2CFD_FASTFLUENT_ROOT", "FASTFLUENT_ROOT")


@dataclass(frozen=True)
class FastCFDPreflightReport:
    """Environment report for optional FastFluent execution."""

    status: str
    source_root: str | None
    source_root_status: str
    compiler: str | None
    make_tool: str | None
    wsl_command: str | None
    platform_system: str
    known_blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_root": self.source_root,
            "source_root_status": self.source_root_status,
            "compiler": self.compiler,
            "make_tool": self.make_tool,
            "wsl_command": self.wsl_command,
            "platform_system": self.platform_system,
            "known_blockers": self.known_blockers,
            "notes": self.notes,
        }


def _source_root_candidates(explicit: str | None = None) -> list[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    for env_name in SOURCE_ROOT_ENV_VARS:
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _find_source_root(explicit: str | None = None) -> Path | None:
    for candidate in _source_root_candidates(explicit):
        if (candidate / "src").is_dir() and (candidate / "examples").is_dir():
            return candidate
    return None


def _find_first(*commands: str) -> str | None:
    for command in commands:
        found = shutil.which(command)
        if found:
            return found
    return None


def _known_blockers(source_root: Path | None) -> list[str]:
    blockers: list[str] = []
    if platform.system() == "Windows" and source_root:
        field_header = source_root / "src" / "data_struct" / "field.h"
        content = field_header.read_text(encoding="utf-8", errors="ignore") if field_header.exists() else ""
        has_posix_mmap = "sys/mman.h" in content
        has_windows_fallback = "Windows native builds do not provide POSIX" in content
        if has_posix_mmap and not has_windows_fallback:
            blockers.append(
                "Native Windows builds may fail because src/data_struct/field.h includes POSIX sys/mman.h. "
                "Patch the FastFluent source interface or build through a Linux-compatible toolchain."
            )
    return blockers


def detect_fastcfd_environment(source_root: str | None = None) -> FastCFDPreflightReport:
    root = _find_source_root(source_root)
    compiler = _find_first("g++", "c++", "cl")
    make_tool = _find_first("mingw32-make", "make", "nmake")
    wsl_command = _find_first("wsl")
    blockers = _known_blockers(root)
    notes = [
        "Mock backend is available without FastFluent.",
        "Real backend execution will remain template-limited and validation-gated.",
    ]
    if not root:
        return FastCFDPreflightReport(
            status="skipped",
            source_root=None,
            source_root_status="missing",
            compiler=compiler,
            make_tool=make_tool,
            wsl_command=wsl_command,
            platform_system=platform.system(),
            known_blockers=blockers,
            notes=notes + ["Set FROMCAD2CFD_FASTFLUENT_ROOT or FASTFLUENT_ROOT to enable real backend checks."],
        )
    status = "success" if compiler and make_tool and not blockers else "partial"
    return FastCFDPreflightReport(
        status=status,
        source_root=str(root),
        source_root_status="found",
        compiler=compiler,
        make_tool=make_tool,
        wsl_command=wsl_command,
        platform_system=platform.system(),
        known_blockers=blockers,
        notes=notes,
    )


def run_preflight(source_root: str | None = None) -> AgentResult:
    report = detect_fastcfd_environment(source_root)
    status = "success" if report.status == "success" else ("skipped" if report.status == "skipped" else "partial")
    return AgentResult(
        status=status,
        backend="fastcfd",
        operation="preflight",
        message="FastCFD preflight completed.",
        outputs={"preflight": report.to_dict(), "capabilities": capability_inventory()},
        metadata={"real_backend_available": report.status == "success"},
    )
