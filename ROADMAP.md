# Pyflow roadmap

This is the **living roadmap** — an honest snapshot of what's built and a prioritized plan for what's
next. It supersedes the original phased vision in [docs/08-roadmap.md](docs/08-roadmap.md), which
described the initial concept before implementation.

Milestones are ordered by priority, **not dated** — Pyflow is an early-stage, community-built project
and priorities may shift. Legend: ✅ done · 🚧 in progress · 📋 planned.

---

## Where things stand today

**Built and working:**

- ✅ Monorepo: pure-Python **engine**, tool-authoring **SDK**, FastAPI **server**, React Flow **Studio**
- ✅ Visual canvas — drag/drop, multi-anchor tools, live per-node run status, sampled previews + profiling
- ✅ **22 tools**: file + database I/O (SQL Server / Redshift / Oracle / Postgres / MySQL / SQLite), prep
  (Select, Filter, Formula, Sort, Sample, Unique), blend (Join, Union), the four Transform reshapers
  (Summarize, Cross Tab, Unpivot, Transpose), a Parse pack (Text to Columns, RegEx, DateTime, JSON), and
  a custom multi-in/multi-out **Python tool**
- ✅ Alteryx-style **formula language** (`[Field]`, `IF…ENDIF`, ~30 functions) compiled to Polars
- ✅ **Design-time schema inference** with cache-aware propagation (data-dependent columns appear after a run)
- ✅ **Content-addressed incremental caching** (edit one node → only it and its descendants recompute)
- ✅ Headless CLI (`pyflow run` / `validate`) — the same engine runs in the GUI and in a terminal

**Honest limitations right now:**

- ⚠️ The execution engine is **Polars-only.** DuckDB (out-of-core), Dask/Ray (cluster), and true
  streaming are described in the specs but **not yet implemented** — several tools materialize fully in
  memory. Pyflow handles small-to-medium data well today; the "larger-than-memory" story is a goal, not
  a current fact.
- ⚠️ **No automated tests or CI**, no PyPI package, no workflow save/open in the UI, and the developer
  tools (Python/SQL) run **unsandboxed**. These are the focus of the milestones below.

---

## Milestone 1 — Trustworthy (accuracy · tests · CI)

**Goal: the repo tells the truth and is verifiably correct.** This is the top priority now that the code
is public.

- 📋 **Docs-accuracy pass** — align all docs with the Polars-only reality; mark DuckDB / Dask / Ray and
  "larger-than-memory" clearly as roadmap, not current behavior.
- 📋 **Test suite** — `pytest` for the engine, every tool (round-trips), the formula language, the cache,
  and the schema pass; **Playwright** end-to-end for the Studio; golden-file tests for example workflows.
- 📋 **Continuous integration** — GitHub Actions running ruff + mypy + `pytest` + `npm run build`, on a
  Linux/macOS/Windows matrix.

**Done when:** CI is green on every PR, coverage covers each tool, and no doc claims an unimplemented feature.

## Milestone 2 — Usable for real work (persistence & editing)

**Goal: you can build, save, reopen, and iterate on real workflows** — today the canvas is lost on refresh.

- 📋 **Save / Open `.pyflow` in the UI** — server endpoints + toolbar actions; recent-files list.
- 📋 **Undo / redo, copy / paste, multi-select** on the canvas.
- 📋 **Node enable/disable, annotations, and containers** (visual grouping).
- 📋 **Richer editors** — Monaco for the formula and Python tools (syntax highlighting + field/function
  autocomplete) instead of plain textareas.

**Done when:** a user builds a workflow, saves it, reloads the page, reopens it, and edits with undo/redo.

## Milestone 3 — Actually big data (deliver the original promise)

**Goal: larger-than-memory execution, for real.** This closes the gap between the specs and the engine.

- 📋 **DuckDB backend** — out-of-core SQL, joins, and aggregations behind the `Frame` abstraction; a
  dedicated **SQL tool**; predicate/projection push-down for database reads.
- 📋 **End-to-end streaming** — use Polars' streaming engine and `sink_*` paths; avoid full `collect()`
  where possible; spill to disk on blocking operations.
- 📋 **Prove the backend abstraction** with ≥2 real backends (Polars + DuckDB) and a benchmark suite
  (1 / 10 / 50 GB).
- 📋 *(Stretch)* **Dask / Ray backend** for cluster-scale, partitioned execution.

**Done when:** a ~20 GB join + aggregate completes on a 16 GB laptop without OOM.

## Milestone 4 — Safe to share & install (security & packaging)

**Goal: safe defaults, and a real one-command install.**

- 📋 **Sandbox the Python/SQL tools** — subprocess isolation with CPU/memory/time limits and no ambient
  network by default (a prerequisite for any hosted/shared mode).
- 📋 **Secret store + connection manager** — get database credentials out of the `.pyflow` file.
- 📋 **Optional authentication** for a self-hosted, multi-user deployment.
- 📋 **Bundle the built UI into the wheel** and **publish to PyPI** (resolving the `pyflow` name collision),
  so `pip install <name>` yields a working Studio.

**Done when:** `pip install` gives a working UI, and no secrets live in workflow files by default.

## Milestone 5 — Breadth (tool library & reuse)

**Goal: cover more of the daily analyst workflow.**

- 📋 **More tools** — Reporting (Table / Chart → PDF/HTML/Excel), Excel / Google Sheets / cloud (S3, GCS) /
  REST-API inputs, Multi-Row & Multi-Field Formula, Find & Replace, Fuzzy Match, Generate Rows, Running Total.
- 📋 **Macros** — package a sub-workflow as a reusable tool; batch and iterative macros.
- 📋 **Scheduler + run history** — a simple built-in scheduler, and first-class triggering from
  Airflow/Dagster/CI.

**Done when:** an analyst can build a reporting-grade prep → blend → transform → report pipeline end to end.

## Later / vision

- **Server mode** — multi-user self-hosted gallery, RBAC, run auditing, lineage.
- **Plugin marketplace** — discover/install community tool packs (signed).
- **Advanced tool packs** (optional plugins) — Predictive/ML (scikit-learn), Spatial (geopandas), Time
  Series, Text Mining.
- **In-database execution** — Ibis-style multi-backend push-down (BigQuery, Snowflake, …).
- **Desktop shell** — a pywebview/Tauri one-click installer.

---

## How this maps to the original spec

[docs/08-roadmap.md](docs/08-roadmap.md) laid out the initial Phase 0–4 vision. In practice, **Phase 0
and most of Phase 1** shipped (canvas + engine + the full MVP tool set + incremental caching), and this
roadmap re-sequences the remainder around the real gaps found in implementation. The deeper design specs
in [`docs/`](docs/) remain the reference for *how* each area should work.

## Want to help?

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). The highest-leverage places to start
are **Milestone 1** (tests + CI) and **Milestone 2** (workflow save/open), and **new tools** are always a
good first PR (see [docs/05-tool-sdk.md](docs/05-tool-sdk.md)).
