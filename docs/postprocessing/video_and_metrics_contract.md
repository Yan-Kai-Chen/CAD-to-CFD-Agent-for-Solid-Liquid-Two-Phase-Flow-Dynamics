# Fluent Video And Metrics Contract

The first public implementation writes video frame plans instead of rendering
videos directly.

Frame plans include:

- source autosave directory;
- selected field;
- solver time step;
- physical time interval;
- data file path per frame;
- timestamp label per frame.

Timestamp labels are required for transient videos because playback time is not
simulation time.

Surface metrics:

- pressure: normal fluid-load proxy;
- wall shear: tangential fluid-load proxy;
- wall-adjacent temperature: fluid-side thermal exposure;
- solid structural stress: out of scope without structural or FSI handoff.
