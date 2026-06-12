"""Controlled NXOpen journal for transforms, derived curves, revolve, sweep, and loft."""

from __future__ import print_function

import datetime
import io
import json
import math
import os
import re
import sys
import time
import traceback

import NXOpen
import NXOpen.Features
import NXOpen.GeometricUtilities
import NXOpen.UF


SCHEMA_VERSION = "fromcad2cfd_nx_job_v1"


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
    values = [str(item) for item in (args or []) if str(item) != "-args"]
    if not values:
        values = [str(item) for item in sys.argv[1:] if str(item) != "-args"]
    if not values:
        raise RuntimeError("Missing job JSON path. Use run_journal.exe create_transform_profile_pack_demo.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Transform Profile Pack Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "create_transform_profile_pack_demo"),
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
    for key, value in sorted((result.get("validation") or {}).items()):
        lines.append("- `%s`: `%s`" % (key, value))
    lines.extend(["", "## Operations", ""])
    operations = result.get("operations") or {}
    if operations:
        for key in sorted(operations):
            lines.append("- `%s`: `%s`" % (key, operations[key]))
    else:
        lines.append("- None")
    lines.extend(["", "## Errors", ""])
    errors = result.get("errors") or []
    if errors:
        for error in errors:
            lines.append("- %s" % error)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _write_reports(job, job_path, result, run_id):
    stem = _safe_name(job.get("model_name"), "nx_transform_profile_pack_demo")
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


def _set_angle_expression(work_part, expression, value):
    try:
        unit = work_part.UnitCollection.FindObject("Degrees")
        work_part.Expressions.EditWithUnits(expression, unit, str(float(value)))
        return
    except Exception:
        pass
    expression.RightHandSide = str(float(value))


def _do_update(session, mark_id, label):
    errors = session.UpdateManager.DoUpdate(mark_id)
    if errors not in (None, 0):
        raise RuntimeError("NX update failed after %s: %s" % (label, errors))


def _feature_body(feature, label):
    bodies = list(feature.GetBodies())
    if len(bodies) != 1:
        raise RuntimeError("%s expected one body; got %s." % (label, len(bodies)))
    return bodies[0]


def _create_block(session, work_part, name, origin, lengths):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, name)
    builder = work_part.Features.CreateBlockFeatureBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.SetOriginAndLengths(
            NXOpen.Point3d(float(origin[0]), float(origin[1]), float(origin[2])),
            str(float(lengths[0])),
            str(float(lengths[1])),
            str(float(lengths[2])),
        )
        feature = builder.CommitFeature()
    finally:
        builder.Destroy()
    _do_update(session, mark_id, name)
    session.DeleteUndoMark(mark_id, name)
    _set_name(feature, name)
    return feature, _feature_body(feature, name)


def _create_circle(work_part, center, radius, name):
    curve = work_part.Curves.CreateArc(
        NXOpen.Point3d(float(center[0]), float(center[1]), float(center[2])),
        NXOpen.Vector3d(1.0, 0.0, 0.0),
        NXOpen.Vector3d(0.0, 1.0, 0.0),
        float(radius),
        0.0,
        2.0 * math.pi,
    )
    _set_name(curve, name)
    return curve


def _create_line(work_part, start, end, name):
    line = work_part.Curves.CreateLine(
        NXOpen.Point3d(float(start[0]), float(start[1]), float(start[2])),
        NXOpen.Point3d(float(end[0]), float(end[1]), float(end[2])),
    )
    _set_name(line, name)
    return line


def _add_curve_to_section(work_part, section, curve, help_point):
    rule = work_part.ScRuleFactory.CreateRuleCurveDumb([curve])
    try:
        mode = NXOpen.Section.ModeCreate
    except Exception:
        mode = NXOpen.Section.Mode.Create
    section.AddToSection([rule], curve, NXOpen.NXObject.Null, NXOpen.NXObject.Null, help_point, mode)


def _rotate_copy(session, work_part, body, rotate_angle_deg):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD rotate copy")
    builder = work_part.BaseFeatures.CreateMoveObjectBuilder(NXOpen.Features.MoveObject.Null)
    try:
        builder.ObjectToMoveObject.Add(body)
        builder.MoveObjectResult = NXOpen.Features.MoveObjectBuilder.MoveObjectResultOptions.CopyOriginal
        builder.Associative = False
        builder.MoveParents = False
        builder.NumberOfCopies = 1
        motion = builder.TransformMotion
        motion.Option = NXOpen.GeometricUtilities.ModlMotion.Options.Angle
        axis = work_part.Axes.CreateAxis(
            NXOpen.Point3d(-60.0, 0.0, 0.0),
            NXOpen.Vector3d(0.0, 0.0, 1.0),
            NXOpen.SmartObject.UpdateOption.WithinModeling,
        )
        motion.AngularAxis = axis
        _set_angle_expression(work_part, motion.Angle, rotate_angle_deg)
        feature = builder.Commit()
        _do_update(session, mark_id, "rotate copy")
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD rotate copy")
    return str(type(feature))


