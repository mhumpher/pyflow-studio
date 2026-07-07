"""Cross Tab — pivot rows into columns (long -> wide).

The output columns come from the distinct values in the header field, so they are
data-dependent: build() (the schema pass) exposes only the known group-by columns,
and run() performs the real pivot (which needs the data). Columns appear after a run.
"""
from __future__ import annotations

from enum import Enum

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class PivotAgg(str, Enum):
    sum = "sum"
    mean = "mean"
    min = "min"
    max = "max"
    first = "first"
    last = "last"
    count = "count"


_PIVOT_AGG = {
    "sum": "sum",
    "mean": "mean",
    "min": "min",
    "max": "max",
    "first": "first",
    "last": "last",
    "count": "len",
}


class CrossTabConfig(BaseModel):
    group_by: list[str] = PField(
        default_factory=list, title="Group by (rows)", json_schema_extra={"x-editor": "fields"}
    )
    header_field: str = PField(
        default="", title="Column headers from", json_schema_extra={"x-editor": "field"}
    )
    value_field: str = PField(
        default="", title="Values from", json_schema_extra={"x-editor": "field"}
    )
    aggregation: PivotAgg = PField(default=PivotAgg.sum, title="Aggregate values with")


class CrossTabTool(Tool):
    type = "transform.crosstab"
    name = "Cross Tab"
    category = "Transform"
    icon = "table"
    Config = CrossTabConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: CrossTabConfig, ctx) -> dict[str, Frame]:
        # Data-dependent columns: expose only the known row (index) columns at design time.
        src = inputs["in"].lazy
        if cfg.group_by:
            names = src.collect_schema().names()
            idx = [c for c in cfg.group_by if c in names]
            if idx:
                return {"out": Frame(src.select(idx))}
        return {"out": Frame(pl.DataFrame().lazy())}

    def run(self, inputs, cfg: CrossTabConfig, ctx) -> dict[str, Frame]:
        if not cfg.group_by or not cfg.header_field or not cfg.value_field:
            raise ValueError("Cross Tab needs group-by field(s), a header field, and a value field")
        df = inputs["in"].lazy.collect()
        out = df.pivot(
            cfg.header_field,
            index=cfg.group_by,
            values=cfg.value_field,
            aggregate_function=_PIVOT_AGG[cfg.aggregation.value],
        )
        return {"out": Frame(out.lazy())}
