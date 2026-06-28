# Dewaxing FastFluent-to-Fluent Asset Inventory

Date: 2026-06-28

Purpose: reorganize the existing dewaxing and early-steam-shock work around the
correct paper logic: FastFluent partitions and screens the complex dewaxing
process first, then guides targeted Fluent validation. The completed Fluent
results are reused as retrospective confirmation of the FastFluent guidance,
not as the primary driver of the FastFluent model.

## Core Narrative Direction

Correct direction:

```text
Complex dewaxing process
-> FastFluent process partitioning and reduced-order screening
-> Agent priority and handoff decisions
-> targeted Fluent high-fidelity validation
-> retrospective check using completed Fluent result packs
```

Incorrect direction to avoid:

```text
Completed Fluent result
-> FastFluent fitted to Fluent
-> Agent reports the fit
```

## Reusable Asset Groups

### A. Early Steam-Shock Fluent Asset Family

Location: `D:\CYK2\Fluent\10_Results`

Reusable packages:

| package group | role in the new paper logic |
| --- | --- |
| `21earlySteamShock_distance-orientation_field-visualization_equivalentCond_nature-style` | field-level evidence for the 0-4.1 s early shock stage |
| `23earlySteamShock_distance-effect_steam-filling_math-physics_nature-style` | distance-effect steam filling and math/physics curves |
| `23earlySteamShock_orientation-effect_math-physics_nature-style` | orientation-effect analysis |
| `24earlySteamShock_distance-effect_layer1-steam-filling-curves_nature-style` | layer-1 steam filling curves |
| `25earlySteamShock_distance-effect_layer1-refined-anomaly-curves_nature-style` | refined anomaly curves |
| `26earlySteamShock_distance-effect_surface-thermal-impact-pilot_nature-style` | surface thermal-impact pilot metrics |
| `28earlySteamShock_distance-effect_surface-projection-videos_nature-style` | surface projection maps and videos |
| `29earlySteamShock_distance-effect_integrated-math-analysis_nature-style` | integrated distance-effect matrix and Nature-style statistical plot language |
| `30earlySteamShock_distance-effect_shell-cracking-stress-proxy_nature-style` | shell cracking/stress proxy |
| `31earlySteamShock_unified-thermal-shock-cracking-pathway_nature-style` | unified thermal-shock cracking pathway |
| `34-36earlySteamShock_inlet-diameter_*_nature-style` | inlet-diameter extension assets |

Observed asset scale from the local inventory:

- Early-steam-shock nature-style packages contain many reusable data and visual
  assets: hundreds of PNG field/projection frames, dozens of SVG/PDF paper
  figures, CSV summaries, and Markdown analysis files.
- The `29earlySteamShock_distance-effect_integrated-math-analysis_nature-style`
  manifest defines the preferred statistical figure style:
  low-saturation thesis blue-pink palette, with high-contrast blue-white-red
  reserved for scalar field maps.

Key reusable physical conclusions from the bridge pack:

- Stage: `0-4.1 s` early steam-shock screening.
- Case count: `6`.
- Maximum early crack-driving index: `0.0147` of the `3.6 MPa` reference
  threshold.
- Maximum mean heat dose: Frontal 900 mm, `31.60 kJ/m2`.
- Maximum shell mean temperature rise: Frontal 900 mm, `1.804 C`.
- Maximum impact impulse: Side 600 mm, `27.91 N s`.

How to reuse:

- Treat this as the early-stage Fluent verification family.
- Use it to validate whether FastFluent correctly identifies the early shock
  window, distance/orientation sensitivity, and surface thermal/impact priority.
- Do not restart early-shock analysis from zero.

### B. Full-Cycle Wax-Melting Fluent Asset Family

Location: `D:\CYK2\Fluent\10_Results`

Reusable packages:

| package | role |
| --- | --- |
| `13WaxMelt_W6-W9D-W10D_drainRelief_240s_pressurePeak4p47MPa_stressDrop82pct` | drainage-relief and pressure/stress reference |
| `14WaxMelt_W6_current_discussion_package_20260625_173800` | W6 discussion package |
| `15WaxMelt_W6_complete420s_LF0p997_pressurePeak4p47MPa_stressDrop94pct` | completed 420 s full-cycle melt package |
| `32Dewaxing_AgentBridge_W6EarlyShockFullCycle` | bridge pack linking early shock and full-cycle dewaxing |

Key full-cycle QoIs from `32Dewaxing_AgentBridge_W6EarlyShockFullCycle`:

