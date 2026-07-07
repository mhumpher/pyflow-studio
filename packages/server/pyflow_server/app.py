"""FastAPI application: tool catalog, run-over-WebSocket, and previews.

Phase 0 is single-session and stateless beyond the last run's cached samples.
The frontend is the source of truth for the canvas and sends the full workflow
document with each run request.
"""
from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from pyflow_engine import Runner, WorkflowDoc, build_default_registry
from pyflow_engine.cache import RunCache
from pyflow_engine.formula import FUNCTION_NAMES, validate as validate_formula
from pyflow_engine.schema_pass import infer_schemas

app = FastAPI(title="Pyflow Studio", version="0.0.1")

# Dev CORS: the Vite dev server (5173) calls this API (8710) directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REGISTRY = build_default_registry()
# wf_id -> last Runner (holds cached samples for previews)
RESULTS: dict[str, Runner] = {}
# wf_id -> session run cache (persists materialized node outputs across runs)
CACHES: dict[str, RunCache] = {}


def _get_cache(wf_id: str) -> RunCache:
    if wf_id not in CACHES:
        safe = re.sub(r"\W+", "_", wf_id)
        root = os.path.join(tempfile.gettempdir(), "pyflow_cache", safe)
        CACHES[wf_id] = RunCache(root)
    return CACHES[wf_id]


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "ok", "tools": len(REGISTRY.all())}


@app.get("/tools")
def tools() -> list[dict[str, Any]]:
    return REGISTRY.descriptors()


@app.get("/formula/functions")
def formula_functions() -> list[str]:
    return FUNCTION_NAMES


class SchemaRequest(BaseModel):
    workflow: dict[str, Any]
    wf_id: str = "current"


@app.post("/workflows/schema")
def workflow_schema(req: SchemaRequest) -> dict[str, Any]:
    """Design-time schema inference for every node (powers field pickers).

    Consults the session cache so a data-dependent tool's real post-run columns
    (e.g. a Cross Tab's pivoted columns) propagate to downstream field pickers.
    """
    try:
        doc = WorkflowDoc.model_validate(req.workflow)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid workflow: {exc}")
    return infer_schemas(doc, REGISTRY, cache=_get_cache(req.wf_id))


class FormulaValidateRequest(BaseModel):
    model_config = {"populate_by_name": True}

    expression: str
    fields: dict[str, str] = Field(default_factory=dict, alias="schema")


@app.post("/formula/validate")
def formula_validate(req: FormulaValidateRequest) -> dict[str, Any]:
    return validate_formula(req.expression, req.fields)


class InspectRequest(BaseModel):
    config: dict[str, Any]


@app.post("/connections/inspect")
def connections_inspect(req: InspectRequest) -> dict[str, Any]:
    """Test a database connection and fetch its result-set columns (no rows)."""
    from pyflow_engine.tools.input_database import DatabaseInputConfig, probe_schema

    try:
        cfg = DatabaseInputConfig.model_validate(req.config)
    except Exception as exc:
        return {"ok": False, "error": f"Invalid connection config: {exc}"}
    return probe_schema(cfg)


@app.get("/workflows/{wf_id}/nodes/{node_id}/preview")
def preview(wf_id: str, node_id: str, anchor: str | None = None) -> dict[str, Any]:
    runner = RESULTS.get(wf_id)
    if runner is None:
        raise HTTPException(status_code=404, detail="No run results for this workflow yet")
    pv = runner.preview(node_id, anchor)
    if pv is None:
        raise HTTPException(status_code=404, detail="No preview available for this node/anchor")
    return pv


@app.websocket("/workflows/{wf_id}/session")
async def session(ws: WebSocket, wf_id: str) -> None:
    await ws.accept()
    loop = asyncio.get_running_loop()
    cancel = {"stop": False}
    try:
        while True:
            msg = await ws.receive_json()
            op = msg.get("op")
            if op == "run":
                cancel["stop"] = False
                try:
                    doc = WorkflowDoc.model_validate(msg["workflow"])
                except Exception as exc:
                    await ws.send_json(
                        {"type": "run_error", "code": "InvalidWorkflow", "detail": str(exc)}
                    )
                    continue

                queue: asyncio.Queue = asyncio.Queue()

                def emit(event: dict[str, Any]) -> None:
                    loop.call_soon_threadsafe(queue.put_nowait, event)

                async def drain() -> None:
                    while True:
                        event = await queue.get()
                        await ws.send_json(event)
                        if event["type"] in ("run_completed", "run_error", "run_cancelled"):
                            break

                cache = _get_cache(wf_id)
                if msg.get("clear_cache"):
                    cache.clear()
                runner = Runner(registry=REGISTRY, emit=emit, cache=cache)
                drain_task = asyncio.create_task(drain())
                await run_in_threadpool(runner.run, doc, msg.get("to"), lambda: cancel["stop"])
                RESULTS[wf_id] = runner
                await drain_task
            elif op == "clear_cache":
                _get_cache(wf_id).clear()
                await ws.send_json({"type": "cache_cleared"})
            elif op == "stop":
                cancel["stop"] = True
            elif op == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        return


# Serve the built frontend if present (production). Mounted last so API routes win.
_DIST = Path(__file__).resolve().parents[3] / "apps" / "studio" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="studio")
else:

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": "Pyflow Studio API is running.",
            "hint": "Build the frontend (apps/studio) or run the Vite dev server.",
            "tools": "/tools",
            "health": "/healthz",
        }
