# Monitor Summary Contract

Global monitor columns:

- `flow-time`
- `delta-time`
- `iters-per-timestep`
- volume-average absolute pressure
- volume-average temperature
- maximum and minimum temperature
- maximum velocity
- average H2O, O2, and N2 mass fractions
- inlet mass flow rate

Wall monitor columns:

- all-wall and selected-wall pressure
- wall-adjacent temperature
- wall shear
- wall heat transfer rate

Positive heat removal is reported as `-wall_heat_transfer_rate` when Fluent
uses the wall heat-flux sign convention where heat leaving the fluid is negative.
