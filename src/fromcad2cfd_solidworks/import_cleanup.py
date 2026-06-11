from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

from .connection import connect_solidworks
from .documents import close_document, create_new_part, save_as
from .errors import SolidWorksOperationError
from .geometry import (
    SW_REVOLVE_OPTIONS_NONE,
    SW_REVOLVE_TYPE_ONE_DIRECTION,
    body_info,
    close_and_select_last_sketch,
    draw_line,
    face_info,
    get_solid_bodies,
    select_sketch_by_name,
    solid_body_inventory,
    start_sketch_on_plane,
    _as_list,
    _set_construction_geometry,
    _to_meters,
)
from .inspect_model import com_attr_or_call, document_inventory
from .paths import project_output_dir, project_reports_dir, timestamp, unique_path
from .rebuild import rebuild_document
from .reports import write_json_report, write_markdown_report


PHASE9_SCHEMA_VERSION = "solidworks_import_cleanup_demo_v1"


def semicircle_polyline_points(radius_mm: float, segments: int) -> list[tuple[float, float]]:
    if radius_mm <= 0:
        raise SolidWorksOperationError("Sphere radius must be positive.")
    if segments < 4:
        raise SolidWorksOperationError("Faceted sphere requires at least 4 latitude segments.")
    points: list[tuple[float, float]] = []
    for index in range(segments + 1):
        angle = -math.pi / 2.0 + math.pi * index / segments
        x = radius_mm * math.cos(angle)
        y = radius_mm * math.sin(angle)
        if index in {0, segments}:
            x = 0.0
        points.append((x, y))
    return points


def infer_sphere_from_box(box_m: list[float]) -> dict[str, Any]:
    if len(box_m) != 6:
        raise SolidWorksOperationError(f"Cannot infer sphere from invalid body box: {box_m}")
    center_m = [
        (box_m[0] + box_m[3]) / 2.0,
        (box_m[1] + box_m[4]) / 2.0,
        (box_m[2] + box_m[5]) / 2.0,
    ]
    extents_m = [
        abs(box_m[3] - box_m[0]),
        abs(box_m[4] - box_m[1]),
        abs(box_m[5] - box_m[2]),
    ]
    radius_m = sum(extents_m) / 6.0
    max_extent = max(extents_m)
    min_extent = min(extents_m)
    roundness_error_pct = 0.0 if max_extent == 0 else (max_extent - min_extent) / max_extent * 100.0
    return {
        "center_m": center_m,
        "center_mm": [value * 1000.0 for value in center_m],
        "extents_m": extents_m,
        "extents_mm": [value * 1000.0 for value in extents_m],
        "radius_m": radius_m,
        "radius_mm": radius_m * 1000.0,
        "roundness_error_pct": roundness_error_pct,
    }


def _draw_semicircle_arc(doc: Any, radius_mm: float) -> dict[str, Any]:
    radius_m = _to_meters(radius_mm, "mm")
    attempts: list[str] = []
    try:
        arc = doc.SketchManager.Create3PointArc(
            0.0,
            -radius_m,
            0.0,
            0.0,
            radius_m,
            0.0,
            radius_m,
            0.0,
            0.0,
        )
        if arc is not None:
            return {"success": True, "method": "Create3PointArc", "radius_mm": radius_mm}
        attempts.append("Create3PointArc returned None")
    except Exception as exc:
        attempts.append(f"Create3PointArc: {type(exc).__name__}: {exc}")

    for direction in (True, False):
        try:
            arc = doc.SketchManager.CreateArc(
                0.0,
                0.0,
                0.0,
                0.0,
                -radius_m,
                0.0,
                0.0,
                radius_m,
                0.0,
                bool(direction),
            )
            if arc is not None:
                return {"success": True, "method": f"CreateArc(direction={direction})", "radius_mm": radius_mm}
            attempts.append(f"CreateArc direction={direction} returned None")
        except Exception as exc:
            attempts.append(f"CreateArc direction={direction}: {type(exc).__name__}: {exc}")
    raise SolidWorksOperationError("Could not draw semicircle arc. " + " | ".join(attempts))