- Full-cycle stage: `0-420 s`.
- Full melt threshold: average liquid fraction `0.995`.
- First full-melt time: `409.0 s`.
- Latest average liquid fraction at 420 s: `0.9973977416905839`.
- Dominant full-cycle risk window: `100.7 s`.
- Peak effective pressure at risk window: `4.465776 MPa`.
- Peak wall VM P99.5 proxy: `42.4515 MPa`.
- Late pressure/stress relief from peak to latest: `94.2%`.

How to reuse:

- Treat this as the already-completed high-fidelity validation family.
- Use it to retrospectively show that FastFluent guidance would have selected
  the correct Fluent time windows and monitored QoIs.
- Do not describe FastFluent as merely fitted to these results.

### C. FastFluent Dewaxing Native Assets

Location:
`D:\CYK2\Fluent\11_FastFluent_Agent\workspaces\public_repo\sandbox\output`

Reusable packs:

| pack | status | reusable role |
| --- | --- | --- |
| `dewaxing_application_bridge_real` | `success` | application chain and manifest bridge |
| `dewaxing_native_study_real` | `success` | reduced-order parameter screening |
| `dewaxing_native_validation_pack_real` | `success`, `passed` | grid/time-step checked native evidence |
| `dewaxing_agent_iteration_pack_real` | `success`, `passed` | multi-round Agent search and stable candidate acceptance |
| `dewaxing_paper_evidence_pack_real` | `success`, `passed` | paper-ready tables, sections, claims, and SVG figures |

FastFluent native study:

- Native study runs: `15`.
- Best reduced-order agreement case: `shell_thin`.
- Best full-melt agreement case: `wax_layer_thick`.
- Closest risk-window case: `baseline`.
- Lowest early shell-stress proxy: `htc_low`.
- Important sensitivity findings:
  - full-melt timing is most sensitive to `steam_boundary_temperature_K`;
  - risk-window timing is most sensitive to `initial_temperature_K`;
  - early shell-stress proxy is most sensitive to `steam_boundary_temperature_K`.

FastFluent native validation:

- Native validation cases: `10`.
- Native cell-time steps: `20,525,400`.
- Quality status: `passed`.
- Recommended target in the validation pack: `shell_thin`.
- `shell_thin` full-melt relative error: `2.279%`.
- `shell_thin` full-melt spread: `2.842%`.
- `shell_thin` risk-window spread: `4.599%`.
- `shell_thin` shell-stress proxy spread: `5.330%`.

Agent iteration pack:

- Rounds: `3`.
- Candidates: `16`.
- Validation targets checked: `6`.
- Native solver runs: `46`.
- Native cell-time steps: `80,140,200`.
- Best unvalidated candidate: `path110_initial8`, objective `0.023146`.
- Accepted stable candidate: `path106_initial6`, objective `0.042093`.
- Rejected during stability review: `5` fitted candidates.
- Improvement vs baseline objective: `46.099%`.
- Improvement vs `shell_thin` objective: `34.364%`.

How to reuse:

- Use these packs as the FastFluent guidance layer.
- Reframe the study/validation/iteration results as a method to propose Fluent
  time windows, spatial blocks, parameter priorities, monitor fields, and
  targeted high-fidelity cases.
- Keep completed Fluent results as retrospective confirmation.

## Reusable Process Partitions

The existing assets already support the following process decomposition:

| partition | FastFluent role | reusable Fluent confirmation |
| --- | --- | --- |
| `0-4.1 s` early steam shock | identify thermal/impact screening window | early-steam-shock packages `21-31`, `34-36` |
| `~100.7 s` dominant risk window | pressure-risk and shell-stress proxy priority | W6/W9D/W10D/W11 bridge evidence |
| `120-420 s` melt/drainage evolution | melt front and drainage-accessibility screening | full-cycle W6 420 s package |
| `~409 s` full melt | completion timing and final melt state | W6 first full-melt time |
| late relief state | pressure/stress drop after drainage | 94.2% late pressure/stress drop |

## Reusable Spatial/Physics Blocks

These can become the core of the FastFluent-to-Fluent guidance pack:

| block | current reusable evidence | Fluent guidance implication |
| --- | --- | --- |
| steam inlet / jet path | early shock field visualization and inlet-diameter packages | refine inlet/jet region and early 0-4 s sampling |
| shell inner surface | heat dose, shell rise, shell-stress proxy packages | surface heat-flux and shell-temperature monitors |
| wax thermal path | FastFluent native study: `thickness_m`, shell/thickness effects | prioritize thermal-path and shell-resistance variants |
| wax latent/melt front | FastFluent native study: latent heat and full-melt timing | monitor liquid fraction and melt-front progress |
| drainage accessibility | full-cycle bridge, pressure relief metrics | track outlet discharge, release ratio, trapped/unreleased fraction |
| pressure-risk retention | risk-window proxy and W9D pressure peak | dense monitor output near 100.7 s |
| accepted stable candidate | Agent iteration accepted `path106_initial6` | use as stable reduced-order candidate for targeted Fluent validation |

