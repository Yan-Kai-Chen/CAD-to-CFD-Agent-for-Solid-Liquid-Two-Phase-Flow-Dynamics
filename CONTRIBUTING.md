# Contributing

Contributions are welcome, especially around safe CAD automation, reproducible CFD workflows, and documentation.

## Rules

- Do not commit proprietary CAD, mesh, Fluent case/data, license, or local configuration files.
- Keep examples generic and reproducible.
- Add tests for reusable logic.
- Keep SolidWorks-dependent integration tests isolated from unit tests.
- Prefer high-level safe tool APIs over raw COM or arbitrary code execution.

## Development

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```
