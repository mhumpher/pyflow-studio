"""Formula — add or replace columns using the Pyflow formula language."""
from __future__ import annotations

from pydantic import BaseModel, Field as PField

from ..formula import compile_expr
from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool
from ..types import pyflow_to_polars


class FormulaItem(BaseModel):
    output: str = PField(default="", title="Output field")
    expression: str = PField(
        default="", title="Expression", json_schema_extra={"x-editor": "formula"}
    )
    type: str = PField(default="", title="Type", json_schema_extra={"x-editor": "type"})


class FormulaConfig(BaseModel):
    formulas: list[FormulaItem] = PField(default_factory=list, title="Formulas")


class FormulaTool(Tool):
    type = "prep.formula"
    name = "Formula"
    category = "Preparation"
    icon = "function"
    Config = FormulaConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: FormulaConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        exprs = []
        for item in cfg.formulas:
            if not item.output or not item.expression.strip():
                continue
            expr = compile_expr(item.expression)
            if item.type:
                expr = expr.cast(pyflow_to_polars(item.type), strict=False)
            exprs.append(expr.alias(item.output))

        if not exprs:
            return {"out": Frame(src)}
        return {"out": Frame(src.with_columns(exprs))}
