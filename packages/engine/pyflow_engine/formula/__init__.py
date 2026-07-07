"""The Pyflow formula language.

An Alteryx-like expression language — ``[Field]`` references, familiar functions,
and ``IF ... THEN ... ELSE ... ENDIF`` — that compiles to a Polars expression.

Public API:
    compile_expr(source)             -> pl.Expr
    result_type(source, schema)      -> pyflow type string of the result
    validate(source, schema)         -> {"ok": bool, "type"?: str, "error"?: str}
    FUNCTION_NAMES                    -> list[str] (for editor autocomplete)
"""
from __future__ import annotations

from typing import Any

import polars as pl

from ..types import polars_to_pyflow, pyflow_to_polars
from .compiler import FUNCTIONS, compile_ast
from .parser import FormulaError, parse

__all__ = [
    "compile_expr",
    "result_type",
    "validate",
    "FormulaError",
    "FUNCTION_NAMES",
]

FUNCTION_NAMES = sorted(FUNCTIONS.keys())


def compile_expr(source: str) -> pl.Expr:
    """Parse and compile a formula string into a Polars expression."""
    return compile_ast(parse(source))


def _safe_polars_dtype(pyflow_type: str) -> Any:
    try:
        return pyflow_to_polars(pyflow_type)
    except ValueError:
        return pl.String  # unknown/parametric types stand in as String for inference


def _empty_frame(schema: dict[str, str]) -> pl.DataFrame:
    return pl.DataFrame(
        {name: pl.Series(name, [], dtype=_safe_polars_dtype(t)) for name, t in schema.items()}
    )


def _clean_error(exc: Exception) -> str:
    msg = str(exc).strip()
    return msg.splitlines()[0] if msg else exc.__class__.__name__


def result_type(source: str, schema: dict[str, str]) -> str:
    """Infer the Pyflow result type of a formula against an input schema (no data)."""
    expr = compile_expr(source)
    frame = _empty_frame(schema)
    dtype = frame.select(expr.alias("__pyflow_result__")).schema["__pyflow_result__"]
    return polars_to_pyflow(dtype)


def validate(source: str, schema: dict[str, str]) -> dict[str, Any]:
    """Validate a formula against a schema; return its result type or an error."""
    if not source or not source.strip():
        return {"ok": False, "error": "Empty expression"}
    try:
        return {"ok": True, "type": result_type(source, schema)}
    except FormulaError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # Polars errors (unknown column, type mismatch, ...)
        return {"ok": False, "error": _clean_error(exc)}
