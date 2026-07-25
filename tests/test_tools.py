import polars as pl
import pytest
from pyflow_sdk.testing import run_tool


def T(registry, type_):
    return registry.get(type_)


# --- Preparation ----------------------------------------------------------

def test_filter_splits_true_false(registry, customers):
    out = run_tool(T(registry, "prep.filter"), {"expression": '[status] == "active"'}, {"in": customers})
    assert out["true"].height == 5
    assert out["false"].height == 3


def test_select_choose_rename_drop(registry, customers):
    out = run_tool(
        T(registry, "prep.select"),
        {"fields": [
            {"source": "name", "rename": "customer", "type": "", "include": True},
            {"source": "spend", "rename": "", "type": "", "include": True},
            {"source": "region", "rename": "", "type": "", "include": False},
        ]},
        {"in": customers},
    )
    assert out["out"].columns == ["customer", "spend"]


def test_formula_adds_column(registry, customers):
    out = run_tool(
        T(registry, "prep.formula"),
        {"formulas": [{"output": "rev", "expression": "[spend] * 2", "type": ""}]},
        {"in": customers},
    )
    assert out["out"]["rev"].to_list()[0] == customers["spend"][0] * 2


def test_sort_descending(registry, customers):
    out = run_tool(T(registry, "prep.sort"), {"keys": [{"field": "spend", "direction": "descending"}]}, {"in": customers})
    assert out["out"]["spend"].to_list()[0] == 9800.75


def test_sample_first_n(registry, customers):
    out = run_tool(T(registry, "prep.sample"), {"mode": "first", "n": 3, "seed": 0}, {"in": customers})
    assert out["out"]["id"].to_list() == [1, 2, 3]


def test_sample_random_is_seed_deterministic(registry, customers):
    cfg = {"mode": "random_n", "n": 3, "seed": 42}
    a = run_tool(T(registry, "prep.sample"), cfg, {"in": customers})["out"]
    b = run_tool(T(registry, "prep.sample"), cfg, {"in": customers})["out"]
    assert a["id"].to_list() == b["id"].to_list()


def test_unique_splits(registry, customers):
    out = run_tool(T(registry, "prep.unique"), {"fields": ["region"]}, {"in": customers})
    assert out["unique"].height == 2
    assert out["duplicates"].height == 6


# --- Join / Union ---------------------------------------------------------

def test_join_left_join_right(registry, customers, regions):
    out = run_tool(
        T(registry, "join.standard"),
        {"join_keys": [{"left": "region", "right": "region"}]},
        {"left": customers, "right": regions},
    )
    assert out["join"].height == 8
    assert out["left_only"].height == 0
    assert out["right_only"].height == 1  # North has no customers


def test_union_by_name_fills_missing(registry, customers, regions):
    out = run_tool(T(registry, "join.union"), {"mode": "by_name"}, {"in": [customers, regions]})
    assert out["out"].height == 11
    assert "manager" in out["out"].columns  # diagonal union fills with null


# --- Transform ------------------------------------------------------------

def test_summarize_group_sum(registry, customers):
    out = run_tool(
        T(registry, "transform.summarize"),
        {"group_by": ["region"], "aggregations": [{"field": "spend", "func": "sum", "output": "total"}]},
        {"in": customers},
    )
    totals = dict(zip(out["out"]["region"].to_list(), out["out"]["total"].to_list()))
    assert totals["West"] == 1200.5 + 5400.0 + 50.0 + 4200.0


def test_crosstab_pivot(registry, customers):
    out = run_tool(
        T(registry, "transform.crosstab"),
        {"group_by": ["region"], "header_field": "status", "value_field": "spend", "aggregation": "sum"},
        {"in": customers},
    )
    assert set(out["out"].columns) == {"region", "active", "inactive"}


