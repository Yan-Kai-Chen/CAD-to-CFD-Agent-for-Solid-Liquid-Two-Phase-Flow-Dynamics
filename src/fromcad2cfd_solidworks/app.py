from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .connection import connect_solidworks, preflight as connection_preflight
from .documents import close_document, create_new_part, save_as
from .geometry import (
    apply_all_edge_chamfer,
    apply_all_edge_fillet,
    apply_shell,
    apply_uniform_scale,
    combine_bodies,
    create_circular_boss,
    create_circular_sweep,
    create_coordinate_system,
    create_cylinder,
    create_reference_axis_from_planes,
    create_loft_between_circles,
    create_offset_rectangle_sketch,
    create_offset_reference_plane,
    create_rectangular_prism,
    create_revolved_boss,
    create_web_rib,
    cut_counterbore_hole,
    cut_circular_hole,
    cut_hole_grid,
    delete_or_keep_body,
    mirror_body_across_plane,
    move_copy_body,
    offset_selected_face,
    solid_body_inventory,
    thicken_selected_face,
)
from .inspect_model import document_inventory
from .paths import logs_dir, project_output_dir, project_reports_dir, timestamp, unique_path
from .rebuild import rebuild_document
from .reports import write_json_report, write_markdown_report


def run_preflight() -> dict[str, Any]:
    stamp = timestamp()
    data: dict[str, Any] = {
        "title": "SolidWorks Agent Preflight",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "summary": [],
        "steps": [],
        "outputs": {},
        "error": None,
    }
    try:
        result = connection_preflight(visible=False, allow_launch=True, close_if_launched=True)
        data["status"] = "success"
        data["summary"] = [
            f"Connected: {result.get('connected')}",
            f"Revision: {result.get('revision_number')}",
            f"Document count: {result.get('document_count')}",
        ]
        data["steps"].append({"name": "preflight", "success": True, "details": result})
    except Exception as exc:
        data["status"] = "error"
        data["error"] = f"{type(exc).__name__}: {exc}"
        data["steps"].append({"name": "preflight", "success": False, "message": data["error"]})

    md_path = logs_dir() / f"fromcad2cfd_solidworks_preflight_{stamp}.md"
    json_path = logs_dir() / f"fromcad2cfd_solidworks_preflight_{stamp}.json"
    json_written = write_json_report(json_path, data)
    md_written = write_markdown_report(md_path, data)
    data["outputs"] = {"json_report": str(json_written), "markdown_report": str(md_written)}
    json_written.write_text(__import__("json").dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return data


def run_create_cylinder(project: str, radius_mm: float, height_mm: float, visible: bool = True) -> dict[str, Any]:
    stamp = timestamp()
    base = f"fromcad2cfd_solidworks_cylinder_r{radius_mm:g}mm_h{height_mm:g}mm_{stamp}"
    output_dir = project_output_dir(project)
    reports_dir = project_reports_dir(project)
    part_path = unique_path(output_dir / f"{base}.SLDPRT")
    step_path = unique_path(output_dir / f"{base}.STEP")
    md_path = unique_path(reports_dir / f"{base}.md")
    json_path = unique_path(reports_dir / f"{base}.json")

    data: dict[str, Any] = {
        "title": "SolidWorks Agent Cylinder Creation",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "summary": [],
        "steps": [],
        "outputs": {
            "part": str(part_path),
            "step": str(step_path),
            "markdown_report": str(md_path),
            "json_report": str(json_path),
        },
        "request": {
            "project": project,
            "shape": "cylinder",
            "radius_mm": radius_mm,
            "height_mm": height_mm,
        },
        "error": None,
    }

    connection = None
    try:
        connection = connect_solidworks(visible=visible, allow_launch=True)
        data["steps"].append({
            "name": "connect_solidworks",
            "success": True,
            "details": {
                "launched_by_agent": connection.launched_by_agent,
                "attached_to_running_process": connection.attached_to_running_process,
            },
        })

        result = create_cylinder(connection.app, radius_mm, height_mm, part_path, step_path)
        data["status"] = "success"
        data["steps"].extend(result["steps"])
        data["summary"] = [
            "Created cylinder with direct pywin32 COM automation.",
            f"Part exists: {result['part_exists']} size {result['part_size']}",
            f"STEP exists: {result['step_exists']} size {result['step_size']}",
        ]
        data["result"] = result
    except Exception as exc:
        data["status"] = "error"
        data["error"] = f"{type(exc).__name__}: {exc}"
        data["steps"].append({"name": "create_cylinder", "success": False, "message": data["error"]})
    finally:
        if connection and connection.launched_by_agent:
            try:
                connection.app.ExitApp()
                data["steps"].append({"name": "exit_app_if_launched", "success": True})
            except Exception as exc:
                data["steps"].append({"name": "exit_app_if_launched", "success": False, "message": f"{type(exc).__name__}: {exc}"})

    json_written = write_json_report(Path(data["outputs"]["json_report"]), data)
    md_written = write_markdown_report(Path(data["outputs"]["markdown_report"]), data)
    data["outputs"]["json_report"] = str(json_written)
    data["outputs"]["markdown_report"] = str(md_written)
    json_written.write_text(__import__("json").dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return data


def _append_rebuild_step(doc: Any, steps: list[dict[str, Any]], name: str) -> None:
    rebuild = rebuild_document(doc)
    steps.append({"name": name, "success": True, "details": rebuild})


def _append_operation_step(
    doc: Any,
    steps: list[dict[str, Any]],
    name: str,
    operation: Any,
    *,
    rebuild_name: str | None = None,
) -> Any:
    result = operation()
    steps.append({"name": name, "success": True, "details": result})
    if rebuild_name:
        _append_rebuild_step(doc, steps, rebuild_name)
        steps.append({"name": f"{name}_body_inventory", "success": True, "details": solid_body_inventory(doc)})
    return result


def _save_demo_document(doc: Any, output_dir: Path, base_name: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    part_path = unique_path(output_dir / f"{base_name}.SLDPRT")
    step_path = unique_path(output_dir / f"{base_name}.STEP")
    part_save = save_as(doc, part_path)
    steps.append({"name": "save_part", "success": True, "details": part_save})
    step_save = save_as(doc, step_path)
    steps.append({"name": "export_step", "success": True, "details": step_save})
    return {
        "part": str(part_path),
        "step": str(step_path),
        "part_exists": part_path.exists(),
        "part_size": part_path.stat().st_size if part_path.exists() else 0,
        "step_exists": step_path.exists(),
        "step_size": step_path.stat().st_size if step_path.exists() else 0,
    }


def _run_demo_scenario(app: Any, output_dir: Path, base_name: str, scenario_name: str, build: Any) -> dict[str, Any]:
    doc = None
    steps: list[dict[str, Any]] = []
    scenario: dict[str, Any] = {
        "name": scenario_name,
        "status": "running",
        "steps": steps,
        "outputs": {},
        "error": None,
    }
    try:
        doc = create_new_part(app)
        steps.append({"name": "create_new_part", "success": True, "details": document_inventory(doc)})
        build(doc, steps)
        steps.append({"name": "final_inventory", "success": True, "details": document_inventory(doc)})
        steps.append({"name": "final_body_inventory", "success": True, "details": solid_body_inventory(doc)})
        scenario["outputs"] = _save_demo_document(doc, output_dir, f"{base_name}_{scenario_name}", steps)
        close_info = close_document(app, doc, save=False)
        steps.append({"name": "close_document", "success": True, "details": close_info})
        doc = None
        scenario["status"] = "success"
    except Exception as exc:
        scenario["status"] = "error"
        scenario["error"] = f"{type(exc).__name__}: {exc}"
        steps.append({"name": "scenario_error", "success": False, "message": scenario["error"]})
        if doc is not None:
            try:
                close_info = close_document(app, doc, save=False)
                steps.append({"name": "close_document_after_error", "success": True, "details": close_info})
            except Exception as close_exc:
                steps.append(
                    {
                        "name": "close_document_after_error",
                        "success": False,
                        "message": f"{type(close_exc).__name__}: {close_exc}",
                    }
                )
    return scenario


def _build_draft_cut_boss_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_drafted_rectangular_prism",
        lambda: create_rectangular_prism(
            doc,
            width_mm=42,
            height_mm=26,
            depth_mm=18,
            draft_angle_deg=2.0,
        ),
        rebuild_name="rebuild_after_drafted_prism",
    )
    _append_operation_step(
        doc,
        steps,
        "cut_circular_hole",
        lambda: cut_circular_hole(doc, radius_mm=4, center_x_mm=0, center_y_mm=0, through_all=True),
        rebuild_name="rebuild_after_cut_hole",
    )
    _append_operation_step(
        doc,
        steps,
        "create_merged_circular_boss",
        lambda: create_circular_boss(doc, radius_mm=5, depth_mm=6, center_x_mm=12, center_y_mm=0, merge_result=True),
        rebuild_name="rebuild_after_circular_boss",
    )


def _build_offset_sketch_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_offset_rectangle_sketch",
        lambda: create_offset_rectangle_sketch(doc, width_mm=34, height_mm=22, offset_mm=3),
        rebuild_name="rebuild_after_offset_sketch",
    )
    _append_operation_step(
        doc,
        steps,
        "create_export_body_after_offset_check",
        lambda: create_rectangular_prism(doc, width_mm=18, height_mm=12, depth_mm=6, center_y_mm=-28),
        rebuild_name="rebuild_after_export_body",
    )


def _build_fillet_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_rectangular_prism",
        lambda: create_rectangular_prism(doc, width_mm=28, height_mm=18, depth_mm=14),
        rebuild_name="rebuild_after_prism",
    )
    _append_operation_step(
        doc,
        steps,
        "apply_all_edge_fillet",
        lambda: apply_all_edge_fillet(doc, radius_mm=1.0),
        rebuild_name="rebuild_after_fillet",
    )


