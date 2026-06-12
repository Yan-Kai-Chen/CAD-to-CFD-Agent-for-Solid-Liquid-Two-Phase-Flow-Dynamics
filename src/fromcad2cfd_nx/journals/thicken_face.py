"""Controlled NXOpen journal for thickening a selected face on a copied part."""

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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe thicken_face.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Thicken Face Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "thicken_face"),
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
    stem = _safe_name(job.get("model_name"), "nx_thicken_face")
    report_dir = _report_dir_for_job(job, job_path)
    json_path = _unique_file(report_dir, stem + "_journal_result", ".json", run_id)
    md_path = _unique_file(report_dir, stem + "_journal_result", ".md", run_id)
    result["reports"] = {"json": json_path, "markdown": md_path}
    _write_json(json_path, result)
    _write_text(md_path, _result_markdown(result))
    return result


def _open_display_part(session, path):
    opened = session.Parts.OpenDisplay(path)
    if isinstance(opened, tuple):
        part = opened[0]
        load_status = opened[1] if len(opened) > 1 else None
    else:
        part = opened
        load_status = None
    return part, load_status


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


def _select_face(work_part, body_index, face_index):
    bodies = _work_bodies(work_part)
    if body_index < 1 or body_index > len(bodies):
        raise RuntimeError("body_index %s is out of range for %s bodies." % (body_index, len(bodies)))
    body = bodies[body_index - 1]
    faces = list(body.GetFaces())
    if face_index < 1 or face_index > len(faces):
        raise RuntimeError("face_index %s is out of range for %s faces." % (face_index, len(faces)))
    return body, faces[face_index - 1]


def _extract_face(session, work_part, face):
    builder = work_part.Features.CreateExtractFaceBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.Type = NXOpen.Features.ExtractFaceBuilder.ExtractType.Face
        builder.FaceOption = NXOpen.Features.ExtractFaceBuilder.FaceOptionType.SingleFace
        builder.ParentPart = NXOpen.Features.ExtractFaceBuilder.ParentPartType.WorkPart
        builder.SurfaceType = NXOpen.Features.ExtractFaceBuilder.FaceSurfaceType.SameAsOriginal
        builder.HideOriginal = False
        builder.ObjectToExtract.Add(face)
        mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD extract face")
        feature = builder.CommitFeature()
        update_errors = session.UpdateManager.DoUpdate(mark_id)
        session.DeleteUndoMark(mark_id, "FromCAD2CFD extract face")
    finally:
        builder.Destroy()
    if update_errors not in (None, 0):
        raise RuntimeError("NX update failed after face extraction: %s" % update_errors)
    bodies = []
    try:
        bodies = list(feature.GetBodies())
    except Exception:
        pass
    if not bodies:
        bodies = _work_bodies(work_part)
    if not bodies:
        raise RuntimeError("Face extraction did not create a sheet body.")
    sheet_body = bodies[-1]
    sheet_faces = list(sheet_body.GetFaces())
    if len(sheet_faces) != 1:
        raise RuntimeError("Extracted sheet body does not have exactly one face; got %s." % len(sheet_faces))
    try:
        feature.SetName("fromcad2cfd_extracted_sheet_face")
    except Exception:
        pass
    return feature, sheet_body, sheet_faces[0]


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


