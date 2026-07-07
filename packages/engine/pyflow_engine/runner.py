"""Runner — schedules and executes a workflow DAG, with optional incremental caching.

Without a cache, nodes execute lazily (outputs stay lazy; only samples/counts
materialize). With a RunCache, each cacheable node's output is materialized to an
Arrow file keyed by its content hash; on the next run a node whose hash is unchanged
reuses that file instead of recomputing — so editing one node only recomputes it and
its descendants. Side-effecting sinks (cacheable=False) always execute.
"""
from __future__ import annotations

import time
from typing import Any, Callable

import polars as pl

from .cache import RunCache, compute_hashes, materialize
from .context import RunContext
from .document import WorkflowDoc, ancestors_including, topo_sort
from .execution import gather_inputs, incoming_edges
from .frame import Frame
from .registry import ToolRegistry, build_default_registry
from .serialize import df_to_grid
from .types import Schema

EventSink = Callable[[dict[str, Any]], None]


class Runner:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        emit: EventSink | None = None,
        sample_rows: int = 1000,
        cache: RunCache | None = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        self.emit = emit or (lambda e: None)
        self.sample_rows = sample_rows
        self.cache = cache
        self.results: dict[str, dict[str, Frame]] = {}
        self.samples: dict[str, dict[str, dict[str, Any]]] = {}

    def run(
        self,
        doc: WorkflowDoc,
        to: str | None = None,
        cancelled: Callable[[], bool] | None = None,
        use_cache: bool = True,
    ) -> "Runner":
        order = topo_sort(doc)
        if to is not None:
            wanted = ancestors_including(doc, to)
            order = [n for n in order if n in wanted]

        nodes = doc.node_by_id()
        incoming = incoming_edges(doc)
        hashes = compute_hashes(doc, self.registry) if self.cache is not None else {}

        self.emit({"type": "run_started", "nodes": len(order)})
        cached_n = 0
        computed_n = 0
        try:
            for node_id in order:
                node = nodes[node_id]
                if node.disabled:
                    continue
                if cancelled and cancelled():
                    self.emit({"type": "run_cancelled"})
                    return self
                if self._try_cache_hit(node_id, node, hashes, use_cache):
                    cached_n += 1
                else:
                    self._run_node(node_id, node, hashes, incoming, cancelled)
                    computed_n += 1
        except Exception as exc:
            self.emit({"type": "run_error", "code": exc.__class__.__name__, "detail": str(exc)})
            return self

        self.emit(
            {
                "type": "run_completed",
                "nodes": len(order),
                "cached": cached_n,
                "computed": computed_n,
            }
        )
        return self

    def _try_cache_hit(
        self, node_id: str, node: Any, hashes: dict[str, str], use_cache: bool
    ) -> bool:
        if not (use_cache and self.cache is not None):
            return False
        tool_cls = self.registry.get(node.type)
        if not getattr(tool_cls, "cacheable", True):
            return False
        node_hash = hashes.get(node_id)
        if not node_hash:
            return False
        entry = self.cache.get(node_hash)
        if not entry or not self.cache.all_files_exist(entry):
            return False

        self.emit({"type": "node_started", "node": node_id})
        outputs: dict[str, Frame] = {}
        self.samples[node_id] = {}
        anchor_rows: dict[str, int] = {}
        headline_rows = 0
        headline_cols = 0
        for i, (anchor, meta) in enumerate(entry.items()):
            outputs[anchor] = Frame(pl.scan_ipc(meta["path"]))
            self.samples[node_id][anchor] = {
                "schema": meta["schema"],
                "count": meta["count"],
                "grid": meta["grid"],
            }
            anchor_rows[anchor] = meta["count"]
            if i == 0:
                headline_rows = meta["count"]
                headline_cols = len(meta["schema"]["fields"])
        self.results[node_id] = outputs
        self.emit(
            {
                "type": "node_completed",
                "node": node_id,
                "rows": headline_rows,
                "cols": headline_cols,
                "anchor_rows": anchor_rows,
                "ms": 0.0,
                "cached": True,
            }
        )
        return True

    def _run_node(
        self,
        node_id: str,
        node: Any,
        hashes: dict[str, str],
        incoming: dict[str, dict[str, list[tuple[str, str]]]],
        cancelled: Callable[[], bool] | None,
    ) -> None:
        self.emit({"type": "node_started", "node": node_id})
        t0 = time.perf_counter()
        try:
            tool_cls = self.registry.get(node.type)
            cfg = tool_cls.Config.model_validate(node.config)
            inputs = gather_inputs(node_id, tool_cls, incoming, self.results)
            ctx = RunContext(node_id, self.emit, cancelled)
            outputs = tool_cls().run(inputs, cfg, ctx)

            cacheable = getattr(tool_cls, "cacheable", True)
            node_hash = hashes.get(node_id)
            do_cache = self.cache is not None and node_hash is not None and cacheable

            self.results[node_id] = {}
            self.samples[node_id] = {}
            anchor_rows: dict[str, int] = {}
            headline_rows = 0
            headline_cols = 0
            entry: dict[str, dict[str, Any]] = {}
            for i, (anchor, frame) in enumerate(outputs.items()):
                if do_cache:
                    path = self.cache.path_for(node_hash, anchor)
                    materialize(frame.lazy, path)
                    lf = pl.scan_ipc(path)
                else:
                    path = None
                    lf = frame.lazy

                schema = Schema.from_polars(lf.collect_schema())
                count = int(lf.select(pl.len()).collect().item())
                grid = df_to_grid(lf.head(self.sample_rows).collect())

                self.results[node_id][anchor] = Frame(lf)
                self.samples[node_id][anchor] = {
                    "schema": schema.to_dict(),
                    "count": count,
                    "grid": grid,
                }
                anchor_rows[anchor] = count
                if path is not None:
                    entry[anchor] = {
                        "path": path,
                        "schema": schema.to_dict(),
                        "count": count,
                        "grid": grid,
                    }
                if i == 0:
                    headline_rows = count
                    headline_cols = len(schema.fields)

            if do_cache and entry:
                self.cache.put(node_hash, entry)
        except Exception as exc:
            self.emit(
                {
                    "type": "node_error",
                    "node": node_id,
                    "code": exc.__class__.__name__,
                    "detail": str(exc),
                }
            )
            raise

        ms = round((time.perf_counter() - t0) * 1000, 1)
        self.emit(
            {
                "type": "node_completed",
                "node": node_id,
                "rows": headline_rows,
                "cols": headline_cols,
                "anchor_rows": anchor_rows,
                "ms": ms,
                "cached": False,
            }
        )

    def preview(self, node_id: str, anchor: str | None = None) -> dict[str, Any] | None:
        node_samples = self.samples.get(node_id)
        if not node_samples:
            return None
        if anchor is None:
            anchor = next(iter(node_samples))
        return node_samples.get(anchor)
