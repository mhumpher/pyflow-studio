"""Sample — keep a subset of rows: first/last N, every Nth, or a random count/percent.

Random modes need the full input, so they are done in run() (not build()), keeping
the design-time schema pass lazy — sampling never changes the schema.
"""
from __future__ import annotations

from enum import Enum

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class SampleMode(str, Enum):
    first = "first"
    last = "last"
    every_n = "every_n"
    random_n = "random_n"
    random_pct = "random_pct"


class SampleConfig(BaseModel):
    mode: SampleMode = PField(default=SampleMode.first, title="Mode")
    n: float = PField(
        default=100,
        title="N",
        description="Row count; the step for 'every Nth'; or a percent (0-100) for 'random %'.",
    )
    seed: int = PField(default=0, title="Random seed", description="0 = nondeterministic")


class SampleTool(Tool):
    type = "prep.sample"
    name = "Sample"
    category = "Preparation"
    icon = "percent"
    Config = SampleConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: SampleConfig, ctx) -> dict[str, Frame]:
        src = inputs["in"].lazy
        if cfg.mode is SampleMode.first:
            return {"out": Frame(src.head(int(cfg.n)))}
        if cfg.mode is SampleMode.last:
            return {"out": Frame(src.tail(int(cfg.n)))}
        if cfg.mode is SampleMode.every_n:
            step = max(1, int(cfg.n))
            out = (
                src.with_row_index("__pf_rid")
                .filter((pl.col("__pf_rid") % step) == 0)
                .drop("__pf_rid")
            )
            return {"out": Frame(out)}
        # Random modes: schema-only here (lazy passthrough); real sampling in run().
        return {"out": Frame(src)}

    def run(self, inputs, cfg: SampleConfig, ctx) -> dict[str, Frame]:
        if cfg.mode in (SampleMode.first, SampleMode.last, SampleMode.every_n):
            return self.build(inputs, cfg, ctx)

        df = inputs["in"].lazy.collect()
        seed = cfg.seed or None
        if cfg.mode is SampleMode.random_n:
            out = df.sample(n=min(int(cfg.n), df.height), seed=seed)
        else:  # random_pct
            frac = max(0.0, min(1.0, cfg.n / 100.0))
            out = df.sample(fraction=frac, seed=seed)
        return {"out": Frame(out.lazy())}
