import time

import pytest

from pyflow_engine import Runner, WorkflowDoc
from pyflow_engine.cache import RunCache


def _doc(src, expr='[status] == "active"'):
    return WorkflowDoc.model_validate(
        {
            "nodes": [
                {"id": "i", "type": "input.file", "config": {"path": src, "format": "csv", "has_header": True, "delimiter": ","}},
                {"id": "f", "type": "prep.filter", "config": {"expression": expr}},
                {"id": "s", "type": "transform.summarize", "config": {"group_by": ["region"], "aggregations": [{"field": "spend", "func": "sum", "output": "total"}]}},
            ],
            "edges": [
                {"id": "e1", "source": {"node": "i", "anchor": "out"}, "target": {"node": "f", "anchor": "in"}},
                {"id": "e2", "source": {"node": "f", "anchor": "true"}, "target": {"node": "s", "anchor": "in"}},
            ],
        }
    )


def _run(registry, cache, doc) -> dict[str, bool]:
    """Return {node_id: was_cached}."""
    status: dict[str, bool] = {}

    def emit(e):
        if e["type"] == "node_completed":
            status[e["node"]] = e["cached"]

    Runner(registry=registry, emit=emit, cache=cache).run(doc)
    return status


@pytest.fixture
def src(tmp_path, customers):
    p = tmp_path / "c.csv"
    customers.write_csv(p)
    return str(p)


def test_cold_run_computes_everything(registry, tmp_path, src):
    cache = RunCache(str(tmp_path / "cache"))
    assert _run(registry, cache, _doc(src)) == {"i": False, "f": False, "s": False}


def test_rerun_reuses_all(registry, tmp_path, src):
    cache = RunCache(str(tmp_path / "cache"))
    _run(registry, cache, _doc(src))
    assert _run(registry, cache, _doc(src)) == {"i": True, "f": True, "s": True}


def test_edit_invalidates_node_and_descendants(registry, tmp_path, src):
    cache = RunCache(str(tmp_path / "cache"))
    _run(registry, cache, _doc(src))
    st = _run(registry, cache, _doc(src, expr='[status] != "active"'))
    assert st["i"] is True  # unchanged upstream reused
    assert st["f"] is False  # edited node recomputed
    assert st["s"] is False  # descendant recomputed


def test_source_file_change_invalidates(registry, tmp_path, src, customers):
    cache = RunCache(str(tmp_path / "cache"))
    _run(registry, cache, _doc(src))
    time.sleep(0.01)
    customers.head(4).write_csv(src)  # change the source file
    assert _run(registry, cache, _doc(src))["i"] is False


def test_sink_always_runs(registry, tmp_path, src):
    cache = RunCache(str(tmp_path / "cache"))
    doc = WorkflowDoc.model_validate(
        {
            "nodes": [
                {"id": "i", "type": "input.file", "config": {"path": src, "format": "csv", "has_header": True, "delimiter": ","}},
                {"id": "o", "type": "output.file", "config": {"path": (tmp_path / "o.csv").as_posix(), "format": "csv", "delimiter": ",", "write_header": True}},
            ],
            "edges": [{"id": "e", "source": {"node": "i", "anchor": "out"}, "target": {"node": "o", "anchor": "in"}}],
        }
    )
    _run(registry, cache, doc)
    st = _run(registry, cache, doc)
    assert st["i"] is True  # input reused
    assert st["o"] is False  # side-effecting sink always runs
