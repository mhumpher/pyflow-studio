import polars as pl
import pytest

from pyflow_sdk.testing import run_tool


def test_input_file_csv(registry, tmp_path, customers):
    p = tmp_path / "c.csv"
    customers.write_csv(p)
    out = run_tool(
        registry.get("input.file"),
        {"path": str(p), "format": "csv", "has_header": True, "delimiter": ","},
        {},
    )
    assert out["out"].height == 8
    assert out["out"].columns == customers.columns


def test_input_file_parquet(registry, tmp_path, customers):
    p = tmp_path / "c.parquet"
    customers.write_parquet(p)
    out = run_tool(registry.get("input.file"), {"path": str(p), "format": "parquet"}, {})
    assert out["out"].height == 8


def test_output_file_csv_roundtrip(registry, tmp_path, customers):
    p = tmp_path / "out.csv"
    run_tool(
        registry.get("output.file"),
        {"path": str(p), "format": "csv", "delimiter": ",", "write_header": True},
        {"in": customers},
    )
    assert pl.read_csv(p).height == 8


def test_output_file_parquet(registry, tmp_path, customers):
    p = tmp_path / "out.parquet"
    run_tool(registry.get("output.file"), {"path": str(p), "format": "parquet"}, {"in": customers})
    assert pl.read_parquet(p).height == 8


def test_database_roundtrip_sqlite(registry, tmp_path, customers):
    pytest.importorskip("sqlalchemy")
    pytest.importorskip("pandas")
    db = (tmp_path / "t.db").as_posix()

    run_tool(
        registry.get("output.database"),
        {"dialect": "sqlite", "database": db, "table": "customers", "mode": "overwrite"},
        {"in": customers},
    )
    out = run_tool(
        registry.get("input.database"),
        {
            "dialect": "sqlite",
            "database": db,
            "query": "SELECT * FROM customers WHERE status = 'active'",
            "engine": "sqlalchemy",
        },
        {},
    )
    assert out["out"].height == 5
