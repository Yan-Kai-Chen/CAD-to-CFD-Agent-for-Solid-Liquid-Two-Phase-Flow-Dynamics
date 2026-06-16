# Post-processing Interface

The first public-safe postprocessing interface reads Fluent report-monitor
files, computes summary metrics, writes Markdown/JSON reports, and creates
video frame plans. It does not require Fluent case/data files.

Implemented commands:

```text
fromcad2cfd post parse-monitor --monitor <monitor.out>
fromcad2cfd post summarize-run --global-monitor <global.out> --wall-monitor <wall.out>
fromcad2cfd post write-video-plan --autosave-dir <autosaves> --field <field> --output <plan.json>
fromcad2cfd post compare-runs --left-summary <a.json> --right-summary <b.json>
```

Example:

```powershell
fromcad2cfd post summarize-run `
  --global-monitor examples/postprocessing/basic_monitor_summary/global_monitors.out `
  --wall-monitor examples/postprocessing/basic_monitor_summary/wall_exposure_indicators.out `
  --output-dir sandbox/reports/basic_monitor_summary `
  --model-name basic_monitor_summary
```

MCP entry point:

```powershell
fromcad2cfd-post-mcp --describe
fromcad2cfd-post-mcp --list-tools
```

Pressure is reported as a normal fluid-load proxy. Wall shear is reported as a
tangential fluid-load proxy. Neither is solid structural stress.
