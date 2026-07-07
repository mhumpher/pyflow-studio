# 08 — Roadmap & MVP

> **Note:** this is the *original* phased vision, written before implementation. Phase 0 and most of
> Phase 1 have since shipped. For the current, honest status and the prioritized plan for what's next,
> see the living **[ROADMAP.md](../ROADMAP.md)** at the repo root. This document is retained as the
> initial concept and for its acceptance-criteria detail.

A phased plan from empty repo to a fully featured platform. Each phase has a **theme**, a **deliverable**,
and **acceptance criteria**. Phases are sequential but tools within a phase can be parallelized.

---

## Phase 0 — Foundations (repo & skeleton)

**Theme:** Make the walking skeleton runnable end-to-end with one trivial tool.

- Monorepo scaffold (`packages/engine`, `packages/server`, `packages/sdk`, `apps/studio`) per
  [Architecture](01-architecture.md).
- Engine core: DAG model, topological scheduler, `Tool` base class, tool registry, Arrow/Polars `Frame`
  wrapper, run context + event bus.
- Server: FastAPI app, `GET /tools`, workflow CRUD, `WS run`, static hosting of the built frontend.
- Studio: React Flow canvas, palette, drag-to-add, connect edges, config panel shell, results grid shell.
- Dev tooling: `uv`/`hatch`, Vite, pre-commit (ruff/black/mypy, eslint/prettier), pytest, CI.
- **Two tools only:** `input.file` (CSV) and `output.browse`.

**Acceptance:** drag CSV Input → Browse, connect, **Run**, see rows in the grid — through the real
server and engine.

---

## Phase 1 — MVP (the no-code loop)  ⟵ *first releasable milestone*

**Theme:** A non-programmer completes a real prep→blend→transform→output task with no code.

- **Tool set (~18)** from [Tool Catalog §1](04-tool-catalog.md): Input Data, Text Input, Output Data,
  Browse, Select, Filter, Formula, Sort, Sample, Unique, Data Cleansing, Join, Union, Append Fields,
  Summarize, Cross Tab, Transpose, Select Records.
- **Formula/expression language** (v1) compiling to Polars, with the Monaco editor + autocomplete.
- **Engine:** design-time schema pass; lazy Polars execution; **streaming** for large inputs;
  content-hash **cache** + incremental re-runs; per-node events/messages; cancellation.
- **Frontend:** full canvas UX (multi-anchor nodes, status badges, undo/redo, copy/paste, containers,
  annotations), auto-generated config panels, field pickers bound to real schema, Data/Profile/Messages/
  Metadata tabs.
- **File I/O:** CSV, Parquet, Arrow, JSON, Excel (read/write).
- **Persistence:** save/load `.pyflow`; autosave to session.
- **CLI:** `pyflow studio`, `pyflow run file.pyflow`, `pyflow validate`.
- **Docs:** getting-started + a worked example workflow with sample data.

