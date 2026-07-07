# 02 — Data & Workflow Model

This document defines the two data models at the heart of Pyflow:

1. **The workflow model** — how a saved `.pyflow` file describes a pipeline (the DAG).
2. **The record/type model** — how data and its schema flow between tools at runtime.

---

## 1. Workflow model

A **workflow** is a directed acyclic graph (DAG). Nodes are **tool instances**; edges are
**connections** between an output anchor of one node and an input anchor of another.

### 1.1 The `.pyflow` file

Human-readable JSON (YAML export optional), designed to diff cleanly in Git.

```jsonc
{
  "pyflow_version": "1.0",
  "id": "wf_9c1e...",
  "name": "Customer cleanup",
  "meta": {
    "created": "2026-06-30T14:00:00Z",
    "modified": "2026-06-30T14:32:10Z",
    "author": "ana",
    "description": "Clean CRM export, join to regions, summarize by region."
  },
  "nodes": [
    {
      "id": "n1",
      "type": "input.file",          // tool type id (registry key)
      "version": "1.0",              // tool version for compatibility
      "position": { "x": 80, "y": 120 },
      "title": "CRM export",         // user-facing label (optional override)
      "config": {
        "path": "data/crm.csv",
        "format": "csv",
        "options": { "delimiter": ",", "header": true, "encoding": "utf-8" }
      }
    },
    {
      "id": "n2",
      "type": "prep.filter",
      "version": "1.0",
      "position": { "x": 340, "y": 120 },
      "config": { "mode": "expression", "expression": "[status] == \"active\"" }
    }
  ],
  "edges": [
    {
      "id": "e1",
      "source": { "node": "n1", "anchor": "out" },
      "target": { "node": "n2", "anchor": "in" }
    }
  ],
  "annotations": [
    { "id": "a1", "type": "comment", "text": "Source refreshed nightly",
      "position": { "x": 80, "y": 60 } }
  ],
  "containers": [
    { "id": "c1", "title": "Ingest", "node_ids": ["n1", "n2"],
      "collapsed": false, "color": "#3b82f6" }
  ]
}
```

### 1.2 Node

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique within the workflow (stable across edits) |
| `type` | string | Tool registry key, e.g. `join.standard` |
| `version` | string | Tool schema version, for migration |
| `position` | {x,y} | Canvas coordinates (view state) |
| `title` | string? | Optional user label; defaults to the tool's display name |
| `config` | object | Tool-specific settings, validated against the tool's config schema |
| `disabled` | bool? | If true, node is skipped (passes input through or produces nothing) |

### 1.3 Anchor (port)

Each tool declares **input** and **output anchors**. Anchors are typed by *cardinality* and *role*:

- **Input anchors** — `single` (exactly one connection) or `multi` (fan-in, e.g. Union).
- **Output anchors** — one logical output; may fan out to many downstream inputs.
- **Named/typed anchors** — e.g. Join exposes `left`/`right` inputs and `join`/`left_only`/`right_only`
  outputs.

Anchors carry a **schema contract** used for validation *before* running (see §3.4).

### 1.4 Edge

Connects `source {node, anchor}` → `target {node, anchor}`. Constraints:
- No cycles (enforced on every edit; the DAG invariant is non-negotiable).
- A `single` input anchor accepts at most one edge.
- Type-compatibility is checked at connect time and re-checked at run time.

### 1.5 Annotations & containers
- **Annotations** — free comments/labels on the canvas; no runtime effect.
- **Containers (tool groups)** — visual grouping; collapsible; can later become the basis for **macros**
  (a reusable sub-workflow exposed as a single tool — see [Roadmap](08-roadmap.md)).

### 1.6 Validation rules
A workflow is *runnable* when: it is acyclic; every required input anchor is connected; every node's
config validates against its schema; and every edge is schema-compatible. Validation errors are surfaced
per-node in the UI without blocking editing.

---

## 2. Record & type model

