"""Union — stack multiple inputs into one table, by field name or by position."""
from __future__ import annotations

from enum import Enum

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class UnionMode(str, Enum):
    by_name = "by_name"
    by_position = "by_position"


class UnionConfig(BaseModel):
    mode: UnionMode = PField(default=UnionMode.by_name, title="Combine")


class UnionTool(Tool):
    type = "join.union"
    name = "Union"
    category = "Join"
    icon = "rows"
    Config = UnionConfig
    inputs = [InputAnchor("in", multi=True, label="in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: UnionConfig, ctx) -> dict[str, Frame]:
        frames = inputs.get("in", [])
        if isinstance(frames, Frame):
            frames = [frames]
        lazies = [f.lazy for f in frames]

        if not lazies:
            raise ValueError("Union has no connected inputs")
        if len(lazies) == 1:
            return {"out": Frame(lazies[0])}

        if cfg.mode is UnionMode.by_position:
            names = lazies[0].collect_schema().names()
            aligned = []
            for lf in lazies:
                cols = lf.collect_schema().names()
                if len(cols) != len(names):
                    raise ValueError("Union by position requires the same number of columns")
                aligned.append(lf.rename(dict(zip(cols, names))))
            combined = pl.concat(aligned, how="vertical_relaxed")
        else:
            combined = pl.concat(lazies, how="diagonal_relaxed")

        return {"out": Frame(combined)}
