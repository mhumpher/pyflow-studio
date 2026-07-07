# Database connections

Two tools connect workflows to databases:

- **Database Input** (`input.database`) — reads a SQL query into the workflow.
- **Database Output** (`output.database`) — writes a table to the database.

**Reads** use two interchangeable engines:

- **ConnectorX** (default for networked databases) — fast, Arrow-native, understands `mssql://`,
  `redshift://`, `oracle://`, `postgresql://`, `mysql://`, `sqlite://` URIs directly.
- **SQLAlchemy** (fallback / alternative) — universal, via a per-database driver.

The `Driver` field on Database Input selects `auto` (ConnectorX for networked DBs, SQLAlchemy for
SQLite), `connectorx`, or `sqlalchemy`. **Writes** always use SQLAlchemy + pandas (`pandas.to_sql`
handles cross-dialect table creation); ConnectorX is read-only.

## Install

Pyflow isn't on PyPI yet, so install the database extras **from source** (from a clone of the repo —
see the [README](../README.md#installation)):

```bash
pip install -e ".[db]"        # ConnectorX + SQLAlchemy + pandas
```

ConnectorX bundles native clients for SQL Server (TDS) and the Postgres protocol (Redshift), so those
need **no ODBC/driver install** for reads. Per-database SQLAlchemy drivers (needed for writes, and for
the SQLAlchemy read path) are separate extras (see each section).

## How you connect (in the UI)

1. Drag **Database Input** onto the canvas.
2. Pick the **Database** (dialect), fill in **Host / Port / Database / User / Password**, and write a
   **SQL query**. (Port `0` uses the dialect default.)
3. Click **Test connection & fetch schema** — this runs a zero-row probe and caches the result-set
   columns so downstream field pickers work *without* re-querying while you edit.
4. **Run** to pull the data.

> **Secrets:** put `${ENV_VAR}` in any field (e.g. Password) to read it from an environment variable
> instead of storing it in the `.pyflow` file. Example password value: `${REDSHIFT_PASSWORD}`.

The query runs **only** on Run (and on the explicit schema probe) — never during normal editing.

## Writing back (Database Output)

**Database Output** writes its input table to a database table. It shares the same connection fields
(dialect / host / port / database / user / password / URI, with `${ENV_VAR}` secrets), plus:

- **Target table** — the destination table name (may be schema-qualified, e.g. `dbo.sales`).
- **If table exists** — `append` (insert rows, creating the table if needed), `overwrite` (drop &
  recreate), or `create` (fail if the table already exists).

Writes go through **SQLAlchemy + pandas**, so install the same per-database driver you'd use for the
SQLAlchemy read path (pymssql / psycopg / oracledb / …). The write runs **only** on Run — the
design-time schema pass never touches the database. The tool passes its input through, so you can
preview exactly what was written.

---

## SQL Server

| Field | Value |
| --- | --- |
| Database | `sqlserver` |
| Port | `1433` (default) |
| Database | your database name |

- **ConnectorX (recommended):** works out of the box (`pip install -e ".[db]"`), no ODBC.
  URI form: `mssql://user:pass@host:1433/mydb`.
  If the server enforces encryption, use the **Custom connection URI** with parameters, e.g.
  `mssql://user:pass@host:1433/mydb?encrypt=true&trust_server_certificate=true`.
- **SQLAlchemy alternative:** `pip install -e ".[mssql]"` (pymssql), set Driver = `sqlalchemy`
  → `mssql+pymssql://user:pass@host:1433/mydb`. (Or pyodbc if you already have the MS ODBC driver.)

## Redshift

| Field | Value |
| --- | --- |
| Database | `redshift` |
| Port | `5439` (default) |
| Database | your database name |

- **ConnectorX (recommended):** built in — Redshift speaks the Postgres wire protocol.
  URI form: `redshift://user:pass@cluster.xxxx.region.redshift.amazonaws.com:5439/dev`.
- **SQLAlchemy alternative:** `pip install -e ".[redshift]"` (psycopg), Driver = `sqlalchemy`
  → `postgresql+psycopg://user:pass@host:5439/dev`.

## Oracle

| Field | Value |
| --- | --- |
| Database | `oracle` |
| Port | `1521` (default) |
| Database / service | your **service name** (or SID) |

- **SQLAlchemy + python-oracledb (recommended):** `pip install -e ".[oracle]"`, Driver =
  `sqlalchemy`. Thin mode needs **no Oracle client install**.
  For a **service name**, use the **Custom connection URI** field:
  `oracle+oracledb://user:pass@host:1521/?service_name=ORCLPDB1`
  (a bare `/NAME` path is treated as a SID).
- **ConnectorX:** supports `oracle://user:pass@host:1521/service`, but its Oracle source requires the
  **Oracle Instant Client (OCI)** to be installed. If you don't have OCI, prefer the SQLAlchemy path
  above.

---

## Other databases

`postgresql` and `mysql` work the same way (ConnectorX built in; SQLAlchemy via `psycopg` / `pymysql`).
For anything else, choose dialect **`custom`** and provide a full **Custom connection URI** that matches
your chosen `Driver` (ConnectorX or SQLAlchemy URI syntax).

## Notes & current limitations

- **Types on probe:** the schema probe reports the columns and the *driver-provided* types. Enterprise
  databases return precise types; SQLite reports weak types for an empty result (they resolve correctly
  on Run).
- **Whole-query read:** `run()` currently materializes the query result. Partitioned/streaming reads
  (ConnectorX `partition_on`) and write-back (**Database Output**) are planned follow-ons.
- **Security:** this is a local-first tool. Prefer `${ENV_VAR}` for secrets; a managed secret store and
  connection-manager UI are on the roadmap (see [09-non-functional.md](09-non-functional.md)).

## What's tested

The full mechanism — URI building, the schema probe, `build()`/`run()` separation, design-time schema
propagation, and **Database Output** write modes (append / overwrite / create) plus a write→read
round-trip — is verified end-to-end against **SQLite**. SQL Server, Redshift, and Oracle use the
**same code path** with their respective URIs/drivers and require a live server to exercise.
