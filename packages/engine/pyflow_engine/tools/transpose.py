"""Transpose — flip the table so rows become columns and columns become rows.

Output columns = one per input row, so they are data-dependent: build() exposes only
the optional names column at design time; run() performs the real transpose.
Note: transposing columns of mixed types coerces them to a common type (often string).
"""
from __future__ import annotations

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class TransposeConfig(BaseModel):
    header_column: str = PField(
        default="",
        title="Column names from",
        description="Optional: use this column's values as the new column names.",
        json_schema_extra={"x-editor": "field"},
    )
    include_names: bool = PField(default=True, title="Keep original column names")
    names_to: str = PField(default="column", title="Name of the names column")


class TransposeTool(Tool):
    type = "transform.transpose"
    name = "Transpose"
    category = "Transform"
    icon = "flip"
    Config = TransposeConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: TransposeConfig, ctx) -> dict[str, Frame]:
        # Data-dependent columns (one per input row); expose only the names column.
        if cfg.include_names:
            col = cfg.names_to or "column"
            return {"out": Frame(pl.DataFrame({col: pl.Series(col, [], dtype=pl.String)}).lazy())}
        return {"out": Frame(pl.DataFrame().lazy())}

    def run(self, inputs, cfg: TransposeConfig, ctx) -> dict[str, Frame]:
        df = inputs["in"].lazy.collect()
        names_to = cfg.names_to or "column"

        if cfg.header_column and cfg.header_column in df.columns:
            column_names = df[cfg.header_column].cast(pl.String).to_list()
            body = df.drop(cfg.header_column)
            out = body.transpose(
                include_header=cfg.include_names, header_name=names_to, column_names=column_names
            )
        else:
            out = df.transpose(include_header=cfg.include_names, header_name=names_to)
        return {"out": Frame(out.lazy())}