def _build_chamfer_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_rectangular_prism",
        lambda: create_rectangular_prism(doc, width_mm=28, height_mm=18, depth_mm=14),
        rebuild_name="rebuild_after_prism",
    )
    _append_operation_step(
        doc,
        steps,
        "apply_all_edge_chamfer",
        lambda: apply_all_edge_chamfer(doc, distance_mm=1.0, angle_deg=45.0),
        rebuild_name="rebuild_after_chamfer",
    )


def _build_combine_add_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_main_body",
        lambda: create_rectangular_prism(doc, width_mm=24, height_mm=20, depth_mm=12, merge_result=True),
        rebuild_name="rebuild_after_main_body",
    )
    _append_operation_step(
        doc,
        steps,
        "create_tool_body",
        lambda: create_rectangular_prism(
            doc,
            width_mm=18,
            height_mm=18,
            depth_mm=12,
            center_x_mm=8,
            center_y_mm=0,
            merge_result=False,
        ),
        rebuild_name="rebuild_after_tool_body",
    )
    _append_operation_step(
        doc,
        steps,
        "combine_add",
        lambda: combine_bodies(doc, operation="add", main_body_index=1, tool_body_indices=[0]),
        rebuild_name="rebuild_after_combine_add",
    )


def _build_combine_subtract_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_main_body",
        lambda: create_rectangular_prism(doc, width_mm=32, height_mm=24, depth_mm=16, merge_result=True),
        rebuild_name="rebuild_after_main_body",
    )
    _append_operation_step(
        doc,
        steps,
        "create_cylindrical_tool_body",
        lambda: create_circular_boss(doc, radius_mm=5, depth_mm=20, center_x_mm=0, center_y_mm=0, merge_result=False),
        rebuild_name="rebuild_after_tool_body",
    )
    _append_operation_step(
        doc,
        steps,
        "combine_subtract",
        lambda: combine_bodies(doc, operation="subtract", main_body_index=1, tool_body_indices=[0]),
        rebuild_name="rebuild_after_combine_subtract",
    )


