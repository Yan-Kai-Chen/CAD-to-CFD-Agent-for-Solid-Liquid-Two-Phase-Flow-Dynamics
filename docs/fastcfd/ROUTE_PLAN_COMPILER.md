# FastFluent Route Plan Compiler

Route Plan Compiler is the M6 planning layer. It turns an M5 route selection
into a reviewable pre-execution plan.

The compiler does not run FastFluent, Fluent, PyFluent, UDFs, or arbitrary
scripts. It writes a plan, an approval gate, and, when supported, a controlled
job scaffold plus physics passport.

## Public Demo

```powershell
python -m fromcad2cfd fastcfd route-plan demo --output-dir sandbox/output/route_plan_demo
```

The demo builds a public Flow Pack, selects a route, and compiles an M6 route
plan using short sibling output directories.
For the public structured channel-flow case, it materializes:

- `route_plan.json`
- `route_plan_report.md`
- `approval_gate.json`
- `job/job.json`
- `job/physics_passport.json`
- `job/job_mapping.json`

## Compile From Existing Route Selection

```powershell
python -m fromcad2cfd fastcfd route-plan compile sandbox/output/route_selector_demo/s --output-dir sandbox/output/route_plan
python -m fromcad2cfd fastcfd route-plan validate sandbox/output/route_plan
```

The input can be either a directory containing `route_selection.json` or the
file itself.

## Safe Starter Scaling

For `native_fastfluent_structured`, the compiler materializes a starter
`channel2d` FastCFD job. Geometry comes from the CaseSpec. The current job
scaffold uses a conservative LBM starter scaling profile rather than copying SI
physical values directly into the LBM backend.

This is intentional: the scaffold is a safe pre-execution artifact, not a final
physics reproduction.

## Approval Gate

The generated `approval_gate.json` separates review artifacts from commands that
may be run later. Commands are stored under `commands_after_approval`; the
compiler never executes them.

## Current Limitations

- M6 only materializes a concrete FastCFD job scaffold for
  `native_fastfluent_structured`.
- Other routes currently produce review-only plans.
- The job scaffold must be reviewed before execution.
- Route-plan confidence is workflow confidence, not final CFD validation.
