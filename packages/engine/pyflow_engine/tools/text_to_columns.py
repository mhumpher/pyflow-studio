"""Text to Columns — split a delimited field into multiple columns, or into rows."""
from __future__ import annotations

from enum import Enum

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class SplitMode(str, Enum):
    columns = "columns"
    rows = "rows"


class TextToColumnsConfig(BaseModel):
    field: str = PField(default="", title="Field to split", json_schema_extra={"x-editor": "field"})
    delimiter: str = PField(default=",", title="Delimiter")
    mode: SplitMode = PField(default=SplitMode.columns, title="Split into")
    num_columns: int = PField(default=3, title="Number of columns (columns mode)")
    prefix: str = PField(default="col", title="New column prefix (columns mode)")
    keep_original: bool = PField(default=False, title="Keep original field")


class TextToColumnsTool(Tool):
    type = "parse.text_to_columns"
    name = "Text to Columns"
    category = "Parse"
    icon = "columns"
    Config = TextToColumnsConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: TextToColumnsConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        if not cfg.field:
            return {"out": Frame(src)}
        delim = cfg.delimiter or ","
        col = pl.col(cfg.field).cast(pl.String)

        if cfg.mode is SplitMode.rows:
            out = src.with_columns(col.str.split(delim).alias(cfg.field)).explode(cfg.field)
            return {"out": Frame(out)}

        n = max(1, cfg.num_columns)
        prefix = cfg.prefix or "col"
        names = [f"{prefix}{i + 1}" for i in range(n)]
        # splitn keeps the remainder in the last field (no data loss)
        struct = col.str.splitn(delim, n).struct.rename_fields(names)
        out = src.with_columns(struct.alias("__pf_ttc")).unnest("__pf_ttc")
        if not cfg.keep_original:
            out = out.drop(cfg.field)
        return {"out": Frame(out)}
