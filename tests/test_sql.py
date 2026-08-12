"""SQL tool — DuckDB SQL over one or more connected inputs."""
import pytest

pytest.importorskip("duckdb")

from pyflow_sdk.testing import run_tool  # noqa: E402


def _sql(registry, query, inputs, **kw):
    return run_tool(registry.get("transform.sql"), {"query": query}, inputs, **kw)["out"]


def test_filter_and_select(registry, customers):
    out = _sql(
        registry,
        "SELECT name, spend FROM input1 WHERE status = 'active' ORDER BY spend DESC",
        {"in1": customers},
    )
    assert out.columns == ["name", "spend"]
    assert out.height == 5  # active customers
    assert out["spend"][0] == 9800.75  # Stark, highest active spend


def test_aggregate(registry, customers):
    out = _sql(
        registry,
        "SELECT region, sum(spend) AS total FROM input1 GROUP BY region ORDER BY region",
        {"in1": customers},
    )
    assert out.columns == ["region", "total"]
    assert set(out["region"].to_list()) == {"East", "West"}


def test_join_two_inputs(registry, customers, regions):
    out = _sql(
        registry,
        "SELECT c.name, r.manager FROM input1 c JOIN input2 r ON c.region = r.region",
        {"in1": customers, "in2": regions},
    )
    assert set(out.columns) == {"name", "manager"}
    assert out.height == 8  # every customer's region (West/East) exists in regions


def test_build_is_schema_only(registry, customers):
    # build() (schema pass) returns the right columns with zero rows.
    out = _sql(
        registry,
        "SELECT name, spend * 2 AS double_spend FROM input1",
        {"in1": customers},
        build_only=True,
    )
    assert out.columns == ["name", "double_spend"]
    assert out.height == 0


def test_requires_input(registry):
    with pytest.raises(Exception, match="at least one input"):
        _sql(registry, "SELECT 1 AS x", {})


def test_empty_query_errors(registry, customers):
    with pytest.raises(Exception, match="SQL query"):
        _sql(registry, "   ", {"in1": customers})


def test_invalid_query_errors(registry, customers):
    with pytest.raises(Exception):
        _sql(registry, "SELECT nope FROM input1", {"in1": customers})