def _revolve_selected_sketch(doc: Any, sketch_name: str, *, merge_result: bool = True, angle_deg: float = 360.0) -> dict[str, Any]:
    attempts: list[str] = []
    angle_rad = math.radians(angle_deg)
    for method_name, action in [
        (
            "FeatureManager.FeatureRevolve2",
            lambda: doc.FeatureManager.FeatureRevolve2(
                True,
                True,
                False,
                False,
                False,
                False,
                SW_REVOLVE_TYPE_ONE_DIRECTION,
                SW_REVOLVE_TYPE_ONE_DIRECTION,
                angle_rad,
                0.0,
                False,
                False,
                0.0,
                0.0,
                0,
                0.0,
                0.0,
                bool(merge_result),
                True,
                True,
            ),
        ),
        (
            "ModelDoc2.FeatureRevolve2",
            lambda: doc.FeatureRevolve2(angle_rad, False, 0.0, SW_REVOLVE_TYPE_ONE_DIRECTION, SW_REVOLVE_OPTIONS_NONE),
        ),
    ]:
        try:
            select_sketch_by_name(doc, sketch_name)
            feat = action()
            if feat:
                return {"success": True, "method": method_name, "sketch_name": sketch_name, "angle_deg": angle_deg}
            attempts.append(f"{method_name} returned None")
        except Exception as exc:
            attempts.append(f"{method_name}: {type(exc).__name__}: {exc}")
    raise SolidWorksOperationError("Revolve selected sphere profile failed. " + " | ".join(attempts))


def create_faceted_revolved_sphere(
    doc: Any,
    *,
    radius_mm: float,
    latitude_segments: int = 18,
    plane: str = "Front",
) -> dict[str, Any]:
    selected_plane = start_sketch_on_plane(doc, plane)
    axis = draw_line(doc, 0.0, -radius_mm * 1.2, 0.0, radius_mm * 1.2, construction=True)
    points = semicircle_polyline_points(radius_mm, latitude_segments)
    for start, end in zip(points, points[1:]):
        draw_line(doc, start[0], start[1], end[0], end[1])
    sketch_name = close_and_select_last_sketch(doc)
    revolve = _revolve_selected_sketch(doc, sketch_name)
    return {
        "success": True,
        "method": "faceted_polyline_revolve",
        "plane": selected_plane,
        "sketch_name": sketch_name,
        "radius_mm": radius_mm,
        "latitude_segments": latitude_segments,
        "profile_point_count": len(points),
        "axis_construction_set": _set_construction_geometry(axis, True),
        "revolve": revolve,
    }


def create_smooth_revolved_sphere(
    doc: Any,
    *,
    radius_mm: float,
    plane: str = "Front",
) -> dict[str, Any]:
    selected_plane = start_sketch_on_plane(doc, plane)
    axis = draw_line(doc, 0.0, -radius_mm * 1.2, 0.0, radius_mm * 1.2, construction=True)
    arc = _draw_semicircle_arc(doc, radius_mm)
    closure = draw_line(doc, 0.0, radius_mm, 0.0, -radius_mm)
    sketch_name = close_and_select_last_sketch(doc)
    revolve = _revolve_selected_sketch(doc, sketch_name)
    return {
        "success": True,
        "method": "smooth_semicircle_revolve",
        "plane": selected_plane,
        "sketch_name": sketch_name,
        "radius_mm": radius_mm,
        "axis_construction_set": _set_construction_geometry(axis, True),
        "arc": arc,
        "closure_line": {"success": closure is not None, "method": "CreateLine(diameter_closure)"},
        "revolve": revolve,
    }


def _edge_length(edge: Any) -> float | None:
    for attr_name in ("GetLength", "IGetLength"):
        try:
            return float(com_attr_or_call(edge, attr_name))
        except Exception:
            continue
    return None


