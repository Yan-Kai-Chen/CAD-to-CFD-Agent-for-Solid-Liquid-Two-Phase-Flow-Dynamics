from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import SolidWorksOperationError
from .paths import project_reports_dir, require_under_workspace, timestamp, unique_path


FLUENT_HANDOFF_SCHEMA_VERSION = "solidworks_fluent_handoff_v1"


TEMPLATE_BOUNDARY_HINTS: dict[str, list[dict[str, str]]] = {
    "external-cylinder-flow": [
        {
            "name": "inlet",
            "location_hint": "negative streamwise end face of the rectangular fluid domain",
            "fluent_action": "Create or select this face in Fluent and assign the inlet boundary type there.",
        },
        {
            "name": "outlet",
            "location_hint": "positive streamwise end face of the rectangular fluid domain",
            "fluent_action": "Create or select this face in Fluent and assign the outlet boundary type there.",
        },
        {
            "name": "obstacle_wall",
            "location_hint": "cylindrical internal cut surface left by the subtracted obstacle",
            "fluent_action": "Create or select this cylindrical surface in Fluent and assign a wall or moving wall as needed.",
        },
        {
            "name": "farfield_or_walls",
            "location_hint": "remaining outer faces of the rectangular domain",
            "fluent_action": "Assign wall, symmetry, pressure far-field, or periodic settings in Fluent according to the case.",
        },
    ],
    "diffuser-transition": [
        {
            "name": "inlet",
            "location_hint": "smaller circular end face unless the flow direction is intentionally reversed",
            "fluent_action": "Create or select the inlet face in Fluent and assign the chosen inlet boundary type.",
        },
        {
            "name": "outlet",
            "location_hint": "larger circular end face unless the flow direction is intentionally reversed",
            "fluent_action": "Create or select the outlet face in Fluent and assign the chosen outlet boundary type.",
        },
        {
            "name": "diffuser_wall",
            "location_hint": "lofted side surface between the two circular end faces",
            "fluent_action": "Create or select the side surface in Fluent and assign wall or interface settings there.",
        },
    ],
    "shell-thicken-wall": [
        {
            "name": "solid_wall_body",
            "location_hint": "shelled and thickened wall volume exported as geometry",
            "fluent_action": "Use Fluent meshing or SpaceClaim/Fluent surface tools to define fluid-solid interface or wall conditions.",
        },
        {
            "name": "open_face",
            "location_hint": "the z+ face was opened by the shell operation before thickening",
            "fluent_action": "Review whether this face should remain open, become a wall, or participate in an interface in Fluent.",
        },
    ],
    "perforated-plate-channel": [
        {
            "name": "plate_wall",
            "location_hint": "front/back and outer plate faces after chamfer",
            "fluent_action": "Assign wall or fluid-solid interface settings in Fluent.",
        },
        {
            "name": "hole_walls",
            "location_hint": "cylindrical through-hole surfaces in the repeated hole grid",
            "fluent_action": "Create or select these repeated surfaces in Fluent if they need a distinct wall/interface group.",
        },
        {
            "name": "upstream_downstream_sides",
            "location_hint": "two broad sides of the plate normal to expected flow",
            "fluent_action": "Define inlet/outlet or internal interface regions in Fluent based on the assembled CFD domain.",
        },
    ],
}


def _load_report(report_path: Path) -> dict[str, Any]:
    report_path = require_under_workspace(report_path)
    if not report_path.exists():
        raise SolidWorksOperationError(f"Report does not exist: {report_path}")
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SolidWorksOperationError(f"Report is not valid JSON: {report_path}: {exc}") from exc


def _source_plan_template(report: dict[str, Any]) -> dict[str, Any]:
    request = report.get("request") or {}
    plan_path = request.get("plan_path")
    if plan_path:
        candidate = require_under_workspace(Path(plan_path))
        if candidate.exists():
            try:
                source_plan = json.loads(candidate.read_text(encoding="utf-8"))
                return source_plan.get("template") or {}
            except json.JSONDecodeError:
                return {}
    return {}


def _template_name(report: dict[str, Any]) -> str:
    template = (report.get("plan") or {}).get("template") or {}
    name = template.get("template_name")
    if name:
        return str(name)

    source_name = _source_plan_template(report).get("template_name")
    if source_name:
        return str(source_name)

    model_name = str((report.get("plan") or {}).get("model_name") or "").lower()
    fallback_by_model_fragment = {
        "external_cylinder_flow": "external-cylinder-flow",
        "diffuser_transition": "diffuser-transition",
        "shell_thicken_wall": "shell-thicken-wall",
        "perforated_plate_channel": "perforated-plate-channel",
    }
    for fragment, fallback_name in fallback_by_model_fragment.items():
        if fragment in model_name:
            return fallback_name
    return "unknown"


def _operation_summaries(report: dict[str, Any]) -> list[dict[str, Any]]:
    operations = (report.get("plan") or {}).get("operations") or []
    summaries = []
    for index, operation in enumerate(operations, start=1):
        summaries.append(
            {
                "index": index,
                "id": operation.get("id"),
                "op": operation.get("op"),
                "args": operation.get("args") or {},
                "rebuild": operation.get("rebuild", True),
            }
        )
    return summaries


