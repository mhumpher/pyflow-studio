"""RegEx — parse (extract capture groups to columns), match, replace, or tokenize.

Parse uses named/positional capture groups, so its output columns are known from the
pattern (lazy). Named groups ``(?<name>...)`` become the column names.
"""
from __future__ import annotations

from enum import Enum

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class RegexMethod(str, Enum):
    parse = "parse"
    match = "match"
    replace = "replace"
    tokenize = "tokenize"


class RegexConfig(BaseModel):
    field: str = PField(default="", title="Field", json_schema_extra={"x-editor": "field"})
    pattern: str = PField(
        default="",
        title="Regular expression",
        description=r"e.g. (?<area>\d{3})-(\d{3})-(\d{4})  — named groups become column names.",
    )
    method: RegexMethod = PField(default=RegexMethod.parse, title="Method")
    replacement: str = PField(default="", title="Replacement (replace mode)")
    output_field: str = PField(
        default="", title="Output field", description="match: flag column; replace: target (blank = in place)"
    )


class RegexTool(Tool):
    type = "parse.regex"
    name = "RegEx"
    category = "Parse"
    icon = "regex"
    Config = RegexConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: RegexConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        if not cfg.field or not cfg.pattern:
            return {"out": Frame(src)}
        col = pl.col(cfg.field).cast(pl.String)

        if cfg.method is RegexMethod.parse:
            out = src.with_columns(col.str.extract_groups(cfg.pattern).alias("__pf_rx")).unnest(
                "__pf_rx"
            )
        elif cfg.method is RegexMethod.match:
            name = cfg.output_field or "matched"
            out = src.with_columns(col.str.contains(cfg.pattern).alias(name))
        elif cfg.method is RegexMethod.replace:
            target = cfg.output_field or cfg.field
            out = src.with_columns(
                col.str.replace_all(cfg.pattern, cfg.replacement).alias(target)
            )
        else:  # tokenize -> one row per match
            out = src.with_columns(col.str.extract_all(cfg.pattern).alias(cfg.field)).explode(
                cfg.field
            )
        return {"out": Frame(out)}
