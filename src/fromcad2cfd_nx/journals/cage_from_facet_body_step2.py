"""Controlled NXOpen journal for reverse-modeling Step 2 Cage from Facet Body."""

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
        raise RuntimeError("Missing job JSON path. Use run_journal.exe cage_from_facet_body_step2.py -args <job.json>.")
    return os.path.abspath(values[0])


def _report_dir_for_job(job, job_path):
    output_dir = os.path.abspath(job.get("output_dir") or os.path.dirname(job_path))
    return os.path.join(os.path.dirname(output_dir), "reports")


def _result_markdown(result):
    lines = [
        "# NX Reverse Modeling Step 2 Cage from Facet Body Result",
        "",
        "Status: `%s`" % result.get("status", "failed"),
        "Operation: `%s`" % result.get("operation", "reverse_step2_cage_from_facet_body"),
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
    lines.extend(["", "## Parameters", ""])
    for key, value in sorted((result.get("parameters") or {}).items()):
        lines.append("- `%s`: `%s`" % (key, value))
    lines.extend(["", "## Selected Bodies", ""])
    selected = ((result.get("inspection") or {}).get("selected_bodies") or [])
    if selected:
        for body in selected:
            lines.append(
                "- index `%s`: classification=`%s`, convergent=`%s`, sheet=`%s`, faces=`%s`, facets=`%s`"
                % (
                    body.get("index"),
                    body.get("classification"),
                    body.get("is_convergent_body"),
                    body.get("is_sheet_body"),
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
    lines.extend(["", "## Warnings", ""])
    warnings = ((result.get("metadata") or {}).get("warnings") or [])
    if warnings:
        for warning in warnings:
            lines.append("- %s" % warning)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _write_reports(job, job_path, result, run_id):
    stem = _safe_name(job.get("model_name"), "reverse_step2_cage_from_facet_body")
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


def _subdivision_bodies(work_part):
    try:
        return list(work_part.SubdivisionBodies.ToArray())
    except Exception:
        return []


def _feature_rows(work_part):
    try:
        features = list(work_part.Features.ToArray())
    except Exception:
        try:
            features = [feature for feature in work_part.Features]
        except Exception:
            features = []
    rows = []
    for index, feature in enumerate(features, start=1):
        name = ""
        journal_identifier = ""
        try:
            name = str(feature.Name)
        except Exception:
            pass
        try:
            journal_identifier = str(feature.JournalIdentifier)
        except Exception:
            pass
        rows.append(
            {
                "index": index,
                "name": name,
                "journal_identifier": journal_identifier,
                "type": str(type(feature)),
            }
        )
    return rows


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


def _body_rows(work_part):
    rows = []
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
        rows.append(
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
    return rows, warnings


def _body_summary(rows):
    summary = {
        "body_count": len(rows),
        "solid_body_count": 0,
        "sheet_body_count": 0,
        "convergent_body_count": 0,
        "facet_candidate_count": 0,
        "total_face_count": 0,
        "total_edge_count": 0,
        "total_facet_count": 0,
    }
    for row in rows:
        if row.get("is_solid_body"):
            summary["solid_body_count"] += 1
        if row.get("is_sheet_body"):
            summary["sheet_body_count"] += 1
        if row.get("is_convergent_body"):
            summary["convergent_body_count"] += 1
        if row.get("classification") == "facet":
            summary["facet_candidate_count"] += 1
        if row.get("face_count") is not None:
            summary["total_face_count"] += int(row["face_count"])
        if row.get("edge_count") is not None:
            summary["total_edge_count"] += int(row["edge_count"])
        if row.get("facet_count") is not None:
            summary["total_facet_count"] += int(row["facet_count"])
    return summary


def _select_bodies(work_part, rows, selector):
    bodies = _work_bodies(work_part)
    if selector == "all_bodies":
        selected_indices = list(range(1, len(bodies) + 1))
    else:
        selected_indices = [row["index"] for row in rows if row.get("is_convergent_body")]
    if not selected_indices:
        raise RuntimeError("No bodies matched Step 2 selector `%s`." % selector)
    selected = [bodies[index - 1] for index in selected_indices]
    selected_rows = [row for row in rows if row["index"] in selected_indices]
    return selected, selected_rows


def _set_average_size(builder, average_size_mm):
    average = builder.AverageSize
    text = ("%.12g" % float(average_size_mm)).rstrip(".")
    attempts = []
    try:
        average.Value = float(average_size_mm)
        return "AverageSize.Value"
    except Exception as exc:
        attempts.append("AverageSize.Value: %s: %s" % (type(exc).__name__, exc))
    try:
        average.RightHandSide = text
        return "AverageSize.RightHandSide"
    except Exception as exc:
        attempts.append("AverageSize.RightHandSide: %s: %s" % (type(exc).__name__, exc))
    try:
        average.Value.RightHandSide = text
        return "AverageSize.Value.RightHandSide"
    except Exception as exc:
        attempts.append("AverageSize.Value.RightHandSide: %s: %s" % (type(exc).__name__, exc))
    raise RuntimeError("Could not set CageFromFacetBodyBuilder AverageSize: %s" % "; ".join(attempts))


def _add_body_facet_rules(work_part, builder, selected_bodies):
    factory = work_part.FacetSelectionRuleFactory
    attempts = []
    try:
        rule = factory.CreateRuleBodyFacets(list(selected_bodies))
        builder.FacetRegion.AddRules([rule])
        return {"mode": "single_rule_for_all_bodies", "rule_count": 1}
    except Exception as exc:
        attempts.append("single rule failed: %s: %s" % (type(exc).__name__, exc))
    rules = []
    for body in selected_bodies:
        try:
            rules.append(factory.CreateRuleBodyFacets([body]))
        except Exception as exc:
            attempts.append("per-body rule failed: %s: %s" % (type(exc).__name__, exc))
    if not rules:
        raise RuntimeError("Could not create facet selection rules: %s" % "; ".join(attempts))
    builder.FacetRegion.AddRules(rules)
    return {"mode": "one_rule_per_body", "rule_count": len(rules)}


def _require_nonempty_file(path, label):
    for _index in range(20):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        time.sleep(0.25)
    if not os.path.exists(path):
        raise RuntimeError("%s output did not create the expected file: %s" % (label, path))
    if os.path.getsize(path) <= 0:
        raise RuntimeError("%s output created an empty file: %s" % (label, path))


def _save_part(work_part):
    work_part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)


def _validate_job(job):
    if job.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported job schema: %s" % job.get("schema_version"))
    if job.get("operation") != "reverse_step2_cage_from_facet_body":
        raise RuntimeError("Unsupported operation for cage_from_facet_body_step2.py: %s" % job.get("operation"))
    input_file = os.path.abspath(str(job.get("input_file") or ""))
    if not input_file or not os.path.exists(input_file):
        raise RuntimeError("Input Step 1 PRT does not exist: %s" % input_file)
    if os.path.splitext(input_file)[1].lower() != ".prt":
        raise RuntimeError("Step 2 expects a Step 1 .prt input: %s" % input_file)
    parameters = job.get("parameters") or {}
    average_size = float(parameters.get("average_size_mm", 10.0))
    if average_size <= 0.0:
        raise RuntimeError("average_size_mm must be positive.")
    selector = str(parameters.get("body_selector", "all_convergent"))
    if selector not in ("all_convergent", "all_bodies"):
        raise RuntimeError("Unsupported body_selector: %s" % selector)
    return input_file, {
        "average_size_mm": average_size,
        "body_selector": selector,
        "show_deviation_plot": bool(parameters.get("show_deviation_plot", False)),
    }


def _run_job(job, job_path, run_id):
    input_file, parameters = _validate_job(job)
    output_dir = os.path.abspath(job["output_dir"])
    _ensure_dir(output_dir)

    model_stem = _safe_name(job.get("model_name"), os.path.splitext(os.path.basename(input_file))[0] + "_step2_cage")
    copied_part = _unique_file(output_dir, model_stem + "_input_copy", ".prt", run_id)
    shutil.copy2(input_file, copied_part)

    session = NXOpen.Session.GetSession()
    work_part, load_status = _open_display_part(session, copied_part)
    if work_part is None:
        raise RuntimeError("NX did not open copied Step 1 PRT: %s" % copied_part)
    try:
        work_part.LoadThisPartFully()
    except Exception:
        pass

    pre_rows, pre_warnings = _body_rows(work_part)
    selected_bodies, selected_rows = _select_bodies(work_part, pre_rows, parameters["body_selector"])
    pre_subdivision_count = len(_subdivision_bodies(work_part))
    pre_feature_rows = _feature_rows(work_part)

    task_environment = session.SubdivisionTaskEnvironment
    entered = False
    committed = None
    builder_debug = {}
    try:
        task_environment.Enter()
        entered = True
        builder = work_part.SubdivisionBodies.CreateCageFromFacetBodyBuilder()
        try:
            builder_debug["average_size_setter"] = _set_average_size(builder, parameters["average_size_mm"])
            if parameters["show_deviation_plot"]:
                builder.ShowDeviationPlot = True
            builder_debug["facet_rules"] = _add_body_facet_rules(work_part, builder, selected_bodies)
            mark_id = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "FromCAD2CFD reverse step2 cage from facet body")
            try:
                committed = builder.Commit()
                update_errors = session.UpdateManager.DoUpdate(mark_id)
                try:
                    active_before_exit = task_environment.ActiveSubdivisionBodyFeature
                    builder_debug["active_feature_before_exit_type"] = str(type(active_before_exit))
                    builder_debug["active_feature_before_exit_is_none"] = active_before_exit is None
                except Exception as exc:
                    builder_debug["active_feature_before_exit_error"] = "%s: %s" % (type(exc).__name__, exc)
            finally:
                session.DeleteUndoMark(mark_id, "FromCAD2CFD reverse step2 cage from facet body")
            if update_errors not in (None, 0):
                raise RuntimeError("NX update failed after Cage from Facet Body: %s" % update_errors)
        finally:
            try:
                builder.Destroy()
            except Exception:
                pass
        task_environment.Exit()
        entered = False
    except Exception:
        if entered:
            try:
                task_environment.SetCancelled()
            except Exception:
                pass
            try:
                task_environment.Exit()
            except Exception:
                pass
        raise

    post_rows, post_warnings = _body_rows(work_part)
    post_subdivision_count = len(_subdivision_bodies(work_part))
    post_feature_rows = _feature_rows(work_part)
    active_feature_type = None
    try:
        active_feature_type = str(type(task_environment.ActiveSubdivisionBodyFeature))
    except Exception:
        active_feature_type = None

    warnings = []
    if post_subdivision_count <= pre_subdivision_count:
        warnings.append("SubdivisionBodies.ToArray did not show a new subdivision body; NX may store the committed cage outside this collection in journal mode.")
    if len(post_feature_rows) <= len(pre_feature_rows):
        warnings.append("Feature count did not increase after Cage from Facet Body; inspect the saved PRT visually before treating the cage as final.")

    validation = {
        "commit_completed": True,
        "committed_is_none": committed is None,
        "committed_type": str(type(committed)),
        "pre_body_count": len(pre_rows),
        "selected_body_count": len(selected_rows),
        "selected_total_facet_count": sum([int(row.get("facet_count") or 0) for row in selected_rows]),
        "pre_subdivision_body_count": pre_subdivision_count,
        "post_subdivision_body_count": post_subdivision_count,
        "subdivision_body_count_delta": post_subdivision_count - pre_subdivision_count,
        "pre_feature_count": len(pre_feature_rows),
        "post_feature_count": len(post_feature_rows),
        "feature_count_delta": len(post_feature_rows) - len(pre_feature_rows),
        "average_size_mm": parameters["average_size_mm"],
        "prt_exists_nonempty": os.path.exists(copied_part) and os.path.getsize(copied_part) > 0,
    }

    _save_part(work_part)
    _require_nonempty_file(copied_part, "NX Step 2 PRT")
    if load_status is not None:
        try:
            load_status.Dispose()
        except Exception:
            pass

    return {
        "status": "success",
        "backend": "nx",
        "operation": "reverse_step2_cage_from_facet_body",
        "message": "NX reverse-modeling Step 2 created a subdivision cage from selected facet/convergent bodies.",
        "outputs": {
            "source_prt": input_file,
            "copied_part": copied_part,
            "part": copied_part,
        },
        "inspection": {
            "pre_summary": _body_summary(pre_rows),
            "post_summary": _body_summary(post_rows),
            "selected_bodies": selected_rows,
            "pre_features": pre_feature_rows,
            "post_features": post_feature_rows,
            "pre_warnings": pre_warnings,
            "post_warnings": post_warnings,
        },
        "validation": validation,
        "parameters": parameters,
        "errors": [],
        "metadata": {
            "job_path": job_path,
            "run_id": run_id,
            "schema_version": job.get("schema_version"),
            "builder_debug": builder_debug,
            "commit_type": str(type(committed)),
            "active_subdivision_body_feature_type": active_feature_type,
            "requires_nx_version": "NX1926_or_newer",
            "requires_license": "nx_subdivision",
            "original_source_file": (job.get("metadata") or {}).get("original_source_file"),
            "warnings": warnings,
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
            "operation": str(job.get("operation") or "reverse_step2_cage_from_facet_body"),
            "message": "NX reverse-modeling Step 2 Cage from Facet Body journal failed.",
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
