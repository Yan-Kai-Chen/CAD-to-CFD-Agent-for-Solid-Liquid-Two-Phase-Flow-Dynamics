# FastFluent Baseline Manifest

Date: 2026-06-13

## Purpose

This baseline records the local FastFluent solver state before the first
FromCAD2CFD FastCFD integration batch. The goal is to preserve the validated
source behavior while adding an agent-safe interface contract in the
FromCAD2CFD repository.

## Source Snapshot

- Local source root used for assessment:
  private local FastFluent source checkout, not distributed in this public
  repository.
- Interface style:
  C++ case source plus `.ini` configuration, built into per-case executables.
- Core source folders:
  `src/lbm`, `src/boundary`, `src/geometry`, `src/io`, `src/offLattice`,
  `src/ca`, and `src/parallel`.

## Validated Local Smoke Tests

- `examples/cavity2d`
  - Short run succeeded with a `30 x 30` grid and `200` steps.
  - Produced `.vtm/.vti` outputs and convergence log lines.
- `tests/io/stlreader`
  - Read `cylinder100_20_20finer.stl`.
  - Produced block-geometry VTK XML outputs.

## Known Build Finding

Native Windows Makefile execution originally failed because
`src/data_struct/field.h` included POSIX `sys/mman.h`, and `make.mk` linked
`-lrt`. The first local source-level portability patch adds a non-CUDA Windows
fallback for `StreamMapArray` and removes `-lrt` from Windows link flags.

## Integration Boundary

The first FastCFD batch does not copy solver source into the public repository
and does not expose arbitrary C++ editing or arbitrary executable execution.
It defines the stable agent-facing contract that future FastFluent source
refactoring must satisfy. The first real backend target is the controlled
`examples/cavity2d` route.
