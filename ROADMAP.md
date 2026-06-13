# Roadmap

## v0.1.0 SolidWorks Alpha

- [x] SolidWorks COM preflight.
- [x] Create controlled geometry.
- [x] Save SolidWorks part files locally.
- [x] Export STEP.
- [x] Generate Markdown and JSON reports.
- [x] Provide safe editing policy.
- [x] Provide CFD-oriented geometry templates.
- [ ] Publish stable SolidWorks MCP wrapper.

## v0.2.0 CAD Backend Abstraction And NX Controlled Journal Backend

- [x] Define common CAD backend contract.
- [x] Standardize backend-neutral result, recipe, inspection, and export metadata structures.
- [x] Add lightweight backend registry.
- [x] Add Siemens NX controlled-journal backend.
- [x] Add Siemens NX MCP wrapper scaffold with safe high-level tool inventory.
- [x] Add NX documentation and examples.
- [x] Run controlled NXOpen journals through `run_journal.exe`.
- [x] Add NX basic solid, edge/wall/trim/import, transform/profile, and curve/surface capability packs.
- [x] Add a public-safe NX cylindrical CFD fluid-domain construction demo.
- [x] Add copied-model NX inspection, boolean subtract, plane cut, face thicken, and sheet sew job builders.
- [x] Add user-taught NX reverse-modeling workflow: STL-to-convergent, cage-from-facet-body, XOY plane CombineSheets.
- [x] Add manual NX journal capture playbook as a development method for selector-sensitive UI workflows.
- [ ] Rename legacy `xoz` command/file identifiers after downstream compatibility is reviewed.

## v0.3.0 CAD Parameter Editing

- [x] Safe model copy workflow.
- [x] SolidWorks exact dimension modification.
- [x] NX exact expression modification scaffold.
- [ ] Unified backend-neutral parameter edit request.
- [ ] Rebuild validation.
- [ ] STEP export after edit.
- [ ] Old/new value reporting.
- [ ] Real model read-only inspection.

## v0.3.1 Public Examples And Documentation Hardening

- [x] Keep real research devices out of the repository.
- [x] Add synthetic SolidWorks and NX examples.
- [x] Add public NX reverse-modeling workflow templates without private geometry.
- [x] Add small generated synthetic test geometry that can be recreated from code.
- [x] Add CI-safe tests that do not require installed CAD software.

## v0.3.2 Mesh Solidification Candidate Route

- [x] Add copied-input STL inspection and coarse watertightness reporting.
- [x] Add FreeCAD/OpenCascade mesh-to-solid job writing.
- [x] Add FreeCADCmd execution wrapper with blocked diagnostics when unavailable.
- [x] Validate portable FreeCAD 1.1.1 execution through bundled Python.
- [x] Add public synthetic mesh example.
- [ ] Add optional mesh simplification before FreeCAD conversion.
- [ ] Add NX STEP import-to-PRT follow-up wrapper.

## v0.3.3 FastCFD / FastFluent Foundation

- [x] Add `fromcad2cfd_fastcfd` package skeleton and CLI routing.
- [x] Add `FastCFDJob`, `FastCFDScene`, physics contract, QoI, flow fingerprint, Fluent hints, result manifest, and claim ledger schemas.
- [x] Add capability registry and optional FastFluent source/build preflight.
- [x] Add deterministic `cavity2d` mock backend with full artifact contract.
- [x] Add baseline manifest for the internal FastFluent source snapshot.
- [x] Add CI-safe tests that do not require FastFluent to be installed.
- [x] Add first local FastFluent Windows portability patch for native `cavity2d` build.
- [x] Add real controlled `cavity2d` backend.
- [x] Add mandatory physics validator before mock and controlled real runs.
- [x] Add source-of-truth registry for case templates, lattice sets, boundary types, and collision models.
- [x] Add semantic scene validation and scene-to-job compilation for `cavity2d`, `channel2d`, `obstacle2d`, and planned `dambreak2d`.
- [x] Add controlled real FastFluent backend for `channel2d` using the `openboundary2d` example.
- [x] Add controlled generated-source real FastFluent backend for circle/rectangle `obstacle2d`.
- [x] Add field-derived QoI extraction from real FastFluent VTK XML output.
- [x] Add native FastFluent executable run-summary hooks for source-level run facts.
- [x] Add native FastFluent residual-history CSV hooks.
- [x] Add recipe-derived lattice-domain trust summaries.
- [x] Add bounded pilot-decision policy artifacts for Fluent handoff control.
- [ ] Promote native FastFluent entrypoint output from run summary to the full artifact contract.

## v0.4.0 Fluent Meshing Planning Gate And Prototype

- [x] Add FastCFD evidence preflight gate before Fluent Meshing preparation.
- [ ] Import STEP.
- [ ] Geometry cleanup.
- [ ] Named selections.
- [ ] Global mesh controls.
- [ ] Boundary layer controls.
- [ ] Mesh generation.
- [ ] Mesh quality reporting.

## v0.5.0 Fluent Solver Setup Prototype

- [ ] Load mesh.
- [ ] Set physics models.
- [ ] Set materials.
- [ ] Set boundary conditions.
- [ ] Initialize and run.
- [ ] Save case/data.

## v0.6.0 Post-processing Prototype

- [ ] Residual plots.
- [ ] Contours.
- [ ] Streamlines.
- [ ] Force and pressure extraction.
- [ ] Automated report generation.

## v1.0.0 CAD-to-CFD Closed-loop Workflow

- [ ] Geometry creation or modification.
- [ ] Mesh generation.
- [ ] Solver setup.
- [ ] Solve.
- [ ] Post-process.
- [ ] Report.
- [ ] Re-run with changed geometry parameters.
