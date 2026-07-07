"""Workflow document model (.pyflow) plus graph utilities (topo sort, ancestors)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field as PField


class Position(BaseModel):
    x: float = 0.0
    y: float = 0.0


class NodeModel(BaseModel):
    id: str
    type: str
    version: str = "1.0"
    position: Position = PField(default_factory=Position)
    title: str | None = None
    config: dict[str, Any] = PField(default_factory=dict)
    disabled: bool = False


class AnchorRef(BaseModel):
    node: str
    anchor: str


class EdgeModel(BaseModel):
    id: str
    source: AnchorRef
    target: AnchorRef


class WorkflowDoc(BaseModel):
    pyflow_version: str = "1.0"
    id: str = "wf"
    name: str = "Untitled"
    meta: dict[str, Any] = PField(default_factory=dict)
    nodes: list[NodeModel] = PField(default_factory=list)
    edges: list[EdgeModel] = PField(default_factory=list)
    annotations: list[dict] = PField(default_factory=list)
    containers: list[dict] = PField(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "WorkflowDoc":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def node_by_id(self) -> dict[str, NodeModel]:
        return {n.id: n for n in self.nodes}


def topo_sort(doc: WorkflowDoc) -> list[str]:
    """Kahn's algorithm. Raises ValueError on a cycle."""
    ids = [n.id for n in doc.nodes]
    indegree = {i: 0 for i in ids}
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for e in doc.edges:
        if e.source.node in adj and e.target.node in indegree:
            adj[e.source.node].append(e.target.node)
            indegree[e.target.node] += 1

    queue = [i for i in ids if indegree[i] == 0]
    order: list[str] = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in adj[n]:
            indegree[m] -= 1
            if indegree[m] == 0:
                queue.append(m)

    if len(order) != len(ids):
        raise ValueError("Workflow contains a cycle")
    return order


def ancestors_including(doc: WorkflowDoc, node_id: str) -> set[str]:
    """All upstream nodes of node_id, plus node_id itself."""
    parents: dict[str, list[str]] = {n.id: [] for n in doc.nodes}
    for e in doc.edges:
        if e.target.node in parents:
            parents[e.target.node].append(e.source.node)

    seen: set[str] = set()
    stack = [node_id]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(parents.get(cur, []))
    return seen