def audit_part_geometry_for_cleanup(doc: Any, *, small_face_area_mm2: float = 1.0, short_edge_mm: float = 0.5) -> dict[str, Any]:
    bodies = get_solid_bodies(doc)
    body_records: list[dict[str, Any]] = []
    total_faces = 0
    total_edges = 0
    all_face_areas_m2: list[float] = []
    all_edge_lengths_m: list[float] = []
    small_face_area_m2 = small_face_area_mm2 * 1.0e-6
    short_edge_m = short_edge_mm * 0.001

    for body_index, body in enumerate(bodies):
        info = body_info(body)
        faces = _as_list(com_attr_or_call(body, "GetFaces"))
        edges = _as_list(com_attr_or_call(body, "GetEdges"))
        face_areas = []
        for face in faces:
            area = face_info(face).get("area_m2")
            if area is not None:
                face_areas.append(float(area))
                all_face_areas_m2.append(float(area))

        edge_lengths = []
        for edge in edges:
            length = _edge_length(edge)
            if length is not None:
                edge_lengths.append(length)
                all_edge_lengths_m.append(length)

        total_faces += len(faces)
        total_edges += len(edges)
        box = [float(value) for value in (info.get("box_m") or [])]
        sphere_fit = infer_sphere_from_box(box) if len(box) == 6 else None
        body_records.append(
            {
                "body_index": body_index,
                "body": info,
                "face_count": len(faces),
                "edge_count": len(edges),
                "min_face_area_mm2": min(face_areas) * 1.0e6 if face_areas else None,
                "median_face_area_mm2": median(face_areas) * 1.0e6 if face_areas else None,
                "small_face_count": sum(1 for area in face_areas if area < small_face_area_m2),
                "min_edge_length_mm": min(edge_lengths) * 1000.0 if edge_lengths else None,
                "median_edge_length_mm": median(edge_lengths) * 1000.0 if edge_lengths else None,
                "short_edge_count": sum(1 for length in edge_lengths if length < short_edge_m),
                "sphere_fit_from_box": sphere_fit,
            }
        )

    return {
        "solid_body_count": len(bodies),
        "total_face_count": total_faces,
        "total_edge_count": total_edges,
        "min_face_area_mm2": min(all_face_areas_m2) * 1.0e6 if all_face_areas_m2 else None,
        "median_face_area_mm2": median(all_face_areas_m2) * 1.0e6 if all_face_areas_m2 else None,
        "small_face_count": sum(1 for area in all_face_areas_m2 if area < small_face_area_m2),
        "min_edge_length_mm": min(all_edge_lengths_m) * 1000.0 if all_edge_lengths_m else None,
        "median_edge_length_mm": median(all_edge_lengths_m) * 1000.0 if all_edge_lengths_m else None,
        "short_edge_count": sum(1 for length in all_edge_lengths_m if length < short_edge_m),
        "thresholds": {
            "small_face_area_mm2": small_face_area_mm2,
            "short_edge_mm": short_edge_mm,
        },
        "bodies": body_records,
    }


def _safe_ratio(before: int | float | None, after: int | float | None) -> float | None:
    if before in {None, 0} or after is None:
        return None
    return float(after) / float(before)


