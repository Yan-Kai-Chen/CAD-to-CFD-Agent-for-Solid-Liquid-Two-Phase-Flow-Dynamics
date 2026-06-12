# NX Solid Operation Contract

Use this contract before implementing or running a controlled NX solid modeling operation.

## Required Job Fields

- `schema_version`: project job schema identifier.
- `operation`: controlled operation name.
- `input_file`: optional copied input model path.
- `output_dir`: output directory inside an ignored runtime project folder.
- `model_name`: safe ASCII model stem.
- `units`: default `mm`.
- `parameters`: operation-specific numeric values.
- `target_selector`: exact body, face, edge, feature, or expression selector when editing existing geometry.
- `tool_selector`: exact selector for boolean tool geometry when needed.
- `expected_outputs`: required artifacts, normally `.prt` and `.x_t`.
- `expected_body_count`: expected body count after update.
- `validation`: dimensions, bounding box, volume, or topology checks.

## Operation Families

### Primitive Bodies

Supported first:

- `create_cylinder`
- `create_block`
- `create_sphere`
- `create_cone`

Current implementation:

- `create_cylinder` is available as an individual synthetic journal.
- `create_basic_solid_pack_demo` validates block, sphere, cone, boolean unite, boolean intersect, and copy-translate in one bounded synthetic pack.
- `create_edge_wall_trim_pack_demo` validates edge blend, chamfer, shell, shell-face, controlled tapered frustum, plane cut by cutter, Parasolid export, and Parasolid import-to-`.prt` in one bounded synthetic pack.

Acceptance:

- One solid body unless the job explicitly requests multiple bodies.
- Bounding box matches requested dimensions.
- Body is centered or placed according to explicit origin and axis parameters.

### Body Transforms

Supported first:

- `translate_body`
- `rotate_body`
- `mirror_body`
- `copy_body`

Current implementation:

- Copy-translate is validated only in `create_basic_solid_pack_demo`.
- Rotate-copy and mirror body are validated in `create_transform_profile_pack_demo`.
- Copied-model transform workflows still require explicit body selector contracts before use on real models.

Acceptance:

- Transform matrix or axis-angle is recorded.
- Body count matches copy or move intent.
- Original body is preserved only when the operation requests a copy.

### Boolean Operations

Supported first:

- `boolean_subtract`
- `boolean_unite`
- `boolean_intersect`

Current implementation:

- Synthetic subtract and copied-model subtract are available.
- Unite and intersect are validated in `create_basic_solid_pack_demo` and should be generalized only through a controlled selector schema.
- Axis-aligned plane cutting is available through `plane_cut_body`, which generates a cutter body and subtracts it from one selected solid body.

Acceptance:

- Target and tool bodies are selected uniquely.
- Tool body deletion or preservation is explicit.
- Output body count is verified.
- For CFD fluid-domain creation, the accepted pattern is `outer_domain - device_body`.

### Edge and Wall Operations

Supported after booleans:

- `fillet_edges`
- `chamfer_edges`
- `draft_faces`
- `shell_body`
- `thicken_body`
- `plane_cut_body`
- `import_parasolid`

Current implementation:

- Copied-model selected-face thicken is available.
- Synthetic edge blend, chamfer, shell, shell-face, tapered frustum, and plane cut are available in `create_edge_wall_trim_pack_demo`.
- Copied-model plane cut is available for axis-aligned x/y/z cuts through an explicit 1-based solid body selector.
- Parasolid import-to-`.prt` is available for `.x_t` and `.x_b` files.
- True DraftBody is not agent-facing because local probing showed selector-sensitive failures.

Acceptance:

- Edge or face selectors are exact and auditable.
- Radius, offset, angle, and thickness are positive where required.
- Failed or partial feature creation stops the workflow.
- Plane-cut side removal is explicit: `positive` or `negative`.
- Plane-cut cutter placement must pass through the target body interior; tangent or contact-only placement can fail as outside-target.
- Parasolid import validates that at least one body exists before accepting the result.

### Revolve, Sweep, and Loft

Supported after primitive and boolean smoke tests:

- `revolve_profile`
- `sweep_profile`
- `loft_profiles`

Current implementation:

- `create_transform_profile_pack_demo` validates a synthetic revolve profile, sweep-profile-along-path via the NX 12 UF extrusion-path route, and through-curves loft.
- The validated through-curves loft output is a sheet body.
- Real-model revolve, sweep, and loft tools still require explicit section, guide, axis, and output solid/sheet contracts.

Acceptance:

- Sketch/profile references are unique.
- Guide curves and section curves are validated.
- Resulting solid/sheet state matches the requested operation.

### Derived Curves

Supported first:

- `project_curve_to_face`
- `intersection_curve_body_plane`

Current implementation:

- `create_transform_profile_pack_demo` validates project-curve-to-face with an explicit projection vector and explicit target face.
- `create_transform_profile_pack_demo` validates body-plane intersection curve creation with an explicit datum plane.
- User-specified derived-curve workflows on imported models require audited body, face, curve, and datum selectors.

Acceptance:

- Source curves and target faces or bodies are selected uniquely.
- Projection direction or intersection datum is explicit.
- Resulting curve feature creation is recorded in the JSON and Markdown reports.

## Stop Conditions

Stop before execution when:

- The selector matches zero or multiple entities.
- Units are missing for dimensional parameters.
- The requested operation would overwrite an existing output.
- The user asks to run a new operation class on a real model before a test smoke case exists.

Stop after execution when:

- NX update returns an error.
- The expected body count is wrong.
- The export artifact is missing or empty.
- A boolean removes the target body unexpectedly.
