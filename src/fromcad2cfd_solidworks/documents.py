from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import SolidWorksOperationError
from .inspect_model import com_attr_or_call
from .paths import default_templates, require_under_workspace


def get_title(doc: Any) -> str:
    try:
        return str(com_attr_or_call(doc, "GetTitle"))
    except Exception:
        return ""


def get_path(doc: Any) -> str:
    try:
        return str(com_attr_or_call(doc, "GetPathName"))
    except Exception:
        return ""


def create_new_part(app: Any, template_path: Path | None = None) -> Any:
    template = template_path or default_templates()["part"]
    if not template or not template.exists():
        raise SolidWorksOperationError("Part template not found.")

    doc = app.NewDocument(str(template), 0, 0, 0)
    if doc is None:
        raise SolidWorksOperationError(f"SolidWorks failed to create a part with template: {template}")

    try:
        doc.ShowNamedView2("*Isometric", 7)
        doc.ViewZoomtofit2()
    except Exception:
        pass
    return doc


def open_part_document(app: Any, path: Path, *, silent: bool = True) -> dict[str, Any]:
    path = require_under_workspace(path)
    if not path.exists():
        raise SolidWorksOperationError(f"Part file does not exist: {path}")
    if path.suffix.lower() != ".sldprt":
        raise SolidWorksOperationError(f"Only .SLDPRT files are supported for part open: {path}")

    try:
        import pythoncom
        import win32com.client

        errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        options = 1 if silent else 0
        doc = app.OpenDoc6(str(path), 1, options, "", errors, warnings)
        if doc is None:
            raise SolidWorksOperationError(f"OpenDoc6 returned None for {path}; errors={errors.value}, warnings={warnings.value}")
        return {
            "doc": doc,
            "path": str(path),
            "method": "OpenDoc6",
            "errors": int(errors.value),
            "warnings": int(warnings.value),
        }
    except SolidWorksOperationError:
        raise
    except Exception as exc:
        raise SolidWorksOperationError(f"Open part failed: {type(exc).__name__}: {exc}") from exc


def save_current(doc: Any) -> dict[str, Any]:
    raw_path = get_path(doc)
    if not raw_path:
        raise SolidWorksOperationError("Cannot save current document because it has no path.")
    path = Path(raw_path)
    path = require_under_workspace(path)

    attempts: list[str] = []
    try:
        import pythoncom
        import win32com.client

        errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        ok = bool(doc.Save3(1, errors, warnings))
        if ok and int(errors.value) == 0:
            return {
                "path": str(path),
                "method": "Save3",
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
                "warnings": int(warnings.value),
            }
        attempts.append(f"Save3 returned ok={ok}, errors={errors.value}, warnings={warnings.value}")
    except Exception as exc:
        attempts.append(f"Save3: {type(exc).__name__}: {exc}")

    try:
        value = doc.Save()
        if path.exists():
            return {
                "path": str(path),
                "method": "Save",
                "raw": str(value),
                "exists": True,
                "size": path.stat().st_size,
            }
        attempts.append(f"Save returned {value!r} but path does not exist")
    except Exception as exc:
        attempts.append(f"Save: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Save current document failed. " + " | ".join(attempts))


def save_as(doc: Any, path: Path) -> dict[str, Any]:
    path = require_under_workspace(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SolidWorksOperationError(f"Refusing to overwrite existing file: {path}")

    method_errors: list[str] = []
    try:
        ok = bool(doc.SaveAs(str(path)))
        if ok:
            return {"path": str(path), "method": "SaveAs", "exists": path.exists(), "size": path.stat().st_size if path.exists() else 0}
    except Exception as exc:
        method_errors.append(f"SaveAs: {type(exc).__name__}: {exc}")

    try:
        import pythoncom
        import win32com.client

        errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        empty_export = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        ok = bool(doc.Extension.SaveAs(str(path), 0, 0, empty_export, errors, warnings))
        if ok and int(errors.value) == 0:
            return {
                "path": str(path),
                "method": "Extension.SaveAs",
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
                "warnings": int(warnings.value),
            }
        method_errors.append(f"Extension.SaveAs returned ok={ok}, errors={errors.value}, warnings={warnings.value}")
    except Exception as exc:
        method_errors.append(f"Extension.SaveAs: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Save failed; " + " | ".join(method_errors))


def close_document(app: Any, doc: Any, save: bool = False) -> dict[str, Any]:
    title = get_title(doc)
    if save:
        try:
            doc.Save3(0, 0, 0)
        except Exception as exc:
            raise SolidWorksOperationError(f"Save before close failed: {exc}") from exc
    if title:
        app.CloseDoc(title)
    return {"title": title, "save": save}

