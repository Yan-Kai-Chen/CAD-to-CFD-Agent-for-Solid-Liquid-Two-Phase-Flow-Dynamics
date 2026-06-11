from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import SolidWorksConnectionError
from .paths import default_templates, solidworks_exe_path


def _has_sldworks_process() -> bool:
    proc = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"],
        capture_output=True,
        text=True,
        check=False,
    )
    return "SLDWORKS.exe" in proc.stdout


def _com_attr_or_call(obj: object, name: str) -> object:
    value = getattr(obj, name)
    if callable(value):
        return value()
    return value


@dataclass
class SolidWorksConnection:
    app: Any
    launched_by_agent: bool
    attached_to_running_process: bool


def connect_solidworks(visible: bool = True, allow_launch: bool = True) -> SolidWorksConnection:
    try:
        import win32com.client
    except Exception as exc:  # pragma: no cover - environment dependent
        raise SolidWorksConnectionError(f"pywin32 is not available: {exc}") from exc

    had_process = _has_sldworks_process()
    try:
        app = win32com.client.GetActiveObject("SldWorks.Application")
        attached = True
        launched = False
    except Exception:
        if not allow_launch:
            raise SolidWorksConnectionError("SolidWorks is not active and launching is disabled.")
        try:
            app = win32com.client.Dispatch("SldWorks.Application")
        except Exception as exc:
            raise SolidWorksConnectionError(f"Failed to dispatch SldWorks.Application: {exc}") from exc
        attached = had_process
        launched = not had_process

    try:
        app.Visible = bool(visible)
    except Exception:
        pass

    return SolidWorksConnection(app=app, launched_by_agent=launched, attached_to_running_process=attached)


def preflight(visible: bool = False, allow_launch: bool = True, close_if_launched: bool = True) -> dict[str, Any]:
    connection = connect_solidworks(visible=visible, allow_launch=allow_launch)
    app = connection.app
    result: dict[str, Any] = {
        "connected": True,
        "launched_by_agent": connection.launched_by_agent,
        "attached_to_running_process": connection.attached_to_running_process,
        "revision_number": None,
        "document_count": None,
        "executable_path": None,
        "solidworks_exe_expected": str(solidworks_exe_path()) if solidworks_exe_path() else None,
        "templates": {key: str(value) if value else None for key, value in default_templates().items()},
    }

    try:
        result["revision_number"] = _com_attr_or_call(app, "RevisionNumber")
    except Exception as exc:
        result["revision_error"] = f"{type(exc).__name__}: {exc}"

    try:
        result["document_count"] = _com_attr_or_call(app, "GetDocumentCount")
    except Exception as exc:
        result["document_count_error"] = f"{type(exc).__name__}: {exc}"

    try:
        result["executable_path"] = str(Path(str(_com_attr_or_call(app, "GetExecutablePath"))))
    except Exception as exc:
        result["executable_path_error"] = f"{type(exc).__name__}: {exc}"

    if close_if_launched and connection.launched_by_agent:
        try:
            app.ExitApp()
            result["exit_app_called"] = True
        except Exception as exc:
            result["exit_app_error"] = f"{type(exc).__name__}: {exc}"

    return result