def _build_combine_common_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_main_body",
        lambda: create_rectangular_prism(doc, width_mm=26, height_mm=22, depth_mm=12, merge_result=True),
        rebuild_name="rebuild_after_main_body",
    )
    _append_operation_step(
        doc,
        steps,
        "create_tool_body",
        lambda: create_rectangular_prism(
            doc,
            width_mm=20,
            height_mm=18,
            depth_mm=12,
            center_x_mm=8,
            center_y_mm=0,
            merge_result=False,
        ),
        rebuild_name="rebuild_after_tool_body",
    )
    _append_operation_step(
        doc,
        steps,
        "combine_common",
        lambda: combine_bodies(doc, operation="common", main_body_index=1, tool_body_indices=[0]),
        rebuild_name="rebuild_after_combine_common",
    )


def _build_move_copy_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_main_body",
        lambda: create_rectangular_prism(doc, width_mm=12, height_mm=12, depth_mm=10, merge_result=True),
        rebuild_name="rebuild_after_main_body",
    )
    _append_operation_step(
        doc,
        steps,
        "create_second_body",
        lambda: create_rectangular_prism(
            doc,
            width_mm=9,
            height_mm=9,
            depth_mm=9,
            center_x_mm=18,
            center_y_mm=0,
            merge_result=False,
        ),
        rebuild_name="rebuild_after_second_body",
    )
    _append_operation_step(
        doc,
        steps,
        "move_rotate_second_body",
        lambda: move_copy_body(doc, body_index=0, translate_mm=(12, 4, 0), rotate_deg=(0, 0, 20), copy=False),
        rebuild_name="rebuild_after_move_copy",
    )


