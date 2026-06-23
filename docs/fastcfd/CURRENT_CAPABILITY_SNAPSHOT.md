# FastFluent Current Capability Snapshot

Snapshot date: 2026-06-23

This document records the M0 audit for expanding FastFluent from a collection
of bounded screening and native-solver utilities into a general, agent-usable
CFD evidence layer. It is intentionally an audit document: no solver code was
modified during M0.

## Post-M0 Status Note

After the M0 audit, the general evidence-engine route advanced through the
shared contract and workflow layers. The current recommended agent entrypoint is
S7:

```powershell
python -m fromcad2cfd fastcfd workflow demo --output-dir sandbox/output/s7_workflow_demo --mode native_advisory
```

S7 connects CaseSpec v3, Flow Pack, Route Selector, Route Plan, Execution Gate,
Controlled Runner, optional S6 native advisory transport evidence, Result Pack,
and `agent_decision.json`. See:

- `fastcfd/WORKFLOW_RUNNER.md`
- `fastcfd/AGENT_WORKFLOW_STATUS_AUDIT.md`

The M0 inventory below remains useful as the baseline audit, but S7 is now the
preferred entrypoint for agent workflow demonstrations.

## Audit Scope

Audited areas:

- `src/fromcad2cfd_fastcfd`
- `src/fromcad2cfd_fastcfd/unstructured`
- `cpp/fastfluent_core`
- `examples/fastcfd`
- `examples/unstructured`
- `docs/fastcfd`
- `tests/unit/test_fastcfd*.py`

Local evidence was generated under:

```text
sandbox/output/fastfluent_capability_snapshot/
```

The local snapshot directory contains:

- `capabilities.json`
- `registry.json`
- `fastcfd_help.txt`
- `ustruct_help.txt`
- `file_inventory.txt`
- `audit_summary.json`
- `cli_commands.txt`
- `test_inventory.txt`

These files are runtime audit outputs and are intentionally under `sandbox`
rather than committed source.

## Current Scale

The audit found the following current public surface:

| Area | Count |
| --- | ---: |
| Top-level `fastcfd` CLI commands | 43 |
| `fastcfd unstructured` CLI commands | 19 |
| Top-level FastCFD Python modules | 39 |
| Unstructured FastFluent Python modules | 23 |
| FastCFD documentation pages | 8 |
| FastCFD example files | 9 |
| Public unstructured example files | 3 |
| FastCFD unit-test files | 22 |
| FastFluent C++ core relevant source/config files | 162 |

## Current Positioning

FastFluent is already more than a placeholder. It currently acts as a bounded
pre-Fluent evidence layer with:

- semantic scene compilation;
- physics passports;
- structured FastFluent backend status and controlled routes;
- unstructured finite-volume evidence routes;
- public benchmark and validation packs;
- practical native heat, scalar, material, source-term, and sweep utilities;
- Fluent setup hints;
- non-executing `solver_plan_patch.json` handoff artifacts.

The current boundary remains correct: FastFluent is not a Fluent replacement.
It should provide screening, native low-cost evidence, parameter ranking, and
handoff artifacts before high-fidelity Fluent work.

## Current Command Surface

The top-level FastCFD CLI currently includes:

- inventory and setup: `capabilities`, `registry`, `preflight`;
- job and scene routes: `write-demo-job`, `run-mock-job`, `validate-job`,
  `write-scene`, `validate-scene`, `compile-scene`;
- controlled structured backend routes: `write-cavity2d-job`,
  `write-channel2d-job`, `write-obstacle2d-job`, `run-fastfluent-job`,
  `run-fastfluent-cavity2d-job`;
- prediction and screening: `predict-from-output`, `screen-parameters`;
- passports and handoff: `write-vof-demo`, `validate-vof`,
  `write-turbulence-demo`, `validate-turbulence`, `write-rheology-demo`,
  `run-rheology-benchmark`, `write-steam-air-demo`,
  `validate-steam-air-condensation`, `write-steam-air-v2-demo`,
  `validate-steam-air-condensation-v2`, `write-solid-liquid-demo`,
  `validate-solid-liquid-suspension`, `write-wax-rheology-demo`,
  `validate-wax-rheology-phase-change`;
