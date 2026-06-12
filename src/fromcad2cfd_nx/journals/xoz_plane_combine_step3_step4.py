"""Controlled NXOpen journal for reverse-modeling Step 3/4 XOY plane combine.

The filename keeps the older xoz token for compatibility with existing job
builders. The validated geometry is an XOY bounded-plane sheet moved +Z.
"""

from __future__ import print_function

import datetime
import io
import json
import os
import re
import shutil
import sys
import time
import traceback

import NXOpen
import NXOpen.Features
import NXOpen.GeometricUtilities
import NXOpen.UF


SCHEMA_VERSION = "fromcad2cfd_nx_job_v1"


def _debug(message):
    debug_path = os.environ.get("FROMCAD2CFD_NX_DEBUG_LOG")
    if not debug_path:
        return
    try:
        _ensure_dir(os.path.dirname(debug_path))
        with io.open(debug_path, "a", encoding="utf-8") as debug_handle:
            debug_handle.write("%s\n" % message)
    except Exception:
        pass


def _timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_name(value, fallback):
    text = str(value or fallback)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._")
    return text or fallback


def _ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def _unique_file(directory, stem, suffix, run_id):
    _ensure_dir(directory)
    candidate = os.path.join(directory, "%s_%s%s" % (stem, run_id, suffix))
    if not os.path.exists(candidate):
        return candidate
    index = 1
    while True:
        candidate = os.path.join(directory, "%s_%s_%02d%s" % (stem, run_id, index, suffix))
        if not os.path.exists(candidate):
            return candidate
        index += 1


def _read_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write_json(path, payload):
    with io.open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, indent=2))
        handle.write("\n")


def _write_text(path, text):
    with io.open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _job_path_from_args(args):
    raw_values = [str(item) for item in (args or [])]
    for index, value in enumerate(raw_values):
        if value == "-args" and index + 1 < len(raw_values):
            return os.path.abspath(raw_values[index + 1])
    values = [item for item in raw_values if item != "-args"]
    if not values:
        raw_values = [str(item) for item in sys.argv[1:]]
        for index, value in enumerate(raw_values):
            if value == "-args" and index + 1 < len(raw_values):
                return os.path.abspath(raw_values[index + 1])
        values = [item for item in raw_values if item != "-args"]
    if not values:
        raise RuntimeError("Missing job JSON path. Use run_journal.exe xoz_plane_combine_step3_step4.py -args <job.json>.")
    json_values = [value for value in values if value.lower().endswith(".json")]
    if json_values:
        return os.path.abspath(json_values[-1])
    return os.path.abspath(values[-1])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Reverse Modeling Step 3/4 XOY Plane Combine Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "reverse_step3_step4_xoz_plane_combine"),
        "Message: %s" % result.get("message", ""),
        "",
        "## Outputs",
        "",
    ]
    outputs = result.get("outputs") or {}
    if outputs:
        for key in sorted(outputs):
            lines.append("- `%s`: `%s`" % (key, outputs[key]))
    else:
        lines.append("- None")
    lines.extend(["", "## Validation", ""])
    validation = result.get("validation") or {}
    if validation:
        for key in sorted(validation):
            lines.append("- `%s`: `%s`" % (key, validation[key]))
    else:
        lines.append("- None")
    lines.extend(["", "## Combine Attempts", ""])
    attempts = ((result.get("metadata") or {}).get("combine_attempts") or [])
    if attempts:
        for attempt in attempts:
            lines.append("- `%s`: `%s`" % (attempt.get("name"), attempt.get("status")))
            if attempt.get("error"):
                lines.append("  - error: %s" % attempt.get("error"))
    else:
        lines.append("- None")
    lines.extend(["", "## Errors", ""])
    errors = result.get("errors") or []
    if errors:
        for error in errors:
            lines.append("- %s" % error)
    else:
        lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    warnings = ((result.get("metadata") or {}).get("warnings") or [])
    if warnings:
        for warning in warnings:
            lines.append("- %s" % warning)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _write_reports(job, job_path, result, run_id):
    stem = _safe_name(job.get("model_name"), "reverse_step3_step4_xoz_plane_combine")
    report_dir = _report_dir_for_job(job, job_path)
    json_path = _unique_file(report_dir, stem + "_journal_result", ".json", run_id)
    md_path = _unique_file(report_dir, stem + "_journal_result", ".md", run_id)
    result["reports"] = {"json": json_path, "markdown": md_path}
    _write_json(json_path, result)
    _write_text(md_path, _result_markdown(result))
    return result


