from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import SolidWorksOperationError
from .paths import project_output_dir, require_under_workspace, unique_path
from .plan_executor import PLAN_SCHEMA_VERSION, safe_slug, validate_plan


CFD_TEMPLATE_VERSION = "fromcad2cfd_solidworks_cfd_templates_v1"


def _float_param(params: dict[str, Any], key: str, default: float) -> float:
    value = params.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SolidWorksOperationError(f"Template parameter {key!r} must be numeric; got {value!r}") from exc


def _int_param(params: dict[str, Any], key: str, default: int) -> int:
    value = params.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise SolidWorksOperationError(f"Template parameter {key!r} must be an integer; got {value!r}") from exc


def _base_plan(project: str, model_name: str, description: str) -> dict[str, Any]:
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "project": project,
        "model_name": safe_slug(model_name),
        "description": description,
        "document": {
            "type": "part",
            "save_part": True,
            "export_step": True,
            "close_document": True,
        },
        "execution": {
            "stop_on_error": True,
            "visible": False,
        },
        "operations": [],
    }


def _external_cylinder_flow(project: str, model_name: str, params: dict[str, Any]) -> dict[str, Any]:
    length = _float_param(params, "domain_length_mm", 100.0)
    height = _float_param(params, "domain_height_mm", 42.0)
    depth = _float_param(params, "domain_depth_mm", 20.0)
    radius = _float_param(params, "obstacle_radius_mm", 6.0)
    obstacle_x = _float_param(params, "obstacle_center_x_mm", 0.0)
    obstacle_y = _float_param(params, "obstacle_center_y_mm", 0.0)
    plan = _base_plan(project, model_name, "CFD template: external flow domain with cylindrical obstacle subtracted.")
    plan["operations"] = [
        {
            "id": "fluid_domain_box",
            "op": "create_rectangular_prism",
            "args": {"width_mm": length, "height_mm": height, "depth_mm": depth, "merge_result": True},
        },
        {
            "id": "cylindrical_obstacle_tool",
            "op": "create_circular_boss",
            "args": {
                "radius_mm": radius,
                "depth_mm": depth + 4.0,
                "center_x_mm": obstacle_x,
                "center_y_mm": obstacle_y,
                "merge_result": False,
            },
        },
        {
            "id": "subtract_obstacle_from_domain",
            "op": "combine_bodies",
            "args": {"operation": "subtract", "main_body_index": 1, "tool_body_indices": [0]},
        },
        {
            "id": "flow_axis",
            "op": "create_reference_axis_from_planes",
            "args": {"plane_a": "Front", "plane_b": "Right"},
        },
        {
            "id": "analysis_coordinate_system",
            "op": "create_coordinate_system",
            "args": {"location_mm": [0, 0, 0], "rotation_deg": [0, 0, 0]},
        },
    ]
    return plan


def _diffuser_transition(project: str, model_name: str, params: dict[str, Any]) -> dict[str, Any]:
    inlet_radius = _float_param(params, "inlet_radius_mm", 5.0)
    outlet_radius = _float_param(params, "outlet_radius_mm", 12.0)
    length = _float_param(params, "length_mm", 45.0)
    plan = _base_plan(project, model_name, "CFD template: lofted diffuser or contraction fluid volume.")
    plan["operations"] = [
        {
            "id": "lofted_fluid_volume",
            "op": "create_loft_between_circles",
            "args": {"radius1_mm": inlet_radius, "radius2_mm": outlet_radius, "distance_mm": length},
        },
        {
            "id": "center_axis",
            "op": "create_reference_axis_from_planes",
            "args": {"plane_a": "Front", "plane_b": "Right"},
        },
        {
            "id": "analysis_coordinate_system",
            "op": "create_coordinate_system",
            "args": {"location_mm": [0, 0, 0], "rotation_deg": [0, 0, 0]},
        },
    ]
    return plan


def _shell_thicken_wall(project: str, model_name: str, params: dict[str, Any]) -> dict[str, Any]:
    width = _float_param(params, "width_mm", 42.0)
    height = _float_param(params, "height_mm", 30.0)
    depth = _float_param(params, "depth_mm", 20.0)
    shell = _float_param(params, "shell_thickness_mm", 1.6)
    thicken = _float_param(params, "thicken_mm", 2.0)
    plan = _base_plan(project, model_name, "CFD template: shell and thicken workflow for reusable wall geometry.")
    plan["operations"] = [
        {
            "id": "solid_wall_seed",
            "op": "create_rectangular_prism",
            "args": {"width_mm": width, "height_mm": height, "depth_mm": depth, "merge_result": True},
        },
        {
            "id": "open_top_shell",
            "op": "apply_shell",
            "args": {"thickness_mm": shell, "open_face_axis": "z+", "outward": False},
        },
        {
            "id": "thicken_top_face",
            "op": "thicken_selected_face",
            "args": {"thickness_mm": thicken, "face_axis": "z+", "merge_result": True},
        },
    ]
    return plan


