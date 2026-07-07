# 07 — Backend API

The server exposes a **REST API** for documents, catalog, schemas, and previews, and a **WebSocket
channel** for run control and live events. All heavy work is delegated to the engine. This is a contract
sketch, not final OpenAPI — payloads are illustrative.

Base URL (local default): `http://127.0.0.1:8710`. All bodies are JSON unless noted. Data previews are
returned as Arrow IPC or JSON depending on the `Accept` header.

---

## 1. REST endpoints

### 1.1 Tool catalog & schemas

```
GET /tools
→ 200
[
  { "type": "prep.filter", "name": "Filter", "category": "Preparation",
    "version": "1.0", "icon": "filter",
    "inputs":  [{ "id": "in", "contract": "any_table" }],
    "outputs": [{ "id": "true" }, { "id": "false" }] },
  ...
]

GET /tools/{type}/config-schema
→ 200  (JSON Schema used to render the config panel)
{ "title": "Filter", "type": "object",
  "properties": { "expression": { "type": "string", "x-editor": "formula",
                                   "title": "Keep rows where" } },
  "required": ["expression"] }
```

### 1.2 Workflows

```
GET    /workflows                  → list (name, id, modified)
POST   /workflows                  → create {name} → {id}
GET    /workflows/{id}             → full .pyflow document
PUT    /workflows/{id}             → replace document
PATCH  /workflows/{id}             → partial (e.g. rename)
DELETE /workflows/{id}
POST   /workflows/{id}/save        → persist to a .pyflow file on disk
POST   /workflows/import           → upload a .pyflow file → {id}
GET    /workflows/{id}/export      → download .pyflow
```

### 1.3 Node-level editing (fine-grained, for responsiveness)

```
POST   /workflows/{id}/nodes                 → add node {type, position} → node
PATCH  /workflows/{id}/nodes/{nodeId}        → update {config?, position?, title?, disabled?}
DELETE /workflows/{id}/nodes/{nodeId}
POST   /workflows/{id}/edges                 → add {source, target} (validated) → edge | 409 with reason
DELETE /workflows/{id}/edges/{edgeId}
```

### 1.4 Validation & design-time schema

```
POST /workflows/{id}/validate
→ 200
{ "runnable": false,
  "issues": [
    { "node": "n5", "level": "error", "code": "JoinKeyTypeMismatch",
      "message": "[cust_id] int64 vs [id] string", "anchor": "right" },
    { "node": "n2", "level": "warning", "code": "UnusedOutput", "message": "False output not connected" }
  ] }

GET /workflows/{id}/nodes/{nodeId}/schema     → design-time output schema(s) (no data run)
→ 200
{ "outputs": {
    "out": { "fields": [
      { "name": "id", "type": "int64", "nullable": false, "description": null, "source": "crm.csv" },
      { "name": "revenue", "type": "decimal(18,2)", "nullable": true } ] } } }
```

### 1.5 Previews & profiling (sampled — never full data)

```
GET /workflows/{id}/nodes/{nodeId}/preview?anchor=out&rows=1000&offset=0
Accept: application/vnd.apache.arrow.stream   (or application/json)
→ 200  Arrow IPC batch (or JSON rows)  — a bounded sample from the node cache

GET /workflows/{id}/nodes/{nodeId}/profile?anchor=out
→ 200
{ "rows": 480123,
  "columns": [
    { "name": "revenue", "type": "decimal(18,2)", "null_pct": 0.02,
      "distinct": 41233, "min": "0.00", "max": "98211.50", "mean": "512.34",
      "histogram": [ {"bin": "0-100", "count": 120344}, ... ] } ] }
```

### 1.6 Filesystem / data sources (allow-listed)

```
GET  /fs/browse?path=data/            → dir listing within the configured root (path-traversal guarded)
POST /fs/inspect                      → {path, format?} → inferred schema + sample for Input Data config
GET  /connections                     → configured DB/cloud connections (names only, no secrets)
POST /connections/{name}/tables       → list tables/schemas for a DB connection
```

## 2. WebSocket channel

`WS /workflows/{id}/session` — bidirectional, JSON messages. Handles run control and live events so the
UI reflects execution in real time.

### 2.1 Client → server

```jsonc
{ "op": "run",   "mode": "full" }                         // run entire workflow
{ "op": "run",   "mode": "interactive", "to": "n5" }      // run up to node n5 (ancestors only)
{ "op": "stop" }                                          // cancel the active run
{ "op": "subscribe_preview", "node": "n5", "anchor": "out", "rows": 1000 }
```

### 2.2 Server → client (engine event stream)

Mirrors the engine events in [Execution Engine §7](03-execution-engine.md):

```jsonc
{ "type": "run_started",    "run_id": "r_88", "nodes": 6 }
{ "type": "node_started",   "node": "n2" }
{ "type": "node_progress",  "node": "n2", "rows": 250000, "pct": 0.4 }
{ "type": "node_message",   "node": "n2", "level": "warn", "text": "12 rows failed date parse; set null" }
{ "type": "node_completed", "node": "n2", "rows": 480123, "cols": 9, "ms": 812, "cached": false }
{ "type": "node_error",     "node": "n5", "code": "JoinKeyTypeMismatch", "detail": "int64 vs string" }
{ "type": "run_completed",  "run_id": "r_88", "ms": 3410 }
{ "type": "run_cancelled",  "run_id": "r_88" }
```

> Node config edits go over **REST** (`PATCH …/nodes/{id}`) for simple request/response semantics;
> **runs and live status** go over **WebSocket**. This split keeps document edits transactional while
> streaming run telemetry efficiently.

## 3. Data serialization

- **Documents / configs / schemas / profiles** → JSON.
- **Preview row data** → **Arrow IPC stream** by default (compact, typed, zero-copy into the grid),
  with a JSON fallback for debugging. Always bounded (`rows`, `offset`) and paginated.
- Content negotiation via `Accept`.

## 4. Errors

Consistent envelope:

```jsonc
{ "error": { "code": "JoinKeyTypeMismatch",
             "message": "Join keys have incompatible types.",
             "detail": { "left": "cust_id:int64", "right": "id:string" },
             "node": "n5", "anchor": "right" } }
```

- `4xx` for client/validation problems (invalid edge, bad config, path outside root).
- `5xx` for engine/internal faults, with a `code` and safe message (no stack traces to the client).
- Run-time tool errors arrive as `node_error` **events**, not HTTP errors, since the run is async.

## 5. AuthN/AuthZ

- **MVP (local single-user):** bound to `127.0.0.1`, no auth, with a per-session token (CSRF/WS guard) to
  block other local processes from hijacking the session.
- **Phase 4 (multi-user server):** pluggable auth (OIDC/token), per-workflow RBAC, and per-connection
  secret scoping. Designed for from the start (endpoints are session/workflow-scoped) but not built at MVP.

## 6. Versioning & stability

- REST is versioned via header or `/v1/` prefix once it stabilizes.
- The `.pyflow` document carries `pyflow_version`; the server migrates older documents on load.
- OpenAPI is generated from FastAPI/Pydantic; the frontend's REST client is generated from it to keep
  types in sync.

## 7. Local security posture

- Filesystem and connection access is confined to an **allow-listed workspace root** with path-traversal
  protection.
- Secrets (DB passwords, cloud keys) live in a local secret store and are **never** returned to the
  client — tools fetch them via `ctx.secret(name)` server-side.
- Developer tools that execute user code (Python/SQL) run under the sandboxing described in
  [Non-Functional Requirements §Security](09-non-functional.md).