def _new_part(session, part_path):
    file_new = session.Parts.FileNew()
    try:
        file_new.TemplateFileName = "model-plain-1-mm-template.prt"
        file_new.Units = NXOpen.Part.Units.Millimeters
        file_new.NewFileName = part_path
        file_new.MakeDisplayedPart = True
        file_new.ApplicationName = "ModelTemplate"
        file_new.MasterFileName = ""
        file_new.UseBlankTemplate = False
        file_new.Commit()
    finally:
        if hasattr(file_new, "Destroy"):
            try:
                file_new.Destroy()
            except Exception:
                pass
    return session.Parts.Work or session.Parts.Display


def _set_name(obj, name):
    try:
        obj.SetName(name)
        return
    except Exception:
        pass
    try:
        obj.Name = name
    except Exception:
        pass


def _set_length_expression(work_part, expression, value):
    try:
        unit = work_part.UnitCollection.FindObject("MilliMeter")
        work_part.Expressions.EditWithUnits(expression, unit, str(float(value)))
        return
    except Exception:
        pass
    expression.RightHandSide = str(float(value))


def _do_update(session, mark_id, label):
    errors = session.UpdateManager.DoUpdate(mark_id)
    if errors not in (None, 0):
        raise RuntimeError("NX update failed after %s: %s" % (label, errors))


def _work_bodies(work_part):
    try:
        return list(work_part.Bodies.ToArray())
    except Exception:
        pass
    try:
        return [body for body in work_part.Bodies]
    except Exception:
        return []


def _safe_bool(obj, attr):
    try:
        return bool(getattr(obj, attr))
    except Exception:
        return None


def _safe_count(label, func, warnings):
    try:
        return len(list(func()))
    except Exception as exc:
        warnings.append("%s failed: %s: %s" % (label, type(exc).__name__, exc))
        return None


def _bounding_box(body, warnings):
    try:
        box = NXOpen.UF.UFSession.GetUFSession().Sf.BodyAskBoundingBox(body.Tag)
        return [float(value) for value in list(box)]
    except Exception as exc:
        warnings.append("AskBoundingBox failed: %s: %s" % (type(exc).__name__, exc))
        return None


def _body_name(body):
    for attr in ("Name", "JournalIdentifier"):
        try:
            value = getattr(body, attr)
            if value:
                return str(value)
        except Exception:
            pass
    return ""


def _classify_body(is_solid, is_sheet, is_convergent, face_count):
    if is_solid:
        return "solid"
    if is_sheet:
        return "sheet"
    if is_convergent:
        return "convergent"
    if face_count in (None, 0):
        return "facet_or_unknown"
    return "b-rep"


def _body_summary(work_part):
    rows = []
    warnings = []
    for index, body in enumerate(_work_bodies(work_part), start=1):
        face_count = _safe_count("GetFaces", body.GetFaces, warnings)
        edge_count = _safe_count("GetEdges", body.GetEdges, warnings)
        is_solid = _safe_bool(body, "IsSolidBody")
        is_sheet = _safe_bool(body, "IsSheetBody")
        is_convergent = _safe_bool(body, "IsConvergentBody")
        rows.append(
            {
                "index": index,
                "name": _body_name(body),
                "tag": int(body.Tag),
                "classification": _classify_body(is_solid, is_sheet, is_convergent, face_count),
                "is_solid_body": is_solid,
                "is_sheet_body": is_sheet,
                "is_convergent_body": is_convergent,
                "face_count": face_count,
                "edge_count": edge_count,
                "bounding_box": _bounding_box(body, warnings),
            }
        )
    return rows, warnings


