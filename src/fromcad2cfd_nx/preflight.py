"""Local Siemens NX preflight detection."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Iterable

from fromcad2cfd_cad import AgentResult, CADBackendCapabilities

from .paths import logs_dir, timestamp, unique_path


ENV_NAMES = ("UGII_BASE_DIR", "UGII_ROOT_DIR", "NXBIN", "UGII_LANG", "SPLM_LICENSE_SERVER")


@dataclass(frozen=True)
class NXPreflightReport:
    """Detected local NX state."""

    status: str
    nx_base_dir: str | None
    nx_bin_dir: str | None
    run_journal: str | None
    ugraf: str | None
    env: dict[str, str | None] = field(default_factory=dict)
    candidates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def can_run_journal(self) -> bool:
        return bool(self.run_journal and Path(self.run_journal).exists())

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "nx_base_dir": self.nx_base_dir,
            "nx_bin_dir": self.nx_bin_dir,
            "run_journal": self.run_journal,
            "ugraf": self.ugraf,
            "env": self.env,
            "candidates": self.candidates,
            "warnings": self.warnings,
            "can_run_journal": self.can_run_journal,
        }


def _env_value(name: str) -> str | None:
    return (
        os.environ.get(name)
        or os.environ.get(name.upper())
        or os.environ.get(name.lower())
    )


def _known_base_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("UGII_BASE_DIR", "UGII_ROOT_DIR"):
        value = _env_value(env_name)
        if value:
            candidates.append(Path(value))

    nxbin = _env_value("NXBIN")
    if nxbin:
        nxbin_path = Path(nxbin)
        candidates.extend([nxbin_path, nxbin_path.parent])

    candidates.extend(
        [
            Path(r"C:\Program Files\Siemens\NX"),
            Path(r"C:\Program Files\Siemens\NX2300"),
            Path(r"C:\Program Files\Siemens\NX2406"),
            Path(r"C:\Program Files\Siemens\NX2506"),
        ]
    )
    return _dedupe_paths(candidates)


def _dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path)
        if key.lower() in seen:
            continue
        seen.add(key.lower())
        unique.append(path)
    return unique


def _nxbin_candidates(base: Path) -> list[Path]:
    return _dedupe_paths(
        [
            base,
            base / "NXBIN",
            base / "UGII",
            base.parent / "NXBIN",
        ]
    )


def _find_file(base_candidates: Iterable[Path], filename: str) -> Path | None:
    for base in base_candidates:
        for nxbin in _nxbin_candidates(base):
            candidate = nxbin / filename
            if candidate.exists():
                return candidate
    return None


def _base_from_tool(tool_path: Path | None) -> Path | None:
    if tool_path is None:
        return None
    parent = tool_path.parent
    if parent.name.upper() == "NXBIN":
        return parent.parent
    return parent


def detect_nx_environment(extra_base_dirs: Iterable[str | Path] = ()) -> NXPreflightReport:
    """Detect local NX paths without starting NX."""

    base_candidates = _dedupe_paths([Path(path) for path in extra_base_dirs] + _known_base_candidates())
    run_journal = _find_file(base_candidates, "run_journal.exe")
    ugraf = _find_file(base_candidates, "ugraf.exe")
    nx_base = _base_from_tool(run_journal) or _base_from_tool(ugraf)
    nx_bin = run_journal.parent if run_journal else (ugraf.parent if ugraf else None)
    env = {name: _env_value(name) for name in ENV_NAMES}
    warnings: list[str] = []

    env_base = env.get("UGII_BASE_DIR")
    if env_base and nx_base and Path(env_base).resolve() != nx_base.resolve():
        warnings.append("UGII_BASE_DIR does not match the detected NX base directory.")
    if not run_journal:
        warnings.append("run_journal.exe was not found.")
    if not ugraf:
        warnings.append("ugraf.exe was not found.")

    status = "success" if run_journal else ("partial" if ugraf or nx_base else "failed")
    return NXPreflightReport(
        status=status,
        nx_base_dir=str(nx_base) if nx_base else None,
        nx_bin_dir=str(nx_bin) if nx_bin else None,
        run_journal=str(run_journal) if run_journal else None,
        ugraf=str(ugraf) if ugraf else None,
        env=env,
        candidates=[str(path) for path in base_candidates],
        warnings=warnings,
    )


def capabilities_from_preflight(report: NXPreflightReport) -> CADBackendCapabilities:
    return CADBackendCapabilities(
        backend="nx",
        status=report.status,
        native_formats=("PRT",),
        export_formats=("STEP", "PARASOLID"),
        supports_parameter_editing=True,
        supports_batch_runner=report.can_run_journal,
        supports_interactive_session=bool(report.ugraf),
        notes="NXOpen journal runner is the preferred automation foundation.",
    )


def run_preflight(*, write_reports: bool = True) -> AgentResult:
    report = detect_nx_environment()
    outputs: dict[str, object] = {
        "preflight": report.to_dict(),
        "capabilities": capabilities_from_preflight(report).to_dict(),
    }
    reports: dict[str, str] = {}
    if write_reports:
        reports = write_preflight_reports(report)
    return AgentResult(
        status=report.status,
        backend="nx",
        operation="preflight",
        message="NX preflight completed." if report.status != "failed" else "NX preflight did not find a runnable NX installation.",
        outputs=outputs,
        reports=reports,
        errors=report.warnings if report.status == "failed" else [],
        metadata={"warnings": report.warnings},
    )


def write_preflight_reports(report: NXPreflightReport) -> dict[str, str]:
    stamp = timestamp()
    base = f"nx_preflight_{stamp}"
    json_path = unique_path(logs_dir() / f"{base}.json")
    md_path = unique_path(logs_dir() / f"{base}.md")
    payload = report.to_dict()
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(_preflight_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _preflight_markdown(report: NXPreflightReport) -> str:
    lines = [
        "# Siemens NX Preflight Report",
        "",
        f"Status: `{report.status}`",
        f"NX base directory: `{report.nx_base_dir}`",
        f"NX bin directory: `{report.nx_bin_dir}`",
        f"run_journal: `{report.run_journal}`",
        f"ugraf: `{report.ugraf}`",
        "",
        "## Environment",
        "",
    ]
    for key, value in report.env.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Warnings", ""])
    if report.warnings:
        lines.extend([f"- {warning}" for warning in report.warnings])
    else:
        lines.append("- None")
    lines.extend(["", "## Candidates", ""])
    lines.extend([f"- `{candidate}`" for candidate in report.candidates])
    lines.append("")
    return "\n".join(lines)
