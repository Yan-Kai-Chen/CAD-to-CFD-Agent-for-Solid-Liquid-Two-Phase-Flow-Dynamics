# FastFluent Dewaxing Application Bridge

The dewaxing application bridge is a public-safe FastFluent entrypoint for the
dewaxing case study. It connects the existing FastFluent agent workflow spine to
an already-computed dewaxing Fluent result pack without launching Fluent again.

The bridge exists to make the application stage continuous:

```text
public-safe dewaxing CaseSpec v3
  -> Flow Pack setup evidence
  -> Route Selector
  -> Dewaxing native application Route Plan
  -> H4 wax rheology / phase-change handoff
  -> native dewaxing reduced-order solver
  -> S6 temperature and wax-fraction auxiliary proxy calculations
  -> FastFluent native Result Packs
  -> existing dewaxing Result Pack validation
  -> Agent-guided native iteration campaign
  -> agent_decision.json
```

## Run

Use the public synthetic dewaxing result-pack fixture:

```powershell
python -m fromcad2cfd fastcfd dewaxing-application-demo `
  --output-dir sandbox/output/dewaxing_application_bridge `
  --format markdown
```

Use a private local bridge pack from an existing Fluent analysis:

```powershell
python -m fromcad2cfd fastcfd dewaxing-application-demo `
  --output-dir sandbox/output/dewaxing_application_private_review `
  --dewaxing-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --format markdown
```

Run only the native reduced-order dewaxing solver:

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-native-solver `
  --output-dir sandbox/output/dewaxing_native_solver `
  --comparison-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --format markdown
```

Run the native parameter study pack:

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-native-study `
  --output-dir sandbox/output/dewaxing_native_study `
  --comparison-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --format markdown
```

Run the Agent-guided native iteration campaign:

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-agent-iteration-pack `
  --output-dir sandbox/output/dewaxing_agent_iteration_pack `
  --comparison-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --format markdown
```

Run the native validation/evidence pack after the study identifies a candidate:

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-native-validation-pack `
  --output-dir sandbox/output/dewaxing_native_validation_pack `
  --comparison-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --profile standard `
  --format markdown
```

Compile the paper evidence pack from a completed validation pack. Add the
iteration pack when the paper needs the closed-loop Agent search evidence:

```powershell
python -m fromcad2cfd fastcfd compile-dewaxing-paper-evidence-pack `
  --validation-pack sandbox/output/dewaxing_native_validation_pack `
  --iteration-pack sandbox/output/dewaxing_agent_iteration_pack `
  --output-dir sandbox/output/dewaxing_paper_evidence_pack `
  --manuscript-title "Agent-Guided FastFluent Dewaxing Simulation" `
  --format markdown
```

## Outputs

The command writes:

- `application_manifest.json`
- `stage_status.json`
- `agent_decision.json`
- `agent_flow_report.md`
- `01_case/dewaxing_application_case.json`
- `02_flow_pack/flow_pack.json`
- `03_route_selection/route_selection.json`
- `04_route_plan/route_plan.json`
- `04_route_plan/dewaxing_application/dewaxing_application_plan.json`
- `05_wax_h4_handoff/solver_plan_patch.json`
- `06_fastfluent_native_dewaxing/native_result/dewaxing_native_status.json`
- `06_fastfluent_native_dewaxing/native_result/dewaxing_native_history.csv`
- `06_fastfluent_native_dewaxing/native_result/dewaxing_native_final_field.csv`
- `06_fastfluent_native_dewaxing/result_pack/result_pack.json`
- `07_fastfluent_native_proxy/temperature/result_pack/result_pack.json`
- `07_fastfluent_native_proxy/wax_fraction/result_pack/result_pack.json`

The native solver computes:

- 2D transient heat conduction on a shell/wax public surrogate domain.
- Effective heat-capacity enthalpy melting across a wax melting interval.
- Liquid-fraction fields and full-melt time.
- Early thermal-shock stress proxies.
- Drainage-accessibility and pressure-risk screening proxies.
- Energy-balance and comparison metrics against an existing dewaxing Result Pack.

The native study pack runs multiple solver variants and writes:

- `study_manifest.json`
- `variant_summary.csv`
- `variant_summary.json`
- `sensitivity_summary.json`
- `dewaxing_guidance.json`
- one native solver output tree and Result Pack per variant

The study currently sweeps heat-transfer coefficient, steam temperature, latent
heat, wax thermal conductivity, shell thickness, thermal path thickness, and
initial temperature. The guidance artifact ranks variants by agreement with the
reviewed Fluent pack and reports local sensitivity of full-melt timing, risk
window timing, early stress proxy, and pressure-risk proxy.

The native validation pack runs grid/time-step perturbations for the baseline
and the best study candidate. It writes:

- `validation_pack_manifest.json`
- `convergence_summary.csv`
- `convergence_summary.json`
- `qoi_stability.json`
- `paper_tables.md`
- `study_interpretation.md`
- `agent_validation_decision.json`
- one native solver output tree and Result Pack per validation case

The standard validation profile runs `10` native solver cases. The real local
dewaxing run completed `20,525,400` native cell-time steps, recommended
`shell_thin`, and reached final quality status `passed`. The `shell_thin`
full-melt spread was `2.842%`, smoothed risk-window spread was `4.599%`, and
heat-flux shell-stress spread was `5.330%`, so the pack can report these as
grid/time-step checked application screening metrics.

The Agent iteration pack runs a closed-loop native campaign and writes:

