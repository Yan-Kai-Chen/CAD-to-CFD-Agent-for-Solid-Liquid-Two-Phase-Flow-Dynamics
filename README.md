# An Agent Framework for FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dynamics

This repository is the public software workspace for **An Agent Framework for
FastFluent-to-Fluent Simulation of Complex Solid-Liquid Dynamics**.

The Python package is still named `fromcad2cfd`. It provides auditable,
agent-assisted workflows for CAD preparation, fast CFD evidence generation,
Fluent setup planning, and post-run interpretation.

The project does not replace SolidWorks, Siemens NX, HyperMesh, or ANSYS
Fluent. It keeps the agent layer explicit: every important step writes inputs,
checks, reports, and decision artifacts before moving to a higher-cost stage.

## Workflow Blocks

| Block | Purpose | Typical output |
| --- | --- | --- |
| `Modeling` | Prepare CAD geometry through bounded SolidWorks, NX, and mesh-solidification workflows. | Repaired/copied solids, export reports, geometry checks. |
| `FastFluent` | Generate fast native CFD evidence before full Fluent work. | Physics passports, Result Packs, QoIs, agent decisions. |
| `Meshing` | Validate meshing plans and controlled local meshing adapters. | Mesh preflight reports and adapter-safe plans. |
| `Fluent` | Validate Fluent setup contracts and summarize Fluent-side results. | Solver-plan checks, patch previews, monitor summaries, handoff reports. |

## Start Here

Install for local development:

```powershell
python -m pip install -e ".[dev]"
python -m fromcad2cfd --help
```

Run the current FastFluent agent workflow demo:

```powershell
python -m fromcad2cfd fastcfd workflow demo `
  --output-dir sandbox/output/fastfluent_s7_workflow_demo `
  --mode native_advisory `
  --format markdown
```

This writes staged workflow artifacts, optional native advisory evidence, a
Result Pack, `workflow_manifest.json`, and `agent_decision.json`. It does not
launch Fluent.

## Public Asset Organization

The public assets are split by reader need rather than by old folder history:

| Reader path | Entry point | Use it for |
| --- | --- | --- |
| Engineering workflow | [Architecture](docs/architecture.md) | The four-block `Modeling` / `FastFluent` / `Meshing` / `Fluent` structure. |
| Agent validation | [Agent benchmark ladder](docs/agent_benchmark_ladder/README.md) | The compact `4+1` public CFD benchmark ladder. |
| Paper case study | [Dewaxing Agent case study](docs/dewaxing_agent/README.md) | The FastFluent-to-Fluent dewaxing route used for the paper-facing case. |

The detailed rule for retaining and splitting original public GitHub assets is
in [Public asset framework map](docs/public_asset_framework_map.md).

## Repository Map

```text
src/
  fromcad2cfd/                    # top-level CLI
  fromcad2cfd_fastcfd/            # FastFluent workflow and evidence layer
  fromcad2cfd_solidworks/         # SolidWorks automation surface
  fromcad2cfd_nx/                 # Siemens NX automation surface
  fromcad2cfd_hypermesh_meshing/  # HyperMesh meshing interface
  fromcad2cfd_fluent_solver/      # Fluent solver planning interface
  fromcad2cfd_postprocessing/     # monitor parsing and summaries
cpp/
  fastfluent_core/                # C++ FastFluent numerical core
docs/
  fastcfd/                        # FastFluent contracts and runbooks
  agent_benchmark_ladder/         # public Agent CFD benchmark ladder
  dewaxing_agent/                 # paper-facing dewaxing Agent case study
examples/
  fastcfd/                        # public FastFluent examples
  fluent_solver/                  # public solver-plan examples
  postprocessing/                 # public monitor/result fixtures
tests/
  unit/                           # Python unit tests
```

## Main Documentation

- [Architecture](docs/architecture.md)
- [Documentation index](docs/index.md)
- [Public asset framework map](docs/public_asset_framework_map.md)
- [FastFluent quickstart](docs/fastcfd/quickstart.md)
- [Agent benchmark ladder](docs/agent_benchmark_ladder/README.md)
- [Dewaxing Agent case study](docs/dewaxing_agent/README.md)
- [FastFluent server Codex deployment runbook](docs/fastcfd/SERVER_CODEX_DEPLOYMENT_RUNBOOK.md)
- [Fluent solver interface](docs/fluent_solver/interface_draft.md)
- [Post-processing interface](docs/postprocessing/interface_draft.md)

## Validation

Run the full Python suite:

```powershell
python -m pytest
```

Latest checked local state on 2026-06-28:

- Full Python suite: `424 passed`.
- Public asset/title suite: `5 passed`.
- Wheel build: `fromcad2cfd-0.2.0-py3-none-any.whl` built successfully through
  a short-path `subst` workspace.

Detailed benchmark, dewaxing, and FastFluent-to-Fluent evidence is kept in the
documentation paths above instead of being repeated on this page.

## Public Data Policy

The public repository keeps source code, tests, public examples, synthetic
fixtures, and documentation. It must not contain private CAD geometry,
proprietary CAD exports, private meshes, Fluent case/data files, license files,
machine-specific absolute paths, or generated local solver outputs.

## Licensing

The Python framework is published under the root Apache-2.0 license.

The C++ FastFluent core retains its original GPLv3 license; see
[`cpp/fastfluent_core/LICENSE`](cpp/fastfluent_core/LICENSE).

## Citation

If you use this project in academic work, cite it using
[CITATION.cff](CITATION.cff).
