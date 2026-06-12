"""Local workspace paths for NX backend runtime artifacts."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path


REPO_ROOT = Path(__file__).absolute().parents[2]
_workspace_override = os.environ.get("FROMCAD2CFD_WORKSPACE_ROOT")
if _workspace_override:
    WORKSPACE_ROOT = Path(_workspace_override)
else:
    WORKSPACE_ROOT = REPO_ROOT.parent.parent if REPO_ROOT.parent.name == "10_github" else REPO_ROOT
PROJECTS_ROOT = WORKSPACE_ROOT / "05_projects"
DEFAULT_PROJECT = "nx_test_project"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def logs_dir() -> Path:
    path = WORKSPACE_ROOT / "06_logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_root(project: str = DEFAULT_PROJECT) -> Path:
    path = PROJECTS_ROOT / project
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_input_dir(project: str = DEFAULT_PROJECT) -> Path:
    path = project_root(project) / "input"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_output_dir(project: str = DEFAULT_PROJECT) -> Path:
    path = project_root(project) / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_reports_dir(project: str = DEFAULT_PROJECT) -> Path:
    path = project_root(project) / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def unique_path(path: Path) -> Path:
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
