"""Serialize a Polars sample DataFrame into a compact, JSON-safe grid payload."""
from __future__ import annotations

import math
from typing import Any

import polars as pl


def _san(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    # dates, datetimes, decimals, bytes, nested list/struct -> display string
    return str(v)


def df_to_grid(df: pl.DataFrame) -> dict[str, Any]:
    """Return {"columns": [...], "rows": [[...], ...]} with JSON-safe values."""
    return {
        "columns": df.columns,
        "rows": [[_san(v) for v in row] for row in df.rows()],
    }
