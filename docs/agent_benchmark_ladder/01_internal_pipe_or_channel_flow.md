# Benchmark 1: Internal Pipe Or Channel Flow

Status: `partial`

## Purpose

Validate the basic Agent/FastFluent CFD workflow for inlet, outlet, wall, pressure
drop, and velocity-profile evidence.

## Planned QoIs

- Pressure drop.
- Mean velocity.
- Cross-section or centerline velocity profile.
- Mass-balance residual.
- Mesh/time-step sensitivity label.

## Likely Reusable Assets

- `examples/fastcfd/channel2d_scene`
- `examples/unstructured/channel2d.msh`
- existing unstructured channel validation utilities

## Missing Work

- Package a clean benchmark manifest.
- Add benchmark-specific output table.
- Add a small figure or profile plot.
- Add public command examples.

## Paper Role

General capability benchmark, likely concise main-text table plus supplement.
