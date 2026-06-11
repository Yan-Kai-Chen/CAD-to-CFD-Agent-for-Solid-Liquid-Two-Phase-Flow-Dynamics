from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

from .documents import close_document, create_new_part, save_as
from .errors import SolidWorksOperationError
from .inspect_model import com_attr_or_call, document_inventory
from .rebuild import rebuild_document


SW_END_COND_BLIND = 0
SW_END_COND_THROUGH_ALL = 1
SW_END_COND_MID_PLANE = 6
SW_END_COND_THROUGH_ALL_BOTH = 9

SW_BODY_SOLID = 0

SW_BODY_OPERATION_INTERSECT = 15901
SW_BODY_OPERATION_CUT = 15902
SW_BODY_OPERATION_ADD = 15903

SW_CHAMFER_ANGLE_DISTANCE = 1
SW_CHAMFER_EQUAL_DISTANCE = 16
SW_CHAMFER_TANGENT_PROPAGATION = 4

SW_FILLET_PROPAGATE = 1
SW_FILLET_UNIFORM_RADIUS = 2
SW_FILLET_TYPE_SIMPLE = 0
SW_FILLET_OVERFLOW_DEFAULT = 0

SW_BODY_SHEET = 1

SW_THICKEN_SIDE_ONE = 0
SW_THICKEN_SIDE_TWO = 1
SW_THICKEN_BOTH = 2

SW_REVOLVE_TYPE_ONE_DIRECTION = 0
SW_REVOLVE_TYPE_ONE_DIRECTION_360 = 3
SW_REVOLVE_OPTIONS_NONE = 0

SW_REF_PLANE_DISTANCE = 8
SW_FM_SHELL = 8
SW_FM_THICKEN = 21


def _empty_callout() -> Any:
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)


def _empty_variant() -> Any:
    import pythoncom

    return pythoncom.Empty


def _nothing_variant() -> Any:
    import pythoncom

    return pythoncom.Nothing


def _dispatch_array(values: list[Any] | tuple[Any, ...]) -> Any:
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, list(values))


def _variant_array(values: list[Any] | tuple[Any, ...]) -> Any:
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, list(values))


def _to_meters(value: float, unit: str = "mm") -> float:
    unit = unit.lower()
    factors = {
        "m": 1.0,
        "mm": 0.001,
        "cm": 0.01,
        "inch": 0.0254,
        "in": 0.0254,
        "ft": 0.3048,
    }
    if unit not in factors:
        raise SolidWorksOperationError(f"Unsupported unit: {unit}")
    return float(value) * factors[unit]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    try:
        return list(value)
    except TypeError:
        return [value]


def _select_entity(entity: Any, *, append: bool, mark: int = 0) -> dict[str, Any]:
    attempts: list[str] = []
    for name, call in [
        ("SelectByMark", lambda: entity.SelectByMark(append, mark)),
        ("Select2", lambda: entity.Select2(append, mark)),
        ("Select", lambda: entity.Select(append, mark)),
        ("SelectAppendOnly", lambda: entity.Select(append)),
    ]:
        try:
            selected = bool(call())
            if selected:
                return {"success": True, "method": name, "mark": mark}
            attempts.append(f"{name} returned false")
        except Exception as exc:
            attempts.append(f"{name}: {type(exc).__name__}: {exc}")
    return {"success": False, "mark": mark, "attempts": attempts}


def _set_construction_geometry(segment: Any, value: bool = True) -> bool:
    for name, action in [
        ("ConstructionGeometry", lambda: setattr(segment, "ConstructionGeometry", bool(value))),
        ("IConstructionGeometry", lambda: setattr(segment, "IConstructionGeometry", bool(value))),
    ]:
        try:
            action()
            return True
        except Exception:
            continue
    return False


def select_reference_plane(doc: Any, plane: str = "Front") -> str:
    candidates = {
        "front": [
            "Front Plane",
            "\u524d\u89c6\u57fa\u51c6\u9762",
            "\u524d\u57fa\u51c6\u9762",
            "\u524d\u89c6",
        ],
        "top": [
            "Top Plane",
            "\u4e0a\u89c6\u57fa\u51c6\u9762",
            "\u4e0a\u57fa\u51c6\u9762",
            "\u4e0a\u89c6",
        ],
        "right": [
            "Right Plane",
            "\u53f3\u89c6\u57fa\u51c6\u9762",
            "\u53f3\u57fa\u51c6\u9762",
            "\u53f3\u89c6",
        ],
    }.get(plane.lower(), [plane])

    try:
        doc.ClearSelection2(True)
    except Exception:
        pass

    callout = _empty_callout()
    for candidate in candidates:
        try:
            ok = bool(doc.Extension.SelectByID2(candidate, "PLANE", 0, 0, 0, False, 0, callout, 0))
        except Exception:
            ok = False
        if ok:
            return candidate
    raise SolidWorksOperationError(f"Could not select reference plane. Tried: {candidates}")


def select_reference_plane_for_operation(doc: Any, plane: str = "Front", *, append: bool = False, mark: int = 0) -> str:
    candidates = {
        "front": ["Front Plane", "\u524d\u89c6\u57fa\u51c6\u9762", "\u524d\u57fa\u51c6\u9762", "\u524d\u89c6"],
        "top": ["Top Plane", "\u4e0a\u89c6\u57fa\u51c6\u9762", "\u4e0a\u57fa\u51c6\u9762", "\u4e0a\u89c6"],
        "right": ["Right Plane", "\u53f3\u89c6\u57fa\u51c6\u9762", "\u53f3\u57fa\u51c6\u9762", "\u53f3\u89c6"],
    }.get(plane.lower(), [plane])

    callout = _empty_callout()
    for candidate in candidates:
        try:
            selected = bool(doc.Extension.SelectByID2(candidate, "PLANE", 0, 0, 0, append, mark, callout, 0))
        except Exception:
            selected = False
        if selected:
            return candidate
    raise SolidWorksOperationError(f"Could not select reference plane for operation. Tried: {candidates}")


def select_named_plane(doc: Any, plane_name: str, *, append: bool = False, mark: int = 0) -> dict[str, Any]:
    callout = _empty_callout()
    attempts: list[str] = []
    for object_type in ("PLANE", "REFPLANE"):
        try:
            selected = bool(doc.Extension.SelectByID2(plane_name, object_type, 0, 0, 0, append, mark, callout, 0))
            if selected:
                return {"success": True, "method": "Extension.SelectByID2", "plane_name": plane_name, "type": object_type, "mark": mark}
            attempts.append(f"SelectByID2 {object_type} returned false")
        except Exception as exc:
            attempts.append(f"SelectByID2 {object_type}: {type(exc).__name__}: {exc}")
    return {"success": False, "plane_name": plane_name, "attempts": attempts, "mark": mark}


def select_sketch_by_name(doc: Any, sketch_name: str, *, append: bool = False, mark: int = 0) -> dict[str, Any]:
    callout = _empty_callout()
    attempts: list[str] = []
    try:
        selected = bool(doc.Extension.SelectByID2(sketch_name, "SKETCH", 0, 0, 0, append, mark, callout, 0))
        if selected:
            return {"success": True, "method": "Extension.SelectByID2", "sketch_name": sketch_name, "mark": mark}
        attempts.append("SelectByID2 SKETCH returned false")
    except Exception as exc:
        attempts.append(f"SelectByID2 SKETCH: {type(exc).__name__}: {exc}")
    return {"success": False, "sketch_name": sketch_name, "attempts": attempts, "mark": mark}


def close_and_select_last_sketch(doc: Any) -> str:
    try:
        active_sketch = doc.SketchManager.ActiveSketch
        if active_sketch is not None:
            doc.SketchManager.InsertSketch(True)
    except Exception:
        try:
            doc.InsertSketch2(True)
        except Exception:
            pass

    try:
        doc.ClearSelection2(True)
    except Exception:
        pass

    inventory = document_inventory(doc)
    sketches = [
        feature
        for feature in inventory.get("features", [])
        if str(feature.get("type")) == "ProfileFeature" and feature.get("name")
    ]
    if not sketches:
        raise SolidWorksOperationError(f"No sketch found after drawing. Features: {inventory.get('features')}")

    sketch_name = str(sketches[-1]["name"])
    callout = _empty_callout()
    selected = bool(doc.Extension.SelectByID2(sketch_name, "SKETCH", 0, 0, 0, False, 0, callout, 0))
    if not selected:
        import pythoncom

        selected = bool(doc.Extension.SelectByID2(sketch_name, "SKETCH", 0, 0, 0, False, 0, pythoncom.Nothing, 0))
    if not selected:
        raise SolidWorksOperationError(f"Could not select sketch: {sketch_name}")
    return sketch_name


