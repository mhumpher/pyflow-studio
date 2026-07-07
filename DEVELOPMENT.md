# Development guide

How to set up, build, and run Pyflow locally from source. Pyflow is **not yet published to PyPI**, and
the compiled web UI isn't checked in, so setup builds both the Python packages and the frontend.

## Prerequisites

- **Python 3.11+** (developed against 3.13)
- **Node.js 18+** (developed against 24) — only needed to build/serve the frontend

## 1. Backend + engine (Python)

From the repo root:

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -e .
```

This installs three packages (all from this repo): `pyflow_engine` (pure-Python core),
`pyflow_sdk` (tool-authoring surface), and `pyflow_server` (FastAPI app), plus the `pyflow` CLI.

### Run a workflow headless (no browser)

```bash
pyflow validate examples/customer_filter.pyflow
pyflow run examples/customer_filter.pyflow
```

`run` streams JSON run events to stdout; `validate` checks structure, anchors, and tool configs.

## 2. Frontend (React + React Flow)

```bash
cd apps/studio
npm install
```

> **Windows note:** npm 11's script-gating skips esbuild's post-install step, which Vite needs.
> If the build complains about esbuild, run `npm rebuild esbuild` once after `npm install`.

Then either **build** it (served by the Python server) or run the **dev server** (hot reload):

```bash
npm run build        # produces apps/studio/dist, which the server auto-serves
# or, for frontend development with hot reload:
npm run dev          # Vite dev server on http://127.0.0.1:5173 (talks to the API on :8710)
```

## 3. Run the Studio

With the frontend built (step 2) and the venv active:

```bash
pyflow studio                      # serves UI + API at http://127.0.0.1:8710 and opens a browser
pyflow studio --no-browser         # don't auto-open a browser
pyflow studio --port 9000          # choose a port
```

In the browser: click **Load example** to drop the Input → Filter → Browse graph, then **Run**.
Click any node to preview its output (and switch the Filter's True/False anchors in the Results panel).
You can also drag tools from the left palette and connect anchors manually.

### Dev mode (two processes)

For frontend iteration, run the API and the Vite dev server separately:

```bash
# Terminal 1 — API only
python -m uvicorn pyflow_server.app:app --port 8710 --reload

# Terminal 2 — frontend with hot reload
cd apps/studio && npm run dev        # open http://127.0.0.1:5173
```

The frontend auto-detects dev mode (port 5173) and points at the API on 8710.

## Project layout

```
packages/engine/pyflow_engine   # DAG model, scheduler, backends, built-in tools, type system
packages/sdk/pyflow_sdk         # stable public API for custom tools
packages/server/pyflow_server   # FastAPI app (REST + WebSocket) and the `pyflow` CLI
apps/studio                     # React + React Flow frontend (Vite)
examples/                       # sample data + a sample .pyflow
docs/                           # full specification (start with docs/00 and docs/08)
```

## What works today (Phase 0 + Phase 1 core)

- Visual canvas (drag/drop, connect, multi-output anchors) with live per-node run status + row counts
- **Tools:** Input Data (CSV/Parquet/Arrow/JSON) · Database Input (SQL Server / Redshift / Oracle /
  Postgres / MySQL / SQLite) · Select · Filter (expression) · Formula · Sort ·
  Sample (first/last/every-Nth/random-N/random-%) · Unique (Unique + Duplicates) · Summarize ·
  Cross Tab (pivot, long->wide) · Unpivot (wide->long) · Transpose ·
  Text to Columns · RegEx (parse/match/replace/tokenize) · DateTime (parse/format) · JSON Parse ·
  Join (Left-only / Join / Right-only) · Union (fan-in, by name or position) · Browse ·
  Output Data (CSV/Parquet/Arrow/JSON/Excel) · Database Output (append / overwrite / create)
- **Database Input/Output:** `pip install -e ".[db]"`; connect via the UI's *Test connection &
  fetch schema* button (input). See [docs/database-connections.md](docs/database-connections.md).
- **Formula language** — `[Field]` references, `IF…ELSEIF…ELSE…ENDIF`, ~30 functions, compiled to Polars
- **Design-time schema pass** — output/field schemas computed without running, powering:
  - **Field pickers** bound to the real upstream columns (single + multi select)
  - **Repeatable-group** config (Select field table, Summarize aggregations)
  - A **formula editor** with clickable field chips and **live validation** (shows result type or error)
  - **Data-dependent columns** (Cross Tab's pivoted columns, Transpose's rows) propagate to downstream
    field pickers **after one run** — the pass reuses each node's real post-run schema from the cache,
    keyed by the same content hash, so an edit never yields a stale schema.
- Lazy Polars execution; per-node sampled previews + metadata
- **Incremental caching** — each cacheable node's output is materialized (Arrow) and content-hashed
  (config + upstream + source mtime); a re-run reuses unchanged nodes and recomputes only the edited
  node and its descendants. Sinks (Output Data/Database) always run. **Run** uses the cache; **↻ Fresh**
  clears it and recomputes everything.
- Run over WebSocket; headless `pyflow run` / `pyflow validate`

### Try the formula language headless

```bash
python -c "import polars as pl; from pyflow_engine.formula import compile_expr; \
print(pl.DataFrame({'x':[1,2,3]}).select(compile_expr('IF [x] > 1 THEN [x]*10 ELSE 0 ENDIF').alias('y')))"
```

The Phase 1 tool set, incremental caching, and the parse pack are done. See
[docs/08-roadmap.md](docs/08-roadmap.md) for what's next — partitioned/streaming DB reads, a connection
manager + secret store, and macros (reusable sub-workflows).
