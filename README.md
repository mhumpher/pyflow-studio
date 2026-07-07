# Pyflow

**A free, open-source, Python-native visual analytics platform — an Alteryx-style drag-and-drop workflow designer powered by a modern big-data engine.**

Pyflow lets analysts build data pipelines by dragging **tools** onto a canvas and wiring them
together — no code required — while data engineers can extend it with custom tools in plain
Python. Under the hood it runs on **Polars** and **DuckDB** for larger-than-memory speed, with an
optional **Dask/Ray** backend for cluster-scale jobs.

```
┌─ Browser (localhost) ───────────────────┐
│  React + React Flow drag-and-drop canvas │
│     [Input]──[Filter]──[Join]──[Output]  │
└─────────────────────┬────────────────────┘
            WebSocket / REST
┌─────────────────────▼────────────────────┐
│  FastAPI  ·  DAG execution engine         │
│  Polars (streaming) · DuckDB · Dask/Ray   │
└───────────────────────────────────────────┘
```

---

## Why Pyflow?

Commercial visual-ETL tools (Alteryx, in particular) are powerful but expensive and closed. The
free alternatives are either Java-based and heavyweight (KNIME), research-oriented (Orange), or
code-first with no visual canvas (Prefect, Dagster). Pyflow aims to be:

| Goal | How |
| --- | --- |
| **Free & open** | Apache-2.0 / MIT licensed, no seat fees, self-hostable |
| **Python-native** | The engine, the tools, and every extension are plain Python |
| **Fast & scalable** | Polars + DuckDB out-of-core by default; Dask/Ray for clusters |
| **Familiar UX** | Alteryx-style canvas, tool palette, config panel, and results grid |
| **Extensible** | Author a custom tool in ~40 lines; ship it as a pip package |

## Key capabilities (target)

- Visual drag-and-drop **workflow canvas** with live run status
- A catalog of **data tools** — input/output, prep, join/blend, transform, parse, reporting
- **Larger-than-memory** execution via Polars streaming and DuckDB
- **Interactive previews** — click any tool to see its output data + column profiling
- **Reproducible workflows** saved as human-readable JSON (`.pyflow`)
- **CLI + headless runner** for scheduling and CI
- **Tool SDK** for building custom tools and shipping them as plugins

---

## Documentation index

The full specification lives in [`docs/`](docs/):

| # | Document | What it covers |
| --- | --- | --- |
| 00 | [Vision & Scope](docs/00-vision-and-scope.md) | Problem, personas, competitive analysis, goals/non-goals, success metrics |
| 01 | [Architecture](docs/01-architecture.md) | System components, tech stack, repository layout, data flow |
| 02 | [Data & Workflow Model](docs/02-data-and-workflow-model.md) | `.pyflow` schema, DAG semantics, type system, field metadata |
| 03 | [Execution Engine](docs/03-execution-engine.md) | Lazy DAG execution, backends, streaming, caching, big-data strategy |
| 04 | [Tool Catalog](docs/04-tool-catalog.md) | The node library — MVP set and full roadmap, per category |
| 05 | [Tool SDK](docs/05-tool-sdk.md) | Authoring custom tools, config schemas, plugin packaging |
| 06 | [Frontend / GUI](docs/06-frontend-gui.md) | Canvas UX, panels, interactions, component breakdown |
| 07 | [Backend API](docs/07-backend-api.md) | REST + WebSocket contract with example payloads |
| 08 | [Roadmap & MVP](docs/08-roadmap.md) | Phased plan, MVP definition, milestone acceptance criteria |
| 09 | [Non-Functional Requirements](docs/09-non-functional.md) | Performance, security, testing, packaging, observability |
| — | [Database Connections](docs/database-connections.md) | Connecting Database Input to SQL Server, Redshift, Oracle, etc. |

**New here? Read 00 → 01 → 08 first** for the vision, the shape of the system, and what ships first.

---

## Planned repository layout