def run_phase2_modeling_demo(project: str = "phase2_modeling_demo", visible: bool = True) -> dict[str, Any]:
    stamp = timestamp()
    base = f"fromcad2cfd_solidworks_phase2_modeling_{stamp}"
    output_dir = project_output_dir(project)
    reports_dir = project_reports_dir(project)
    md_path = unique_path(reports_dir / f"{base}.md")
    json_path = unique_path(reports_dir / f"{base}.json")

    data: dict[str, Any] = {
        "title": "SolidWorks Agent Phase2 Modeling Demo",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "summary": [],
        "steps": [],
        "outputs": {
            "markdown_report": str(md_path),
            "json_report": str(json_path),
            "project_output_dir": str(output_dir),
        },
        "request": {
            "project": project,
            "phase": "Phase2",
            "purpose": "modeling primitives and advanced operation smoke tests",
        },
        "scenarios": [],
        "error": None,
    }

    scenarios = [
        ("draft_cut_boss", _build_draft_cut_boss_demo),
        ("offset_sketch", _build_offset_sketch_demo),
        ("fillet_all_edges", _build_fillet_demo),
        ("chamfer_all_edges", _build_chamfer_demo),
        ("boolean_add", _build_combine_add_demo),
        ("boolean_subtract", _build_combine_subtract_demo),
        ("boolean_common", _build_combine_common_demo),
        ("move_rotate_body", _build_move_copy_demo),
    ]

    connection = None
    try:
        connection = connect_solidworks(visible=visible, allow_launch=True)
        data["steps"].append(
            {
                "name": "connect_solidworks",
                "success": True,
                "details": {
                    "launched_by_agent": connection.launched_by_agent,
                    "attached_to_running_process": connection.attached_to_running_process,
                },
            }
        )
        for scenario_name, build in scenarios:
            result = _run_demo_scenario(connection.app, output_dir, base, scenario_name, build)
            data["scenarios"].append(result)
            data["steps"].append(
                {
                    "name": f"scenario_{scenario_name}",
                    "success": result["status"] == "success",
                    "message": result.get("error"),
                    "details": {
                        "outputs": result.get("outputs"),
                        "step_count": len(result.get("steps", [])),
                    },
                }
            )

        success_count = sum(1 for scenario in data["scenarios"] if scenario.get("status") == "success")
        error_count = len(data["scenarios"]) - success_count
        data["status"] = "success" if error_count == 0 else "partial"
        data["summary"] = [
            f"Phase2 scenarios run: {len(data['scenarios'])}",
            f"Successful scenarios: {success_count}",
            f"Failed scenarios: {error_count}",
            f"Project output dir: {output_dir}",
        ]
    except Exception as exc:
        data["status"] = "error"
        data["error"] = f"{type(exc).__name__}: {exc}"
        data["steps"].append({"name": "phase2_demo", "success": False, "message": data["error"]})
    finally:
        if connection and connection.launched_by_agent:
            try:
                connection.app.ExitApp()
                data["steps"].append({"name": "exit_app_if_launched", "success": True})
            except Exception as exc:
                data["steps"].append({"name": "exit_app_if_launched", "success": False, "message": f"{type(exc).__name__}: {exc}"})

    json_written = write_json_report(Path(data["outputs"]["json_report"]), data)
    md_written = write_markdown_report(Path(data["outputs"]["markdown_report"]), data)
    data["outputs"]["json_report"] = str(json_written)
    data["outputs"]["markdown_report"] = str(md_written)
    json_written.write_text(__import__("json").dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return data


def _build_shell_open_top_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_box_for_shell",
        lambda: create_rectangular_prism(doc, width_mm=34, height_mm=24, depth_mm=18),
        rebuild_name="rebuild_after_box",
    )
    _append_operation_step(
        doc,
        steps,
        "apply_shell_open_z_plus",
        lambda: apply_shell(doc, thickness_mm=1.5, outward=False, open_face_axis="z+"),
        rebuild_name="rebuild_after_shell",
    )


