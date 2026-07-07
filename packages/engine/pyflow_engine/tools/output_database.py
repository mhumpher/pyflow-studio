"""Database Output — write the incoming table to a database table.

Writes go through SQLAlchemy (ConnectorX is read-only). Like the file output, the
write happens only in run() — never in build() — so the design-time schema pass has
no side effects. Passes its input through on an ``out`` anchor so it stays previewable.

Needs SQLAlchemy plus the driver for your database (pymssql / psycopg / oracledb / ...).
See docs/database-connections.md.
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool
from ._db_common import ConnectionFields, sqlalchemy_uri


class WriteMode(str, Enum):
    append = "append"
    overwrite = "overwrite"
    create = "create"


# Pyflow write mode -> Polars write_database if_table_exists
_IF_EXISTS = {"append": "append", "overwrite": "replace", "create": "fail"}


class DatabaseOutputConfig(ConnectionFields):
    table: str = PField(default="", title="Target table")
    mode: WriteMode = PField(
        default=WriteMode.append,
        title="If table exists",
        description="append = insert rows; overwrite = drop & recreate; create = fail if it exists",
    )


class DatabaseOutputTool(Tool):
    type = "output.database"
    name = "Database Output"
    category = "Input/Output"
    icon = "database"
    Config = DatabaseOutputConfig
    cacheable = False  # side effect (writes to the database): always execute
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]  # pass-through, so the written data stays previewable

    def build(self, inputs, cfg: DatabaseOutputConfig, ctx) -> dict[str, Frame]:
        if "in" not in inputs:
            raise ValueError("Database Output has no input connected")
        return {"out": inputs["in"]}

    def run(self, inputs, cfg: DatabaseOutputConfig, ctx) -> dict[str, Frame]:
        if "in" not in inputs:
            raise ValueError("Database Output has no input connected")
        if not cfg.table.strip():
            raise ValueError("No target table configured")

        frame = inputs["in"]
        df = frame.lazy.collect()
        try:
            df.write_database(
                table_name=cfg.table.strip(),
                connection=sqlalchemy_uri(cfg),
                if_table_exists=_IF_EXISTS[cfg.mode.value],
            )
        except ModuleNotFoundError as exc:
            raise ValueError(
                "Database writes need SQLAlchemy, pandas, and your database's driver: "
                'pip install "pyflow-studio[db]" plus the driver (see docs/database-connections.md)'
            ) from exc

        ctx.message("info", f"Wrote {df.height} rows to {cfg.table} ({cfg.mode.value})")
        return {"out": frame}
