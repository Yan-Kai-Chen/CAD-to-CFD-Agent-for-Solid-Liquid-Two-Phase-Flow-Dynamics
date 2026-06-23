# FastFluent S6 Unified Transport Coupling Core

S6 provides the shared scalar-transport layer used to connect FastFluent
screening evidence across VOF-lite, temperature, species, particle
concentration, and wax-fraction style setup checks.

It is intentionally a bounded native evidence route. It does not solve coupled
pressure-momentum, turbulence, dynamic mesh, phase-interface reconstruction, or
final Fluent validation.

## Commands

Write an editable public case:

```powershell
python -m fromcad2cfd fastcfd transport write-demo --case-file sandbox/output/s6_transport_case.json --quantity alpha
```

Validate a case:

```powershell
python -m fromcad2cfd fastcfd transport validate sandbox/output/s6_transport_case.json
```

Run a case:

```powershell
python -m fromcad2cfd fastcfd transport run sandbox/output/s6_transport_case.json --output-dir sandbox/output/s6_transport_run
```

Run a one-command public demo:

```powershell
python -m fromcad2cfd fastcfd transport demo --output-dir sandbox/output/s6_transport_alpha --quantity alpha
python -m fromcad2cfd fastcfd transport demo --output-dir sandbox/output/s6_transport_temperature --quantity temperature
```

Compile the native result into the unified Result Pack layer:

```powershell
python -m fromcad2cfd fastcfd result-pack compile-native sandbox/output/s6_transport_alpha/status.json --output-dir sandbox/output/s6_transport_alpha_pack
```

## Case Surface

The S6 case schema is `fastfluent_transport_case_v1`.

Core fields:

- `field`: scalar name, quantity, units, and optional bounds.
- `velocity_m_s`: advective velocity vector.
- `diffusivity_m2_s`: scalar diffusivity.
- `initial_condition`: `uniform`, `left_column`, or `linear_x`.
- `boundary_conditions`: currently `fixed_value` and `zero_gradient`.
- `source`: `none`, `constant`, or `linear_relaxation`.
- `material_couplings`: property-range evaluation from the scalar field.
- `acceptance`: Courant, diffusion, balance, and clipping thresholds.

Supported public demo quantities:

- `alpha`
- `temperature`
- `species`
- `particle_concentration`
- `wax_fraction`

## Outputs

A successful run writes:

```text
transport_case.json
mesh_manifest.json
mesh_quality.json
fv_geometry.json
transport_history.csv
transport_qoi.json
material_properties.json
transport_solution.vtu
transport_report.md
status.json
```

The `status.json` file is intentionally compatible with:

```powershell
python -m fromcad2cfd fastcfd result-pack compile-native <status.json> --output-dir <result_pack_dir>
```

## QoI

`transport_qoi.json` records:

- scalar bounds and min/max values;
- initial and final field integrals;
- advective and diffusive boundary flux integrals;
- source contribution;
- absolute and relative balance residual;
- bounded clipping integral;
- maximum Courant number;
- maximum diffusion number;
- material-property coupling ranges;
- Fluent setup hints for screening.

## Boundary

S6 is valid for agent workflow control and low-cost pre-Fluent screening. It is
not final CFD validation and should not be reported as a replacement for Fluent
or reviewed high-fidelity CFD.
