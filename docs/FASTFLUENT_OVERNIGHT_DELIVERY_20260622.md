# FastFluent Overnight Delivery Report

Date: 2026-06-22

## Goal Summary

This implementation upgrades FastCFD / FastFluent from a preliminary advisory
screening layer into a structured evidence-to-Fluent handoff layer. The new
workflow is:

```text
FastFluent / FastCFD physics screening
-> physics passport
-> Fluent setup hints
-> validated solver_plan_patch.json
-> Markdown handoff report
-> tests and public demo artifacts
```

The delivered route is non-executing with respect to Fluent. It does not launch
Fluent, edit Fluent case files, emit arbitrary TUI commands, or generate
arbitrary UDF source code.

## What Was Implemented

### Solver Plan Patch Contract

Implemented `src/fromcad2cfd_fastcfd/solver_plan_patch.py`.

Key capabilities:

- schema version `fromcad2cfd_fastfluent_solver_plan_patch_v1`;
- dataclasses for `PatchEvidence`, `PatchOperation`, `SolverPlanPatch`, and
  `PatchValidationResult`;
- recursive dangerous-key rejection;
- allowlisted patch operations and patch path prefixes;
- evidence-reference requirements for physics, numerics, transient, monitor,
  and source-term patches;
- JSON writer and Markdown report writer;
- reviewer checklist in generated reports.

### Steam-Air Condensation Physics Passport

Implemented `src/fromcad2cfd_fastcfd/steam_air_condensation.py`.

Key capabilities:

- case schema `fromcad2cfd_fastfluent_steam_air_condensation_case_v1`;
- passport schema `fromcad2cfd_fastfluent_steam_air_condensation_passport_v1`;
- Fluent-hints schema
  `fromcad2cfd_fastfluent_steam_air_condensation_fluent_hints_v1`;
- public synthetic steam-air wall-condensation demo case writer;
- bounded saturation-temperature lookup and log-pressure interpolation;
- inlet superheat, wall subcooling, non-condensable risk, thermal penetration
  depth, near-wall resolution, convective/diffusive time scale, recommended
  time step, and source-stiffness risk checks;
- fail-closed validation for invalid inputs and dangerous keys;
- JSON passport, Fluent hints, status artifact, and Markdown report outputs.

### Fluent Patch Compiler

Implemented `src/fromcad2cfd_fastcfd/fluent_patch_compiler.py`.

Key capabilities:

- compiles steam-air passports into validated solver-plan patches;
- preserves evidence records and source artifact traceability;
- emits non-executing Fluent-facing recommendations for physics, numerics,
  transient controls, monitors, source-term controls, post-processing, and
  acceptance criteria;
- supports merge behavior for patch bundles, including duplicate monitor
  handling and conflicting replace-patch warnings;
- writes `solver_plan_patch.json` and `solver_plan_patch_report.md`;
- provides a full public steam-air handoff demo pipeline.

### CLI Integration

Added FastCFD CLI commands:

```powershell
python -m fromcad2cfd fastcfd write-steam-air-demo --output-dir sandbox/output/steam_air_demo
python -m fromcad2cfd fastcfd validate-steam-air-condensation --case sandbox/output/steam_air_demo/steam_air_condensation_case.json --output-dir sandbox/output/steam_air_demo/passport
python -m fromcad2cfd fastcfd compile-fluent-patch --input sandbox/output/steam_air_demo/passport/steam_air_condensation_passport.json --output sandbox/output/steam_air_demo/solver_plan_patch.json
python -m fromcad2cfd fastcfd steam-air-handoff-demo --output-dir sandbox/output/steam_air_handoff_demo
```

### Capability Registry

Added capability entries:

- `steam_air_condensation_passport`;
- `solver_plan_patch_contract`;
- `fluent_patch_compiler`;
- `steam_air_handoff_demo`.

Added physics model family:

- `steam_air_condensation`.

Added disabled public capabilities:

