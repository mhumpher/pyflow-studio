"""Sort — order rows by one or more fields, ascending or descending."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class SortDirection(str, Enum):
    ascending = "ascending"
    descending = "descending"


class SortKey(BaseModel):
    field: str = PField(default="", title="Field", json_schema_extra={"x-editor": "field"})
    direction: SortDirection = PField(default=SortDirection.ascending, title="Direction")


class SortConfig(BaseModel):
    keys: list[SortKey] = PField(default_factory=list, title="Sort by")


class SortTool(Tool):
    type = "prep.sort"
    name = "Sort"
    category = "Preparation"
    icon = "sort"
    Config = SortConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: SortConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        keys = [k for k in cfg.keys if k.field]
        if not keys:
            return {"out": Frame(src)}
        by = [k.field for k in keys]
        descending = [k.direction is SortDirection.descending for k in keys]
        return {"out": Frame(src.sort(by=by, descending=descending))}
