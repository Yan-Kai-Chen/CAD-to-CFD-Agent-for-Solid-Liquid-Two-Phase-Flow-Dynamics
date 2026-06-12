# NX Basic Solid Pack Example

This example uses synthetic geometry only. It is intended to validate the NX
controlled-journal route without touching private CAD.

Write the job JSON:

```powershell
fromcad2cfd nx write-basic-solid-pack-job --project nx_basic_solid_pack_demo
```

Run the generated job through the controlled journal runner on a machine with
Siemens NX installed:

```powershell
fromcad2cfd nx prepare-journal-command --job-file 05_projects\nx_basic_solid_pack_demo\input\nx_basic_solid_pack_demo_job.json
```

Expected coverage:

- block
- sphere
- cone
- boolean unite
- boolean intersect
- copy-translate
- NX `.prt` save
- Parasolid `.x_t` export where supported
- JSON and Markdown reports

Generated files must remain under ignored runtime folders.
