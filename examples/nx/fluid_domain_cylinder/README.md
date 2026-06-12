# NX Cylindrical Fluid-Domain Example

This example uses synthetic geometry only. It creates a cylindrical
computational domain and subtracts a centered cylindrical obstacle. It is safe
to share because it does not include private device geometry.

Write the job JSON:

```powershell
fromcad2cfd nx write-fluid-domain-demo-job --project nx_fluid_domain_cylinder_demo --domain-radius-mm 500 --domain-length-mm 1200 --obstacle-radius-mm 10 --obstacle-length-mm 1400
```

Expected coverage:

- outer cylindrical computational domain
- centered cylindrical obstacle
- boolean subtract
- NX `.prt` save
- Parasolid `.x_t` export where supported
- JSON and Markdown reports

Use copied-model inspection plus explicit boolean body selectors before
subtracting private device geometry from a real CFD domain.
