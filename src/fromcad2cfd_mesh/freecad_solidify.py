"""FreeCAD-backed coarse mesh solidification workflow."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .job_schema import MeshJob, read_mesh_job
from .paths import project_input_dir, project_output_dir, project_reports_dir, timestamp, unique_path
from .stl import inspect_stl


OPERATION = "solidify_mesh_freecad"


@dataclass(frozen=True)
class FreeCADPreflight:
    """FreeCADCmd availability report."""

    status: str
    freecadcmd: str | None
    message: str

    def to_dict(self) -> dict[str, str | None]:
        return {"status": self.status, "freecadcmd": self.freecadcmd, "message": self.message}


def _candidate_freecadcmd(explicit: str | None = None) -> list[Path]:
    candidates: list[Path] = []
    for value in (explicit, os.environ.get("FREECADCMD_EXE")):
        if value:
            candidates.append(Path(value))
    found = shutil.which("FreeCADCmd") or shutil.which("freecadcmd") or shutil.which("FreeCADCmd.exe")
    if found:
        candidates.append(Path(found))
    candidates.extend(
        [
            Path(r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe"),
            Path(r"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe"),
            Path(r"C:\Program Files\FreeCAD 0.20\bin\FreeCADCmd.exe"),
        ]
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def freecad_preflight(freecadcmd: str | None = None) -> FreeCADPreflight:
    """Locate FreeCADCmd without launching CAD."""

    for candidate in _candidate_freecadcmd(freecadcmd):
        if candidate.exists() and candidate.is_file():
            return FreeCADPreflight(status="success", freecadcmd=str(candidate), message="FreeCADCmd found.")
    return FreeCADPreflight(
        status="missing",
        freecadcmd=None,
        message="FreeCADCmd was not found. Set FREECADCMD_EXE or pass --freecadcmd to execute solidification.",
    )


def solidify_freecad_job(
    input_file: str | Path,
    output_dir: str | Path,
    *,
    model_name: str | None = None,
    sew_tolerance_mm: float = 0.05,
    refine_shape: bool = True,
    save_fcstd: bool = True,
    export_step: bool = True,
) -> MeshJob:
    """Create a coarse mesh-to-solid job consumed by FreeCADCmd."""

    source = Path(input_file)
    if not source.exists():
        raise FileNotFoundError(f"Input STL does not exist: {source}")
    if source.suffix.lower() != ".stl":
        raise ValueError("solidify_mesh_freecad currently accepts STL input only.")
    if float(sew_tolerance_mm) <= 0.0:
        raise ValueError("sew_tolerance_mm must be positive.")
    inspection = inspect_stl(source)
    return MeshJob(
        operation=OPERATION,
        input_file=str(source),
        output_dir=str(output_dir),
        model_name=model_name or f"{source.stem}_solid_candidate",
        parameters={
            "sew_tolerance_mm": float(sew_tolerance_mm),
            "refine_shape": bool(refine_shape),
            "save_fcstd": bool(save_fcstd),
            "export_step": bool(export_step),
        },
        metadata={
            "operation_family": "reverse_modeling",
            "route": "freecad_opencascade_mesh_to_solid",
            "input_summary": inspection.to_dict(),
            "acceptance": "coarse solid candidate exported as STEP; not an analytic or parametric reconstruction",
            "boundary": "Output may remain faceted and heavy; use only as a CFD preprocessing solid candidate.",
        },
    )


def write_solidify_freecad_job(
    input_file: str | Path,
    *,
    project: str = "mesh_solidify_freecad",
    model_name: str | None = None,
    sew_tolerance_mm: float = 0.05,
    refine_shape: bool = True,
    save_fcstd: bool = True,
    export_step: bool = True,
) -> dict[str, Any]:
    """Copy STL input to project runtime and write a solidification job."""

    source = Path(input_file)
    if not source.exists():
        raise FileNotFoundError(f"Input STL does not exist: {source}")
    copied_input = unique_path(project_input_dir(project) / source.name)
    shutil.copy2(source, copied_input)
    job = solidify_freecad_job(
        copied_input,
        output_dir=project_output_dir(project),
        model_name=model_name,
        sew_tolerance_mm=sew_tolerance_mm,
        refine_shape=refine_shape,
        save_fcstd=save_fcstd,
        export_step=export_step,
    )
    job.metadata["original_source_file"] = str(source)
    job.metadata["copied_input_file"] = str(copied_input)
    job_path = unique_path(project_input_dir(project) / f"{job.model_name}_job.json")
    job.write(job_path)
    return {"status": "success", "job_path": str(job_path), "job": job.to_dict()}


def _report_paths(job: MeshJob, result: dict[str, Any], reports_dir: Path | None = None) -> tuple[Path, Path]:
    report_dir = reports_dir or Path(job.output_dir).parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    run_id = result.get("run_id") or timestamp()
    json_path = unique_path(report_dir / f"solidify_{run_id}.json")
    md_path = json_path.with_suffix(".md")
    return json_path, md_path


def _write_reports(job: MeshJob, result: dict[str, Any], reports_dir: Path | None = None) -> dict[str, str]:
    json_path, md_path = _report_paths(job, result, reports_dir)
    result = dict(result)
    result["report_json"] = str(json_path)
    result["report_markdown"] = str(md_path)
    json_path.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")

    input_summary = job.metadata.get("input_summary") or {}
    lines = [
        "# Mesh Solidify FreeCAD Result",
        "",
        f"Status: `{result.get('status')}`",
        f"Operation: `{job.operation}`",
        f"Model: `{job.model_name}`",
        f"Message: {result.get('message', '')}",
        "",
        "## Input",
        "",
        f"- Copied input: `{job.input_file}`",
        f"- Original input: `{job.metadata.get('original_source_file', '')}`",
        f"- Triangle count: `{input_summary.get('triangle_count')}`",
        f"- Probably watertight: `{input_summary.get('is_probably_watertight')}`",
        "",
        "## Outputs",
        "",
    ]
    outputs = result.get("outputs") or {}
    if outputs:
        lines.extend(f"- {key}: `{value}`" for key, value in outputs.items())
    else:
        lines.append("- No geometry output produced.")
    solid = result.get("solid") or {}
    if solid:
        lines.extend(
            [
                "",
                "## Solid Check",
                "",
                f"- Valid: `{solid.get('is_valid')}`",
                f"- Solid count: `{solid.get('solid_count')}`",
                f"- Shell count: `{solid.get('shell_count')}`",
                f"- Face count: `{solid.get('face_count')}`",
                f"- Edge count: `{solid.get('edge_count')}`",
                f"- Volume: `{solid.get('volume')}`",
            ]
        )
    lines.extend(["", "## Boundary", "", "- This is a coarse solid candidate, not a parametric or analytic CAD reconstruction."])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _script_path() -> Path:
    return Path(__file__).resolve().parent / "freecad_scripts" / "solidify_mesh_to_step.py"


def _candidate_freecad_python(freecadcmd: str) -> Path | None:
    """Return the Python interpreter bundled with a FreeCAD installation."""

    command_path = Path(freecadcmd).resolve()
    candidates = [
        command_path.parent / "python.exe",
        command_path.parent / "bin" / "python.exe",
        command_path.parent.parent / "bin" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _execution_command(freecadcmd: str, script_path: Path, job_path: Path, result_path: Path) -> tuple[list[str], dict[str, str], str]:
    """Build a stable headless FreeCAD execution command."""

    freecad_python = _candidate_freecad_python(freecadcmd)
    env = os.environ.copy()
    if freecad_python:
        python_dir = str(freecad_python.parent)
        env["PATH"] = python_dir + os.pathsep + env.get("PATH", "")
        return [str(freecad_python), str(script_path), str(job_path), str(result_path)], env, "bundled_python"
    return [freecadcmd, str(script_path), "--pass", str(job_path), str(result_path)], env, "freecadcmd_pass"


def run_freecad_solidify_job(
    job_path: str | Path,
    *,
    freecadcmd: str | None = None,
    timeout_sec: int = 3600,
) -> dict[str, Any]:
    """Run a solidification job through FreeCADCmd when available."""

    job = read_mesh_job(job_path)
    if job.operation != OPERATION:
        raise ValueError(f"Unsupported mesh operation: {job.operation}")
    preflight = freecad_preflight(freecadcmd)
    run_id = timestamp()
    if preflight.status != "success" or not preflight.freecadcmd:
        result = {
            "status": "blocked",
            "operation": job.operation,
            "run_id": run_id,
            "message": preflight.message,
            "job_path": str(job_path),
            "outputs": {},
            "preflight": preflight.to_dict(),
        }
        result["reports"] = _write_reports(job, result)
        return result

    result_path = unique_path(Path(job.output_dir).parent / "reports" / f"{job.model_name}_freecad_raw_{run_id}.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    command, env, execution_mode = _execution_command(preflight.freecadcmd, _script_path(), Path(job_path), result_path)
    completed = subprocess.run(command, env=env, capture_output=True, text=True, timeout=timeout_sec, check=False)
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8"))
    else:
        result = {
            "status": "failed",
            "operation": job.operation,
            "message": "FreeCADCmd did not write a result JSON file.",
            "outputs": {},
        }
    result.update(
        {
            "run_id": run_id,
            "job_path": str(job_path),
            "freecadcmd": preflight.freecadcmd,
            "execution_mode": execution_mode,
            "execution_command": command,
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }
    )
    if completed.returncode != 0 and result.get("status") == "success":
        result["status"] = "failed"
        result["message"] = "FreeCADCmd returned a non-zero exit code after writing a success payload."
    result["reports"] = _write_reports(job, result)
    return result