def _geometry_files(report: dict[str, Any]) -> dict[str, Any]:
    outputs = report.get("outputs") or {}
    part = outputs.get("part")
    step = outputs.get("step")
    if not step:
        raise SolidWorksOperationError("Source report has no STEP output path.")

    step_path = require_under_workspace(Path(step))
    part_path = require_under_workspace(Path(part)) if part else None
    if not step_path.exists():
        raise SolidWorksOperationError(f"STEP output does not exist: {step_path}")

    return {
        "part": str(part_path) if part_path else None,
        "part_exists": bool(part_path and part_path.exists()),
        "part_size_bytes": part_path.stat().st_size if part_path and part_path.exists() else None,
        "step": str(step_path),
        "step_exists": True,
        "step_size_bytes": step_path.stat().st_size,
    }


def build_fluent_handoff_manifest(report_path: Path) -> dict[str, Any]:
    report_path = require_under_workspace(report_path)
    report = _load_report(report_path)
    if report.get("status") != "success":
        raise SolidWorksOperationError(f"Only successful SolidWorks reports can be handed off. Status: {report.get('status')!r}")

    plan = report.get("plan") or {}
    template_name = _template_name(report)
    source_template = _source_plan_template(report)
    boundary_hints = TEMPLATE_BOUNDARY_HINTS.get(
        template_name,
        [
            {
                "name": "manual_boundary_review",
                "location_hint": "template is unknown to the Phase8 handoff layer",
                "fluent_action": "Import STEP in Fluent and create boundary labels manually from the visible geometry.",
            }
        ],
    )

    return {
        "schema_version": FLUENT_HANDOFF_SCHEMA_VERSION,
        "timestamp": timestamp(),
        "handoff_scope": "geometry_only",
        "source_report": str(report_path),
        "source_status": report.get("status"),
        "solidworks": {
            "plan_schema_version": plan.get("schema_version"),
            "project": plan.get("project"),
            "model_name": plan.get("model_name"),
            "template_name": template_name,
            "template_parameters": (plan.get("template") or {}).get("parameters") or source_template.get("parameters") or {},
            "operations": _operation_summaries(report),
        },
        "geometry_files": _geometry_files(report),
        "units": {
            "plan_length_unit": "mm",
            "solidworks_internal_length_unit": "m",
            "fluent_import_action": "Check STEP import units in Fluent before meshing; template dimensions are specified in millimeters.",
        },
        "boundary_hints": boundary_hints,
        "recommended_fluent_checks": [
            "Import the STEP file and verify model scale before any meshing operation.",
            "Create or verify named selections in Fluent/Fluent Meshing rather than relying on CAD feature names.",
            "Check for unwanted small faces after booleans, chamfers, shell, or thicken operations.",
            "Set boundary types, material zones, interfaces, and mesh controls in Fluent according to the actual simulation case.",
            "Keep the SolidWorks JSON/Markdown report with the Fluent case for geometry traceability.",
        ],
        "non_goals": [
            "No Fluent boundary condition is assigned by this handoff file.",
            "No mesh control is assigned by this handoff file.",
            "No Fluent case or mesh file is generated by this handoff file.",
            "No SolidWorks model is opened or modified by this handoff step.",
        ],
    }


def _markdown_for_manifest(manifest: dict[str, Any]) -> str:
    geometry = manifest["geometry_files"]
    sw = manifest["solidworks"]
    lines = [
        "# SolidWorks To Fluent Handoff",
        "",
        f"Timestamp: `{manifest['timestamp']}`",
        f"Schema: `{manifest['schema_version']}`",
        f"Scope: `{manifest['handoff_scope']}`",
        "",
        "## Geometry",
        "",
        f"- Model: `{sw.get('model_name')}`",
        f"- Template: `{sw.get('template_name')}`",
        f"- STEP: `{geometry['step']}`",
        f"- STEP size: `{geometry['step_size_bytes']}` bytes",
        f"- SLDPRT: `{geometry.get('part')}`",
        "",
        "## Boundary Hints For Fluent",
        "",
    ]
    for hint in manifest["boundary_hints"]:
        lines.extend(
            [
                f"### {hint['name']}",
                "",
                f"- Location hint: {hint['location_hint']}",
                f"- Fluent action: {hint['fluent_action']}",
                "",
            ]
        )

    lines.extend(["## Recommended Fluent Checks", ""])
    lines.extend([f"- [ ] {item}" for item in manifest["recommended_fluent_checks"]])
    lines.append("")

    lines.extend(["## SolidWorks Operations", ""])
    for operation in sw["operations"]:
        lines.append(f"- {operation['index']}. `{operation['op']}` / `{operation['id']}`")
    lines.append("")

    lines.extend(["## Non Goals", ""])
    lines.extend([f"- {item}" for item in manifest["non_goals"]])
    lines.append("")
    return "\n".join(lines)


def write_fluent_handoff_from_report(report_path: Path, *, project: str = "phase8_fluent_handoff") -> dict[str, Any]:
    manifest = build_fluent_handoff_manifest(report_path)
    reports_dir = project_reports_dir(project)
    model_name = str(manifest["solidworks"].get("model_name") or "solidworks_model")
    base = f"solidworks_to_fluent_handoff_{model_name}_{manifest['timestamp']}"
    json_path = unique_path(reports_dir / f"{base}.json")
    md_path = unique_path(reports_dir / f"{base}.md")
    json_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(_markdown_for_manifest(manifest), encoding="utf-8")
    return {
        "status": "success",
        "schema_version": FLUENT_HANDOFF_SCHEMA_VERSION,
        "source_report": str(require_under_workspace(report_path)),
        "template_name": manifest["solidworks"]["template_name"],
        "model_name": manifest["solidworks"]["model_name"],
        "geometry_step": manifest["geometry_files"]["step"],
        "outputs": {
            "json_manifest": str(json_path),
            "markdown_checklist": str(md_path),
        },
    }