- patch and hint compilation: `compile-fluent-hints`,
  `compile-fluent-patch`, `existing-passport-patch-demo`;
- public packs: `steam-air-handoff-demo`, `steam-air-v2-demo`,
  `solid-liquid-handoff-demo`, `wax-rheology-handoff-demo`,
  `horizontal-validation-pack-demo`, `native-simulation-validation-pack-demo`,
  `practical-native-demo-pack`, `practical-native-setup-demo`;
- unstructured routes under `unstructured`;
- the legacy convenience `mock-demo`.

The unstructured subcommands currently include:

- mesh and case gateway: `inspect-mesh`, `write-steady-channel-case`,
  `run-case`;
- scalar and manufactured benchmarks: `solve-diffusion`,
  `solve-tetra-diffusion`, `solve-stokes`, `solve-projection`;
- flow evidence: `solve-flow-benchmark`, `solve-steady-incompressible`,
  `solve-channel-validation`, `solve-channel-convergence`,
  `solve-obstacle-channel`;
- multiphase-lite and turbulence evidence: `solve-vof-lite`,
  `solve-turbulent-channel`, `solve-kepsilon-channel`,
  `solve-kepsilon-pressure-channel`, `solve-sst-channel`,
  `solve-turbulence-ladder`;
- public suite: `run-benchmark-suite`.

## Existing Schema And Contract Assets

Current reusable foundations:

- `schemas.py` defines `FastCFDJob`, `FastCFDScene`, `PhysicsContract`,
  `ResultManifest`, `QoIManifest`, `FlowFingerprint`, `FluentHints`, and a
  lightweight `ClaimLedger`.
- `registry.py` defines the current structured case registry for `cavity2d`,
  `channel2d`, `obstacle2d`, and `dambreak2d`.
- `native_simulation_artifacts.py` defines the S1 native simulation result
  contract.
- `solver_plan_patch.py` defines the non-executing Fluent-facing solver-plan
  patch contract with dangerous-key filtering and allowlisted patch paths.
- `unstructured/case_runner.py` defines an agent-safe unstructured JSON case
  route for `steady_incompressible`.
- `unstructured/quality.py` defines mesh manifest and mesh-quality contracts.
- `unstructured/boundary.py` defines a reusable boundary-condition validator
  for unstructured routes.

These are strong foundations for the next architecture step, but they are not
yet one shared general CaseSpec/EvidenceBundle system.

## Native Evidence Coverage

Current native evidence includes:

- structured FastFluent route status for controlled cavity, channel, and
  obstacle cases;
- public unstructured mesh inspection and finite-volume geometry generation;
- 2D scalar diffusion with manufactured solutions;
- 3D tetra scalar diffusion smoke evidence;
- manufactured Stokes benchmark;
- pressure-correction projection benchmark;
- controlled steady incompressible pressure-correction route;
- channel validation and convergence evidence;
- obstacle-channel evidence with named zones;
- VOF-lite alpha transport;
- algebraic eddy-viscosity turbulent channel;
- standard k-epsilon turbulent channel;
- pressure-corrected k-epsilon turbulent channel;
- Menter SST turbulent channel;
- turbulence ladder comparison;
- public unstructured benchmark suite.

This is a meaningful native evidence stack. The remaining issue is not the
absence of physics evidence; it is the lack of one canonical bundle layout that
all routes write.

## Physics Passport And Handoff Coverage

Current passport and handoff coverage includes:

- VOF setup readiness and Fluent VOF hints;
- turbulence setup readiness and Fluent turbulence hints;
- rheology benchmark and material hints;
- steam-air condensation readiness, including v2 heat/mass-transfer estimates;
- solid-liquid suspension model-selection evidence;
- wax rheology and phase-change readiness evidence;
- evidence-backed Fluent setup hints;
- evidence-backed, non-executing solver-plan patch generation.

These routes correctly avoid launching Fluent, writing raw Fluent TUI, emitting
UDF code, or editing Fluent case files.

## C++ Core Coverage

The public C++ core is present under `cpp/fastfluent_core`. It contains:

