"""Pyflow logical type system and its mapping to Polars/Arrow dtypes.

Logical types are stable string identifiers used across the API and UI. They map
to concrete Polars dtypes for execution (and, via Polars, to Arrow on the wire).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl

# --- logical type <-> polars ------------------------------------------------

_PYFLOW_TO_POLARS: dict[str, Any] = {
    "bool": pl.Boolean,
    "int8": pl.Int8,
    "int16": pl.Int16,
    "int32": pl.Int32,
    "int64": pl.Int64,
    "uint8": pl.UInt8,
    "uint16": pl.UInt16,
    "uint32": pl.UInt32,
    "uint64": pl.UInt64,
    "float32": pl.Float32,
    "float64": pl.Float64,
    "string": pl.String,
    "date": pl.Date,
    "time": pl.Time,
    "datetime": pl.Datetime,
    "duration": pl.Duration,
    "binary": pl.Binary,
}

_SIMPLE_PAIRS = [
    (pl.Boolean, "bool"),
    (pl.Int8, "int8"),
    (pl.Int16, "int16"),
    (pl.Int32, "int32"),
    (pl.Int64, "int64"),
    (pl.UInt8, "uint8"),
    (pl.UInt16, "uint16"),
    (pl.UInt32, "uint32"),
    (pl.UInt64, "uint64"),
    (pl.Float32, "float32"),
    (pl.Float64, "float64"),
    (pl.String, "string"),
    (pl.Date, "date"),
    (pl.Time, "time"),
    (pl.Binary, "binary"),
]

INTEGER_DTYPES = {
    pl.Int8, pl.Int16, pl.Int32, pl.Int64,
    pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
}
FLOAT_DTYPES = {pl.Float32, pl.Float64}


def polars_to_pyflow(dtype: Any) -> str:
    """Map a Polars dtype to a Pyflow logical type string."""
    for pl_type, name in _SIMPLE_PAIRS:
        if dtype == pl_type:
            return name
    # parametric dtypes
    if isinstance(dtype, pl.Datetime):
        return "datetime"
    if isinstance(dtype, pl.Duration):
        return "duration"
    if isinstance(dtype, pl.Decimal):
        return "decimal"
    if isinstance(dtype, pl.List):
        return "list"
    if isinstance(dtype, pl.Struct):
        return "struct"
    if isinstance(dtype, pl.Categorical) or dtype == pl.Categorical:
        return "string"
    return "string"


def pyflow_to_polars(name: str) -> Any:
    """Map a Pyflow logical type string to a Polars dtype (for casts)."""
    try:
        return _PYFLOW_TO_POLARS[name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown Pyflow type: {name!r}") from exc


# --- schema model -----------------------------------------------------------

@dataclass
class Field:
    name: str
    type: str
    nullable: bool = True
    description: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "description": self.description,
            "source": self.source,
        }


@dataclass
class Schema:
    fields: list[Field]

    @classmethod
    def from_polars(cls, pl_schema: Any) -> "Schema":
        return cls([Field(name, polars_to_pyflow(dt)) for name, dt in pl_schema.items()])

    def names(self) -> list[str]:
        return [f.name for f in self.fields]

    def to_dict(self) -> dict[str, Any]:
        return {"fields": [f.to_dict() for f in self.fields]}
