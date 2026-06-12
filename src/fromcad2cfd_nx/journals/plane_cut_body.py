"""Controlled NXOpen journal for cutting one copied solid body by an axis-aligned plane."""

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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe plane_cut_body.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Plane Cut Body Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "plane_cut_body"),
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
    stem = _safe_name(job.get("model_name"), "nx_plane_cut_body")
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
        return opened[0], opened[1] if len(opened) > 1 else None
    return opened, None


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


def _select_body_by_index(bodies, index):
    if index < 1 or index > len(bodies):
        raise RuntimeError("body_index %s is out of range for %s bodies." % (index, len(bodies)))
    body = bodies[index - 1]
    if not bool(getattr(body, "IsSolidBody", False)):
        raise RuntimeError("Selected body_index %s is not a solid body." % index)
    return body


def _create_cutter_block(session, work_part, plane_axis, plane_offset, remove_side, extent):
    axis = plane_axis.lower()
    side = remove_side.lower()
    if axis not in ("x", "y", "z"):
        raise RuntimeError("plane_axis must be x, y, or z.")
    if side not in ("positive", "negative"):
        raise RuntimeError("remove_side must be positive or negative.")
    e = float(extent)
    o = float(plane_offset)
    if axis == "x":
        origin = (o if side == "positive" else o - e, -e, -e)
        lengths = (e, 2.0 * e, 2.0 * e)
    elif axis == "y":
        origin = (-e, o if side == "positive" else o - e, -e)
        lengths = (2.0 * e, e, 2.0 * e)
    else:
        origin = (-e, -e, o if side == "positive" else o - e)
        lengths = (2.0 * e, 2.0 * e, e)

    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD plane cutter")
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
    _do_update(session, mark_id, "plane cutter")
    session.DeleteUndoMark(mark_id, "FromCAD2CFD plane cutter")
    _set_name(feature, "fromcad2cfd_plane_cut_cutter")
    bodies = list(feature.GetBodies())
    if len(bodies) != 1:
        raise RuntimeError("Plane cutter block expected one body; got %s." % len(bodies))
    return bodies[0]


def _plane_cut(session, work_part, target_body, cutter_body):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD plane cut")
    try:
        result = work_part.Features.CreateSubtractFeature(target_body, False, [cutter_body], False, True)
        _do_update(session, mark_id, "plane cut subtract")
    finally:
        session.DeleteUndoMark(mark_id, "FromCAD2CFD plane cut")
    features = []
    if isinstance(result, tuple):
        features = list(result[0] or [])
    else:
        try:
            features = list(result)
        except Exception:
            features = [result]
    return features


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


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "plane_cut_body":
        raise RuntimeError("Unsupported operation for plane_cut_body.py: %s" % job.get("operation"))
    input_file = os.path.abspath(str(job.get("input_file") or ""))
    if not input_file or not os.path.exists(input_file):
        raise RuntimeError("Input model does not exist: %s" % input_file)
    if os.path.splitext(input_file)[1].lower() != ".prt":
        raise RuntimeError("plane_cut_body supports copied .prt inputs only. Import Parasolid first when starting from .x_t.")
    p = job.get("parameters") or {}
    body_index = int(p.get("body_index", 1))
    cutter_extent_mm = float(p.get("cutter_extent_mm", 1000.0))
    if body_index < 1:
        raise RuntimeError("body_index must be 1-based and positive.")
    if cutter_extent_mm <= 0.0:
        raise RuntimeError("cutter_extent_mm must be positive.")
    return input_file, body_index, p


def _run_job(job, job_path, run_id):
    input_file, body_index, parameters = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)
    model_stem = _safe_name(job.get("model_name"), os.path.splitext(os.path.basename(input_file))[0] + "_plane_cut")
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

    pre_bodies = _work_bodies(work_part)
    pre_summary = _body_summary(work_part)
    target_body = _select_body_by_index(pre_bodies, body_index)
    cutter = _create_cutter_block(
        session,
        work_part,
        str(parameters.get("plane_axis", "x")),
        float(parameters.get("plane_offset_mm", 0.0)),
        str(parameters.get("remove_side", "positive")),
        float(parameters.get("cutter_extent_mm", 1000.0)),
    )
    features = _plane_cut(session, work_part, target_body, cutter)
    post_summary = _body_summary(work_part)
    solid_body_count = len([row for row in post_summary if row.get("is_solid_body")])
    validation = {
        "pre_body_count": len(pre_summary),
        "post_body_count": len(post_summary),
        "solid_body_count": solid_body_count,
        "plane_cut_feature_count": len(features),
        "body_index": body_index,
        "plane_axis": str(parameters.get("plane_axis", "x")),
        "plane_offset_mm": float(parameters.get("plane_offset_mm", 0.0)),
        "remove_side": str(parameters.get("remove_side", "positive")),
    }
    if solid_body_count < 1:
        raise RuntimeError("Plane cut did not leave a solid body: %s" % validation)

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
        "operation": "plane_cut_body",
        "message": "NX plane cut completed on a copied part.",
        "outputs": {"source_model": input_file, "copied_part": copied_part, "parasolid": parasolid},
        "inspection": {"pre_bodies": pre_summary, "post_bodies": post_summary},
        "validation": validation,
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
            "operation": str(job.get("operation") or "plane_cut_body"),
            "message": "NX plane cut journal failed.",
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
