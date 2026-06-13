# Native Summary Source Hooks

This note documents the bounded local FastFluent source hooks used by
FromCAD2CFD. The public repository does not vendor the full FastFluent source.

## Hook Boundary

The hook adds:

- `#include <fstream>`
- one `WriteFastFluentNativeSummary(...)` helper after the local `using`
  declarations,
- `InitFastFluentNativeConvergence()` and
  `AppendFastFluentNativeConvergence(...)` helpers,
- one initialization call after the initial field output,
- one append call immediately after each output-step residual is computed,
- one call to that helper after final timing output and before `return 0`.

The hook does not change:

- solver loops,
- collision models,
- boundary conditions,
- geometry construction,
- VTK field writers.

## Hooked Local Files

Validated local files:

```text
examples/cavity2d/cavity2d.cpp
examples/openboundary2d/openbd2d.cpp
```

The generated obstacle route uses the same hook pattern inside the generated
`obstacle2d.cpp` template owned by FromCAD2CFD.

## Output

Each hooked executable writes this file in its run working directory:

```text
fastfluent_native_summary.json
```

It also writes:

```text
fastfluent_native_convergence.csv
```

The JSON must include:

```json
{
  "schema_version": "fromcad2cfd_fastfluent_native_summary_v1",
  "case_type": "channel2d",
  "executable_role": "fastfluent_example",
  "completed_steps": 100,
  "requested_total_steps": 100,
  "output_interval": 50,
  "final_residual": 0.0240816,
  "physical_time_s": 0.0,
  "field_prefix": "cavblock2d",
  "grid": {
    "nx": 120,
    "ny": 40,
    "cell_length_mm": 1.0
  },
  "physical_properties": {
    "rho_ref_g_per_mm3": 1.0e-9,
    "kinematic_viscosity_mm2_s": 1.0
  },
  "boundary_conditions": {
    "reference_velocity_mm_s": 0.03
  }
}
```

Numerical values above are illustrative. The real executable writes values from
its parsed `.ini` file, timer, and final residual variable.

The convergence CSV format is:

```csv
step,residual
50,0.25
100,0.125
```

Rows are written only when the native solver computes an output-step residual.
