import polars as pl
import pytest

from pyflow_engine.formula import FormulaError, compile_expr, validate


@pytest.fixture
def df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "spend": [100.0, 2000.0],
            "name": [" Acme ", "globex"],
            "status": ["active", "inactive"],
        }
    )


def _eval(df: pl.DataFrame, src: str):
    return df.select(compile_expr(src).alias("r"))["r"].to_list()


def test_arithmetic(df):
    assert _eval(df, "[spend] * 2") == [200.0, 4000.0]


def test_if(df):
    assert _eval(df, 'IF [spend] > 1000 THEN "big" ELSE "small" ENDIF') == ["small", "big"]


def test_if_elseif(df):
    src = 'IF [status] == "active" THEN "A" ELSEIF [spend] > 1000 THEN "B" ELSE "C" ENDIF'
    assert _eval(df, src) == ["A", "B"]


def test_string_functions(df):
    assert _eval(df, "Trim(Upper([name]))") == ["ACME", "GLOBEX"]
    assert _eval(df, "Substring(Trim([name]), 0, 2)") == ["Ac", "gl"]


def test_round_and_concat(df):
    assert _eval(df, "Round([spend] * 1.1, 2)") == [110.0, 2200.0]
    assert _eval(df, 'Concat([status], "-", [name])')[0] == "active- Acme "


def test_coalesce():
    d = pl.DataFrame({"a": [None, "x"]})
    assert d.select(compile_expr('Coalesce([a], "?")').alias("r"))["r"].to_list() == ["?", "x"]


def test_comparison_and_logic(df):
    assert _eval(df, "[spend] >= 2000") == [False, True]
    assert _eval(df, '[status] == "active" AND [spend] < 1000') == [True, False]


def test_validate_ok_returns_type():
    assert validate("[spend] * 2", {"spend": "float64"}) == {"ok": True, "type": "float64"}


@pytest.mark.parametrize(
    "src,schema",
    [
        ("[nope] + 1", {"spend": "float64"}),  # unknown column
        ("IF [x] THEN", {"x": "int64"}),  # syntax error
        ("Round()", {"x": "float64"}),  # arity error
        ("", {"x": "float64"}),  # empty
    ],
)
def test_validate_errors(src, schema):
    result = validate(src, schema)
    assert result["ok"] is False
    assert "error" in result


def test_parse_error_is_formula_error():
    with pytest.raises(FormulaError):
        compile_expr("1 +")
