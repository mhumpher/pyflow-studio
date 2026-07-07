"""Compile a formula AST into a Polars expression, plus the function library."""
from __future__ import annotations

import datetime as _dt
from typing import Any, Callable

import polars as pl

from .parser import (
    BinOp,
    Bool,
    BoolOp,
    Call,
    Compare,
    FieldRef,
    FormulaError,
    IfExpr,
    Not,
    Null,
    Num,
    Str,
    Unary,
)

# name (lowercased) -> function taking the raw arg AST list, returning a pl.Expr
FUNCTIONS: dict[str, Callable[[list[Any]], pl.Expr]] = {}


def _register(name: str) -> Callable[[Callable], Callable]:
    def deco(fn: Callable[[list[Any]], pl.Expr]) -> Callable:
        FUNCTIONS[name] = fn
        return fn

    return deco


def _need(args: list[Any], lo: int, hi: int | None, name: str) -> None:
    hi = lo if hi is None else hi
    if not (lo <= len(args) <= hi):
        want = str(lo) if lo == hi else f"{lo}-{hi}"
        raise FormulaError(f"{name} expects {want} argument(s), got {len(args)}")


def _literal(node: Any) -> Any:
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Str):
        return node.value
    if isinstance(node, Bool):
        return node.value
    raise FormulaError("Expected a constant literal argument here")


_ARITH = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "%": lambda a, b: a % b,
}
_COMPARE = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
}


def compile_ast(node: Any) -> pl.Expr:
    if isinstance(node, Num):
        return pl.lit(node.value)
    if isinstance(node, Str):
        return pl.lit(node.value)
    if isinstance(node, Bool):
        return pl.lit(node.value)
    if isinstance(node, Null):
        return pl.lit(None)
    if isinstance(node, FieldRef):
        return pl.col(node.name)
    if isinstance(node, Unary):
        operand = compile_ast(node.operand)
        return -operand if node.op == "-" else operand
    if isinstance(node, BinOp):
        return _ARITH[node.op](compile_ast(node.left), compile_ast(node.right))
    if isinstance(node, Compare):
        return _COMPARE[node.op](compile_ast(node.left), compile_ast(node.right))
    if isinstance(node, BoolOp):
        left, right = compile_ast(node.left), compile_ast(node.right)
        return (left & right) if node.op == "AND" else (left | right)
    if isinstance(node, Not):
        return ~compile_ast(node.operand)
    if isinstance(node, IfExpr):
        return _compile_if(node)
    if isinstance(node, Call):
        fn = FUNCTIONS.get(node.name.lower())
        if fn is None:
            raise FormulaError(f"Unknown function {node.name!r}")
        return fn(node.args)
    raise FormulaError(f"Cannot compile node {type(node).__name__}")


def _compile_if(node: IfExpr) -> pl.Expr:
    acc: Any = None
    for cond, result in node.branches:
        c, r = compile_ast(cond), compile_ast(result)
        acc = pl.when(c).then(r) if acc is None else acc.when(c).then(r)
    orelse = compile_ast(node.orelse) if node.orelse is not None else pl.lit(None)
    return acc.otherwise(orelse)


# --- function library -------------------------------------------------------

def _c(node: Any) -> pl.Expr:
    return compile_ast(node)


# text
@_register("trim")
def _trim(a):
    _need(a, 1, 1, "Trim")
    return _c(a[0]).cast(pl.String).str.strip_chars()


@_register("upper")
def _upper(a):
    _need(a, 1, 1, "Upper")
    return _c(a[0]).cast(pl.String).str.to_uppercase()


@_register("lower")
def _lower(a):
    _need(a, 1, 1, "Lower")
    return _c(a[0]).cast(pl.String).str.to_lowercase()


@_register("length")
def _length(a):
    _need(a, 1, 1, "Length")
    return _c(a[0]).cast(pl.String).str.len_chars()