## What We Should Not Restart

- Do not rerun Fluent just to rebuild the existing early-shock and full-cycle
  evidence.
- Do not recreate the nature-style distance figures from scratch.
- Do not rebuild the public FastFluent dewaxing native solver from zero.
- Do not treat `shell_thin` or `path106_initial6` as final physical geometry
  changes without additional material/geometry evidence.

## What Is Missing

The main missing piece was not more raw computation. It was a formal guidance
artifact:

```text
FastFluent-to-Fluent Dewaxing Guidance Pack
```

It should compile the existing FastFluent study, validation, and iteration
outputs into Fluent-facing recommendations:

- time windows to validate in Fluent;
- spatial zones requiring mesh/time-step attention;
- monitored QoIs and report definitions;
- parameter combinations worth high-fidelity Fluent validation;
- existing Fluent packages that already confirm or challenge each guidance
  recommendation.

This guidance pack will convert the current asset collection into the intended
paper logic: FastFluent guides Fluent, while the already-completed Fluent
results are used to verify that the guidance was meaningful.

## Generated Guidance Pack

The first real guidance pack has now been generated at:

```text
sandbox/output/dewaxing_fluent_guidance_pack_real
```

It compiles:

- FastFluent native study: `15` native runs.
- FastFluent native validation: `10` checked cases and `20,525,400`
  cell-time steps.
- FastFluent Agent iteration: `46` native runs, `80,140,200` cell-time
  steps, `16` candidates, and accepted candidate `path106_initial6`.
- Completed Fluent bridge pack:
  `D:/CYK2/Fluent/10_Results/32Dewaxing_AgentBridge_W6EarlyShockFullCycle/01_agent_result_pack`.

The pack writes:

- `guidance_manifest.json`
- `fluent_guidance_report.md`
- `fluent_handoff_brief.md`
- `figures/figure_01_fastfluent_guided_fluent_workflow.svg`
- `figures/figure_01_fastfluent_guided_fluent_workflow_preview.png`
- `sections/paper_outline.md`
- `sections/methods_guidance_section.md`
- `sections/results_guidance_section.md`
- `sections/workflow_figure_notes.md`
- four CSV/Markdown tables:
  process partitions, Fluent validation targets, parameter priorities, and
  reusable asset mapping.

Core paper-ready outputs:

- `5` process partitions:
  early shock, dominant risk window, melt/drainage, completion, and candidate
  handoff.
- `7` Fluent validation targets:
  early sampling, risk-window refinement, melt/drainage monitoring, completion
  endpoint, steam-temperature variants, initial-temperature variants, and the
  accepted candidate case.
- Top Fluent parameter priorities from FastFluent screening:
  `initial_temperature_K`, `steam_boundary_temperature_K`, and `thickness_m`.
- Retrospective Fluent confirmations:
  early shock `0-4.1 s`, risk window near `100.7 s`, full melt near `409.0 s`,
  peak effective pressure `4.465776 MPa`, and wall VM P99.5 `42.451535 MPa`.

The first workflow figure uses the `nature_soft_statistical` style and locks the
direction of the project logic:

```text
FastFluent computation -> guidance synthesis -> Fluent-facing plan -> paper evidence
```

The existing Fluent bridge is drawn as a dashed retrospective confirmation layer
only. It should not be interpreted as the source that selected the FastFluent
partitions.

Reproducible command:

```powershell
$env:PYTHONPATH='src'
python -m fromcad2cfd fastcfd compile-dewaxing-fluent-guidance-pack `
  --study-pack sandbox/output/dewaxing_native_study_real `
  --validation-pack sandbox/output/dewaxing_native_validation_pack_real `
  --iteration-pack sandbox/output/dewaxing_agent_iteration_pack_real `
  --fluent-bridge-pack D:\CYK2\Fluent\10_Results\32Dewaxing_AgentBridge_W6EarlyShockFullCycle\01_agent_result_pack `
  --output-dir sandbox/output/dewaxing_fluent_guidance_pack_real `
  --manuscript-title "FastFluent-Guided Fluent Dewaxing Workflow" `
  --format markdown
```
