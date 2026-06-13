# FastCFD Quickstart

FastCFD is the FromCAD2CFD preliminary CFD prediction and physics-screening
layer. It is designed to run cheap, bounded FastFluent-derived tests before
high-fidelity Fluent validation. It is not a Fluent replacement and its reports
must remain evidence-led.

## Capability Inventory

```powershell
python -m fromcad2cfd fastcfd capabilities --format markdown
```

## Source-Of-Truth Registry

The registry is the bounded list of case templates, lattice sets, boundary
types, and collision models that an agent is allowed to use.

```powershell
python -m fromcad2cfd fastcfd registry --format markdown
```

## Environment Preflight

```powershell
python -m fromcad2cfd fastcfd preflight
```

Set one of these variables before real FastFluent backend work:

- `FROMCAD2CFD_FASTFLUENT_ROOT`
- `FASTFLUENT_ROOT`

## CI-Safe Mock Demo

```powershell
python -m fromcad2cfd fastcfd mock-demo --project fastcfd_mock_cavity2d --model-name fastcfd_mock_cavity2d
```

The mock backend writes the same artifact classes expected from real FastCFD
runs:

- `generated.ini`
- `convergence.csv`
- `qoi.json`
- `physics_contract.json`
- `lattice_domain_summary.json`
- `flow_fingerprint.json`
- `fastcfd_prediction.json`
- `pilot_decision.json`
- `fluent_hints.json`
- `claim_ledger.json`
- `result_manifest.json`
- `fastcfd_report.json`
- `fastcfd_report.md`

The mock backend is deterministic and validates workflow plumbing only. It does
not produce numerical CFD evidence.

## Semantic Scene To Job

For agent workflows, prefer a semantic scene first. A scene describes the
domain, zones, obstacle intent, and physics intent. It is then validated and
compiled into a bounded `FastCFDJob`.

```powershell
python -m fromcad2cfd fastcfd write-scene --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_scene --scene-type obstacle2d --obstacle circle
python -m fromcad2cfd fastcfd validate-scene --scene-file <scene.json>
python -m fromcad2cfd fastcfd compile-scene --scene-file <scene.json> --project fastcfd_obstacle2d_scene --model-name fastcfd_obstacle2d_job
python -m fromcad2cfd fastcfd validate-job --job-file <job.json>
python -m fromcad2cfd fastcfd run-mock-job --job-file <job.json>
```

Public examples:

- `examples/fastcfd/mock_cavity2d/job.json`
- `examples/fastcfd/channel2d_scene/scene.json`
- `examples/fastcfd/obstacle2d_scene/scene.json`

## Controlled Real Cavity2D Backend

After the local FastFluent source root is available and preflight is acceptable:

```powershell
python -m fromcad2cfd fastcfd write-cavity2d-job --project fastcfd_cavity2d_real --model-name fastcfd_cavity2d_real
python -m fromcad2cfd fastcfd run-fastfluent-cavity2d-job --job-file <job.json> --source-root <FastFluent source root>
```

The command builds only the known `examples/cavity2d` target, writes a generated
`cavity2d.ini`, runs the executable in the project output directory, captures
logs, indexes VTK XML outputs, and writes the same report contract as the mock
backend.

## Controlled Real Channel2D And Obstacle2D Backends

The first inlet/outlet route uses the known FastFluent `openboundary2d` example.
The obstacle route generates a controlled local C++ variant from the channel
recipe, supports circle and rectangle recipe obstacles, and does not modify the
global FastFluent source tree.

```powershell
python -m fromcad2cfd fastcfd write-channel2d-job --project fastcfd_channel2d_real --model-name fastcfd_channel2d_real --total-steps 100 --output-interval 50
python -m fromcad2cfd fastcfd run-fastfluent-job --job-file <channel_job.json> --source-root <FastFluent source root>

python -m fromcad2cfd fastcfd write-obstacle2d-job --project fastcfd_obstacle2d_real --model-name fastcfd_obstacle2d_real --obstacle circle --total-steps 100 --output-interval 50
python -m fromcad2cfd fastcfd run-fastfluent-job --job-file <obstacle_job.json> --source-root <FastFluent source root>
```

