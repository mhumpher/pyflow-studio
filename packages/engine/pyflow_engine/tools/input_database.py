"""Database Input — read a SQL query from a database into the workflow.

Connectivity uses Polars' ``read_database_uri`` (ConnectorX) as the fast, Arrow-native
path, with a SQLAlchemy fallback. Design-time safety: the query runs only in run().
build() (called by the schema pass on every edit) never touches the database — it
reconstructs an empty frame from the column list cached by the "Fetch schema" action.

Connection handling (dialects, ports, ${ENV_VAR} secrets, URIs) lives in _db_common.
See docs/database-connections.md for per-database driver requirements.
"""
from __future__ import annotations

import polars as pl
from pydantic import Field as PField

from ..frame import Frame
from ..tool import OutputAnchor, Tool
from ..types import polars_to_pyflow
from ._db_common import (
    ConnectionFields,
    DbColumn,
    DbEngine,
    Dialect,
    clean_query,
    connectorx_uri,
    safe_pl_dtype,
    sqlalchemy_uri,
)


class DatabaseInputConfig(ConnectionFields):
    query: str = PField(default="", title="SQL query", json_schema_extra={"x-editor": "sql"})
    engine: DbEngine = PField(default=DbEngine.auto, title="Driver")
    columns: list[DbColumn] = PField(
        default_factory=list, json_schema_extra={"x-editor": "hidden"}
    )


def _read(cfg: DatabaseInputConfig, query: str) -> pl.DataFrame:
    engine = cfg.engine

    # ConnectorX is the fast path for networked databases. SQLite goes through
    # SQLAlchemy under "auto" (ConnectorX mishandles local file paths), but an
    # explicit engine=connectorx is still honored.
    use_connectorx = engine is DbEngine.connectorx or (
        engine is DbEngine.auto and cfg.dialect is not Dialect.sqlite
    )
    if use_connectorx:
        try:
            import connectorx  # noqa: F401
        except ModuleNotFoundError:
            if engine is DbEngine.connectorx:
                raise ValueError(
                    "engine=connectorx needs the 'connectorx' package: pip install connectorx"
                )
        else:
            return pl.read_database_uri(query=query, uri=connectorx_uri(cfg), engine="connectorx")

    try:
        from sqlalchemy import create_engine
    except ModuleNotFoundError:
        raise ValueError(
            "No database engine available. Install one: pip install connectorx"
            "  (or)  pip install sqlalchemy plus a driver for your database"
        )
    sa_engine = create_engine(sqlalchemy_uri(cfg))
    with sa_engine.connect() as conn:
        return pl.read_database(query=query, connection=conn)


def probe_schema(cfg: DatabaseInputConfig) -> dict:
    """Fetch column names/types without pulling rows (wraps the query as WHERE 1=0)."""
    query = clean_query(cfg.query)
    if not query:
        return {"ok": False, "error": "Enter a SQL query first"}
    probe = f"SELECT * FROM ( {query} ) _pf_probe WHERE 1=0"
    try:
        df = _read(cfg, probe)
    except Exception as exc:
        msg = str(exc).strip()
        return {"ok": False, "error": (msg.splitlines()[0] if msg else exc.__class__.__name__)}
    return {
        "ok": True,
        "columns": [{"name": n, "type": polars_to_pyflow(dt)} for n, dt in df.schema.items()],
    }


class DatabaseInputTool(Tool):
    type = "input.database"
    name = "Database Input"
    category = "Input/Output"
    icon = "database"
    Config = DatabaseInputConfig
    inputs = []
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: DatabaseInputConfig, ctx) -> dict[str, Frame]:
        # No DB access at design time: reconstruct an empty frame from the cached schema.
        if cfg.columns:
            data = {c.name: pl.Series(c.name, [], dtype=safe_pl_dtype(c.type)) for c in cfg.columns}
            return {"out": Frame(pl.DataFrame(data).lazy())}
        return {"out": Frame(pl.DataFrame().lazy())}

    def run(self, inputs, cfg: DatabaseInputConfig, ctx) -> dict[str, Frame]:
        query = clean_query(cfg.query)
        if not query:
            raise ValueError("No SQL query configured")
        df = _read(cfg, query)
        ctx.message("info", f"Read {df.height} rows from {cfg.dialect.value}")
        return {"out": Frame(df.lazy())}
