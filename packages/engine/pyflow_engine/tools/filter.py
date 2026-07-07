"""Filter — split rows by a boolean formula expression into True/False outputs."""
from __future__ import annotations

from pydantic import BaseModel, Field as PField

from ..formula import compile_expr
from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class FilterConfig(BaseModel):
    expression: str = PField(
        default="",
        title="Keep rows where",
        description='A boolean formula, e.g. [status] == "active" AND [spend] > 1000',
        json_schema_extra={"x-editor": "formula"},
    )


class FilterTool(Tool):
    type = "prep.filter"
    name = "Filter"
    category = "Preparation"
    icon = "filter"
    Config = FilterConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("true", label="True"), OutputAnchor("false", label="False")]

    def build(self, inputs, cfg: FilterConfig, ctx) -> dict[str, Frame]:
        if not cfg.expression.strip():
            raise ValueError("No filter expression configured")
        src = inputs["in"].lazy
        pred = compile_expr(cfg.expression)
        return {"true": Frame(src.filter(pred)), "false": Frame(src.filter(~pred))}
