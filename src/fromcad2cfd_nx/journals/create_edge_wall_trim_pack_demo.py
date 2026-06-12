"""Controlled NXOpen journal for edge, wall, trim, and import smoke coverage."""

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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe create_edge_wall_trim_pack_demo.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Edge Wall Trim Pack Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "create_edge_wall_trim_pack_demo"),
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
    stem = _safe_name(job.get("model_name"), "nx_edge_wall_trim_pack_demo")
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


def _set_expr(work_part, expression, value):
    text = str(float(value))
    try:
        unit = work_part.UnitCollection.FindObject("MilliMeter")
        work_part.Expressions.EditWithUnits(expression, unit, text)
        return
    except Exception:
        pass
    try:
        expression.RightHandSide = text
        return
    except Exception:
        pass
    raise RuntimeError("Unable to set expression to %s." % text)


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


def _do_update(session, mark_id, label):
    update_errors = session.UpdateManager.DoUpdate(mark_id)
    if update_errors not in (None, 0):
        raise RuntimeError("NX update failed after %s: %s" % (label, update_errors))


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


def _create_tapered_frustum(session, work_part, name, origin, base_diameter, top_diameter, height):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, name)
    builder = work_part.Features.CreateConeBuilder(NXOpen.Features.Cone.Null)
    try:
        builder.Type = NXOpen.Features.ConeBuilder.Types.DiametersAndHeight
        axis = work_part.Axes.CreateAxis(
            NXOpen.Point3d(float(origin[0]), float(origin[1]), float(origin[2])),
            NXOpen.Vector3d(0.0, 0.0, 1.0),
            NXOpen.SmartObject.UpdateOption.WithinModeling,
        )
        builder.Axis = axis
        _set_expr(work_part, builder.BaseDiameter, base_diameter)
        _set_expr(work_part, builder.TopDiameter, top_diameter)
        _set_expr(work_part, builder.Height, height)
        feature = builder.CommitFeature()
    finally:
        builder.Destroy()
    _do_update(session, mark_id, name)
    session.DeleteUndoMark(mark_id, name)
    _set_name(feature, name)
    return feature, _feature_body(feature, name)


def _collector_for_edge(work_part, edge):
    collector = work_part.ScCollectors.CreateCollector()
    collector.ReplaceRules([work_part.ScRuleFactory.CreateRuleEdgeDumb([edge])], False)
    return collector


def _collector_for_face(work_part, face):
    collector = work_part.ScCollectors.CreateCollector()
    collector.ReplaceRules([work_part.ScRuleFactory.CreateRuleFaceDumb([face])], False)
    return collector


def _first_edge(body):
    edges = list(body.GetEdges())
    if not edges:
        raise RuntimeError("Body has no edges.")
    return edges[0]


def _face_data(face):
    face_type, point, direction, box, radius, rad_data, norm_dir = NXOpen.UF.UFSession.GetUFSession().Modeling.AskFaceData(face.Tag)
    return {"face": face, "point": list(point), "direction": list(direction)}


def _top_face(body):
    rows = [_face_data(face) for face in body.GetFaces()]
    rows.sort(key=lambda row: row["point"][2], reverse=True)
    return rows[0]["face"]


def _edge_blend(session, work_part, body, radius):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD edge blend")
    builder = work_part.Features.CreateEdgeBlendBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.AddChainset(_collector_for_edge(work_part, _first_edge(body)), str(float(radius)))
        feature = builder.CommitFeature()
        _do_update(session, mark_id, "edge blend")
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD edge blend")
    return feature


def _chamfer(session, work_part, body, offset, angle_deg):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD chamfer")
    builder = work_part.Features.CreateChamferBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.Option = NXOpen.Features.ChamferBuilder.ChamferOption.OffsetAndAngle
        builder.Method = NXOpen.Features.ChamferBuilder.OffsetMethod.EdgesAlongFaces
        builder.FirstOffset = str(float(offset))
        builder.SecondOffset = str(float(offset))
        builder.Angle = str(float(angle_deg))
        builder.Tolerance = 0.01
        builder.SmartCollector = _collector_for_edge(work_part, _first_edge(body))
        feature = builder.CommitFeature()
        _do_update(session, mark_id, "chamfer")
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD chamfer")
    return feature


