"""Summarize — group by fields and compute aggregations."""
from __future__ import annotations

from enum import Enum

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class AggFunc(str, Enum):
    sum = "sum"
    count = "count"
    count_distinct = "count_distinct"
    min = "min"
    max = "max"
    mean = "mean"
    median = "median"
    std = "std"
    first = "first"
    last = "last"


class Aggregation(BaseModel):
    field: str = PField(default="", title="Field", json_schema_extra={"x-editor": "field"})
    func: AggFunc = PField(default=AggFunc.sum, title="Aggregation")
    output: str = PField(default="", title="Output field")


class SummarizeConfig(BaseModel):
    group_by: list[str] = PField(
        default_factory=list, title="Group by", json_schema_extra={"x-editor": "fields"}
    )
    aggregations: list[Aggregation] = PField(default_factory=list, title="Aggregations")


def _agg_expr(agg: Aggregation) -> pl.Expr:
    col = pl.col(agg.field)
    fn = {
        AggFunc.sum: col.sum,
        AggFunc.count: col.count,
        AggFunc.count_distinct: col.n_unique,
        AggFunc.min: col.min,
        AggFunc.max: col.max,
        AggFunc.mean: col.mean,
        AggFunc.median: col.median,
        AggFunc.std: col.std,
        AggFunc.first: col.first,
        AggFunc.last: col.last,
    }[agg.func]
    output = agg.output or f"{agg.func.value}_{agg.field}"
    return fn().alias(output)


class SummarizeTool(Tool):
    type = "transform.summarize"
    name = "Summarize"
    category = "Transform"
    icon = "sigma"
    Config = SummarizeConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: SummarizeConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        aggs = [_agg_expr(a) for a in cfg.aggregations if a.field]

        if not aggs:
            if cfg.group_by:
                return {"out": Frame(src.select(cfg.group_by).unique(maintain_order=True))}
            return {"out": Frame(src)}

        if cfg.group_by:
            return {"out": Frame(src.group_by(cfg.group_by, maintain_order=True).agg(aggs))}
        return {"out": Frame(src.select(aggs))}
