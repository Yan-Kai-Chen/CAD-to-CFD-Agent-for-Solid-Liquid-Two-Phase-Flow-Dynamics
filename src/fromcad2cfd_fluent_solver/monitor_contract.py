"""Public-safe Fluent report monitor contracts."""

from __future__ import annotations

from typing import Any


MONITOR_CONTRACT_SCHEMA_VERSION = "fromcad2cfd_fluent_monitor_contract_v1"

GLOBAL_REPORT_DEFS = [
    "flow-time",
    "delta-time",
    "iters-per-timestep",
    "vol_avg_abs_pressure",
    "vol_avg_temperature",
    "vol_max_temperature",
    "vol_min_temperature",
    "vol_max_velocity",
    "vol_avg_h2o_mass_fraction",
    "vol_avg_o2_mass_fraction",
    "vol_avg_n2_mass_fraction",
    "inlet_mass_flow_rate",
]

WALL_REPORT_DEFS = [
    "flow-time",
    "delta-time",
    "all_walls_avg_abs_pressure",
    "all_walls_max_abs_pressure",
    "all_walls_avg_wall_adjacent_temperature",
    "all_walls_max_wall_adjacent_temperature",
    "all_walls_avg_wall_shear",
    "all_walls_max_wall_shear",
    "all_walls_total_heat_transfer_rate",
    "outer_wall_avg_abs_pressure",
    "outer_wall_max_abs_pressure",
    "outer_wall_avg_wall_adjacent_temperature",
    "outer_wall_max_wall_adjacent_temperature",
    "outer_wall_total_heat_transfer_rate",
    "model_avg_abs_pressure",
    "model_max_abs_pressure",
    "model_avg_wall_adjacent_temperature",
    "model_max_wall_adjacent_temperature",
]


def monitor_contract() -> dict[str, Any]:
    """Return the public Fluent report monitor contract."""

    return {
        "schema_version": MONITOR_CONTRACT_SCHEMA_VERSION,
        "global_monitor": {
            "file_name": "monitors/global_monitors.out",
            "frequency": 1,
            "frequency_of": "time-step",
            "report_defs": list(GLOBAL_REPORT_DEFS),
        },
        "wall_monitor": {
            "file_name": "monitors/wall_exposure_indicators.out",
            "frequency": 1,
            "frequency_of": "time-step",
            "report_defs": list(WALL_REPORT_DEFS),
        },
        "interpretation": {
            "pressure": "Fluid absolute pressure on model or wall surfaces; usable as a normal fluid-load proxy.",
            "wall_shear": "Fluid-side tangential shear stress proxy.",
            "structural_stress": "Not computed by Fluent pressure or wall shear; requires structural or FSI handoff.",
            "heat_rate_sign": "Project reports usually present heat removed from fluid as positive -wall_heat_transfer_rate.",
        },
    }
