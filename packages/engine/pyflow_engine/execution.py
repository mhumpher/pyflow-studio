"""Shared edge/input resolution used by both the runner and the schema pass.

Supports multiple edges into a single anchor: a ``multi`` input anchor receives a
list of frames (fan-in, e.g. Union); a normal anchor receives a single frame.
"""
from __future__ import annotations

from typing import Any

from .document import WorkflowDoc
from .frame import Frame

# target_node -> anchor -> [(source_node, source_anchor), ...] (in document edge order)
Incoming = dict[str, dict[str, list[tuple[str, str]]]]


def incoming_edges(doc: WorkflowDoc) -> Incoming:
    incoming: Incoming = {}
    for e in doc.edges:
        incoming.setdefault(e.target.node, {}).setdefault(e.target.anchor, []).append(
            (e.source.node, e.source.anchor)
        )
    return incoming


def gather_inputs(
    node_id: str,
    tool_cls: Any,
    incoming: Incoming,
    frames: dict[str, dict[str, Frame]],
) -> dict[str, Any]:
    """Resolve a node's inputs from already-computed upstream frames.

    Returns ``{anchor: Frame}`` for single anchors and ``{anchor: [Frame, ...]}``
    for anchors declared ``multi``. Unresolved single anchors are omitted.
    """
    multi = {a.id: a.multi for a in tool_cls.inputs}
    inputs: dict[str, Any] = {}
    for anchor, sources in incoming.get(node_id, {}).items():
        resolved = [
            frames[src][src_anchor]
            for src, src_anchor in sources
            if src in frames and src_anchor in frames[src]
        ]
        if multi.get(anchor, False):
            inputs[anchor] = resolved
        elif resolved:
            inputs[anchor] = resolved[0]
    return inputs
