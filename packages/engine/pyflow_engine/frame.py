"""Frame — the backend-neutral table handle tools operate on.

Phase 0 wraps a Polars LazyFrame. The public surface (schema/head/count/to_arrow)
is intentionally small so later backends (DuckDB, Dask) can implement the same
protocol without changing tool code.
"""
from __future__ import annotations

from typing import Any

import polars as pl

from .types import Schema


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    """Collect with Polars' streaming engine so large blocking operations
    (group-by / join / sort) spill to disk instead of exhausting memory. Falls
    back to the in-memory engine if the streaming engine can't run the plan."""
    try:
        return lf.collect(engine="streaming")
    except Exception:
        return lf.collect()


class Frame:
    def __init__(self, lazy: pl.LazyFrame) -> None:
        self._lazy = lazy

    @property
    def lazy(self) -> pl.LazyFrame:
        return self._lazy

    def schema(self) -> Schema:
        """Resolve the output schema lazily (no data materialized)."""
        return Schema.from_polars(self._lazy.collect_schema())

    def head(self, n: int) -> pl.DataFrame:
        """Collect a bounded sample for previews."""
        return collect_streaming(self._lazy.head(n))

    def count(self) -> int:
        """Row count via a cheap aggregation."""
        return int(collect_streaming(self._lazy.select(pl.len())).item())

    def collect(self) -> pl.DataFrame:
        return collect_streaming(self._lazy)

    def to_arrow(self) -> Any:
        return collect_streaming(self._lazy).to_arrow()

    @classmethod
    def from_polars(cls, df: pl.DataFrame | pl.LazyFrame) -> "Frame":
        return cls(df if isinstance(df, pl.LazyFrame) else df.lazy())