Data flowing on an edge is a **table**: an ordered set of **fields** (columns) with a shared schema,
plus rows. Internally this is an **Arrow-backed columnar frame** (Polars `DataFrame`/`LazyFrame` or a
DuckDB relation), never a Python list-of-dicts, so it stays columnar and can exceed memory.

### 2.1 Schema and field metadata

A **schema** is an ordered list of fields. Each field carries metadata Alteryx users expect:

| Field attribute | Purpose |
| --- | --- |
| `name` | Column name (unique within a table) |
| `type` | Pyflow logical type (see §2.2) |
| `nullable` | Whether nulls are allowed |
| `description` | Optional documentation, carried through tools |
| `source` | Provenance hint (origin tool/column), for lineage & profiling |
| `format` | Optional display/parse format (e.g. date format, number precision) |

Schema is **propagated and transformed** by every tool: a Select renames/retypes, a Formula adds a
field, a Join concatenates left+right schemas, etc. The engine computes the **output schema of every
node without running data** where possible (metadata flow), so the UI can show downstream field lists
and validate connections before execution.

### 2.2 Type system

Logical types map to Arrow physical types for zero-copy interchange:

| Pyflow type | Arrow type | Notes |
| --- | --- | --- |
| `bool` | `bool` | |
| `int8/16/32/64` | `int8..64` | Signed integers |
| `uint8/16/32/64` | `uint8..64` | Unsigned |
| `float32/64` | `float32/64` | |
| `decimal(p,s)` | `decimal128` | Exact numerics (money) |
| `string` | `utf8` / `large_utf8` | Unicode text |
| `binary` | `binary` | Blobs |
| `date` | `date32` | Calendar date |
| `time` | `time64` | Time of day |
| `datetime` | `timestamp(tz?)` | Optional timezone |
| `duration` | `duration` | Elapsed time |
| `list<T>` | `list` | Nested arrays |
| `struct{...}` | `struct` | Nested records |

- **Type coercion** rules are explicit and centralized (e.g. `int32 → int64` widens silently;
  `string → int` requires an explicit parse tool and can error/allow-null).
- A **"fixed decimal"/money** type is first-class because financial analysts depend on exactness.
- Nulls are represented via Arrow validity bitmaps (not sentinel values).

### 2.3 Batching & streaming

For larger-than-memory data, tables move as **streams of Arrow record batches** rather than one
materialized frame:

- Sources emit batches; tools transform batch-by-batch where the operation is streamable
  (filter, formula, select, sample).
- **Blocking operations** (sort, distinct, group-by, join) buffer or spill to disk via the backend
  (Polars streaming engine or DuckDB), not by loading everything into Python.
- The engine chooses **materialize vs stream** per node based on the tool and the chosen backend
  (see [Execution Engine](03-execution-engine.md)).

### 2.4 Metadata-only flow (design-time schema)

Before any run, the engine performs a **schema pass**: starting from source tools (which can infer a
schema cheaply from headers/samples), each tool implements `infer_schema(inputs) -> schema` so the UI
can show every node's output fields, power the Formula/Select editors' autocomplete, and validate
connections — all without touching row data.

### 2.5 Connection compatibility

At connect time and run time, an edge is valid if the source's output schema satisfies the target
anchor's **contract**. Contracts range from permissive (*any table*) to specific (*must contain a
numeric field*, *both inputs must share join keys of compatible type*). Incompatibilities produce a
clear, per-anchor error rather than a late crash.

---

## 3. Worked example (schema propagation)

```
input.file (crm.csv)          →  schema: [id:int64, name:string, status:string, spend:float64]
  └─ prep.filter [status]=="active"  →  same schema (row count changes only)
       └─ prep.select (drop status, rename spend→revenue, retype revenue→decimal(18,2))
                                  →  [id:int64, name:string, revenue:decimal(18,2)]
            └─ transform.summarize (group by none, sum revenue)
                                  →  [sum_revenue:decimal(18,2)]
```

Every arrow above is computed at **design time** by the schema pass, so the analyst sees the resulting
fields in the config panel before running.