def extrude_selected_sketch(
    doc: Any,
    height_m: float,
    *,
    merge_result: bool = True,
    draft_angle_deg: float = 0.0,
    both_directions: bool = False,
) -> tuple[Any, str]:
    attempts: list[str] = []
    end_cond = SW_END_COND_MID_PLANE if both_directions else SW_END_COND_BLIND
    draft_on = abs(float(draft_angle_deg)) > 1e-9
    draft_angle = math.radians(abs(float(draft_angle_deg)))

    try:
        feat = doc.FeatureManager.FeatureExtrusion2(
            True,
            False,
            False,
            end_cond,
            SW_END_COND_BLIND,
            height_m,
            height_m,
            draft_on,
            False,
            False,
            False,
            draft_angle,
            0.0,
            False,
            False,
            False,
            False,
            merge_result,
            True,
            True,
            0,
            0.0,
            False,
        )
        if feat:
            return feat, "FeatureExtrusion2"
        attempts.append("FeatureExtrusion2 returned None")
    except Exception as exc:
        attempts.append(f"FeatureExtrusion2: {type(exc).__name__}: {exc}")

    try:
        feat = doc.FeatureManager.FeatureExtrusion3(
            True,
            False,
            False,
            end_cond,
            SW_END_COND_BLIND,
            height_m,
            height_m,
            draft_on,
            False,
            False,
            False,
            draft_angle,
            0.0,
            False,
            False,
            False,
            False,
            merge_result,
            True,
            True,
            0,
            0.0,
            False,
        )
        if feat:
            return feat, "FeatureExtrusion3"
        attempts.append("FeatureExtrusion3 returned None")
    except Exception as exc:
        attempts.append(f"FeatureExtrusion3: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Extrusion failed. " + " | ".join(attempts))


def cut_selected_sketch(
    doc: Any,
    depth_m: float,
    *,
    through_all: bool = False,
    both_directions: bool = False,
) -> tuple[Any, str]:
    attempts: list[str] = []
    if through_all:
        end_cond = SW_END_COND_THROUGH_ALL_BOTH if both_directions else SW_END_COND_THROUGH_ALL
        cut_depth = 0.0
    else:
        end_cond = SW_END_COND_MID_PLANE if both_directions else SW_END_COND_BLIND
        cut_depth = depth_m

    for reverse_direction in (False, True):
        try:
            feat = doc.FeatureManager.FeatureCut4(
                True,
                False,
                reverse_direction,
                end_cond,
                SW_END_COND_BLIND,
                cut_depth,
                cut_depth,
                False,
                False,
                False,
                False,
                0.0,
                0.0,
                False,
                False,
                False,
                False,
                False,
                True,
                True,
                False,
                False,
                False,
                0,
                0.0,
                False,
                True,
            )
            if feat:
                return feat, f"FeatureCut4(reverse_direction={reverse_direction})"
            attempts.append(f"FeatureCut4 reverse_direction={reverse_direction} returned None")
        except Exception as exc:
            attempts.append(f"FeatureCut4 reverse_direction={reverse_direction}: {type(exc).__name__}: {exc}")

    for reverse_direction in (False, True):
        try:
            feat = doc.FeatureManager.FeatureCut3(
                True,
                False,
                reverse_direction,
                end_cond,
                SW_END_COND_BLIND,
                cut_depth,
                cut_depth,
                False,
                False,
                False,
                False,
                0.0,
                0.0,
                False,
                False,
                False,
                False,
                False,
                True,
                True,
                False,
                False,
                False,
                0,
                0.0,
                False,
            )
            if feat:
                return feat, f"FeatureCut3(reverse_direction={reverse_direction})"
            attempts.append(f"FeatureCut3 reverse_direction={reverse_direction} returned None")
        except Exception as exc:
            attempts.append(f"FeatureCut3 reverse_direction={reverse_direction}: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Cut extrude failed. " + " | ".join(attempts))


def start_sketch_on_plane(doc: Any, plane: str = "Front") -> str:
    selected_plane = select_reference_plane(doc, plane)
    doc.InsertSketch2(True)
    return selected_plane


def draw_center_rectangle(doc: Any, center_x_mm: float, center_y_mm: float, width_mm: float, height_mm: float) -> list[Any]:
    x1 = _to_meters(center_x_mm - width_mm / 2, "mm")
    y1 = _to_meters(center_y_mm - height_mm / 2, "mm")
    x2 = _to_meters(center_x_mm + width_mm / 2, "mm")
    y2 = _to_meters(center_y_mm + height_mm / 2, "mm")
    rect = doc.SketchManager.CreateCornerRectangle(x1, y1, 0.0, x2, y2, 0.0)
    segments = _as_list(rect)
    if not segments:
        raise SolidWorksOperationError("CreateCornerRectangle returned no sketch segments.")
    return segments


def draw_circle(doc: Any, center_x_mm: float, center_y_mm: float, radius_mm: float) -> Any:
    circle = doc.SketchManager.CreateCircleByRadius(
        _to_meters(center_x_mm, "mm"),
        _to_meters(center_y_mm, "mm"),
        0.0,
        _to_meters(radius_mm, "mm"),
    )
    if circle is None:
        raise SolidWorksOperationError("CreateCircleByRadius returned None.")
    return circle


def draw_line(
    doc: Any,
    start_x_mm: float,
    start_y_mm: float,
    end_x_mm: float,
    end_y_mm: float,
    *,
    construction: bool = False,
) -> Any:
    line = doc.SketchManager.CreateLine(
        _to_meters(start_x_mm, "mm"),
        _to_meters(start_y_mm, "mm"),
        0.0,
        _to_meters(end_x_mm, "mm"),
        _to_meters(end_y_mm, "mm"),
        0.0,
    )
    if line is None:
        raise SolidWorksOperationError("CreateLine returned None.")
    if construction:
        try:
            line.Select(False)
            doc.SketchManager.CreateConstructionGeometry()
        except Exception:
            _set_construction_geometry(line, True)
    return line


def select_sketch_segments(segments: Iterable[Any], *, mark: int = 0) -> dict[str, Any]:
    selected = 0
    attempts: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        result = _select_entity(segment, append=selected > 0, mark=mark)
        attempts.append({"index": index, **result})
        if result.get("success"):
            selected += 1
    return {"selected_count": selected, "attempts": attempts}


def offset_selected_sketch_entities(
    doc: Any,
    offset_mm: float,
    *,
    both_directions: bool = False,
    chain: bool = True,
    cap_ends: bool = False,
    make_construction: bool = False,
    add_dimensions: bool = True,
) -> dict[str, Any]:
    attempts: list[str] = []
    offset_m = _to_meters(offset_mm, "mm")
    try:
        value = doc.SketchManager.SketchOffset2(
            offset_m,
            bool(both_directions),
            bool(chain),
            bool(cap_ends),
            bool(make_construction),
            bool(add_dimensions),
        )
        if bool(value):
            return {"success": True, "method": "SketchOffset2", "offset_mm": offset_mm, "raw": str(value)}
        attempts.append(f"SketchOffset2 returned {value!r}")
    except Exception as exc:
        attempts.append(f"SketchOffset2: {type(exc).__name__}: {exc}")

    try:
        value = doc.SketchManager.SketchOffset(
            offset_m,
            bool(both_directions),
            bool(chain),
            bool(cap_ends),
            bool(make_construction),
            bool(add_dimensions),
        )
        if bool(value):
            return {"success": True, "method": "SketchOffset", "offset_mm": offset_mm, "raw": str(value)}
        attempts.append(f"SketchOffset returned {value!r}")
    except Exception as exc:
        attempts.append(f"SketchOffset: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Sketch offset failed. " + " | ".join(attempts))


def create_offset_rectangle_sketch(
    doc: Any,
    *,
    width_mm: float,
    height_mm: float,
    offset_mm: float,
    center_x_mm: float = 0.0,
    center_y_mm: float = 0.0,
    plane: str = "Front",
) -> dict[str, Any]:
    selected_plane = start_sketch_on_plane(doc, plane)
    segments = draw_center_rectangle(doc, center_x_mm, center_y_mm, width_mm, height_mm)
    selection = select_sketch_segments(segments)
    if selection["selected_count"] != len(segments):
        raise SolidWorksOperationError(f"Could not select all rectangle segments for offset: {selection}")
    offset = offset_selected_sketch_entities(doc, offset_mm)
    sketch_name = close_and_select_last_sketch(doc)
    return {
        "plane": selected_plane,
        "sketch_name": sketch_name,
        "width_mm": width_mm,
        "height_mm": height_mm,
        "offset_mm": offset_mm,
        "segment_count": len(segments),
        "selection": selection,
        "offset": offset,
    }


def create_rectangular_prism(
    doc: Any,
    *,
    width_mm: float,
    height_mm: float,
    depth_mm: float,
    center_x_mm: float = 0.0,
    center_y_mm: float = 0.0,
    plane: str = "Front",
    merge_result: bool = True,
    draft_angle_deg: float = 0.0,
) -> dict[str, Any]:
    selected_plane = start_sketch_on_plane(doc, plane)
    draw_center_rectangle(doc, center_x_mm, center_y_mm, width_mm, height_mm)
    sketch_name = close_and_select_last_sketch(doc)
    _, method = extrude_selected_sketch(
        doc,
        _to_meters(depth_mm, "mm"),
        merge_result=merge_result,
        draft_angle_deg=draft_angle_deg,
    )
    return {
        "plane": selected_plane,
        "sketch_name": sketch_name,
        "method": method,
        "width_mm": width_mm,
        "height_mm": height_mm,
        "depth_mm": depth_mm,
        "merge_result": merge_result,
        "draft_angle_deg": draft_angle_deg,
    }


