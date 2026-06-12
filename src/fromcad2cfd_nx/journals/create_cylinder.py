"""Controlled NXOpen journal for creating a simple cylinder.

This journal consumes one validated FromCAD2CFD job JSON path. It creates a new
NX part, adds a centered cylinder, saves the part, exports STEP and Parasolid,
and writes JSON and Markdown reports. It is intentionally not a general Python
execution entry point.
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
    if args is None:
        args = []
    values = [str(item) for item in args if str(item) != "-args"]
    if not values:
        values = [str(item) for item in sys.argv[1:] if str(item) != "-args"]
    if not values:
        raise RuntimeError("Missing job JSON path. Use run_journal.exe create_cylinder.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    project_root = os.path.dirname(output_dir)
    return os.path.join(project_root, "reports")


def _result_markdown(result):
    lines = [
        "# NX Cylinder Journal Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "create_cylinder"),
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
    lines.extend(["", "## Errors", ""])
    errors = result.get("errors") or []
    if errors:
        for error in errors:
            lines.append("- %s" % error)
    else:
        lines.append("- None")
    lines.extend(["", "## Metadata", ""])
    metadata = result.get("metadata") or {}
    if metadata:
        for key in sorted(metadata):
            lines.append("- `%s`: `%s`" % (key, metadata[key]))
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _write_reports(job, job_path, result, run_id):
    stem = _safe_name(job.get("model_name"), "nx_cylinder")
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


def _set_cylinder_axis(builder, origin, direction):
    if hasattr(builder, "SetOrigin"):
        builder.SetOrigin(origin)
    else:
        builder.Origin = origin
    if hasattr(builder, "SetDirection"):
        builder.SetDirection(direction)
    else:
        builder.Direction = direction


def _create_centered_cylinder(session, work_part, radius_mm, height_mm):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD create cylinder")
    builder = work_part.Features.CreateCylinderBuilder(NXOpen.Features.Feature.Null)
    try:
        _set_length_expression(work_part, builder.Diameter, float(radius_mm) * 2.0)
        _set_length_expression(work_part, builder.Height, float(height_mm))
        _set_cylinder_axis(
            builder,
            NXOpen.Point3d(0.0, 0.0, -float(height_mm) / 2.0),
            NXOpen.Vector3d(0.0, 0.0, 1.0),
        )
        feature = builder.CommitFeature()
        try:
            feature.SetName("fromcad2cfd_test_cylinder")
        except Exception:
            try:
                feature.Name = "fromcad2cfd_test_cylinder"
            except Exception:
                pass
    finally:
        builder.Destroy()

    update_errors = session.UpdateManager.DoUpdate(mark_id)
    session.DeleteUndoMark(mark_id, "FromCAD2CFD create cylinder")
    if update_errors not in (None, 0):
        raise RuntimeError("NX update failed after cylinder creation: %s" % update_errors)
    return feature


def _feature_body_count(feature):
    try:
        bodies = feature.GetBodies()
        return len(list(bodies))
    except Exception:
        return None


def _save_part(work_part):
    work_part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)


def _commit_translator(creator):
    if hasattr(creator, "Apply"):
        creator.Apply()
    else:
        creator.Commit()


def _require_nonempty_file(path, label):
    for _index in range(20):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        time.sleep(0.25)
    if not os.path.exists(path):
        raise RuntimeError("%s export did not create the expected file: %s" % (label, path))
    if os.path.getsize(path) <= 0:
        raise RuntimeError("%s export created an empty file: %s" % (label, path))


def _export_step(session, work_part, path):
    creator = session.DexManager.CreateStepCreator()
    try:
        creator.ExportFrom = creator.ExportFromOption.DisplayPart
        creator.OutputFile = path
        creator.ObjectTypes.Solids = True
        creator.ObjectTypes.Surfaces = True
        creator.ObjectTypes.Curves = False
        creator.ObjectTypes.Csys = False
        creator.FileSaveFlag = False
        _commit_translator(creator)
    finally:
        if hasattr(creator, "Destroy"):
            try:
                creator.Destroy()
            except Exception:
                pass
    _require_nonempty_file(path, "STEP")


def _body_tags(work_part, feature=None):
    tags = []
    body_sources = []
    if feature is not None:
        try:
            body_sources.append(feature.GetBodies())
        except Exception:
            pass
    try:
        body_sources.append(work_part.Bodies.ToArray())
    except Exception:
        pass
    try:
        body_sources.append(work_part.Bodies)
    except Exception:
        pass
    for bodies in body_sources:
        for body in bodies:
            try:
                tag = body.Tag
            except Exception:
                continue
            if tag not in tags:
                tags.append(tag)
    if not tags:
        raise RuntimeError("No NX bodies were available for Parasolid export.")
    return tags


def _export_parasolid(work_part, feature, path):
    uf_session = NXOpen.UF.UFSession.GetUFSession()
    uf_session.Ps.ExportData(_body_tags(work_part, feature), path)
    _require_nonempty_file(path, "Parasolid")


def _export_formats(session, work_part, feature, output_dir, model_stem, run_id, export_formats):
    outputs = {}
    errors = []
    normalized = [str(item).strip().upper() for item in (export_formats or [])]
    if not normalized:
        normalized = ["PARASOLID"]

    ordered = []
    if "PARASOLID" in normalized:
        ordered.append("PARASOLID")
    for fmt in normalized:
        if fmt not in ordered:
            ordered.append(fmt)

    for fmt in ordered:
        if fmt == "STEP":
            path = _unique_file(output_dir, model_stem, ".stp", run_id)
            try:
                _export_step(session, work_part, path)
                outputs["step"] = path
            except Exception as exc:
                errors.append("Optional STEP export failed: %s" % exc)
        elif fmt == "PARASOLID":
            path = _unique_file(output_dir, model_stem, ".x_t", run_id)
            _export_parasolid(work_part, feature, path)
            outputs["parasolid"] = path
        else:
            raise RuntimeError("Unsupported export format for this journal: %s" % fmt)

    return outputs, errors


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "create_cylinder":
        raise RuntimeError("Unsupported operation for create_cylinder.py: %s" % job.get("operation"))
    parameters = job.get("parameters") or {}
    radius_mm = float(parameters.get("radius_mm"))
    height_mm = float(parameters.get("height_mm"))
    if radius_mm <= 0.0 or height_mm <= 0.0:
        raise RuntimeError("Cylinder radius and height must be positive.")
    return radius_mm, height_mm


def _run_job(job, job_path, run_id):
    radius_mm, height_mm = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)

    model_stem = _safe_name(job.get("model_name"), "nx_test_cylinder")
    part_path = _unique_file(output_dir, model_stem, ".prt", run_id)

    session = NXOpen.Session.GetSession()
    work_part = _new_part(session, part_path)
    if work_part is None:
        raise RuntimeError("NX did not create a work part.")

    feature = _create_centered_cylinder(session, work_part, radius_mm, height_mm)
    _save_part(work_part)

    exports, export_errors = _export_formats(session, work_part, feature, output_dir, model_stem, run_id, job.get("export_formats"))
    _save_part(work_part)

    outputs = {
        "part": part_path,
        "radius_mm": radius_mm,
        "height_mm": height_mm,
        "body_count": _feature_body_count(feature),
    }
    outputs.update(exports)

    return {
        "status": "partial" if export_errors else "success",
        "backend": "nx",
        "operation": "create_cylinder",
        "message": "NX cylinder journal completed." if not export_errors else "NX cylinder journal completed with optional export warnings.",
        "outputs": outputs,
        "errors": export_errors,
        "metadata": {
            "job_path": job_path,
            "run_id": run_id,
            "schema_version": job.get("schema_version"),
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
            "operation": str(job.get("operation") or "create_cylinder"),
            "message": "NX cylinder journal failed.",
            "outputs": {},
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
