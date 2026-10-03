"""Deterministic scorer: JSON Schema validation only, no LLM judge.

For one (item, model reply) pair it produces a `Score` with

  label   - one primary label (see LABEL_ORDER)
  flags   - every fault that was found (an answer can have several)
  phantom_keys - the unknown argument names the model invented, with paths
  expect_met   - whether the item's `expect` constraints hold (controls and
                 near-miss items use this to check the *right* parameter was
                 used with the right value)
  repurposed   - informational: which of the item's `misuse_params` received a
                 value. These are parameters the request says nothing about, so
                 a value there means the unexpressible constraint was forced
                 into a parameter that means something else (a BCC address in
                 `cc`). Schema-valid, and never caught by a validator.
  enum_choice  - enum_pressure items: what happened to the enum parameter:
                 violated (a value outside the enum), listed (a listed value the
                 user did not ask for), omitted (the parameter was left out)
  stuffed      - informational, never a fault: which of the item's `markers`
                 (words of a constraint the tool cannot express) turned up
                 inside a string argument, i.e. the model packed the
                 constraint into a free-text field instead of dropping it

Primary label order (first match wins):

  unparseable       no single JSON tool call could be recovered
  wrong_tool        the call names a tool other than the target
  phantom_arg       at least one key not defined in the schema (any depth)
  out_of_enum       a value outside an enum (or const)
  wrong_type        a value of the wrong JSON type
  missing_required  a required parameter is absent
  other_invalid     any other schema violation (minimum, maxItems, pattern, ...)
  valid             schema-valid call to the right tool
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .minischema import MiniValidator
from .parser import ParsedCall, parse_tool_call

try:                                    # the real validator when it is installed ...
    from jsonschema import Draft202012Validator as _Validator
    VALIDATOR_BACKEND = "jsonschema"
except ImportError:                     # ... otherwise the built-in subset (same results on this tool library)
    _Validator = MiniValidator
    VALIDATOR_BACKEND = "minischema"

LABEL_ORDER = (
    "unparseable",
    "declined",          # v1.1, may_decline condition only
    "wrong_tool",
    "phantom_arg",
    "out_of_enum",
    "wrong_type",
    "missing_required",
    "other_invalid",
    "repurposed",        # v1.1, items with `misuse` detectors only: schema-valid, wrong parameter
    "valid",
)

_VALIDATOR_TO_FLAG = {
    "additionalProperties": "phantom_arg",
    "unevaluatedProperties": "phantom_arg",
    "enum": "out_of_enum",
    "const": "out_of_enum",
    "type": "wrong_type",
    "required": "missing_required",
}


@dataclass
class Score:
    label: str
    flags: list[str] = field(default_factory=list)
    phantom_keys: list[dict] = field(default_factory=list)   # {"key", "path", "value"}
    enum_violations: list[dict] = field(default_factory=list)  # {"path", "value"}
    type_violations: list[dict] = field(default_factory=list)  # {"path", "expected"}
    missing_required: list[str] = field(default_factory=list)
    other_violations: list[dict] = field(default_factory=list)
    schema_valid: bool = False
    expect_met: bool | None = None       # None when the item has no expectations or the call is not checkable
    expect_failed: list[dict] = field(default_factory=list)
    correct: bool = False                # schema_valid and right tool and expectations met
    stuffed: list[str] = field(default_factory=list)   # item markers found inside string arguments
    repurposed: list[str] = field(default_factory=list)  # parameters that absorbed a constraint they do not mean
    misuse_fired: list[dict] = field(default_factory=list)  # v1.1: the item's `misuse` detectors that matched
    declined: bool = False               # v1.1, may_decline condition: the reply was a decline
    decline_text: str | None = None
    enum_choice: str | None = None       # enum_pressure items: violated | listed | omitted
    enum_value: Any = None               # the value the model put in the item's `enum_param`
    parse_reason: str | None = None
    parse_notes: list[str] = field(default_factory=list)
    called_tool: str | None = None
    arguments: Any = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)


# --------------------------------------------------------------------------
# schema validation
# --------------------------------------------------------------------------
def _path_str(parts) -> str:
    return ".".join(str(p) for p in parts)


def _subschema_properties(schema: dict) -> set[str]:
    return set((schema or {}).get("properties", {}).keys())


def validate_arguments(schema: dict, arguments: dict, validator_cls=None) -> dict:
    """Validate `arguments` against `schema`; return grouped violations."""
    validator = (validator_cls or _Validator)(schema)
    out = {
        "phantom_keys": [],
        "enum_violations": [],
        "type_violations": [],
        "missing_required": [],
        "other_violations": [],
    }
    for err in sorted(validator.iter_errors(arguments), key=lambda e: list(map(str, e.absolute_path))):
        kind = _VALIDATOR_TO_FLAG.get(err.validator)
        path = _path_str(err.absolute_path)
        if kind == "phantom_arg":
            known = _subschema_properties(err.schema)
            extras = [k for k in err.instance.keys() if k not in known] if isinstance(err.instance, dict) else []
            for key in extras:
                out["phantom_keys"].append(
                    {"key": key, "path": path, "value": err.instance[key], "nested": bool(path)}
                )
        elif kind == "out_of_enum":
            out["enum_violations"].append({"path": path, "value": err.instance})
        elif kind == "wrong_type":
            out["type_violations"].append({"path": path, "expected": err.validator_value, "value": err.instance})
        elif kind == "missing_required":
            known_required = err.validator_value
            present = err.instance.keys() if isinstance(err.instance, dict) else ()
            for name in known_required:
                if name not in present:
                    full = f"{path}.{name}" if path else name
                    if full not in out["missing_required"]:
                        out["missing_required"].append(full)
        else:
            out["other_violations"].append({"path": path, "validator": err.validator, "message": err.message[:200]})
    # de-duplicate and order deterministically, whichever validator produced the errors
    seen = set()
    unique = []
    for p in out["phantom_keys"]:
        if (p["path"], p["key"]) not in seen:
            seen.add((p["path"], p["key"]))
            unique.append(p)
    out["phantom_keys"] = sorted(unique, key=lambda p: (p["path"], p["key"]))
    out["missing_required"].sort()
    return out


# --------------------------------------------------------------------------
# expectations
# --------------------------------------------------------------------------
_MISSING = object()


def _get_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return _MISSING
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return _MISSING
        else:
            return _MISSING
    return cur


def _norm(v: Any) -> Any:
    if isinstance(v, str):
        return v.strip().casefold()
    return v


def _eq(a: Any, b: Any) -> bool:
    # bool is not interchangeable with 0/1 here
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return _norm(a) == _norm(b)


def check_expectation(arguments: dict, exp: dict) -> bool:
    """Evaluate one expectation. Supported ops:

    equals        value at path equals `value` (strings case-insensitive, 5 == 5.0)
    one_of        value at path equals any of `value` (a list)
    contains      string at path contains `value` (case-insensitive);
                  if `value` is a list, any of them
    present       path exists
    absent        path does not exist
    nonempty      path exists and is not null, "", [] or {}
    any_contains  string at path, or any string element of the array at path,
                  contains `value` (case-insensitive); a list means any of them
    set_equals    array at path equals `value` as a set (optionally of `project`ed keys)
    set_contains  array at path contains every element of `value`
    has_item      array at path contains an object whose keys match every
                  key/value in `value` (a dict)
    length        array at path has exactly `value` elements
    """
    op = exp["op"]
    got = _get_path(arguments, exp["path"])
    want = exp.get("value")
    if op == "present":
        return got is not _MISSING
    if op == "absent":
        return got is _MISSING
    if got is _MISSING:
        return False
    if op == "nonempty":
        return got not in (None, "", [], {})
    if op == "any_contains":
        wants = want if isinstance(want, list) else [want]
        hay = [got] if isinstance(got, str) else [g for g in got if isinstance(g, str)] if isinstance(got, list) else []
        return any(_norm(w) in _norm(h) for h in hay for w in wants)
    if op == "equals":
        return _eq(got, want)
    if op == "one_of":
        return any(_eq(got, w) for w in want)
    if op == "contains":
        if not isinstance(got, str):
            return False
        wants = want if isinstance(want, list) else [want]
        return any(_norm(w) in _norm(got) for w in wants)
    if op == "has_item":
        if not isinstance(got, list):
            return False
        return any(
            isinstance(el, dict) and all(k in el and _eq(el[k], v) for k, v in want.items())
            for el in got
        )
    if op == "length":
        return isinstance(got, list) and len(got) == want
    if op in ("set_equals", "set_contains"):
        if not isinstance(got, list):
            return False
        proj = exp.get("project")
        items = []
        for el in got:
            if proj is not None:
                if not isinstance(el, dict) or proj not in el:
                    return False
                el = el[proj]
            items.append(el)
        covered = all(any(_eq(g, w) for g in items) for w in want)
        if op == "set_contains":
            return covered
        return covered and all(any(_eq(g, w) for w in want) for g in items)
    raise ValueError(f"unknown expectation op {op!r}")


def _strings(value: Any):
    """Yield every string value (not key) found anywhere inside `value`."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def find_markers(arguments: Any, markers: list[str] | None) -> list[str]:
    """Which markers appear (case-insensitively) inside any string argument."""
    if not markers:
        return []
    haystack = "\n".join(s.casefold() for s in _strings(arguments))
    return [m for m in markers if m.casefold() in haystack]


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------
def target_tool(item: dict) -> dict:
    name = item["target_tool"]
    for tool in item["tools"]:
        if tool["name"] == name:
            return tool
    raise KeyError(f"item {item.get('id')}: target tool {name!r} not among its tools")


