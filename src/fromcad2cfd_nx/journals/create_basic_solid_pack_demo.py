"""Controlled NXOpen journal for the basic NX solid-modeling capability pack.

This journal consumes one validated FromCAD2CFD job JSON path. It creates a
synthetic model that exercises the core foundation operations used by later CAD
to CFD workflows: block, sphere, cone, boolean unite, boolean intersect, and
copy-translate. It saves `.prt`, exports Parasolid `.x_t`, and writes JSON and
Markdown reports. It is intentionally not a general Python execution entry
point.
"""

from __future__ import print_function

import datetime
import io
import json
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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe create_basic_solid_pack_demo.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Basic Solid Pack Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "create_basic_solid_pack_demo"),
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
    stem = _safe_name(job.get("model_name"), "nx_basic_solid_pack_demo")
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


def _set_length_expression(work_part, expression, value):
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
    raise RuntimeError("Unable to set NX length expression to %s." % text)


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


def _feature_body(feature, label):
    try:
        bodies = list(feature.GetBodies())
    except Exception:
        bodies = []
    if len(bodies) != 1:
        raise RuntimeError("%s did not create exactly one body; got %s." % (label, len(bodies)))
    return bodies[0]


def _do_update(session, mark_id, label):
    update_errors = session.UpdateManager.DoUpdate(mark_id)
    if update_errors not in (None, 0):
        raise RuntimeError("NX update failed after %s: %s" % (label, update_errors))


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


def _create_sphere(session, work_part, name, center, diameter):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, name)
    builder = work_part.Features.CreateSphereBuilder(NXOpen.Features.Sphere.Null)
    try:
        builder.Type = NXOpen.Features.SphereBuilder.Types.CenterPointAndDiameter
        point = work_part.Points.CreatePoint(NXOpen.Point3d(float(center[0]), float(center[1]), float(center[2])))
        builder.CenterPoint = point
        _set_length_expression(work_part, builder.Diameter, diameter)
        feature = builder.CommitFeature()
    finally:
        builder.Destroy()
    _do_update(session, mark_id, name)
    session.DeleteUndoMark(mark_id, name)
    _set_name(feature, name)
    return feature, _feature_body(feature, name)


def _create_cone(session, work_part, name, origin, direction, base_diameter, top_diameter, height):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, name)
    builder = work_part.Features.CreateConeBuilder(NXOpen.Features.Cone.Null)
    try:
        builder.Type = NXOpen.Features.ConeBuilder.Types.DiametersAndHeight
        axis = work_part.Axes.CreateAxis(
            NXOpen.Point3d(float(origin[0]), float(origin[1]), float(origin[2])),
            NXOpen.Vector3d(float(direction[0]), float(direction[1]), float(direction[2])),
            NXOpen.SmartObject.UpdateOption.WithinModeling,
        )
        builder.Axis = axis
        _set_length_expression(work_part, builder.BaseDiameter, base_diameter)
        _set_length_expression(work_part, builder.TopDiameter, top_diameter)
        _set_length_expression(work_part, builder.Height, height)
        feature = builder.CommitFeature()
    finally:
        builder.Destroy()
    _do_update(session, mark_id, name)
    session.DeleteUndoMark(mark_id, name)
    _set_name(feature, name)
    return feature, _feature_body(feature, name)


def _boolean_feature(session, work_part, operation, target_body, tool_body, name):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, name)
    try:
        if operation == "unite":
            result = work_part.Features.CreateUniteFeature(target_body, False, [tool_body], False, True)
        elif operation == "intersect":
            result = work_part.Features.CreateIntersectFeature(target_body, False, [tool_body], False, True)
        else:
            raise RuntimeError("Unsupported boolean operation: %s" % operation)
        _do_update(session, mark_id, name)
    finally:
        session.DeleteUndoMark(mark_id, name)
    features = []
    if isinstance(result, tuple):
        features = list(result[0] or [])
    else:
        try:
            features = list(result)
        except Exception:
            features = [result]
    for index, feature in enumerate(features):
        _set_name(feature, "%s_%d" % (name, index + 1))
    return features