**Acceptance (maps to [success metrics](00-vision-and-scope.md#8-success-metrics)):**
1. First-time analyst builds & runs a 6+ tool CSV→clean→join→summarize→Excel workflow in <15 min.
2. A 5 GB CSV join+aggregate completes on a 16 GB laptop without OOM (streaming/DuckDB path).
3. Editing one node re-runs only that node + descendants (cache verified).
4. The same `.pyflow` runs identically via `pyflow run` headless.

---

## Phase 2 — Depth & data sources

**Theme:** Handle messy, real-world data and connect to databases; add power-user escape hatches.

- **Parse pack:** Text to Columns, RegEx, DateTime, JSON Parse. ⭑
- **Database I/O:** `input.db` / `output.db` via SQLAlchemy/ADBC + DuckDB, with predicate pushdown. ⭑
- **Developer tools:** **SQL tool** (DuckDB SQL over inputs) and **Python tool** (sandboxed frame in/out). ⭑
- **Prep depth:** Multi-Row Formula, Multi-Field Formula, Auto Field, Imputation. ⭑
- **Blend depth:** Find & Replace; Join Multiple.
- **Directory/multi-file & cloud storage** input via `fsspec` (S3/GCS/Azure).
- **DuckDB backend** wired as an auto-selected path for big joins/aggregations + out-of-core.
- **Richer profiling** (distributions, outliers) and preview paging improvements.

**Acceptance:** ingest from Postgres + a folder of CSVs, parse/clean with RegEx/DateTime, blend, and
write to Parquet and a DB table; a 50 GB out-of-core aggregation completes via DuckDB on a laptop.

---

## Phase 3 — Scale & reuse

**Theme:** Cluster-scale execution, reusable workflows, and automation.

- **Distributed backend:** Dask and/or Ray behind the `Frame` abstraction; auto/manual backend selection;
  connect to an existing cluster.
- **Macros:** package a container/sub-workflow as a **reusable tool** with exposed parameters; batch &
  iterative macros (loop over groups / until condition).
- **Parameters & workflow variables:** run-time inputs (`--var`), enabling templated/parameterized runs.
- **Scheduler & headless automation:** a simple built-in scheduler (cron-like) + first-class triggering
  from Airflow/Dagster/CI; run history & logs.
- **Analytic apps (lightweight):** a form UI wrapping a parameterized workflow for non-editing users.

**Acceptance:** a parameterized workflow runs on a Dask cluster over a partitioned Parquet dataset; a
macro authored once is reused in three workflows; a scheduled nightly run produces logged outputs.

---

## Phase 4 — Platform (multi-user & ecosystem)

**Theme:** Teams, sharing, governance, and an extension ecosystem.

- **Server mode:** multi-user self-hosted deployment; workflow **gallery**/sharing; auth (OIDC/token) +
  per-workflow RBAC; per-connection secret scoping.
- **Collaboration:** versioning/history, comments, and (stretch) concurrent editing.
- **Governance:** lineage view, run auditing, data-source cataloging.
- **Plugin marketplace:** discover/install community tool packs; signed plugins.
- **Advanced tool packs** as optional plugins: **Predictive/ML** (scikit-learn), **Spatial** (geopandas),
  **Time Series**, **Text Mining**, **In-Database** (Ibis-style multi-backend pushdown).
- **Reporting:** Table/Chart/Render tools → PDF/HTML/Excel reports.
- **Desktop app:** pywebview/Tauri shell bundling Python + frontend for one-click install.

**Acceptance:** a team shares and runs governed workflows on a hosted server with auth; a community plugin
installs from the marketplace and its tools appear in the palette; a spatial/ML pack runs as an optional
plugin without bloating the core.

---

## Sequencing rationale & risks

| Decision | Why |
| --- | --- |
| Engine-first, thin GUI in Phase 0 | De-risk the hardest part (execution/scale) before polishing UX |
| Polars-only in MVP; DuckDB in Phase 2; Dask/Ray in Phase 3 | Ship value fast; add scale where it pays off; keep the `Frame` abstraction honest by having ≥2 backends before claiming "pluggable" |
| Formula language in MVP | It's the connective tissue for Filter/Formula/Summarize; late arrival would rework tools |
| Macros before marketplace | Reuse is more valuable than distribution early on |
| Multi-user last | Local-first delivers value with far less security/ops surface |

**Top risks to watch:**
- **Backend abstraction leakage** — validate it with DuckDB (P2) and Dask (P3) early; don't let Polars
  idioms ossify the `Frame` API.
- **UX for big results** — never ship full data to the browser; enforce sampled previews from day one.
- **Scope creep in tools** — the MVP list is a contract; new tools wait for their phase.
- **User-code sandboxing** (Python/SQL tools) — treat as a security feature, design before P2 ships them.
- **Name/licensing** — resolve the published-name collision before any public release.
