# Benchmark 3: Heated Channel / CHT Toy Case

Status: `partial`

## Purpose

Validate thermal boundary handling and create a bridge toward dewaxing heat
dose, wall heating, and phase-change interpretation.

## Planned QoIs

- Wall heat flux.
- Outlet temperature.
- Heat dose.
- Wall or solid temperature rise.
- Energy-balance residual.

## Likely Reusable Assets

- S6 scalar transport routes.
- Existing thermal/wax handoff logic.
- Dewaxing early heat-dose metrics.

## Missing Work

- Decide whether this is a pure heated-channel case or a minimal conjugate
  heat-transfer toy case.
- Add a public fixture.
- Add thermal QoI tables and a small figure.
- Connect output to Fluent-facing handoff language.

## Paper Role

General thermal capability benchmark and conceptual bridge to dewaxing.
