import pytest

from pyflow_engine import Runner, WorkflowDoc
from pyflow_engine.document import ancestors_including, topo_sort


def _linear():
    return WorkflowDoc.model_validate(
        {
            "nodes": [{"id": "a", "type": "x"}, {"id": "b", "type": "x"}, {"id": "c", "type": "x"}],
            "edges": [
                {"id": "e1", "source": {"node": "a", "anchor": "out"}, "target": {"node": "b", "anchor": "in"}},
                {"id": "e2", "source": {"node": "b", "anchor": "out"}, "target": {"node": "c", "anchor": "in"}},
            ],
        }
    )


def test_topo_sort_orders_ancestors_first():
    assert topo_sort(_linear()) == ["a", "b", "c"]


def test_cycle_detection_raises():
    doc = WorkflowDoc.model_validate(
        {
            "nodes": [{"id": "a", "type": "x"}, {"id": "b", "type": "x"}],
            "edges": [
                {"id": "e1", "source": {"node": "a", "anchor": "out"}, "target": {"node": "b", "anchor": "in"}},
                {"id": "e2", "source": {"node": "b", "anchor": "out"}, "target": {"node": "a", "anchor": "in"}},
            ],
        }
    )
    with pytest.raises(ValueError):
        topo_sort(doc)


def test_ancestors_including():
    assert ancestors_including(_linear(), "c") == {"a", "b", "c"}
    assert ancestors_including(_linear(), "a") == {"a"}


def test_runner_surfaces_node_error(registry, tmp_path, customers):
    src = tmp_path / "c.csv"
    customers.write_csv(src)
    doc = WorkflowDoc.model_validate(
        {
            "nodes": [
                {"id": "i", "type": "input.file", "config": {"path": str(src), "format": "csv", "has_header": True, "delimiter": ","}},
                {"id": "f", "type": "prep.filter", "config": {"expression": "[nonexistent] == 1"}},
            ],
            "edges": [{"id": "e", "source": {"node": "i", "anchor": "out"}, "target": {"node": "f", "anchor": "in"}}],
        }
    )
    events = []
    Runner(registry=registry, emit=events.append).run(doc)
    types = [e["type"] for e in events]
    assert "node_error" in types
    assert "run_error" in types
