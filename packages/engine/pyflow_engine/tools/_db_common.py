"""Shared database connection config and URI building for the DB input/output tools.

``ConnectionFields`` is a Pydantic base model the tool configs inherit, so connection
handling (dialects, ports, ${ENV_VAR} secrets, ConnectorX/SQLAlchemy URIs) lives in
one place.
"""
from __future__ import annotations

import os
import re
from enum import Enum
from urllib.parse import quote

import polars as pl
from pydantic import BaseModel, Field as PField

from ..types import pyflow_to_polars


class Dialect(str, Enum):
    sqlserver = "sqlserver"
    redshift = "redshift"
    oracle = "oracle"
    postgresql = "postgresql"
    mysql = "mysql"
    sqlite = "sqlite"
    custom = "custom"


class DbEngine(str, Enum):
    auto = "auto"
    connectorx = "connectorx"
    sqlalchemy = "sqlalchemy"


class DbColumn(BaseModel):
    name: str = ""
    type: str = "string"


_CX_SCHEME = {
    "sqlserver": "mssql",
    "redshift": "redshift",
    "oracle": "oracle",
    "postgresql": "postgresql",
    "mysql": "mysql",
    "sqlite": "sqlite",
}
_SA_DRIVER = {
    "sqlserver": "mssql+pymssql",
    "redshift": "postgresql+psycopg",
    "oracle": "oracle+oracledb",
    "postgresql": "postgresql+psycopg",
    "mysql": "mysql+pymysql",
    "sqlite": "sqlite",
}
_DEFAULT_PORT = {
    "sqlserver": 1433,
    "redshift": 5439,
    "oracle": 1521,
    "postgresql": 5432,
    "mysql": 3306,
}

_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def interp(value: str) -> str:
    """Replace ${ENV_VAR} references with environment values."""
    if not value:
        return value
    return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)


def clean_query(query: str) -> str:
    return query.strip().rstrip(";").strip()


def safe_pl_dtype(pyflow_type: str):
    try:
        return pyflow_to_polars(pyflow_type)
    except ValueError:
        return pl.String


class ConnectionFields(BaseModel):
    dialect: Dialect = PField(default=Dialect.sqlserver, title="Database")
    host: str = PField(default="", title="Host")
    port: int = PField(default=0, title="Port", description="0 = the dialect's default port")
    database: str = PField(default="", title="Database / service / file")
    user: str = PField(default="", title="User")
    password: str = PField(
        default="",
        title="Password",
        description="Tip: use ${ENV_VAR} to reference an environment variable.",
        json_schema_extra={"x-editor": "secret"},
    )
    uri: str = PField(
        default="",
        title="Custom connection URI",
        description="Overrides the fields above. Required for the 'custom' dialect.",
    )


def connectorx_uri(cfg: ConnectionFields) -> str:
    if cfg.uri.strip():
        return interp(cfg.uri)
    d = cfg.dialect.value
    if d == "sqlite":
        return f"sqlite://{interp(cfg.database)}"
    if d == "custom":
        raise ValueError("The 'custom' dialect requires a connection URI")
    scheme = _CX_SCHEME[d]
    port = cfg.port or _DEFAULT_PORT.get(d, 0)
    user = quote(interp(cfg.user), safe="")
    pw = quote(interp(cfg.password), safe="")
    return f"{scheme}://{user}:{pw}@{interp(cfg.host)}:{port}/{interp(cfg.database)}"


def sqlalchemy_uri(cfg: ConnectionFields) -> str:
    if cfg.uri.strip():
        return interp(cfg.uri)
    d = cfg.dialect.value
    if d == "sqlite":
        return f"sqlite:///{interp(cfg.database)}"
    if d == "custom":
        raise ValueError("The 'custom' dialect requires a connection URI")
    driver = _SA_DRIVER[d]
    port = cfg.port or _DEFAULT_PORT.get(d, 0)
    user = quote(interp(cfg.user), safe="")
    pw = quote(interp(cfg.password), safe="")
    return f"{driver}://{user}:{pw}@{interp(cfg.host)}:{port}/{interp(cfg.database)}"
