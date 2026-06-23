# FastFluent Flow Pack Adapter

Flow Pack v1 is the M4 integration layer for the general FastFluent workflow.
It combines the setup contracts introduced in M1-M3 into one reviewable package:

- CaseSpec v3 validation
- boundary-condition contract validation
- material contract validation
- Mesh Gateway v2 evidence
- setup-only readiness gate
- agent next-action list
- optional setup-only EvidenceBundle v3 export

Flow Pack is intentionally setup-only. It does not run FastFluent, Fluent,
PyFluent, UDF code, or arbitrary scripts.

## Why It Exists

Earlier FastFluent routes produced useful artifacts, but the setup evidence was
spread across separate commands. Flow Pack v1 gives agents a single entrypoint
before choosing a controlled native FastFluent route or a later Fluent setup
route.

## Public Demo

```powershell
python -m fromcad2cfd fastcfd flow-pack build-demo --output-dir sandbox/output/flow_pack_demo
python -m fromcad2cfd fastcfd flow-pack validate sandbox/output/flow_pack_demo --format markdown
python -m fromcad2cfd fastcfd flow-pack export-evidence-bundle sandbox/output/flow_pack_demo --output-dir sandbox/output/flow_pack_demo_bundle
```

The demo uses `examples/fastcfd/casespec_v3/channel_flow_case.json` and a
generated public structured mesh. It contains no private geometry or solver
output.

## Main Artifacts

```text
flow_pack.json
flow_pack_report.md
flow_pack_status.json
case.json
case_validation.json
case_summary.md
boundary_contract.json
boundary_validation.md
material_contract.json
material_model_report.md
mesh_manifest.json
mesh_quality.json
fv_geometry.json
mesh.vtu
mesh_status.json
readiness_gate.json
agent_next_actions.json
fluent_hints.json
```

## EvidenceBundle Export

The export command writes a setup-only EvidenceBundle v3. Its `qoi.json` records
that solver QoI is not computed, and its claim ledger is downgraded to
`setup_only` even when the input CaseSpec requests a stronger downstream claim.

This prevents setup readiness from being confused with physics validation.

## Readiness Semantics

- `success`: CaseSpec, boundary, material, and mesh-gateway evidence are present
  and internally consistent enough for solver setup review.
- `partial`: case, boundary, and material contracts may be present, but required
  setup evidence such as mesh-gateway output is incomplete.
- `failed`: at least one fail-closed validation gate failed.

## Current Limitations

- Flow Pack v1 is a setup adapter, not a solver runner.
- It does not decide which turbulence, multiphase, rheology, or thermal model is
  physically sufficient for final CFD.
- It does not edit a Fluent case or launch Fluent.
- External Gmsh meshes are supported through the current Mesh Gateway v2 subset.
