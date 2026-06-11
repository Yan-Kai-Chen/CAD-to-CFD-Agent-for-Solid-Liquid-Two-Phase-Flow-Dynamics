from __future__ import annotations

import json
import math
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
WORKSPACE_ROOT = THIS_FILE.parents[3]
TOOL_ROOT = WORKSPACE_ROOT / "src"
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))

from fromcad2cfd_solidworks.connection import connect_solidworks
from fromcad2cfd_solidworks.documents import close_document, save_as
from fromcad2cfd_solidworks.geometry import (
    body_info,
    create_circular_boss,
    get_solid_bodies,
    move_copy_body,
    solid_body_inventory,
    solid_body_volume_indices,
)
from fromcad2cfd_solidworks.inspect_model import com_attr_or_call
from fromcad2cfd_solidworks.rebuild import rebuild_document


PROJECT_ROOT = WORKSPACE_ROOT / "05_projects" / "example_cylindrical_fluid_domain"
INPUT_PATH = PROJECT_ROOT / "input" / "device_model.x_t"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORT_DIR = PROJECT_ROOT / "reports"

RADIUS_MM = 500.0
HEIGHT_MM = 1200.0
AXIS = "Z"
SWBODYCUT = 15902


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def progress(message: str) -> None:
    print(f"[fluid-domain] {datetime.now().strftime('%H:%M:%S')} {message}", flush=True)


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 1
    while True:
        candidate = parent / f"{stem}_{index:02d}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def box_dims_m(box: list[float]) -> list[float]:
    if len(box) != 6:
        return []
    return [abs(box[3] - box[0]), abs(box[4] - box[1]), abs(box[5] - box[2])]


