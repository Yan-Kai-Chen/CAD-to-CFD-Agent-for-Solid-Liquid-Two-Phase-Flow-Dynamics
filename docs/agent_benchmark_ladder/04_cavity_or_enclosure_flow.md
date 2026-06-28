# Benchmark 4: Cavity / Enclosure Flow

Status: `partial`

## Purpose

Validate closed-domain recirculating flow behavior and stable bounded-domain
workflow output.

## Planned QoIs

- Vortex center or recirculation proxy.
- Maximum velocity.
- Kinetic-energy trend.
- Stability flag.
- Mesh sensitivity.

## Likely Reusable Assets

- `mock_cavity2d`
- FastFluent cavity route

## Missing Work

- Decide whether this remains a simple cavity benchmark or becomes an enclosure
  natural-convection toy case.
- Package public benchmark output.
- Add figure and table definitions.
- Add tests for the benchmark manifest.

## Paper Role

General capability benchmark, likely supplement or compact main-text table.
