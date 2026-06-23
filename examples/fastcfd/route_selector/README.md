# Route Selector Demo

This public example exercises the M5 Route Selector:

```powershell
python -m fromcad2cfd fastcfd route-selector demo --output-dir sandbox/output/route_selector_demo
```

The command builds a Flow Pack from the public CaseSpec v3 channel-flow example
and writes:

```text
demo_status.json
f/
s/
    route_selection.json
    route_selection_report.md
    route_catalog.json
```

The selector recommends a next controlled route. It does not run that route.
