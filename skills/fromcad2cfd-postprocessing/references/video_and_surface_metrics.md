# Video And Surface Metrics

Video planning:

- Select autosave data frames using physical simulation time.
- Keep camera and color ranges consistent for comparisons.
- Add timestamp labels with physical time and solver step.
- Store frame plans and generated reports under `sandbox/reports/` in public examples.

Surface interpretation:

- `pressure` on a wall is a normal fluid-load proxy.
- `wall-shear` is a tangential fluid-load proxy.
- Model wall-adjacent temperature is a fluid-side thermal exposure metric.
- True solid stress requires a structural or FSI workflow.
