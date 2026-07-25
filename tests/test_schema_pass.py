import pytest
from pyflow_engine import Runner, WorkflowDoc
from pyflow_engine.cache import RunCache
from pyflow_engine.schema_pass import infer_schemas


@pytest.fixture
def src(tmp_path, customers):
    p = tmp_path / "c.csv"
    customers.write_csv(p)
    return str(p)


def _out_cols(schemas, node):
    d = schemas[node]["outputs"].get("out")
    return [f["name"] for f in d["fields"]] if d else None


def _input_node(src):
    return {"id": "i", "type": "input.file", "config": {"path": src, "format": "csv", "has_header": True, "delimiter": ","}}


def test_formula_output_schema_known_at_design_time(registry, src):
    doc = WorkflowDoc.model_validate(
        {
            "nodes": [
                _input_node(src),
                {"id": "f", "type": "prep.formula", "config": {"formulas": [{"output": "rev", "expression": "[spend] * 2", "type": ""}]}},
            ],
            "edges": [{"id": "e", "source": {"node": "i", "anchor": "out"}, "target": {"node": "f", "anchor": "in"}}],
        }
    )
    cols = _out_cols(infer_schemas(doc, registry), "f")
    assert "rev" in cols and "spend" in cols


def test_crosstab_schema_data_dependent_then_cache_aware(registry, tmp_path, src):
    doc = WorkflowDoc.model_validate(
        {
            "nodes": [
                _input_node(src),
                {"id": "x", "type": "transform.crosstab", "config": {"group_by": ["region"], "header_field": "status", "value_field": "spend", "aggregation": "sum"}},
            ],
            "edges": [{"id": "e", "source": {"node": "i", "anchor": "out"}, "target": {"node": "x", "anchor": "in"}}],
        }
    )
    # Without a prior run, only the known index column is exposed.
    assert _out_cols(infer_schemas(doc, registry), "x") == ["region"]

    # After a run, the cache-aware pass knows the real pivoted columns.
    cache = RunCache(str(tmp_path / "cache"))
    Runner(registry=registry, cache=cache).run(doc)
    cols = _out_cols(infer_schemas(doc, registry, cache=cache), "x")
    assert set(cols) == {"region", "active", "inactive"}


def test_unknown_tool_reports_error(registry):
    doc = WorkflowDoc.model_validate({"nodes": [{"id": "n", "type": "does.not.exist", "config": {}}], "edges": []})
    assert infer_schemas(doc, registry)["n"]["error"] is not None
