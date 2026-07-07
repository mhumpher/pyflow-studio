# 00 — Vision & Scope

## 1. The problem

Data analysts spend most of their time on **preparation and blending** — cleaning, joining,
reshaping, and aggregating data before any analysis happens. Two families of tools address this:

- **Visual ETL platforms** (Alteryx, KNIME, RapidMiner) — approachable drag-and-drop canvases, but
  either expensive and proprietary (Alteryx starts at thousands of USD/user/year) or heavyweight and
  non-Python (KNIME is JVM-based).
- **Code-first frameworks** (pandas, Polars, dbt, Prefect, Dagster) — powerful and free, but require
  fluent programming and give non-engineers no visual model of the pipeline.

There is a gap: **no free, Python-native tool offers an Alteryx-quality visual canvas backed by a
modern, fast, larger-than-memory engine.** Pyflow targets exactly that gap.

## 2. Vision statement

> **Pyflow is a free, open-source visual analytics platform where anyone can build fast, reproducible
> data pipelines by dragging and connecting tools — and where every tool is just Python.**

Analysts get Alteryx-style productivity. Engineers get a hackable, pip-installable Python codebase.
Both get Polars/DuckDB performance and workflows that run headless in production.

## 3. Target users (personas)

| Persona | Description | Primary need |
| --- | --- | --- |
| **Ana — the analyst** | Excel/SQL-literate, not a programmer. Preps data daily. | Build & re-run pipelines visually; trust the results; export to Excel/DB. |
| **Devin — the data engineer** | Writes Python/SQL. Owns pipelines. | Extend Pyflow with custom tools; run workflows in CI/cron; scale to big data. |
| **Priya — the analytics lead** | Manages a small team. | Standardize/share reusable workflows; reproducibility; no per-seat license cost. |
| **Sam — the student/hobbyist** | Learning data work. | A free, friendly, local tool to learn ETL concepts visually. |

**Primary persona for the MVP: Ana.** The MVP must let a non-programmer complete a real
prep-and-blend task end to end without writing code.

## 4. Competitive landscape / prior art

| Tool | Model | Free? | Python? | Engine | Notes |
| --- | --- | --- | --- | --- | --- |
| **Alteryx Designer** | Visual canvas | ✗ (costly) | Partly | Proprietary | The UX benchmark to match |
| **KNIME Analytics Platform** | Visual canvas | ✓ (core) | JVM + Py nodes | JVM | Closest free analog; heavy, non-Python |
| **RapidMiner / Orange** | Visual canvas | Partly | Py (Orange) | In-memory | ML/research focus, weaker ETL/scale |
| **n8n / Node-RED** | Visual flows | ✓ | JS | Event/API | Automation, not data-table analytics |
| **Prefect / Dagster** | Code + DAG UI | ✓ | ✓ | Any | Orchestration, *no* visual authoring canvas |
| **PyFlow / Ryven** | Visual node editor | ✓ | ✓ | Generic | Python *scripting* graphs, not data-analytics tools |
| **Airbyte / Meltano** | Connector ELT | ✓ | Mixed | Various | Ingestion, not interactive prep/blend |

**Positioning:** Pyflow = KNIME's approachability + Alteryx's UX polish + Polars/DuckDB speed +
a pure-Python, pip-installable, genuinely free codebase.

## 5. Goals

1. A visual canvas where a non-programmer can build a working prep→blend→output pipeline.
2. Interactive feedback: preview any tool's output and column profile instantly on realistic samples.
3. Performance that beats a pandas-based equivalent and handles datasets larger than RAM.
4. Reproducible, diff-able, version-controllable workflow files.
5. Workflows that run **headless** (CLI/scheduler/CI) identically to the GUI.
6. A tool SDK simple enough to write a useful custom tool in an afternoon.
7. Local-first and private by default — no data leaves the machine unless the user connects a source.

## 6. Non-goals (for the foreseeable roadmap)

- **Not** a general-purpose BI/dashboarding tool (use Superset/Metabase/PowerBI downstream).
- **Not** a real-time streaming/event bus (batch and micro-batch only; no Kafka-style always-on).
- **Not** a full orchestration platform replacing Airflow/Dagster (Pyflow has a *simple* scheduler; it
  can be triggered *by* those tools).
- **Not** a notebook (complements Jupyter; does not replace it).
- **Not** a general Python visual-scripting IDE (data tables are the unit of work, not arbitrary objects).
- **Not** a cloud SaaS at launch — self-hosted/local first; hosted multi-user is a late phase.

## 7. Guiding principles

- **Local-first & private.** Everything runs on the user's machine by default.
- **The engine is independent of the GUI.** Same code runs a workflow in the browser or in cron.
- **Lazy and columnar.** Build a query plan; execute once; push down filters and projections.
- **Text-first artifacts.** Workflows are readable JSON that diffs cleanly in Git.
- **Progressive disclosure.** Simple tasks are simple; power (SQL, Python, macros) is one click deeper.
- **Extensibility is a first-class feature, not an afterthought.**

## 8. Success metrics

**MVP (validation):**
- A first-time analyst builds and runs a 6+ tool CSV→clean→join→summarize→Excel workflow in <15 min
  with no documentation beyond tooltips.
- Pyflow processes a 5 GB CSV join+aggregate on a 16 GB laptop without OOM.
- A developer scaffolds and registers a working custom tool in <30 min following the SDK guide.

**Post-MVP (adoption):**
- GitHub stars / active installs (telemetry opt-in only).
- Number of community-contributed tools/plugins.
- Median workflow size and re-run frequency (opt-in usage metrics).

## 9. Key open decisions

| Decision | Options | Owner | Status |
| --- | --- | --- | --- |
| Published product/package name | `pyflow-studio`, new brand | Product | **Open** (see README naming note) |
| License | Apache-2.0 vs MIT | Eng | Leaning Apache-2.0 |
| Formula language | Custom mini-language vs SQL expr vs Python-subset | Eng | See [Tool Catalog](04-tool-catalog.md#formula) |
| Desktop packaging | pywebview shell vs browser-only | Eng | Browser-first; shell later |
