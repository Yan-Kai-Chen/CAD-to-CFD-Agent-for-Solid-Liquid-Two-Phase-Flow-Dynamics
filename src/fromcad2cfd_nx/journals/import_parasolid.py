"""Controlled NXOpen journal for importing Parasolid into a new NX PRT."""

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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe import_parasolid.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Parasolid Import Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "import_parasolid"),
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
    stem = _safe_name(job.get("model_name"), "nx_import_parasolid")
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


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "import_parasolid":
        raise RuntimeError("Unsupported operation for import_parasolid.py: %s" % job.get("operation"))
    input_file = os.path.abspath(str(job.get("input_file") or ""))
    if not input_file or not os.path.exists(input_file):
        raise RuntimeError("Input Parasolid file does not exist: %s" % input_file)
    if os.path.splitext(input_file)[1].lower() not in (".x_t", ".x_b"):
        raise RuntimeError("import_parasolid supports Parasolid .x_t and .x_b inputs only.")
    return input_file


def _run_job(job, job_path, run_id):
    input_file = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)
    model_stem = _safe_name(job.get("model_name"), os.path.splitext(os.path.basename(input_file))[0] + "_imported")
    part_path = _unique_file(output_dir, model_stem, ".prt", run_id)

    session = NXOpen.Session.GetSession()
    work_part = _new_part(session, part_path)
    if work_part is None:
        raise RuntimeError("NX did not create an import work part.")

    importer = work_part.ImportManager.CreateParasolidImporter()
    try:
        importer.FileName = input_file
        importer.Commit()
    finally:
        if hasattr(importer, "Destroy"):
            try:
                importer.Destroy()
            except Exception:
                pass

    _save_part(work_part)
    _require_nonempty_file(part_path, "Imported PRT")
    body_summary = _body_summary(work_part)
    imported_body_count = len(body_summary)
    solid_body_count = len([row for row in body_summary if row.get("is_solid_body")])
    if imported_body_count < 1:
        raise RuntimeError("Parasolid import did not create any bodies.")
    parasolid = _export_parasolid(work_part, output_dir, model_stem, run_id)

    return {
        "status": "success",
        "backend": "nx",
        "operation": "import_parasolid",
        "message": "Parasolid was imported into a controlled NX PRT.",
        "outputs": {"source_parasolid": input_file, "part": part_path, "parasolid": parasolid},
        "inspection": {"bodies": body_summary},
        "validation": {"imported_body_count": imported_body_count, "solid_body_count": solid_body_count},
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
            "operation": str(job.get("operation") or "import_parasolid"),
            "message": "NX Parasolid import journal failed.",
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
