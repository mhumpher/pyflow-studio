"""Browse — a terminal preview point. Passes its input through so it is previewable
and can be chained during exploration.
"""
from __future__ import annotations

from ..frame import Frame
from ..tool import EmptyConfig, InputAnchor, OutputAnchor, Tool


class BrowseTool(Tool):
    type = "output.browse"
    name = "Browse"
    category = "Input/Output"
    icon = "eye"
    Config = EmptyConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg, ctx) -> dict[str, Frame]:
        return {"out": inputs["in"]}
