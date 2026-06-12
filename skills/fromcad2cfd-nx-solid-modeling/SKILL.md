---
name: fromcad2cfd-nx-solid-modeling
description: Controlled Siemens NX solid modeling workflows for FromCAD2CFD. Use when creating or modifying NX primitive bodies, flow-domain solids, datum-aligned cylinders or boxes, body transforms, boolean unite/subtract/intersect, fillet, chamfer, draft, shell, thicken, revolve, sweep, loft, or other CFD-oriented solid modeling operations through approved NXOpen journals or MCP tools.
---

# FromCAD2CFD NX Solid Modeling

Use this skill to plan and execute controlled NX solid modeling operations for CFD geometry preparation.

## Mandatory Rules

- Never modify original input geometry in place.
- Use test geometry before applying a new operation to real models.
- Copy real inputs to an output workspace before editing.
- Use millimeters as the operation-level unit unless a job explicitly states otherwise.
- Use timestamped output filenames.
- Prefer `.prt` plus `.x_t` as primary NX outputs.
- Treat STEP as optional unless the user explicitly requires it.
- Write JSON and Markdown reports for every executed operation.
- Stop when the target body, tool body, edge, face, feature, or expression cannot be uniquely identified.
- Stop when rebuild, update, boolean, or export validation fails.
- Do not expose arbitrary Python, arbitrary journals, or raw NXOpen execution through an agent-facing tool.

## Workflow

1. Run NX preflight and confirm `run_journal.exe`.
2. Define an operation contract before writing or running a journal.
3. Use short runtime paths when NX path-length limits are likely.
4. Generate a controlled job JSON inside an ignored project runtime folder.
5. Run only a known project journal or MCP tool that maps to the contract.
6. Validate body count, bounding box, units, and export artifacts.
7. Save `.prt`, export `.x_t`, and write reports.
8. Write project memory after a new operation class succeeds.

For the operation contract schema and acceptance checklist, read `references/solid_operation_contract.md`.
For the bounded implementation status, read `../../docs/nx/basic_modeling_matrix.md`.

## Implemented Entrypoints

Use only these controlled entrypoints for the currently implemented NX solid operations:

- `fromcad2cfd nx write-basic-solid-pack-job`: write the synthetic basic solid-modeling capability-pack job covering block, sphere, cone, boolean unite, boolean intersect, and copy-translate.
- `fromcad2cfd nx write-edge-wall-trim-pack-job`: write the synthetic edge/wall/trim/import capability-pack job covering edge blend, chamfer, shell, shell-face, controlled tapered frustum, plane cut by cutter, Parasolid export, and Parasolid import-to-`.prt`.
- `fromcad2cfd nx write-transform-profile-pack-job`: write the synthetic transform/profile capability-pack job covering rotate-copy, mirror body, project curve to face, body-plane intersection curve, revolve, sweep-profile-along-path, and through-curves loft.
- `fromcad2cfd nx write-job --recipe boolean-subtract-demo`: write a synthetic cylinder-minus-cylinder smoke job.
- `fromcad2cfd nx write-boolean-subtract-job --input-file <copied-or-source-prt> --target-body-index <n> --tool-body-indices <n[,n]>`: write a copied-model solid-body subtract job.
- `fromcad2cfd nx write-plane-cut-body-job --input-file <source-prt> --body-index <n> --plane-axis <x|y|z> --plane-offset-mm <value> --remove-side <positive|negative>`: write a copied-model axis-aligned plane-cut job.
- `fromcad2cfd nx write-import-parasolid-job --input-file <source-x_t-or-x_b>`: write a controlled Parasolid import-to-`.prt` job.
- `src/fromcad2cfd_nx/journals/create_basic_solid_pack_demo.py`: execute the synthetic basic solid pack smoke job.
- `src/fromcad2cfd_nx/journals/create_edge_wall_trim_pack_demo.py`: execute the synthetic edge/wall/trim/import smoke job.
- `src/fromcad2cfd_nx/journals/create_transform_profile_pack_demo.py`: execute the synthetic transform/profile smoke job.
- `src/fromcad2cfd_nx/journals/create_boolean_subtract_demo.py`: execute the synthetic boolean subtract smoke job.
- `src/fromcad2cfd_nx/journals/boolean_subtract_bodies.py`: copy an input `.prt`, select target/tool solid bodies by explicit 1-based body index, subtract tools from target, save `.prt`, export `.x_t`, and write reports.
- `src/fromcad2cfd_nx/journals/plane_cut_body.py`: copy an input `.prt`, select one solid body by explicit 1-based body index, remove one side of an x/y/z plane with a generated cutter, save `.prt`, export `.x_t`, and write reports.
- `src/fromcad2cfd_nx/journals/import_parasolid.py`: import `.x_t` or `.x_b` into a new controlled `.prt`, verify imported bodies, re-export `.x_t`, and write reports.

Use `work_part.Features.CreateSubtractFeature(target_body, retain_target, tool_bodies, retain_tools, True)` for NX 12 boolean subtract. Do not use `CreateBooleanBuilder(None)` or `CreateBooleanBuilder(NXOpen.Features.Feature.Null)` for this path; both were rejected during local NX 12 probing.

Use these verified NX 12 primitive and transform patterns when extending controlled journals:

