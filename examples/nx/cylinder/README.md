# NX Cylinder Job

This example is a synthetic job payload for controlled NXOpen journal execution.
It does not contain private geometry and does not run NX by itself.

```powershell
fromcad2cfd nx write-job --recipe cylinder --radius-mm 10 --height-mm 20
```

Generated NX `.prt`, Parasolid, and report files should stay under ignored
runtime folders such as `05_projects/` or `sandbox/output/`.
