# Server Codex Deployment Runbook for FastFluent

Date: 2026-06-24

Repository: `Yan-Kai-Chen/CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics`

Minimum code baseline: `e4c79ea`

Deployment recommendation: use the current `main` commit that contains this
runbook. Do not check out `e4c79ea` exactly unless this runbook has already been
copied outside the repository.

## Purpose

This runbook is written for a Codex agent working on a server. Its job is to
clone the public repository, deploy the FastFluent/FastCFD workflow layer, run
the current server-safe validation gates, and prepare a clean handoff toward
server-side Fluent work.

The server Codex must keep the following boundary:

- FastFluent evidence is preliminary engineering evidence.
- S7 workflow output is valid for agent workflow control and screening.
- S7 does not launch Fluent and does not claim final CFD validation.
- Real Fluent execution requires a licensed Fluent environment and a separate
  server-side execution plan.

## Hard Rules

1. Do not commit private CAD, STL, mesh, Parasolid, NX, SolidWorks, Fluent
   case/data, or generated solver-output files.
2. Keep generated outputs under ignored folders such as `sandbox/output/`,
   `sandbox/reports/`, or local server scratch directories.
3. Do not edit global Codex, Fluent, ANSYS, SSH, or shell configuration unless
   the human explicitly asks for it.
4. Do not run arbitrary source-generation, arbitrary Python, arbitrary shell,
   or unreviewed Fluent scripts as part of this deployment.
5. Treat Fluent execution as a later gated phase. This runbook only validates
   the portable public contract and FastFluent evidence layer.

## Required Server Tools

Minimum:

- Git.
- Python 3.10 or newer.
- `pip` and Python virtual environment support.
- Network access to GitHub.

For optional C++ FastFluent real-backend smoke tests:

- C++17 compiler.
- GNU Make or compatible make tool.
- On Linux, `build-essential` is usually sufficient.
- On Windows, MinGW-w64 or a compatible GNU toolchain is recommended.

For later Fluent integration:

- Licensed ANSYS Fluent installation.
- Fluent executable visible through a known path or module environment.
- Optional PyFluent installation, if the server workflow will use PyFluent.

## Phase 1: Clone The Repository

Use SSH if the server already has GitHub SSH access:

```bash
git clone git@github.com:Yan-Kai-Chen/CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics.git
cd CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics
```

HTTPS fallback:

```bash
git clone https://github.com/Yan-Kai-Chen/CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics.git
cd CAD-to-CFD-Agent-for-Solid-Liquid-Two-Phase-Flow-Dynamics
```

Pin or record the commit:

```bash
git checkout main
git pull --ff-only
git rev-parse HEAD
```

Acceptance:

- `git rev-parse HEAD` returns a reviewed commit at or after `e4c79ea`.
- `git status --short` is clean.

## Phase 2: Create The Python Environment

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Basic checks:

```bash
python -m fromcad2cfd --version
python -m fromcad2cfd --help
python -m fromcad2cfd fastcfd --help
```

Acceptance:

- `fromcad2cfd` imports successfully.
- The `fastcfd` command group lists `workflow`, `transport`, `unstructured`,
  `result-pack`, and `solver-capability-matrix`.

## Phase 3: Run Public Validation Tests

Run the full Python test suite:

```bash
python -m pytest -q
```

Run the FastFluent-focused suite:

Linux:

```bash
python -m pytest tests/unit/test_fastcfd*.py -q
```

Windows PowerShell:

```powershell
$files = Get-ChildItem -Path tests\unit -Filter 'test_fastcfd*.py' | ForEach-Object { $_.FullName }
python -m pytest $files -q
```

Acceptance:

- Full test suite passes.
- FastFluent-focused suite passes.
- Record the exact pass count in the server deployment report.

Reference local baseline from the publishing machine:

- Full suite: `396 passed`.
- FastFluent suite: `277 passed`.