- LBM source layers;
- CA/free-surface/non-Newtonian-related source files;
- public examples such as cavity, Couette, dam break, open boundary, and pipe
  injection;
- benchmark and test sources;
- an integration note explaining its role as the default source root for the
  Python agent layer.

The C++ core is not yet exposed through a general CaseSpec v3 route. Current
Python wrappers use bounded structured templates rather than arbitrary C++
case generation.

## Public Examples

Current public examples are safe and small:

- `examples/fastcfd/mock_cavity2d/job.json`
- `examples/fastcfd/channel2d_scene/scene.json`
- `examples/fastcfd/obstacle2d_scene/scene.json`
- `examples/fastcfd/vof_dambreak2d_passport/`
- `examples/fastcfd/turbulence_channel2d_passport/`
- `examples/fastcfd/rheology_power_law_passport/`
- `examples/unstructured/channel2d.msh`
- `examples/unstructured/unit_square_4x4.msh`

No private CAD, private mesh, Fluent case/data, or licensed-tool artifact is
required for these examples.

## Current Redundancy And Fragmentation

The audit found several redundancies that should be addressed after M0:

1. Multiple input schemas exist in parallel:
   `FastCFDJob`, `FastCFDScene`, passport-specific case schemas,
   unstructured case JSON, practical native demo case templates, and
   solver-plan patch input artifacts. These need a common CaseSpec v3 facade.

2. Output layouts are inconsistent across routes:
   some routes write `qoi.json`, some write `*_qoi.json`, some write
   `simulation_result.json`, and handoff routes write passport-specific
   reports. These need a canonical EvidenceBundle v3 index.

3. Boundary contracts are duplicated:
   structured registry boundaries, unstructured boundary contracts, practical
   setup boundary contracts, and Fluent hints use related concepts but different
   shapes.

4. Material contracts are fragmented:
   rheology, wax, steam-air, solid-liquid, and practical material utilities
   each hold local material assumptions. They need a shared material model
   contract layer before more physics packs are added.

5. Mesh contracts are partly unified only inside the unstructured route:
   `mesh_manifest.json`, `mesh_quality.json`, and `fv_geometry.json` are good
   foundations, but structured and practical setup routes do not yet report
   through the same mesh gateway vocabulary.

6. The CLI is broad but flat:
   many mature commands live at the top level. This is usable today, but future
   public CLI should group stable functionality under `case`, `evidence`,
   `mesh`, `flow`, `physics`, `sweep`, `handoff`, and `agent`.

7. Documentation mixes stable user guides with progress logs:
   `docs/fastcfd/quickstart.md` and `docs/fastcfd/unstructured_mesh_gateway.md`
   are useful stable docs, while many H/S progress and delivery files are
   historical implementation records. Public docs should eventually separate
   stable docs from development history.

## Missing General Abstractions

The next general architecture needs these missing abstractions:

- `CaseSpec v3`: one public-safe input model for geometry, mesh, materials,
  boundary conditions, numerics, physics intent, QoI targets, claim level, and
  handoff options.
- `EvidenceBundle v3`: one output layout for validation, mesh, boundary,
  material, numerics, residuals, fields, QoI, Fluent hints, solver-plan patch,
  claim ledger, limitations, and report.
- `ClaimLedger`: a stronger common ledger with supported claims, unsupported
  claims, required next steps, and claim-level mapping.
- `Unit and dimension checks`: a shared validator for all physics packs.
- `BoundaryContract`: one reusable boundary-condition contract across
  structured, unstructured, practical native, and Fluent-handoff routes.
- `MaterialContract`: one shared material model contract for constant,
  temperature-dependent, non-Newtonian, porous, particle, and two-phase inputs.
- `MeshGateway v2`: one mesh manifest and quality-gate vocabulary for both
  structured and unstructured inputs.
- `Agent tool surface`: stable bounded tools that call validated CaseSpec and
  EvidenceBundle routes instead of exposing a broad internal CLI directly.

## Recommended M1-M3 Implementation Plan

### M1: CaseSpec v3 And EvidenceBundle v3

Create:

