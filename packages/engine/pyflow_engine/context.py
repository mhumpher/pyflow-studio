"""RunContext — the controlled capability surface passed to a tool's build().

Tools use it to emit messages/progress and to check cooperative cancellation.
Events are plain dicts (JSON-ready) consumed by the server -> WebSocket -> UI.
"""
from __future__ import annotations

from typing import Any, Callable

EventSink = Callable[[dict[str, Any]], None]


class RunContext:
    def __init__(
        self,
        node_id: str,
        emit: EventSink,
        is_cancelled: Callable[[], bool] | None = None,
        backend: str = "polars",
    ) -> None:
        self.node_id = node_id
        self.backend = backend
        self._emit = emit
        self._is_cancelled = is_cancelled or (lambda: False)

    def message(self, level: str, text: str, field: str | None = None) -> None:
        self._emit(
            {
                "type": "node_message",
                "node": self.node_id,
                "level": level,
                "text": text,
                "field": field,
            }
        )

    def progress(self, rows: int | None = None, pct: float | None = None) -> None:
        self._emit(
            {"type": "node_progress", "node": self.node_id, "rows": rows, "pct": pct}
        )

    def is_cancelled(self) -> bool:
        return self._is_cancelled()