def _create_datum_plane_from_point_direction(session, work_part, point, normal, name):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, name)
    point_obj = work_part.Points.CreatePoint(NXOpen.Point3d(float(point[0]), float(point[1]), float(point[2])))
    direction = work_part.Directions.CreateDirection(
        NXOpen.Point3d(float(point[0]), float(point[1]), float(point[2])),
        NXOpen.Vector3d(float(normal[0]), float(normal[1]), float(normal[2])),
        NXOpen.SmartObject.UpdateOption.WithinModeling,
    )
    builder = work_part.Features.CreateDatumPlaneBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.SetPointAndDirection(point_obj, direction)
        feature = builder.CommitFeature()
        _do_update(session, mark_id, name)
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, name)
    datum = list(feature.GetEntities())[0]
    _set_name(feature, name)
    return feature, datum


def _mirror_body(session, work_part, body):
    datum_feature, datum = _create_datum_plane_from_point_direction(
        session,
        work_part,
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        "fromcad2cfd_mirror_datum_plane",
    )
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD mirror body")
    builder = work_part.Features.CreateMirrorBodyBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.MirrorBodyList.Add(body)
        builder.Plane.SetValue(datum, NXOpen.View.Null, NXOpen.Point3d(0.0, 0.0, 0.0))
        feature = builder.CommitFeature()
        _do_update(session, mark_id, "mirror body")
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD mirror body")
    return {"datum_feature": str(type(datum_feature)), "mirror_feature": str(type(feature))}


def _top_face(body):
    uf_session = NXOpen.UF.UFSession.GetUFSession()
    rows = []
    for face in body.GetFaces():
        face_type, point, direction, box, radius, rad_data, norm_dir = uf_session.Modeling.AskFaceData(face.Tag)
        rows.append((point[2], face))
    if not rows:
        raise RuntimeError("Target body has no faces for projection.")
    rows.sort(key=lambda item: item[0], reverse=True)
    return rows[0][1]


def _project_curve(work_part, target_body):
    uf_session = NXOpen.UF.UFSession.GetUFSession()
    line = _create_line(work_part, (-10.0, -10.0, 35.0), (10.0, 10.0, 35.0), "fromcad2cfd_project_source_line")
    face = _top_face(target_body)
    data = NXOpen.UF.CurveProj_Struct()
    uf_session.Curve.InitProjCurvesData(data)
    data.ProjType = 3
    data.ProjVec = [0.0, 0.0, -1.0]
    data.Multiplicity = 1
    feature = uf_session.Curve.CreateProjCurves(1, [line.Tag], 1, [face.Tag], 0, data)
    return str(feature)


def _intersection_curve(session, work_part, target_body):
    _datum_feature, datum = _create_datum_plane_from_point_direction(
        session,
        work_part,
        (0.0, 0.0, 10.0),
        (0.0, 0.0, 1.0),
        "fromcad2cfd_intersection_datum_plane",
    )
    feature = NXOpen.UF.UFSession.GetUFSession().Curve.CreateIntObject(1, [target_body.Tag], 1, [datum.Tag])
    return str(feature)


