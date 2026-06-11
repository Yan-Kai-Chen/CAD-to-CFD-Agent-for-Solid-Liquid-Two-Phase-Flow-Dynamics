from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from .errors import WorkspacePathError


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_ROOT = WORKSPACE_ROOT / "05_projects"
DEFAULT_PROJECT = "test_project"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def resolve_project(project: str = DEFAULT_PROJECT) -> Path:
    project_root = PROJECTS_ROOT / project
    project_root.mkdir(parents=True, exist_ok=True)
    return project_root


def project_output_dir(project: str = DEFAULT_PROJECT) -> Path:
    path = resolve_project(project) / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_reports_dir(project: str = DEFAULT_PROJECT) -> Path:
    path = resolve_project(project) / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = WORKSPACE_ROOT / "06_logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_under_workspace(path: Path) -> bool:
    try:
        full = path.resolve()
    except FileNotFoundError:
        full = path.absolute()
    root = WORKSPACE_ROOT.resolve()
    return full == root or root in full.parents


def require_under_workspace(path: Path) -> Path:
    full = path.absolute()
    if not is_under_workspace(full):
        raise WorkspacePathError(f"Path is outside workspace root: {full}")
    return full


def unique_path(path: Path) -> Path:
    path = require_under_workspace(path)
    if not path.exists():
        return path
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    index = 1
    while True:
        candidate = parent / f"{stem}_{index:02d}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def default_templates() -> dict[str, Path | None]:
    template_root = os.environ.get("SOLIDWORKS_TEMPLATE_DIR")
    candidates = {
        "part": [
            Path(template_root) / "Part.prtdot" if template_root else None,
            Path(template_root) / "gb_part.prtdot" if template_root else None,
            Path(r"C:\ProgramData\SolidWorks\SOLIDWORKS 2025\templates\gb_part.prtdot"),
            Path(r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates\gb_part.prtdot"),
        ],
        "assembly": [
            Path(template_root) / "Assembly.asmdot" if template_root else None,
            Path(template_root) / "gb_assembly.asmdot" if template_root else None,
            Path(r"C:\ProgramData\SolidWorks\SOLIDWORKS 2025\templates\gb_assembly.asmdot"),
            Path(r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates\gb_assembly.asmdot"),
        ],
        "drawing": [
            Path(template_root) / "Drawing.drwdot" if template_root else None,
            Path(template_root) / "gb_a4.drwdot" if template_root else None,
            Path(r"C:\ProgramData\SolidWorks\SOLIDWORKS 2025\templates\gb_a4.drwdot"),
            Path(r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates\gb_a4.drwdot"),
        ],
    }
    found: dict[str, Path | None] = {}
    for key, paths in candidates.items():
        found[key] = next((path for path in paths if path and path.exists()), None)
    return found


def solidworks_exe_path() -> Path | None:
    env_path = os.environ.get("SOLIDWORKS_EXE")
    if env_path:
        path = Path(env_path)
        return path if path.exists() else None
    candidates = [
        Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe"),
        Path(r"C:\Program Files\Dassault Systemes\SOLIDWORKS\SLDWORKS.exe"),
    ]
    return next((path for path in candidates if path.exists()), None)