def _feature_rows(work_part):
    try:
        features = list(work_part.Features.ToArray())
    except Exception:
        try:
            features = [feature for feature in work_part.Features]
        except Exception:
            features = []
    rows = []
    for index, feature in enumerate(features, start=1):
        try:
            journal_identifier = str(feature.JournalIdentifier)
        except Exception:
            journal_identifier = ""
        rows.append({"index": index, "type": str(type(feature)), "journal_identifier": journal_identifier})
    return rows


def _add_curve_to_section(work_part, section, curve, help_point):
    rule = work_part.ScRuleFactory.CreateRuleCurveDumb([curve])
    try:
        mode = NXOpen.Section.ModeCreate
    except Exception:
        mode = NXOpen.Section.Mode.Create
    section.AddToSection([rule], curve, NXOpen.NXObject.Null, NXOpen.NXObject.Null, help_point, mode)


def _create_xoy_bounded_plane(session, work_part, square_size_mm):
    half = float(square_size_mm) / 2.0
    points = [
        NXOpen.Point3d(-half, -half, 0.0),
        NXOpen.Point3d(half, -half, 0.0),
        NXOpen.Point3d(half, half, 0.0),
        NXOpen.Point3d(-half, half, 0.0),
    ]
    boundary = []
    for index, pair in enumerate(((0, 1), (1, 2), (2, 3), (3, 0)), start=1):
        line = work_part.Curves.CreateLine(points[pair[0]], points[pair[1]])
        _set_name(line, "fromcad2cfd_step3_xoy_square_line_%d" % index)
        boundary.append(line)

    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD Step3 XOY bounded plane")
    builder = work_part.Features.CreateBoundedPlaneBuilder(NXOpen.Features.BoundedPlane.Null)
    try:
        section = builder.BoundingCurves
        section.SetAllowedEntityTypes(NXOpen.Section.AllowTypes.OnlyCurves)
        help_points = [
            NXOpen.Point3d(0.0, -half - 1.0, 0.0),
            NXOpen.Point3d(half + 1.0, 0.0, 0.0),
            NXOpen.Point3d(0.0, half + 1.0, 0.0),
            NXOpen.Point3d(-half - 1.0, 0.0, 0.0),
        ]
        for curve, help_point in zip(boundary, help_points):
            _add_curve_to_section(work_part, section, curve, help_point)
        feature = builder.CommitFeature()
        _do_update(session, mark_id, "Step3 bounded plane")
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD Step3 XOY bounded plane")
    _set_name(feature, "fromcad2cfd_step3_xoy_bounded_plane")
    bodies = list(feature.GetBodies())
    if len(bodies) != 1:
        raise RuntimeError("Step3 bounded plane expected one sheet body; got %s." % len(bodies))
    _set_name(bodies[0], "fromcad2cfd_step3_xoy_plane_sheet")
    return feature, bodies[0], boundary


def _move_body_z(session, work_part, body, offset_z_mm):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD Step3 move plane +Z")
    builder = work_part.BaseFeatures.CreateMoveObjectBuilder(NXOpen.Features.MoveObject.Null)
    try:
        builder.ObjectToMoveObject.Add(body)
        builder.MoveObjectResult = NXOpen.Features.MoveObjectBuilder.MoveObjectResultOptions.MoveOriginal
        builder.Associative = False
        builder.MoveParents = True
        builder.NumberOfCopies = 1
        motion = builder.TransformMotion
        motion.Option = NXOpen.GeometricUtilities.ModlMotion.Options.DeltaXyz
        motion.DeltaEnum = NXOpen.GeometricUtilities.ModlMotion.Delta.ReferenceWcsWorkPart
        _set_length_expression(work_part, motion.DeltaXc, 0.0)
        _set_length_expression(work_part, motion.DeltaYc, 0.0)
        _set_length_expression(work_part, motion.DeltaZc, float(offset_z_mm))
        feature = builder.Commit()
        _do_update(session, mark_id, "Step3 move plane +Z")
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD Step3 move plane +Z")
    return feature