Both routes write:

- generated `.ini`
- `fastfluent_native_summary.json` when the local executable has the native
  FromCAD2CFD summary hook installed
- `fastfluent_native_convergence.csv` when the local executable has the native
  residual-history hook installed
- build log
- stdout and stderr logs
- `physics_contract.json`
- `field_qoi.json`
- `lattice_domain_summary.json`
- `flow_fingerprint.json`
- `pilot_decision.json`
- `qoi.json`
- `fluent_hints.json`
- `claim_ledger.json`
- `result_manifest.json`
- Markdown and JSON reports

When real FastFluent VTK XML fields are available, `field_qoi.json` decodes the
latest field `.vti` and optional `GeoFlag` file into conservative pilot metrics:

- selected output step and grid metadata
- speed and density summaries
- centerline velocity samples
- inlet and outlet velocity profile summaries
- outlet spread and reverse-flow proxies
- obstacle wake bounding-box proxy when applicable
- near-wall and obstacle-near-field refinement hints

`flow_fingerprint.json` is a compact agent-facing subset of the same evidence.
`qoi.json`, `fluent_hints.json`, `claim_ledger.json`, and `result_manifest.json`
reference the parser status so downstream tools can distinguish parsed field
evidence from missing or failed field analysis.

## Preliminary CFD Prediction Report

Every successful mock or controlled real run writes:

- `fastcfd_prediction.json`
- `<model_name>_fastcfd_prediction.md`

The prediction report reframes available FastCFD evidence as preliminary CFD
screening rather than only as a handoff gate. It records:

- physics-screening verdict, Reynolds regime, lattice Mach estimate, tau/omega,
  and concerns,
- expected flow behavior for cavity, channel, or obstacle cases,
- numerical-quality review from residual history, field parser status, and
  lattice-domain trust,
- design implications such as outlet/domain review, wake-region optimization,
  or velocity/lattice scaling changes,
- recommended next parameter checks.

Existing output directories can be reprocessed:

```powershell
python -m fromcad2cfd fastcfd predict-from-output --fastcfd-output-dir <FastCFD output dir>
```

## Bounded Parameter Screening

Before running many solver variants, use the bounded pre-run screen. It expands
a finite set of velocity and grid-size variants, validates each physics passport,
and ranks the candidates without launching FastFluent.

```powershell
python -m fromcad2cfd fastcfd screen-parameters --job-file <job.json> --velocity-multipliers 0.5,1.0,2.0 --cell-length-multipliers 1.0,0.5 --max-variants 6
```

The output is a screening matrix with recommended and blocked variants. This is
the safe first step for simple tests such as "does the intended Reynolds regime
make sense?" or "which grid scale is worth running next?".

`lattice_domain_summary.json` records recipe-to-lattice domain checks, including
zone counts, obstacle resolution, obstacle clearance, warnings, errors, and a
bounded trust score. `pilot_decision.json` combines lattice evidence, native
residual history, and parsed field QoI into a conservative next-action status
such as `proceed_with_advisory_handoff`, `extend_pilot_before_handoff`,
`review_domain_extent`, or `revise_lattice_domain`. See
[lattice_trust_and_pilot_decision.md](lattice_trust_and_pilot_decision.md).

When present, `fastfluent_native_summary.json` is emitted directly by the
FastFluent executable and records run facts such as case type, completed steps,
grid size, physical properties, reference velocity, final residual, physical
time, and field prefix. It complements wrapper-side reports and VTK parsing.
See [native_summary_contract.md](native_summary_contract.md).

When present, `fastfluent_native_convergence.csv` is also emitted directly by
the executable and records residual history as `step,residual`. The backend
summarizes it into QoI fields such as sample count, final residual, reduction
ratio, and non-increasing fraction.

The `obstacle2d` route also writes the generated controlled C++ source and an
`obstacle_summary.json` report.