- `src/fromcad2cfd_fastcfd/core/case_spec.py`
- `src/fromcad2cfd_fastcfd/core/evidence_bundle.py`
- `src/fromcad2cfd_fastcfd/core/claim_ledger.py`
- `docs/fastcfd/CASESPEC_V3.md`
- `docs/fastcfd/EVIDENCE_BUNDLE_V3.md`
- `examples/fastcfd/casespec_v3/channel_flow_case.json`
- `tests/unit/test_fastcfd_casespec_v3.py`
- `tests/unit/test_fastcfd_evidence_bundle_v3.py`

M1 should be additive. It should wrap and normalize existing artifacts rather
than deleting existing commands immediately.

Acceptance:

```powershell
python -m fromcad2cfd fastcfd validate-case examples/fastcfd/casespec_v3/channel_flow_case.json
python -m fromcad2cfd fastcfd explain-case examples/fastcfd/casespec_v3/channel_flow_case.json --format markdown
python -m fromcad2cfd fastcfd evidence validate-bundle sandbox/output/example_case
python -m pytest tests/unit/test_fastcfd_casespec_v3.py tests/unit/test_fastcfd_evidence_bundle_v3.py
```

### M2: Unit, Boundary, And Material Contracts

Create or consolidate:

- `src/fromcad2cfd_fastcfd/core/units.py`
- `src/fromcad2cfd_fastcfd/boundary/boundary_contract.py`
- `src/fromcad2cfd_fastcfd/boundary/boundary_validator.py`
- `src/fromcad2cfd_fastcfd/materials/material_contract.py`
- `src/fromcad2cfd_fastcfd/materials/material_library.py`
- `docs/fastcfd/BOUNDARY_AND_MATERIAL_CONTRACTS.md`

M2 should reuse the current unstructured boundary contract and current
passport/material code where possible.

Acceptance:

```powershell
python -m fromcad2cfd fastcfd validate-case examples/fastcfd/casespec_v3/channel_flow_case.json
python -m pytest tests/unit/test_fastcfd_units.py tests/unit/test_fastcfd_boundary_contract.py tests/unit/test_fastcfd_material_contract.py
```

### M3: Mesh Gateway v2

Create or consolidate:

- `src/fromcad2cfd_fastcfd/mesh/mesh_manifest.py`
- `src/fromcad2cfd_fastcfd/mesh/mesh_quality.py`
- `src/fromcad2cfd_fastcfd/mesh/structured_grid.py`
- `src/fromcad2cfd_fastcfd/mesh/gmsh_reader.py`
- `src/fromcad2cfd_fastcfd/mesh/fv_geometry.py`
- `docs/fastcfd/MESH_GATEWAY_V2.md`

M3 should preserve existing `fastcfd unstructured` commands while adding a
common mesh gateway API.

Acceptance:

```powershell
python -m fromcad2cfd fastcfd mesh inspect examples/unstructured/channel2d.msh --output-dir sandbox/output/mesh_inspect
python -m fromcad2cfd fastcfd mesh generate-structured-demo --output-dir sandbox/output/structured_mesh_demo
python -m pytest tests/unit/test_fastcfd_mesh_gateway_v2.py
```

## Refactor Policy

The repository can be refactored, but the next refactor should be controlled:

- keep existing public commands working unless a migration note is added;
- add the new `core/`, `boundary/`, `materials/`, and `mesh/` abstractions
  before moving old modules;
- avoid large directory moves in the same commit as behavior changes;
- keep all examples public-safe and license-free;
- do not call Fluent, PyFluent, SolidWorks, NX, or HyperMesh from FastFluent
  tests;
- keep every solver claim bounded by a claim ledger or limitations artifact.

## M0 Conclusion

FastFluent already has substantial engineering value. The strongest current
areas are:

- unstructured mesh and finite-volume evidence;
- turbulence ladder and bounded turbulence-channel evidence;
- practical native mini-computations;
- physics passports;
- evidence-backed Fluent handoff artifacts;
- public-safe examples and tests.

The main weakness is architectural cohesion. The next work should not add more
standalone physics first. It should first introduce CaseSpec v3, EvidenceBundle
v3, shared contracts, and Mesh Gateway v2 so that all existing and future
physics packs become agent-callable through one stable interface.