def _select_imported_bodies(work_part, imported_tags, selector):
    bodies_by_tag = {}
    for body in _work_bodies(work_part):
        try:
            bodies_by_tag[int(body.Tag)] = body
        except Exception:
            pass
    imported = [bodies_by_tag[tag] for tag in imported_tags if tag in bodies_by_tag]
    if not imported:
        raise RuntimeError("No imported Parasolid bodies remained available for Step4 combine.")
    if selector == "all_imported_bodies":
        return imported
    sheets = [body for body in imported if bool(getattr(body, "IsSheetBody", False))]
    if sheets:
        return sheets
    return imported


def _set_region_methods(regions, config):
    select_method = config.get("select_method")
    if select_method == "not_set":
        regions.SelectMethod = NXOpen.GeometricUtilities.BooleanRegionSelect.SelectOption.NotSet
    elif select_method == "keep_or_remove":
        regions.SelectMethod = NXOpen.GeometricUtilities.BooleanRegionSelect.SelectOption.KeepOrRemove
    elif select_method == "keep_and_remove":
        regions.SelectMethod = NXOpen.GeometricUtilities.BooleanRegionSelect.SelectOption.KeepAndRemove
    keep_remove = config.get("keep_remove")
    if keep_remove == "keep":
        regions.KeepRemoveTargetMethod = NXOpen.GeometricUtilities.BooleanRegionSelect.KeepRemoveOption.Keep
        regions.KeepRemoveToolMethod = NXOpen.GeometricUtilities.BooleanRegionSelect.KeepRemoveOption.Keep


def _body_faces(body):
    try:
        return list(body.GetFaces())
    except Exception:
        return []


def _first_face(body):
    faces = _body_faces(body)
    if not faces:
        raise RuntimeError("Body has no selectable faces for Step4 region tracking: %s" % _body_name(body))
    return faces[0]


def _inside_xy(box, x_value, y_value):
    return box[0] <= x_value <= box[3] and box[1] <= y_value <= box[4]


def _outside_imported_xy(imported_boxes, x_value, y_value):
    margin = 5.0
    for box in imported_boxes:
        if box is None or len(box) < 6:
            continue
        if box[0] - margin <= x_value <= box[3] + margin and box[1] - margin <= y_value <= box[4] + margin:
            return False
    return True


def _target_region_point(plane_body, imported_bodies):
    warnings = []
    plane_box = _bounding_box(plane_body, warnings)
    imported_boxes = [_bounding_box(body, warnings) for body in imported_bodies]
    if not plane_box or len(plane_box) < 6:
        return NXOpen.Point3d(0.0, 0.0, 5.0)

    xmin, ymin, zmin, xmax, ymax, zmax = [float(value) for value in plane_box[:6]]
    xmid = (xmin + xmax) / 2.0
    ymid = (ymin + ymax) / 2.0
    zmid = (zmin + zmax) / 2.0
    width = xmax - xmin
    height = ymax - ymin
    candidates = [
        (xmid, ymax - 0.10 * height, zmid),
        (xmid, ymin + 0.10 * height, zmid),
        (xmax - 0.10 * width, ymid, zmid),
        (xmin + 0.10 * width, ymid, zmid),
        (xmin + 0.15 * width, ymax - 0.15 * height, zmid),
        (xmax - 0.15 * width, ymax - 0.15 * height, zmid),
        (xmin + 0.15 * width, ymin + 0.15 * height, zmid),
        (xmax - 0.15 * width, ymin + 0.15 * height, zmid),
        (xmid, ymid, zmid),
    ]
    for x_value, y_value, z_value in candidates:
        if _inside_xy(plane_box, x_value, y_value) and _outside_imported_xy(imported_boxes, x_value, y_value):
            return NXOpen.Point3d(x_value, y_value, z_value)
    return NXOpen.Point3d(xmid, ymid, zmid)


def _body_rule(work_part, bodies):
    options = None
    try:
        options = work_part.ScRuleFactory.CreateRuleOptions()
        options.SetSelectedFromInactive(False)
        return work_part.ScRuleFactory.CreateRuleBodyDumb(list(bodies), True, options)
    except Exception:
        return work_part.ScRuleFactory.CreateRuleBodyDumb(list(bodies))
    finally:
        if options is not None:
            try:
                options.Dispose()
            except Exception:
                pass


