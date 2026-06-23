# FastFluent S2 Practical Native Function Expansion Progress

Date: 2026-06-23

## Scope

S2 expands FastFluent beyond narrow physics passports by adding practical native
mini computations. These utilities generate fields, histories, QoIs, stability
indicators, parameter-sweep tables, and public demo artifacts without launching
ANSYS Fluent.

## Baseline Before S2

- S1 provided a native simulation validation pack with public unstructured FVM
  cases, field outputs, convergence histories, QoIs, manifests, and
  passport-simulation alignment reports.
- H4 provided wax rheology / phase-change passports, Fluent hints, and
  non-executing solver-plan patch handoff evidence.
- Existing unstructured routes already covered scalar diffusion, Stokes,
  projection, controlled steady incompressible flow, VOF-lite alpha transport,
  and bounded turbulence-ladder evidence.
- Baseline after H4 and before S2 implementation:

```text
python -m pytest -q
290 passed in 9.00s
```

## Acceptance Gates

- At least four practical native modules are implemented.
- 1D heat diffusion runs and writes CSV/JSON artifacts.
- Scalar advection-diffusion or bounded scalar transport runs.
- Arrhenius viscosity/property field evaluation runs.
- Source-term ramp/clamp toy model runs.
- Parameter sweep runs.
- Wax application demo combines practical native utilities.
- `practical-native-demo-pack` CLI exists and writes a manifest plus summary.
- Targeted and full tests pass.
- Fluent is not launched.

## Implemented

- `practical_native_artifacts.py`
  - Schema-versioned practical result contract.
  - JSON, CSV, Markdown writing helpers.
  - Dangerous-key rejection and explicit no-Fluent metadata.
- `practical_heat_diffusion.py`
  - 1D explicit heat diffusion.
  - 2D explicit heat diffusion.
  - Fourier-number stability gates.
  - Temperature fields, histories, QoIs, and summaries.
- `practical_scalar_transport.py`
  - 1D upwind advection-diffusion.
  - CFL and diffusion-number stability gates.
  - Bounded scalar clamp comparison.
- `practical_material_properties.py`
  - Constant, linear, piecewise-linear, and Arrhenius property evaluation.
  - Arrhenius viscosity field demo.
  - Property range and fit-range checks.
- `practical_source_terms.py`
  - Single-cell source-term toy model.
  - Constant, temperature-window, and phase-change-interval source modes.
  - Ramp, clamp, and NaN guard controls.
- `practical_sweep.py`
  - Lightweight parameter sweep.
  - Sweep summary, risk map, and recommended time-step table.
- `practical_native_demo_pack.py`
  - One-command public S2 demo pack.
  - Wax application demo combining heat diffusion, Arrhenius viscosity, source
    controls, and parameter sweep.

## Demo Result

Command:

```powershell
python -B -m fromcad2cfd fastcfd practical-native-demo-pack --output-dir sandbox/output/fastfluent_practical_native_demo_pack --format markdown
```

Observed result:

```text
Status: success
Case count: 8
Heat diffusion 1D: True
Scalar transport: True
Material property field: True
Source ramp/clamp: True
Parameter sweep: True
Wax application demo: True
Fluent launched: False
```

## Test Results

Targeted S2 filter:

```powershell
python -m pytest -q tests -k "practical or heat_diffusion or scalar_transport or material_properties or source_terms or sweep"
```

Result:

```text
16 passed, 289 deselected in 0.99s
```

Full repository test suite:

```powershell
python -m pytest -q
```

Result:

```text
305 passed in 9.19s
```

## Boundaries

- Fluent was not launched.
- PyFluent was not called.
- Fluent case/data files were not edited.
- Fluent TUI commands were not emitted.
- Executable UDF source was not generated.
- S2 validates practical native utilities and artifact generation; it does not
  prove high-fidelity CFD accuracy.
