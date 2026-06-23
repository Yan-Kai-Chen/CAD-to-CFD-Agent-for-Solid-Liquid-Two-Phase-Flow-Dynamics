# Flow Pack Demo

This public example builds a setup-only Flow Pack from the CaseSpec v3 channel
case:

```powershell
python -m fromcad2cfd fastcfd flow-pack build-demo --output-dir sandbox/output/flow_pack_demo
python -m fromcad2cfd fastcfd flow-pack validate sandbox/output/flow_pack_demo
python -m fromcad2cfd fastcfd flow-pack export-evidence-bundle sandbox/output/flow_pack_demo --output-dir sandbox/output/flow_pack_demo_bundle
```

The demo generates a structured mesh gateway artifact set and exports a
setup-only EvidenceBundle v3. It is a route-selection and setup-review example,
not a solver result.
