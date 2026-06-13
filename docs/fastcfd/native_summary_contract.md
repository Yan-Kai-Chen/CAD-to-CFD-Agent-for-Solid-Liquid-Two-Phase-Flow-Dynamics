# FastFluent Native Summary Contract

FastFluent native summaries are lightweight JSON files emitted directly by
selected FastFluent executables at the end of a controlled run.

Filename:

```text
fastfluent_native_summary.json
```

Native residual history is emitted as:

```text
fastfluent_native_convergence.csv
```

Schema version:

```text
fromcad2cfd_fastfluent_native_summary_v1
```

## Purpose

The native summary records run facts that are most trustworthy at the solver
entrypoint level:

- case type,
- executable role,
- completed and requested steps,
- output interval,
- final residual,
- physical time,
- field prefix,
- grid size and cell length,
- physical properties,
- reference velocity,
- optional obstacle-cell count.

The native convergence CSV records the residual samples available at each output
interval:

```csv
step,residual
50,0.25
100,0.125
```

The native summary does not replace wrapper-side reports or VTK field parsing.
Field-derived metrics such as centerline velocity, outlet spread, reverse-flow
fraction, wake bounding boxes, and refinement hints still come from
`field_qoi.json`.

## Current Hooked Entrypoints

The current local source hooks target:

- `examples/cavity2d/cavity2d.cpp`
- `examples/openboundary2d/openbd2d.cpp`
- generated controlled `obstacle2d.cpp`

The hook is intentionally small: it adds a JSON writer after the solver loop and
does not modify collision models, boundary conditions, geometry construction, or
VTK output.

See [native_summary_source_hooks.md](native_summary_source_hooks.md) for the
source-hook placement pattern.

## Wrapper Handling

`fromcad2cfd_fastcfd.native_summary` reads the native files when present. The
controlled real backend then:

- stores them as the `native_summary` and `native_convergence` artifacts,
- propagates compact native metrics and residual-history summaries into
  `qoi.json`,
- records native-file availability in `claim_ledger.json`,
- leaves an unavailable reason when an executable has not yet been hooked.

## Boundary

This contract is a source-level run-fact bridge. It is not final CFD validation
and does not make FastFluent a substitute for Fluent.
