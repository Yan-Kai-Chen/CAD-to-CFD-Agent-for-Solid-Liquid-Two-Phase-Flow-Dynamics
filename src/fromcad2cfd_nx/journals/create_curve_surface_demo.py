"""Controlled NXOpen journal for basic curves and a bounded-plane sheet surface."""

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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe create_curve_surface_demo.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Curve Surface Demo Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "create_curve_surface_demo"),
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
    stem = _safe_name(job.get("model_name"), "nx_curve_surface_demo")
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
    for body in work_part.Bodies:
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


def _body_summary(work_part):
    rows = []
    try:
        bodies = [body for body in work_part.Bodies]
    except Exception:
        bodies = []
    for index, body in enumerate(bodies, start=1):
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


def _add_curve_to_section(work_part, section, curve, help_point):
    rule = work_part.ScRuleFactory.CreateRuleCurveDumb([curve])
    null_obj = NXOpen.NXObject.Null
    try:
        mode = NXOpen.Section.ModeCreate
    except Exception:
        mode = NXOpen.Section.Mode.Create
    section.AddToSection([rule], curve, null_obj, null_obj, help_point, mode)


def _create_curves(work_part, width_mm, height_mm, circle_radius_mm, ellipse_major_mm, ellipse_minor_mm):
    half_w = float(width_mm) / 2.0
    half_h = float(height_mm) / 2.0
    points = [
        (NXOpen.Point3d(-half_w, -half_h, 0.0), NXOpen.Point3d(half_w, -half_h, 0.0)),
        (NXOpen.Point3d(half_w, -half_h, 0.0), NXOpen.Point3d(half_w, half_h, 0.0)),
        (NXOpen.Point3d(half_w, half_h, 0.0), NXOpen.Point3d(-half_w, half_h, 0.0)),
        (NXOpen.Point3d(-half_w, half_h, 0.0), NXOpen.Point3d(-half_w, -half_h, 0.0)),
    ]
    lines = []
    curve_rows = []
    for index, pair in enumerate(points, start=1):
        line = work_part.Curves.CreateLine(pair[0], pair[1])
        _set_name(line, "fromcad2cfd_rectangle_line_%d" % index)
        lines.append(line)
        curve_rows.append({"name": "rectangle_line_%d" % index, "type": "Line", "tag": int(line.Tag)})

    circle = work_part.Curves.CreateArc(
        NXOpen.Point3d(0.0, half_h + circle_radius_mm + 10.0, 0.0),
        NXOpen.Vector3d(1.0, 0.0, 0.0),
        NXOpen.Vector3d(0.0, 1.0, 0.0),
        float(circle_radius_mm),
        0.0,
        2.0 * math.pi,
    )
    _set_name(circle, "fromcad2cfd_reference_circle")
    curve_rows.append({"name": "reference_circle", "type": "Arc", "tag": int(circle.Tag)})

    ellipse = work_part.Curves.CreateEllipse(
        NXOpen.Point3d(0.0, -half_h - ellipse_minor_mm - 10.0, 0.0),
        NXOpen.Vector3d(1.0, 0.0, 0.0),
        NXOpen.Vector3d(0.0, 1.0, 0.0),
        float(ellipse_major_mm),
        float(ellipse_minor_mm),
        0.0,
        2.0 * math.pi,
    )
    _set_name(ellipse, "fromcad2cfd_reference_ellipse")
    curve_rows.append({"name": "reference_ellipse", "type": "Ellipse", "tag": int(ellipse.Tag)})
    return lines, curve_rows


