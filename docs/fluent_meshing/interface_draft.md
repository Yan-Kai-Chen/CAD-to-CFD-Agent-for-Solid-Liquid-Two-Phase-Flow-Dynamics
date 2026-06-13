# Fluent Meshing Interface Draft

Implemented planning command:

```text
fromcad2cfd fluent-meshing preflight-gate --fastcfd-output-dir <FastCFD output dir>
```

The preflight gate reads:

- `qoi.json`
- `pilot_decision.json`
- `lattice_domain_summary.json`
- `field_qoi.json`
- `result_manifest.json`

It writes a JSON and Markdown gate report with:

- `passed`, `warning`, or `blocked` status,
- a concrete meshing-preparation decision,
- FastCFD evidence summary,
- gate checks,
- required actions,
- Fluent Meshing planning hints.

It does not launch Fluent, import geometry, generate a mesh, or write case/data
files.

Planned commands:

```text
fromcad2cfd fluent-meshing import-step
fromcad2cfd fluent-meshing generate-mesh
fromcad2cfd fluent-meshing check-quality
```
