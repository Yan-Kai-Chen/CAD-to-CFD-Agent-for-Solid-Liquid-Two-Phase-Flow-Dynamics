"""Practical geometry, boundary-condition, and initialization utilities.

S3 prepares small public-safe native setup artifacts that can feed the S2
practical mini computations. It does not launch Fluent, call PyFluent, emit
Fluent commands, generate UDF code, or claim production CFD setup completeness.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from fromcad2cfd_cad import AgentResult

from .practical_heat_diffusion import demo_heat_diffusion_1d_case
from .practical_native_artifacts import ensure_dir, write_csv, write_json, write_text
from .practical_scalar_transport import demo_scalar_transport_case
from .wax_rheology_phase_change import create_demo_wax_rheology_case


PRACTICAL_SETUP_SCHEMA_VERSION = "fromcad2cfd_fastfluent_practical_setup_contract_v1"
PRACTICAL_SETUP_PACK_SCHEMA_VERSION = "fromcad2cfd_fastfluent_practical_setup_pack_v1"
PRACTICAL_CASE_TEMPLATE_SCHEMA_VERSION = "fromcad2cfd_fastfluent_practical_case_template_v1"

LIMITATIONS = [
    "S3 writes public-safe native setup artifacts only.",
    "S3 does not launch Fluent or call PyFluent.",
    "S3 does not edit Fluent case/data files.",
    "S3 does not emit Fluent TUI or executable UDF source.",
    "S3 does not replace CAD meshing, Fluent Meshing, HyperMesh, or production CFD validation.",
]


def build_line_1d_geometry(*, length_m: float = 0.02, nx: int = 41, geometry_id: str = "line_1d") -> dict[str, Any]:
    if nx < 2:
        raise ValueError("nx must be at least 2 for 1D geometry.")
    dx = float(length_m) / (nx - 1)
    nodes = [{"node_id": i, "x_m": i * dx, "zone": "left" if i == 0 else "right" if i == nx - 1 else "interior"} for i in range(nx)]
    return {
        "schema_version": PRACTICAL_SETUP_SCHEMA_VERSION,
        "geometry_id": geometry_id,
        "geometry_type": "line_1d",
        "dimension": 1,
        "length_m": float(length_m),
        "grid": {"nx": nx, "dx_m": dx, "node_count": nx, "cell_count": nx - 1},
        "boundary_zones": {"left": 1, "right": 1, "interior": nx - 2},
        "nodes": nodes,
        "metadata": {"public_safe": True, "fluent_launched": False},
        "limitations": list(LIMITATIONS),
    }


def build_channel_2d_geometry(
    *,
    length_m: float = 0.1,
    height_m: float = 0.02,
    nx: int = 51,
    ny: int = 21,
    obstacle: dict[str, Any] | None = None,
    geometry_id: str = "channel_2d",
) -> dict[str, Any]:
    if nx < 3 or ny < 3:
        raise ValueError("nx and ny must be at least 3 for 2D channel geometry.")
    dx = float(length_m) / (nx - 1)
    dy = float(height_m) / (ny - 1)
    obstacle_cfg = obstacle or {"type": "circle", "center_x_m": 0.045, "center_y_m": 0.01, "radius_m": 0.003}
    nodes: list[dict[str, Any]] = []
    zone_counts: dict[str, int] = {"inlet": 0, "outlet": 0, "wall": 0, "obstacle": 0, "interior": 0}
    node_id = 0
    for j in range(ny):
        y = j * dy
        for i in range(nx):
            x = i * dx
            zone = _classify_channel_node(i, j, x, y, nx, ny, obstacle_cfg)
            zone_counts[zone] = zone_counts.get(zone, 0) + 1
            nodes.append({"node_id": node_id, "i": i, "j": j, "x_m": x, "y_m": y, "zone": zone})
            node_id += 1
    active_node_count = len(nodes) - zone_counts.get("obstacle", 0)
    return {
        "schema_version": PRACTICAL_SETUP_SCHEMA_VERSION,
        "geometry_id": geometry_id,
        "geometry_type": "channel_2d_structured",
        "dimension": 2,
        "length_m": float(length_m),
        "height_m": float(height_m),
        "grid": {"nx": nx, "ny": ny, "dx_m": dx, "dy_m": dy, "node_count": len(nodes), "active_node_count": active_node_count, "cell_count": (nx - 1) * (ny - 1)},
        "obstacle": obstacle_cfg,
        "boundary_zones": zone_counts,
        "nodes": nodes,
        "metadata": {"public_safe": True, "fluent_launched": False},
        "limitations": list(LIMITATIONS),
    }


def build_boundary_condition_contract(geometry: dict[str, Any], *, contract_id: str = "channel_bc_contract") -> dict[str, Any]:
    zones = geometry.get("boundary_zones", {})
    dimension = int(geometry.get("dimension", 0))
    if dimension == 1:
        conditions = {
            "left": {"heat": {"type": "fixed_temperature", "temperature_K": 373.15}, "scalar": {"type": "fixed_value", "value": 1.0}},
            "right": {"heat": {"type": "fixed_temperature", "temperature_K": 293.15}, "scalar": {"type": "zero_gradient"}},
        }
        required = ["left", "right"]
    else:
        conditions = {
            "inlet": {
                "flow": {"type": "velocity_inlet", "profile": "parabolic", "mean_velocity_m_s": 0.2},
                "heat": {"type": "fixed_temperature", "temperature_K": 353.15},
                "scalar": {"type": "fixed_value", "value": 1.0},
            },
            "outlet": {
                "flow": {"type": "pressure_outlet", "gauge_pressure_Pa": 0.0},
                "heat": {"type": "zero_gradient"},
                "scalar": {"type": "zero_gradient"},
            },
            "wall": {
                "flow": {"type": "no_slip"},
                "heat": {"type": "insulated"},
                "scalar": {"type": "no_flux"},
            },
            "obstacle": {
                "flow": {"type": "no_slip"},
                "heat": {"type": "insulated"},
                "scalar": {"type": "no_flux"},
            },
        }
        required = ["inlet", "outlet", "wall"]
    validation = validate_boundary_condition_contract({"required_zones": required, "conditions": conditions}, geometry)
    return {
        "schema_version": PRACTICAL_SETUP_SCHEMA_VERSION,
        "contract_id": contract_id,
        "geometry_id": geometry.get("geometry_id"),
        "geometry_type": geometry.get("geometry_type"),
        "required_zones": required,
        "available_zones": zones,
        "conditions": conditions,
        "validation": validation,
        "metadata": {"public_safe": True, "fluent_launched": False},
        "limitations": list(LIMITATIONS),
    }


def validate_boundary_condition_contract(contract: dict[str, Any], geometry: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    zones = geometry.get("boundary_zones", {})
    for zone in contract.get("required_zones", []):
        if int(zones.get(zone, 0)) <= 0:
            errors.append(f"Required zone is missing or empty: {zone}")
    conditions = contract.get("conditions", {})
    for zone in contract.get("required_zones", []):
        if zone not in conditions:
            errors.append(f"Missing boundary condition for required zone: {zone}")
    if geometry.get("dimension") == 2 and int(zones.get("obstacle", 0)) > 0 and "obstacle" not in conditions:
        warnings.append("Obstacle nodes exist but no obstacle boundary condition was provided.")
    return {"status": "failed" if errors else "passed", "passed": not errors, "errors": errors, "warnings": warnings}


def write_geometry_files(geometry: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    target = Path(output_dir)
    nodes = list(geometry.get("nodes", []))
    manifest_path = write_json(target / f"{geometry['geometry_id']}_geometry_manifest.json", {key: value for key, value in geometry.items() if key != "nodes"})
    nodes_path = write_csv(target / f"{geometry['geometry_id']}_nodes.csv", nodes)
    return {"geometry_manifest": str(manifest_path), "nodes": str(nodes_path)}


def write_boundary_condition_contract(contract: dict[str, Any], output_dir: str | Path) -> Path:
    return write_json(Path(output_dir) / "boundary_condition_contract.json", contract)


def write_initial_field_files(geometry: dict[str, Any], contract: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    target = Path(output_dir)
    ensure_dir(target)
    rows = initial_field_rows(geometry, contract)
    temperature_path = write_csv(target / "temperature_field.csv", _project_field(rows, "temperature_K"))
    scalar_path = write_csv(target / "scalar_field.csv", _project_field(rows, "scalar"))
    velocity_path = write_csv(target / "velocity_field.csv", _project_velocity(rows))
    summary = field_initialization_summary(rows)
    summary_path = write_json(target / "field_initialization_summary.json", summary)
    return {"temperature_field": str(temperature_path), "scalar_field": str(scalar_path), "velocity_field": str(velocity_path), "field_initialization_summary": str(summary_path)}


def initial_field_rows(geometry: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    del contract
    if int(geometry.get("dimension", 0)) == 1:
        length = float(geometry["length_m"])
        rows = []
        for node in geometry.get("nodes", []):
            x = float(node["x_m"])
            rows.append(
                {
                    "node_id": node["node_id"],
                    "x_m": x,
                    "zone": node["zone"],
                    "temperature_K": 373.15 + (293.15 - 373.15) * x / max(length, 1.0e-30),
                    "scalar": 1.0 if x <= 0.35 * length else 0.0,
                    "velocity_x_m_s": 0.2,
                    "velocity_y_m_s": 0.0,
                }
            )
        return rows
    height = float(geometry["height_m"])
    length = float(geometry["length_m"])
    mean_velocity = 0.2
    rows = []
    for node in geometry.get("nodes", []):
        x = float(node["x_m"])
        y = float(node["y_m"])
        zone = str(node["zone"])
        eta = min(max(y / max(height, 1.0e-30), 0.0), 1.0)
        parabolic = 6.0 * mean_velocity * eta * (1.0 - eta)
        if zone in {"wall", "obstacle"}:
            parabolic = 0.0
        rows.append(
            {
                "node_id": node["node_id"],
                "x_m": x,
                "y_m": y,
                "zone": zone,
                "temperature_K": 353.15 + (293.15 - 353.15) * x / max(length, 1.0e-30),
                "scalar": 1.0 if x <= 0.25 * length and zone != "obstacle" else 0.0,
                "velocity_x_m_s": parabolic,
                "velocity_y_m_s": 0.0,
            }
        )
    return rows


def field_initialization_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    temperatures = [float(row["temperature_K"]) for row in rows]
    scalars = [float(row["scalar"]) for row in rows]
    velocities = [math.hypot(float(row["velocity_x_m_s"]), float(row["velocity_y_m_s"])) for row in rows]
    return {
        "schema_version": PRACTICAL_SETUP_SCHEMA_VERSION,
        "node_count": len(rows),
        "temperature_min_K": min(temperatures),
        "temperature_max_K": max(temperatures),
        "scalar_min": min(scalars),
        "scalar_max": max(scalars),
        "velocity_min_m_s": min(velocities),
        "velocity_max_m_s": max(velocities),
        "nonfinite_count": sum(1 for value in temperatures + scalars + velocities if not math.isfinite(value)),
        "fluent_launched": False,
    }


def build_case_templates(line_geometry: dict[str, Any], channel_geometry: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    target = Path(output_dir)
    ensure_dir(target)
    heat_case = demo_heat_diffusion_1d_case()
    heat_case.update(
        {
            "schema_version": PRACTICAL_CASE_TEMPLATE_SCHEMA_VERSION,
            "case_id": "s3_heat_diffusion_from_setup",
            "case_name": "S3 Heat Diffusion Template From Setup",
            "length_m": line_geometry["length_m"],
            "nx": line_geometry["grid"]["nx"],
        }
    )
    scalar_case = demo_scalar_transport_case(bounded=True, clamp_enabled=True)
    scalar_case.update(
        {
            "schema_version": PRACTICAL_CASE_TEMPLATE_SCHEMA_VERSION,
            "case_id": "s3_scalar_transport_from_setup",
            "case_name": "S3 Scalar Transport Template From Setup",
            "length_m": channel_geometry["length_m"],
            "nx": channel_geometry["grid"]["nx"],
            "time_step_s": 0.001,
            "initial_patch_min_m": 0.01,
            "initial_patch_max_m": 0.03,
        }
    )
    wax_case = create_demo_wax_rheology_case(case_name="s3_wax_practical_template")
    wax_case["template_schema_version"] = PRACTICAL_CASE_TEMPLATE_SCHEMA_VERSION
    paths = {
        "heat_diffusion_1d_case": str(write_json(target / "heat_diffusion_1d_case.json", heat_case)),
        "scalar_transport_1d_case": str(write_json(target / "scalar_transport_1d_case.json", scalar_case)),
        "wax_practical_case": str(write_json(target / "wax_practical_case.json", wax_case)),
    }
    template_manifest = {
        "schema_version": PRACTICAL_CASE_TEMPLATE_SCHEMA_VERSION,
        "templates": paths,
        "compatible_cli": [
            "fromcad2cfd fastcfd practical-native-demo-pack",
            "fromcad2cfd fastcfd wax-rheology-handoff-demo",
        ],
        "fluent_launched": False,
    }
    paths["template_manifest"] = str(write_json(target / "case_template_manifest.json", template_manifest))
    return paths


def run_practical_native_setup_demo(output_dir: str | Path) -> dict[str, Any]:
    root = Path(output_dir)
    ensure_dir(root)
    line_geometry = build_line_1d_geometry()
    channel_geometry = build_channel_2d_geometry()
    contract = build_boundary_condition_contract(channel_geometry)
    artifacts = {
        "line_geometry": write_geometry_files(line_geometry, root / "geometry"),
        "channel_geometry": write_geometry_files(channel_geometry, root / "geometry"),
        "boundary_condition_contract": str(write_boundary_condition_contract(contract, root / "boundary_conditions")),
        "initial_fields": write_initial_field_files(channel_geometry, contract, root / "initial_fields"),
        "case_templates": build_case_templates(line_geometry, channel_geometry, root / "case_templates"),
    }
    manifest = build_practical_setup_manifest(line_geometry, channel_geometry, contract, artifacts, root)
    manifest_path = write_json(root / "practical_setup_manifest.json", manifest)
    summary_path = write_text(root / "practical_setup_summary.md", practical_setup_summary_markdown(manifest))
    result = AgentResult.success(
        backend="fastcfd",
        operation="practical_native_setup_demo",
        message="FastFluent S3 practical native setup demo generated.",
        outputs={"manifest": manifest, "artifacts": artifacts | {"practical_setup_manifest": str(manifest_path), "practical_setup_summary": str(summary_path)}},
        metadata={"output_dir": str(root), "fluent_launched": False, "pyfluent_called": False},
    )
    write_json(root / "pack_status.json", result.to_dict())
    return result.to_dict()


def build_practical_setup_manifest(
    line_geometry: dict[str, Any],
    channel_geometry: dict[str, Any],
    contract: dict[str, Any],
    artifacts: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    acceptance = {
        "line_1d_geometry_generated": True,
        "channel_2d_geometry_generated": True,
        "boundary_condition_contract_valid": contract["validation"]["passed"],
        "initial_temperature_field_generated": True,
        "initial_scalar_field_generated": True,
        "initial_velocity_field_generated": True,
        "case_templates_generated": True,
        "fluent_launched": False,
    }
    return {
        "schema_version": PRACTICAL_SETUP_PACK_SCHEMA_VERSION,
        "pack_name": "FastFluent S3 Practical Native Setup Pack",
        "line_1d_summary": {"node_count": line_geometry["grid"]["node_count"], "cell_count": line_geometry["grid"]["cell_count"]},
        "channel_2d_summary": {
            "node_count": channel_geometry["grid"]["node_count"],
            "active_node_count": channel_geometry["grid"]["active_node_count"],
            "cell_count": channel_geometry["grid"]["cell_count"],
            "boundary_zones": channel_geometry["boundary_zones"],
        },
        "acceptance_summary": acceptance,
        "artifact_index": artifacts,
        "output_dir": str(output_dir),
        "limitations": list(LIMITATIONS),
        "metadata": {"fluent_launched": False, "pyfluent_called": False, "private_data_used": False},
    }


def practical_setup_summary_markdown(manifest: dict[str, Any]) -> str:
    acceptance = manifest["acceptance_summary"]
    return "\n".join(
        [
            "# FastFluent S3 Practical Native Setup Pack",
            "",
            f"- Overall result: `{'pass' if all(value for key, value in acceptance.items() if key != 'fluent_launched') and acceptance['fluent_launched'] is False else 'warn'}`",
            f"- Line 1D nodes: `{manifest['line_1d_summary']['node_count']}`",
            f"- Channel 2D nodes: `{manifest['channel_2d_summary']['node_count']}`",
            f"- Boundary zones: `{manifest['channel_2d_summary']['boundary_zones']}`",
            f"- Boundary contract valid: `{acceptance['boundary_condition_contract_valid']}`",
            f"- Fluent launched: `{manifest['metadata']['fluent_launched']}`",
            "",
            "## What S3 Provides",
            "",
            "S3 provides public-safe native geometry manifests, boundary-condition contracts, initial fields, and practical case templates for S2 utilities.",
            "",
            "## What S3 Does Not Provide",
            "",
            "S3 does not launch Fluent, call PyFluent, generate executable UDF code, run meshing software, or prove production CFD readiness.",
            "",
        ]
    )


def _classify_channel_node(i: int, j: int, x: float, y: float, nx: int, ny: int, obstacle: dict[str, Any]) -> str:
    if obstacle and obstacle.get("type") == "circle":
        dx = x - float(obstacle["center_x_m"])
        dy = y - float(obstacle["center_y_m"])
        if dx * dx + dy * dy <= float(obstacle["radius_m"]) ** 2:
            return "obstacle"
    if i == 0:
        return "inlet"
    if i == nx - 1:
        return "outlet"
    if j == 0 or j == ny - 1:
        return "wall"
    return "interior"


def _project_field(rows: list[dict[str, Any]], field_name: str) -> list[dict[str, Any]]:
    projected = []
    for row in rows:
        payload = {"node_id": row["node_id"], "x_m": row["x_m"], "zone": row["zone"], field_name: row[field_name]}
        if "y_m" in row:
            payload["y_m"] = row["y_m"]
        projected.append(payload)
    return projected


def _project_velocity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projected = []
    for row in rows:
        payload = {"node_id": row["node_id"], "x_m": row["x_m"], "zone": row["zone"], "velocity_x_m_s": row["velocity_x_m_s"], "velocity_y_m_s": row["velocity_y_m_s"]}
        if "y_m" in row:
            payload["y_m"] = row["y_m"]
        projected.append(payload)
    return projected
