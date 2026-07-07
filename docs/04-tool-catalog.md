# 04 — Tool Catalog

Tools are the nodes on the canvas. This document defines the **MVP tool set** (what ships first) and the
**full roadmap catalog**, organized by category the way analysts expect (mirroring, but not copying,
Alteryx's tool groups).

Each tool has: a `type` id, a display name, input/output anchors, a config schema (which auto-generates
its panel — see [Tool SDK](05-tool-sdk.md)), and a documented schema transformation.

---

## 1. MVP tool set (Phase 1)

The MVP proves the end-to-end loop: **ingest → prepare → blend → transform → output**, all no-code.
Target: ~18 tools.

### Input / Output
| Tool (`type`) | Anchors | Purpose |
| --- | --- | --- |
| **Input Data** (`input.file`) | – → 1 | Read CSV / Parquet / Arrow / JSON / Excel. Auto-detect + configure delimiter, header, encoding, sheet. Infers schema from a sample. |
| **Text Input** (`input.text`) | – → 1 | Hand-enter a small table (constants/lookups) in a grid. |
| **Output Data** (`output.file`) | 1 → – | Write CSV / Parquet / Arrow / Excel to a path, with mode (overwrite/append) and format options. |
| **Browse** (`output.browse`) | 1 → – | Terminal preview: full profiling + data grid of the input. |

### Preparation
| Tool | Anchors | Purpose |
| --- | --- | --- |
| **Select** (`prep.select`) | 1 → 1 | Choose, reorder, rename, and **retype** fields; edit descriptions. The workhorse. |
| **Filter** (`prep.filter`) | 1 → 2 | Split rows by a condition (expression or basic UI): **True** and **False** outputs. |
| **Formula** (`prep.formula`) | 1 → 1 | Add/replace columns via expressions (see §Formula). Multiple outputs in one tool. |
| **Sort** (`prep.sort`) | 1 → 1 | Order rows by one or more fields, asc/desc. |
| **Sample** (`prep.sample`) | 1 → 1 | First/last N, every Nth, or random % (optionally grouped). |
| **Unique** (`prep.unique`) | 1 → 2 | Deduplicate on selected fields: **Unique** and **Duplicates** outputs. |
| **Data Cleansing** (`prep.cleanse`) | 1 → 1 | Trim whitespace, fix case, remove punctuation/nulls, replace nulls, per selected fields. |

### Join / Blend
| Tool | Anchors | Purpose |
| --- | --- | --- |
| **Join** (`join.standard`) | 2 (L,R) → 3 | Join on keys; outputs **Left-only**, **Inner (Join)**, **Right-only** (Alteryx-style 3-anchor). Choose output fields. |
| **Union** (`join.union`) | N → 1 | Stack tables by field name or position; configurable handling of mismatched fields. |
| **Append Fields** (`join.append`) | 2 (T,S) → 1 | Cartesian/append of a small "source" onto a "target" (lookups, cross join). |

### Transform
| Tool | Anchors | Purpose |
| --- | --- | --- |
| **Summarize** (`transform.summarize`) | 1 → 1 | Group-by + aggregations (sum, count, min, max, mean, median, stddev, first/last, concat). The analytics workhorse. |
| **Cross Tab** (`transform.crosstab`) | 1 → 1 | Pivot: rows × header-values → aggregated cells (long → wide). |
| **Transpose** (`transform.transpose`) | 1 → 1 | Unpivot: wide → long (key/name/value). |

### Developer (thin at MVP)
| Tool | Anchors | Purpose |
| --- | --- | --- |
| **Select Records** (`dev.select_records`) | 1 → 1 | Keep specific row ranges/numbers (e.g. `1-100, 250`). |

> **MVP formula/expression support** is the connective tissue for Filter, Formula, and Summarize — see
> §Formula below.

---

## 2. Full roadmap catalog (Phases 2–4)

Grouped by category. Items marked ⭑ are high-priority follow-ons.

### Input / Output
- ⭑ **Database Input/Output** (`input.db` / `output.db`) — SQL sources/sinks via SQLAlchemy/DuckDB/ADBC
  (Postgres, MySQL, SQLite, DuckDB, Snowflake, BigQuery). Custom SQL or table picker; predicate pushdown.
- ⭑ **Directory / multi-file input** — read a folder/glob of files into one stream, with a filename field.
- **API / REST input** — paged HTTP JSON to a table.
- **Cloud storage** — S3 / GCS / Azure Blob (via `fsspec`).
- **Google Sheets**, **Parquet dataset (partitioned)**, **Delta/Iceberg** (later).

### Preparation
- ⭑ **Multi-Row Formula** — expressions referencing previous/next rows (running totals, gap-fill).
- ⭑ **Multi-Field Formula** — apply one expression across many selected fields at once.
- **Auto Field** — infer the smallest correct type per field.
- **Random % Sample**, **Oversample/Undersample**, **Generate Rows** (sequence generator).
- **Imputation** (mean/median/constant), **Field Info** (schema-as-data).

### Join / Blend
- ⭑ **Find & Replace** — lookup-and-substitute across a field using another table.
- **Fuzzy Match** — approximate/duplicate matching (name/address dedupe) — a marquee Alteryx feature.
- **Make Group** — connected-components grouping from match pairs.
- **Join Multiple** — N-way join in one tool.

### Transform
- ⭑ **Running Total**, **Weighted Average**, **Count Records**.
- **Tile / Bucket** — quantiles/equal-width binning.
- **Arrange** — advanced pivot/reshape UI on top of Cross Tab/Transpose.

### Parse
- ⭑ **Text to Columns** — split a delimited field into columns/rows.
- ⭑ **RegEx** — parse/match/replace/tokenize with named groups.
- ⭑ **DateTime** — parse strings ↔ datetime with format locales.
- **JSON Parse**, **XML Parse** — flatten nested structures to columns.

### Developer / Automation
- ⭑ **SQL tool** (`dev.sql`) — write DuckDB SQL over the input(s) as named tables; power-user escape hatch.
- ⭑ **Python tool** (`dev.python`) — sandboxed Python cell receiving/returning a Polars/pandas frame.
- **Run Command** — shell out (guarded), **Message/Test** — assertions & logging.
- **Macro / Container → reusable tool** — package a sub-workflow as a single tool with exposed params.
- **Batch/Iterative macros** — loop a sub-workflow over groups or until a condition.

### Reporting
- **Table**, **Chart** (bar/line/scatter/histogram), **Summary Stats**, **Render** (to PDF/HTML/Excel),
  **Layout/Text/Image** — compose a report from a workflow's outputs.

### Predictive / ML (later)
- **Sample/Split**, **Linear/Logistic Regression**, **Decision Tree/Forest**, **Cluster (k-means)**,
  **Score**, **Model Comparison** — wrapping scikit-learn; kept optional to avoid a heavy core.

### Spatial (later)
- **Create Points**, **Spatial Join**, **Distance**, **Buffer**, **Trade Area** — via `shapely`/`geopandas`.

### Time Series (later)
- **TS Filler**, **Decompose**, **ARIMA/ETS Forecast**, **TS Plot**.

### Text Mining (later)
- **Tokenize**, **Word Count/TF-IDF**, **Sentiment**, **Topic/Cluster** — via `spaCy`/`scikit-learn`.

### In-Database (later)
- **Connect In-DB**, **In-DB Filter/Formula/Join/Summarize/Select**, **Data Stream In/Out** — build a
  pushed-down query that executes in the warehouse (DuckDB first, then an Ibis-style multi-backend path).

---

## 3. Formula & expression language {#formula}

A single expression language powers Filter, Formula, Summarize, and any config that takes a condition.

**Decision (recommended):** an **Alteryx-like formula syntax** — `[Field]` references, familiar
functions, and operators — compiled to a backend expression AST (Polars `pl.Expr` / DuckDB SQL). This
is more approachable for analysts than raw Python and portable across backends.

```text
IF [status] == "active" AND [spend] > 1000 THEN "VIP" ELSE "Standard" ENDIF
Trim(Upper([name]))
DateTimeDiff([closed], [opened], "days")
[revenue] * 1.1
```

- **Field references:** `[Field Name]` (bracketed; supports spaces).
- **Types & functions:** string (`Trim`, `Upper`, `Substring`, `Contains`, `RegExReplace`), numeric
  (`Round`, `Abs`, `Pow`, `Log`), date (`DateTimeAdd`, `DateTimeParse`, `Now`), conditional (`IF/THEN/
  ELSE/ENDIF`, `Switch`), null handling (`IsNull`, `Coalesce`).
- **Editor support:** Monaco with autocomplete for the input schema's field names and the function
  library, inline type checking, and a live sample-evaluated preview.
- **Escape hatches:** the **SQL tool** (DuckDB SQL) and **Python tool** for logic beyond the formula
  language.

> Alternative considered: expose raw Polars expressions or a Python-subset. Rejected as the *default*
> because it raises the floor for non-programmers; both remain available via the Developer tools.

---

## 4. Anchor & schema conventions

- **Filter/Unique/Join** use **multiple typed outputs** so downstream branches are explicit
  (matches Alteryx and keeps DAGs readable).
- Every tool documents its **schema transformation** (`infer_schema`) so the design-time schema pass
  (see [Data Model §2.4](02-data-and-workflow-model.md)) can show downstream fields before running.
- Tools declare **input contracts** (e.g. Summarize needs ≥1 groupable/aggregatable field) to give
  early, clear validation errors.

## 5. Prioritization rationale

The MVP set is chosen so that a realistic task — *read a messy CSV, filter, clean, join to a lookup,
summarize by group, and export to Excel* — is fully achievable no-code. The Phase-2 ⭑ items (Database
I/O, RegEx/Text-to-Columns/DateTime parsing, SQL & Python tools, Multi-Row Formula, Fuzzy Match) are the
most-requested next capabilities and are sequenced first in the [Roadmap](08-roadmap.md).
