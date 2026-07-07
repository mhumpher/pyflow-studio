"""Select — choose, reorder, rename, and retype fields."""
from __future__ import annotations

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool
from ..types import pyflow_to_polars


class SelectField(BaseModel):
    source: str = PField(default="", title="Field", json_schema_extra={"x-editor": "field"})
    rename: str = PField(default="", title="Rename to")
    type: str = PField(default="", title="Type", json_schema_extra={"x-editor": "type"})
    include: bool = PField(default=True, title="Keep")


class SelectConfig(BaseModel):
    fields: list[SelectField] = PField(default_factory=list, title="Fields")


class SelectTool(Tool):
    type = "prep.select"
    name = "Select"
    category = "Preparation"
    icon = "columns"
    Config = SelectConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: SelectConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        if not cfg.fields:
            return {"out": Frame(src)}  # unconfigured Select passes through

        exprs = []
        for f in cfg.fields:
            if not f.include or not f.source:
                continue
            expr = pl.col(f.source)
            if f.type:
                expr = expr.cast(pyflow_to_polars(f.type), strict=False)
            if f.rename:
                expr = expr.alias(f.rename)
            exprs.append(expr)

        if not exprs:
            return {"out": Frame(src)}
        return {"out": Frame(src.select(exprs))}
