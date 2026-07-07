"""DateTime — parse a string to a date/datetime, or format a date/datetime to a string."""
from __future__ import annotations

from enum import Enum

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class DtDirection(str, Enum):
    parse = "parse"  # string -> date/datetime
    format = "format"  # date/datetime -> string


class DtOutputType(str, Enum):
    datetime = "datetime"
    date = "date"


class DateTimeConfig(BaseModel):
    field: str = PField(default="", title="Field", json_schema_extra={"x-editor": "field"})
    direction: DtDirection = PField(default=DtDirection.parse, title="Direction")
    format: str = PField(
        default="",
        title="Format",
        description="strptime/strftime, e.g. %Y-%m-%d or %m/%d/%Y. Blank = infer (parse only).",
    )
    output_type: DtOutputType = PField(default=DtOutputType.date, title="Parse to (parse mode)")
    output_field: str = PField(default="", title="Output field (blank = replace)")


class DateTimeTool(Tool):
    type = "parse.datetime"
    name = "DateTime"
    category = "Parse"
    icon = "calendar"
    Config = DateTimeConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: DateTimeConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        if not cfg.field:
            return {"out": Frame(src)}
        col = pl.col(cfg.field)
        target = cfg.output_field or cfg.field

        if cfg.direction is DtDirection.parse:
            fmt = cfg.format or None
            if cfg.output_type is DtOutputType.date:
                expr = col.cast(pl.String).str.to_date(fmt, strict=False)
            else:
                expr = col.cast(pl.String).str.to_datetime(fmt, strict=False)
        else:
            expr = col.dt.strftime(cfg.format or "%Y-%m-%d")

        return {"out": Frame(src.with_columns(expr.alias(target)))}