def _shell_remove_face(session, work_part, body, thickness):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD shell")
    builder = work_part.Features.CreateShellBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.Body = body
        builder.Tolerance = 0.01
        builder.SetDefaultThickness(str(float(thickness)))
        builder.RemovedFacesCollector = _collector_for_face(work_part, _top_face(body))
        feature = builder.CommitFeature()
        _do_update(session, mark_id, "shell")
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD shell")
    return feature


def _shell_face(session, work_part, body, thickness):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD shell face")
    builder = work_part.Features.CreateShellFaceBuilder(NXOpen.Features.ShellFace.Null)
    try:
        builder.FacesToShell.ReplaceRules([work_part.ScRuleFactory.CreateRuleFaceDumb([_top_face(body)])], False)
        _set_expr(work_part, builder.Thickness, thickness)
        feature = builder.CommitFeature()
        _do_update(session, mark_id, "shell face")
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD shell face")
    return feature


def _plane_cut_by_cutter(session, work_part, target_body, plane_x):
    _cutter_feature, cutter = _create_block(
        session,
        work_part,
        "fromcad2cfd_plane_cut_cutter",
        (float(plane_x), -50.0, -50.0),
        (100.0, 100.0, 100.0),
    )
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD plane cut")
    try:
        result = work_part.Features.CreateSubtractFeature(target_body, False, [cutter], False, True)
        _do_update(session, mark_id, "plane cut")
    finally:
        session.DeleteUndoMark(mark_id, "FromCAD2CFD plane cut")
    return result


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
    NXOpen.UF.UFSession.GetUFSession().Ps.ExportData(tags, path)
    _require_nonempty_file(path, "Parasolid")
    return path


def _import_parasolid(session, input_xt, output_dir, model_stem, run_id):
    import_part = _unique_file(output_dir, model_stem + "_import_check", ".prt", run_id)
    work_part = _new_part(session, import_part)
    importer = work_part.ImportManager.CreateParasolidImporter()
    try:
        importer.FileName = input_xt
        importer.Commit()
    finally:
        if hasattr(importer, "Destroy"):
            try:
                importer.Destroy()
            except Exception:
                pass
    _save_part(work_part)
    _require_nonempty_file(import_part, "Imported PRT")
    return import_part, _body_summary(work_part)


def _positive(parameters, name, default):
    value = float(parameters.get(name, default))
    if value <= 0.0:
        raise RuntimeError("%s must be positive." % name)
    return value


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "create_edge_wall_trim_pack_demo":
        raise RuntimeError("Unsupported operation for create_edge_wall_trim_pack_demo.py: %s" % job.get("operation"))
    parameters = job.get("parameters") or {}
    values = {
        "edge_radius_mm": _positive(parameters, "edge_radius_mm", 2.0),
        "chamfer_offset_mm": _positive(parameters, "chamfer_offset_mm", 2.0),
        "chamfer_angle_deg": _positive(parameters, "chamfer_angle_deg", 45.0),
        "shell_thickness_mm": _positive(parameters, "shell_thickness_mm", 0.5),
        "shell_face_thickness_mm": _positive(parameters, "shell_face_thickness_mm", 1.0),
        "taper_base_diameter_mm": _positive(parameters, "taper_base_diameter_mm", 18.0),
        "taper_top_diameter_mm": _positive(parameters, "taper_top_diameter_mm", 10.0),
        "taper_height_mm": _positive(parameters, "taper_height_mm", 24.0),
        "plane_cut_x_mm": float(parameters.get("plane_cut_x_mm", 110.0)),
    }
    if values["taper_top_diameter_mm"] >= values["taper_base_diameter_mm"]:
        raise RuntimeError("taper_top_diameter_mm must be smaller than taper_base_diameter_mm.")
    return values


