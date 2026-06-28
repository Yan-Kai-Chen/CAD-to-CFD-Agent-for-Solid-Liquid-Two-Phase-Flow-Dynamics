# FastFluent Dewaxing Native Solver Progress

Date: 2026-06-27

This progress note records the dewaxing application upgrade from a bridge with
auxiliary S6 proxy evidence to a bridge with a FastFluent-native reduced-order
dewaxing computation.

## Implemented

- Added `fromcad2cfd_fastcfd.dewaxing_native_solver`.
- Added CLI command:

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-native-solver --output-dir sandbox/output/dewaxing_native_solver --format markdown
```

- Added the native solver into `fastcfd dewaxing-application-demo`.
- Added native Result Pack compilation for `dewaxing_native_status.json`.
- Added tests for solver QoI, native Result Pack compilation, CLI, and
  application bridge continuity.

## Native Computation

The solver performs a bounded FastFluent-native reduced-order calculation:

- 2D transient finite-volume heat conduction.
- Shell and wax regions with material-specific thermal properties.
- Effective heat-capacity enthalpy treatment for wax melting.
- Liquid-fraction field and full-melt timing.
- Early thermal-shock stress proxy.
- Drainage-accessibility and pressure-risk screening proxy.
- Energy-balance check.

It writes:

- `dewaxing_native_history.csv`
- `dewaxing_native_final_field.csv`
- `dewaxing_native_snapshots.csv`
- `dewaxing_native_qoi.json`
- `hardening_summary.json`
- `dewaxing_native_comparison.json`
- `dewaxing_native_status.json`

## Real Dewaxing Pack Check

Command used:

```powershell
python -m fromcad2cfd fastcfd dewaxing-application-demo `
  --output-dir sandbox/output/dewaxing_application_native_real `
  --dewaxing-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --format markdown
```

Result:

- Application status: `success`
- Native dewaxing solver stage: `passed`
- Native Result Pack status: `advisory_native_evidence`
- Existing dewaxing Result Pack validation: `passed`
- New Fluent calculation: `false`

Native reduced-order QoI:

- Grid cells: `221`
- Time steps: `5250`
- Final average liquid fraction: `1.0`
- Predicted full-melt time: `359.36 s`
- Dominant native risk time: `100.724744 s`
- Raw peak-risk time retained for traceability: `143.28 s`
- Early shell stress proxy: `1.723578103 MPa`
- Energy-balance relative error: `0.0519751133`

Comparison against existing Fluent pack:

- Fluent full-melt time: `409.0 s`
- Full-melt absolute error: `49.64 s`
- Full-melt relative error: `0.121369`
- Fluent dominant risk time: `100.7 s`
- Dominant-risk absolute error: `0.0247444 s`
- Dominant-risk relative error: `0.000245724`

## Application Scope

This solver is now the primary FastFluent computation in the dewaxing
application bridge. It is still reduced-order evidence:

- no Fluent launch;
- no PyFluent call;
- no Fluent case/data edit;
- no final CFD validation claim;
- no calibrated crack-probability claim;
- no two-way FSI validation claim.

The application positioning should describe this as:

FastFluent performs an independent reduced-order dewaxing calculation and the
Agent compares that native evidence against reviewed Fluent results under
an explicit application scope.

## Native Study Pack Update

Added `fromcad2cfd_fastcfd.dewaxing_native_study` and CLI command:

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-native-study `
  --output-dir sandbox/output/dewaxing_native_study_real `
  --comparison-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --format markdown
```

The full study ran `15` native reduced-order solver variants and wrote
`dewaxing_guidance.json`, `sensitivity_summary.json`, `variant_summary.csv`,
and one native Result Pack per variant.

Full-study result:

- Study status: `success`
- Best match variant: `shell_thin`
- Best objective score: `0.055559`
- Best full-melt time: `399.68 s`
- Fluent full-melt time: `409.0 s`
- Best full-melt relative error: `0.0227873`
- Best dominant-risk time: `115.668278 s`
- Fluent dominant-risk time: `100.7 s`
- Best dominant-risk relative error: `0.148642`
- Best early shell stress proxy: `1.547805 MPa`

Dominant local sensitivities:

- Full-melt timing: `steam_boundary_temperature_K`
- Risk-window timing: `initial_temperature_K`
- Early thermal-shock stress proxy: `steam_boundary_temperature_K`
- Pressure-risk proxy: `initial_temperature_K`

Agent guidance:

- Use `shell_thin` as the best reduced-order agreement case in this study pack.
- Use the native study to bracket reduced-order uncertainty before interpreting
  the reviewed Fluent result pack.
- Treat pressure-risk proxy as reduced-order screening only, not Fluent pressure
  or calibrated crack probability.

## Native Validation Pack Update

Added `fromcad2cfd_fastcfd.dewaxing_native_validation_pack` and CLI command:

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-native-validation-pack `
  --output-dir sandbox/output/dewaxing_native_validation_pack_real `
  --comparison-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --profile standard `
  --format markdown
```

The standard validation pack runs grid/time-step perturbations for two targets:

- `baseline`
- `shell_thin`

