"""Unique — split rows into first occurrences (Unique) and the rest (Duplicates)."""
from __future__ import annotations

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class UniqueConfig(BaseModel):
    fields: list[str] = PField(
        default_factory=list,
        title="Unique on fields",
        description="Leave empty to dedupe on all fields.",
        json_schema_extra={"x-editor": "fields"},
    )


class UniqueTool(Tool):
    type = "prep.unique"
    name = "Unique"
    category = "Preparation"
    icon = "fingerprint"
    Config = UniqueConfig
    inputs = [InputAnchor("in")]
    outputs = [
        OutputAnchor("unique", label="Unique"),
        OutputAnchor("duplicates", label="Duplicates"),
    ]

    def build(self, inputs, cfg: UniqueConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        names = cfg.fields or src.collect_schema().names()
        is_first = pl.struct(names).is_first_distinct()
        tagged = src.with_columns(is_first.alias("__pf_first"))
        unique = tagged.filter(pl.col("__pf_first")).drop("__pf_first")
        duplicates = tagged.filter(~pl.col("__pf_first")).drop("__pf_first")
        return {"unique": Frame(unique), "duplicates": Frame(duplicates)}
