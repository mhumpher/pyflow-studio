"""Content-addressed run cache for incremental re-runs.

Each node gets a hash over its tool type/version, normalized config, an optional
source signature (e.g. a file's mtime), and the hashes of its upstream inputs — so
changing any ancestor invalidates every node downstream. A cacheable node whose hash
is unchanged reuses its materialized Arrow output instead of recomputing.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from typing import Any

import polars as pl

from .document import WorkflowDoc, topo_sort
from .execution import incoming_edges

# Bump to invalidate all caches when execution semantics change.
_ENGINE_CACHE_VERSION = "1"


def materialize(lf: pl.LazyFrame, path: str) -> None:
    """Write a lazy frame to an Arrow IPC file (streaming when possible)."""
    try:
        lf.sink_ipc(path)
    except Exception:
        lf.collect().write_ipc(path)


def compute_hashes(doc: WorkflowDoc, registry: Any) -> dict[str, str]:
    """Content hash per node id, computed in topological order."""
    order = topo_sort(doc)
    incoming = incoming_edges(doc)
    nodes = doc.node_by_id()
    hashes: dict[str, str] = {}

    for nid in order:
        node = nodes[nid]

        # input signature: per anchor (sorted), the ordered upstream (hash, anchor) pairs
        input_sig = []
        for anchor in sorted(incoming.get(nid, {})):
            sources = [[hashes.get(src), src_anchor] for src, src_anchor in incoming[nid][anchor]]
            input_sig.append([anchor, sources])

        source_key = None
        try:
            tool_cls = registry.get(node.type)
            cfg = tool_cls.Config.model_validate(node.config)
            source_key = tool_cls().cache_key(cfg)
        except Exception:
            source_key = None

        payload = json.dumps(
            {
                "type": node.type,
                "version": node.version,
                "disabled": node.disabled,
                "config": node.config,
                "source_key": source_key,
                "inputs": input_sig,
                "engine": _ENGINE_CACHE_VERSION,
            },
            sort_keys=True,
            default=str,
        )
        hashes[nid] = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    return hashes


class RunCache:
    """Session-scoped cache of node outputs (Arrow files + preview metadata)."""

    def __init__(self, root: str) -> None:
        self.root = root
        os.makedirs(root, exist_ok=True)
        # node_hash -> {anchor -> {"path", "schema", "count", "grid"}}
        self.entries: dict[str, dict[str, dict[str, Any]]] = {}

    def get(self, node_hash: str) -> dict[str, dict[str, Any]] | None:
        return self.entries.get(node_hash)

    def put(self, node_hash: str, entry: dict[str, dict[str, Any]]) -> None:
        self.entries[node_hash] = entry

    def path_for(self, node_hash: str, anchor: str) -> str:
        safe = "".join(c if c.isalnum() else "_" for c in anchor)
        return os.path.join(self.root, f"{node_hash}__{safe}.arrow")

    def all_files_exist(self, entry: dict[str, dict[str, Any]]) -> bool:
        return all(os.path.exists(meta["path"]) for meta in entry.values())

    def clear(self) -> None:
        self.entries.clear()
        for f in glob.glob(os.path.join(self.root, "*.arrow")):
            try:
                os.remove(f)
            except OSError:
                pass