def _build_thicken_face_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_base_for_thicken",
        lambda: create_rectangular_prism(doc, width_mm=28, height_mm=18, depth_mm=8),
        rebuild_name="rebuild_after_base",
    )
    _append_operation_step(
        doc,
        steps,
        "thicken_z_plus_face",
        lambda: thicken_selected_face(doc, thickness_mm=2.0, face_axis="z+", merge_result=True),
        rebuild_name="rebuild_after_thicken",
    )


def _build_revolved_boss_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_revolved_ring",
        lambda: create_revolved_boss(doc, inner_radius_mm=3, outer_radius_mm=9, height_mm=20),
        rebuild_name="rebuild_after_revolve",
    )


def _build_reference_plane_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_offset_reference_plane",
        lambda: create_offset_reference_plane(doc, base_plane="Front", distance_mm=18),
        rebuild_name="rebuild_after_reference_plane",
    )
    _append_operation_step(
        doc,
        steps,
        "create_export_body_with_reference_plane",
        lambda: create_rectangular_prism(doc, width_mm=18, height_mm=12, depth_mm=6),
        rebuild_name="rebuild_after_export_body",
    )


def _build_mirror_body_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_offset_seed_body",
        lambda: create_rectangular_prism(doc, width_mm=8, height_mm=12, depth_mm=10, center_x_mm=14),
        rebuild_name="rebuild_after_seed_body",
    )
    _append_operation_step(
        doc,
        steps,
        "mirror_body_across_right_plane",
        lambda: mirror_body_across_plane(doc, body_index=0, plane="Right", merge_result=False),
        rebuild_name="rebuild_after_mirror",
    )


def _build_linear_copy_array_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_linear_array_seed",
        lambda: create_rectangular_prism(doc, width_mm=6, height_mm=8, depth_mm=8),
        rebuild_name="rebuild_after_seed",
    )
    _append_operation_step(
        doc,
        steps,
        "linear_body_copy_array",
        lambda: move_copy_body(doc, body_index=0, translate_mm=(14, 0, 0), rotate_deg=(0, 0, 0), copy=True, number_of_copies=3),
        rebuild_name="rebuild_after_linear_array",
    )


def _build_circular_copy_array_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_circular_array_seed",
        lambda: create_rectangular_prism(doc, width_mm=5, height_mm=7, depth_mm=7, center_x_mm=16),
        rebuild_name="rebuild_after_seed",
    )
    _append_operation_step(
        doc,
        steps,
        "circular_body_copy_array",
        lambda: move_copy_body(doc, body_index=0, translate_mm=(0, 0, 0), rotate_deg=(0, 0, 60), copy=True, number_of_copies=5),
        rebuild_name="rebuild_after_circular_array",
    )


def _build_cfd_fluid_domain_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_outer_fluid_box",
        lambda: create_rectangular_prism(doc, width_mm=70, height_mm=34, depth_mm=24, merge_result=True),
        rebuild_name="rebuild_after_outer_domain",
    )
    _append_operation_step(
        doc,
        steps,
        "create_cylindrical_obstacle_tool",
        lambda: create_circular_boss(doc, radius_mm=5, depth_mm=28, center_x_mm=0, center_y_mm=0, merge_result=False),
        rebuild_name="rebuild_after_obstacle_tool",
    )
    _append_operation_step(
        doc,
        steps,
        "subtract_obstacle_from_fluid_domain",
        lambda: combine_bodies(doc, operation="subtract", main_body_index=1, tool_body_indices=[0]),
        rebuild_name="rebuild_after_fluid_boolean",
    )