def _thicken_face(session, work_part, face, thickness_mm):
    builder = work_part.Features.CreateThickenBuilder(NXOpen.Features.Feature.Null)
    try:
        _set_length_expression(work_part, builder.FirstOffset, float(thickness_mm))
        _set_length_expression(work_part, builder.SecondOffset, 0.0)
        try:
            builder.SetTolerance(0.01)
        except Exception:
            builder.Tolerance = 0.01
        try:
            builder.BooleanOperation.Type = NXOpen.GeometricUtilities.BooleanOperation.BooleanType.Create
        except Exception:
            pass
        rule = work_part.ScRuleFactory.CreateRuleFaceDumb([face])
        builder.FaceCollector.ReplaceRules([rule], False)
        mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD thicken face")
        feature = builder.CommitFeature()
        update_errors = session.UpdateManager.DoUpdate(mark_id)
        session.DeleteUndoMark(mark_id, "FromCAD2CFD thicken face")
    finally:
        builder.Destroy()
    if update_errors not in (None, 0):
        raise RuntimeError("NX update failed after thicken: %s" % update_errors)
    try:
        feature.SetName("fromcad2cfd_thicken_face")
    except Exception:
        pass
    return feature


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


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "thicken_face":
        raise RuntimeError("Unsupported operation for thicken_face.py: %s" % job.get("operation"))
    input_file = os.path.abspath(str(job.get("input_file") or ""))
    if not input_file or not os.path.exists(input_file):
        raise RuntimeError("Input model does not exist: %s" % input_file)
    if os.path.splitext(input_file)[1].lower() != ".prt":
        raise RuntimeError("thicken_face currently supports copied .prt inputs only: %s" % input_file)
    parameters = job.get("parameters") or {}
    body_index = int(parameters.get("body_index", 1))
    face_index = int(parameters.get("face_index", 1))
    thickness_mm = float(parameters.get("thickness_mm", 2.0))
    expected_min_solid_bodies = int(parameters.get("expected_min_solid_bodies", 1))
    if min(body_index, face_index, expected_min_solid_bodies) < 1:
        raise RuntimeError("body_index, face_index, and expected_min_solid_bodies must be positive.")
    if thickness_mm <= 0.0:
        raise RuntimeError("thickness_mm must be positive.")
    return input_file, body_index, face_index, thickness_mm, expected_min_solid_bodies


def _run_job(job, job_path, run_id):
    input_file, body_index, face_index, thickness_mm, expected_min_solid_bodies = _validate_job(job)
    parameters = job.get("parameters") or {}
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)
    model_stem = _safe_name(job.get("model_name"), os.path.splitext(os.path.basename(input_file))[0] + "_thicken_face")
    copied_part = _unique_file(output_dir, model_stem + "_input_copy", ".prt", run_id)
    shutil.copy2(input_file, copied_part)

    session = NXOpen.Session.GetSession()
    work_part, load_status = _open_display_part(session, copied_part)
    if work_part is None:
        raise RuntimeError("NX did not open copied model: %s" % copied_part)
    try:
        work_part.LoadThisPartFully()
    except Exception:
        pass

    pre_summary = _body_summary(work_part)
    _source_body, selected_face = _select_face(work_part, body_index, face_index)
    extracted_sheet = None
    thicken_face = selected_face
    if bool(parameters.get("extract_face_first", True)):
        _extract_feature, extracted_sheet, thicken_face = _extract_face(session, work_part, selected_face)
    feature = _thicken_face(session, work_part, thicken_face, thickness_mm)
    post_summary = _body_summary(work_part)
    solid_body_count = len([row for row in post_summary if row.get("is_solid_body")])
    sheet_body_count = len([row for row in post_summary if row.get("is_sheet_body")])
    validation = {
        "pre_body_count": len(pre_summary),
        "post_body_count": len(post_summary),
        "solid_body_count": solid_body_count,
        "sheet_body_count": sheet_body_count,
        "expected_min_solid_bodies": expected_min_solid_bodies,
        "body_index": body_index,
        "face_index": face_index,
        "thickness_mm": thickness_mm,
        "extract_face_first": bool(parameters.get("extract_face_first", True)),
        "extracted_sheet_is_sheet_body": bool(getattr(extracted_sheet, "IsSheetBody", False)) if extracted_sheet is not None else None,
    }
    if solid_body_count < expected_min_solid_bodies:
        raise RuntimeError("Thicken validation failed: %s" % validation)

    _save_part(work_part)
    parasolid = _export_parasolid(work_part, output_dir, model_stem, run_id)
    _save_part(work_part)
    if load_status is not None:
        try:
            load_status.Dispose()
        except Exception:
            pass

    return {
        "status": "success",
        "backend": "nx",
        "operation": "thicken_face",
        "message": "NX face/sheet thicken completed on a copied part.",
        "outputs": {
            "source_model": input_file,
            "copied_part": copied_part,
            "parasolid": parasolid,
        },
        "inspection": {
            "pre_bodies": pre_summary,
            "post_bodies": post_summary,
        },
        "validation": validation,
        "errors": [],
        "metadata": {
            "job_path": job_path,
            "run_id": run_id,
            "schema_version": job.get("schema_version"),
            "thicken_feature_type": str(type(feature)),
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
            "operation": str(job.get("operation") or "thicken_face"),
            "message": "NX thicken face journal failed.",
            "outputs": {},
            "inspection": {},
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
