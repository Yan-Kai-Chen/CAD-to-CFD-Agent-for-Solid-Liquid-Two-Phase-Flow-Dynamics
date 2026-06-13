# Public VOF Physics Passport Example

This folder contains a public-safe VOF setup-validation example. It does not
contain private geometry or Fluent case/data files.

Run:

```powershell
python -m fromcad2cfd fastcfd validate-vof --case-file examples\fastcfd\vof_dambreak2d_passport\vof_case.json --format json
```

The command writes a VOF physics passport, Fluent setup hints, a Markdown
report, and a status JSON file. It validates two-phase setup readiness only; it
does not run a VOF solver.
