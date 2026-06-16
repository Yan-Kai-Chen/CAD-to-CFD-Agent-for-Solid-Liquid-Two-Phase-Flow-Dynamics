# Fluent Resume And Monitoring

Public resume plans use:

```text
fromcad2cfd_fluent_solver_resume_plan_v1
```

Guardrails:

- resume from a complete checkpoint;
- reject suspiciously small data files when expected size is known;
- do not run standard initialization;
- set adaptive `total_time` to the absolute target flow time;
- keep global and wall monitor contracts active after resume.

Required global monitor file:

```text
monitors/global_monitors.out
```

Required wall monitor file:

```text
monitors/wall_exposure_indicators.out
```

Wall pressure is a normal fluid-load proxy. Wall shear is a tangential
fluid-load proxy. Solid structural stress requires a separate structural or FSI
workflow.
