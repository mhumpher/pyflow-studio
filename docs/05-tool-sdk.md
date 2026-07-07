# 05 — Tool SDK

Extensibility is a first-class feature. A developer should be able to write a useful custom tool in an
afternoon and ship it as a pip package. This document specifies the tool-authoring contract.

---

## 1. Anatomy of a tool

Every tool declares four things:

1. **Identity & metadata** — `type` id, display name, category, icon, version, docs.
2. **Anchors** — its input and output ports (with contracts).
3. **Config schema** — a Pydantic model; the UI panel is generated from it automatically.
4. **Behavior** — `infer_schema()` (design-time) and `execute()` (run-time).

```python
from pyflow_sdk import Tool, InputAnchor, OutputAnchor, config
from pyflow_sdk.expr import Expr
from pyflow_sdk.types import Schema
from pyflow_sdk.frame import Frame
import polars as pl


class FilterConfig(config.Model):
    """Config models render themselves as the tool's panel."""
    expression: Expr = config.field(
        title="Keep rows where",
        help="Rows matching this expression go to the True output.",
        editor="formula",           # hint the UI to use the formula editor
    )


class FilterTool(Tool):
    type = "prep.filter"
    name = "Filter"
    category = "Preparation"
    version = "1.0"
    icon = "filter"
    Config = FilterConfig

    inputs = [InputAnchor("in", contract="any_table")]
    outputs = [
        OutputAnchor("true",  help="Rows matching the expression"),
        OutputAnchor("false", help="Rows not matching"),
    ]

    def infer_schema(self, inputs: dict[str, Schema], cfg: FilterConfig) -> dict[str, Schema]:
        # Filtering doesn't change the schema; both outputs match the input.
        return {"true": inputs["in"], "false": inputs["in"]}

    def execute(self, inputs: dict[str, Frame], cfg: FilterConfig, ctx) -> dict[str, Frame]:
        pred = cfg.expression.compile(ctx.backend)     # → pl.Expr or SQL
        src = inputs["in"]
        return {
            "true":  src.filter(pred),
            "false": src.filter(~pred),
        }
```

That's a complete, streaming, backend-neutral tool.

## 2. The config → UI contract

- Config is a **Pydantic v2 model**. Its JSON Schema is sent to the frontend, which renders a panel
  automatically (text, number, dropdown, multiselect, checkbox, field-picker, formula editor, file path).
- `config.field(...)` adds UI hints (`title`, `help`, `editor`, `depends_on`, `group`, `order`).
- **Field pickers** bind to the input schema: `columns: FieldSelection` renders a checkbox list of the
  actual upstream fields (available because of the design-time schema pass).
- **Conditional fields** (`depends_on`) show/hide based on other values (e.g. show "delimiter" only when
  format == csv).
- Authors can optionally supply a **custom React panel** for advanced tools, but the default generated
  panel should cover the large majority.

### Common config field types
| SDK field | Renders as | Notes |
| --- | --- | --- |
| `str`, `int`, `float`, `bool` | text / number / checkbox | Basic inputs |
| `Enum` / `Literal[...]` | dropdown | Fixed choices |
| `Expr` | formula editor | Autocompletes fields + functions |
| `FieldSelection` | field picker (multi) | Bound to upstream schema |
| `FieldRef` | field picker (single) | e.g. sort/join key |
| `FilePath` | file browser | Restricted to allow-listed root |
| `list[SubModel]` | repeatable group | e.g. multiple aggregations |

## 3. `infer_schema` vs `execute`

| Method | When | Input | Output | Cost |
| --- | --- | --- | --- | --- |
| `infer_schema` | Design time, on every edit | upstream **schemas** | this node's output **schemas** | Cheap, no data |
| `execute` | Run time | upstream **Frames** (lazy) | this node's output **Frames** | Real work (lazy/streamed) |

`infer_schema` powers the UI's field lists, connection validation, and downstream autocomplete **without
running data** — implement it faithfully.

