# FastFluent S7 Workflow Runner

S7 is the recommended FastFluent agent entrypoint. It turns a CaseSpec v3 file
into a complete, inspectable workflow chain:

```text
CaseSpec
  -> Flow Pack
  -> Route Selection
  -> Route Plan
  -> Execution Gate
  -> Controlled Runner
  -> optional S6 native advisory evidence
  -> Result Pack
  -> Agent Decision
```

S7 does not replace Fluent and does not launch Fluent. It is a bounded workflow
control layer for setup review and FastFluent advisory evidence.

Use S7 when an agent needs one command that can answer:

- whether the setup contracts are coherent;
- which controlled route should be used next;
- whether execution is still gated by review;
- whether bounded native advisory evidence is available;
- what decision artifact should be handed to the next workflow block.

## Commands

Dry-run workflow:

```powershell
python -m fromcad2cfd fastcfd workflow run `
  --case-file examples/fastcfd/casespec_v3/channel_flow_case.json `
  --output-dir sandbox/output/s7_workflow_dry `
  --mode dry_run `
  --mesh-mode structured-demo
```

Native advisory workflow:

```powershell
python -m fromcad2cfd fastcfd workflow run `
  --case-file examples/fastcfd/casespec_v3/channel_flow_case.json `
  --output-dir sandbox/output/s7_workflow_native `
  --mode native_advisory `
  --mesh-mode structured-demo `
  --transport-quantity alpha
```

Public demo:

```powershell
python -m fromcad2cfd fastcfd workflow demo --output-dir sandbox/output/s7_workflow_demo --mode native_advisory
```

Expected public-demo terminal status:

```text
native_advisory_complete
```

## Modes

`dry_run`

- builds and validates the setup chain;
- compiles route selection and route plan;
- audits execution gate;
- records Controlled Runner dry-run ledger;
- compiles a review-only Result Pack.

`native_advisory`

- runs the same setup/control chain as `dry_run`;
- runs the S6 unified transport route as bounded native evidence;
- compiles the S6 `status.json` into the unified Result Pack layer.

The current S7 native route is intentionally narrow: `native_route=transport`.

## Output Layout

```text
01_flow_pack/
02_route_selection/
03_route_plan/
04_execution_gate/
05_controlled_runner/
06_native_result/        # native_advisory only
07_result_pack/
workflow_manifest.json
stage_status.json
agent_decision.json
workflow_report.md
workflow_status.json
```

## Failure Behavior

S7 stops at the first blocking stage. For example, an invalid CaseSpec stops at
Flow Pack and does not run route selection, native evidence, or Result Pack
compilation.

## Acceptance Gate

A valid S7 public run should satisfy all of the following:

- `workflow_manifest.json` exists.
- `stage_status.json` exists and records each completed stage.
- `agent_decision.json` exists.
- `workflow_report.md` exists.
- `dry_run` mode produces a review-only Result Pack.
- `native_advisory` mode produces a S6 native advisory Result Pack.
- `can_support_final_cfd_validation` remains `false`.
- Fluent is not launched and arbitrary code is not executed.

## Boundary

S7 is valid for agent workflow control and pre-Fluent screening. It does not
launch Fluent, does not execute arbitrary code, and does not claim final CFD
validation.
