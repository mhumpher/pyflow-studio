"""Tool registry and default registration (built-ins + entry-point plugins)."""
from __future__ import annotations

from typing import Iterable

from .tool import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, type[Tool]] = {}

    def register(self, tool_cls: type[Tool]) -> None:
        self._tools[tool_cls.type] = tool_cls

    def register_all(self, tool_classes: Iterable[type[Tool]]) -> None:
        for tc in tool_classes:
            self.register(tc)

    def get(self, type_: str) -> type[Tool]:
        if type_ not in self._tools:
            raise KeyError(f"Unknown tool type: {type_!r}")
        return self._tools[type_]

    def all(self) -> list[type[Tool]]:
        return list(self._tools.values())

    def descriptors(self) -> list[dict]:
        return [t.descriptor() for t in self._tools.values()]


def build_default_registry() -> ToolRegistry:
    """Register Phase 0 built-in tools plus any installed plugins."""
    from .tools.browse import BrowseTool
    from .tools.crosstab import CrossTabTool
    from .tools.datetime_tool import DateTimeTool
    from .tools.filter import FilterTool
    from .tools.formula import FormulaTool
    from .tools.json_parse import JsonParseTool
    from .tools.input_database import DatabaseInputTool
    from .tools.input_file import InputFileTool
    from .tools.join import JoinTool
    from .tools.output_database import DatabaseOutputTool
    from .tools.output_file import OutputFileTool
    from .tools.python_tool import PythonTool
    from .tools.regex import RegexTool
    from .tools.sample import SampleTool
    from .tools.select import SelectTool
    from .tools.sort import SortTool
    from .tools.summarize import SummarizeTool
    from .tools.text_to_columns import TextToColumnsTool
    from .tools.transpose import TransposeTool
    from .tools.union import UnionTool
    from .tools.unique import UniqueTool
    from .tools.unpivot import UnpivotTool

    reg = ToolRegistry()
    reg.register_all(
        [
            InputFileTool,
            DatabaseInputTool,
            SelectTool,
            FilterTool,
            FormulaTool,
            SortTool,
            SampleTool,
            UniqueTool,
            SummarizeTool,
            CrossTabTool,
            UnpivotTool,
            TransposeTool,
            TextToColumnsTool,
            RegexTool,
            DateTimeTool,
            JsonParseTool,
            JoinTool,
            UnionTool,
            PythonTool,
            BrowseTool,
            OutputFileTool,
            DatabaseOutputTool,
        ]
    )

    # Plugin discovery via entry points (group "pyflow.tools"). Wired now; used later.
    try:
        from importlib.metadata import entry_points

        for ep in entry_points(group="pyflow.tools"):
            try:
                reg.register(ep.load())
            except Exception:  # pragma: no cover - a bad plugin must not break startup
                pass
    except Exception:  # pragma: no cover
        pass

    return reg