def _revolve_profile(work_part, revolve_angle_deg):
    uf_session = NXOpen.UF.UFSession.GetUFSession()
    l1 = _create_line(work_part, (40.0, 0.0, 0.0), (40.0, 8.0, 0.0), "fromcad2cfd_revolve_line_1")
    l2 = _create_line(work_part, (40.0, 8.0, 0.0), (48.0, 8.0, 0.0), "fromcad2cfd_revolve_line_2")
    l3 = _create_line(work_part, (48.0, 8.0, 0.0), (48.0, 0.0, 0.0), "fromcad2cfd_revolve_line_3")
    l4 = _create_line(work_part, (48.0, 0.0, 0.0), (40.0, 0.0, 0.0), "fromcad2cfd_revolve_line_4")
    result = uf_session.Modl.CreateRevolution(
        [l1.Tag, l2.Tag, l3.Tag, l4.Tag],
        4,
        None,
        ["0.0", str(float(revolve_angle_deg))],
        ["0.0", "0.0"],
        [0.0, 0.0, 0.0],
        False,
        True,
        [35.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        NXOpen.UF.ModlFeatureSigns.NULLSIGN,
    )
    return str(result)


def _sweep_profile_along_path(work_part, sweep_height_mm):
    uf_session = NXOpen.UF.UFSession.GetUFSession()
    guide = _create_line(work_part, (70.0, 0.0, 0.0), (70.0, 0.0, float(sweep_height_mm)), "fromcad2cfd_sweep_guide")
    section = _create_circle(work_part, (70.0, 0.0, 0.0), 3.0, "fromcad2cfd_sweep_section")
    result = uf_session.Modl.CreateExtrusionPath(
        [section.Tag],
        1,
        [guide.Tag],
        1,
        None,
        ["0.0", "0.0"],
        [70.0, 0.0, 0.0],
        False,
        True,
        NXOpen.UF.ModlFeatureSigns.NULLSIGN,
    )
    return str(result)


def _loft_through_curves(session, work_part, loft_height_mm):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD through curves")
    c1 = _create_circle(work_part, (100.0, 0.0, 0.0), 4.0, "fromcad2cfd_loft_section_1")
    c2 = _create_circle(work_part, (100.0, 0.0, 0.5 * float(loft_height_mm)), 7.0, "fromcad2cfd_loft_section_2")
    c3 = _create_circle(work_part, (100.0, 0.0, float(loft_height_mm)), 5.0, "fromcad2cfd_loft_section_3")
    builder = work_part.Features.CreateThroughCurvesBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.BodyPreference = NXOpen.Features.ThroughCurvesBuilder.BodyPreferenceTypes.Sheet
        builder.PatchType = NXOpen.Features.ThroughCurvesBuilder.PatchTypes.Multiple
        builder.Construction = NXOpen.Features.ThroughCurvesBuilder.ConstructionMethod.Normal
        builder.PositionTolerance = 0.01
        builder.TangentTolerance = 0.5
        builder.CurvatureTolerance = 0.5
        for curve, help_point in [
            (c1, NXOpen.Point3d(104.0, 0.0, 0.0)),
            (c2, NXOpen.Point3d(107.0, 0.0, 0.5 * float(loft_height_mm))),
            (c3, NXOpen.Point3d(105.0, 0.0, float(loft_height_mm))),
        ]:
            section = work_part.Sections.CreateSection(0.01, 0.01, 0.5)
            section.SetAllowedEntityTypes(NXOpen.Section.AllowTypes.OnlyCurves)
            _add_curve_to_section(work_part, section, curve, help_point)
            builder.SectionsList.Append(section)
        feature = builder.CommitFeature()
        _do_update(session, mark_id, "through curves")
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD through curves")
    return str(type(feature))


def _work_bodies(work_part):
    try:
        return list(work_part.Bodies.ToArray())
    except Exception:
        pass
    try:
        return [body for body in work_part.Bodies]
    except Exception:
        return []


def _body_summary(work_part):
    rows = []
    for index, body in enumerate(_work_bodies(work_part), start=1):
        rows.append(
            {
                "index": index,
                "name": str(getattr(body, "Name", "")),
                "is_solid_body": bool(getattr(body, "IsSolidBody", False)),
                "is_sheet_body": bool(getattr(body, "IsSheetBody", False)),
                "face_count": len(list(body.GetFaces())),
                "edge_count": len(list(body.GetEdges())),
            }
        )
    return rows


def _save_part(work_part):
    work_part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)


def _require_nonempty_file(path, label):
    for _index in range(20):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        time.sleep(0.25)
    raise RuntimeError("%s output was missing or empty: %s" % (label, path))


def _export_parasolid(work_part, output_dir, model_stem, run_id):
    path = _unique_file(output_dir, model_stem, ".x_t", run_id)
    tags = [body.Tag for body in _work_bodies(work_part)]
    if not tags:
        raise RuntimeError("No bodies are available for Parasolid export.")
    NXOpen.UF.UFSession.GetUFSession().Ps.ExportData(tags, path)
    _require_nonempty_file(path, "Parasolid")
    return path