The server result may be higher if new commits were added after `e4c79ea`.

## Phase 4: Run The Recommended S7 Agent Workflow

Run the server-safe native advisory workflow:

```bash
python -m fromcad2cfd fastcfd workflow demo \
  --output-dir sandbox/output/server_s7_native_advisory \
  --mode native_advisory \
  --format json
```

Windows PowerShell:

```powershell
python -m fromcad2cfd fastcfd workflow demo `
  --output-dir sandbox\output\server_s7_native_advisory `
  --mode native_advisory `
  --format json
```

Inspect the final decision:

Linux:

```bash
cat sandbox/output/server_s7_native_advisory/agent_decision.json
```

Windows PowerShell:

```powershell
Get-Content sandbox\output\server_s7_native_advisory\agent_decision.json
```

Expected key status:

```json
{
  "status": "native_advisory_complete",
  "can_support_workflow_decision": true,
  "can_support_screening_decision": true,
  "can_support_final_cfd_validation": false
}
```

Expected artifact groups:

- `01_flow_pack/`
- `02_route_selection/`
- `03_route_plan/`
- `04_execution_gate/`
- `05_controlled_runner/`
- `06_native_result/`
- `07_result_pack/`
- `workflow_manifest.json`
- `stage_status.json`
- `agent_decision.json`
- `workflow_report.md`

Acceptance:

- Command exits with code `0`.
- Top-level workflow status is `native_advisory_complete`.
- `07_result_pack/result_pack.json` exists.
- `agent_decision.json` explicitly says final CFD validation is not supported.

## Phase 5: Run Focused FastFluent Evidence Commands

Capability and registry:

```bash
python -m fromcad2cfd fastcfd capabilities --format markdown
python -m fromcad2cfd fastcfd registry --format markdown
python -m fromcad2cfd fastcfd solver-capability-matrix --format markdown
```

S6 scalar transport evidence:

```bash
python -m fromcad2cfd fastcfd transport demo \
  --output-dir sandbox/output/server_s6_transport_alpha \
  --quantity alpha \
  --format json

python -m fromcad2cfd fastcfd result-pack compile-native \
  sandbox/output/server_s6_transport_alpha/status.json \
  --output-dir sandbox/output/server_s6_transport_alpha_pack \
  --format json
```

Unstructured mesh gateway:

```bash
python -m fromcad2cfd fastcfd unstructured inspect-mesh \
  examples/unstructured/channel2d.msh \
  --format json
```

Unstructured channel validation:

```bash
python -m fromcad2cfd fastcfd unstructured solve-channel-validation \
  examples/unstructured/unit_square_4x4.msh \
  --pressure-drop 1.0 \
  --linear-solver sparse-cg \
  --format json
```

Turbulence ladder evidence:

```bash
python -m fromcad2cfd fastcfd unstructured solve-turbulence-ladder \
  --output-dir sandbox/output/server_turbulence_ladder \
  --iterations 8 \
  --format json
```

Acceptance:

- Each command exits with code `0`.
- Every output directory contains JSON and Markdown evidence.
- Any warning must be copied into the server deployment report.

## Phase 6: Check The C++ FastFluent Core

The C++ core is vendored under:

```text
cpp/fastfluent_core
```

Run preflight:

```bash
python -m fromcad2cfd fastcfd preflight --source-root cpp/fastfluent_core
```

Acceptance:

- `source_root_status` is `found`.
- Compiler and make-tool status are recorded.
- If compiler or make is missing, stop and report the missing dependency
  instead of editing global build configuration.

Optional controlled cavity2d backend smoke:

```bash
python -m fromcad2cfd fastcfd write-cavity2d-job \
  --project server_cavity_smoke \
  --model-name server_cavity \
  --nx 40 \
  --ny 40 \
  --total-steps 20 \
  --output-interval 10
