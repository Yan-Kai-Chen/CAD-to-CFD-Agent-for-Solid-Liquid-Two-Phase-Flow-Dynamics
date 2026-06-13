# Public Rheology Passport Example

This public-safe example validates a shear-thinning power-law material over a
bounded shear-rate range. It does not run a non-Newtonian CFD solver.

```powershell
python -m fromcad2cfd fastcfd run-rheology-benchmark --case-file examples\fastcfd\rheology_power_law_passport\rheology_case.json --output-dir 05_projects\rheology_power_law_passport\reports --format json
```