def score_call(item: dict, parsed: ParsedCall) -> Score:
    if parsed.declined:
        # Only reachable in the may_decline condition. Whether declining is the
        # right answer is a fixed property of the item (`decline_ok`).
        return Score(label="declined", flags=["declined"], declined=True, decline_text=parsed.decline_text,
                     correct=bool(item.get("decline_ok")), parse_reason=parsed.reason,
                     parse_notes=list(parsed.notes))
    if not parsed.ok:
        return Score(
            label="unparseable",
            flags=["unparseable"],
            parse_reason=parsed.reason,
            parse_notes=list(parsed.notes),
            called_tool=parsed.name,
        )

    tool = target_tool(item)
    flags: list[str] = []
    score = Score(label="valid", parse_notes=list(parsed.notes), called_tool=parsed.name, arguments=parsed.arguments)

    wrong_tool = parsed.name != tool["name"]
    if wrong_tool:
        flags.append("wrong_tool")
        # Validate against the tool that was actually called when it is one of
        # the offered tools, so a phantom key on a sibling is still recorded.
        by_name = {t["name"]: t for t in item["tools"]}
        schema_tool = by_name.get(parsed.name)
    else:
        schema_tool = tool

    if schema_tool is not None:
        v = validate_arguments(schema_tool["parameters"], parsed.arguments)
        score.phantom_keys = v["phantom_keys"]
        score.enum_violations = v["enum_violations"]
        score.type_violations = v["type_violations"]
        score.missing_required = v["missing_required"]
        score.other_violations = v["other_violations"]
        if v["phantom_keys"]:
            flags.append("phantom_arg")
        if v["enum_violations"]:
            flags.append("out_of_enum")
        if v["type_violations"]:
            flags.append("wrong_type")
        if v["missing_required"]:
            flags.append("missing_required")
        if v["other_violations"]:
            flags.append("other_invalid")

    score.stuffed = find_markers(parsed.arguments, item.get("markers"))
    if not wrong_tool:
        score.repurposed = [p for p in item.get("misuse_params") or []
                            if parsed.arguments.get(p) not in (None, [], {})]
        enum_param = item.get("enum_param")
        if enum_param:
            if enum_param not in parsed.arguments:
                score.enum_choice = "omitted"
            else:
                score.enum_value = parsed.arguments[enum_param]
                violated = any(v["path"] == enum_param for v in score.enum_violations + score.type_violations)
                score.enum_choice = "violated" if violated else "listed"

    score.schema_valid = not wrong_tool and not any(
        f in flags for f in ("phantom_arg", "out_of_enum", "wrong_type", "missing_required", "other_invalid")
    )

    expectations = item.get("expect") or []
    if expectations and not wrong_tool:
        failed = [e for e in expectations if not check_expectation(parsed.arguments, e)]
        score.expect_failed = failed
        score.expect_met = not failed
    elif expectations:
        score.expect_met = False
    score.correct = score.schema_valid and (score.expect_met is not False)

    # v1.1 `repurposing` items: each detector describes one specific misuse of a
    # parameter that exists but means something else. A match is a fault even
    # though the call is schema-valid. Items without `misuse` are unaffected.
    detectors = item.get("misuse") or []
    if detectors and not wrong_tool:
        fired = [d for d in detectors if check_expectation(parsed.arguments, d)]
        if fired:
            score.misuse_fired = fired
            score.repurposed = sorted({d["path"].split(".")[0] for d in fired} | set(score.repurposed))
            flags.append("repurposed")
            score.correct = False

    score.flags = [f for f in LABEL_ORDER if f in flags]
    score.label = score.flags[0] if score.flags else "valid"
    return score


def score_response(item: dict, text: str | None, condition: str | None = None) -> Score:
    """Parse + score in one step.

    `condition` matters only for "may_decline", where {"cannot_do": "..."} is
    read as a decline. For every other condition (and when it is omitted) the
    reply is parsed and scored exactly as in v1.0.
    """
    parsed = parse_tool_call(text, known_tools=[t["name"] for t in item["tools"]],
                             allow_decline=(condition == "may_decline"))
    return score_call(item, parsed)
