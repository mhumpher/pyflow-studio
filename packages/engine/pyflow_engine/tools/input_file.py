"""Input Data — read a file into the workflow as a lazy Frame."""
from __future__ import annotations

import os
from enum import Enum

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import OutputAnchor, Tool


class FileFormat(str, Enum):
    csv = "csv"
    parquet = "parquet"
    arrow = "arrow"
    json = "json"


class InputFileConfig(BaseModel):
    path: str = PField(default="", title="File path", json_schema_extra={"x-editor": "file"})
    format: FileFormat = PField(default=FileFormat.csv, title="Format")
    has_header: bool = PField(default=True, title="First row is header")
    delimiter: str = PField(default=",", title="Delimiter (CSV)")


class InputFileTool(Tool):
    type = "input.file"
    name = "Input Data"
    category = "Input/Output"
    icon = "file-input"
    Config = InputFileConfig
    inputs = []
    outputs = [OutputAnchor("out")]

    def cache_key(self, cfg: InputFileConfig) -> object:
        # Invalidate the cache when the source file changes.
        try:
            st = os.stat(cfg.path)
            return [st.st_mtime_ns, st.st_size]
        except OSError:
            return None

    def build(self, inputs, cfg: InputFileConfig, ctx) -> dict[str, Frame]:
        if not cfg.path:
            raise ValueError("No file path configured")

        if cfg.format is FileFormat.csv:
            lf = pl.scan_csv(cfg.path, has_header=cfg.has_header, separator=cfg.delimiter)
        elif cfg.format is FileFormat.parquet:
            lf = pl.scan_parquet(cfg.path)
        elif cfg.format is FileFormat.arrow:
            lf = pl.scan_ipc(cfg.path)
        elif cfg.format is FileFormat.json:
            lf = pl.read_json(cfg.path).lazy()
        else:  # pragma: no cover - enum is exhaustive
            raise ValueError(f"Unsupported format: {cfg.format}")

        return {"out": Frame(lf)}
