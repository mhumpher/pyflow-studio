"""Lexer, AST, and recursive-descent parser for the Pyflow formula language.

Grammar (low -> high precedence):
    expr        := if_expr | or_expr
    if_expr     := IF or_expr THEN expr (ELSEIF or_expr THEN expr)* (ELSE expr)? ENDIF
    or_expr     := and_expr (OR and_expr)*
    and_expr    := not_expr (AND not_expr)*
    not_expr    := NOT not_expr | comparison
    comparison  := add ((== | != | < | > | <= | >=) add)?
    add         := mul ((+ | -) mul)*
    mul         := unary ((* | / | %) unary)*
    unary       := (- | +) unary | primary
    primary     := NUMBER | STRING | TRUE | FALSE | NULL | [Field]
                 | IDENT '(' args ')' | '(' expr ')'
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class FormulaError(ValueError):
    """Raised for lexing, parsing, or compilation errors in a formula."""


# --- AST nodes --------------------------------------------------------------

@dataclass
class Num:
    value: int | float


@dataclass
class Str:
    value: str


@dataclass
class Bool:
    value: bool


@dataclass
class Null:
    pass


@dataclass
class FieldRef:
    name: str


@dataclass
class Unary:
    op: str
    operand: Any


@dataclass
class BinOp:
    op: str
    left: Any
    right: Any


@dataclass
class BoolOp:
    op: str  # "AND" | "OR"
    left: Any
    right: Any


@dataclass
class Not:
    operand: Any


@dataclass
class Compare:
    op: str
    left: Any
    right: Any


@dataclass
class IfExpr:
    branches: list[tuple[Any, Any]] = field(default_factory=list)  # (cond, result)
    orelse: Any | None = None


@dataclass
class Call:
    name: str
    args: list[Any] = field(default_factory=list)


# --- lexer ------------------------------------------------------------------

KEYWORDS = {"IF", "THEN", "ELSEIF", "ELSE", "ENDIF", "AND", "OR", "NOT", "TRUE", "FALSE", "NULL"}
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}


def tokenize(s: str) -> list[tuple[str, Any]]:
    tokens: list[tuple[str, Any]] = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch in " \t\r\n":
            i += 1
            continue
        if ch == "[":
            j = s.find("]", i + 1)
            if j == -1:
                raise FormulaError("Unterminated field reference '['")
            tokens.append(("FIELD", s[i + 1 : j].strip()))
            i = j + 1
            continue
        if ch in "\"'":
            quote = ch
            j = i + 1
            buf: list[str] = []
            while j < n and s[j] != quote:
                if s[j] == "\\" and j + 1 < n:
                    buf.append(_ESCAPES.get(s[j + 1], s[j + 1]))
                    j += 2
                    continue
                buf.append(s[j])
                j += 1
            if j >= n:
                raise FormulaError("Unterminated string literal")
            tokens.append(("STRING", "".join(buf)))
            i = j + 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and s[i + 1].isdigit()):
            j = i
            while j < n and (s[j].isdigit() or s[j] == "."):
                j += 1
            raw = s[i:j]
            tokens.append(("NUMBER", float(raw) if "." in raw else int(raw)))
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (s[j].isalnum() or s[j] == "_"):
                j += 1
            word = s[i:j]
            up = word.upper()
            tokens.append(("KW", up) if up in KEYWORDS else ("IDENT", word))
            i = j
            continue
        two = s[i : i + 2]
        if two in ("==", "!=", "<=", ">=", "<>"):
            tokens.append(("OP", "!=" if two == "<>" else two))
            i += 2
            continue
        if ch in "+-*/%(),<>=":
            tokens.append(("OP", "==" if ch == "=" else ch))
            i += 1
            continue
        raise FormulaError(f"Unexpected character {ch!r}")
    tokens.append(("EOF", None))
    return tokens


# --- parser -----------------------------------------------------------------

_COMPARE_OPS = {"==", "!=", "<", ">", "<=", ">="}


class Parser:
    def __init__(self, tokens: list[tuple[str, Any]]) -> None:
        self.toks = tokens
        self.pos = 0

    def peek(self) -> tuple[str, Any]:
        return self.toks[self.pos]

    def advance(self) -> tuple[str, Any]:
        tok = self.toks[self.pos]
        self.pos += 1
        return tok

    def at(self, kind: str, value: Any = None) -> bool:
        k, v = self.peek()
        return k == kind and (value is None or v == value)

    def expect(self, kind: str, value: Any = None) -> tuple[str, Any]:
        if not self.at(kind, value):
            k, v = self.peek()
            got = v if v is not None else k
            raise FormulaError(f"Expected {value or kind}, got {got!r}")
        return self.advance()

    def parse(self) -> Any:
        node = self.parse_expr()
        if not self.at("EOF"):
            k, v = self.peek()
            raise FormulaError(f"Unexpected token {v if v is not None else k!r}")
        return node

    def parse_expr(self) -> Any:
        if self.at("KW", "IF"):
            return self.parse_if()
        return self.parse_or()

    def parse_if(self) -> Any:
        self.expect("KW", "IF")
        branches = []
        cond = self.parse_or()
        self.expect("KW", "THEN")
        branches.append((cond, self.parse_expr()))
        while self.at("KW", "ELSEIF"):
            self.advance()
            c = self.parse_or()
            self.expect("KW", "THEN")
            branches.append((c, self.parse_expr()))
        orelse = None
        if self.at("KW", "ELSE"):
            self.advance()
            orelse = self.parse_expr()
        self.expect("KW", "ENDIF")
        return IfExpr(branches, orelse)

    def parse_or(self) -> Any:
        left = self.parse_and()
        while self.at("KW", "OR"):
            self.advance()
            left = BoolOp("OR", left, self.parse_and())
        return left

    def parse_and(self) -> Any:
        left = self.parse_not()
        while self.at("KW", "AND"):
            self.advance()
            left = BoolOp("AND", left, self.parse_not())
        return left

    def parse_not(self) -> Any:
        if self.at("KW", "NOT"):
            self.advance()
            return Not(self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self) -> Any:
        left = self.parse_add()
        k, v = self.peek()
        if k == "OP" and v in _COMPARE_OPS:
            self.advance()
            return Compare(v, left, self.parse_add())
        return left

    def parse_add(self) -> Any:
        left = self.parse_mul()
        while self.peek() in (("OP", "+"), ("OP", "-")):
            op = self.advance()[1]
            left = BinOp(op, left, self.parse_mul())
        return left

    def parse_mul(self) -> Any:
        left = self.parse_unary()
        while self.peek()[0] == "OP" and self.peek()[1] in ("*", "/", "%"):
            op = self.advance()[1]
            left = BinOp(op, left, self.parse_unary())
        return left

    def parse_unary(self) -> Any:
        if self.peek()[0] == "OP" and self.peek()[1] in ("-", "+"):
            op = self.advance()[1]
            return Unary(op, self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> Any:
        k, v = self.peek()
        if k == "NUMBER":
            self.advance()
            return Num(v)
        if k == "STRING":
            self.advance()
            return Str(v)
        if k == "FIELD":
            self.advance()
            return FieldRef(v)
        if k == "KW" and v in ("TRUE", "FALSE"):
            self.advance()
            return Bool(v == "TRUE")
        if k == "KW" and v == "NULL":
            self.advance()
            return Null()
        if k == "OP" and v == "(":
            self.advance()
            node = self.parse_expr()
            self.expect("OP", ")")
            return node
        if k == "IDENT":
            name = self.advance()[1]
            if self.at("OP", "("):
                self.advance()
                args = []
                if not self.at("OP", ")"):
                    args.append(self.parse_expr())
                    while self.at("OP", ","):
                        self.advance()
                        args.append(self.parse_expr())
                self.expect("OP", ")")
                return Call(name, args)
            raise FormulaError(f"Unknown name {name!r}; use [FieldName] to reference a column")
        raise FormulaError(f"Unexpected token {v if v is not None else k!r}")


def parse(source: str) -> Any:
    return Parser(tokenize(source)).parse()