def test_unpivot_wide_to_long(registry):
    wide = pl.DataFrame({"region": ["W", "E"], "active": [10.0, 20.0], "inactive": [1.0, 2.0]})
    out = run_tool(
        T(registry, "transform.unpivot"),
        {"id_fields": ["region"], "value_fields": ["active", "inactive"], "name_column": "status", "value_column": "v"},
        {"in": wide},
    )
    assert out["out"].height == 4
    assert set(out["out"].columns) == {"region", "status", "v"}


def test_transpose(registry, regions):
    out = run_tool(
        T(registry, "transform.transpose"),
        {"header_column": "region", "include_names": True, "names_to": "column"},
        {"in": regions},
    )
    assert out["out"].columns[0] == "column"
    assert {"West", "East", "North"}.issubset(set(out["out"].columns))


# --- Parse ----------------------------------------------------------------

def test_text_to_columns(registry):
    d = pl.DataFrame({"name": ["Ada Lovelace", "Alan Turing"]})
    out = run_tool(
        T(registry, "parse.text_to_columns"),
        {"field": "name", "delimiter": " ", "mode": "columns", "num_columns": 2, "prefix": "n", "keep_original": False},
        {"in": d},
    )
    assert out["out"]["n1"].to_list() == ["Ada", "Alan"]
    assert "name" not in out["out"].columns


def test_text_to_columns_rows(registry):
    d = pl.DataFrame({"csv": ["a,b,c"]})
    out = run_tool(T(registry, "parse.text_to_columns"), {"field": "csv", "delimiter": ",", "mode": "rows"}, {"in": d})
    assert out["out"].height == 3


def test_regex_parse_named_groups(registry):
    d = pl.DataFrame({"phone": ["555-123-4567"]})
    out = run_tool(
        T(registry, "parse.regex"),
        {"field": "phone", "pattern": r"(?<area>\d{3})-(?<mid>\d{3})-(?<last>\d{4})", "method": "parse"},
        {"in": d},
    )
    assert out["out"]["area"].to_list() == ["555"]
    assert out["out"]["last"].to_list() == ["4567"]


def test_regex_match_flag(registry):
    d = pl.DataFrame({"phone": ["555-1", "444-2"]})
    out = run_tool(
        T(registry, "parse.regex"),
        {"field": "phone", "pattern": r"^555", "method": "match", "output_field": "is555"},
        {"in": d},
    )
    assert out["out"]["is555"].to_list() == [True, False]


def test_datetime_parse(registry):
    d = pl.DataFrame({"d": ["2020-01-15", "2019-06-30"]})
    out = run_tool(
        T(registry, "parse.datetime"),
        {"field": "d", "direction": "parse", "format": "%Y-%m-%d", "output_type": "date", "output_field": "parsed"},
        {"in": d},
    )
    assert out["out"]["parsed"].dtype == pl.Date


def test_json_parse(registry):
    d = pl.DataFrame({"payload": ['{"user":"alice","score":10}', '{"user":"bob","score":20}']})
    out = run_tool(T(registry, "parse.json"), {"field": "payload", "keep_original": False}, {"in": d})
    assert out["out"]["user"].to_list() == ["alice", "bob"]
    assert out["out"]["score"].to_list() == [10, 20]


# --- Developer (Python) ---------------------------------------------------

def test_python_multi_in_multi_out(registry, customers, regions):
    code = "output1 = input1.filter(pl.col('status') == 'active')\noutput2 = input2.head(1)"
    out = run_tool(T(registry, "dev.python"), {"code": code}, {"in1": customers, "in2": regions})
    assert out["out1"].height == 5
    assert out["out2"].height == 1


def test_python_bad_output_type_raises(registry, customers):
    with pytest.raises(ValueError):
        run_tool(T(registry, "dev.python"), {"code": "output1 = [1, 2, 3]"}, {"in1": customers})


def test_python_runtime_error_raises(registry, customers):
    with pytest.raises(ValueError):
        run_tool(T(registry, "dev.python"), {"code": "output1 = input1.select(['nope'])"}, {"in1": customers})