- Block: `CreateBlockFeatureBuilder(NXOpen.Features.Feature.Null)` with `SetOriginAndLengths(...)`.
- Sphere: `CreateSphereBuilder(NXOpen.Features.Sphere.Null)`, `builder.Type = NXOpen.Features.SphereBuilder.Types.CenterPointAndDiameter`, `builder.CenterPoint = point`.
- Cone: `CreateConeBuilder(NXOpen.Features.Cone.Null)`, `builder.Type = NXOpen.Features.ConeBuilder.Types.DiametersAndHeight`, `builder.Axis = axis`.
- Unite/intersect: `CreateUniteFeature(...)` and `CreateIntersectFeature(...)` with explicit body references.
- Copy-translate: `CreateMoveObjectBuilder(NXOpen.Features.MoveObject.Null)`, `MoveObjectResultOptions.CopyOriginal`, `ModlMotion.Options.DeltaXyz`.
- Edge blend: `CreateEdgeBlendBuilder(NXOpen.Features.Feature.Null)` and `AddChainset(...)`.
- Chamfer: `CreateChamferBuilder(NXOpen.Features.Feature.Null)` with `OffsetAndAngle`, `EdgesAlongFaces`, and `SmartCollector`.
- Shell: `CreateShellBuilder(NXOpen.Features.Feature.Null)` with explicit `Body`, `SetDefaultThickness(...)`, and `RemovedFacesCollector`.
- Shell-face: `CreateShellFaceBuilder(NXOpen.Features.ShellFace.Null)` with exact face rules and `Thickness`.
- Controlled taper: use `CreateConeBuilder(NXOpen.Features.Cone.Null)` with different base and top diameters before exposing true DraftBody operations.
- Plane cut: create a half-space-like cutter block on one side of an x/y/z plane and subtract it from the selected target body. The cut plane must pass through the target body interior; contact-only or tangent cutter placement can fail with `Tool body completely outside target body`.
- Parasolid import: `work_part.ImportManager.CreateParasolidImporter()`, set `FileName`, commit, save `.prt`, and verify body count.
- Rotate-copy: `CreateMoveObjectBuilder(NXOpen.Features.MoveObject.Null)` with `MoveObjectResultOptions.CopyOriginal`, `ModlMotion.Options.Angle`, and an explicit angular axis.
- Mirror body: create a datum plane with `DatumPlaneBuilder.CommitFeature()`, extract the committed datum entity with `GetEntities()`, then set `MirrorBodyBuilder.Plane`.
- Project curve: use `NXOpen.UF.CurveProj_Struct`, initialize with `UFSession.Curve.InitProjCurvesData(...)`, set projection vector and target face tags, then call `CreateProjCurves(...)`.
- Intersection curve: create an explicit datum plane and call `UFSession.Curve.CreateIntObject(...)` with body and datum tags.
- Revolve: use `UFSession.Modl.CreateRevolution(...)` with a closed profile and explicit axis point/direction.
- Sweep-profile-along-path: use the validated NX 12 `UFSession.Modl.CreateExtrusionPath(...)` route before exposing arbitrary swept-section selector workflows.
- Through-curves loft: use `CreateThroughCurvesBuilder(...)`, add each closed section through `SectionsList.Append(section)`, and validate the expected sheet or solid state.

The copied-model boolean and plane-cut paths currently require `.prt` input. If the user provides `.x_t`, first run a controlled import-to-`.prt` conversion rather than editing the Parasolid directly.

## Operation Priority

Implement and test operations in this order:

1. Primitive bodies: cylinder, block, sphere, cone. Current status: cylinder and the basic solid pack are implemented.
2. Body transforms: translate, rotate, mirror, copy. Current status: copy-translate is implemented in the basic solid pack; rotate-copy and mirror are implemented in the synthetic transform/profile pack; copied-model transform selectors still require inspection-backed contracts.
3. Boolean operations: subtract, unite, intersect. Current status: subtract is implemented for synthetic and copied-model workflows; unite and intersect are implemented in the basic solid pack.
4. CFD domain construction: outer domain minus device body.
5. Edge operations: fillet and chamfer. Current status: synthetic edge blend and chamfer are implemented in the edge/wall/trim/import pack; copied-model edge selectors still require inspection-backed contracts.
6. Wall/thickness operations: shell, thicken, offset-solid workflows. Current status: thicken is implemented for selected faces; shell and shell-face are implemented in the synthetic edge/wall/trim/import pack.
7. Draft and taper operations. Current status: controlled tapered frustum is implemented; true DraftBody is not agent-facing because local probing showed selector-sensitive failures.
8. Sweep, revolve, and loft operations. Current status: revolve, sweep-profile-along-path, and through-curves loft are implemented in the synthetic transform/profile pack; real-model section/guide selectors still require separate contracts.

## Validation

Accept an operation only when:

- The expected number of solid bodies exists.
- The output body is a solid body when a solid is required.
- Dimensions match the requested values within the project tolerance.
- `.prt` exists and is non-empty.
- `.x_t` exists and is non-empty.
- The report records input paths, output paths, parameters, body count, and errors.

Reject or mark partial when:

- The geometry updates but export fails.
- A boolean produces extra bodies or deletes the target unexpectedly.
- A face or edge selector matches more than one entity.
- NX reports success but the exported file is missing or empty.
