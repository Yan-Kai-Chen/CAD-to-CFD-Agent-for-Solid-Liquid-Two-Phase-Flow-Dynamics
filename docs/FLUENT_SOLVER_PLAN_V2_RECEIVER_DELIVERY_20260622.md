# Fluent Solver Plan v2 Receiver Delivery

Date: 2026-06-22

## Goal Summary

This delivery adds the minimum downstream receiver for FastFluent
`solver_plan_patch.json` artifacts:

```text
base_solver_plan_v2.json
+ solver_plan_patch.json
-> patched_solver_plan_preview.json
-> patch_application_report.md
-> conflict_report.json
-> before_after_diff.md
-> reviewer_checklist.md
```

The implementation is intentionally preview-only. It does not launch Fluent,
does not execute PyFluent, does not emit raw Fluent TUI commands, does not
generate UDF source, and does not modify Fluent case/data files.

## What Was Implemented

- Fluent Solver Plan v2 schema and validator.
- Recursive dangerous-key rejection for plan and patch payloads.
- Safe slash-path patch traversal with a Solver Plan v2 top-level allowlist.
- Patch operations: `add`, `replace`, `append_unique`, `warn`, and `block`.
- Conflict detection for duplicate incompatible `replace` operations.
- Blocking behavior for unsafe paths, dangerous values, invalid evidence, and
  attempts to move away from `runtime.execution_policy = preview_only`.
- Preview artifact writers:
  - `patched_solver_plan_preview.json`
  - `patch_application_report.md`
  - `conflict_report.json`
  - `before_after_diff.md`
  - `reviewer_checklist.md`
- CLI integration under `fromcad2cfd fluent-solver`.
- MCP-safe tool inventory expansion for Solver Plan v2 demo writing and patch
  preview.
- Unit tests for schema validation, patch preview, fail-closed behavior, and
  CLI output generation.

## Files Changed

New implementation files:

- `src/fromcad2cfd_fluent_solver/solver_plan_v2.py`
- `src/fromcad2cfd_fluent_solver/patch_preview.py`

Updated integration files:

- `src/fromcad2cfd_fluent_solver/__init__.py`
- `src/fromcad2cfd_fluent_solver/cli.py`
- `src/fromcad2cfd_mcp_fluent_solver/tools.py`

New tests:

- `tests/unit/test_fluent_solver_plan_v2.py`
- `tests/unit/test_fluent_solver_patch_preview.py`
- `tests/unit/test_fluent_solver_plan_v2_cli.py`

Documentation:

- `docs/FLUENT_SOLVER_PLAN_V2_RECEIVER_GOAL_20260622.md`
- `docs/FLUENT_SOLVER_PLAN_V2_RECEIVER_PROGRESS_20260622.md`
- `docs/FLUENT_SOLVER_PLAN_V2_RECEIVER_DELIVERY_20260622.md`
- `README.md`
- `ROADMAP.md`
- `docs/architecture.md`
- `docs/fluent_solver/interface_draft.md`
- `docs/fluent_solver/solver_plan_contract.md`

## New CLI Commands

```powershell
python -m fromcad2cfd fluent-solver capabilities --format json
python -m fromcad2cfd fluent-solver write-plan-v2-demo --output-dir sandbox/output/fluent_plan_v2_demo
python -m fromcad2cfd fluent-solver preview-patch --base-plan sandbox/output/fluent_plan_v2_demo/base_solver_plan_v2.json --patch sandbox/output/steam_air_demo/solver_plan_patch.json --output-dir sandbox/output/fluent_plan_v2_demo/preview
python -m fromcad2cfd fluent-solver plan-v2-patch-preview-demo --output-dir sandbox/output/fluent_plan_v2_patch_preview_demo
```

If `--patch` is omitted from the convenience demo, a synthetic public-safe patch
is generated internally. If `--patch` is provided, the command preserves a copy
under `patch/solver_plan_patch.json`.

## Generated Artifact List

The verified demo using the existing steam-air FastFluent patch wrote:

```text
sandbox/output/fluent_plan_v2_patch_preview_demo/
|-- base_solver_plan_v2.json
|-- base_solver_plan_v2_report.md
|-- patch/
|   `-- solver_plan_patch.json
`-- preview/
    |-- patched_solver_plan_preview.json
    |-- patch_application_report.md
    |-- conflict_report.json
    |-- before_after_diff.md
    `-- reviewer_checklist.md
```

Demo result:

- Preview status: `ready_for_review`
- Applied operations: `28`
- Skipped operations: `0`
- Conflicts: `0`
- Blocking errors: `0`

## Test Commands And Results

Baseline relevant test group before v2 implementation:

```powershell
python -m pytest -q tests/unit/test_fastcfd_solver_plan_patch.py tests/unit/test_fastcfd_fluent_patch_compiler.py tests/unit/test_fastcfd_steam_air_condensation.py tests/unit/test_fastcfd_steam_air_cli.py tests/unit/test_fluent_solver_public_interface.py -p no:cacheprovider
```

Result:

```text
26 passed in 0.28s
```

New targeted tests:

```powershell
python -m pytest -q tests/unit/test_fluent_solver_plan_v2.py tests/unit/test_fluent_solver_patch_preview.py tests/unit/test_fluent_solver_plan_v2_cli.py -p no:cacheprovider
```

Result:

```text
20 passed in 0.26s
```

Required filtered test command:

```powershell
python -m pytest -q tests -k "solver_plan_v2 or patch_preview or fluent_solver"
```

Result:

```text
27 passed, 204 deselected in 0.59s
```

Required full test command:

```powershell
python -m pytest -q
```

Result:

```text
231 passed in 6.20s
```

## Known Limitations

- Solver Plan v2 is a preview/review contract, not an execution-ready Fluent
  case setup.
- Mesh file, named zones, material cards, boundary values, and time controls
  remain reviewer-owned.
- Patch preview supports only allowlisted JSON paths and operations.
- The system does not generate UDF code or raw source expressions.
- The system does not perform runtime diagnostics or recovery.
- Deep sandbox artifact paths may exceed normal Windows `Get-Content` path
  handling; the Python writers use long-path handling, and PowerShell can read
  those files with a `\\?\` path prefix.

## Explicit Stop Boundary

This delivery stops at:

```text
schema
validate
preview
diff
conflict report
reviewer checklist
```

Do not extend this phase into:

- Fluent launch
- PyFluent execution
- raw TUI or journal execution
- UDF lifecycle
- runtime diagnostics
- recovery loops
- trust-report infrastructure
- GPU or OpenFOAM integration

## Recommended Next Work: FastFluent Horizontal Expansion

The immediate next phase should be FastFluent horizontal physics expansion,
not more solver-plan receiver infrastructure.

Recommended order:

1. Connect existing VOF passport output to `solver_plan_patch.json`.
2. Connect existing turbulence passport output to `solver_plan_patch.json`.
3. Connect existing rheology passport output to `solver_plan_patch.json`.
4. Add mesh-quality evidence to solver-plan patch generation.
5. Strengthen steam-air condensation evidence with dimensionless groups and
   source-term consistency checks.
6. Add solid-liquid suspension readiness passport.
7. Add wax rheology / melting-solidification readiness passport.
8. Add phase-change source-term dimensional checks.
9. Add unstructured heat-transfer mini benchmark evidence.