def _create_bounded_plane(session, work_part, boundary_lines):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD bounded plane")
    builder = work_part.Features.CreateBoundedPlaneBuilder(NXOpen.Features.BoundedPlane.Null)
    try:
        section = builder.BoundingCurves
        section.SetAllowedEntityTypes(NXOpen.Section.AllowTypes.OnlyCurves)
        help_points = [
            NXOpen.Point3d(0.0, -1.0, 0.0),
            NXOpen.Point3d(1.0, 0.0, 0.0),
            NXOpen.Point3d(0.0, 1.0, 0.0),
            NXOpen.Point3d(-1.0, 0.0, 0.0),
        ]
        for curve, help_point in zip(boundary_lines, help_points):
            _add_curve_to_section(work_part, section, curve, help_point)
        feature = builder.CommitFeature()
        update_errors = session.UpdateManager.DoUpdate(mark_id)
    finally:
        builder.Destroy()
        session.DeleteUndoMark(mark_id, "FromCAD2CFD bounded plane")
    if update_errors not in (None, 0):
        raise RuntimeError("NX update failed after bounded plane creation: %s" % update_errors)
    _set_name(feature, "fromcad2cfd_bounded_plane")
    return feature


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "create_curve_surface_demo":
        raise RuntimeError("Unsupported operation for create_curve_surface_demo.py: %s" % job.get("operation"))
    parameters = job.get("parameters") or {}
    width = float(parameters.get("rectangle_width_mm", 40.0))
    height = float(parameters.get("rectangle_height_mm", 30.0))
    circle_radius = float(parameters.get("circle_radius_mm", 8.0))
    ellipse_major = float(parameters.get("ellipse_major_radius_mm", 12.0))
    ellipse_minor = float(parameters.get("ellipse_minor_radius_mm", 6.0))
    if min(width, height, circle_radius, ellipse_major, ellipse_minor) <= 0.0:
        raise RuntimeError("All curve and surface dimensions must be positive.")
    if ellipse_minor > ellipse_major:
        raise RuntimeError("Ellipse minor radius must not exceed major radius.")
    return width, height, circle_radius, ellipse_major, ellipse_minor


def _run_job(job, job_path, run_id):
    width, height, circle_radius, ellipse_major, ellipse_minor = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)
    model_stem = _safe_name(job.get("model_name"), "nx_curve_surface_demo")
    part_path = _unique_file(output_dir, model_stem, ".prt", run_id)

    session = NXOpen.Session.GetSession()
    work_part = _new_part(session, part_path)
    if work_part is None:
        raise RuntimeError("NX did not create a work part.")

    boundary_lines, curves = _create_curves(work_part, width, height, circle_radius, ellipse_major, ellipse_minor)
    feature = _create_bounded_plane(session, work_part, boundary_lines)
    body_summary = _body_summary(work_part)
    sheet_body_count = len([row for row in body_summary if row.get("is_sheet_body")])
    solid_body_count = len([row for row in body_summary if row.get("is_solid_body")])
    validation = {
        "curve_count": len(curves),
        "expected_curve_count": 6,
        "body_count": len(body_summary),
        "sheet_body_count": sheet_body_count,
        "solid_body_count": solid_body_count,
        "rectangle_width_mm": width,
        "rectangle_height_mm": height,
    }
    if len(curves) != 6 or sheet_body_count != 1:
        raise RuntimeError("Curve surface validation failed: %s" % validation)

    _save_part(work_part)
    parasolid = _export_parasolid(work_part, output_dir, model_stem, run_id)
    _save_part(work_part)

    return {
        "status": "success",
        "backend": "nx",
        "operation": "create_curve_surface_demo",
        "message": "NX basic curve and bounded-plane surface demo completed.",
        "outputs": {
            "part": part_path,
            "parasolid": parasolid,
        },
        "curves": curves,
        "inspection": {
            "bodies": body_summary,
        },
        "validation": validation,
        "errors": [],
        "metadata": {
            "job_path": job_path,
            "run_id": run_id,
            "schema_version": job.get("schema_version"),
            "surface_feature_type": str(type(feature)),
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
            "operation": str(job.get("operation") or "create_curve_surface_demo"),
            "message": "NX curve surface demo journal failed.",
            "outputs": {},
            "curves": [],
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
