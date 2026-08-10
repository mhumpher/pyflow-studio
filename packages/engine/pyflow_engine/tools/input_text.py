"""Text Input — manually entered rows as a source Frame (Alteryx's Text Input)."""
from __future__ import annotations

import polars as pl
from pydantic import BaseModel
from pydantic import Field as PField

from ..frame import Frame
from ..tool import OutputAnchor, Tool
from ..types import pyflow_to_polars

# A friendly starting grid so the tool isn't blank when dropped.
_DEFAULT_TABLE = {
    "columns": [
        {"name": "Column1", "type": "string"},
        {"name": "Column2", "type": "string"},
    ],
    "rows": [["", ""], ["", ""], ["", ""]],
}

_TRUE = ["true", "1", "yes", "y", "t"]
_FALSE = ["false", "0", "no", "n", "f"]


class TextColumn(BaseModel):
    name: str = ""
    type: str = "string"


class TextTable(BaseModel):
    columns: list[TextColumn] = PField(default_factory=list)
    # Cells are stored as strings and cast per column type at build time.
    rows: list[list[str]] = PField(default_factory=list)


class TextInputConfig(BaseModel):
    table: TextTable = PField(
        default_factory=lambda: TextTable.model_validate(_DEFAULT_TABLE),
        title="Data",
        json_schema_extra={"x-editor": "grid", "default": _DEFAULT_TABLE},
    )


def _cast_expr(name: str, ptype: str) -> pl.Expr:
    """Cast a string column to its declared type; blank cells become null."""
    raw = pl.col(name).cast(pl.String)
    stripped = raw.str.strip_chars()

    if ptype == "string":
        return pl.when(raw == "").then(None).otherwise(raw).alias(name)
    if ptype == "bool":
        low = stripped.str.to_lowercase()
        return (
            pl.when(low.is_in(_TRUE))
            .then(pl.lit(True))
            .when(low.is_in(_FALSE))
            .then(pl.lit(False))
            .otherwise(pl.lit(None))
            .alias(name)
        )

    col = pl.when(stripped == "").then(None).otherwise(stripped)
    if ptype == "date":
        return col.str.to_date(strict=False).alias(name)
    if ptype == "datetime":
        return col.str.to_datetime(strict=False).alias(name)
    if ptype == "time":
        return col.str.to_time(strict=False).alias(name)
    try:
        dtype = pyflow_to_polars(ptype)
    except ValueError:
        return col.alias(name)  # unknown type — leave as string
    return col.cast(dtype, strict=False).alias(name)


class TextInputTool(Tool):
    type = "input.text"
    name = "Text Input"
    category = "Input/Output"
    icon = "table"
    Config = TextInputConfig
    inputs = []
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: TextInputConfig, ctx) -> dict[str, Frame]:
        columns = cfg.table.columns
        names = [c.name.strip() for c in columns]

        if not names:
            raise ValueError("Add at least one column")
        if any(n == "" for n in names):
            raise ValueError("Every column needs a name")
        if len(set(names)) != len(names):
            raise ValueError("Column names must be unique")

        n = len(names)
        data: dict[str, list[str]] = {name: [] for name in names}
        for row in cfg.table.rows:
            for i, name in enumerate(names):
                cell = row[i] if i < len(row) else ""
                data[name].append("" if cell is None else str(cell))

        df = pl.DataFrame(data, schema={name: pl.String for name in names})
        df = df.with_columns([_cast_expr(names[i], columns[i].type or "string") for i in range(n)])
        return {"out": Frame(df.lazy())}