def run_phase9_faceted_sphere_cleanup_demo(
    project: str = "phase9_import_cleanup_demo",
    *,
    radius_mm: float = 20.0,
    latitude_segments: int = 24,
    visible: bool = True,
) -> dict[str, Any]:
    stamp = timestamp()
    base = f"p9_sphere_{stamp}"
    output_dir = project_output_dir(project)
    reports_dir = project_reports_dir(project)
    md_path = unique_path(reports_dir / f"{base}.md")
    json_path = unique_path(reports_dir / f"{base}.json")
    source_part = unique_path(output_dir / f"{base}_src.SLDPRT")
    source_step = unique_path(output_dir / f"{base}_src.STEP")
    clean_part = unique_path(output_dir / f"{base}_clean.SLDPRT")
    clean_step = unique_path(output_dir / f"{base}_clean.STEP")

    data: dict[str, Any] = {
        "title": "SolidWorks Agent Phase9 Imported Geometry Cleanup Demo",
        "schema_version": PHASE9_SCHEMA_VERSION,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "summary": [],
        "steps": [],
        "outputs": {
            "source_part": str(source_part),
            "source_step": str(source_step),
            "rebuilt_part": str(clean_part),
            "rebuilt_step": str(clean_step),
            "markdown_report": str(md_path),
            "json_report": str(json_path),
            "project_output_dir": str(output_dir),
        },
        "request": {
            "project": project,
            "radius_mm": radius_mm,
            "latitude_segments": latitude_segments,
            "purpose": "Prototype faceted imported sphere audit and analytic sphere rebuild.",
        },
        "error": None,
    }

    connection = None
    source_doc = None
    clean_doc = None
    try:
        connection = connect_solidworks(visible=visible, allow_launch=True)
        data["steps"].append(
            {
                "name": "connect_solidworks",
                "success": True,
                "details": {
                    "launched_by_agent": connection.launched_by_agent,
                    "attached_to_running_process": connection.attached_to_running_process,
                },
            }
        )

        source_doc = create_new_part(connection.app)
        data["steps"].append({"name": "create_source_part", "success": True, "details": document_inventory(source_doc)})
        faceted = create_faceted_revolved_sphere(source_doc, radius_mm=radius_mm, latitude_segments=latitude_segments)
        data["steps"].append({"name": "create_faceted_sphere", "success": True, "details": faceted})
        data["steps"].append({"name": "rebuild_source_faceted", "success": True, "details": rebuild_document(source_doc)})
        source_audit = audit_part_geometry_for_cleanup(source_doc)
        data["steps"].append({"name": "audit_source_faceted", "success": True, "details": source_audit})
        data["steps"].append({"name": "source_body_inventory", "success": True, "details": solid_body_inventory(source_doc)})
        data["steps"].append({"name": "save_source_part", "success": True, "details": save_as(source_doc, source_part)})
        data["steps"].append({"name": "export_source_step", "success": True, "details": save_as(source_doc, source_step)})
        data["steps"].append({"name": "close_source_part", "success": True, "details": close_document(connection.app, source_doc, save=False)})
        source_doc = None

        body_fits = [
            body.get("sphere_fit_from_box")
            for body in source_audit.get("bodies", [])
            if body.get("sphere_fit_from_box")
        ]
        inferred_radius_mm = float(body_fits[0]["radius_mm"]) if body_fits else radius_mm

        clean_doc = create_new_part(connection.app)
        data["steps"].append({"name": "create_rebuilt_part", "success": True, "details": document_inventory(clean_doc)})
        rebuilt = create_smooth_revolved_sphere(clean_doc, radius_mm=inferred_radius_mm)
        data["steps"].append({"name": "rebuild_as_analytic_sphere", "success": True, "details": rebuilt})
        data["steps"].append({"name": "rebuild_clean_sphere", "success": True, "details": rebuild_document(clean_doc)})
        clean_audit = audit_part_geometry_for_cleanup(clean_doc)
        data["steps"].append({"name": "audit_rebuilt_smooth_sphere", "success": True, "details": clean_audit})
        data["steps"].append({"name": "rebuilt_body_inventory", "success": True, "details": solid_body_inventory(clean_doc)})
        data["steps"].append({"name": "save_rebuilt_part", "success": True, "details": save_as(clean_doc, clean_part)})
        data["steps"].append({"name": "export_rebuilt_step", "success": True, "details": save_as(clean_doc, clean_step)})
        data["steps"].append({"name": "close_rebuilt_part", "success": True, "details": close_document(connection.app, clean_doc, save=False)})
        clean_doc = None

        data["comparison"] = {
            "source_face_count": source_audit.get("total_face_count"),
            "rebuilt_face_count": clean_audit.get("total_face_count"),
            "face_count_ratio_rebuilt_over_source": _safe_ratio(source_audit.get("total_face_count"), clean_audit.get("total_face_count")),
            "source_edge_count": source_audit.get("total_edge_count"),
            "rebuilt_edge_count": clean_audit.get("total_edge_count"),
            "edge_count_ratio_rebuilt_over_source": _safe_ratio(source_audit.get("total_edge_count"), clean_audit.get("total_edge_count")),
            "source_min_face_area_mm2": source_audit.get("min_face_area_mm2"),
            "rebuilt_min_face_area_mm2": clean_audit.get("min_face_area_mm2"),
            "inferred_radius_mm": inferred_radius_mm,
            "strategy": "replace faceted sphere-like imported geometry with a new analytic revolved sphere from the inferred bounding box",
        }
        data["status"] = "success"
        data["summary"] = [
            "Created a controlled faceted sphere-like source model.",
            "Audited face and edge counts before cleanup.",
            "Rebuilt the source as a smooth analytic revolved sphere from inferred radius.",
            f"Source faces: {data['comparison']['source_face_count']}",
            f"Rebuilt faces: {data['comparison']['rebuilt_face_count']}",
            f"Source STEP: {source_step}",
            f"Rebuilt STEP: {clean_step}",
        ]
    except Exception as exc:
        data["status"] = "error"
        data["error"] = f"{type(exc).__name__}: {exc}"
        data["steps"].append({"name": "phase9_faceted_sphere_cleanup_demo", "success": False, "message": data["error"]})
    finally:
        for doc_name, doc in (("source", source_doc), ("rebuilt", clean_doc)):
            if doc is not None and connection is not None:
                try:
                    data["steps"].append(
                        {
                            "name": f"close_{doc_name}_part_after_error",
                            "success": True,
                            "details": close_document(connection.app, doc, save=False),
                        }
                    )
                except Exception as exc:
                    data["steps"].append({"name": f"close_{doc_name}_part_after_error", "success": False, "message": f"{type(exc).__name__}: {exc}"})
        if connection and connection.launched_by_agent:
            try:
                connection.app.ExitApp()
                data["steps"].append({"name": "exit_app_if_launched", "success": True})
            except Exception as exc:
                data["steps"].append({"name": "exit_app_if_launched", "success": False, "message": f"{type(exc).__name__}: {exc}"})

    json_written = write_json_report(Path(data["outputs"]["json_report"]), data)
    md_written = write_markdown_report(Path(data["outputs"]["markdown_report"]), data)
    data["outputs"]["json_report"] = str(json_written)
    data["outputs"]["markdown_report"] = str(md_written)
    json_written.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return data

