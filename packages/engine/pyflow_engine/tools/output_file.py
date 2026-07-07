"""Output Data — write the incoming table to a file (the write happens in run(),
never in build(), so the design-time schema pass has no side effects).

Passes its input through on an ``out`` anchor so the written data stays previewable.
"""
from __future__ import annotations

import os
from enum import Enum

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class OutputFormat(str, Enum):
    csv = "csv"
    parquet = "parquet"
    arrow = "arrow"
    json = "json"
    excel = "excel"


class OutputFileConfig(BaseModel):
    path: str = PField(default="", title="Output path", json_schema_extra={"x-editor": "file"})
    format: OutputFormat = PField(default=OutputFormat.csv, title="Format")
    delimiter: str = PField(default=",", title="Delimiter (CSV)")
    write_header: bool = PField(default=True, title="Write header (CSV)")


class OutputFileTool(Tool):
    type = "output.file"
    name = "Output Data"
    category = "Input/Output"
    icon = "file-output"
    Config = OutputFileConfig
    cacheable = False  # side effect (writes a file): always execute
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]  # pass-through, so the write is previewable

    def build(self, inputs, cfg: OutputFileConfig, ctx) -> dict[str, Frame]:
        # No side effects: this is what the design-time schema pass calls.
        if "in" not in inputs:
            raise ValueError("Output Data has no input connected")
        return {"out": inputs["in"]}

    def run(self, inputs, cfg: OutputFileConfig, ctx) -> dict[str, Frame]:
        if "in" not in inputs:
            raise ValueError("Output Data has no input connected")
        if not cfg.path:
            raise ValueError("No output path configured")
        frame = inputs["in"]
        self._write(frame.lazy, cfg)
        ctx.message("info", f"Wrote {cfg.format.value} to {cfg.path}")
        return {"out": frame}

    def _write(self, lf: pl.LazyFrame, cfg: OutputFileConfig) -> None:
        parent = os.path.dirname(cfg.path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        fmt = cfg.format
        if fmt is OutputFormat.csv:
            try:
                lf.sink_csv(cfg.path, separator=cfg.delimiter, include_header=cfg.write_header)
            except Exception:
                lf.collect().write_csv(cfg.path, separator=cfg.delimiter, include_header=cfg.write_header)
        elif fmt is OutputFormat.parquet:
            try:
                lf.sink_parquet(cfg.path)
            except Exception:
                lf.collect().write_parquet(cfg.path)
        elif fmt is OutputFormat.arrow:
            try:
                lf.sink_ipc(cfg.path)
            except Exception:
                lf.collect().write_ipc(cfg.path)
        elif fmt is OutputFormat.json:
            try:
                lf.sink_ndjson(cfg.path)
            except Exception:
                lf.collect().write_ndjson(cfg.path)
        elif fmt is OutputFormat.excel:
            lf.collect().write_excel(cfg.path)  # requires xlsxwriter
        else:  # pragma: no cover - enum is exhaustive
            raise ValueError(f"Unsupported format: {fmt}")
