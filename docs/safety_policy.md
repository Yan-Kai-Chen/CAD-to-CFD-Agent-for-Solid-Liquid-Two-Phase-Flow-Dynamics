# Safety Policy

The framework uses conservative engineering automation rules.

## Required Rules

- Do not modify original inputs in place.
- Copy inputs into a working/output folder before edits.
- Never overwrite an existing output file.
- Use timestamped output names.
- Inspect features, dimensions, materials, and configurations before model edits.
- Stop when a target dimension or feature cannot be uniquely identified.
- Rebuild after every edit.
- Stop when rebuild fails.
- Export STEP after successful operations.
- Generate Markdown and JSON reports.

## Disallowed Agent Tool Patterns

- Arbitrary code execution exposed as an agent tool.
- Raw COM call exposure.
- Unrestricted delete or overwrite tools.
- Macro execution without explicit human review.