## 4. The `Frame` API (backend-neutral)

Tools operate on `Frame`, a lazy handle that compiles to Polars, DuckDB, or Dask. Authors use a
Polars-like fluent API; the engine picks the backend. When a tool needs backend specifics, it can
branch on `ctx.backend`, but most tools never need to.

```python
def execute(self, inputs, cfg, ctx):
    df = inputs["in"]                      # Frame (lazy)
    out = (df
        .with_columns(cfg.new_field.compile(ctx.backend).alias(cfg.name))
        .filter(...))
    return {"out": out}
```

For power tools, `ctx.to_polars(frame)` / `ctx.to_duckdb(frame)` / `ctx.to_arrow(frame)` provide
explicit, zero-copy(-ish) escape hatches.

## 5. Run context (`ctx`)

The `ctx` passed to `execute` exposes controlled capabilities:

| Capability | Use |
| --- | --- |
| `ctx.backend` | Active backend (`"polars"` / `"duckdb"` / `"dask"`) |
| `ctx.message(level, text, field=None)` | Emit info/warn/error to the results panel |
| `ctx.progress(rows=..., pct=...)` | Report progress for long operations |
| `ctx.is_cancelled()` | Cooperative cancellation check (in loops) |
| `ctx.temp_dir` | Scratch space for spills |
| `ctx.workspace_path(rel)` | Resolve a user path within the allow-listed root |
| `ctx.secret(name)` | Fetch a configured credential (never hard-code) |

## 6. Packaging & discovery (plugins)

Tools are discovered via **Python entry points**, so a third-party package "just works" once pip-installed.

```toml
# pyproject.toml of a plugin package
[project]
name = "pyflow-tools-geo"
dependencies = ["pyflow-sdk>=1.0", "shapely", "geopandas"]

[project.entry-points."pyflow.tools"]
spatial_join = "pyflow_tools_geo.spatial:SpatialJoinTool"
create_points = "pyflow_tools_geo.points:CreatePointsTool"
```

- On startup (and on a "rescan" action) the engine loads all `pyflow.tools` entry points into the
  **tool registry**; the frontend fetches the updated catalog.
- Tools declare their own **dependencies**; heavy optional stacks (ML, spatial, spaCy) live in separate
  plugin packages so the core stays lean.
- **Versioning:** a tool's `version` enables **config migrations** — a `migrate(old_cfg, from_version)`
  hook upgrades saved workflows when a tool's schema changes, so old `.pyflow` files keep opening.

## 7. Testing a tool

The SDK ships a test harness so tools are unit-testable without the server or browser:

```python
from pyflow_sdk.testing import run_tool
import polars as pl

def test_filter_splits_rows():
    df = pl.DataFrame({"status": ["active", "inactive"], "spend": [10, 20]})
    out = run_tool(FilterTool, {"expression": '[status] == "active"'}, {"in": df})
    assert out["true"].to_polars().to_dict(as_series=False) == {"status": ["active"], "spend": [10]}
    assert out["false"].height == 1
```

Recommended coverage per tool: schema inference correctness, the happy path, null/empty-input handling,
type-error behavior, and a large-input smoke test for streaming tools.

## 8. Guidelines for well-behaved tools

- **Be lazy.** Return lazy `Frame` transforms; don't `.collect()` unless the operation truly requires it.
- **Preserve/annotate schema.** Keep field descriptions and provenance flowing through.
- **Handle nulls and bad data explicitly**, with a config choice (error / warn+null / drop) where relevant.
- **Emit messages**, not prints — they belong in the results panel.
- **Respect cancellation** in any manual loop.
- **Keep dependencies in the plugin**, not the core.
- **Write `infer_schema`** even when it seems trivial — the UX depends on it.

## 9. Stability contract

`pyflow-sdk` is the **only** supported import surface for third-party tools and is **semver-stable**.
Engine internals may change between minor releases; the SDK will not break within a major version. This
separation (SDK vs engine) is why tools written today keep working as the engine evolves.
