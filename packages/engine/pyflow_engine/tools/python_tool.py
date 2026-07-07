"""Python — run custom Python code over multiple inputs, producing multiple outputs.

The code receives ``input1..input3`` (Polars DataFrames, or None if unconnected) and
assigns ``output1..output3``. ``pl`` (Polars) is preloaded. Output columns depend on
the code, so this is a data-dependent tool (build/run split): downstream field pickers
learn the real output columns after one run, via the cache-aware schema pass.

SECURITY: this executes arbitrary Python in-process — appropriate for a local,
single-user tool (you are running your own code), but it means a ``.pyflow`` file can
contain executable code. Treat shared workflows as you would any script, and do not run
untrusted ones. Subprocess/sandbox isolation is the prerequisite for running this tool in
a shared/server context (see docs/09-non-functional.md).
"""
from __future__ import annotations

import traceback

import polars as pl
from pydantic import BaseModel, Field as PField

from ..frame import Frame
from ..tool import InputAnchor, OutputAnchor, Tool

_N = 3

_DEFAULT_CODE = """# Inputs:  input1, input2, input3  (Polars DataFrames, or None if not connected)
# Outputs: assign output1, output2, output3  (Polars DataFrames)
# 'pl' is Polars.

output1 = input1
"""


def _format_error(exc: Exception) -> str:
    if isinstance(exc, SyntaxError):
        return f"SyntaxError: {exc.msg} (line {exc.lineno})"
    lineno = None
    for frame, ln in traceback.walk_tb(exc.__traceback__):
        if frame.f_code.co_filename == "<python_tool>":
            lineno = ln
    loc = f" (line {lineno})" if lineno else ""
    return f"{type(exc).__name__}: {exc}{loc}"


def _to_polars(value: object) -> pl.DataFrame | None:
    if value is None:
        return None
    if isinstance(value, pl.DataFrame):
        return value
    if isinstance(value, pl.LazyFrame):
        return value.collect()
    try:
        import pandas as pd

        if isinstance(value, pd.DataFrame):
            return pl.from_pandas(value)
    except ModuleNotFoundError:
        pass
    raise ValueError(
        f"Outputs must be Polars (or pandas) DataFrames; got {type(value).__name__}"
    )


class PythonConfig(BaseModel):
    code: str = PField(
        default=_DEFAULT_CODE, title="Python code", json_schema_extra={"x-editor": "python"}
    )


class PythonTool(Tool):
    type = "dev.python"
    name = "Python"
    category = "Developer"
    icon = "code"
    Config = PythonConfig
    inputs = [InputAnchor(f"in{i}", label=str(i)) for i in range(1, _N + 1)]
    outputs = [OutputAnchor(f"out{i}", label=str(i)) for i in range(1, _N + 1)]

    def build(self, inputs, cfg: PythonConfig, ctx) -> dict[str, Frame]:
        # Output columns depend on the code; expose empty outputs at design time.
        return {f"out{i}": Frame(pl.DataFrame().lazy()) for i in range(1, _N + 1)}

    def run(self, inputs, cfg: PythonConfig, ctx) -> dict[str, Frame]:
        namespace: dict[str, object] = {"pl": pl}
        for i in range(1, _N + 1):
            frame = inputs.get(f"in{i}")
            namespace[f"input{i}"] = frame.lazy.collect() if frame is not None else None
            namespace[f"output{i}"] = None

        try:
            compiled = compile(cfg.code, "<python_tool>", "exec")
            exec(compiled, namespace)  # noqa: S102 - intentional user-code execution
        except Exception as exc:
            raise ValueError(_format_error(exc)) from exc

        outputs: dict[str, Frame] = {}
        for i in range(1, _N + 1):
            df = _to_polars(namespace.get(f"output{i}"))
            outputs[f"out{i}"] = Frame((df if df is not None else pl.DataFrame()).lazy())
        return outputs