def _translate_copy(session, work_part, body, delta_xyz, name):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, name)
    builder = work_part.BaseFeatures.CreateMoveObjectBuilder(NXOpen.Features.MoveObject.Null)
    try:
        builder.ObjectToMoveObject.Add(body)
        builder.MoveObjectResult = NXOpen.Features.MoveObjectBuilder.MoveObjectResultOptions.CopyOriginal
        builder.Associative = False
        builder.MoveParents = False
        builder.NumberOfCopies = 1
        motion = builder.TransformMotion
        motion.Option = NXOpen.GeometricUtilities.ModlMotion.Options.DeltaXyz
        motion.DeltaEnum = NXOpen.GeometricUtilities.ModlMotion.Delta.ReferenceWcsWorkPart
        _set_length_expression(work_part, motion.DeltaXc, float(delta_xyz[0]))
        _set_length_expression(work_part, motion.DeltaYc, float(delta_xyz[1]))
        _set_length_expression(work_part, motion.DeltaZc, float(delta_xyz[2]))
        feature = builder.Commit()
        _do_update(session, mark_id, name)
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, name)
    return feature


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
        try:
            faces = list(body.GetFaces())
        except Exception:
            faces = []
        try:
            edges = list(body.GetEdges())
        except Exception:
            edges = []
        rows.append(
            {
                "index": index,
                "name": str(getattr(body, "Name", "")),
                "is_solid_body": bool(getattr(body, "IsSolidBody", False)),
                "is_sheet_body": bool(getattr(body, "IsSheetBody", False)),
                "face_count": len(faces),
                "edge_count": len(edges),
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
    if not os.path.exists(path):
        raise RuntimeError("%s export did not create the expected file: %s" % (label, path))
    if os.path.getsize(path) <= 0:
        raise RuntimeError("%s export created an empty file: %s" % (label, path))


def _body_tags(work_part):
    tags = []
    for body in _work_bodies(work_part):
        try:
            tag = body.Tag
        except Exception:
            continue
        if tag not in tags:
            tags.append(tag)
    if not tags:
        raise RuntimeError("No NX bodies were available for Parasolid export.")
    return tags


def _export_parasolid(work_part, output_dir, model_stem, run_id):
    path = _unique_file(output_dir, model_stem, ".x_t", run_id)
    NXOpen.UF.UFSession.GetUFSession().Ps.ExportData(_body_tags(work_part), path)
    _require_nonempty_file(path, "Parasolid")
    return path


def _positive_float(parameters, name, default):
    value = float(parameters.get(name, default))
    if value <= 0.0:
        raise RuntimeError("%s must be positive." % name)
    return value


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "create_basic_solid_pack_demo":
        raise RuntimeError("Unsupported operation for create_basic_solid_pack_demo.py: %s" % job.get("operation"))
    parameters = job.get("parameters") or {}
    values = {
        "block_length_mm": _positive_float(parameters, "block_length_mm", 20.0),
        "block_width_mm": _positive_float(parameters, "block_width_mm", 20.0),
        "block_height_mm": _positive_float(parameters, "block_height_mm", 20.0),
        "sphere_diameter_mm": _positive_float(parameters, "sphere_diameter_mm", 18.0),
        "cone_base_diameter_mm": _positive_float(parameters, "cone_base_diameter_mm", 18.0),
        "cone_top_diameter_mm": _positive_float(parameters, "cone_top_diameter_mm", 6.0),
        "cone_height_mm": _positive_float(parameters, "cone_height_mm", 24.0),
        "boolean_block_length_mm": _positive_float(parameters, "boolean_block_length_mm", 24.0),
        "boolean_block_width_mm": _positive_float(parameters, "boolean_block_width_mm", 20.0),
        "boolean_block_height_mm": _positive_float(parameters, "boolean_block_height_mm", 20.0),
        "boolean_overlap_mm": _positive_float(parameters, "boolean_overlap_mm", 12.0),
        "translate_copy_y_mm": _positive_float(parameters, "translate_copy_y_mm", 35.0),
    }
    if values["cone_top_diameter_mm"] >= values["cone_base_diameter_mm"]:
        raise RuntimeError("cone_top_diameter_mm must be smaller than cone_base_diameter_mm.")
    if values["boolean_overlap_mm"] >= values["boolean_block_length_mm"]:
        raise RuntimeError("boolean_overlap_mm must be smaller than boolean_block_length_mm.")
    return values


def _run_job(job, job_path, run_id):
    parameters = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)
    model_stem = _safe_name(job.get("model_name"), "nx_basic_solid_pack_demo")
    part_path = _unique_file(output_dir, model_stem, ".prt", run_id)

    session = NXOpen.Session.GetSession()
    work_part = _new_part(session, part_path)
    if work_part is None:
        raise RuntimeError("NX did not create a work part.")

    block_lengths = (
        parameters["block_length_mm"],
        parameters["block_width_mm"],
        parameters["block_height_mm"],
    )
    boolean_lengths = (
        parameters["boolean_block_length_mm"],
        parameters["boolean_block_width_mm"],
        parameters["boolean_block_height_mm"],
    )

    _block_feature, block_body = _create_block(session, work_part, "fromcad2cfd_basic_block", (-60.0, -10.0, -10.0), block_lengths)
    _create_sphere(session, work_part, "fromcad2cfd_basic_sphere", (-20.0, 0.0, 0.0), parameters["sphere_diameter_mm"])
    _create_cone(
        session,
        work_part,
        "fromcad2cfd_basic_cone",
        (20.0, 0.0, -0.5 * parameters["cone_height_mm"]),
        (0.0, 0.0, 1.0),
        parameters["cone_base_diameter_mm"],
        parameters["cone_top_diameter_mm"],
        parameters["cone_height_mm"],
    )

    base_x = 60.0
    overlap_shift = parameters["boolean_block_length_mm"] - parameters["boolean_overlap_mm"]
    _target_feature, unite_target = _create_block(session, work_part, "fromcad2cfd_unite_target", (base_x, -10.0, -10.0), boolean_lengths)
    _tool_feature, unite_tool = _create_block(session, work_part, "fromcad2cfd_unite_tool", (base_x + overlap_shift, -10.0, -10.0), boolean_lengths)
    unite_features = _boolean_feature(session, work_part, "unite", unite_target, unite_tool, "fromcad2cfd_boolean_unite")

    intersect_x = 110.0
    _target_feature, intersect_target = _create_block(session, work_part, "fromcad2cfd_intersect_target", (intersect_x, -10.0, -10.0), boolean_lengths)
    _tool_feature, intersect_tool = _create_block(session, work_part, "fromcad2cfd_intersect_tool", (intersect_x + overlap_shift, -10.0, -10.0), boolean_lengths)
    intersect_features = _boolean_feature(session, work_part, "intersect", intersect_target, intersect_tool, "fromcad2cfd_boolean_intersect")

    _translate_copy(session, work_part, block_body, (0.0, parameters["translate_copy_y_mm"], 0.0), "fromcad2cfd_translate_copy")
    body_summary = _body_summary(work_part)
    solid_body_count = len([row for row in body_summary if row.get("is_solid_body")])
    validation = {
        "expected_body_count": 6,
        "body_count": len(body_summary),
        "solid_body_count": solid_body_count,
        "expected_solid_body_count": 6,
        "unite_feature_count": len(unite_features),
        "intersect_feature_count": len(intersect_features),
        "copy_translate_expected": True,
    }
    if len(body_summary) != 6 or solid_body_count != 6 or len(unite_features) != 1 or len(intersect_features) != 1:
        raise RuntimeError("Basic solid pack validation failed: %s" % validation)

    _save_part(work_part)
    parasolid = _export_parasolid(work_part, output_dir, model_stem, run_id)
    _save_part(work_part)

    return {
        "status": "success",
        "backend": "nx",
        "operation": "create_basic_solid_pack_demo",
        "message": "NX basic solid modeling pack completed.",
        "outputs": {"part": part_path, "parasolid": parasolid},
        "inspection": {"bodies": body_summary},
        "validation": validation,
        "parameters": parameters,
        "errors": [],
        "metadata": {
            "job_path": job_path,
            "run_id": run_id,
            "schema_version": job.get("schema_version"),
            "operations": ["block", "sphere", "cone", "boolean_unite", "boolean_intersect", "copy_translate"],
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
            "operation": str(job.get("operation") or "create_basic_solid_pack_demo"),
            "message": "NX basic solid pack journal failed.",
            "outputs": {},
            "validation": {},
            "errors": [str(exc)],
            "metadata": {
                "job_path": job_path,
                "run_id": run_id,
                "traceback": traceback.format_exc(),
            },
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
