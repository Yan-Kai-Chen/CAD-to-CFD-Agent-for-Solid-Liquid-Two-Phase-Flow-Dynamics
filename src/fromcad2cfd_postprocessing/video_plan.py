"""Public-safe video planning utilities for Fluent autosave sequences."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


VIDEO_PLAN_SCHEMA_VERSION = "fromcad2cfd_fluent_video_plan_v1"


def write_video_plan(
    autosave_dir: str | Path,
    *,
    output_path: str | Path,
    field: str,
    time_step_s: float = 0.001,
    interval_s: float = 0.1,
) -> dict[str, Any]:
    source = Path(autosave_dir)
    frames = []
    step_interval = max(1, round(interval_s / time_step_s))
    for data_file in sorted(source.glob("*.dat.h5")):
        step = _step_from_name(data_file.name)
        if step is None:
            continue
        if step % step_interval == 0:
            frames.append(
                {
                    "step": step,
                    "physical_time_s": step * time_step_s,
                    "data_file": str(data_file),
                    "field": field,
                    "timestamp_label": f"t = {step * time_step_s:.3f} s, step = {step}",
                }
            )
    payload = {
        "schema_version": VIDEO_PLAN_SCHEMA_VERSION,
        "status": "success" if frames else "empty",
        "autosave_dir": str(source),
        "field": field,
        "time_step_s": time_step_s,
        "interval_s": interval_s,
        "frame_count": len(frames),
        "frames": frames,
        "notes": [
            "This is a public-safe plan only. Rendering requires a local Fluent or compatible postprocessor.",
            "Timestamp labels should be overlaid on videos to avoid confusing playback time with simulated time.",
        ],
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    import json

    output.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return payload


def _step_from_name(name: str) -> int | None:
    match = re.search(r"-(\d{5,})\.dat\.h5$", name)
    if match:
        return int(match.group(1))
    return None
