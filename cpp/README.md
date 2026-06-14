# C++ Solver Cores

This directory contains source-level solver components used by FromCAD2CFD.

## `fastfluent_core`

`fastfluent_core` is the vendored C++ FastFluent / FreeLB-derived solver core.
It includes the low-level LBM/CA/free-surface/non-Newtonian source tree,
examples, benchmarks, Makefiles, and the original GPLv3 license file.

The Python agent layer discovers this directory as the default FastFluent source
root. A different source root can still be supplied through:

- `--source-root`
- `FROMCAD2CFD_FASTFLUENT_ROOT`
- `FASTFLUENT_ROOT`

Generated executables, object files, generated VTK output, Fluent case/data
files, and unreviewed CAD/STL geometry data are not committed.