def _positive(parameters, name, default):
    value = float(parameters.get(name, default))
    if value <= 0.0:
        raise RuntimeError("%s must be positive." % name)
    return value


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "create_transform_profile_pack_demo":
        raise RuntimeError("Unsupported operation for create_transform_profile_pack_demo.py: %s" % job.get("operation"))
    parameters = job.get("parameters") or {}
    values = {
        "rotate_angle_deg": float(parameters.get("rotate_angle_deg", 45.0)),
        "sweep_height_mm": _positive(parameters, "sweep_height_mm", 25.0),
        "loft_height_mm": _positive(parameters, "loft_height_mm", 24.0),
        "revolve_angle_deg": _positive(parameters, "revolve_angle_deg", 360.0),
    }
    if values["rotate_angle_deg"] == 0.0:
        raise RuntimeError("rotate_angle_deg must be non-zero.")
    if values["revolve_angle_deg"] > 360.0:
        raise RuntimeError("revolve_angle_deg must not exceed 360.")
    return values


def _run_job(job, job_path, run_id):
    parameters = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)
    model_stem = _safe_name(job.get("model_name"), "nx_transform_profile_pack_demo")
    part_path = _unique_file(output_dir, model_stem, ".prt", run_id)

    session = NXOpen.Session.GetSession()
    work_part = _new_part(session, part_path)
    if work_part is None:
        raise RuntimeError("NX did not create a work part.")

    operations = {}
    _feature, rotate_body = _create_block(session, work_part, "fromcad2cfd_rotate_block", (-70.0, -5.0, -5.0), (10.0, 10.0, 10.0))
    operations["rotate_copy"] = _rotate_copy(session, work_part, rotate_body, parameters["rotate_angle_deg"])

    _feature, mirror_body = _create_block(session, work_part, "fromcad2cfd_mirror_block", (10.0, -5.0, -5.0), (10.0, 10.0, 10.0))
    operations["mirror_body"] = _mirror_body(session, work_part, mirror_body)

    _feature, curve_body = _create_block(session, work_part, "fromcad2cfd_curve_target_block", (-10.0, -10.0, 0.0), (20.0, 20.0, 20.0))
    operations["project_curve_to_face"] = _project_curve(work_part, curve_body)
    operations["intersection_curve_body_plane"] = _intersection_curve(session, work_part, curve_body)
    operations["revolve_profile"] = _revolve_profile(work_part, parameters["revolve_angle_deg"])
    operations["sweep_profile_along_path"] = _sweep_profile_along_path(work_part, parameters["sweep_height_mm"])
    operations["loft_through_curves"] = _loft_through_curves(session, work_part, parameters["loft_height_mm"])

    _save_part(work_part)
    parasolid = _export_parasolid(work_part, output_dir, model_stem, run_id)
    body_summary = _body_summary(work_part)
    solid_body_count = len([row for row in body_summary if row.get("is_solid_body")])
    sheet_body_count = len([row for row in body_summary if row.get("is_sheet_body")])
    validation = {
        "body_count": len(body_summary),
        "solid_body_count": solid_body_count,
        "sheet_body_count": sheet_body_count,
        "expected_min_solid_body_count": 7,
        "expected_sheet_body_count": 1,
        "operation_count": len(operations),
    }
    if len(operations) != 7 or solid_body_count < 7 or sheet_body_count != 1:
        raise RuntimeError("Transform/profile pack validation failed: %s" % validation)
    _save_part(work_part)

    return {
        "status": "success",
        "backend": "nx",
        "operation": "create_transform_profile_pack_demo",
        "message": "NX transform, derived-curve, revolve, sweep, and loft pack completed.",
        "outputs": {"part": part_path, "parasolid": parasolid},
        "operations": operations,
        "inspection": {"bodies": body_summary},
        "validation": validation,
        "parameters": parameters,
        "errors": [],
        "metadata": {"job_path": job_path, "run_id": run_id, "schema_version": job.get("schema_version")},
    }


def main(args=None):
    run_id = _timestamp()
    job_path = None
    job = {}
    try:
        job_path = _job_path_from_args(args)
        job = _read_json(job_path)
        result = _run_job(job, job_path, run_id)
        _write_reports(job, job_path, result, run_id)
        return result
    except Exception as exc:
        if job_path is None:
            job_path = os.getcwd()
        result = {
            "status": "failed",
            "backend": "nx",
            "operation": str(job.get("operation") or "create_transform_profile_pack_demo"),
            "message": "NX transform/profile pack journal failed.",
            "outputs": {},
            "operations": {},
            "inspection": {},
            "validation": {},
            "errors": [str(exc)],
            "metadata": {"job_path": job_path, "run_id": run_id, "traceback": traceback.format_exc()},
        }
        try:
            _write_reports(job, job_path, result, run_id)
        except Exception:
            pass
        raise


def Main(args):
    return main(args)


if __name__ == "__main__":
    main(sys.argv[1:])
