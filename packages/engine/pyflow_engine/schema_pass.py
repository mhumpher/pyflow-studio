"""Design-time schema inference.

Computes each node's input and output schemas *without running data*, by building
the lazy plan for every node and resolving its schema. Powers field pickers,
downstream field lists, and validation.

For tools whose output columns are data-dependent (Cross Tab, Transpose), build()
can only expose the columns known ahead of time. To close that gap, this pass also
consults the run cache: if a node's content hash matches a cached run, its real
post-run output schema is reused (and threaded downstream), so a Cross Tab's pivoted
columns become pickable in downstream tools after one run. Because the hash folds in
config + upstream, an edited node never reuses a stale cached schema.

Degrades gracefully: a node whose source is unreadable or whose config is incomplete
simply has no schema; the rest of the graph is still inferred.
"""
from __future__ import annotations

from typing import Any

import polars as pl

from .cache import RunCache, compute_hashes
from .context import RunContext
from .document import WorkflowDoc, topo_sort
from .execution import gather_inputs, incoming_edges
from .frame import Frame
from .registry import ToolRegistry, build_default_registry
from .types import pyflow_to_polars


def _noop_emit(_event: dict[str, Any]) -> None:
    pass


def _anchor_schema(value: Any) -> dict[str, Any] | None:
    """Schema dict for a resolved input (a Frame, or the first of a multi list)."""
    frame = value[0] if isinstance(value, list) else value
    if frame is None:
        return None
    try:
        return frame.schema().to_dict()
    except Exception:
        return None


def _empty_frame_from_fields(fields: list[dict[str, Any]]) -> pl.LazyFrame:
    """Build a zero-row lazy frame matching a cached schema, to thread downstream."""
    data: dict[str, pl.Series] = {}
    for f in fields or []:
        try:
            dtype = pyflow_to_polars(f["type"])
        except ValueError:
            dtype = pl.String
        data[f["name"]] = pl.Series(f["name"], [], dtype=dtype)
    return pl.DataFrame(data).lazy()


def infer_schemas(
    doc: WorkflowDoc,
    registry: ToolRegistry | None = None,
    cache: RunCache | None = None,
) -> dict[str, dict[str, Any]]:
    """Return {node_id: {"inputs": {anchor: schema|None}, "outputs": {...}, "error": str|None}}."""
    registry = registry or build_default_registry()
    try:
        order = topo_sort(doc)
    except ValueError as exc:
        return {n.id: {"inputs": {}, "outputs": {}, "error": str(exc)} for n in doc.nodes}

    nodes = doc.node_by_id()
    incoming = incoming_edges(doc)
    hashes = compute_hashes(doc, registry) if cache is not None else {}
    frames: dict[str, dict[str, Frame]] = {}
    result: dict[str, dict[str, Any]] = {}

    for node_id in order:
        node = nodes[node_id]
        entry: dict[str, Any] = {"inputs": {}, "outputs": {}, "error": None}

        try:
            tool_cls = registry.get(node.type)
        except KeyError:
            entry["error"] = f"Unknown tool type: {node.type}"
            result[node_id] = entry
            continue

        inputs = gather_inputs(node_id, tool_cls, incoming, frames)
        for anchor, value in inputs.items():
            entry["inputs"][anchor] = _anchor_schema(value)

        if node.disabled:
            result[node_id] = entry
            continue

        # Prefer a cached real schema (makes data-dependent columns known after a run).
        node_hash = hashes.get(node_id) if cache is not None else None
        cached = cache.get(node_hash) if (cache is not None and node_hash) else None
        if cached:
            cached_outputs: dict[str, Frame] = {}
            for anchor, meta in cached.items():
                entry["outputs"][anchor] = meta["schema"]
                cached_outputs[anchor] = Frame(_empty_frame_from_fields(meta["schema"]["fields"]))
            frames[node_id] = cached_outputs
            result[node_id] = entry
            continue

        try:
            cfg = tool_cls.Config.model_validate(node.config)
            ctx = RunContext(node_id, _noop_emit)
            outputs = tool_cls().build(inputs, cfg, ctx)
            frames[node_id] = outputs
            for anchor, frame in outputs.items():
                try:
                    entry["outputs"][anchor] = frame.schema().to_dict()
                except Exception:
                    entry["outputs"][anchor] = None
        except Exception as exc:
            msg = str(exc).strip()
            entry["error"] = msg.splitlines()[0] if msg else exc.__class__.__name__

        result[node_id] = entry

    return result
