"""Controlled NXOpen journal for model classification before surface repair."""

from __future__ import print_function

import datetime
import io
import json
import os
import re
import shutil
import sys
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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe inspect_model.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Model Inspection Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "inspect_model"),
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
    lines.extend(["", "## Body Summary", ""])
    inspection = result.get("inspection") or {}
    summary = inspection.get("summary") or {}
    if summary:
        for key in sorted(summary):
            lines.append("- `%s`: `%s`" % (key, summary[key]))
    else:
        lines.append("- None")
    lines.extend(["", "## Bodies", ""])
    bodies = inspection.get("bodies") or []
    if bodies:
        for body in bodies:
            lines.append(
                "- `%s`: type=`%s`, faces=`%s`, edges=`%s`, facets=`%s`"
                % (
                    body.get("name") or body.get("journal_identifier") or body.get("index"),
                    body.get("classification"),
                    body.get("face_count"),
                    body.get("edge_count"),
                    body.get("facet_count"),
                )
            )
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
    stem = _safe_name(job.get("model_name"), "nx_model_inspection")
    report_dir = _report_dir_for_job(job, job_path)
    json_path = _unique_file(report_dir, stem + "_journal_result", ".json", run_id)
    md_path = _unique_file(report_dir, stem + "_journal_result", ".md", run_id)
    result["reports"] = {"json": json_path, "markdown": md_path}
    _write_json(json_path, result)
    _write_text(md_path, _result_markdown(result))
    return result


def _open_display_part(session, path):
    opened = session.Parts.OpenDisplay(path)
    load_status = None
    if isinstance(opened, tuple):
        part = opened[0]
        if len(opened) > 1:
            load_status = opened[1]
    else:
        part = opened
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


def _safe_number(label, func, warnings):
    try:
        return func()
    except Exception as exc:
        warnings.append("%s failed: %s: %s" % (label, type(exc).__name__, exc))
        return None


def _bounding_box(body, warnings):
    try:
        uf_session = NXOpen.UF.UFSession.GetUFSession()
        box = uf_session.Sf.BodyAskBoundingBox(body.Tag)
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


def _classify_body(is_solid, is_sheet, is_convergent, facet_count, face_count):
    if is_solid:
        return "solid"
    if is_sheet:
        return "sheet"
    if is_convergent:
        return "convergent"
    if facet_count and (face_count in (None, 0)):
        return "facet"
    return "unknown"


def _inspect_part(work_part):
    bodies = []
    summary = {
        "body_count": 0,
        "solid_body_count": 0,
        "sheet_body_count": 0,
        "convergent_body_count": 0,
        "facet_candidate_count": 0,
        "unknown_body_count": 0,
        "total_face_count": 0,
        "total_edge_count": 0,
    }
    warnings = []
    for index, body in enumerate(_work_bodies(work_part), start=1):
        body_warnings = []
        is_solid = _safe_bool(body, "IsSolidBody")
        is_sheet = _safe_bool(body, "IsSheetBody")
        is_convergent = _safe_bool(body, "IsConvergentBody")
        face_count = _safe_count("GetFaces", body.GetFaces, body_warnings)
        edge_count = _safe_count("GetEdges", body.GetEdges, body_warnings)
        facet_count = _safe_number("GetNumberOfFacets", body.GetNumberOfFacets, body_warnings)
        vertex_count = _safe_number("GetNumberOfVertices", body.GetNumberOfVertices, body_warnings)
        classification = _classify_body(is_solid, is_sheet, is_convergent, facet_count, face_count)

        if classification == "solid":
            summary["solid_body_count"] += 1
        elif classification == "sheet":
            summary["sheet_body_count"] += 1
        elif classification == "convergent":
            summary["convergent_body_count"] += 1
        elif classification == "facet":
            summary["facet_candidate_count"] += 1
        else:
            summary["unknown_body_count"] += 1

        if face_count is not None:
            summary["total_face_count"] += face_count
        if edge_count is not None:
            summary["total_edge_count"] += edge_count

        bodies.append(
            {
                "index": index,
                "name": _body_name(body),
                "journal_identifier": _safe_number("JournalIdentifier", lambda: body.JournalIdentifier, body_warnings),
                "classification": classification,
                "is_solid_body": is_solid,
                "is_sheet_body": is_sheet,
                "is_convergent_body": is_convergent,
                "face_count": face_count,
                "edge_count": edge_count,
                "facet_count": facet_count,
                "vertex_count": vertex_count,
                "bounding_box": _bounding_box(body, body_warnings),
                "warnings": body_warnings,
            }
        )
        warnings.extend(["body %d: %s" % (index, item) for item in body_warnings])

    summary["body_count"] = len(bodies)
    return {"summary": summary, "bodies": bodies, "warnings": warnings}


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "inspect_model":
        raise RuntimeError("Unsupported operation for inspect_model.py: %s" % job.get("operation"))
    input_file = os.path.abspath(str(job.get("input_file") or ""))
    if not input_file or not os.path.exists(input_file):
        raise RuntimeError("Input model does not exist: %s" % input_file)
    return input_file


def _run_job(job, job_path, run_id):
    input_file = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)

    stem = _safe_name(job.get("model_name"), os.path.splitext(os.path.basename(input_file))[0] + "_inspection")
    suffix = os.path.splitext(input_file)[1] or ".prt"
    copied_input = _unique_file(output_dir, stem + "_input_copy", suffix, run_id)
    shutil.copy2(input_file, copied_input)

    session = NXOpen.Session.GetSession()
    work_part, load_status = _open_display_part(session, copied_input)
    if work_part is None:
        raise RuntimeError("NX did not open the copied model: %s" % copied_input)
    try:
        work_part.LoadThisPartFully()
    except Exception:
        pass

    inspection = _inspect_part(work_part)
    load_status_text = ""
    if load_status is not None:
        try:
            load_status_text = str(load_status)
        except Exception:
            load_status_text = "<unavailable>"
        try:
            load_status.Dispose()
        except Exception:
            pass

    return {
        "status": "success",
        "backend": "nx",
        "operation": "inspect_model",
        "message": "NX model inspection completed.",
        "outputs": {
            "source_model": input_file,
            "copied_model": copied_input,
        },
        "inspection": inspection,
        "errors": [],
        "metadata": {
            "job_path": job_path,
            "run_id": run_id,
            "schema_version": job.get("schema_version"),
            "load_status": load_status_text,
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
            "operation": str(job.get("operation") or "inspect_model"),
            "message": "NX model inspection journal failed.",
            "outputs": {},
            "inspection": {},
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