```

The command prints a `job_path`. Use that exact path in the next command:

```bash
python -m fromcad2cfd fastcfd run-fastfluent-cavity2d-job \
  --job-file <job_path_from_previous_command> \
  --source-root cpp/fastfluent_core \
  --build-timeout-sec 300 \
  --run-timeout-sec 300
```

Acceptance:

- If the compiler toolchain is available, the controlled cavity job builds and
  runs or reports a precise build/run error.
- Do not retry by randomly changing C++ source files.
- If it fails, preserve the build log and write a short diagnosis.

## Phase 7: Server Fluent Availability Check

This phase only checks availability. Do not launch a production Fluent solve
yet.

Linux:

```bash
which fluent || true
fluent -v || true
python - <<'PY'
try:
    import ansys.fluent.core as pyfluent
    print("pyfluent_available", pyfluent.__version__)
except Exception as exc:
    print("pyfluent_unavailable", repr(exc))
PY
```

Windows PowerShell:

```powershell
where.exe fluent
fluent -v
python -c "import ansys.fluent.core as pyfluent; print(pyfluent.__version__)"
```

Acceptance:

- Record whether Fluent exists.
- Record Fluent version, executable path, and PyFluent availability if present.
- Do not modify global ANSYS or license settings.

## Phase 8: Fluent Handoff Preview Without Launching Fluent

Run public patch-preview artifacts:

```bash
python -m fromcad2cfd fastcfd existing-passport-patch-demo \
  --output-dir sandbox/output/server_existing_passport_patch_demo

python -m fromcad2cfd fluent-solver plan-v2-patch-preview-demo \
  --output-dir sandbox/output/server_fluent_plan_v2_patch_preview
```

Acceptance:

- Both commands complete without launching Fluent.
- `solver_plan_patch.json` style outputs are generated.
- The report states that these are preview or planning artifacts only.

## Required Server Deployment Report

Create a report under:

```text
sandbox/reports/server_deployment/SERVER_DEPLOYMENT_REPORT_YYYYMMDD_HHMMSS.md
```

The report must include:

1. Server OS and shell.
2. Git remote URL.
3. Commit hash.
4. Python version.
5. Virtual environment path.
6. Installation command used.
7. Full test-suite result.
8. FastFluent-focused test result.
9. S7 workflow status and output directory.
10. S6 transport status and Result Pack directory.
11. Unstructured validation status.
12. C++ core preflight result.
13. Optional C++ cavity smoke result.
14. Fluent executable path and version, if available.
15. PyFluent availability, if checked.
16. Blocking errors.
17. Recommended next step.

## Expected Final Server Codex Reply

The server Codex should report:

```text
Repository: <path>
Commit: <hash>
Python environment: <path>
Tests: <pass/fail with count>
S7 workflow: <status>
FastFluent C++ preflight: <status>
Optional C++ smoke: <status or skipped>
Fluent availability: <available/unavailable, version/path if available>
Main output root: <path>
Deployment report: <path>
Blocking issues: <none or list>
```

## Stop Conditions

Stop and report instead of improvising if any of the following occurs:

- GitHub authentication fails.
- Python package installation fails.
- Full tests fail.
- S7 does not reach `native_advisory_complete`.
- C++ build fails with unclear compiler or dependency errors.
- Fluent license or executable discovery is ambiguous.
- Any private model, mesh, or case file would need to be copied into the public
  repository.

## Server-Side Next Step After This Runbook

After this runbook passes, the next phase is a separate Fluent execution bridge:

1. Consume S7 `Result Pack` and FastFluent `solver_plan_patch.json` artifacts.
2. Map them to a server-local Fluent setup plan.
3. Run a small public or synthetic Fluent case first.
4. Parse Fluent monitors with `fromcad2cfd post`.
5. Only then move to private research geometry and production Fluent cases.

That later Fluent bridge should be implemented as a server-specific adapter and
kept separate from portable public repository contracts until it is cleaned and
reviewed.
