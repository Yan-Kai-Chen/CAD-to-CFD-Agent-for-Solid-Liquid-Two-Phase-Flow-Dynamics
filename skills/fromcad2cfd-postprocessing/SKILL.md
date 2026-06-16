---
name: fromcad2cfd-postprocessing
description: Public-safe Fluent postprocessing for FromCAD2CFD. Use when parsing Fluent report monitors, summarizing pressure/temperature/species/wall heat metrics, planning timestamped videos, comparing runs, or explaining pressure and wall shear as fluid-load proxies without exposing private Fluent case/data files.
---

# FromCAD2CFD Postprocessing

Use this skill for public-safe Fluent monitor parsing and derived reports.

## Rules

- Prefer monitor files, manifests, and synthetic examples over private Fluent case/data files.
- Do not commit `.cas.h5`, `.dat.h5`, private videos, or local absolute paths.
- Parse global and wall report files before making claims.
- Use timestamp overlays for transient videos so playback time is not confused with physical time.
- Treat pressure as a normal fluid-load proxy and wall shear as a tangential fluid-load proxy.
- Do not claim solid structural stress from Fluent pressure or wall shear.

## Workflow

1. Parse or summarize monitor files:

```powershell
fromcad2cfd post summarize-run --global-monitor <global.out> --wall-monitor <wall.out> --output-dir sandbox/reports/run
```

2. Write video plans from autosaves instead of running Fluent GUI automation:

```powershell
fromcad2cfd post write-video-plan --autosave-dir sandbox/input/autosaves --field temperature --output sandbox/reports/video_plan.json
```

3. Keep rendering as a local operator step unless the environment and inputs are explicitly approved.

## References

- Monitor columns and summary metrics: `references/monitor_summary_contract.md`
- Video planning and surface-load interpretation: `references/video_and_surface_metrics.md`
