"""SQL — transform data with DuckDB SQL over the connected inputs.

Each connected input is exposed to the query as a table named ``input1``..``input3``
(matching its anchor order). DuckDB runs the query — out-of-core for large joins and
aggregations — and the result flows on as a normal Frame.

build/run split: the schema pass runs the query wrapped in ``LIMIT 0`` over empty,
correctly-typed input tables, so design-time inference is cheap and never materializes
data (and surfaces SQL errors live); run() executes the query over the real inputs.
"""
from __future__ import annotations

import polars as pl
from pydantic import BaseModel
from pydantic import Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool

_N = 3
_DEFAULT_QUERY = "SELECT *\nFROM input1"


class SqlConfig(BaseModel):
    query: str = PField(
        default=_DEFAULT_QUERY, title="SQL query", json_schema_extra={"x-editor": "sql"}
    )


def _connect():
    try:
        import duckdb
    except ModuleNotFoundError as exc:  # pragma: no cover - duckdb is a core dependency
        raise ValueError("The SQL tool needs DuckDB: pip install duckdb") from exc
    return duckdb.connect()


class SqlTool(Tool):
    type = "transform.sql"
    name = "SQL"
    category = "Developer"
    icon = "sql"
    Config = SqlConfig
    inputs = [InputAnchor(f"in{i}", label=str(i)) for i in range(1, _N + 1)]
    outputs = [OutputAnchor("out")]

    def _execute(self, inputs, cfg: SqlConfig, *, schema_only: bool) -> pl.DataFrame:
        query = (cfg.query or "").strip().rstrip(";").strip()
        if not query:
            raise ValueError("Write a SQL query")

        con = _connect()
        try:
            registered = 0
            for i in range(1, _N + 1):
                frame = inputs.get(f"in{i}")
                if frame is None:
                    continue
                lf = frame.lazy
                # Schema pass: register an empty, correctly-typed table so DuckDB can
                # plan the query without us collecting the real (possibly huge) input.
                data = pl.DataFrame(schema=dict(lf.collect_schema())) if schema_only else lf.collect()
                con.register(f"input{i}", data.to_arrow())
                registered += 1
            if registered == 0:
                raise ValueError("Connect at least one input")

            wrapped = f"SELECT * FROM (\n{query}\n) AS _pyflow_q"
            if schema_only:
                wrapped += "\nLIMIT 0"
            # .pl() returns a Polars DataFrame directly and handles the zero-row
            # (schema-only) case, which the Arrow path mishandles.
            return con.execute(wrapped).pl()
        finally:
            con.close()

    def build(self, inputs, cfg: SqlConfig, ctx) -> dict[str, Frame]:
        return {"out": Frame(self._execute(inputs, cfg, schema_only=True).lazy())}

    def run(self, inputs, cfg: SqlConfig, ctx) -> dict[str, Frame]:
        return {"out": Frame(self._execute(inputs, cfg, schema_only=False).lazy())}
