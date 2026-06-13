# FastCFD Lattice Trust And Pilot Decision

This note documents two bounded FastCFD artifacts that help an agent decide
whether a cheap FastFluent-derived run is usable for preliminary CFD prediction,
physics screening, and later Fluent setup reasoning.

They are workflow controls for low-cost screening. They do not certify final CFD
accuracy and do not replace Fluent mesh-quality, residual, or engineering QoI
checks.

## `lattice_domain_summary.json`

`lattice_domain_summary.json` is generated from the validated `FastCFDJob`
recipe. It summarizes the recipe lattice before interpreting field output.

The artifact records:

- schema version and case type,
- lattice dimensions and cell length,
- recipe domain size and source,
- estimated fluid, wall, inlet, outlet, moving-wall, and obstacle cells,
- obstacle resolution and obstacle-to-boundary clearance when applicable,
- a bounded `trust_score`,
- warnings, errors, and limitations.

The score is intentionally conservative. It penalizes very small grids,
low fluid-cell counts, low obstacle resolution, low obstacle clearance, and
large pilot domains that may need resource planning.

The current implementation is recipe-derived. It is not a Fluent mesh parser
and should be checked against the final Fluent mesh-quality report.

## `pilot_decision.json`

`pilot_decision.json` combines available pilot evidence into a ranked action
list. The policy currently uses:

- lattice-domain status and trust score,
- native residual-history status, reduction ratio, and non-increasing fraction,
- field-parser status,
- outlet spread and reverse-flow proxies,
- wake detection for obstacle cases.

Possible statuses include:

- `proceed_with_advisory_handoff`,
- `extend_pilot_before_handoff`,
- `review_domain_extent`,
- `review_before_handoff`,
- `revise_lattice_domain`,
- `insufficient_evidence`.

The decision also records confidence, metrics used, recommended actions, and
limitations. It is designed for agent workflow control: for example, decide
whether to carry a wake bounding box into Fluent mesh refinement, extend a short
pilot run, or revise a coarse recipe domain before handoff.

## Backend Integration

Controlled real FastFluent runs write both artifacts after a successful run and
reference them from:

- `qoi.json`,
- `fluent_hints.json`,
- `claim_ledger.json`,
- `result_manifest.json`,
- the JSON and Markdown run reports.

The deterministic mock backend also writes both artifacts so CI and agent tests
can verify the same interface without requiring a local FastFluent build.

## Boundary

These artifacts support early, cheap prediction and physics screening only. A
valid downstream Fluent workflow still needs explicit CAD/mesh handoff, named
selections, Fluent mesh quality, Fluent residuals, and the project-specific
engineering outputs.
