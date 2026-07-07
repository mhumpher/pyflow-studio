"""Unpivot — turn columns into rows (wide -> long), the inverse of Cross Tab.

Fully lazy: the output schema (kept fields + name + value) is known at design time.
"""
from __future__ import annotations

from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class UnpivotConfig(BaseModel):
    id_fields: list[str] = PField(
        default_factory=list, title="Keep fields", json_schema_extra={"x-editor": "fields"}
    )
    value_fields: list[str] = PField(
        default_factory=list, title="Unpivot fields", json_schema_extra={"x-editor": "fields"}
    )
    name_column: str = PField(default="name", title="Name column")
    value_column: str = PField(default="value", title="Value column")


class UnpivotTool(Tool):
    type = "transform.unpivot"
    name = "Unpivot"
    category = "Transform"
    icon = "rows"
    Config = UnpivotConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: UnpivotConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        names = src.collect_schema().names()
        value_fields = [f for f in cfg.value_fields if f in names]
        if not value_fields:
            return {"out": Frame(src)}  # nothing selected -> passthrough
        id_fields = [f for f in cfg.id_fields if f in names]
        out = src.unpivot(
            on=value_fields,
            index=id_fields,
            variable_name=cfg.name_column or "name",
            value_name=cfg.value_column or "value",
        )
        return {"out": Frame(out)}
