# Basic Fluent Monitor Summary Example

This example uses synthetic Fluent report-monitor rows. It is intended to test
the public postprocessing parser and summary contract without requiring Fluent
case/data files.

Run:

```powershell
fromcad2cfd post summarize-run `
  --global-monitor examples/postprocessing/basic_monitor_summary/global_monitors.out `
  --wall-monitor examples/postprocessing/basic_monitor_summary/wall_exposure_indicators.out `
  --output-dir sandbox/reports/basic_monitor_summary `
  --model-name basic_monitor_summary
```

The summary reports final pressure, temperature, species fraction, wall heat
absorption, and model pressure/load proxy metrics.
