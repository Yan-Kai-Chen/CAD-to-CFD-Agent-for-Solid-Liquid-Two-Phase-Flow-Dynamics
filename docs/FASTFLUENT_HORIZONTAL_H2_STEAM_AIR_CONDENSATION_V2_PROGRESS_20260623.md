# FastFluent Horizontal H2 Steam-Air Condensation v2 Progress Log

Date: 2026-06-23

## Goal

Horizontal H2 upgrades the existing steam-air condensation passport from a
basic readiness gate into a richer engineering evidence module. It remains a
non-executing FastFluent-to-Fluent handoff layer and does not implement Fluent
execution, UDF generation, GPU acceleration, or a full condensation solver.

## Implemented

- Added `src/fromcad2cfd_fastcfd/steam_air_condensation_v2.py`.
- Added v2 schemas:
  - `fromcad2cfd_fastfluent_steam_air_condensation_case_v2`
  - `fromcad2cfd_fastfluent_steam_air_condensation_passport_v2`
  - `fromcad2cfd_fastfluent_steam_air_condensation_fluent_hints_v2`
- Added dimensionless groups:
  - Reynolds number
  - Prandtl number
  - Peclet number
  - Jakob number
  - Stefan number
- Added heat-transfer estimates:
  - Nusselt number
  - HTC
  - heat flux
  - heat-transfer rate
  - correlation metadata and limitations
- Added non-condensable resistance estimates:
  - Schmidt number
  - Sherwood number
  - mass-transfer coefficient
  - mass-transfer resistance
  - low/moderate/high risk classification
- Added source-term checks:
  - `kg/(m^3*s)` mass-source dimension check
  - `W/m^3` energy-source dimension check
  - latent-heat consistency
  - sign convention
  - source stiffness level
- Added expanded solver-plan patch recommendations for:
  - `/physics/energy`
  - `/physics/species_transport`
  - `/physics/turbulence`
  - `/transient`
  - `/source_terms`
  - `/monitors`
  - `/postprocessing`
- Added public CLI routes:

```powershell
python -m fromcad2cfd fastcfd write-steam-air-v2-demo --output-dir sandbox/output/steam_air_v2_case
python -m fromcad2cfd fastcfd validate-steam-air-condensation-v2 --case sandbox/output/steam_air_v2_case/steam_air_condensation_case_v2.json --output-dir sandbox/output/steam_air_v2_passport
python -m fromcad2cfd fastcfd steam-air-v2-demo --output-dir sandbox/output/steam_air_v2_demo --format markdown
```

## Demo Verification

Command:

```powershell
python -m fromcad2cfd fastcfd steam-air-v2-demo --output-dir sandbox/output/steam_air_v2_demo --format markdown
```

Result:

```text
Status: success
Patch status: warn
Patch count: 27
Evidence count: 11
```

Key computed quantities:

| Quantity | Value |
| --- | ---: |
| Reynolds number | 142500.0 |
| Flow regime | turbulent |
| Prandtl number | 0.8 |
| Peclet number | 114000.0 |
| Jakob number | 0.06981081081081078 |
| Stefan number | 0.06981081081081078 |
| Nusselt number | 279.26449384896796 |
| HTC | 234.58217483313308 W/(m^2*K) |
| Heat flux | 17600.700577729967 W/m^2 |
| Heat-transfer rate | 352.01401155459934 W |
| Schmidt number | 0.21052631578947367 |
| Sherwood number | 219.60841889730327 |
| Mass-transfer coefficient | 0.08784336755892132 m/s |
| Mass-transfer resistance | 11.383898725526953 s/m |
| Non-condensable risk | high |
| Source dimension check | pass |
| Source sign check | pass |
| Latent heat consistency | pass |
| Source stiffness level | low |

The passport and patch are `warn` because the public demo intentionally carries
high non-condensable layer risk. This is expected and keeps the handoff
reviewable.

## Stop Boundary

H2 stops at passport, hints, solver-plan patch, report, and demo artifact
generation. It does not:

- execute Fluent,
- call PyFluent,
- edit Fluent case/data files,
- generate UDF code,
- solve condensation physics,
- claim production heat-transfer or mass-transfer validation.

## Final Verification

H2-related test filter:

```powershell
python -m pytest -q tests -k "steam_air_condensation_v2 or steam_air or condensation or patch_compiler"
```

Result:

```text
34 passed, 217 deselected in 0.73s
```

Full repository test suite:

```powershell
python -m pytest -q
```

Result:

```text
251 passed in 6.18s
```
