# Dewaxing Validation And Sensitivity

Status: `active validation guide`

The validation pack checks whether reduced-order guidance is stable enough to
support Agent decisions and Fluent-facing target selection.

## Implementation Assets

- `src/fromcad2cfd_fastcfd/dewaxing_native_validation_pack.py`
- `tests/unit/test_fastcfd_dewaxing_native_validation_pack.py`

## Current Validation Summary

- validation cases: `10`;
- native cell-time steps: `20,525,400`;
- quality status: `passed`;
- recommended target: `shell_thin`.

## Sensitivity Focus

Important parameters:

- `initial_temperature_K`
- `steam_boundary_temperature_K`
- `thickness_m`

The validation and guidance tables should be used to explain:

- grid and time-step sensitivity;
- risk-window timing sensitivity;
- shell-stress proxy sensitivity;
- parameter priority for later Fluent validation targets.

## Public Command

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-native-validation-pack `
  --output-dir sandbox/output/dewaxing_native_validation_pack `
  --profile standard `
  --format markdown
```

## Boundary

Passing this validation pack supports reduced-order screening confidence. It
does not convert proxy stress or pressure-risk quantities into calibrated
failure probabilities.
