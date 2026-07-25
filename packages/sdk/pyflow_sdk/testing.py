"""Test helpers for tool authors.

``run_tool`` executes a single tool in isolation — no server, no browser — and returns
its outputs as collected Polars DataFrames:

    from pyflow_sdk.testing import run_tool
    out = run_tool(FilterTool, {"expression": '[status] == "active"'}, {"in": df})
    assert out["true"].height == 5
"""
from __future__ import annotations

from typing import Any

import polars as pl

from pyflow_engine.context import RunContext
from pyflow_engine.frame import Frame
from pyflow_engine.tool import Tool

__all__ = ["run_tool"]


def _wrap(value: Any) -> Any:
    if isinstance(value, list):
        return [Frame.from_polars(v) for v in value]
    return Frame.from_polars(value)


def run_tool(
    tool_cls: type[Tool],
    config: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    *,
    build_only: bool = False,
) -> dict[str, pl.DataFrame]:
    """Run one tool and return ``{anchor: DataFrame}``.

    ``inputs`` maps input-anchor ids to Polars DataFrames (or a list of DataFrames for
    a ``multi`` anchor). ``build_only=True`` calls ``build()`` instead of ``run()``
    (the design-time path, with no side effects).
    """
    cfg = tool_cls.Config.model_validate(config or {})
    frame_inputs = {anchor: _wrap(value) for anchor, value in (inputs or {}).items()}
    ctx = RunContext("test", lambda _event: None)
    tool = tool_cls()
    outputs = (
        tool.build(frame_inputs, cfg, ctx) if build_only else tool.run(frame_inputs, cfg, ctx)
    )
    return {anchor: frame.lazy.collect() for anchor, frame in outputs.items()}
