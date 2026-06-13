"""FreeCAD Python script for coarse STL mesh to STEP solid conversion.

This script is executed inside FreeCAD's Python runtime:

    <FreeCAD bundle>\\bin\\python.exe solidify_mesh_to_step.py <job.json> <result.json>
"""

from __future__ import annotations

from datetime import datetime
import json
import os
import re
import sys
import traceback


def _safe_name(value, fallback):
    text = str(value or fallback)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._")
    return text or fallback


def _write_json(path, payload):
    folder = os.path.dirname(os.path.abspath(path))
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)


def _main(argv):
    if len(argv) < 3:
        raise RuntimeError("Usage: FreeCAD Python solidify_mesh_to_step.py <job.json> <result.json>")
    job_path = os.path.abspath(argv[1])
    result_path = os.path.abspath(argv[2])
    with open(job_path, "r", encoding="utf-8") as handle:
        job = json.load(handle)

    import FreeCAD as App
    import Mesh
    import Part
    import Import

    if job.get("operation") != "solidify_mesh_freecad":
        raise RuntimeError("Unsupported operation: %s" % job.get("operation"))

    input_file = os.path.abspath(str(job.get("input_file") or ""))
    if not os.path.exists(input_file):
        raise RuntimeError("Input file does not exist: %s" % input_file)

    output_dir = os.path.abspath(str(job.get("output_dir") or os.getcwd()))
    os.makedirs(output_dir, exist_ok=True)
    params = job.get("parameters") or {}
    tolerance = float(params.get("sew_tolerance_mm", 0.05))
    refine_shape = bool(params.get("refine_shape", True))
    save_fcstd = bool(params.get("save_fcstd", True))
    export_step = bool(params.get("export_step", True))
    model_name = _safe_name(job.get("model_name"), "mesh_solid_candidate")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    doc = App.newDocument(model_name)
    mesh = Mesh.Mesh(input_file)
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, tolerance)
    if refine_shape and hasattr(shape, "removeSplitter"):
        shape = shape.removeSplitter()
    solid = Part.makeSolid(shape)
    if refine_shape and hasattr(solid, "removeSplitter"):
        solid = solid.removeSplitter()

    obj = doc.addObject("Part::Feature", model_name)
    obj.Shape = solid
    doc.recompute()

    step_path = os.path.join(output_dir, "%s_%s.step" % (model_name, run_id))
    fcstd_path = os.path.join(output_dir, "%s_%s.FCStd" % (model_name, run_id))
    outputs = {}
    if export_step:
        Import.export([obj], step_path)
        outputs["step"] = step_path
    if save_fcstd:
        doc.saveAs(fcstd_path)
        outputs["fcstd"] = fcstd_path

    result = {
        "status": "success",
        "operation": "solidify_mesh_freecad",
        "message": "FreeCAD mesh-to-solid conversion completed.",
        "job_path": job_path,
        "input_file": input_file,
        "model_name": model_name,
        "outputs": outputs,
        "solid": {
            "is_valid": bool(solid.isValid()),
            "volume": float(getattr(solid, "Volume", 0.0)),
            "shell_count": len(getattr(solid, "Shells", [])),
            "solid_count": len(getattr(solid, "Solids", [])) or 1,
            "face_count": len(getattr(solid, "Faces", [])),
            "edge_count": len(getattr(solid, "Edges", [])),
        },
        "parameters": params,
    }
    _write_json(result_path, result)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main(sys.argv))
    except Exception as exc:
        result_path = os.path.abspath(sys.argv[2]) if len(sys.argv) >= 3 else os.path.abspath("freecad_solidify_failed.json")
        payload = {
            "status": "failed",
            "operation": "solidify_mesh_freecad",
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        _write_json(result_path, payload)
        print(json.dumps(payload, ensure_ascii=True))
        raise
