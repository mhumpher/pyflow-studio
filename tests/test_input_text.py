"""Text Input — manually entered rows become a typed source Frame."""
from datetime import date

import polars as pl
import pytest
from pyflow_engine.tools.input_text import TextInputTool
from pyflow_sdk.testing import run_tool


def _cfg(columns, rows):
    return {"table": {"columns": columns, "rows": rows}}


def test_types_are_cast_from_strings(registry):
    out = run_tool(
        registry.get("input.text"),
        _cfg(
            [{"name": "id", "type": "int64"}, {"name": "name", "type": "string"},
             {"name": "score", "type": "float64"}, {"name": "vip", "type": "bool"}],
            [["1", "Acme", "9.5", "true"], ["2", "Globex", "3.0", "no"]],
        ),
        {},
    )["out"]
    assert out.columns == ["id", "name", "score", "vip"]
    assert out.schema["id"] == pl.Int64
    assert out.schema["score"] == pl.Float64
    assert out.schema["vip"] == pl.Boolean
    assert out.to_dicts() == [
        {"id": 1, "name": "Acme", "score": 9.5, "vip": True},
        {"id": 2, "name": "Globex", "score": 3.0, "vip": False},
    ]


def test_blank_cells_become_null(registry):
    out = run_tool(
        registry.get("input.text"),
        _cfg(
            [{"name": "a", "type": "int64"}, {"name": "b", "type": "string"}],
            [["", ""], ["5", "x"]],
        ),
        {},
    )["out"]
    assert out["a"].to_list() == [None, 5]
    assert out["b"].to_list() == [None, "x"]


def test_dates_parse(registry):
    out = run_tool(
        registry.get("input.text"),
        _cfg([{"name": "d", "type": "date"}], [["2026-01-15"], ["not-a-date"]]),
        {},
    )["out"]
    assert out.schema["d"] == pl.Date
    assert out["d"][0] == date(2026, 1, 15)
    assert out["d"][1] is None  # unparseable -> null (non-strict)


def test_empty_rows_yield_typed_empty_frame(registry):
    out = run_tool(
        registry.get("input.text"),
        _cfg([{"name": "a", "type": "int64"}, {"name": "b", "type": "string"}], []),
        {},
    )["out"]
    assert out.height == 0
    assert out.columns == ["a", "b"]
    assert out.schema["a"] == pl.Int64


def test_ragged_row_is_padded(registry):
    out = run_tool(
        registry.get("input.text"),
        _cfg([{"name": "a", "type": "string"}, {"name": "b", "type": "string"}], [["x"]]),
        {},
    )["out"]
    assert out.to_dicts() == [{"a": "x", "b": None}]


@pytest.mark.parametrize(
    "columns, message",
    [
        ([], "at least one column"),
        ([{"name": "", "type": "string"}], "needs a name"),
        ([{"name": "a", "type": "string"}, {"name": "a", "type": "int64"}], "unique"),
    ],
)
def test_invalid_columns_raise(registry, columns, message):
    with pytest.raises(Exception, match=message):
        run_tool(registry.get("input.text"), _cfg(columns, []), {})


def test_default_config_builds(registry):
    # Dropping the tool with no edits (its default grid) must build cleanly.
    from pyflow_engine.tools.input_text import TextInputConfig

    cfg = TextInputConfig()
    out = TextInputTool().build({}, cfg, None)["out"]
    df = out.lazy.collect()
    assert df.columns == ["Column1", "Column2"]
    assert df.height == 3
