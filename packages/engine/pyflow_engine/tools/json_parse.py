"""JSON Parse — decode a JSON string field and flatten it into columns.

The output columns come from the JSON structure, so they are data-dependent: build()
passes the input schema through, and run() decodes + unnests. After one run the parsed
columns propagate to downstream field pickers via the cache-aware schema pass.
"""
from __future__ import annotations

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool


class JsonParseConfig(BaseModel):
    field: str = PField(default="", title="JSON field", json_schema_extra={"x-editor": "field"})
    keep_original: bool = PField(default=False, title="Keep original field")


class JsonParseTool(Tool):
    type = "parse.json"
    name = "JSON Parse"
    category = "Parse"
    icon = "braces"
    Config = JsonParseConfig
    inputs = [InputAnchor("in")]
    outputs = [OutputAnchor("out")]

    def build(self, inputs, cfg: JsonParseConfig, ctx) -> dict[str, Frame]:
        # Data-dependent columns: pass the input schema through at design time.
        return {"out": Frame(inputs["in"].lazy)}

    def run(self, inputs, cfg: JsonParseConfig, ctx) -> dict[str, Frame]:
        if not cfg.field:
            raise ValueError("Select a JSON field to parse")
        df = inputs["in"].lazy.collect()
        # The Series API infers the JSON schema from the data (the Expr API needs an
        # explicit dtype); run() has the materialized frame, so this is the right path.
        decoded_series = df[cfg.field].cast(pl.String).str.json_decode()
        out = df.with_columns(decoded_series.alias("__pf_json"))
        if isinstance(out.schema["__pf_json"], pl.Struct):
            out = out.unnest("__pf_json")
        else:
            out = out.rename({"__pf_json": f"{cfg.field}_parsed"})
        if not cfg.keep_original and cfg.field in out.columns:
            out = out.drop(cfg.field)
        return {"out": Frame(out.lazy())}