- `fluent_execution_from_patch_compiler`;
- `raw_fluent_patch_command`.

## Files Changed

### New source files

- `src/fromcad2cfd_fastcfd/solver_plan_patch.py`
- `src/fromcad2cfd_fastcfd/steam_air_condensation.py`
- `src/fromcad2cfd_fastcfd/fluent_patch_compiler.py`

### Updated source files

- `src/fromcad2cfd_fastcfd/cli.py`
- `src/fromcad2cfd_fastcfd/capabilities.py`
- `src/fromcad2cfd_fastcfd/__init__.py`

### New tests

- `tests/unit/test_fastcfd_solver_plan_patch.py`
- `tests/unit/test_fastcfd_steam_air_condensation.py`
- `tests/unit/test_fastcfd_fluent_patch_compiler.py`
- `tests/unit/test_fastcfd_steam_air_cli.py`

### Documentation

- `README.md`
- `docs/architecture.md`
- `docs/FASTFLUENT_OVERNIGHT_PROGRESS_20260622.md`
- `docs/FASTFLUENT_OVERNIGHT_DELIVERY_20260622.md`

## Generated Demo Artifacts

Public synthetic artifacts were generated under:

```text
sandbox/output/steam_air_demo/
```

Artifact list:

```text
sandbox/output/steam_air_demo/steam_air_condensation_case.json
sandbox/output/steam_air_demo/passport/steam_air_condensation_passport.json
sandbox/output/steam_air_demo/passport/steam_air_condensation_fluent_hints.json
sandbox/output/steam_air_demo/passport/steam_air_condensation_report.md
sandbox/output/steam_air_demo/solver_plan_patch.json
sandbox/output/steam_air_demo/solver_plan_patch_report.md
```

Optional full demo artifacts were also generated under:

```text
sandbox/output/steam_air_handoff_demo/
```

The public demo passport status is `warn`, not `pass`, because the synthetic
case intentionally has high non-condensable-gas risk and high source-term
stiffness risk. The generated patch remains valid and non-executing.

## Test Commands And Results

Targeted new tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q tests/unit/test_fastcfd_solver_plan_patch.py tests/unit/test_fastcfd_steam_air_condensation.py tests/unit/test_fastcfd_fluent_patch_compiler.py tests/unit/test_fastcfd_steam_air_cli.py -p no:cacheprovider
```

Result:

```text
19 passed in 0.24s
```

FastCFD-related regression filter:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q tests -k "fastcfd or steam or patch or vof or turbulence or rheology" -p no:cacheprovider
```

Result:

```text
118 passed, 93 deselected in 5.88s
```

Full test suite:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q -p no:cacheprovider
```

Result:

```text
211 passed in 6.15s
```

## Known Limitations

- The steam-air saturation estimate is a bounded engineering lookup and
  interpolation table, not IAPWS thermodynamics.
- The condensation passport is a readiness gate and setup-evidence generator,
  not a high-fidelity condensation solver.
- The solver-plan patch does not execute Fluent and does not edit Fluent case
  files.
- The generated `solver_plan_patch.json` is intended for reviewer-approved
  future Fluent Solver Plan v2 consumption.
- Unsupported FastFluent evidence schemas fail closed in the patch compiler.
- Windows long-path-safe I/O was added for the new artifact paths because this
  checkout path is long.

## What Remains For Next Iteration

Recommended next development issues:

1. Fluent Solver Plan v2 schema and validator.
2. Executable PyFluent template generator.
3. Fluent local execution adapter.
4. Fluent diagnostics and recovery loop.
5. UDF-safe source-term template lifecycle.
6. FastFluent mesh quality to Fluent mesh gate integration.
7. Trust report for Fluent outputs.

## Final State

The overnight evidence-to-Fluent handoff slice is implemented, documented, and
tested. It creates a public synthetic steam-air physics passport, Fluent setup
hints, a validated `solver_plan_patch.json`, and Markdown handoff reports
without executing Fluent.