def _run_job(job, job_path, run_id):
    parameters = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)
    model_stem = _safe_name(job.get("model_name"), "nx_edge_wall_trim_pack_demo")
    part_path = _unique_file(output_dir, model_stem, ".prt", run_id)

    session = NXOpen.Session.GetSession()
    work_part = _new_part(session, part_path)
    if work_part is None:
        raise RuntimeError("NX did not create a work part.")

    operations = {}
    _feature, fillet_body = _create_block(session, work_part, "fromcad2cfd_fillet_block", (-80.0, -10.0, -10.0), (20.0, 20.0, 20.0))
    _edge_blend(session, work_part, fillet_body, parameters["edge_radius_mm"])
    operations["fillet_edge_blend"] = "success"

    _feature, chamfer_body = _create_block(session, work_part, "fromcad2cfd_chamfer_block", (-40.0, -10.0, -10.0), (20.0, 20.0, 20.0))
    _chamfer(session, work_part, chamfer_body, parameters["chamfer_offset_mm"], parameters["chamfer_angle_deg"])
    operations["chamfer"] = "success"

    _feature, shell_body = _create_block(session, work_part, "fromcad2cfd_shell_block", (0.0, -10.0, -10.0), (20.0, 20.0, 20.0))
    _shell_remove_face(session, work_part, shell_body, parameters["shell_thickness_mm"])
    operations["shell_remove_face"] = "success"

    _feature, shell_face_body = _create_block(session, work_part, "fromcad2cfd_shell_face_block", (30.0, -10.0, -10.0), (20.0, 20.0, 20.0))
    _shell_face(session, work_part, shell_face_body, parameters["shell_face_thickness_mm"])
    operations["shell_face"] = "success"

    _create_tapered_frustum(
        session,
        work_part,
        "fromcad2cfd_tapered_frustum",
        (65.0, 0.0, -0.5 * parameters["taper_height_mm"]),
        parameters["taper_base_diameter_mm"],
        parameters["taper_top_diameter_mm"],
        parameters["taper_height_mm"],
    )
    operations["tapered_frustum"] = "success"

    _feature, trim_body = _create_block(session, work_part, "fromcad2cfd_plane_cut_block", (90.0, -10.0, -10.0), (40.0, 20.0, 20.0))
    _plane_cut_by_cutter(session, work_part, trim_body, parameters["plane_cut_x_mm"])
    operations["plane_cut_by_cutter"] = "success"

    _save_part(work_part)
    parasolid = _export_parasolid(work_part, output_dir, model_stem, run_id)
    import_part, import_bodies = _import_parasolid(session, parasolid, output_dir, model_stem, run_id)

    body_summary = _body_summary(work_part)
    solid_body_count = len([row for row in body_summary if row.get("is_solid_body")])
    validation = {
        "body_count": len(body_summary),
        "solid_body_count": solid_body_count,
        "min_expected_solid_body_count": 6,
        "operations": operations,
        "imported_body_count": len(import_bodies),
    }
    if solid_body_count < 6:
        raise RuntimeError("Edge/wall/trim pack validation failed: %s" % validation)
    if len(import_bodies) < 1:
        raise RuntimeError("Parasolid import validation failed: %s" % validation)
    _save_part(work_part)

    return {
        "status": "success",
        "backend": "nx",
        "operation": "create_edge_wall_trim_pack_demo",
        "message": "NX edge, wall, trim, taper, and Parasolid import pack completed.",
        "outputs": {"part": part_path, "parasolid": parasolid, "import_part": import_part},
        "inspection": {"bodies": body_summary, "imported_bodies": import_bodies},
        "validation": validation,
        "parameters": parameters,
        "errors": [],
        "metadata": {
            "job_path": job_path,
            "run_id": run_id,
            "schema_version": job.get("schema_version"),
            "draft_feature_status": "not_agent_facing; taper is represented by a controlled frustum in this pack",
        },
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
            "operation": str(job.get("operation") or "create_edge_wall_trim_pack_demo"),
            "message": "NX edge/wall/trim pack journal failed.",
            "outputs": {},
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