def _configure_recorded_keep_regions(builder, plane_body, imported_bodies):
    regions = builder.Regions
    regions.SelectMethod = NXOpen.GeometricUtilities.BooleanRegionSelect.SelectOption.KeepOrRemove
    regions.NotifyBodiesHaveChanged(builder.Bodies)
    regions.ClearAllRegionTrackers()
    regions.KeepRemoveTargetMethod = NXOpen.GeometricUtilities.BooleanRegionSelect.KeepRemoveOption.Keep
    regions.KeepRemoveToolMethod = NXOpen.GeometricUtilities.BooleanRegionSelect.KeepRemoveOption.Keep

    target_tracker = regions.AppendOneRegionTracker()
    target_tracker.OnTool = False
    target_tracker.SetOnePointSelector(_target_region_point(plane_body, imported_bodies))

    for body in imported_bodies:
        tool_tracker = regions.AppendOneRegionTracker()
        tool_tracker.OnTool = True
        tool_tracker.SetOneFaceSelector(_first_face(body))


def _combine_sheets(session, work_part, plane_body, imported_bodies):
    attempts = []
    configs = [
        {"name": "recorded_keep_or_remove_regions"},
    ]
    for config in configs:
        mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD Step4 combine sheets")
        builder = work_part.Features.TrimFeatureCollection.CreateCombineSheetsBuilder(NXOpen.Features.CombineSheets.Null)
        try:
            bodies_to_combine = [plane_body] + list(imported_bodies)
            rule = _body_rule(work_part, bodies_to_combine)
            builder.Bodies.ReplaceRules([rule], False)
            _configure_recorded_keep_regions(builder, plane_body, imported_bodies)
            feature = builder.Commit()
            _do_update(session, mark_id, "Step4 combine sheets")
            _set_name(feature, "fromcad2cfd_step4_combine_sheets")
            attempts.append({"name": config["name"], "status": "success"})
            return feature, attempts
        except Exception as exc:
            attempts.append({"name": config["name"], "status": "commit_failed", "error": "%s: %s" % (type(exc).__name__, exc)})
        finally:
            try:
                builder.Destroy()
            except Exception:
                pass
            session.DeleteUndoMark(mark_id, "FromCAD2CFD Step4 combine sheets")
    raise RuntimeError("Step4 CombineSheets failed for all region-selection modes: %s" % attempts)


def _save_part(work_part, part_path=None):
    save_status = None
    if part_path:
        try:
            save_status = work_part.SaveAs(part_path)
        except Exception as exc:
            _debug("basepart_saveas_failed=%s: %s" % (type(exc).__name__, exc))
            result = NXOpen.UF.UFSession.GetUFSession().Part.SaveAs(part_path)
            _debug("uf_part_saveas_result=%s" % result)
    else:
        save_status = work_part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)
    if save_status is not None and hasattr(save_status, "Dispose"):
        try:
            save_status.Dispose()
        except Exception:
            pass


def _require_nonempty_file(path, label):
    for _index in range(40):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        time.sleep(0.25)
    if not os.path.exists(path):
        raise RuntimeError("%s output was missing: %s" % (label, path))
    if os.path.getsize(path) <= 0:
        raise RuntimeError("%s output was empty: %s" % (label, path))


def _export_parasolid(work_part, output_dir, model_stem, run_id):
    path = _unique_file(output_dir, model_stem, ".x_t", run_id)
    tags = [body.Tag for body in _work_bodies(work_part)]
    if not tags:
        raise RuntimeError("No bodies are available for Parasolid export.")
    NXOpen.UF.UFSession.GetUFSession().Ps.ExportData(tags, path)
    _require_nonempty_file(path, "Parasolid")
    return path


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "reverse_step3_step4_xoz_plane_combine":
        raise RuntimeError("Unsupported operation for xoz_plane_combine_step3_step4.py: %s" % job.get("operation"))
    input_file = os.path.abspath(str(job.get("input_file") or ""))
    if not input_file or not os.path.exists(input_file):
        raise RuntimeError("Input Parasolid file does not exist: %s" % input_file)
    if os.path.splitext(input_file)[1].lower() not in (".x_t", ".x_b"):
        raise RuntimeError("Step3/4 expects copied Parasolid .x_t or .x_b input: %s" % input_file)
    parameters = job.get("parameters") or {}
    square_size_mm = float(parameters.get("square_size_mm", 1000.0))
    plane_offset_z_mm = float(parameters.get("plane_offset_z_mm", 5.0))
    body_selector = str(parameters.get("body_selector", "all_imported_sheet_bodies"))
    run_combine = bool(parameters.get("run_combine", True))
    export_parasolid = bool(parameters.get("export_parasolid", True))
    if square_size_mm <= 0.0:
        raise RuntimeError("square_size_mm must be positive.")
    if body_selector not in ("all_imported_sheet_bodies", "all_imported_bodies"):
        raise RuntimeError("Unsupported body_selector: %s" % body_selector)
    return input_file, square_size_mm, plane_offset_z_mm, body_selector, run_combine, export_parasolid