- `agent_iteration_manifest.json`
- `candidate_summary.csv`
- `candidate_summary.json`
- `round_trace.json`
- `agent_decision.json`
- `iteration_report.md`
- one native solver output tree and Result Pack per candidate
- one five-case stability review for each top candidate checked until an
  accepted candidate is found

The real local Agent iteration campaign completed `46` native solver runs and
`80,140,200` native cell-time steps without launching Fluent. It first found a
best-fit candidate, `path110_initial8`, with full-melt error `0.225%` and
risk-time error `5.590%`, then rejected it because coarse/fine grid validation
did not reach full melt. It rejected four additional fitted candidates during
stability review and accepted `path106_initial6` after its five-case stability
review passed. The accepted candidate uses a `1.06` thermal-path multiplier and `+6 K`
initial-temperature offset; its current-grid full-melt error is `5.428%`,
risk-time error is `1.499%`, full-melt spread is `8.046%`, risk-window spread
is `18.859%`, and shell-stress spread is `3.817%`. Its combined native
objective improved by `46.1%` relative to baseline and `34.4%` relative to
`shell_thin`.

The paper evidence pack compiles an existing validation pack into:

- `paper_evidence_manifest.json`
- `agent_paper_claims.json`
- `sections/results_section.md`
- `sections/methods_section.md`
- `sections/figure_captions.md`
- four CSV/Markdown tables and four SVG figures for validation-only evidence
- six CSV/Markdown tables and seven SVG figures when an Agent iteration pack is
  supplied

The compiler reuses the completed validation results and turns the checked
native results into application-ready tables, figures, claim guidance, and
manuscript text.

The real local paper evidence pack with both source packs reached status
`success`, generated six tables and seven SVG figures, and added the Agent
iteration claims: `16` candidates, `3` rounds, `46` native solver runs,
`80,140,200` native cell-time steps, `5` stability-rejected fitted candidates,
and accepted candidate `path106_initial6`.

The FastFluent-to-Fluent guidance pack compiles the existing study, validation,
iteration, and completed Fluent bridge evidence into a paper-facing handoff:

- `guidance_manifest.json`
- `fluent_guidance_report.md`
- `fluent_handoff_brief.md`
- `figures/figure_01_fastfluent_guided_fluent_workflow.svg`
- `figures/figure_01_fastfluent_guided_fluent_workflow_preview.png`
- draft paper outline, methods guidance, and results guidance sections
- `sections/workflow_figure_notes.md`
- four tables covering process partitions, Fluent validation targets,
  parameter priorities, and reusable assets

The real local guidance pack reached status `success` at
`sandbox/output/dewaxing_fluent_guidance_pack_real`. It defines `5` process
partitions and `7` Fluent validation targets, accepts `path106_initial6` as the
stable reduced-order candidate, and uses the completed Fluent bridge as
retrospective confirmation of the FastFluent-selected windows: early `0-4.1 s`,
risk window near `100.7 s`, and full melt near `409.0 s`.

The workflow figure is the current project-logic baseline. Solid arrows show
FastFluent guiding the Fluent-facing plan. The dashed bottom lane shows existing
Fluent results as retrospective confirmation only.

```powershell
python -m fromcad2cfd fastcfd compile-dewaxing-fluent-guidance-pack `
  --study-pack sandbox/output/dewaxing_native_study_real `
  --validation-pack sandbox/output/dewaxing_native_validation_pack_real `
  --iteration-pack sandbox/output/dewaxing_agent_iteration_pack_real `
  --fluent-bridge-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --output-dir sandbox/output/dewaxing_fluent_guidance_pack_real `
  --format markdown
```

The current figure style is `nature_soft_statistical`, inherited from the
early-steam-shock distance-effect nature-style outputs. Statistical and Agent
workflow figures use the low-saturation thesis blue-pink palette
(`#6F91AA`, `#9FB9CE`, `#DFAFC0`, `#B8738E`) with white background, Arial
text, weak pink-gray grid lines, and thin axes. High-contrast blue-white-red
palettes remain reserved for scalar field maps.

## Application Scope

The bridge is the application layer that connects four evidence sources:

- FastFluent setup and routing evidence.
- FastFluent-native dewaxing calculation.
- S6 temperature and wax-fraction auxiliary proxy calculations.
- Reviewed Fluent dewaxing result pack.

Use the native dewaxing solver for candidate screening, timing comparison, and
compute-load evidence. Use the reviewed Fluent result pack as the high-fidelity
reference for final timing and stress interpretation. Add crack-probability or
two-way FSI wording only after a dedicated evidence source is available.

## Article Positioning

For the dewaxing paper, this bridge lets the application section separate three
claims:

- FastFluent provides reproducible setup, physics-passport, and proxy-calculation evidence.
- FastFluent carries a native reduced-order dewaxing computation with its own
  temperature field, liquid-fraction field, melt timing, risk proxy, and Result Pack.
- FastFluent can run a reduced-order ensemble study to identify dominant
  parameters before interpreting or planning high-fidelity Fluent evidence.
- The Agent can run a multi-round native iteration campaign, reject fitted
  candidates that do not pass stability review, and accept a stable
  reduced-order candidate.
- FastFluent can run a grid/time-step validation pack for the selected
  reduced-order candidate and produce paper-facing tables plus claim
  guidance.
- Existing Fluent dewaxing results provide the high-fidelity external result evidence.
- The Agent connects both evidence classes through explicit manifests and
  decision artifacts instead of silently mixing solver levels.
