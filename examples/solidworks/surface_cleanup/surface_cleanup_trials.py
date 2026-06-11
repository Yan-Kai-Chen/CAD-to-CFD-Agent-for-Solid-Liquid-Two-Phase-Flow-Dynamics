from __future__ import annotations

import json
import sys
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pythoncom
import win32com.client


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = WORKSPACE_ROOT / "05_projects" / "example_surface_cleanup_trials"
INPUT_PATH = PROJECT_ROOT / "input" / "device_model.x_t"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORT_DIR = PROJECT_ROOT / "reports"


def progress(message: str) -> None:
    print(f"[surface-cleanup] {datetime.now().strftime('%H:%M:%S')} {message}", flush=True)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def com_value(obj: Any, name: str) -> Any:
    value = getattr(obj, name)
    return value() if callable(value) else value


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def try_bool(obj: Any, name: str) -> bool | None:
    try:
        value = getattr(obj, name)
        return bool(value() if callable(value) else value)
    except Exception:
        return None


def try_float_call(obj: Any, name: str) -> float | None:
    try:
        value = getattr(obj, name)
        return float(value() if callable(value) else value)
    except Exception:
        return None


def try_raw_call(obj: Any, name: str) -> str | None:
    try:
        value = getattr(obj, name)
        return str(value() if callable(value) else value)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def connect_sw() -> Any:
    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
    except Exception:
        sw = win32com.client.Dispatch("SldWorks.Application")
    sw.Visible = True
    return sw


def close_doc_if_title(sw: Any, doc: Any) -> None:
    try:
        title = str(com_value(doc, "GetTitle"))
    except Exception:
        return
    if title.startswith(("device_model", "surface_cleanup_", "fluid_domain_")):
        try:
            sw.CloseDoc(title)
        except Exception:
            pass


def import_source(sw: Any, route: str) -> Any:
    progress(f"{route}: importing source")
    attempts = []
    for delay_s in (0, 2, 5, 10):
        if delay_s:
            time.sleep(delay_s)
        try:
            loaded = sw.LoadFile4(str(INPUT_PATH), "B", None, 0)
            doc = sw.ActiveDoc
            title = str(com_value(doc, "GetTitle")) if doc else ""
            attempts.append({"delay_s": delay_s, "returned": bool(loaded), "active": bool(doc), "title": title})
            if doc:
                return doc
        except Exception as exc:
            attempts.append({"delay_s": delay_s, "error": f"{type(exc).__name__}: {exc}"})
    raise RuntimeError(f"LoadFile4 failed: {attempts}")