def _run_job(job, job_path, run_id):
    _debug("run_job_enter run_id=%s" % run_id)
    input_file, square_size_mm, plane_offset_z_mm, body_selector, run_combine, should_export_parasolid = _validate_job(job)
    _debug(
        "validated input_file=%s square=%s offset=%s selector=%s run_combine=%s"
        % (input_file, square_size_mm, plane_offset_z_mm, body_selector, run_combine)
    )
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)
    model_stem = _safe_name(job.get("model_name"), os.path.splitext(os.path.basename(input_file))[0] + "_step3_step4")
    copied_input = _unique_file(output_dir, model_stem + "_input_copy", os.path.splitext(input_file)[1], run_id)
    part_path = _unique_file(output_dir, model_stem, ".prt", run_id)
    shutil.copy2(input_file, copied_input)
    _debug("copied_input=%s part_path=%s" % (copied_input, part_path))

    session = NXOpen.Session.GetSession()
    _debug("session_obtained")
    work_part = _new_part(session, part_path)
    _debug("new_part_done work_part=%s" % work_part)
    if work_part is None:
        raise RuntimeError("NX did not create a Step3/4 work part.")

    importer = work_part.ImportManager.CreateParasolidImporter()
    try:
        importer.FileName = copied_input
        _debug("parasolid_import_begin")
        importer.Commit()
        _debug("parasolid_import_done")
    finally:
        try:
            importer.Destroy()
        except Exception:
            pass

    imported_bodies = _work_bodies(work_part)
    _debug("imported_body_count=%s" % len(imported_bodies))
    imported_tags = [int(body.Tag) for body in imported_bodies]
    if not imported_bodies:
        raise RuntimeError("Parasolid import did not create any bodies.")
    pre_summary, pre_warnings = _body_summary(work_part)
    _debug("pre_summary_done")
    pre_feature_rows = _feature_rows(work_part)

    plane_feature, plane_body, boundary_curves = _create_xoy_bounded_plane(session, work_part, square_size_mm)
    _debug("bounded_plane_done plane_tag=%s" % int(plane_body.Tag))
    move_feature = _move_body_z(session, work_part, plane_body, plane_offset_z_mm)
    _debug("move_done")
    after_plane_summary, plane_warnings = _body_summary(work_part)
    _debug("after_plane_summary_done")

    selected_imported = _select_imported_bodies(work_part, imported_tags, body_selector)
    combine_feature = None
    combine_attempts = []
    combine_error = None
    if run_combine:
        try:
            _debug("combine_begin selected_imported=%s total=%s" % (len(selected_imported), len(selected_imported) + 1))
            combine_feature, combine_attempts = _combine_sheets(session, work_part, plane_body, selected_imported)
            _debug("combine_done")
        except Exception as exc:
            combine_error = "%s: %s" % (type(exc).__name__, exc)
            _debug("combine_failed=%s" % combine_error)

    post_summary, post_warnings = _body_summary(work_part)
    _debug("post_summary_done")
    post_feature_rows = _feature_rows(work_part)
    _save_part(work_part)
    _debug("save_done")
    _require_nonempty_file(part_path, "NX PRT")

    parasolid = None
    export_error = None
    if should_export_parasolid:
        try:
            parasolid = _export_parasolid(work_part, output_dir, model_stem, run_id)
            _debug("export_parasolid_done=%s" % parasolid)
        except Exception as exc:
            export_error = "%s: %s" % (type(exc).__name__, exc)
            _debug("export_parasolid_failed=%s" % export_error)
        _save_part(work_part)

    warnings = pre_warnings + plane_warnings + post_warnings
    if export_error:
        warnings.append("Parasolid export failed: %s" % export_error)
    validation = {
        "source_parasolid_exists": os.path.exists(input_file),
        "copied_input_exists": os.path.exists(copied_input),
        "part_exists": os.path.exists(part_path),
        "imported_body_count": len(imported_bodies),
        "selected_imported_body_count": len(selected_imported),
        "body_count_after_plane": len(after_plane_summary),
        "body_count_after_combine": len(post_summary),
        "feature_count_before_step3": len(pre_feature_rows),
        "feature_count_after_step4": len(post_feature_rows),
        "step3_square_size_mm": square_size_mm,
        "step3_plane": "XOY",
        "step3_plane_center": [0.0, 0.0, 0.0],
        "step3_plane_offset_z_mm": plane_offset_z_mm,
        "step3_boundary_curve_count": len(boundary_curves),
        "step4_combine_requested": run_combine,
        "step4_combine_succeeded": combine_feature is not None,
        "parasolid_export_succeeded": parasolid is not None,
    }

    outputs = {
        "source_parasolid": input_file,
        "copied_input": copied_input,
        "part": part_path,
    }
    if parasolid:
        outputs["parasolid"] = parasolid

    status = "success" if (not run_combine or combine_feature is not None) else "partial"
    message = "Step3 XOY bounded plane was created, moved, and saved."
    if run_combine:
        message = "Step3 XOY bounded plane was created and Step4 Combine completed."
    errors = []
    if run_combine and combine_feature is None:
        message = "Step3 XOY bounded plane was created, but Step4 CombineSheets failed. The pre-combine part was saved for inspection."
        errors.append(combine_error or "Step4 CombineSheets failed.")

    return {
        "status": status,
        "backend": "nx",
        "operation": "reverse_step3_step4_xoz_plane_combine",
        "message": message,
        "outputs": outputs,
        "inspection": {
            "pre_bodies": pre_summary,
            "after_plane_bodies": after_plane_summary,
            "post_bodies": post_summary,
            "pre_features": pre_feature_rows,
            "post_features": post_feature_rows,
        },
        "validation": validation,
        "errors": errors,
        "metadata": {
            "job_path": job_path,
            "run_id": run_id,
            "schema_version": job.get("schema_version"),
            "plane_feature_type": str(type(plane_feature)),
            "move_feature_type": str(type(move_feature)),
            "combine_feature_type": str(type(combine_feature)) if combine_feature is not None else None,
            "combine_attempts": combine_attempts,
            "warnings": warnings,
        },
    }