def _build_sweep_pipe_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_circular_sweep_pipe",
        lambda: create_circular_sweep(doc, path_length_mm=42, diameter_mm=6),
        rebuild_name="rebuild_after_sweep",
    )


def _build_loft_transition_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_loft_transition",
        lambda: create_loft_between_circles(doc, radius1_mm=4, radius2_mm=9, distance_mm=28),
        rebuild_name="rebuild_after_loft",
    )


def run_phase3_advanced_demo(project: str = "phase3_advanced_modeling_demo", visible: bool = True) -> dict[str, Any]:
    stamp = timestamp()
    base = f"fromcad2cfd_solidworks_phase3_advanced_{stamp}"
    output_dir = project_output_dir(project)
    reports_dir = project_reports_dir(project)
    md_path = unique_path(reports_dir / f"{base}.md")
    json_path = unique_path(reports_dir / f"{base}.json")

    data: dict[str, Any] = {
        "title": "SolidWorks Agent Phase3 Advanced Modeling Demo",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "summary": [],
        "steps": [],
        "outputs": {
            "markdown_report": str(md_path),
            "json_report": str(json_path),
            "project_output_dir": str(output_dir),
        },
        "request": {
            "project": project,
            "phase": "Phase3",
            "purpose": "advanced modeling primitives with shell/thicken priority",
        },
        "scenarios": [],
        "error": None,
    }

    scenarios = [
        ("shell_open_top", _build_shell_open_top_demo),
        ("thicken_selected_face", _build_thicken_face_demo),
        ("revolved_boss", _build_revolved_boss_demo),
        ("reference_plane_offset", _build_reference_plane_demo),
        ("mirror_body", _build_mirror_body_demo),
        ("linear_body_copy_array", _build_linear_copy_array_demo),
        ("circular_body_copy_array", _build_circular_copy_array_demo),
        ("cfd_fluid_domain_subtract", _build_cfd_fluid_domain_demo),
        ("sweep_pipe", _build_sweep_pipe_demo),
        ("loft_transition", _build_loft_transition_demo),
    ]

    connection = None
    try:
        connection = connect_solidworks(visible=visible, allow_launch=True)
        data["steps"].append(
            {
                "name": "connect_solidworks",
                "success": True,
                "details": {
                    "launched_by_agent": connection.launched_by_agent,
                    "attached_to_running_process": connection.attached_to_running_process,
                },
            }
        )
        for scenario_name, build in scenarios:
            result = _run_demo_scenario(connection.app, output_dir, base, scenario_name, build)
            data["scenarios"].append(result)
            data["steps"].append(
                {
                    "name": f"scenario_{scenario_name}",
                    "success": result["status"] == "success",
                    "message": result.get("error"),
                    "details": {
                        "outputs": result.get("outputs"),
                        "step_count": len(result.get("steps", [])),
                    },
                }
            )

        success_count = sum(1 for scenario in data["scenarios"] if scenario.get("status") == "success")
        error_count = len(data["scenarios"]) - success_count
        data["status"] = "success" if error_count == 0 else "partial"
        data["summary"] = [
            f"Phase3 scenarios run: {len(data['scenarios'])}",
            f"Successful scenarios: {success_count}",
            f"Failed scenarios: {error_count}",
            f"Project output dir: {output_dir}",
            "Shell and thicken scenarios are prioritized at the top of this run.",
        ]
    except Exception as exc:
        data["status"] = "error"
        data["error"] = f"{type(exc).__name__}: {exc}"
        data["steps"].append({"name": "phase3_demo", "success": False, "message": data["error"]})
    finally:
        if connection and connection.launched_by_agent:
            try:
                connection.app.ExitApp()
                data["steps"].append({"name": "exit_app_if_launched", "success": True})
            except Exception as exc:
                data["steps"].append({"name": "exit_app_if_launched", "success": False, "message": f"{type(exc).__name__}: {exc}"})

    json_written = write_json_report(Path(data["outputs"]["json_report"]), data)
    md_written = write_markdown_report(Path(data["outputs"]["markdown_report"]), data)
    data["outputs"]["json_report"] = str(json_written)
    data["outputs"]["markdown_report"] = str(md_written)
    json_written.write_text(__import__("json").dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return data


def _build_multi_hole_grid_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_plate_for_hole_grid",
        lambda: create_rectangular_prism(doc, width_mm=56, height_mm=34, depth_mm=12),
        rebuild_name="rebuild_after_plate",
    )
    _append_operation_step(
        doc,
        steps,
        "cut_four_hole_grid",
        lambda: cut_hole_grid(
            doc,
            radius_mm=2.5,
            centers_mm=[(-18, -9), (18, -9), (-18, 9), (18, 9)],
            through_all=True,
        ),
        rebuild_name="rebuild_after_hole_grid",
    )


