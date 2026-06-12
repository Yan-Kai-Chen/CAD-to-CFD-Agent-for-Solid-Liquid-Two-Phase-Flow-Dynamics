"""Controlled NXOpen journal for reverse-modeling Step 1 STL import."""

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
import NXOpen.Facet
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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe import_stl_convergent_step1.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Reverse Modeling Step 1 STL Import Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "reverse_step1_import_stl_convergent"),
        "Message: %s" % result.get("message", ""),
        "",
        "## Outputs",
        "",
    ]
    outputs = result.get("outputs") or {}
    for key in sorted(outputs):
        lines.append("- `%s`: `%s`" % (key, outputs[key]))
    if not outputs:
        lines.append("- None")
    lines.extend(["", "## Validation", ""])
    for key, value in sorted((result.get("validation") or {}).items()):
        lines.append("- `%s`: `%s`" % (key, value))
    lines.extend(["", "## Import Settings", ""])
    for key, value in sorted((result.get("parameters") or {}).items()):
        lines.append("- `%s`: `%s`" % (key, value))
    lines.extend(["", "## Bodies", ""])
    bodies = ((result.get("inspection") or {}).get("bodies") or [])
    if bodies:
        for body in bodies:
            lines.append(
                "- index `%s`: classification=`%s`, solid=`%s`, sheet=`%s`, convergent=`%s`, faces=`%s`, facets=`%s`"
                % (
                    body.get("index"),
                    body.get("classification"),
                    body.get("is_solid_body"),
                    body.get("is_sheet_body"),
                    body.get("is_convergent_body"),
                    body.get("face_count"),
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
    stem = _safe_name(job.get("model_name"), "reverse_step1_import_stl_convergent")
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
        box = NXOpen.UF.UFSession.GetUFSession().Sf.BodyAskBoundingBox(body.Tag)
        return [float(value) for value in list(box)]
    except Exception as exc:
        warnings.append("AskBoundingBox failed: %s: %s" % (type(exc).__name__, exc))
        return None


def _classify_body(is_solid, is_sheet, is_convergent, facet_count, face_count):
    if is_convergent:
        return "convergent_solid" if is_solid else "convergent"
    if is_solid:
        return "solid"
    if is_sheet:
        return "sheet"
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
        "total_face_count": 0,
        "total_edge_count": 0,
        "total_facet_count": 0,
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
        if is_solid:
            summary["solid_body_count"] += 1
        if is_sheet:
            summary["sheet_body_count"] += 1
        if is_convergent:
            summary["convergent_body_count"] += 1
        if classification == "facet":
            summary["facet_candidate_count"] += 1
        if face_count is not None:
            summary["total_face_count"] += int(face_count)
        if edge_count is not None:
            summary["total_edge_count"] += int(edge_count)
        if facet_count is not None:
            summary["total_facet_count"] += int(facet_count)
        bodies.append(
            {
                "index": index,
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


def _require_nonempty_file(path, label):
    for _index in range(20):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        time.sleep(0.25)
    raise RuntimeError("%s output was missing or empty: %s" % (label, path))


def _try_export_parasolid(work_part, output_dir, model_stem, run_id):
    path = _unique_file(output_dir, model_stem, ".x_t", run_id)
    bodies = _work_bodies(work_part)
    if not bodies:
        return {"status": "skipped", "path": None, "message": "No bodies available for Parasolid export."}
    try:
        NXOpen.UF.UFSession.GetUFSession().Ps.ExportData([body.Tag for body in bodies], path)
        _require_nonempty_file(path, "Parasolid")
        return {"status": "success", "path": path, "message": "Parasolid export completed."}
    except Exception as exc:
        return {"status": "failed", "path": path, "message": "%s: %s" % (type(exc).__name__, exc)}


def _save_part(work_part):
    work_part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)


def _file_units_enum(value):
    mapping = {
        "Millimeters": NXOpen.Facet.STLImportBuilder.STLFileUnitsTypes.Millimeters,
        "Meters": NXOpen.Facet.STLImportBuilder.STLFileUnitsTypes.Meters,
        "Inches": NXOpen.Facet.STLImportBuilder.STLFileUnitsTypes.Inches,
    }
    if value not in mapping:
        raise RuntimeError("Unsupported STL file units: %s" % value)
    return mapping[value]


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "reverse_step1_import_stl_convergent":
        raise RuntimeError("Unsupported operation for import_stl_convergent_step1.py: %s" % job.get("operation"))
    input_file = os.path.abspath(str(job.get("input_file") or ""))
    if not input_file or not os.path.exists(input_file):
        raise RuntimeError("Input STL does not exist: %s" % input_file)
    if os.path.splitext(input_file)[1].lower() != ".stl":
        raise RuntimeError("Input file must be .stl: %s" % input_file)
    parameters = job.get("parameters") or {}
    minimum_angle = float(parameters.get("minimum_angle_folded_facets_deg", 15.0))
    minimum_facets = int(parameters.get("minimum_facet_number", 100))
    if minimum_angle <= 0.0:
        raise RuntimeError("minimum_angle_folded_facets_deg must be positive.")
    if minimum_facets < 1:
        raise RuntimeError("minimum_facet_number must be positive.")
    return input_file, {
        "facet_body_output_type": "Convergent",
        "nx_facet_body_type": "Psm",
        "cleanup": bool(parameters.get("cleanup", True)),
        "minimum_angle_folded_facets_deg": minimum_angle,
        "minimum_facet_number": minimum_facets,
        "stl_file_units": str(parameters.get("stl_file_units", "Millimeters")),
        "show_information_window": bool(parameters.get("show_information_window", False)),
    }


def _run_job(job, job_path, run_id):
    input_file, parameters = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)
    model_stem = _safe_name(job.get("model_name"), os.path.splitext(os.path.basename(input_file))[0] + "_step1_convergent")
    part_path = _unique_file(output_dir, model_stem, ".prt", run_id)

    session = NXOpen.Session.GetSession()
    work_part = _new_part(session, part_path)
    if work_part is None:
        raise RuntimeError("NX did not create a work part.")

    builder = work_part.FacetedBodies.CreateSTLImportBuilder()
    try:
        builder.File = input_file
        builder.FacetBodyType = NXOpen.Facet.STLImportBuilder.FacetBodyTypes.Psm
        builder.CleanUp = parameters["cleanup"]
        builder.MinimumAngleFoldedFacets = parameters["minimum_angle_folded_facets_deg"]
        builder.MinimumFacetNumber = parameters["minimum_facet_number"]
        builder.STLFileUnits = _file_units_enum(parameters["stl_file_units"])
        builder.ShowInformationWindow = parameters["show_information_window"]
        committed = builder.Commit()
    finally:
        try:
            builder.Destroy()
        except Exception:
            pass

    mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "FromCAD2CFD reverse step1 import update")
    update_errors = session.UpdateManager.DoUpdate(mark_id)
    try:
        session.DeleteUndoMark(mark_id, "FromCAD2CFD reverse step1 import update")
    except Exception:
        pass
    if update_errors not in (None, 0):
        raise RuntimeError("NX update failed after STL import: %s" % update_errors)

    _save_part(work_part)
    _require_nonempty_file(part_path, "NX PRT")
    inspection = _inspect_part(work_part)
    summary = inspection["summary"]
    if summary["body_count"] < 1:
        raise RuntimeError("STL import produced no bodies.")
    if summary["convergent_body_count"] < 1:
        raise RuntimeError("STL import did not produce a convergent body: %s" % summary)

    parasolid = _try_export_parasolid(work_part, output_dir, model_stem, run_id)
    outputs = {
        "source_stl": input_file,
        "part": part_path,
    }
    if parasolid.get("status") == "success":
        outputs["parasolid"] = parasolid["path"]

    return {
        "status": "success",
        "backend": "nx",
        "operation": "reverse_step1_import_stl_convergent",
        "message": "NX reverse-modeling Step 1 imported the STL as a cleaned convergent body.",
        "outputs": outputs,
        "inspection": inspection,
        "validation": {
            "body_count": summary["body_count"],
            "solid_body_count": summary["solid_body_count"],
            "sheet_body_count": summary["sheet_body_count"],
            "convergent_body_count": summary["convergent_body_count"],
            "total_facet_count": summary["total_facet_count"],
            "prt_exists_nonempty": os.path.exists(part_path) and os.path.getsize(part_path) > 0,
            "parasolid_export_status": parasolid.get("status"),
            "parasolid_export_message": parasolid.get("message"),
        },
        "parameters": parameters,
        "errors": [],
        "metadata": {
            "job_path": job_path,
            "run_id": run_id,
            "schema_version": job.get("schema_version"),
            "commit_type": str(type(committed)),
            "original_source_file": (job.get("metadata") or {}).get("original_source_file"),
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
            "operation": str(job.get("operation") or "reverse_step1_import_stl_convergent"),
            "message": "NX reverse-modeling Step 1 STL import journal failed.",
            "outputs": {},
            "inspection": {},
            "validation": {},
            "parameters": (job.get("parameters") or {}),
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
