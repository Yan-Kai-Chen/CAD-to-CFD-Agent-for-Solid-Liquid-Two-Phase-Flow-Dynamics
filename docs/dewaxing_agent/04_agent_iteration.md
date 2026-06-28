# Dewaxing Agent Iteration

Status: `active iteration guide`

The Agent iteration campaign records how candidate assumptions were proposed,
checked, rejected, and accepted.

## Implementation Assets

- `src/fromcad2cfd_fastcfd/dewaxing_agent_iteration_pack.py`
- `tests/unit/test_fastcfd_dewaxing_agent_iteration_pack.py`

## Current Campaign Summary

- `3` rounds;
- `16` candidates;
- `46` native solver runs;
- `80,140,200` cell-time steps;
- `5` fitted candidates rejected during stability review;
- accepted candidate `path106_initial6`.

The main point is that the Agent did not simply choose the best-fit candidate.
It chose a stable candidate after validation review.

## Accepted Reduced-Order Edits

The accepted candidate uses reduced-order assumption edits:

- `domain.thickness_m` scale `1.06`;
- `initial.temperature_K` offset `+6.0`.

These are not measured physical geometry or material changes. They are
screening assumptions for the reduced-order model.

## Public Command

```powershell
python -m fromcad2cfd fastcfd run-dewaxing-agent-iteration-pack `
  --output-dir sandbox/output/dewaxing_agent_iteration_pack `
  --format markdown
```

## Review Rule

The accepted candidate must remain tied to stability review and claim
boundaries. Do not present it as a calibrated final Fluent result.