def box_center_m(box: list[float]) -> list[float]:
    if len(box) != 6:
        return []
    return [(box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2]


def cylinder_score(info: dict[str, Any]) -> float:
    dims = sorted(box_dims_m([float(v) for v in info.get("box_m") or []]))
    expected = sorted([1.0, 1.0, 1.2])
    if len(dims) != 3:
        return float("inf")
    return sum(abs(a - b) for a, b in zip(dims, expected))


def find_cylinder_index(doc: Any) -> int:
    records = solid_body_volume_indices(doc)
    if not records:
        raise RuntimeError("No solid bodies found while locating cylinder.")
    return min(records, key=lambda item: cylinder_score(item[2]))[0]


def select_body_with_mark(doc: Any, body: Any, *, append: bool, mark: int) -> dict[str, Any]:
    import pythoncom
    import win32com.client

    attempts: list[str] = []
    selection_ids: list[str] = []
    for attr_name in ("GetSelectionId", "Name"):
        try:
            value = com_attr_or_call(body, attr_name)
            if value:
                selection_ids.append(str(value))
        except Exception as exc:
            attempts.append(f"{attr_name}: {type(exc).__name__}: {exc}")

    callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    for selection_id in selection_ids:
        try:
            ok = bool(doc.Extension.SelectByID2(selection_id, "SOLIDBODY", 0, 0, 0, append, mark, callout, 0))
            if ok:
                return {"success": True, "method": "Extension.SelectByID2", "selection_id": selection_id, "mark": mark}
            attempts.append(f"SelectByID2 {selection_id!r} returned false")
        except Exception as exc:
            attempts.append(f"SelectByID2 {selection_id!r}: {type(exc).__name__}: {exc}")

    try:
        sel_data = doc.SelectionManager.CreateSelectData()
        sel_data.Mark = int(mark)
        ok = bool(body.Select2(bool(append), sel_data))
        if ok:
            return {"success": True, "method": "Body.Select2(CreateSelectData)", "mark": mark}
        attempts.append("Body.Select2(CreateSelectData) returned false")
    except Exception as exc:
        attempts.append(f"Body.Select2(CreateSelectData): {type(exc).__name__}: {exc}")

    return {"success": False, "mark": mark, "attempts": attempts}


def combine_subtract_selected_only(doc: Any, *, main_body_index: int, tool_body_indices: list[int]) -> dict[str, Any]:
    import pythoncom

    bodies = get_solid_bodies(doc)
    if main_body_index < 0 or main_body_index >= len(bodies):
        raise RuntimeError(f"Main body index {main_body_index} out of range for {len(bodies)} bodies.")
    if not tool_body_indices:
        raise RuntimeError("No tool bodies supplied.")

    try:
        doc.ClearSelection2(True)
    except Exception:
        pass

    main_body = bodies[main_body_index]
    main_selection = select_body_with_mark(doc, main_body, append=False, mark=1)
    if not main_selection.get("success"):
        raise RuntimeError(f"Could not select main body with mark=1: {main_selection}")

    tool_selections = []
    for index in tool_body_indices:
        if index < 0 or index >= len(bodies):
            raise RuntimeError(f"Tool body index {index} out of range for {len(bodies)} bodies.")
        selection = select_body_with_mark(doc, bodies[index], append=True, mark=2)
        tool_selections.append(selection)
        if not selection.get("success"):
            raise RuntimeError(f"Could not select tool body {index} with mark=2: {selection}")

    attempts: list[str] = []
    for label, main_arg, tool_arg in [
        ("selected_pythoncom_nothing", pythoncom.Nothing, pythoncom.Nothing),
        ("selected_none", None, None),
    ]:
        try:
            feat = doc.FeatureManager.InsertCombineFeature(SWBODYCUT, main_arg, tool_arg)
            if feat:
                return {
                    "success": True,
                    "method": "FeatureManager.InsertCombineFeature",
                    "argument_mode": label,
                    "operation": "subtract",
                    "main_body_index": main_body_index,
                    "tool_body_indices": tool_body_indices,
                    "main_body": body_info(main_body),
                    "tool_bodies": [body_info(bodies[index]) for index in tool_body_indices],
                    "main_selection": main_selection,
                    "tool_selections": tool_selections,
                }
            attempts.append(f"{label} returned None")
        except Exception as exc:
            attempts.append(f"{label}: {type(exc).__name__}: {exc}")

    raise RuntimeError("Selected-only Combine/Subtract failed. " + " | ".join(attempts))


def save_report(report: dict[str, Any], ts: str) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = unique_path(REPORT_DIR / f"fluid_domain_{ts}.json")
    md_path = unique_path(REPORT_DIR / f"fluid_domain_{ts}.md")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Phase11 Cylindrical Fluid Domain Report",
        "",
        f"- Timestamp: `{report.get('timestamp')}`",
        f"- Status: `{report.get('status')}`",
        f"- Input: `{report.get('input_path')}`",
        f"- Cylinder axis: `{AXIS}`",
        f"- Cylinder radius: `{RADIUS_MM} mm`",
        f"- Cylinder height: `{HEIGHT_MM} mm`",
        "- Cylinder center: `(0, 0, 0)`",
        "- Cylinder Z range: `-600 mm` to `+600 mm`",
        "",
        "## Results",
        "",
        f"- Import success: `{report.get('import_success')}`",
        f"- Boolean success: `{report.get('boolean_success')}`",
        f"- Rebuild success: `{report.get('rebuild_success')}`",
        f"- Export success: `{report.get('export_success')}`",
        "",
        "## Output Files",
        "",
    ]
    for item in report.get("outputs", []):
        lines.append(f"- `{item.get('path')}` ({item.get('size', 0)} bytes)")
    if report.get("errors"):
        lines.extend(["", "## Errors", ""])
        for item in report["errors"]:
            lines.append(f"- `{item}`")
    if report.get("recommendations"):
        lines.extend(["", "## Recommendations", ""])
        for item in report["recommendations"]:
            lines.append(f"- {item}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def load_parasolid(sw_app: Any, path: Path, report: dict[str, Any]) -> Any:
    attempts: list[dict[str, Any]] = []
    arg_strings = ["B", "", "C", "D"]
    for pass_index, delay_s in enumerate([0, 2, 5], start=1):
        if delay_s:
            progress(f"Waiting {delay_s}s before LoadFile4 retry pass {pass_index}")
            time.sleep(delay_s)
        for arg in arg_strings:
            try:
                progress(f"Trying LoadFile4 pass={pass_index} arg={arg!r}")
                loaded = sw_app.LoadFile4(str(path), arg, None, 0)
                active = sw_app.ActiveDoc
                title = ""
                try:
                    title = str(com_attr_or_call(active, "GetTitle")) if active else ""
                except Exception:
                    pass
                attempt = {
                    "method": "ISldWorks.LoadFile4",
                    "pass": pass_index,
                    "arg_string": arg,
                    "returned_object": bool(loaded),
                    "active_doc": bool(active),
                    "active_title": title,
                }
                attempts.append(attempt)
                if active:
                    report["import_attempts"] = attempts
                    return active
            except Exception as exc:
                attempts.append(
                    {
                        "method": "ISldWorks.LoadFile4",
                        "pass": pass_index,
                        "arg_string": arg,
                        "exception": f"{type(exc).__name__}: {exc}",
                    }
                )

    report["import_attempts"] = attempts
    raise RuntimeError(f"LoadFile4 failed for all controlled arg strings: {attempts}")


def main() -> int:
    ts = timestamp()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "timestamp": ts,
        "status": "started",
        "workspace_root": str(WORKSPACE_ROOT),
        "input_path": str(INPUT_PATH),
        "input_exists": INPUT_PATH.exists(),
        "input_size": INPUT_PATH.stat().st_size if INPUT_PATH.exists() else None,
        "cylinder": {
            "axis": AXIS,
            "radius_mm": RADIUS_MM,
            "diameter_mm": RADIUS_MM * 2,
            "height_mm": HEIGHT_MM,
            "center_mm": [0.0, 0.0, 0.0],
            "z_min_mm": -HEIGHT_MM / 2,
            "z_max_mm": HEIGHT_MM / 2,
        },
        "import_success": False,
        "boolean_success": False,
        "rebuild_success": False,
        "export_success": False,
        "outputs": [],
        "errors": [],
        "recommendations": [],
    }

    doc = None
    sw_app = None
    try:
        if not INPUT_PATH.exists():
            raise FileNotFoundError(INPUT_PATH)

        progress("Connecting to SOLIDWORKS")
        connection = connect_solidworks(visible=True, allow_launch=True)
        sw_app = connection.app
        report["connection"] = {
            "launched_by_agent": connection.launched_by_agent,
            "attached_to_running_process": connection.attached_to_running_process,
        }
        try:
            report["solidworks_revision"] = str(com_attr_or_call(sw_app, "RevisionNumber"))
        except Exception:
            pass

        progress("Importing Parasolid device")
        doc = load_parasolid(sw_app, INPUT_PATH, report)
        report["import_success"] = True
        report["inventory_after_import"] = solid_body_inventory(doc)
        imported_count = int(report["inventory_after_import"]["solid_body_count"])
        if imported_count < 1:
            raise RuntimeError("Imported document has no solid bodies.")

        progress("Creating 1000 mm diameter x 1200 mm cylinder")
        report["create_cylinder"] = create_circular_boss(
            doc,
            radius_mm=RADIUS_MM,
            depth_mm=HEIGHT_MM,
            center_x_mm=0.0,
            center_y_mm=0.0,
            plane="Front",
            merge_result=False,
        )
        report["inventory_after_cylinder_create"] = solid_body_inventory(doc)

        progress("Moving cylinder to center at origin")
        cylinder_index_before_move = find_cylinder_index(doc)
        report["cylinder_index_before_move"] = cylinder_index_before_move
        report["move_cylinder_to_origin"] = move_copy_body(
            doc,
            body_index=cylinder_index_before_move,
            translate_mm=(0.0, 0.0, -HEIGHT_MM / 2),
            rotate_deg=(0.0, 0.0, 0.0),
            copy=False,
        )
        report["inventory_after_cylinder_move"] = solid_body_inventory(doc)

        progress("Subtracting device bodies from cylinder")
        cylinder_index = find_cylinder_index(doc)
        bodies_before_boolean = solid_body_inventory(doc)
        tool_indices = [idx for idx in range(int(bodies_before_boolean["solid_body_count"])) if idx != cylinder_index]
        if not tool_indices:
            raise RuntimeError("No device tool bodies available for subtraction.")
        report["cylinder_index_for_boolean"] = cylinder_index
        report["tool_body_indices_for_boolean"] = tool_indices

        report["combine_subtract"] = combine_subtract_selected_only(
            doc,
            main_body_index=cylinder_index,
            tool_body_indices=tool_indices,
        )
        report["boolean_success"] = True
        report["inventory_after_boolean"] = solid_body_inventory(doc)

        progress("Rebuilding document")
        report["rebuild"] = rebuild_document(doc)
        report["rebuild_success"] = True

        outputs = [
            ("sldprt", OUTPUT_DIR / f"fluid_domain_{ts}.SLDPRT"),
            ("parasolid", OUTPUT_DIR / f"fluid_domain_{ts}.x_t"),
            ("step", OUTPUT_DIR / f"fluid_domain_{ts}.STEP"),
        ]
        for label, raw_path in outputs:
            progress(f"Saving {label} output")
            out_path = unique_path(raw_path)
            result = save_as(doc, out_path)
            result["label"] = label
            report["outputs"].append(result)
        report["export_success"] = all(Path(item["path"]).exists() and item.get("size", 0) > 0 for item in report["outputs"])
        report["status"] = "success" if report["export_success"] else "partial_export"

    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        report["traceback"] = traceback.format_exc()
        report["recommendations"].extend(
            [
                "If import failed, open the Parasolid manually in SOLIDWORKS and save a project-local .SLDPRT copy, then rerun the boolean step from that .SLDPRT.",
                "If Boolean subtract failed, inspect whether the device solid fully intersects the cylinder and whether imported bodies are valid solids.",
                "For Fluent handoff, STEP is still preferred after a successful Boolean because it preserves analytic CAD geometry better than STL.",
            ]
        )
    finally:
        if doc is not None and sw_app is not None:
            try:
                close_document(sw_app, doc, save=False)
            except Exception as exc:
                report.setdefault("close_errors", []).append(f"{type(exc).__name__}: {exc}")

    json_path, md_path = save_report(report, ts)
    print(json.dumps({"status": report["status"], "json": str(json_path), "md": str(md_path), "outputs": report["outputs"], "errors": report["errors"]}, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