For each target it runs:

- current grid/time step
- coarse grid
- fine grid with smaller time step
- larger time step
- smaller time step

Real validation result:

- Validation status: `success`
- Quality status: `passed`
- Validation cases: `10`
- Native cell-time steps: `20,525,400`
- New Fluent calculation: `false`
- Recommended target: `shell_thin`
- Recommended next action: `use_validation_pack_for_agent_paper_evidence`

Current target comparison against the reviewed Fluent pack:

- `baseline` full-melt time: `359.36 s`
- `baseline` full-melt relative error: `0.121369`
- `baseline` dominant-risk time: `100.724744 s`
- `baseline` dominant-risk relative error: `0.000245724`
- `shell_thin` full-melt time: `399.68 s`
- `shell_thin` full-melt relative error: `0.0227873`
- `shell_thin` dominant-risk time: `115.668278 s`
- `shell_thin` dominant-risk relative error: `0.148642`

Stability outcome after risk-window smoothing and heat-flux shell-stress proxy:

- `baseline` full-melt timing passed with relative spread `0.0768032`.
- `baseline` dominant-risk timing passed with relative spread `0.161869`.
- `baseline` shell-stress proxy passed with relative spread `0.0538631`.
- `baseline` peak pressure-risk proxy passed with relative spread `0.0392472`.
- `shell_thin` full-melt timing passed with relative spread `0.0284227`.
- `shell_thin` dominant-risk timing passed with relative spread `0.0459941`.
- `shell_thin` shell-stress proxy passed with relative spread `0.0532977`.
- `shell_thin` peak pressure-risk proxy passed with relative spread `0.0283633`.
- `shell_thin` energy-balance error passed with maximum relative error `0.0589133`.

Interpretation:

- The validation pack makes FastFluent carry a substantial native computation
  after the Fluent runs are finished.
- It supports the paper claim that the Agent uses FastFluent-native computation
  to select and validate a dewaxing candidate, not just to summarize Fluent
  outputs.
- The strongest candidate-selection QoI remains full-melt timing.
- The smoothed risk-window and heat-flux shell-stress proxy now pass the
  current grid/time-step checks and can be reported as application screening
  metrics.
- Baseline is closest to Fluent for smoothed dominant-risk timing, while
  `shell_thin` remains selected by the combined objective because it greatly
  improves full-melt agreement.
- `shell_thin` should be described as an effective thermal-resistance
  correction, not proof that the physical shell is thinner.

## Agent Iteration Pack Update

Added `fromcad2cfd_fastcfd.dewaxing_agent_iteration_pack` and CLI command:

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-agent-iteration-pack `
  --output-dir sandbox/output/dewaxing_agent_iteration_pack_real `
  --comparison-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --format markdown
```

This pack makes the dewaxing Agent harder than a fixed sweep. It runs multiple
rounds of native candidate proposals, ranks candidates by a combined full-melt,
risk-window, and energy objective, and then validates top candidates until one
passes a five-case grid/time-step review.

Real Agent iteration result:

- Status: `success`
- Quality status: `passed`
- Candidate rounds: `3`
- Candidate count: `16`
- Validation targets checked: `6`
- Native solver runs: `46`
- Native cell-time steps: `80,140,200`
- New Fluent calculation: `false`
- Best unvalidated candidate: `path110_initial8`
- Accepted stable candidate: `path106_initial6`

The best unvalidated candidate, `path110_initial8`, used a `1.10` thermal-path
multiplier and `+8 K` initial-temperature offset. It matched the reviewed
Fluent pack very closely on the current grid:

- Full-melt time: `409.92 s`
- Full-melt relative error: `0.002249`
- Dominant risk time: `106.329067 s`
- Dominant-risk relative error: `0.055899`

The Agent rejected `path110_initial8` because its coarse-grid and fine-grid
validation cases did not reach full melt within the `420 s` campaign window. It
also rejected:

- `path108_initial8`
- `path108_initial6`
- `path108_initial5`
- `path108_initial4`

Each was a fitted candidate with at least one grid case that did not reach full
melt.

The accepted candidate, `path106_initial6`, used a `1.06` thermal-path
multiplier and `+6 K` initial-temperature offset:

- Current-grid full-melt time: `386.8 s`
- Current-grid full-melt relative error: `0.054279`
- Current-grid dominant risk time: `102.209953 s`
- Current-grid dominant-risk relative error: `0.014995`
- Current-grid early shell-stress proxy: `1.670091 MPa`
- Combined native objective: `0.042093`
- Objective improvement vs baseline: `46.099%`
- Objective improvement vs `shell_thin`: `34.364%`

Accepted-candidate stability:

- Full-melt relative spread: `0.080455` against threshold `0.12`
- Dominant-risk relative spread: `0.188587` against threshold `0.30`
- Shell-stress relative spread: `0.038167` against threshold `0.40`
- Peak pressure-risk relative spread: `0.022775` against threshold `0.35`
- Maximum energy-balance relative error: `0.054615` against threshold `0.08`

Interpretation:

- The Agent now performs a real iterative FastFluent-native campaign, not just a
  one-shot parameter sweep.
- The campaign demonstrates self-checking: it finds a best-fit candidate, then
  rejects it when grid/time-step evidence is weak.
- The accepted candidate is not the best full-melt-only candidate; it is the
  best candidate found so far that improves the combined objective while
  passing stability review.
- This is a strong paper-facing application result because it shows Agent
  guidance, repeated native computation, candidate rejection, and stable
  candidate acceptance without requesting a new Fluent run.

## Paper Evidence Pack Update

Added `fromcad2cfd_fastcfd.dewaxing_paper_evidence_pack` and CLI command:

```powershell
python -m fromcad2cfd fastcfd compile-dewaxing-paper-evidence-pack `
  --validation-pack sandbox/output/dewaxing_native_validation_pack_real `
  --iteration-pack sandbox/output/dewaxing_agent_iteration_pack_real `
  --output-dir sandbox/output/dewaxing_paper_evidence_pack_real `
  --manuscript-title "Agent-Guided FastFluent Dewaxing Simulation" `
  --format markdown
```

