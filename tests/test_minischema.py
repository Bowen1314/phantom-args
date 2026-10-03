"""The built-in fallback validator must agree with jsonschema on this tool library."""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from phantom_args.minischema import MiniValidator
from phantom_args.scorer import validate_arguments

ROOT = Path(__file__).resolve().parent.parent
ITEMS = [json.loads(line) for line in (ROOT / "data" / "items.jsonl").read_text(encoding="utf-8").splitlines() if line]


def strip_messages(v):
    v = copy.deepcopy(v)
    for o in v["other_violations"]:
        o.pop("message", None)          # wording differs, the category and path must not
    v["other_violations"].sort(key=lambda o: (o["path"], o["validator"]))
    for key in ("enum_violations", "type_violations"):
        v[key].sort(key=lambda o: json.dumps(o, sort_keys=True, default=str))
    return v


def same(schema, args):
    a = strip_messages(validate_arguments(schema, args, Draft202012Validator))
    b = strip_messages(validate_arguments(schema, args, MiniValidator))
    assert a == b
    return a


def mutations(args):
    """Nasty variants of a valid arguments object."""
    yield {}
    yield {**args, "limit": 5, "page": "2"}
    for key, value in args.items():
        for bad in (None, "x", 0, -1, 10 ** 9, 1.5, 5.0, True, [], [1, "a", {}], {}, {"zz": 1}, [{"zz": 1}]):
            yield {**args, key: bad}
        yield {k: v for k, v in args.items() if k != key}
        if isinstance(value, dict):
            yield {**args, key: {**value, "extra_key": 1}}
            yield {**args, key: {k: str(v) for k, v in value.items()}}
        if isinstance(value, list) and value and isinstance(value[0], dict):
            yield {**args, key: value + [{"unknown": True}, 7, None]}


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_agrees_with_jsonschema(item):
    schema = item["tools"][0]["parameters"]
    ref = item["reference"]["arguments"]
    assert not any(same(schema, ref).values())
    if item["trap"] and item["family"] == "repurposing":
        assert not any(same(schema, item["trap"]["arguments"]).values())     # the misuse is schema-valid
    elif item["trap"]:
        assert any(same(schema, item["trap"]["arguments"]).values())
    for variant in mutations(ref):
        same(schema, variant)


def test_integer_semantics_match():
    schema = {"type": "object", "properties": {"n": {"type": "integer", "minimum": 1, "maximum": 50}},
              "required": ["n"], "additionalProperties": False}
    for value in (5, 5.0, 5.5, True, "5", 0, 51, None):
        same(schema, {"n": value})
