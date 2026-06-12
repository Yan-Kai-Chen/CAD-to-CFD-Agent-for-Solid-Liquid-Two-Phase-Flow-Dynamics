# Siemens NX Examples

These examples are public, synthetic, and safe to share. They do not include
private CAD, STL, Parasolid, NX `.prt`, Fluent case/data, or generated runtime
outputs.

Use them as references for job payload structure and command shape. Actual NX
execution requires a local Siemens NX installation and the controlled
`run_journal.exe` route described in `docs/nx/quickstart.md`.

## Examples

- `cylinder/`: minimal synthetic cylinder job payload.
- `plate_with_hole/`: backend-neutral plate-with-hole job payload template.
- `basic_solid_pack/`: synthetic NX solid-modeling capability pack.
- `reverse_modeling_template/`: public reverse-modeling command templates using
  placeholder input paths only.

## Private Geometry Rule

Place private geometry only in ignored local folders such as:

```text
sandbox/input/
05_projects/
06_logs/
```

Do not commit real `.stl`, `.prt`, `.x_t`, `.x_b`, `.step`, `.stp`, Fluent case
files, or generated reports from private geometry.
