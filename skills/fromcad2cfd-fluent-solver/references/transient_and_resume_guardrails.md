# Transient And Resume Guardrails

Validated private-project lessons preserved as public rules:

- Run short stability checks before long formal runs.
- Always write global and wall monitor files under a run folder.
- Use autosave with sortable time-step suffixes.
- For interrupted runs, prefer the latest complete checkpoint pair.
- Reject suspiciously small checkpoint data files.
- Do not call `standard_initialize()` during a resume.
- On Fluent 2024 R1 adaptive resumes, `total_time` should be the absolute final
  flow time, not the remaining duration.
- Keep progress and heat-flow monitors separate from solver execution.

Monitor interpretation:

- Wall pressure is a normal fluid-load proxy.
- Wall shear is a tangential fluid-load proxy.
- Neither is solid structural stress.
