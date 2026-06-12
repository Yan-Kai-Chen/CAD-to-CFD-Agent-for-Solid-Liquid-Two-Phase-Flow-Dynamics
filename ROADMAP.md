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
- [ ] Add small generated synthetic test geometry that can be recreated from code.
- [ ] Add CI-safe tests that do not require installed CAD software.

## v0.4.0 Fluent Meshing Prototype

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
