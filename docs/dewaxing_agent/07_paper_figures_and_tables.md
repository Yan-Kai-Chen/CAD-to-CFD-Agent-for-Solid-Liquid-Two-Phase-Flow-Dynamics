# Dewaxing Paper Figures And Tables

Status: `active paper-asset guide`

Paper-facing assets are generated from validation, Agent iteration, and
guidance packs. They should be reproducible from commands and small public
fixtures where possible.

## Implementation Assets

- `src/fromcad2cfd_fastcfd/dewaxing_paper_evidence_pack.py`
- `src/fromcad2cfd_fastcfd/dewaxing_fluent_guidance_pack.py`
- `tests/unit/test_fastcfd_dewaxing_paper_evidence_pack.py`
- `tests/unit/test_fastcfd_dewaxing_fluent_guidance_pack.py`

## Expected Generated Assets

- manuscript methods section;
- manuscript results section;
- figure captions;
- six evidence tables;
- seven statistical or workflow figures from the paper evidence pack;
- one FastFluent-to-Fluent workflow figure from the guidance pack.

Current figure style:

```text
nature_soft_statistical
```

## Public Command Pattern

Generate paper evidence after producing public validation and iteration packs:

```powershell
python -m fromcad2cfd fastcfd compile-dewaxing-paper-evidence-pack `
  --validation-pack sandbox/output/dewaxing_native_validation_pack `
  --iteration-pack sandbox/output/dewaxing_agent_iteration_pack `
  --output-dir sandbox/output/dewaxing_paper_evidence_pack `
  --format markdown
```

The workflow figure should be treated as the current project-logic baseline.
Generated figure outputs belong under `sandbox/output/` unless a small polished
public figure is deliberately promoted later.
