"""Frame — the backend-neutral table handle tools operate on.

Phase 0 wraps a Polars LazyFrame. The public surface (schema/head/count/to_arrow)
is intentionally small so later backends (DuckDB, Dask) can implement the same
protocol without changing tool code.
"""
from __future__ import annotations

from typing import Any

import polars as pl

from .types import Schema


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
        return self._lazy.head(n).collect()

    def count(self) -> int:
        """Row count via a cheap aggregation."""
        return int(self._lazy.select(pl.len()).collect().item())

    def collect(self) -> pl.DataFrame:
        return self._lazy.collect()

    def to_arrow(self) -> Any:
        return self._lazy.collect().to_arrow()

    @classmethod
    def from_polars(cls, df: pl.DataFrame | pl.LazyFrame) -> "Frame":
        return cls(df if isinstance(df, pl.LazyFrame) else df.lazy())