@_register("substring")
def _substring(a):
    _need(a, 2, 3, "Substring")
    start = int(_literal(a[1]))
    length = int(_literal(a[2])) if len(a) > 2 else None
    return _c(a[0]).cast(pl.String).str.slice(start, length)


@_register("contains")
def _contains(a):
    _need(a, 2, 2, "Contains")
    return _c(a[0]).cast(pl.String).str.contains(str(_literal(a[1])), literal=True)


@_register("startswith")
def _startswith(a):
    _need(a, 2, 2, "StartsWith")
    return _c(a[0]).cast(pl.String).str.starts_with(str(_literal(a[1])))


@_register("endswith")
def _endswith(a):
    _need(a, 2, 2, "EndsWith")
    return _c(a[0]).cast(pl.String).str.ends_with(str(_literal(a[1])))


@_register("replace")
def _replace(a):
    _need(a, 3, 3, "Replace")
    return _c(a[0]).cast(pl.String).str.replace_all(
        str(_literal(a[1])), str(_literal(a[2])), literal=True
    )


@_register("concat")
def _concat(a):
    _need(a, 1, 99, "Concat")
    return pl.concat_str([_c(x).cast(pl.String) for x in a], separator="")


# numeric
@_register("abs")
def _abs(a):
    _need(a, 1, 1, "Abs")
    return _c(a[0]).abs()


@_register("round")
def _round(a):
    _need(a, 1, 2, "Round")
    decimals = int(_literal(a[1])) if len(a) > 1 else 0
    return _c(a[0]).round(decimals)


@_register("floor")
def _floor(a):
    _need(a, 1, 1, "Floor")
    return _c(a[0]).floor()


@_register("ceil")
def _ceil(a):
    _need(a, 1, 1, "Ceil")
    return _c(a[0]).ceil()


@_register("pow")
def _pow(a):
    _need(a, 2, 2, "Pow")
    return _c(a[0]).pow(_c(a[1]))


@_register("sqrt")
def _sqrt(a):
    _need(a, 1, 1, "Sqrt")
    return _c(a[0]).sqrt()


@_register("mod")
def _mod(a):
    _need(a, 2, 2, "Mod")
    return _c(a[0]) % _c(a[1])


@_register("min")
def _min(a):
    _need(a, 1, 99, "Min")
    return pl.min_horizontal([_c(x) for x in a])


@_register("max")
def _max(a):
    _need(a, 1, 99, "Max")
    return pl.max_horizontal([_c(x) for x in a])


# null handling
@_register("isnull")
def _isnull(a):
    _need(a, 1, 1, "IsNull")
    return _c(a[0]).is_null()


@_register("isnotnull")
def _isnotnull(a):
    _need(a, 1, 1, "IsNotNull")
    return _c(a[0]).is_not_null()


@_register("coalesce")
def _coalesce(a):
    _need(a, 1, 99, "Coalesce")
    return pl.coalesce([_c(x) for x in a])


# conversion
@_register("tostring")
def _tostring(a):
    _need(a, 1, 1, "ToString")
    return _c(a[0]).cast(pl.String)


@_register("tonumber")
def _tonumber(a):
    _need(a, 1, 1, "ToNumber")
    return _c(a[0]).cast(pl.Float64, strict=False)


@_register("toint")
def _toint(a):
    _need(a, 1, 1, "ToInt")
    return _c(a[0]).cast(pl.Int64, strict=False)


# date/time
@_register("now")
def _now(a):
    _need(a, 0, 0, "Now")
    return pl.lit(_dt.datetime.now())


@_register("today")
def _today(a):
    _need(a, 0, 0, "Today")
    return pl.lit(_dt.date.today())


@_register("year")
def _year(a):
    _need(a, 1, 1, "Year")
    return _c(a[0]).dt.year()


@_register("month")
def _month(a):
    _need(a, 1, 1, "Month")
    return _c(a[0]).dt.month()


@_register("day")
def _day(a):
    _need(a, 1, 1, "Day")
    return _c(a[0]).dt.day()