def body_box(body: Any) -> dict[str, Any]:
    try:
        box = [float(item) for item in as_list(com_value(body, "GetBodyBox"))]
    except Exception:
        box = []
    out: dict[str, Any] = {"box_m": box}
    if len(box) == 6:
        out["dims_m"] = [abs(box[3] - box[0]), abs(box[4] - box[1]), abs(box[5] - box[2])]
        out["center_m"] = [(box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2]
    return out


def surface_kind(face: Any) -> str:
    try:
        surf = com_value(face, "GetSurface")
    except Exception:
        return "surface_unavailable"
    checks = [
        ("plane", "IsPlane"),
        ("cylinder", "IsCylinder"),
        ("cone", "IsCone"),
        ("sphere", "IsSphere"),
        ("torus", "IsTorus"),
        ("parametric", "IsParametric"),
    ]
    for label, method in checks:
        if try_bool(surf, method):
            return label
    return "other"


def curve_kind(edge: Any) -> str:
    try:
        curve = com_value(edge, "GetCurve")
    except Exception:
        return "curve_unavailable"
    checks = [
        ("line", "IsLine"),
        ("circle", "IsCircle"),
        ("ellipse", "IsEllipse"),
        ("parabola", "IsParabola"),
    ]
    for label, method in checks:
        if try_bool(curve, method):
            return label
    return "other"


def audit_doc(doc: Any, route: str, stage: str, *, classify_types: bool = True) -> dict[str, Any]:
    progress(f"{route}: auditing {stage}")
    solid_bodies = as_list(doc.GetBodies2(0, False))
    sheet_bodies = as_list(doc.GetBodies2(1, False))
    wire_bodies = as_list(doc.GetBodies2(2, False))
    audit: dict[str, Any] = {
        "route": route,
        "stage": stage,
        "doc_title": try_raw_call(doc, "GetTitle"),
        "doc_path": try_raw_call(doc, "GetPathName"),
        "body_counts": {"solid": len(solid_bodies), "sheet": len(sheet_bodies), "wire": len(wire_bodies)},
        "bodies": [],
    }
    for body_index, body in enumerate(solid_bodies):
        faces = as_list(com_value(body, "GetFaces"))
        edges = as_list(com_value(body, "GetEdges"))
        record: dict[str, Any] = {
            "index": body_index,
            "name": try_raw_call(body, "Name"),
            **body_box(body),
            "is_mesh_body": try_bool(body, "IsMeshBody"),
            "is_graphics_body": try_bool(body, "IsGraphicsBody"),
            "check": try_raw_call(body, "Check"),
            "check2": try_raw_call(body, "Check2"),
            "face_count": len(faces),
            "edge_count": len(edges),
            "surface_type_counts": {},
            "curve_type_counts": {},
            "smallest_face_areas_m2_sample": [],
        }
        if classify_types:
            surface_counts: Counter[str] = Counter()
            area_sample: list[float] = []
            for face_index, face in enumerate(faces):
                surface_counts[surface_kind(face)] += 1
                area = try_float_call(face, "GetArea")
                if area is not None:
                    area_sample.append(area)
                if face_index and face_index % 10000 == 0:
                    progress(f"{route}: {stage} body {body_index} classified {face_index}/{len(faces)} faces")
            curve_counts: Counter[str] = Counter()
            for edge_index, edge in enumerate(edges):
                curve_counts[curve_kind(edge)] += 1
                if edge_index and edge_index % 10000 == 0:
                    progress(f"{route}: {stage} body {body_index} classified {edge_index}/{len(edges)} edges")
            record["surface_type_counts"] = dict(surface_counts)
            record["curve_type_counts"] = dict(curve_counts)
            record["smallest_face_areas_m2_sample"] = sorted(area_sample)[:20]
        audit["bodies"].append(record)
    audit["classification"] = classify_audit(audit)
    return audit


def classify_audit(audit: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for body in audit.get("bodies", []):
        face_count = int(body.get("face_count") or 0)
        edge_count = int(body.get("edge_count") or 0)
        surface_counts = body.get("surface_type_counts") or {}
        curve_counts = body.get("curve_type_counts") or {}
        mesh = body.get("is_mesh_body")
        plane_faces = int(surface_counts.get("plane") or 0)
        line_edges = int(curve_counts.get("line") or 0)
        if mesh:
            label = "mesh_brep"
            reason = "The body is a SOLIDWORKS mesh BREP body."
        elif face_count > 1000 and plane_faces / max(face_count, 1) > 0.75 and line_edges / max(edge_count, 1) > 0.75:
            label = "standard_brep_with_faceted_topology"
            reason = "The body is standard BREP, but most faces are small planar faces and most edges are line curves."
        elif face_count > 1000:
            label = "standard_brep_with_many_patch_faces"
            reason = "The body is standard BREP with many real faces/edges; lines are topology, not only display style."
        else:
            label = "low_or_moderate_topology"
            reason = "The body has a modest face count."
        result.append({"body_index": body.get("index"), "classification": label, "reason": reason})
    return result


def save_model(doc: Any, stem: str) -> list[dict[str, Any]]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    for suffix in (".SLDPRT", ".STEP", ".x_t"):
        path = unique_path(OUTPUT_DIR / f"{stem}{suffix}")
        progress(f"saving {path.name}")
        try:
            ok = bool(doc.SaveAs(str(path)))
            outputs.append(
                {
                    "path": str(path),
                    "ok": ok,
                    "exists": path.exists(),
                    "size": path.stat().st_size if path.exists() else 0,
                }
            )
        except Exception as exc:
            outputs.append({"path": str(path), "ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return outputs


def route_baseline(sw: Any, ts: str) -> dict[str, Any]:
    route = "baseline"
    doc = import_source(sw, route)
    result: dict[str, Any] = {"route": route, "status": "started"}
    try:
        result["audit"] = audit_doc(doc, route, "baseline")
        result["outputs"] = save_model(doc, f"p12_baseline_{ts}")
        result["status"] = "success"
    finally:
        close_doc_if_title(sw, doc)
    return result


def route_import_diagnostics(sw: Any, ts: str) -> dict[str, Any]:
    route = "import_diagnostics"
    doc = import_source(sw, route)
    result: dict[str, Any] = {"route": route, "status": "started", "diagnosis_attempts": []}
    try:
        result["audit_before"] = audit_doc(doc, route, "before")
        variants = [
            {"close_all_gaps": True, "remove_faces": False, "fix_faces": True, "options": 0},
            {"close_all_gaps": True, "remove_faces": True, "fix_faces": True, "options": 0},
            {"close_all_gaps": False, "remove_faces": False, "fix_faces": True, "options": 0},
        ]
        for variant in variants:
            try:
                progress(f"{route}: ImportDiagnosis {variant}")
                value = doc.ImportDiagnosis(
                    bool(variant["close_all_gaps"]),
                    bool(variant["remove_faces"]),
                    bool(variant["fix_faces"]),
                    int(variant["options"]),
                )
                result["diagnosis_attempts"].append({"variant": variant, "return_value": int(value)})
            except Exception as exc:
                result["diagnosis_attempts"].append({"variant": variant, "error": f"{type(exc).__name__}: {exc}"})
        try:
            doc.ForceRebuild3(False)
        except Exception as exc:
            result["rebuild_error"] = f"{type(exc).__name__}: {exc}"
        result["audit_after"] = audit_doc(doc, route, "after")
        result["outputs"] = save_model(doc, f"p12_import_diagnostics_{ts}")
        result["status"] = "success"
    finally:
        close_doc_if_title(sw, doc)
    return result


def convert_first_body_to_mesh(doc: Any, route: str) -> dict[str, Any]:
    bodies = as_list(doc.GetBodies2(0, False))
    if not bodies:
        return {"success": False, "reason": "no solid bodies"}
    body = bodies[0]
    before = {"is_mesh_body": try_bool(body, "IsMeshBody"), "is_graphics_body": try_bool(body, "IsGraphicsBody")}
    attempts = []
    variants = [
        {
            "group_facets_into_faces": True,
            "keep_original_body": True,
            "hide_original_body": True,
            "mesh_refinement": 0.5,
            "advanced_mesh_refinement": True,
            "maximum_distance_m": 0.001,
            "maximum_angle_rad": 0.17453292519943295,
            "define_max_element_size": False,
            "element_size_m": 0.0,
        },
        {
            "group_facets_into_faces": True,
            "keep_original_body": True,
            "hide_original_body": True,
            "mesh_refinement": 1.0,
            "advanced_mesh_refinement": False,
            "maximum_distance_m": 0.0,
            "maximum_angle_rad": 0.0,
            "define_max_element_size": False,
            "element_size_m": 0.0,
        },
    ]
    for variant in variants:
        errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        try:
            progress(f"{route}: ConvertToMeshBody {variant}")
            value = body.ConvertToMeshBody(
                bool(variant["group_facets_into_faces"]),
                bool(variant["keep_original_body"]),
                bool(variant["hide_original_body"]),
                float(variant["mesh_refinement"]),
                bool(variant["advanced_mesh_refinement"]),
                float(variant["maximum_distance_m"]),
                float(variant["maximum_angle_rad"]),
                bool(variant["define_max_element_size"]),
                float(variant["element_size_m"]),
                errors,
            )
            attempts.append({"variant": variant, "return_value": str(value), "errors": int(errors.value)})
            if bool(value):
                return {"success": True, "before": before, "attempts": attempts}
        except Exception as exc:
            attempts.append({"variant": variant, "errors": int(errors.value), "error": f"{type(exc).__name__}: {exc}"})
    return {"success": False, "before": before, "attempts": attempts}


def route_mesh_tools(sw: Any, ts: str) -> dict[str, Any]:
    route = "mesh_tools"
    doc = import_source(sw, route)
    result: dict[str, Any] = {
        "route": route,
        "status": "started",
        "note": "The source body is expected to be standard BREP, so mesh-only tools may be inapplicable.",
    }
    try:
        result["audit_before"] = audit_doc(doc, route, "before")
        first_body = (result["audit_before"].get("bodies") or [{}])[0]
        result["mesh_applicability"] = {
            "is_mesh_body": first_body.get("is_mesh_body"),
            "is_graphics_body": first_body.get("is_graphics_body"),
            "convert_mesh_to_standard_applicable": bool(first_body.get("is_mesh_body")),
            "surface_from_mesh_directly_applicable": bool(first_body.get("is_mesh_body") or first_body.get("is_graphics_body")),
        }
        result["convert_to_mesh_body_probe"] = convert_first_body_to_mesh(doc, route)
        try:
            doc.ForceRebuild3(False)
        except Exception as exc:
            result["rebuild_error"] = f"{type(exc).__name__}: {exc}"
        result["audit_after_convert_to_mesh_probe"] = audit_doc(doc, route, "after_convert_to_mesh", classify_types=False)

        # SurfaceFromMesh exists on IMeshBody/IGraphicsBody. This is a feasibility probe only;
        # creating one surface from a whole complex part is not expected to produce a useful CFD cleanup.
        result["surface_from_mesh_attempts"] = []
        for body in as_list(doc.GetBodies2(0, False)):
            if not try_bool(body, "IsMeshBody"):
                continue
            try:
                mesh_body = body.GetMeshBody()
            except Exception as exc:
                result["surface_from_mesh_attempts"].append({"body": try_raw_call(body, "Name"), "error": f"GetMeshBody {type(exc).__name__}: {exc}"})
                continue
            for surface_type in (0, 1, 2, 3):
                errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                try:
                    progress(f"{route}: SurfaceFromMesh type={surface_type}")
                    feature = mesh_body.SurfaceFromMesh(int(surface_type), 0.001, 0.0, errors)
                    result["surface_from_mesh_attempts"].append(
                        {"surface_type": surface_type, "feature_created": bool(feature), "errors": int(errors.value)}
                    )
                    if feature:
                        break
                except Exception as exc:
                    result["surface_from_mesh_attempts"].append(
                        {"surface_type": surface_type, "errors": int(errors.value), "error": f"{type(exc).__name__}: {exc}"}
                    )
        result["audit_after_surface_probe"] = audit_doc(doc, route, "after_surface_probe", classify_types=False)
        result["outputs"] = save_model(doc, f"p12_mesh_tools_probe_{ts}")
        result["status"] = "success"
    finally:
        close_doc_if_title(sw, doc)
    return result


def write_reports(report: dict[str, Any], ts: str) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = unique_path(REPORT_DIR / f"p12_cleanup_trials_{ts}.json")
    md_path = unique_path(REPORT_DIR / f"p12_cleanup_trials_{ts}.md")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Phase12 Surface Cleanup Trials",
        "",
        f"- Timestamp: `{ts}`",
        f"- Input: `{INPUT_PATH}`",
        f"- Overall status: `{report.get('status')}`",
        "",
        "## Summary",
        "",
    ]
    for route in report.get("routes", []):
        lines.append(f"### {route.get('route')}")
        lines.append("")
        lines.append(f"- Status: `{route.get('status')}`")
        for key in ("audit", "audit_before", "audit_after", "audit_after_convert_to_mesh_probe", "audit_after_surface_probe"):
            audit = route.get(key)
            if not audit:
                continue
            lines.append(f"- {key} body counts: `{audit.get('body_counts')}`")
            for body in audit.get("bodies", []):
                lines.append(
                    f"- {key} body {body.get('index')}: faces `{body.get('face_count')}`, edges `{body.get('edge_count')}`, "
                    f"mesh `{body.get('is_mesh_body')}`, surface `{body.get('surface_type_counts')}`, curves `{body.get('curve_type_counts')}`"
                )
            for item in audit.get("classification", []):
                lines.append(f"- {key} classification body {item.get('body_index')}: `{item.get('classification')}`")
        if route.get("diagnosis_attempts"):
            lines.append(f"- ImportDiagnosis attempts: `{route.get('diagnosis_attempts')}`")
        if route.get("mesh_applicability"):
            lines.append(f"- Mesh applicability: `{route.get('mesh_applicability')}`")
        if route.get("convert_to_mesh_body_probe"):
            lines.append(f"- ConvertToMeshBody probe: `{route.get('convert_to_mesh_body_probe')}`")
        if route.get("surface_from_mesh_attempts"):
            lines.append(f"- SurfaceFromMesh attempts: `{route.get('surface_from_mesh_attempts')}`")
        if route.get("outputs"):
            lines.append("- Outputs:")
            for output in route.get("outputs", []):
                lines.append(f"  - `{output.get('path')}` size `{output.get('size')}` ok `{output.get('ok')}`")
        if route.get("error"):
            lines.append(f"- Error: `{route.get('error')}`")
        lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


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
        "routes": [],
        "sources": [
            "https://help.solidworks.com/2023/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.ipartdoc~importdiagnosis.html",
            "https://help.solidworks.com/2025/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IBody2~IsMeshBody.html",
            "https://help.solidworks.com/2025/english/SolidWorks/sldworks/t_convert_mesh_brep_standard_brep.htm",
            "https://help.solidworks.com/2025/english/solidworks/sldworks/t_surface_from_mesh.htm",
        ],
    }
    try:
        sw = connect_sw()
        for fn in (route_baseline, route_import_diagnostics, route_mesh_tools):
            try:
                report["routes"].append(fn(sw, ts))
            except Exception as exc:
                report["routes"].append(
                    {
                        "route": getattr(fn, "__name__", str(fn)),
                        "status": "failed",
                        "error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc(),
                    }
                )
                try:
                    sw = connect_sw()
                except Exception:
                    pass
        report["status"] = "success"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["traceback"] = traceback.format_exc()
    json_path, md_path = write_reports(report, ts)
    print(json.dumps({"status": report["status"], "json": str(json_path), "md": str(md_path)}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