```
pyflow/
├── docs/                      # This specification
├── packages/
│   ├── engine/                # pyflow-engine — pure-Python execution core (no web deps)
│   │   └── pyflow_engine/
│   │       ├── graph/         # DAG model, topological scheduling
│   │       ├── backends/      # polars / duckdb / dask adapters
│   │       ├── tools/         # built-in tool implementations
│   │       ├── types/         # Pyflow type system ↔ Arrow
│   │       └── runtime/       # run context, caching, streaming, events
│   ├── server/                # pyflow-server — FastAPI app (REST + WebSocket)
│   │   └── pyflow_server/
│   └── sdk/                   # pyflow-sdk — public API for tool authors
├── apps/
│   └── studio/                # React + React Flow frontend (Vite + TypeScript)
├── examples/                  # Sample workflows and datasets
├── tests/                     # Cross-package integration & golden-workflow tests
└── pyproject.toml
```

The engine is deliberately isolated from the web layer so workflows can run **headless** (CLI, cron,
CI) with no browser or server involved.

---

## Status

**Phase 0 complete; Phase 1 in progress — the schema-aware config foundation and the formula language
are built and working.** The monorepo, pure-Python engine, FastAPI server, and React Flow Studio are in
place, and you can build multi-step workflows on the canvas, run them, and preview each node's output —
or run the same `.pyflow` headless via the CLI. See [DEVELOPMENT.md](DEVELOPMENT.md) to set it up and
[docs/08-roadmap.md](docs/08-roadmap.md) for the plan.

Built so far:
- `packages/engine` — DAG model, topological scheduler, Polars-backed `Frame`, type system, tool
  registry, **design-time schema pass** (`infer_schemas`), the **formula language**
  (`[Field]` / `IF…ENDIF` → Polars, ~30 functions), and **content-addressed incremental caching**
  (edit one node → only it and its descendants recompute)
- `packages/sdk` — stable tool-authoring surface
- `packages/server` — FastAPI REST + WebSocket app (tool catalog, run, previews, **schema inference**,
  **formula validation**) and the `pyflow` CLI (`studio` / `run` / `validate`)
- `apps/studio` — React + React Flow canvas, palette, **schema-aware config panels** (field pickers,
  multi-select, repeatable groups, a formula editor with live validation), and the results grid

**Tools:** Input Data · **Database Input** · Select · Filter (expression) · Formula · Sort · Sample ·
Unique · Summarize · Cross Tab (pivot) · Unpivot · Transpose · **Text to Columns** · **RegEx** ·
**DateTime** · **JSON Parse** · Join (L/J/R) · Union · **Python** (custom code, multi-in/multi-out) ·
Browse · Output Data (CSV/Parquet/Arrow/JSON/Excel) · **Database Output**. Filter/Formula use the formula
language; Select/Summarize/Join/Sort/Unique use field
pickers driven by the design-time schema pass; Union fans in N inputs; Output tools write at run time
only. **Database Input/Output** connect to SQL Server, Redshift, Oracle, Postgres, MySQL, or SQLite
(reads via ConnectorX/SQLAlchemy; writes via SQLAlchemy) — see the
[database connection guide](docs/database-connections.md).

This is a complete no-code loop — **ingest → prep → blend → transform → export**.

## A note on the name

There are existing PyPI projects named `pyflow` (an environment manager) and **PyFlow** (a visual
*scripting* node editor). "Pyflow" is fine as an internal working name, but the **published
distribution name will need to differ** — e.g. `pyflow-studio`, `pyflow-analytics`, or a fresh brand.
Treat the product name as an open decision tracked in [Vision & Scope](docs/00-vision-and-scope.md).

## Security

Pyflow is **local-first and single-user** by default (the server binds to `127.0.0.1`, no auth). Note
that the **Python tool runs arbitrary code** and workflows can embed **database credentials** — so treat
`.pyflow` files like scripts and use `${ENV_VAR}` for secrets. See [SECURITY.md](SECURITY.md).

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and
[DEVELOPMENT.md](DEVELOPMENT.md).

## Disclaimer

Pyflow is an early-stage, experimental project provided "as is" under the license below, without
warranty. **"Alteryx" is a trademark of Alteryx, Inc.** Pyflow is an independent, community-built project
and is **not affiliated with, endorsed by, or sponsored by Alteryx, Inc.** — references to Alteryx
describe interoperability goals and familiar concepts only.

## License

Licensed under the **[Apache License 2.0](LICENSE)** (permissive, with a patent grant). See also
[NOTICE](NOTICE).
