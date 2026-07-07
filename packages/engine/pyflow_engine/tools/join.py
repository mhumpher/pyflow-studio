"""Join — combine two inputs on key fields, Alteryx-style (Left-only / Join / Right-only)."""
from __future__ import annotations

from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class JoinKey(BaseModel):
    left: str = PField(default="", title="Left field", json_schema_extra={"x-editor": "field:left"})
    right: str = PField(
        default="", title="Right field", json_schema_extra={"x-editor": "field:right"}
    )


class JoinConfig(BaseModel):
    join_keys: list[JoinKey] = PField(default_factory=list, title="Join on")


class JoinTool(Tool):
    type = "join.standard"
    name = "Join"
    category = "Join"
    icon = "git-merge"
    Config = JoinConfig
    inputs = [InputAnchor("left", label="L"), InputAnchor("right", label="R")]
    outputs = [
        OutputAnchor("left_only", label="Left only"),
        OutputAnchor("join", label="Join"),
        OutputAnchor("right_only", label="Right only"),
    ]

    def build(self, inputs, cfg: JoinConfig, ctx) -> dict[str, Frame]:
        if "left" not in inputs or "right" not in inputs:
            raise ValueError("Join needs both Left and Right inputs connected")

        keys = [k for k in cfg.join_keys if k.left and k.right]
        if not keys:
            raise ValueError("Join requires at least one complete key pair")

        left = inputs["left"].lazy
        right = inputs["right"].lazy
        left_keys = [k.left for k in keys]
        right_keys = [k.right for k in keys]

        joined = left.join(right, left_on=left_keys, right_on=right_keys, how="inner")
        left_only = left.join(right, left_on=left_keys, right_on=right_keys, how="anti")
        right_only = right.join(left, left_on=right_keys, right_on=left_keys, how="anti")

        return {
            "left_only": Frame(left_only),
            "join": Frame(joined),
            "right_only": Frame(right_only),
        }
