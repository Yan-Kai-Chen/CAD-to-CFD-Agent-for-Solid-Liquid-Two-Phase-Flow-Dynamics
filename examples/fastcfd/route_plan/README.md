# Route Plan Compiler Demo

This public example exercises the M6 Route Plan Compiler:

```powershell
python -m fromcad2cfd fastcfd route-plan demo --output-dir sandbox/output/route_plan_demo
```

The demo first creates a route selection from the public channel-flow CaseSpec,
then compiles a pre-execution plan. It writes:

```text
demo_status.json
f/
s/
p/
    route_plan.json
    route_plan_report.md
    approval_gate.json
    job/
        job.json
        physics_passport.json
        job_mapping.json
```

The compiler does not run the job. Commands are recorded only under the approval
gate for later explicit review.
