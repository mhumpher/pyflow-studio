"""Disabling a tool skips it and everything downstream (runner + schema pass)."""
from pyflow_engine import Runner, WorkflowDoc
from pyflow_engine.document import disabled_closure
from pyflow_engine.schema_pass import infer_schemas


def _doc(nodes, edges):
    return WorkflowDoc.model_validate({"nodes": nodes, "edges": edges})


def _edge(eid, src, tgt, src_anchor="out", tgt_anchor="in"):
    return {
        "id": eid,
        "source": {"node": src, "anchor": src_anchor},
        "target": {"node": tgt, "anchor": tgt_anchor},
    }


def test_disabled_closure_includes_descendants():
    doc = _doc(
        [
            {"id": "a", "type": "x"},
            {"id": "b", "type": "x", "disabled": True},
            {"id": "c", "type": "x"},
        ],
        [_edge("e1", "a", "b"), _edge("e2", "b", "c")],
    )
    assert disabled_closure(doc) == {"b", "c"}


def test_disabled_closure_empty_when_none_disabled():
    doc = _doc(
        [{"id": "a", "type": "x"}, {"id": "b", "type": "x"}],
        [_edge("e1", "a", "b")],
    )
    assert disabled_closure(doc) == set()


def test_disabled_leaf_skips_only_itself():
    doc = _doc(
        [{"id": "a", "type": "x"}, {"id": "b", "type": "x", "disabled": True}],
        [_edge("e1", "a", "b")],
    )
    assert disabled_closure(doc) == {"b"}


def test_disabled_closure_taints_shared_child():
    # a fans out to b (disabled) and c; both feed d. Disabling b switches off d too,
    # since one of d's inputs is now missing — but c stays live.
    doc = _doc(
        [
            {"id": "a", "type": "x"},
            {"id": "b", "type": "x", "disabled": True},
            {"id": "c", "type": "x"},
            {"id": "d", "type": "x"},
        ],
        [
            _edge("e1", "a", "b"),
            _edge("e2", "a", "c"),
            _edge("e3", "b", "d", tgt_anchor="left"),
            _edge("e4", "c", "d", tgt_anchor="right"),
        ],
    )
    assert disabled_closure(doc) == {"b", "d"}


def test_runner_skips_disabled_and_downstream(registry, tmp_path, customers):
    src = tmp_path / "c.csv"
    customers.write_csv(src)
    doc = _doc(
        [
            {
                "id": "i",
                "type": "input.file",
                "config": {"path": str(src), "format": "csv", "has_header": True, "delimiter": ","},
            },
            {
                "id": "f",
                "type": "prep.filter",
                "config": {"expression": '[status] == "active"'},
                "disabled": True,
            },
            {"id": "b", "type": "output.browse", "config": {}},
        ],
        [_edge("e1", "i", "f"), _edge("e2", "f", "b", src_anchor="true")],
    )
    events: list = []
    Runner(registry=registry, emit=events.append).run(doc)
    types = [e["type"] for e in events]

    assert "node_error" not in types
    assert "run_error" not in types
    assert {e["node"] for e in events if e["type"] == "node_skipped"} == {"f", "b"}
    assert any(e["type"] == "node_completed" and e["node"] == "i" for e in events)
    completed = next(e for e in events if e["type"] == "run_completed")
    assert completed["skipped"] == 2
    assert completed["computed"] == 1


def test_schema_pass_skips_downstream_of_disabled(registry, tmp_path, customers):
    src = tmp_path / "c.csv"
    customers.write_csv(src)
    doc = _doc(
        [
            {
                "id": "i",
                "type": "input.file",
                "config": {"path": str(src), "format": "csv", "has_header": True, "delimiter": ","},
            },
            {
                "id": "f",
                "type": "prep.filter",
                "config": {"expression": '[status] == "active"'},
                "disabled": True,
            },
            {"id": "s", "type": "prep.select"},
        ],
        [_edge("e1", "i", "f"), _edge("e2", "f", "s", src_anchor="true")],
    )
    result = infer_schemas(doc, registry)

    # The live input still resolves its schema...
    assert result["i"]["error"] is None
    assert result["i"]["outputs"]
    # ...but the disabled node and its descendant produce nothing, and neither errors.
    assert result["f"]["outputs"] == {} and result["f"]["error"] is None
    assert result["s"]["outputs"] == {} and result["s"]["error"] is None
