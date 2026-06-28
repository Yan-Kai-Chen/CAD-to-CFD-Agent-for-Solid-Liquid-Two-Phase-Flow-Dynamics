# Limitations And Claim Boundaries

Status: `active claim-boundary guide`

This page keeps the public and paper claims conservative.

## Required Boundaries

- FastFluent is reduced-order guidance, not a replacement for Fluent.
- Completed Fluent results are retrospective confirmation.
- Pressure-risk and shell-stress outputs are proxies.
- Accepted parameter edits are reduced-order assumptions, not measured physical
  changes.
- Public tests and examples must not require private Fluent case/data files.

## Allowed Claims

- The Agent can organize a traceable FastFluent-to-Fluent workflow.
- FastFluent can generate reduced-order evidence for screening and target
  selection.
- The Agent can reject unstable fitted candidates before choosing a stable
  reduced-order candidate.
- The public fixture can validate result-pack shape and claim boundaries.

## Disallowed Claims

- FastFluent replaces final Fluent validation.
- Proxy pressure or shell-stress metrics are calibrated crack probabilities.
- Accepted reduced-order edits are measured physical geometry or material
  properties.
- Public examples depend on private Fluent case/data files.
- Existing Fluent results selected the FastFluent partitions.

## Test Coverage

These boundaries are covered by public tests:

- `tests/unit/test_fastcfd_dewaxing_application.py`
- `tests/unit/test_fastcfd_dewaxing_fluent_guidance_pack.py`
- `tests/unit/test_postprocessing_public_interface.py`
- `tests/unit/test_public_asset_framework_map.py`