def create_circular_boss(
    doc: Any,
    *,
    radius_mm: float,
    depth_mm: float,
    center_x_mm: float = 0.0,
    center_y_mm: float = 0.0,
    plane: str = "Front",
    merge_result: bool = True,
    draft_angle_deg: float = 0.0,
) -> dict[str, Any]:
    selected_plane = start_sketch_on_plane(doc, plane)
    draw_circle(doc, center_x_mm, center_y_mm, radius_mm)
    sketch_name = close_and_select_last_sketch(doc)
    _, method = extrude_selected_sketch(
        doc,
        _to_meters(depth_mm, "mm"),
        merge_result=merge_result,
        draft_angle_deg=draft_angle_deg,
    )
    return {
        "plane": selected_plane,
        "sketch_name": sketch_name,
        "method": method,
        "radius_mm": radius_mm,
        "depth_mm": depth_mm,
        "center_x_mm": center_x_mm,
        "center_y_mm": center_y_mm,
        "merge_result": merge_result,
        "draft_angle_deg": draft_angle_deg,
    }


def cut_circular_hole(
    doc: Any,
    *,
    radius_mm: float,
    center_x_mm: float = 0.0,
    center_y_mm: float = 0.0,
    depth_mm: float = 100.0,
    plane: str = "Front",
    through_all: bool = True,
) -> dict[str, Any]:
    selected_plane = start_sketch_on_plane(doc, plane)
    draw_circle(doc, center_x_mm, center_y_mm, radius_mm)
    sketch_name = close_and_select_last_sketch(doc)
    _, method = cut_selected_sketch(doc, _to_meters(depth_mm, "mm"), through_all=through_all)
    return {
        "plane": selected_plane,
        "sketch_name": sketch_name,
        "method": method,
        "radius_mm": radius_mm,
        "center_x_mm": center_x_mm,
        "center_y_mm": center_y_mm,
        "depth_mm": depth_mm,
        "through_all": through_all,
    }


def cut_hole_grid(
    doc: Any,
    *,
    radius_mm: float,
    centers_mm: list[tuple[float, float]],
    depth_mm: float = 100.0,
    plane: str = "Front",
    through_all: bool = True,
) -> dict[str, Any]:
    if not centers_mm:
        raise SolidWorksOperationError("Hole grid requires at least one center point.")
    holes = []
    for center_x_mm, center_y_mm in centers_mm:
        holes.append(
            cut_circular_hole(
                doc,
                radius_mm=radius_mm,
                center_x_mm=center_x_mm,
                center_y_mm=center_y_mm,
                depth_mm=depth_mm,
                plane=plane,
                through_all=through_all,
            )
        )
    return {
        "success": True,
        "method": "repeated_cut_circular_hole",
        "radius_mm": radius_mm,
        "hole_count": len(holes),
        "centers_mm": [list(center) for center in centers_mm],
        "holes": holes,
    }


def cut_counterbore_hole(
    doc: Any,
    *,
    pilot_radius_mm: float,
    counterbore_radius_mm: float,
    counterbore_depth_mm: float,
    center_x_mm: float = 0.0,
    center_y_mm: float = 0.0,
    plane: str = "Front",
) -> dict[str, Any]:
    if counterbore_radius_mm <= pilot_radius_mm:
        raise SolidWorksOperationError("Counterbore radius must be larger than pilot radius.")
    pilot = cut_circular_hole(
        doc,
        radius_mm=pilot_radius_mm,
        center_x_mm=center_x_mm,
        center_y_mm=center_y_mm,
        plane=plane,
        through_all=True,
    )
    counterbore = cut_circular_hole(
        doc,
        radius_mm=counterbore_radius_mm,
        center_x_mm=center_x_mm,
        center_y_mm=center_y_mm,
        depth_mm=counterbore_depth_mm,
        plane=plane,
        through_all=False,
    )
    return {
        "success": True,
        "method": "pilot_hole_plus_shallow_counterbore_cut",
        "pilot_radius_mm": pilot_radius_mm,
        "counterbore_radius_mm": counterbore_radius_mm,
        "counterbore_depth_mm": counterbore_depth_mm,
        "center_x_mm": center_x_mm,
        "center_y_mm": center_y_mm,
        "pilot": pilot,
        "counterbore": counterbore,
    }


def get_solid_bodies(doc: Any, *, visible_only: bool = False) -> list[Any]:
    try:
        return _as_list(doc.GetBodies2(SW_BODY_SOLID, bool(visible_only)))
    except Exception as exc:
        raise SolidWorksOperationError(f"Could not read solid bodies: {type(exc).__name__}: {exc}") from exc


def get_sheet_bodies(doc: Any, *, visible_only: bool = False) -> list[Any]:
    try:
        return _as_list(doc.GetBodies2(SW_BODY_SHEET, bool(visible_only)))
    except Exception as exc:
        raise SolidWorksOperationError(f"Could not read sheet bodies: {type(exc).__name__}: {exc}") from exc


def body_info(body: Any) -> dict[str, Any]:
    name: str | None
    try:
        name = str(com_attr_or_call(body, "Name"))
    except Exception:
        name = None
    try:
        box = [float(v) for v in _as_list(com_attr_or_call(body, "GetBodyBox"))]
    except Exception:
        box = []
    return {"name": name, "box_m": box}


def solid_body_inventory(doc: Any) -> dict[str, Any]:
    bodies = get_solid_bodies(doc)
    return {
        "solid_body_count": len(bodies),
        "bodies": [body_info(body) for body in bodies],
    }


def _box_volume(box: list[float]) -> float:
    if len(box) != 6:
        return 0.0
    return abs((box[3] - box[0]) * (box[4] - box[1]) * (box[5] - box[2]))


def solid_body_volume_indices(doc: Any) -> list[tuple[int, float, dict[str, Any]]]:
    records: list[tuple[int, float, dict[str, Any]]] = []
    for index, body in enumerate(get_solid_bodies(doc)):
        info = body_info(body)
        box = [float(v) for v in (info.get("box_m") or [])]
        records.append((index, _box_volume(box), info))
    return records


def _largest_body_index(doc: Any) -> int:
    records = solid_body_volume_indices(doc)
    if not records:
        raise SolidWorksOperationError("No solid bodies found.")
    return max(records, key=lambda item: item[1])[0]


def _smallest_body_index(doc: Any) -> int:
    records = solid_body_volume_indices(doc)
    if not records:
        raise SolidWorksOperationError("No solid bodies found.")
    return min(records, key=lambda item: item[1])[0]


def _feature_names(doc: Any) -> set[str]:
    return {
        str(item.get("name"))
        for item in document_inventory(doc).get("features", [])
        if item.get("name")
    }


