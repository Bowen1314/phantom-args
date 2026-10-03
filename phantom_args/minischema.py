"""A tiny JSON Schema validator used only when `jsonschema` is not installed.

It covers exactly the keywords the tool library uses (the item builder rejects
anything else): type, enum, properties, required, additionalProperties: false,
items, minimum, maximum. Errors mimic the attributes of jsonschema's
ValidationError that the scorer reads. tests/test_minischema.py checks that it
agrees with jsonschema on every item, every trap and a set of nasty inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class MiniError:
    validator: str
    validator_value: Any
    instance: Any
    schema: dict
    absolute_path: list = field(default_factory=list)
    message: str = ""


def _is_type(value: Any, name: str) -> bool:
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "null":
        return value is None
    raise ValueError(f"unsupported type {name!r}")


def _enum_match(value: Any, options: list) -> bool:
    for opt in options:
        if isinstance(value, bool) != isinstance(opt, bool):
            continue
        if value == opt:
            return True
    return False


def iter_errors(schema: dict, instance: Any, path: list | None = None) -> Iterator[MiniError]:
    path = path or []
    if "type" in schema and not _is_type(instance, schema["type"]):
        yield MiniError("type", schema["type"], instance, schema, list(path),
                        f"{instance!r} is not of type {schema['type']!r}")
    if "enum" in schema and not _enum_match(instance, schema["enum"]):
        yield MiniError("enum", schema["enum"], instance, schema, list(path),
                        f"{instance!r} is not one of {schema['enum']!r}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            yield MiniError("minimum", schema["minimum"], instance, schema, list(path),
                            f"{instance!r} is less than the minimum of {schema['minimum']!r}")
        if "maximum" in schema and instance > schema["maximum"]:
            yield MiniError("maximum", schema["maximum"], instance, schema, list(path),
                            f"{instance!r} is greater than the maximum of {schema['maximum']!r}")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in instance:
                yield MiniError("required", schema["required"], instance, schema, list(path),
                                f"{name!r} is a required property")
        if schema.get("additionalProperties") is False:
            extras = [k for k in instance if k not in props]
            if extras:
                yield MiniError("additionalProperties", False, instance, schema, list(path),
                                f"Additional properties are not allowed ({', '.join(map(repr, extras))})")
        for key, sub in props.items():
            if key in instance:
                yield from iter_errors(sub, instance[key], path + [key])
    if isinstance(instance, list) and isinstance(schema.get("items"), dict):
        for i, el in enumerate(instance):
            yield from iter_errors(schema["items"], el, path + [i])


class MiniValidator:
    def __init__(self, schema: dict):
        self.schema = schema

    def iter_errors(self, instance: Any) -> Iterator[MiniError]:
        return iter_errors(self.schema, instance)
