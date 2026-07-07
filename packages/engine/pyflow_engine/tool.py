"""Tool base class and anchor declarations.

A tool declares identity, anchors, a Pydantic config model (which drives the UI),
and a build() that returns lazy output Frames keyed by output-anchor id.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import BaseModel

from .context import RunContext
from .frame import Frame


@dataclass(frozen=True)
class InputAnchor:
    id: str
    contract: str = "any_table"
    multi: bool = False
    label: str | None = None


@dataclass(frozen=True)
class OutputAnchor:
    id: str
    label: str | None = None


class EmptyConfig(BaseModel):
    pass


def _item_defaults(target: dict[str, Any]) -> dict[str, Any]:
    """Default object for a new array item, from a sub-model's property defaults."""
    out: dict[str, Any] = {}
    for name, prop in target.get("properties", {}).items():
        if "default" in prop:
            out[name] = prop["default"]
        else:
            t = prop.get("type")
            out[name] = False if t == "boolean" else (0 if t in ("integer", "number") else "")
    return out


def _simplify_prop(name: str, prop: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    field: dict[str, Any] = {
        "name": name,
        "title": prop.get("title", name),
        "default": prop.get("default"),
        "help": prop.get("description"),
        "editor": prop.get("x-editor"),
    }

    ref = prop.get("$ref")
    if not ref and isinstance(prop.get("allOf"), list) and prop["allOf"]:
        ref = prop["allOf"][0].get("$ref")

    # array — either of objects (repeatable group) or of scalars (multi picker)
    if prop.get("type") == "array":
        field["type"] = "array"
        items = prop.get("items", {})
        iref = items.get("$ref")
        if iref:
            target = defs.get(iref.split("/")[-1], {})
            field["item"] = [
                _simplify_prop(sn, sp, defs) for sn, sp in target.get("properties", {}).items()
            ]
            field["itemDefaults"] = _item_defaults(target)
        else:
            field["itemType"] = items.get("type", "string")
        return field

    if ref:
        target = defs.get(ref.split("/")[-1], {})
        if target.get("enum"):
            field["type"] = "enum"
            field["enum"] = target["enum"]
        else:
            field["type"] = "string"
        return field

    if prop.get("enum"):
        field["type"] = "enum"
        field["enum"] = prop["enum"]
        return field

    json_type = prop.get("type", "string")
    field["type"] = {"integer": "integer", "number": "number", "boolean": "boolean"}.get(
        json_type, "string"
    )
    return field


def _simplify_config_schema(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a Pydantic JSON schema into simple UI field descriptors.

    Resolves $ref/allOf enum references and array-of-object item schemas so the
    frontend can render a form (including repeatable groups and field pickers)
    without a full JSON-Schema interpreter.
    """
    defs = schema.get("$defs", {})
    return [
        _simplify_prop(name, prop, defs)
        for name, prop in schema.get("properties", {}).items()
    ]


class Tool:
    type: ClassVar[str]
    name: ClassVar[str]
    category: ClassVar[str] = "General"
    icon: ClassVar[str] = "box"
    version: ClassVar[str] = "1.0"
    Config: ClassVar[type[BaseModel]] = EmptyConfig
    inputs: ClassVar[list[InputAnchor]] = []
    outputs: ClassVar[list[OutputAnchor]] = []
    # Cacheable tools can reuse a materialized result across runs. Side-effecting
    # sinks (writing files/tables) set this False so they always execute.
    cacheable: ClassVar[bool] = True

    def build(
        self, inputs: dict[str, Frame], cfg: BaseModel, ctx: RunContext
    ) -> dict[str, Frame]:
        """Pure, lazy output construction. Called at run time AND by the design-time
        schema pass, so it must have NO side effects."""
        raise NotImplementedError

    def run(
        self, inputs: dict[str, Frame], cfg: BaseModel, ctx: RunContext
    ) -> dict[str, Frame]:
        """Run-time execution. Side effects (e.g. writing files) belong here, not in
        build(). Defaults to build() for pure tools."""
        return self.build(inputs, cfg, ctx)

    def cache_key(self, cfg: BaseModel) -> object:
        """Extra content signature folded into this node's cache hash — e.g. a source
        file's mtime/size so external changes invalidate the cache. JSON-serializable,
        or None."""
        return None

    @classmethod
    def descriptor(cls) -> dict[str, Any]:
        json_schema = cls.Config.model_json_schema()
        return {
            "type": cls.type,
            "name": cls.name,
            "category": cls.category,
            "icon": cls.icon,
            "version": cls.version,
            "inputs": [
                {"id": a.id, "contract": a.contract, "multi": a.multi, "label": a.label or a.id}
                for a in cls.inputs
            ],
            "outputs": [{"id": a.id, "label": a.label or a.id} for a in cls.outputs],
            "configSchema": json_schema,
            "configFields": _simplify_config_schema(json_schema),
        }