def _new_feature_matching(doc: Any, before_names: set[str], tokens: tuple[str, ...]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for item in document_inventory(doc).get("features", []):
        name = str(item.get("name") or "")
        feature_type = str(item.get("type") or "")
        if name in before_names:
            continue
        haystack = f"{name} {feature_type}".lower()
        if any(token.lower() in haystack for token in tokens):
            matches.append(item)
    return matches


def sheet_body_inventory(doc: Any) -> dict[str, Any]:
    bodies = get_sheet_bodies(doc)
    return {
        "sheet_body_count": len(bodies),
        "bodies": [body_info(body) for body in bodies],
    }


def face_info(face: Any) -> dict[str, Any]:
    try:
        box = [float(v) for v in _as_list(com_attr_or_call(face, "GetBox"))]
    except Exception:
        box = []
    center = []
    if len(box) == 6:
        center = [(box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2]
    try:
        area = float(com_attr_or_call(face, "GetArea"))
    except Exception:
        area = None
    try:
        normal = [float(v) for v in _as_list(com_attr_or_call(face, "Normal"))]
    except Exception:
        normal = []
    return {"box_m": box, "center_m": center, "area_m2": area, "normal": normal}


def get_solid_body_faces(doc: Any, *, body_index: int = 0) -> list[Any]:
    bodies = get_solid_bodies(doc)
    if body_index < 0 or body_index >= len(bodies):
        raise SolidWorksOperationError(f"Body index {body_index} is out of range for {len(bodies)} solid bodies.")
    try:
        return _as_list(com_attr_or_call(bodies[body_index], "GetFaces"))
    except Exception as exc:
        raise SolidWorksOperationError(f"Could not read faces for body {body_index}: {type(exc).__name__}: {exc}") from exc


def _find_extreme_solid_face(doc: Any, *, axis: str = "z+", body_index: int = 0) -> tuple[int, Any, dict[str, Any], float]:
    axis = axis.lower()
    axis_index_map = {"x": 0, "y": 1, "z": 2}
    if len(axis) != 2 or axis[0] not in axis_index_map or axis[1] not in "+-":
        raise SolidWorksOperationError(f"Unsupported face axis selector: {axis}")

    faces = get_solid_body_faces(doc, body_index=body_index)
    face_records = []
    coord_index = axis_index_map[axis[0]]
    for index, face in enumerate(faces):
        info = face_info(face)
        center = info.get("center_m") or []
        if len(center) != 3:
            continue
        face_records.append((index, face, info, float(center[coord_index])))

    if not face_records:
        raise SolidWorksOperationError(f"No faces with bounding boxes found for body {body_index}.")
    return max(face_records, key=lambda item: item[3]) if axis[1] == "+" else min(face_records, key=lambda item: item[3])


def select_extreme_solid_face(
    doc: Any,
    *,
    axis: str = "z+",
    body_index: int = 0,
    append: bool = False,
    mark: int = 1,
) -> dict[str, Any]:
    try:
        doc.ClearSelection2(True)
    except Exception:
        pass

    index, face, info, coordinate = _find_extreme_solid_face(doc, axis=axis, body_index=body_index)
    center = info.get("center_m") or []
    selection: dict[str, Any] = {"success": False, "attempts": ["no center point available"]}
    if len(center) == 3:
        callout = _empty_callout()
        attempts: list[str] = []
        try:
            selected = bool(doc.Extension.SelectByID2("", "FACE", center[0], center[1], center[2], append, mark, callout, 0))
            if selected:
                selection = {
                    "success": True,
                    "method": "Extension.SelectByID2(FACE)",
                    "mark": mark,
                    "point_m": center,
                }
            else:
                attempts.append("SelectByID2 FACE returned false")
        except Exception as exc:
            attempts.append(f"SelectByID2 FACE: {type(exc).__name__}: {exc}")
        if not selection.get("success"):
            fallback = _select_entity(face, append=append, mark=mark)
            selection = {"success": bool(fallback.get("success")), "method": f"fallback:{fallback.get('method')}", "mark": mark, "point_m": center, "attempts": attempts, "fallback": fallback}
    else:
        selection = _select_entity(face, append=append, mark=mark)
    if not selection.get("success"):
        raise SolidWorksOperationError(f"Could not select {axis} face: {selection}")
    return {
        "success": True,
        "axis": axis,
        "body_index": body_index,
        "face_index": index,
        "coordinate_m": coordinate,
        "face": info,
        "selection": selection,
    }


def select_body(body: Any, *, append: bool = False, mark: int = 0) -> dict[str, Any]:
    attempts: list[str] = []
    for name, call in [
        ("Body.Select", lambda: body.Select(append, mark)),
        ("Body.Select2", lambda: body.Select2(append, _empty_variant())),
        ("Entity.Select2", lambda: body.Select2(append, mark)),
    ]:
        try:
            selected = bool(call())
            if selected:
                return {"success": True, "method": name, "mark": mark}
            attempts.append(f"{name} returned false")
        except Exception as exc:
            attempts.append(f"{name}: {type(exc).__name__}: {exc}")
    return {"success": False, "attempts": attempts, "mark": mark}


def select_body_by_id(doc: Any, body: Any, *, append: bool = False, mark: int = 1) -> dict[str, Any]:
    attempts: list[str] = []
    selection_ids: list[str] = []
    for attr_name in ("GetSelectionId", "Name"):
        try:
            value = com_attr_or_call(body, attr_name)
            if value:
                selection_ids.append(str(value))
        except Exception as exc:
            attempts.append(f"{attr_name}: {type(exc).__name__}: {exc}")

    callout = _empty_callout()
    for selection_id in selection_ids:
        try:
            selected = bool(doc.Extension.SelectByID2(selection_id, "SOLIDBODY", 0, 0, 0, append, mark, callout, 0))
            if selected:
                return {"success": True, "method": "Extension.SelectByID2", "selection_id": selection_id, "mark": mark}
            attempts.append(f"SelectByID2 SOLIDBODY {selection_id!r} returned false")
        except Exception as exc:
            attempts.append(f"SelectByID2 SOLIDBODY {selection_id!r}: {type(exc).__name__}: {exc}")

    fallback = select_body(body, append=append, mark=mark)
    if fallback.get("success"):
        return {"success": True, "method": f"fallback:{fallback.get('method')}", "mark": mark, "fallback": fallback}
    attempts.append(f"fallback body selection failed: {fallback}")
    return {"success": False, "attempts": attempts, "mark": mark}


def select_all_solid_body_edges(doc: Any, *, mark: int = 1, max_edges: int = 300) -> dict[str, Any]:
    try:
        doc.ClearSelection2(True)
    except Exception:
        pass

    selected = 0
    bodies = get_solid_bodies(doc)
    attempts: list[dict[str, Any]] = []
    for body_index, body in enumerate(bodies):
        edges = _as_list(com_attr_or_call(body, "GetEdges"))
        for edge_index, edge in enumerate(edges):
            if selected >= max_edges:
                return {
                    "selected_edge_count": selected,
                    "body_count": len(bodies),
                    "truncated": True,
                    "attempts": attempts,
                }
            result = _select_entity(edge, append=selected > 0, mark=mark)
            attempts.append({"body_index": body_index, "edge_index": edge_index, **result})
            if result.get("success"):
                selected += 1

    return {
        "selected_edge_count": selected,
        "body_count": len(bodies),
        "truncated": False,
        "attempts": attempts,
    }


def apply_all_edge_fillet(doc: Any, radius_mm: float) -> dict[str, Any]:
    selection = select_all_solid_body_edges(doc, mark=1)
    if selection["selected_edge_count"] <= 0:
        raise SolidWorksOperationError(f"No edges selected for fillet: {selection}")

    radius_m = _to_meters(radius_mm, "mm")
    options = SW_FILLET_PROPAGATE | SW_FILLET_UNIFORM_RADIUS
    attempts: list[str] = []
    try:
        feat = doc.FeatureManager.FeatureFillet3(
            options,
            radius_m,
            0.0,
            0.0,
            SW_FILLET_TYPE_SIMPLE,
            SW_FILLET_OVERFLOW_DEFAULT,
            0,
            _empty_variant(),
            _empty_variant(),
            _empty_variant(),
            _empty_variant(),
            _empty_variant(),
            _empty_variant(),
            _empty_variant(),
        )
        if feat:
            return {"success": True, "method": "FeatureFillet3", "radius_mm": radius_mm, "selection": selection}
        attempts.append("FeatureFillet3 returned None")
    except Exception as exc:
        attempts.append(f"FeatureFillet3: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("All-edge fillet failed. " + " | ".join(attempts))


def apply_all_edge_chamfer(doc: Any, distance_mm: float, angle_deg: float = 45.0) -> dict[str, Any]:
    selection = select_all_solid_body_edges(doc, mark=1)
    if selection["selected_edge_count"] <= 0:
        raise SolidWorksOperationError(f"No edges selected for chamfer: {selection}")

    attempts: list[str] = []
    try:
        feat = doc.FeatureManager.InsertFeatureChamfer(
            SW_CHAMFER_TANGENT_PROPAGATION,
            SW_CHAMFER_ANGLE_DISTANCE,
            _to_meters(distance_mm, "mm"),
            math.radians(angle_deg),
            0.0,
            0.0,
            0.0,
            0.0,
        )
        if feat:
            return {
                "success": True,
                "method": "InsertFeatureChamfer",
                "distance_mm": distance_mm,
                "angle_deg": angle_deg,
                "selection": selection,
            }
        attempts.append("InsertFeatureChamfer angle-distance returned None")
    except Exception as exc:
        attempts.append(f"InsertFeatureChamfer angle-distance: {type(exc).__name__}: {exc}")

    try:
        feat = doc.FeatureManager.InsertFeatureChamfer(
            SW_CHAMFER_TANGENT_PROPAGATION,
            SW_CHAMFER_EQUAL_DISTANCE,
            _to_meters(distance_mm, "mm"),
            math.radians(angle_deg),
            _to_meters(distance_mm, "mm"),
            0.0,
            0.0,
            0.0,
        )
        if feat:
            return {
                "success": True,
                "method": "InsertFeatureChamfer",
                "distance_mm": distance_mm,
                "angle_deg": angle_deg,
                "selection": selection,
                "fallback": "equal-distance",
            }
        attempts.append("InsertFeatureChamfer equal-distance returned None")
    except Exception as exc:
        attempts.append(f"InsertFeatureChamfer equal-distance: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("All-edge chamfer failed. " + " | ".join(attempts))


def move_copy_body(
    doc: Any,
    *,
    body_index: int = 0,
    translate_mm: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotate_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    copy: bool = False,
    number_of_copies: int = 1,
) -> dict[str, Any]:
    bodies = get_solid_bodies(doc)
    if body_index < 0 or body_index >= len(bodies):
        raise SolidWorksOperationError(f"Body index {body_index} is out of range for {len(bodies)} solid bodies.")

    try:
        doc.ClearSelection2(True)
    except Exception:
        pass

    selected = select_body_by_id(doc, bodies[body_index], append=False, mark=1)
    if not selected.get("success"):
        raise SolidWorksOperationError(f"Could not select body {body_index} for Move/Copy Body: {selected}")

    tx, ty, tz = (_to_meters(value, "mm") for value in translate_mm)
    rx, ry, rz = (math.radians(value) for value in rotate_deg)

    attempts: list[str] = []
    for method_name in ("InsertMoveCopyBody2", "InsertMoveCopyBody"):
        try:
            method = getattr(doc.FeatureManager, method_name)
            feat = method(
                tx,
                ty,
                tz,
                0.0,
                0.0,
                0.0,
                0.0,
                rx,
                ry,
                rz,
                bool(copy),
                int(number_of_copies),
            )
            if feat:
                return {
                    "success": True,
                    "method": method_name,
                    "selected_body": body_info(bodies[body_index]),
                    "selection": selected,
                    "translate_mm": list(translate_mm),
                    "rotate_deg": list(rotate_deg),
                    "copy": copy,
                    "number_of_copies": number_of_copies,
                }
            attempts.append(f"{method_name} returned None")
        except Exception as exc:
            attempts.append(f"{method_name}: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Move/Copy Body failed. " + " | ".join(attempts))


def apply_uniform_scale(
    doc: Any,
    *,
    scale_factor: float,
    scale_type: int = 0,
) -> dict[str, Any]:
    if scale_factor <= 0:
        raise SolidWorksOperationError("Scale factor must be positive.")
    before = _feature_names(doc)
    attempts: list[str] = []
    try:
        feat = doc.FeatureManager.InsertScale(int(scale_type), True, float(scale_factor), float(scale_factor), float(scale_factor))
        if feat:
            return {
                "success": True,
                "method": "FeatureManager.InsertScale",
                "scale_factor": scale_factor,
                "scale_type": scale_type,
            }
        detected = _new_feature_matching(doc, before, ("scale",))
        if detected:
            return {
                "success": True,
                "method": "FeatureManager.InsertScale(returned_none_feature_detected)",
                "scale_factor": scale_factor,
                "scale_type": scale_type,
                "detected_features": detected,
            }
        attempts.append("FeatureManager.InsertScale returned None")
    except Exception as exc:
        attempts.append(f"FeatureManager.InsertScale: {type(exc).__name__}: {exc}")

    try:
        feat = doc.InsertScale(float(scale_factor), float(scale_factor), float(scale_factor), True, int(scale_type))
        if feat:
            return {
                "success": True,
                "method": "ModelDoc2.InsertScale",
                "scale_factor": scale_factor,
                "scale_type": scale_type,
            }
        detected = _new_feature_matching(doc, before, ("scale",))
        if detected:
            return {
                "success": True,
                "method": "ModelDoc2.InsertScale(returned_none_feature_detected)",
                "scale_factor": scale_factor,
                "scale_type": scale_type,
                "detected_features": detected,
            }
        attempts.append("ModelDoc2.InsertScale returned None")
    except Exception as exc:
        attempts.append(f"ModelDoc2.InsertScale: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Uniform scale failed. " + " | ".join(attempts))


def delete_or_keep_body(
    doc: Any,
    *,
    body_index: int = 0,
    keep_selected: bool = False,
) -> dict[str, Any]:
    bodies = get_solid_bodies(doc)
    if body_index < 0 or body_index >= len(bodies):
        raise SolidWorksOperationError(f"Body index {body_index} is out of range for {len(bodies)} solid bodies.")

    body_count_before = len(bodies)
    try:
        doc.ClearSelection2(True)
    except Exception:
        pass
    selection = select_body_by_id(doc, bodies[body_index], append=False, mark=1)
    if not selection.get("success"):
        raise SolidWorksOperationError(f"Could not select body {body_index} for delete/keep: {selection}")

    before = _feature_names(doc)
    attempts: list[str] = []
    try:
        feat = doc.FeatureManager.InsertDeleteBody2(bool(keep_selected))
        if feat:
            return {
                "success": True,
                "method": "FeatureManager.InsertDeleteBody2",
                "body_index": body_index,
                "keep_selected": keep_selected,
                "body_count_before": body_count_before,
                "selection": selection,
                "selected_body": body_info(bodies[body_index]),
            }
        detected = _new_feature_matching(doc, before, ("delete", "body-delete", "body"))
        if detected:
            return {
                "success": True,
                "method": "FeatureManager.InsertDeleteBody2(returned_none_feature_detected)",
                "body_index": body_index,
                "keep_selected": keep_selected,
                "body_count_before": body_count_before,
                "selection": selection,
                "selected_body": body_info(bodies[body_index]),
                "detected_features": detected,
            }
        attempts.append("InsertDeleteBody2 returned None")
    except Exception as exc:
        attempts.append(f"InsertDeleteBody2: {type(exc).__name__}: {exc}")

    try:
        feat = doc.FeatureManager.InsertDeleteBody()
        if feat:
            return {
                "success": True,
                "method": "FeatureManager.InsertDeleteBody",
                "body_index": body_index,
                "keep_selected": False,
                "body_count_before": body_count_before,
                "selection": selection,
                "selected_body": body_info(bodies[body_index]),
            }
        attempts.append("InsertDeleteBody returned None")
    except Exception as exc:
        attempts.append(f"InsertDeleteBody: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Delete/Keep Body failed. " + " | ".join(attempts))


def offset_selected_face(
    doc: Any,
    *,
    axis: str = "z+",
    body_index: int = 0,
    distance_mm: float,
) -> dict[str, Any]:
    if abs(distance_mm) < 1e-9:
        raise SolidWorksOperationError("Face offset distance cannot be zero.")
    selection = select_extreme_solid_face(doc, axis=axis, body_index=body_index, mark=1)
    distance_m = _to_meters(abs(distance_mm), "mm")
    reverse = distance_mm < 0
    before = _feature_names(doc)
    attempts: list[str] = []
    try:
        feat = doc.FeatureManager.InsertMoveFace3(
            0,
            bool(reverse),
            0.0,
            distance_m,
            None,
            None,
            0,
            0.0,
        )
        if feat:
            return {
                "success": True,
                "method": "FeatureManager.InsertMoveFace3(offset)",
                "axis": axis,
                "body_index": body_index,
                "distance_mm": distance_mm,
                "selection": selection,
            }
        detected = _new_feature_matching(doc, before, ("moveface", "move face"))
        if detected:
            return {
                "success": True,
                "method": "FeatureManager.InsertMoveFace3(offset_returned_none_feature_detected)",
                "axis": axis,
                "body_index": body_index,
                "distance_mm": distance_mm,
                "selection": selection,
                "detected_features": detected,
            }
        attempts.append("InsertMoveFace3 returned None")
    except Exception as exc:
        attempts.append(f"InsertMoveFace3: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Move Face offset failed. " + " | ".join(attempts))


def create_web_rib(
    doc: Any,
    *,
    length_mm: float,
    height_mm: float,
    thickness_mm: float,
    base_top_y_mm: float,
    center_x_mm: float = 0.0,
    plane: str = "Front",
    merge_result: bool = True,
) -> dict[str, Any]:
    rib = create_rectangular_prism(
        doc,
        width_mm=length_mm,
        height_mm=height_mm,
        depth_mm=thickness_mm,
        center_x_mm=center_x_mm,
        center_y_mm=base_top_y_mm + height_mm / 2.0,
        plane=plane,
        merge_result=merge_result,
    )
    rib.update(
        {
            "success": True,
            "method": f"constructive_web_rib_via_{rib.get('method')}",
            "length_mm": length_mm,
            "height_mm": height_mm,
            "thickness_mm": thickness_mm,
            "base_top_y_mm": base_top_y_mm,
        }
    )
    return rib


def create_reference_axis_from_planes(
    doc: Any,
    *,
    plane_a: str = "Front",
    plane_b: str = "Right",
) -> dict[str, Any]:
    try:
        doc.ClearSelection2(True)
    except Exception:
        pass
    selected_a = select_reference_plane_for_operation(doc, plane_a, append=False, mark=0)
    selected_b = select_reference_plane_for_operation(doc, plane_b, append=True, mark=0)
    before = _feature_names(doc)
    attempts: list[str] = []
    for method_name, action in (
        ("ModelDoc2.InsertAxis2", lambda: doc.InsertAxis2(True)),
        ("ModelDoc2.InsertAxis", lambda: doc.InsertAxis()),
    ):
        try:
            feat = action()
            if feat:
                return {
                    "success": True,
                    "method": method_name,
                    "plane_a": selected_a,
                    "plane_b": selected_b,
                }
            detected = _new_feature_matching(doc, before, ("axis",))
            if detected:
                return {
                    "success": True,
                    "method": f"{method_name}(returned_none_or_bool_feature_detected)",
                    "plane_a": selected_a,
                    "plane_b": selected_b,
                    "detected_features": detected,
                }
            attempts.append(f"{method_name} returned {feat!r}")
        except Exception as exc:
            attempts.append(f"{method_name}: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Reference axis creation failed. " + " | ".join(attempts))


def create_coordinate_system(
    doc: Any,
    *,
    location_mm: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, Any]:
    lx, ly, lz = (_to_meters(value, "mm") for value in location_mm)
    rx, ry, rz = (math.radians(value) for value in rotation_deg)
    before = _feature_names(doc)
    attempts: list[str] = []
    try:
        feat = doc.FeatureManager.CreateCoordinateSystemUsingNumericalValues(
            True,
            lx,
            ly,
            lz,
            True,
            rx,
            ry,
            rz,
        )
        if feat:
            return {
                "success": True,
                "method": "FeatureManager.CreateCoordinateSystemUsingNumericalValues",
                "location_mm": list(location_mm),
                "rotation_deg": list(rotation_deg),
            }
        detected = _new_feature_matching(doc, before, ("coordinate", "coordsys"))
        if detected:
            return {
                "success": True,
                "method": "FeatureManager.CreateCoordinateSystemUsingNumericalValues(returned_none_feature_detected)",
                "location_mm": list(location_mm),
                "rotation_deg": list(rotation_deg),
                "detected_features": detected,
            }
        attempts.append("CreateCoordinateSystemUsingNumericalValues returned None")
    except Exception as exc:
        attempts.append(f"CreateCoordinateSystemUsingNumericalValues: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Coordinate system creation failed. " + " | ".join(attempts))


def combine_bodies(
    doc: Any,
    *,
    operation: str,
    main_body_index: int = 0,
    tool_body_indices: list[int] | None = None,
) -> dict[str, Any]:
    operation_map = {
        "add": SW_BODY_OPERATION_ADD,
        "subtract": SW_BODY_OPERATION_CUT,
        "common": SW_BODY_OPERATION_INTERSECT,
    }
    if operation not in operation_map:
        raise SolidWorksOperationError(f"Unsupported combine operation: {operation}")

    bodies = get_solid_bodies(doc)
    if len(bodies) < 2:
        raise SolidWorksOperationError(f"Combine requires at least 2 solid bodies; found {len(bodies)}.")
    if main_body_index < 0 or main_body_index >= len(bodies):
        raise SolidWorksOperationError(f"Main body index {main_body_index} is out of range for {len(bodies)} bodies.")

    tools = tool_body_indices or [idx for idx in range(len(bodies)) if idx != main_body_index]
    if not tools:
        raise SolidWorksOperationError("Combine requires at least one tool body.")
    for index in tools:
        if index < 0 or index >= len(bodies):
            raise SolidWorksOperationError(f"Tool body index {index} is out of range for {len(bodies)} bodies.")
        if index == main_body_index:
            raise SolidWorksOperationError("Tool body cannot be the same as the main body.")

    main_body = bodies[main_body_index]
    tool_bodies = [bodies[index] for index in tools]
    attempts: list[str] = []
    try:
        doc.ClearSelection2(True)
    except Exception:
        pass
    main_selection = select_body_by_id(doc, main_body, append=False, mark=1)
    tool_selections = [select_body_by_id(doc, body, append=True, mark=2) for body in tool_bodies]

    nothing = _nothing_variant()
    all_bodies = [main_body, *tool_bodies]
    combine_attempts = [
        ("main_tool_tuple", main_body, tuple(tool_bodies)),
        ("main_tool_list", main_body, list(tool_bodies)),
        ("main_tool_dispatch_array", main_body, _dispatch_array(tool_bodies)),
        ("main_tool_variant_array", main_body, _variant_array(tool_bodies)),
        ("nothing_all_tuple", nothing, tuple(all_bodies)),
        ("nothing_all_list", nothing, list(all_bodies)),
        ("nothing_all_dispatch_array", nothing, _dispatch_array(all_bodies)),
        ("nothing_all_variant_array", nothing, _variant_array(all_bodies)),
        ("selected_nothing", nothing, nothing),
        ("selected_none", None, None),
    ]
    for label, main_arg, tool_var in combine_attempts:
        try:
            feat = doc.FeatureManager.InsertCombineFeature(operation_map[operation], main_arg, tool_var)
            if feat:
                return {
                    "success": True,
                    "method": "InsertCombineFeature",
                    "operation": operation,
                    "main_body": body_info(main_body),
                    "tool_bodies": [body_info(body) for body in tool_bodies],
                    "main_selection": main_selection,
                    "tool_selections": tool_selections,
                    "body_count_before": len(bodies),
                    "argument_mode": label,
                }
            attempts.append(f"InsertCombineFeature returned None for {label}")
        except Exception as exc:
            attempts.append(f"InsertCombineFeature {label}: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Combine bodies failed. " + " | ".join(attempts))


def apply_shell(
    doc: Any,
    *,
    thickness_mm: float,
    outward: bool = False,
    open_face_axis: str = "z+",
    body_index: int = 0,
) -> dict[str, Any]:
    _, face, face_detail, _ = _find_extreme_solid_face(doc, axis=open_face_axis, body_index=body_index)
    face_selection = select_extreme_solid_face(doc, axis=open_face_axis, body_index=body_index, mark=1)
    attempts: list[str] = []
    before_native = _feature_names(doc)
    try:
        feat = doc.InsertFeatureShell(_to_meters(thickness_mm, "mm"), bool(outward))
        if feat:
            return {
                "success": True,
                "method": "ModelDoc2.InsertFeatureShell",
                "thickness_mm": thickness_mm,
                "outward": outward,
                "open_face_axis": open_face_axis,
                "face_selection": face_selection,
            }
        detected = _new_feature_matching(doc, before_native, ("shell",))
        if detected:
            return {
                "success": True,
                "method": "ModelDoc2.InsertFeatureShell(returned_none_feature_detected)",
                "thickness_mm": thickness_mm,
                "outward": outward,
                "open_face_axis": open_face_axis,
                "face_selection": face_selection,
                "detected_features": detected,
            }
        attempts.append("InsertFeatureShell returned None")
    except Exception as exc:
        attempts.append(f"InsertFeatureShell: {type(exc).__name__}: {exc}")

    try:
        data = doc.FeatureManager.CreateDefinition(SW_FM_SHELL)
        data.Thickness = _to_meters(thickness_mm, "mm")
        data.Direction = bool(outward)
        for label, face_array in [
            ("dispatch_array", _dispatch_array([face])),
            ("variant_array", _variant_array([face])),
            ("list", [face]),
            ("tuple", (face,)),
        ]:
            try:
                data.FacesRemoved = face_array
                feat = doc.FeatureManager.CreateFeature(data)
                if feat:
                    return {
                        "success": True,
                        "method": f"FeatureManager.CreateDefinition(swFmShell:{label})",
                        "thickness_mm": thickness_mm,
                        "outward": outward,
                        "open_face_axis": open_face_axis,
                        "face_selection": face_selection,
                        "face_detail": face_detail,
                    }
                attempts.append(f"CreateFeature shell {label} returned None")
            except Exception as exc:
                attempts.append(f"CreateFeature shell {label}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        attempts.append(f"CreateDefinition(swFmShell): {type(exc).__name__}: {exc}")

    if open_face_axis.lower() == "z+":
        try:
            fallback = construct_z_plus_open_shell_by_boolean(doc, thickness_mm=thickness_mm, body_index=body_index)
            fallback["native_attempts"] = attempts
            return fallback
        except Exception as exc:
            attempts.append(f"construct_z_plus_open_shell_by_boolean: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Shell failed. " + " | ".join(attempts))


def thicken_selected_face(
    doc: Any,
    *,
    thickness_mm: float,
    direction: int = SW_THICKEN_SIDE_ONE,
    face_axis: str = "z+",
    body_index: int = 0,
    merge_result: bool = True,
) -> dict[str, Any]:
    _, face, face_detail, _ = _find_extreme_solid_face(doc, axis=face_axis, body_index=body_index)
    face_selection = select_extreme_solid_face(doc, axis=face_axis, body_index=body_index, mark=1)
    thickness_m = _to_meters(thickness_mm, "mm")
    attempts: list[str] = []
    before_native = _feature_names(doc)

    try:
        feat = doc.FeatureManager.FeatureBossThicken(
            thickness_m,
            int(direction),
            0,
            False,
            bool(merge_result),
            True,
            True,
        )
        if feat:
            return {
                "success": True,
                "method": "FeatureManager.FeatureBossThicken",
                "thickness_mm": thickness_mm,
                "direction": direction,
                "face_axis": face_axis,
                "merge_result": merge_result,
                "face_selection": face_selection,
            }
        detected = _new_feature_matching(doc, before_native, ("thicken",))
        if detected:
            return {
                "success": True,
                "method": "FeatureManager.FeatureBossThicken(returned_none_feature_detected)",
                "thickness_mm": thickness_mm,
                "direction": direction,
                "face_axis": face_axis,
                "merge_result": merge_result,
                "face_selection": face_selection,
                "detected_features": detected,
            }
        attempts.append("FeatureManager.FeatureBossThicken returned None")
    except Exception as exc:
        attempts.append(f"FeatureManager.FeatureBossThicken: {type(exc).__name__}: {exc}")

    try:
        data = doc.FeatureManager.CreateDefinition(SW_FM_THICKEN)
        data.Surface = face
        data.Thickness = thickness_m
        data.ThicknessSide = int(direction)
        data.FillVolume = False
        data.Merge = bool(merge_result)
        data.FeatureScope = 0
        data.AutoSelect = True
        feat = doc.FeatureManager.CreateFeature(data)
        if feat:
            return {
                "success": True,
                "method": "FeatureManager.CreateDefinition(swFmThicken)",
                "thickness_mm": thickness_mm,
                "direction": direction,
                "face_axis": face_axis,
                "merge_result": merge_result,
                "face_selection": face_selection,
                "face_detail": face_detail,
            }
        attempts.append("CreateFeature thicken returned None")
    except Exception as exc:
        attempts.append(f"CreateDefinition(swFmThicken): {type(exc).__name__}: {exc}")

    for method_name, call in [
        ("ModelDoc2.FeatureBossThicken2", lambda: doc.FeatureBossThicken2(thickness_m, int(direction), 0, False)),
        ("ModelDoc2.FeatureBossThicken", lambda: doc.FeatureBossThicken(thickness_m, int(direction), 0)),
    ]:
        try:
            # Re-select because some failed feature calls clear or consume selection.
            face_selection = select_extreme_solid_face(doc, axis=face_axis, body_index=body_index, mark=1)
            feat = call()
            if feat:
                return {
                    "success": True,
                    "method": method_name,
                    "thickness_mm": thickness_mm,
                    "direction": direction,
                    "face_axis": face_axis,
                    "merge_result": merge_result,
                    "face_selection": face_selection,
                }
            attempts.append(f"{method_name} returned None")
        except Exception as exc:
            attempts.append(f"{method_name}: {type(exc).__name__}: {exc}")

    if face_axis.lower() == "z+":
        try:
            fallback = construct_z_plus_face_thicken_by_boolean(doc, thickness_mm=thickness_mm, body_index=body_index)
            fallback["native_attempts"] = attempts
            return fallback
        except Exception as exc:
            attempts.append(f"construct_z_plus_face_thicken_by_boolean: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Thicken selected face failed. " + " | ".join(attempts))


def construct_z_plus_open_shell_by_boolean(doc: Any, *, thickness_mm: float, body_index: int = 0) -> dict[str, Any]:
    bodies = get_solid_bodies(doc)
    if body_index < 0 or body_index >= len(bodies):
        raise SolidWorksOperationError(f"Body index {body_index} is out of range for {len(bodies)} solid bodies.")
    base_info = body_info(bodies[body_index])
    box = [float(v) for v in (base_info.get("box_m") or [])]
    if len(box) != 6:
        raise SolidWorksOperationError(f"Cannot construct shell because body box is unavailable: {base_info}")

    thickness_m = _to_meters(thickness_mm, "mm")
    width_m = box[3] - box[0]
    height_m = box[4] - box[1]
    depth_m = box[5] - box[2]
    if width_m <= 2 * thickness_m or height_m <= 2 * thickness_m or depth_m <= thickness_m:
        raise SolidWorksOperationError("Shell thickness is too large for the selected body box.")

    inner_width_mm = (width_m - 2 * thickness_m) * 1000.0
    inner_height_mm = (height_m - 2 * thickness_m) * 1000.0
    inner_depth_mm = (depth_m - thickness_m + thickness_m * 2) * 1000.0
    center_x_mm = ((box[0] + box[3]) / 2.0) * 1000.0
    center_y_mm = ((box[1] + box[4]) / 2.0) * 1000.0
    z_shift_mm = (box[2] + thickness_m) * 1000.0

    tool = create_rectangular_prism(
        doc,
        width_mm=inner_width_mm,
        height_mm=inner_height_mm,
        depth_mm=inner_depth_mm,
        center_x_mm=center_x_mm,
        center_y_mm=center_y_mm,
        merge_result=False,
    )
    rebuild_after_tool = rebuild_document(doc)
    tool_index = _smallest_body_index(doc)
    move = move_copy_body(doc, body_index=tool_index, translate_mm=(0.0, 0.0, z_shift_mm), copy=False)
    rebuild_after_move = rebuild_document(doc)
    main_index = _largest_body_index(doc)
    tool_indices = [index for index, _, _ in solid_body_volume_indices(doc) if index != main_index]
    combine = combine_bodies(doc, operation="subtract", main_body_index=main_index, tool_body_indices=tool_indices)
    return {
        "success": True,
        "method": "constructive_shell_boolean_subtract",
        "thickness_mm": thickness_mm,
        "open_face_axis": "z+",
        "base_body": base_info,
        "tool": tool,
        "rebuild_after_tool": rebuild_after_tool,
        "move_tool": move,
        "rebuild_after_move": rebuild_after_move,
        "combine": combine,
    }


def construct_z_plus_face_thicken_by_boolean(doc: Any, *, thickness_mm: float, body_index: int = 0) -> dict[str, Any]:
    bodies = get_solid_bodies(doc)
    if body_index < 0 or body_index >= len(bodies):
        raise SolidWorksOperationError(f"Body index {body_index} is out of range for {len(bodies)} solid bodies.")
    base_info = body_info(bodies[body_index])
    box = [float(v) for v in (base_info.get("box_m") or [])]
    if len(box) != 6:
        raise SolidWorksOperationError(f"Cannot construct thicken because body box is unavailable: {base_info}")

    width_mm = (box[3] - box[0]) * 1000.0
    height_mm = (box[4] - box[1]) * 1000.0
    center_x_mm = ((box[0] + box[3]) / 2.0) * 1000.0
    center_y_mm = ((box[1] + box[4]) / 2.0) * 1000.0
    z_shift_mm = box[5] * 1000.0

    cap = create_rectangular_prism(
        doc,
        width_mm=width_mm,
        height_mm=height_mm,
        depth_mm=thickness_mm,
        center_x_mm=center_x_mm,
        center_y_mm=center_y_mm,
        merge_result=False,
    )
    rebuild_after_cap = rebuild_document(doc)
    cap_index = _smallest_body_index(doc)
    move = move_copy_body(doc, body_index=cap_index, translate_mm=(0.0, 0.0, z_shift_mm), copy=False)
    rebuild_after_move = rebuild_document(doc)
    main_index = _largest_body_index(doc)
    tool_indices = [index for index, _, _ in solid_body_volume_indices(doc) if index != main_index]
    combine = combine_bodies(doc, operation="add", main_body_index=main_index, tool_body_indices=tool_indices)
    return {
        "success": True,
        "method": "constructive_thicken_boolean_add",
        "thickness_mm": thickness_mm,
        "face_axis": "z+",
        "base_body": base_info,
        "cap": cap,
        "rebuild_after_cap": rebuild_after_cap,
        "move_cap": move,
        "rebuild_after_move": rebuild_after_move,
        "combine": combine,
    }


def create_revolved_boss(
    doc: Any,
    *,
    inner_radius_mm: float,
    outer_radius_mm: float,
    height_mm: float,
    angle_deg: float = 360.0,
    plane: str = "Front",
    merge_result: bool = True,
) -> dict[str, Any]:
    selected_plane = start_sketch_on_plane(doc, plane)
    half_height = height_mm / 2.0
    axis = draw_line(doc, 0.0, -half_height * 1.4, 0.0, half_height * 1.4, construction=True)
    draw_center_rectangle(
        doc,
        (inner_radius_mm + outer_radius_mm) / 2.0,
        0.0,
        outer_radius_mm - inner_radius_mm,
        height_mm,
    )
    sketch_name = close_and_select_last_sketch(doc)
    attempts: list[str] = []
    angle_rad = math.radians(angle_deg)
    try:
        feat = doc.FeatureManager.FeatureRevolve2(
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
        )
        if feat:
            return {
                "success": True,
                "method": "FeatureManager.FeatureRevolve2",
                "plane": selected_plane,
                "sketch_name": sketch_name,
                "inner_radius_mm": inner_radius_mm,
                "outer_radius_mm": outer_radius_mm,
                "height_mm": height_mm,
                "angle_deg": angle_deg,
                "axis_construction_set": _set_construction_geometry(axis, True),
            }
        attempts.append("FeatureManager.FeatureRevolve2 returned None")
    except Exception as exc:
        attempts.append(f"FeatureManager.FeatureRevolve2: {type(exc).__name__}: {exc}")

    try:
        select_sketch_by_name(doc, sketch_name)
        feat = doc.FeatureRevolve2(angle_rad, False, 0.0, SW_REVOLVE_TYPE_ONE_DIRECTION, SW_REVOLVE_OPTIONS_NONE)
        if feat:
            return {
                "success": True,
                "method": "ModelDoc2.FeatureRevolve2",
                "plane": selected_plane,
                "sketch_name": sketch_name,
                "inner_radius_mm": inner_radius_mm,
                "outer_radius_mm": outer_radius_mm,
                "height_mm": height_mm,
                "angle_deg": angle_deg,
            }
        attempts.append("ModelDoc2.FeatureRevolve2 returned None")
    except Exception as exc:
        attempts.append(f"ModelDoc2.FeatureRevolve2: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Revolved boss failed. " + " | ".join(attempts))


def create_offset_reference_plane(
    doc: Any,
    *,
    base_plane: str = "Front",
    distance_mm: float,
    flip_direction: bool = False,
) -> dict[str, Any]:
    selected_plane = select_reference_plane(doc, base_plane)
    before = document_inventory(doc)
    before_names = {str(item.get("name")) for item in before.get("features", []) if item.get("name")}
    attempts: list[str] = []
    for method_name, call in [
        ("CreatePlaneAtOffset3", lambda: doc.CreatePlaneAtOffset3(_to_meters(distance_mm, "mm"), bool(flip_direction), True)),
        ("CreatePlaneAtOffset2", lambda: doc.CreatePlaneAtOffset2(_to_meters(distance_mm, "mm"), bool(flip_direction))),
        ("CreatePlaneAtOffset", lambda: doc.CreatePlaneAtOffset(_to_meters(distance_mm, "mm"), bool(flip_direction))),
    ]:
        try:
            feat = call()
            if feat:
                name = None
                try:
                    name = str(com_attr_or_call(feat, "Name"))
                except Exception:
                    pass
                if not name:
                    after = document_inventory(doc)
                    new_planes = [
                        str(item.get("name"))
                        for item in after.get("features", [])
                        if item.get("type") == "RefPlane" and str(item.get("name")) not in before_names
                    ]
                    name = new_planes[-1] if new_planes else None
                return {
                    "success": True,
                    "method": method_name,
                    "base_plane": selected_plane,
                    "distance_mm": distance_mm,
                    "flip_direction": flip_direction,
                    "plane_name": name,
                }
            attempts.append(f"{method_name} returned None")
        except Exception as exc:
            attempts.append(f"{method_name}: {type(exc).__name__}: {exc}")
    raise SolidWorksOperationError("Create offset reference plane failed. " + " | ".join(attempts))


def mirror_body_across_plane(
    doc: Any,
    *,
    body_index: int = 0,
    plane: str = "Right",
    merge_result: bool = False,
) -> dict[str, Any]:
    bodies = get_solid_bodies(doc)
    if body_index < 0 or body_index >= len(bodies):
        raise SolidWorksOperationError(f"Body index {body_index} is out of range for {len(bodies)} solid bodies.")
    try:
        doc.ClearSelection2(True)
    except Exception:
        pass
    body_selection = select_body_by_id(doc, bodies[body_index], append=False, mark=1)
    plane_selection = select_reference_plane_for_operation(doc, plane, append=True, mark=2)
    attempts: list[str] = []
    for method_name, call in [
        ("InsertMirrorFeature2", lambda: doc.FeatureManager.InsertMirrorFeature2(True, True, bool(merge_result), False, 0)),
        ("InsertMirrorFeature", lambda: doc.FeatureManager.InsertMirrorFeature(True, True, bool(merge_result), False)),
    ]:
        try:
            feat = call()
            if feat:
                return {
                    "success": True,
                    "method": method_name,
                    "body_index": body_index,
                    "body_selection": body_selection,
                    "plane": plane_selection,
                    "merge_result": merge_result,
                }
            attempts.append(f"{method_name} returned None")
        except Exception as exc:
            attempts.append(f"{method_name}: {type(exc).__name__}: {exc}")

    if plane.lower() == "right":
        try:
            info = body_info(bodies[body_index])
            box = [float(v) for v in (info.get("box_m") or [])]
            if len(box) != 6:
                raise SolidWorksOperationError(f"Body box unavailable for constructive mirror fallback: {info}")
            width_mm = (box[3] - box[0]) * 1000.0
            height_mm = (box[4] - box[1]) * 1000.0
            depth_mm = (box[5] - box[2]) * 1000.0
            mirrored_center_x_mm = -((box[0] + box[3]) / 2.0) * 1000.0
            center_y_mm = ((box[1] + box[4]) / 2.0) * 1000.0
            mirrored = create_rectangular_prism(
                doc,
                width_mm=width_mm,
                height_mm=height_mm,
                depth_mm=depth_mm,
                center_x_mm=mirrored_center_x_mm,
                center_y_mm=center_y_mm,
                merge_result=bool(merge_result),
            )
            return {
                "success": True,
                "method": "constructive_box_mirror_right_plane",
                "native_attempts": attempts,
                "source_body": info,
                "plane": plane,
                "mirrored_body": mirrored,
                "merge_result": merge_result,
            }
        except Exception as exc:
            attempts.append(f"constructive_box_mirror_right_plane: {type(exc).__name__}: {exc}")
    raise SolidWorksOperationError("Mirror body failed. " + " | ".join(attempts))


def create_circular_sweep(
    doc: Any,
    *,
    path_length_mm: float,
    diameter_mm: float,
    plane: str = "Front",
    merge_result: bool = True,
) -> dict[str, Any]:
    selected_plane = start_sketch_on_plane(doc, plane)
    draw_line(doc, 0.0, 0.0, path_length_mm, 0.0)
    sketch_name = close_and_select_last_sketch(doc)
    attempts: list[str] = []
    try:
        select_sketch_by_name(doc, sketch_name, append=False, mark=4)
        feat = doc.FeatureManager.InsertProtrusionSwept4(
            True,
            0,
            0,
            False,
            False,
            0,
            0,
            False,
            0.0,
            0.0,
            0,
            0,
            bool(merge_result),
            True,
            True,
            0.0,
            True,
            True,
            _to_meters(diameter_mm, "mm"),
            0,
        )
        if feat:
            return {
                "success": True,
                "method": "InsertProtrusionSwept4(circular_profile)",
                "plane": selected_plane,
                "path_sketch_name": sketch_name,
                "path_length_mm": path_length_mm,
                "diameter_mm": diameter_mm,
            }
        attempts.append("InsertProtrusionSwept4 returned None")
    except Exception as exc:
        attempts.append(f"InsertProtrusionSwept4: {type(exc).__name__}: {exc}")

    raise SolidWorksOperationError("Circular sweep failed. " + " | ".join(attempts))


def create_loft_between_circles(
    doc: Any,
    *,
    radius1_mm: float,
    radius2_mm: float,
    distance_mm: float,
    plane: str = "Front",
    merge_result: bool = True,
) -> dict[str, Any]:
    selected_plane = start_sketch_on_plane(doc, plane)
    draw_circle(doc, 0.0, 0.0, radius1_mm)
    sketch1 = close_and_select_last_sketch(doc)

    plane_result = create_offset_reference_plane(doc, base_plane=plane, distance_mm=distance_mm)
    plane_name = plane_result.get("plane_name")
    if not plane_name:
        raise SolidWorksOperationError(f"Could not resolve offset plane name for loft: {plane_result}")
    plane_selection = select_named_plane(doc, str(plane_name))
    if not plane_selection.get("success"):
        raise SolidWorksOperationError(f"Could not select offset plane for loft sketch: {plane_selection}")
    doc.InsertSketch2(True)
    draw_circle(doc, 0.0, 0.0, radius2_mm)
    sketch2 = close_and_select_last_sketch(doc)

    attempts: list[str] = []
    try:
        doc.ClearSelection2(True)
    except Exception:
        pass
    select1 = select_sketch_by_name(doc, sketch1, append=False, mark=1)
    select2 = select_sketch_by_name(doc, sketch2, append=True, mark=1)
    for method_name, call in [
        (
            "InsertProtrusionBlend2",
            lambda: doc.FeatureManager.InsertProtrusionBlend2(
                False,
                False,
                False,
                1.0,
                0,
                0,
                0.0,
                0.0,
                False,
                False,
                False,
                0.0,
                0.0,
                0,
                bool(merge_result),
                True,
                True,
                0,
            ),
        ),
        (
            "InsertProtrusionBlend",
            lambda: doc.FeatureManager.InsertProtrusionBlend(
                False,
                False,
                False,
                1.0,
                0,
                0,
                0.0,
                0.0,
                False,
                False,
                False,
                0.0,
                0.0,
                0,
                bool(merge_result),
                True,
                True,
            ),
        ),
    ]:
        try:
            feat = call()
            if feat:
                return {
                    "success": True,
                    "method": method_name,
                    "base_plane": selected_plane,
                    "offset_plane": plane_result,
                    "sketches": [sketch1, sketch2],
                    "selections": [select1, select2],
                    "radius1_mm": radius1_mm,
                    "radius2_mm": radius2_mm,
                    "distance_mm": distance_mm,
                }
            attempts.append(f"{method_name} returned None")
        except Exception as exc:
            attempts.append(f"{method_name}: {type(exc).__name__}: {exc}")
    raise SolidWorksOperationError("Loft between circles failed. " + " | ".join(attempts))


def create_cylinder(app: Any, radius_mm: float, height_mm: float, part_path: Path, step_path: Path) -> dict[str, Any]:
    doc = None
    steps: list[dict[str, Any]] = []
    try:
        doc = create_new_part(app)
        steps.append({"name": "create_new_part", "success": True, "details": document_inventory(doc)})

        selected_plane = select_reference_plane(doc, "Front")
        doc.InsertSketch2(True)
        steps.append({"name": "create_sketch", "success": True, "details": {"plane": selected_plane}})

        radius_m = _to_meters(radius_mm, "mm")
        circle = doc.SketchManager.CreateCircleByRadius(0.0, 0.0, 0.0, radius_m)
        if circle is None:
            raise SolidWorksOperationError("CreateCircleByRadius returned None.")
        steps.append({"name": "draw_circle", "success": True, "details": {"radius_mm": radius_mm}})

        selected_sketch = close_and_select_last_sketch(doc)
        height_m = _to_meters(height_mm, "mm")
        _, extrusion_method = extrude_selected_sketch(doc, height_m)
        steps.append(
            {
                "name": "extrude",
                "success": True,
                "details": {"height_mm": height_mm, "selected_sketch": selected_sketch, "method": extrusion_method},
            }
        )

        rebuild = rebuild_document(doc)
        steps.append({"name": "rebuild", "success": True, "details": rebuild})

        part_save = save_as(doc, part_path)
        steps.append({"name": "save_part", "success": True, "details": part_save})

        step_save = save_as(doc, step_path)
        steps.append({"name": "export_step", "success": True, "details": step_save})

        inventory = document_inventory(doc)
        body_inventory = solid_body_inventory(doc)
        close_info = close_document(app, doc, save=False)
        steps.append({"name": "close_document", "success": True, "details": close_info})
        doc = None

        return {
            "success": True,
            "radius_mm": radius_mm,
            "height_mm": height_mm,
            "part_path": str(part_path),
            "step_path": str(step_path),
            "part_exists": part_path.exists(),
            "part_size": part_path.stat().st_size if part_path.exists() else 0,
            "step_exists": step_path.exists(),
            "step_size": step_path.stat().st_size if step_path.exists() else 0,
            "inventory": inventory,
            "body_inventory": body_inventory,
            "steps": steps,
        }
    except Exception as exc:
        steps.append({"name": "error", "success": False, "message": f"{type(exc).__name__}: {exc}"})
        if doc is not None:
            try:
                close_document(app, doc, save=False)
            except Exception:
                pass
        raise SolidWorksOperationError(f"Create cylinder failed: {exc}") from exc

