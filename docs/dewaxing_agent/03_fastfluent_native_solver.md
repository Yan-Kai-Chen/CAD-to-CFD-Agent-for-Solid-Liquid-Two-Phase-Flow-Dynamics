# FastFluent Native Dewaxing Solver

Status: `active implementation guide`

The native dewaxing solver is the reduced-order FastFluent layer for the
dewaxing case study. It is designed for guidance and screening, not final
Fluent validation.

## Implementation Assets

- `src/fromcad2cfd_fastcfd/dewaxing_native_solver.py`
- `src/fromcad2cfd_fastcfd/dewaxing_native_study.py`
- `tests/unit/test_fastcfd_dewaxing_native_solver.py`
- `tests/unit/test_fastcfd_dewaxing_native_study.py`

## Computed Evidence

The solver writes reviewable fields and QoIs:

- temperature field;
- liquid-fraction field;
- full-melt timing;
- early shell-stress proxy;
- pressure-risk proxy;
- drainage and relief indicators;
- Result Pack style status and claim boundaries.

## Public Commands

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-native-solver `
  --output-dir sandbox/output/dewaxing_native_solver `
  --format markdown

python -m fromcad2cfd fastcfd run-dewaxing-native-study `
  --output-dir sandbox/output/dewaxing_native_study `
  --format markdown
```

## Interpretation Boundary

The native solver can support Agent screening, parameter ranking, and
Fluent-facing target selection. It cannot support final crack probability,
two-way FSI validation, or a claim that Fluent validation has been replaced.