def _perforated_plate_channel(project: str, model_name: str, params: dict[str, Any]) -> dict[str, Any]:
    width = _float_param(params, "width_mm", 72.0)
    height = _float_param(params, "height_mm", 36.0)
    depth = _float_param(params, "depth_mm", 8.0)
    radius = _float_param(params, "hole_radius_mm", 2.0)
    columns = _int_param(params, "columns", 4)
    rows = _int_param(params, "rows", 2)
    spacing_x = _float_param(params, "spacing_x_mm", 16.0)
    spacing_y = _float_param(params, "spacing_y_mm", 12.0)
    if columns < 1 or rows < 1:
        raise SolidWorksOperationError("Perforated plate rows and columns must be >= 1.")
    centers = []
    x0 = -spacing_x * (columns - 1) / 2.0
    y0 = -spacing_y * (rows - 1) / 2.0
    for row in range(rows):
        for col in range(columns):
            centers.append([x0 + col * spacing_x, y0 + row * spacing_y])
    plan = _base_plan(project, model_name, "CFD template: perforated plate or baffle with repeated through holes.")
    plan["operations"] = [
        {
            "id": "plate_body",
            "op": "create_rectangular_prism",
            "args": {"width_mm": width, "height_mm": height, "depth_mm": depth, "merge_result": True},
        },
        {
            "id": "hole_array",
            "op": "cut_hole_grid",
            "args": {"radius_mm": radius, "centers_mm": centers, "through_all": True},
        },
        {
            "id": "edge_chamfer",
            "op": "apply_all_edge_chamfer",
            "args": {"distance_mm": 0.5, "angle_deg": 45.0},
        },
    ]
    return plan


TEMPLATE_BUILDERS = {
    "external-cylinder-flow": _external_cylinder_flow,
    "diffuser-transition": _diffuser_transition,
    "shell-thicken-wall": _shell_thicken_wall,
    "perforated-plate-channel": _perforated_plate_channel,
}


def available_templates() -> list[str]:
    return sorted(TEMPLATE_BUILDERS)


def build_cfd_template_plan(template: str, *, project: str, model_name: str | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
    template = template.strip().lower()
    if template not in TEMPLATE_BUILDERS:
        raise SolidWorksOperationError(f"Unknown CFD template {template!r}. Available: {', '.join(available_templates())}")
    name = model_name or template.replace("-", "_")
    plan = TEMPLATE_BUILDERS[template](project, name, params or {})
    plan["template"] = {
        "template_version": CFD_TEMPLATE_VERSION,
        "template_name": template,
        "parameters": params or {},
    }
    validate_plan(plan)
    return plan


def parse_param_overrides(raw_params: list[str] | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for raw in raw_params or []:
        if "=" not in raw:
            raise SolidWorksOperationError(f"Template parameter must be key=value; got {raw!r}")
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise SolidWorksOperationError(f"Template parameter key cannot be empty: {raw!r}")
        lowered = value.lower()
        if lowered in {"true", "false"}:
            params[key] = lowered == "true"
            continue
        try:
            if "." in value or "e" in lowered:
                params[key] = float(value)
            else:
                params[key] = int(value)
            continue
        except ValueError:
            params[key] = value
    return params


def write_cfd_template_plan(
    template: str,
    *,
    project: str = "phase7_cfd_templates",
    model_name: str | None = None,
    output_path: Path | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = build_cfd_template_plan(template, project=project, model_name=model_name, params=params)
    output = output_path or (project_output_dir(project).parent / "input" / f"{safe_slug(plan['model_name'])}_plan.json")
    output = unique_path(require_under_workspace(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=True, indent=2), encoding="utf-8")
    return {
        "status": "success",
        "success": True,
        "template": template,
        "project": project,
        "model_name": plan["model_name"],
        "path": str(output),
        "operation_count": len(plan["operations"]),
        "plan": plan,
    }