The paper evidence compiler reads existing validation and Agent iteration
packs. It does not rerun Fluent or the native solver.

Real paper evidence output:

- Paper evidence status: `success`
- Source validation status: `success`
- Source validation quality: `passed`
- Recommended target: `shell_thin`
- Source native solver runs: `10`
- Source native cell-time steps: `20,525,400`
- Source Agent iteration runs: `46`
- Source Agent iteration cell-time steps: `80,140,200`
- Agent accepted candidate: `path106_initial6`
- New Fluent calculation: `false`
- Native solver rerun: `false`

Generated artifacts:

- `paper_evidence_manifest.json`
- `agent_paper_claims.json`
- `sections/results_section.md`
- `sections/methods_section.md`
- `sections/figure_captions.md`
- `paper_evidence_report.md`
- `tables/table_01_native_candidate_comparison.csv`
- `tables/table_02_validation_matrix.csv`
- `tables/table_03_stability_summary.csv`
- `tables/table_04_agent_claim_boundary.csv`
- `tables/table_05_agent_iteration_candidates.csv`
- `tables/table_06_agent_iteration_stability.csv`
- `figures/figure_01_agent_evidence_chain.svg`
- `figures/figure_02_candidate_relative_errors.svg`
- `figures/figure_03_stability_spread.svg`
- `figures/figure_04_native_compute_load.svg`
- `figures/figure_05_agent_iteration_objective.svg`
- `figures/figure_06_accepted_candidate_stability.svg`
- `figures/figure_07_agent_iteration_flow.svg`

Figure style update:

- Figure style name: `nature_soft_statistical`
- Source memory: early-steam-shock distance-effect nature-style statistical
  plots.
- Palette rule: use the low-saturation thesis blue-pink palette for
  statistical and Agent workflow figures; reserve high-contrast blue-white-red
  palettes for scalar field maps.
- Main colors: `#6F91AA`, `#9FB9CE`, `#DFAFC0`, `#B8738E`, with white
  background, Arial text, weak pink-gray grid lines, and thin axes.

Draft results statement generated by the pack:

- The reviewed Fluent pack reported full-melt time `409.0 s` and dominant risk
  time `100.7 s`.
- Baseline native relative errors were `12.137%` for full-melt timing and
  `0.025%` for smoothed dominant risk timing.
- `shell_thin` reduced full-melt relative error to `2.279%`; its smoothed
  dominant-risk timing error is `14.864%`.
- `shell_thin` full-melt timing passed the stability gate with `2.842%`
  relative spread.
- `shell_thin` smoothed risk-window timing and heat-flux shell-stress proxy
  also passed with `4.599%` and `5.330%` relative spread.
- The Agent iteration campaign evaluated `16` candidates across `3` rounds,
  ran `46` native solver cases, and accumulated `80,140,200` cell-time steps.
- The best raw-fit candidate was `path110_initial8` with full-melt error
  `0.225%`, but it was not accepted directly after stability review.
- The Agent rejected `5` fitted candidates during stability review and accepted
  `path106_initial6`.
- `path106_initial6` full-melt error was `5.428%`, risk-time error was
  `1.499%`, and its accepted-candidate spreads were `8.046%` for full-melt
  timing, `18.859%` for risk-window timing, and `3.817%` for shell-stress
  proxy.
- The accepted candidate improved the combined native objective by `46.099%`
  relative to baseline and `34.364%` relative to `shell_thin`.

The generated paper claims give application-focused language guidance:

- FastFluent-native validation can be claimed as an auditable intermediate
  computation and screening decision.
- The full-melt timing result can be used as the strongest paper-facing native
  QoI.
- Risk-window and shell-stress proxy statements can be used as grid/time-step
  checked application screening metrics in this reduced-order pack.
- The Agent iteration pack can support candidate search, stability-gated
  acceptance, and compute-load evidence.
- The reduced-order solver must not be described as final CFD validation.
- The pressure-risk proxy must not be described as a Fluent pressure field.
- `shell_thin` must remain an effective thermal-resistance correction unless
  independent geometry/material evidence is added.