def main(args=None):
    run_id = _timestamp()
    job_path = None
    job = {}
    _debug("main_enter args=%s run_id=%s" % (repr(args), run_id))
    try:
        job_path = _job_path_from_args(args)
        _debug("job_path=%s" % job_path)
        job = _read_json(job_path)
        _debug("job_read operation=%s" % job.get("operation"))
        result = _run_job(job, job_path, run_id)
        _debug("run_job_return status=%s" % result.get("status"))
        _write_reports(job, job_path, result, run_id)
        _debug("reports_written")
        return result
    except Exception as exc:
        _debug("main_exception=%s: %s" % (type(exc).__name__, exc))
        if job_path is None:
            job_path = os.getcwd()
        result = {
            "status": "failed",
            "backend": "nx",
            "operation": str(job.get("operation") or "reverse_step3_step4_xoz_plane_combine"),
            "message": "NX reverse-modeling Step3/4 journal failed.",
            "outputs": {},
            "inspection": {},
            "validation": {},
            "errors": ["%s: %s" % (type(exc).__name__, exc), traceback.format_exc()],
            "metadata": {"job_path": job_path, "run_id": run_id, "schema_version": job.get("schema_version")},
        }
        try:
            _write_reports(job, job_path, result, run_id)
        except Exception:
            pass
        return result


def Main(args):
    return main(args)


main(sys.argv[1:])
