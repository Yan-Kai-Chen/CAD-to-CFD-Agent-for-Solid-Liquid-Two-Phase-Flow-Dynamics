# FromCAD2CFD FastFluent Core Integration

This directory vendors the C++ FastFluent / FreeLB-derived solver core used by
the FromCAD2CFD FastCFD pillar.

## Role In This Repository

- Provides the C++ LBM/CA/free-surface/non-Newtonian source tree.
- Provides public examples and benchmark sources used by controlled real
  FastFluent backend routes.
- Acts as the default source root discovered by the Python agent layer.

## What Is Not Included

The public repository intentionally excludes generated or unreviewed artifacts:

- compiled executables,
- object files,
- generated VTK output,
- Fluent case/data files,
- unreviewed STL/CAD geometry data.

## License

The C++ core retains its original GPLv3 license. See `LICENSE` in this
directory. The surrounding Python agent framework uses the repository-root
Apache-2.0 license unless stated otherwise.