def _build_counterbore_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_block_for_counterbore",
        lambda: create_rectangular_prism(doc, width_mm=42, height_mm=30, depth_mm=16),
        rebuild_name="rebuild_after_block",
    )
    _append_operation_step(
        doc,
        steps,
        "cut_counterbore_hole",
        lambda: cut_counterbore_hole(
            doc,
            pilot_radius_mm=2.5,
            counterbore_radius_mm=5.0,
            counterbore_depth_mm=4.0,
        ),
        rebuild_name="rebuild_after_counterbore",
    )


def _build_move_face_offset_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_block_for_move_face",
        lambda: create_rectangular_prism(doc, width_mm=26, height_mm=18, depth_mm=10),
        rebuild_name="rebuild_after_block",
    )
    _append_operation_step(
        doc,
        steps,
        "offset_z_plus_face",
        lambda: offset_selected_face(doc, axis="z+", distance_mm=4.0),
        rebuild_name="rebuild_after_move_face",
    )


def _build_scale_body_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_block_for_scale",
        lambda: create_rectangular_prism(doc, width_mm=20, height_mm=14, depth_mm=10),
        rebuild_name="rebuild_after_block",
    )
    _append_operation_step(
        doc,
        steps,
        "apply_uniform_scale",
        lambda: apply_uniform_scale(doc, scale_factor=1.35),
        rebuild_name="rebuild_after_scale",
    )


def _build_delete_body_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_main_body",
        lambda: create_rectangular_prism(doc, width_mm=26, height_mm=18, depth_mm=12, center_x_mm=-10, merge_result=True),
        rebuild_name="rebuild_after_main_body",
    )
    _append_operation_step(
        doc,
        steps,
        "create_body_to_delete",
        lambda: create_rectangular_prism(doc, width_mm=8, height_mm=8, depth_mm=8, center_x_mm=16, merge_result=False),
        rebuild_name="rebuild_after_second_body",
    )
    _append_operation_step(
        doc,
        steps,
        "delete_selected_body",
        lambda: delete_or_keep_body(doc, body_index=0, keep_selected=False),
        rebuild_name="rebuild_after_delete_body",
    )


def _build_web_rib_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_base_plate_for_rib",
        lambda: create_rectangular_prism(doc, width_mm=48, height_mm=8, depth_mm=16),
        rebuild_name="rebuild_after_base_plate",
    )
    _append_operation_step(
        doc,
        steps,
        "create_web_rib",
        lambda: create_web_rib(doc, length_mm=38, height_mm=16, thickness_mm=3, base_top_y_mm=4),
        rebuild_name="rebuild_after_web_rib",
    )


def _build_reference_axis_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_reference_axis_from_planes",
        lambda: create_reference_axis_from_planes(doc, plane_a="Front", plane_b="Right"),
        rebuild_name="rebuild_after_reference_axis",
    )
    _append_operation_step(
        doc,
        steps,
        "create_export_body_with_axis",
        lambda: create_rectangular_prism(doc, width_mm=14, height_mm=10, depth_mm=8),
        rebuild_name="rebuild_after_export_body",
    )


