"""Controlled NXOpen journal for body-level boolean subtract on a copied part."""

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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe boolean_subtract_bodies.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Boolean Subtract Bodies Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "boolean_subtract_bodies"),
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
    stem = _safe_name(job.get("model_name"), "nx_boolean_subtract_bodies")
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
            name = str(body.Name)
        except Exception:
            name = ""
        try:
            journal_id = str(body.JournalIdentifier)
        except Exception:
            journal_id = ""
        try:
            face_count = len(list(body.GetFaces()))
        except Exception:
            face_count = None
        try:
            edge_count = len(list(body.GetEdges()))
        except Exception:
            edge_count = None
        try:
            is_solid = bool(body.IsSolidBody)
        except Exception:
            is_solid = None
        try:
            is_sheet = bool(body.IsSheetBody)
        except Exception:
            is_sheet = None
        rows.append(
            {
                "index": index,
                "name": name,
                "journal_identifier": journal_id,
                "is_solid_body": is_solid,
                "is_sheet_body": is_sheet,
                "face_count": face_count,
                "edge_count": edge_count,
            }
        )
    return rows


def _select_body_by_index(bodies, index, label):
    if index < 1 or index > len(bodies):
        raise RuntimeError("%s body index %s is out of range for %s bodies." % (label, index, len(bodies)))
    return bodies[index - 1]


def _require_solid(body, label):
    try:
        if bool(body.IsSolidBody):
            return
    except Exception:
        pass
    raise RuntimeError("%s body is not a solid body; boolean subtract requires solid target and tool bodies." % label)


def _boolean_subtract(session, work_part, target_body, tool_bodies, retain_target_body, retain_tool_bodies):
    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD boolean subtract bodies")
    try:
        result = work_part.Features.CreateSubtractFeature(
            target_body,
            bool(retain_target_body),
            list(tool_bodies),
            bool(retain_tool_bodies),
            True,
        )
        update_errors = session.UpdateManager.DoUpdate(mark_id)
    finally:
        session.DeleteUndoMark(mark_id, "FromCAD2CFD boolean subtract bodies")
    if update_errors not in (None, 0):
        raise RuntimeError("NX update failed after boolean subtract: %s" % update_errors)

    features = []
    non_associative = None
    unparameterized = None
    if isinstance(result, tuple):
        if len(result) > 0:
            features = list(result[0] or [])
        if len(result) > 1:
            non_associative = bool(result[1])
        if len(result) > 2:
            unparameterized = bool(result[2])
    else:
        try:
            features = list(result)
        except Exception:
            features = [result]
    for index, feature in enumerate(features):
        try:
            feature.SetName("fromcad2cfd_body_subtract_%d" % (index + 1))
        except Exception:
            pass
    return features, non_associative, unparameterized


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
    if job.get("operation") != "boolean_subtract_bodies":
        raise RuntimeError("Unsupported operation for boolean_subtract_bodies.py: %s" % job.get("operation"))
    input_file = os.path.abspath(str(job.get("input_file") or ""))
    if not input_file or not os.path.exists(input_file):
        raise RuntimeError("Input model does not exist: %s" % input_file)
    if os.path.splitext(input_file)[1].lower() != ".prt":
        raise RuntimeError("boolean_subtract_bodies currently supports copied .prt inputs only: %s" % input_file)

    parameters = job.get("parameters") or {}
    target_body_index = int(parameters.get("target_body_index", 1))
    tool_body_indices = [int(item) for item in parameters.get("tool_body_indices", [2])]
    expected_body_count = int(parameters.get("expected_body_count", 1))
    if target_body_index < 1:
        raise RuntimeError("target_body_index must be 1-based and positive.")
    if not tool_body_indices or any(index < 1 for index in tool_body_indices):
        raise RuntimeError("tool_body_indices must be non-empty 1-based positive indices.")
    if target_body_index in tool_body_indices:
        raise RuntimeError("target body cannot also be a tool body.")
    if expected_body_count < 1:
        raise RuntimeError("expected_body_count must be positive.")
    return input_file, target_body_index, tool_body_indices, expected_body_count


def _run_job(job, job_path, run_id):
    input_file, target_body_index, tool_body_indices, expected_body_count = _validate_job(job)
    parameters = job.get("parameters") or {}
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)

    model_stem = _safe_name(job.get("model_name"), os.path.splitext(os.path.basename(input_file))[0] + "_boolean_subtract")
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
    target_body = _select_body_by_index(pre_bodies, target_body_index, "target")
    tool_bodies = [_select_body_by_index(pre_bodies, index, "tool") for index in tool_body_indices]
    _require_solid(target_body, "target")
    for index, body in zip(tool_body_indices, tool_bodies):
        _require_solid(body, "tool index %s" % index)

    features, non_associative, unparameterized = _boolean_subtract(
        session,
        work_part,
        target_body,
        tool_bodies,
        bool(parameters.get("retain_target_body", False)),
        bool(parameters.get("retain_tool_bodies", False)),
    )
    post_summary = _body_summary(work_part)
    post_body_count = len(_work_bodies(work_part))
    solid_body_count = len([row for row in post_summary if row.get("is_solid_body")])
    validation = {
        "pre_body_count": len(pre_bodies),
        "expected_body_count": expected_body_count,
        "post_body_count": post_body_count,
        "solid_body_count": solid_body_count,
        "boolean_feature_count": len(features),
        "non_associative_boolean": non_associative,
        "unparameterized_solids": unparameterized,
        "target_body_index": target_body_index,
        "tool_body_indices": tool_body_indices,
    }
    if post_body_count != expected_body_count:
        raise RuntimeError("Unexpected post-boolean body count: %s" % validation)
    if solid_body_count < 1:
        raise RuntimeError("Boolean subtract did not leave a solid body: %s" % validation)

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
        "operation": "boolean_subtract_bodies",
        "message": "NX body-level boolean subtract completed on a copied part.",
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
            "operation": str(job.get("operation") or "boolean_subtract_bodies"),
            "message": "NX body-level boolean subtract journal failed.",
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
