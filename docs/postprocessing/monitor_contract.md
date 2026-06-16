# Fluent Monitor Contract

The public postprocessing module expects Fluent report files with numeric rows.
It tolerates Fluent-style quoted header lines.

Global monitor metrics:

- flow time;
- delta time;
- iterations per time step;
- average absolute pressure;
- average, maximum, and minimum temperature;
- maximum velocity;
- average H2O, O2, and N2 mass fraction;
- inlet mass flow rate.

Wall monitor metrics:

- wall average and maximum pressure;
- wall-adjacent temperature;
- wall shear;
- wall heat transfer rate;
- selected outer-wall and model-wall indicators.

Heat removed from fluid is commonly reported as `-wall_heat_transfer_rate`.