def _build_coordinate_system_demo(doc: Any, steps: list[dict[str, Any]]) -> None:
    _append_operation_step(
        doc,
        steps,
        "create_coordinate_system",
        lambda: create_coordinate_system(doc, location_mm=(4, 6, 8), rotation_deg=(10, 0, 25)),
        rebuild_name="rebuild_after_coordinate_system",
    )
    _append_operation_step(
        doc,
        steps,
        "create_export_body_with_coordinate_system",
        lambda: create_rectangular_prism(doc, width_mm=16, height_mm=12, depth_mm=8),
        rebuild_name="rebuild_after_export_body",
    )


def run_phase4_complete_demo(project: str = "phase4_complete_modeling_demo", visible: bool = True) -> dict[str, Any]:
    stamp = timestamp()
    base = f"fromcad2cfd_solidworks_phase4_complete_{stamp}"
    output_dir = project_output_dir(project)
    reports_dir = project_reports_dir(project)
    md_path = unique_path(reports_dir / f"{base}.md")
    json_path = unique_path(reports_dir / f"{base}.json")

    data: dict[str, Any] = {
        "title": "SolidWorks Agent Phase4 Complete Modeling Demo",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "summary": [],
        "steps": [],
        "outputs": {
            "markdown_report": str(md_path),
            "json_report": str(json_path),
            "project_output_dir": str(output_dir),
        },
        "request": {
            "project": project,
            "phase": "Phase4",
            "purpose": "remaining high-value engineering and CFD-prep modeling operations",
        },
        "scenarios": [],
        "error": None,
    }

    scenarios = [
        ("multi_hole_grid", _build_multi_hole_grid_demo),
        ("counterbore_hole", _build_counterbore_demo),
        ("move_face_offset", _build_move_face_offset_demo),
        ("scale_body", _build_scale_body_demo),
        ("delete_body", _build_delete_body_demo),
        ("web_rib", _build_web_rib_demo),
        ("reference_axis", _build_reference_axis_demo),
        ("coordinate_system", _build_coordinate_system_demo),
    ]

    connection = None
    try:
        connection = connect_solidworks(visible=visible, allow_launch=True)
        data["steps"].append(
            {
                "name": "connect_solidworks",
                "success": True,
                "details": {
                    "launched_by_agent": connection.launched_by_agent,
                    "attached_to_running_process": connection.attached_to_running_process,
                },
            }
        )
        for scenario_name, build in scenarios:
            result = _run_demo_scenario(connection.app, output_dir, base, scenario_name, build)
            data["scenarios"].append(result)
            data["steps"].append(
                {
                    "name": f"scenario_{scenario_name}",
                    "success": result["status"] == "success",
                    "message": result.get("error"),
                    "details": {
                        "outputs": result.get("outputs"),
                        "step_count": len(result.get("steps", [])),
                    },
                }
            )

        success_count = sum(1 for scenario in data["scenarios"] if scenario.get("status") == "success")
        error_count = len(data["scenarios"]) - success_count
        data["status"] = "success" if error_count == 0 else "partial"
        data["summary"] = [
            f"Phase4 scenarios run: {len(data['scenarios'])}",
            f"Successful scenarios: {success_count}",
            f"Failed scenarios: {error_count}",
            f"Project output dir: {output_dir}",
            "Phase4 focuses on holes, counterbores, direct face edits, scale, delete body, ribs, axes, and coordinate systems.",
        ]
    except Exception as exc:
        data["status"] = "error"
        data["error"] = f"{type(exc).__name__}: {exc}"
        data["steps"].append({"name": "phase4_demo", "success": False, "message": data["error"]})
    finally:
        if connection and connection.launched_by_agent:
            try:
                connection.app.ExitApp()
                data["steps"].append({"name": "exit_app_if_launched", "success": True})
            except Exception as exc:
                data["steps"].append({"name": "exit_app_if_launched", "success": False, "message": f"{type(exc).__name__}: {exc}"})

    json_written = write_json_report(Path(data["outputs"]["json_report"]), data)
    md_written = write_markdown_report(Path(data["outputs"]["markdown_report"]), data)
    data["outputs"]["json_report"] = str(json_written)
    data["outputs"]["markdown_report"] = str(md_written)
    json_written.write_text(__import__("json").dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return data

