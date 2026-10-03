"""Tolerant tool-call parser.

Turns a model's free-text reply into `ParsedCall(name, arguments)` or a parse
failure with a reason. It never guesses about schema validity; that is the
scorer's job.

Tolerated:
  - code fences, <tool_call> tags, prose before/after the JSON
  - leaked <think>...</think> blocks
  - trailing commas, Python-literal dicts (single quotes, True/False/None)
  - `arguments` given as a JSON string
  - wrapper shapes: {"tool_call": {...}}, {"function": {...}}, {"tool_calls": [...]}
  - alias keys: tool / tool_name / function for the name;
    args / parameters / input / params for the arguments
  - a "flattened" call {"name": "t", "query": ...} and a bare arguments object
    (both flagged as format deviations)

Not tolerated (reported as their own outcome, never as a phantom argument):
  - empty reply                                -> reason "empty"
  - no JSON object at all                      -> reason "no_json"
  - JSON that is not shaped like a tool call   -> reason "not_a_tool_call"
  - two or more *different* tool calls         -> reason "multiple_calls"
  - braces present but no complete call decodes -> reason "malformed_json"
    (prose with no "{" at all is "no_json": the model answered in words)
  - arguments that are not a JSON object       -> reason "arguments_not_object"

Declines (v1.1, `may_decline` condition only, `allow_decline=True`):
  - {"cannot_do": "TEXT"} and no call         -> declined, reason "declined"
  - a decline together with a named call       -> reason "call_and_decline"
  A refusal written as prose is still "no_json": the format was not followed.

The tool library never uses a top-level parameter called name / tool /
function / arguments / args / parameters / params / input / type / id (the
item builder enforces this), so the "flattened" shape is unambiguous.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import Any

DECLINE_KEY = "cannot_do"
NAME_KEYS = ("name", "tool", "tool_name", "function_name", "function")
ARG_KEYS = ("arguments", "args", "parameters", "params", "input", "tool_input")

_THINK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


@dataclass
class ParsedCall:
    ok: bool
    name: str | None = None
    arguments: Any = None
    reason: str | None = None          # set when ok is False
    notes: list[str] = field(default_factory=list)   # format deviations that were tolerated
    n_candidates: int = 0
    declined: bool = False             # may_decline condition only: the reply was {"cannot_do": "..."}
    decline_text: str | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "name": self.name,
            "arguments": self.arguments,
            "reason": self.reason,
            "notes": list(self.notes),
        }


# --------------------------------------------------------------------------
# low-level helpers
# --------------------------------------------------------------------------
def strip_think(text: str) -> str:
    """Remove leaked reasoning blocks; also handles a dangling `</think>`."""
    text = _THINK_RE.sub("", text)
    low = text.lower()
    for closer in ("</think>", "</thinking>"):
        idx = low.rfind(closer)
        if idx != -1:
            text = text[idx + len(closer):]
            low = text.lower()
    return text


def _balanced_objects(text: str) -> list[str]:
    """Return every outermost {...} substring, honouring string literals."""
    out: list[str] = []
    depth = 0
    start = -1
    quote: str | None = None
    escape = False
    for i, ch in enumerate(text):
        if quote is not None:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            continue
        if depth > 0 and ch in ('"', "'"):
            # Only treat ' as a string delimiter when it plausibly opens a
            # Python-style string (after one of  { [ , :  ), so that an
            # apostrophe inside prose never swallows the rest of the text.
            if ch == "'":
                j = i - 1
                while j >= 0 and text[j] in " \t\r\n":
                    j -= 1
                if j < 0 or text[j] not in "{[,:":
                    continue
            quote = ch
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    out.append(text[start:i + 1])
                    start = -1
    return out


def _raw_decode_objects(text: str) -> list[str]:
    """Fallback scan: try a strict JSON decode at every "{".

    Used only when the balanced-brace scan finds nothing decodable, e.g. when
    a stray "{" in the prose before the call unbalances the whole reply.
    """
    decoder = json.JSONDecoder()
    out: list[str] = []
    i = 0
    while True:
        i = text.find("{", i)
        if i == -1:
            return out
        try:
            value, end = decoder.raw_decode(text, i)
        except (json.JSONDecodeError, RecursionError):
            i += 1
            continue
        if isinstance(value, dict):
            out.append(text[i:end])
        i = end


def loads_lenient(blob: str) -> tuple[Any, list[str]]:
    """json.loads with two repairs. Raises ValueError if nothing works."""
    try:
        return json.loads(blob), []
    except (json.JSONDecodeError, RecursionError):
        pass
    repaired = _TRAILING_COMMA_RE.sub(r"\1", blob)
    if repaired != blob:
        try:
            return json.loads(repaired), ["trailing_comma"]
        except (json.JSONDecodeError, RecursionError):
            pass
    try:
        value = ast.literal_eval(repaired)
    except (ValueError, SyntaxError, MemoryError, RecursionError, TypeError):
        raise ValueError("not JSON") from None
    if isinstance(value, (dict, list)):
        return value, ["python_literal"]
    raise ValueError("not JSON")


def _looks_like_tool_definition(obj: dict) -> bool:
    """A model sometimes echoes the tool spec; that is not a call."""
    params = obj.get("parameters")
    return (
        isinstance(params, dict)
        and params.get("type") == "object"
        and "properties" in params
        and ("description" in obj or "required" in params or "additionalProperties" in params)
    )


def _coerce_arguments(value: Any, notes: list[str]) -> Any:
    """Arguments may arrive as a JSON string; decode once (twice if nested)."""
    for _ in range(2):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("{"):
                try:
                    value, extra = loads_lenient(stripped)
                except ValueError:
                    return value
                if "arguments_as_string" not in notes:
                    notes.append("arguments_as_string")
                for n in extra:
                    if n not in notes:
                        notes.append(n)
                continue
        break
    return value


def _extract_calls(obj: Any, notes: list[str]) -> list[tuple[str | None, Any, list[str]]]:
    """Normalise one decoded JSON value into zero or more (name, args, notes)."""
    if isinstance(obj, list):
        calls: list = []
        for el in obj:
            calls.extend(_extract_calls(el, notes))
        return calls
    if not isinstance(obj, dict):
        return []
    if _looks_like_tool_definition(obj):
        return []

    # wrappers
    for wrapper in ("tool_call", "function_call"):
        if isinstance(obj.get(wrapper), dict):
            return _extract_calls(obj[wrapper], notes + [f"wrapped:{wrapper}"])
    if isinstance(obj.get("tool_calls"), list):
        return _extract_calls(obj["tool_calls"], notes + ["wrapped:tool_calls"])
    if isinstance(obj.get("function"), dict):
        return _extract_calls(obj["function"], notes + ["wrapped:function"])

    name_key = next((k for k in NAME_KEYS if isinstance(obj.get(k), str)), None)
    arg_key = next((k for k in ARG_KEYS if k in obj), None)
    local = list(notes)

    if name_key and arg_key:
        if name_key != "name":
            local.append(f"name_key:{name_key}")
        if arg_key != "arguments":
            local.append(f"arguments_key:{arg_key}")
        args = _coerce_arguments(obj[arg_key], local)
        return [(obj[name_key], args, local)]

    if name_key and not arg_key:
        rest = {k: v for k, v in obj.items() if k != name_key and k not in ("type", "id")}
        if rest:
            local.append("flattened_arguments")
        else:
            local.append("no_arguments_key")
        if name_key != "name":
            local.append(f"name_key:{name_key}")
        return [(obj[name_key], rest, local)]

    if arg_key and not name_key and len(obj) == 1:
        local.append("missing_name")
        args = _coerce_arguments(obj[arg_key], local)
        return [(None, args, local)]

    # No name at all: treat the whole object as a bare arguments object.
    local.append("bare_arguments")
    return [(None, obj, local)]


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
def _is_decline(value: Any) -> bool:
    """{"cannot_do": "..."} and nothing that looks like a call."""
    return (isinstance(value, dict) and DECLINE_KEY in value
            and not any(k in value for k in NAME_KEYS + ARG_KEYS))


def parse_tool_call(text: str | None, known_tools: list[str] | None = None,
                    allow_decline: bool = False) -> ParsedCall:
    """Parse a model reply into exactly one tool call.

    With `allow_decline` (the `may_decline` prompt condition only) a reply
    whose JSON is {"cannot_do": "..."} is returned as a decline
    (`declined=True`, `ok=False`, reason "declined"). A reply that both
    declines and calls is a parse failure ("call_and_decline"). Without the
    flag nothing changes: v1.0 conditions are parsed exactly as before.

    `known_tools` (the tool names shown in the prompt) is only used to
    interpret a reply whose arguments were given without a name wrapper: when
    exactly one tool was offered, the bare arguments are attributed to it.
    """
    if text is None or not str(text).strip():
        return ParsedCall(ok=False, reason="empty")
    cleaned = strip_think(str(text))

    decoded: list[tuple[Any, list[str]]] = []
    for blob in _balanced_objects(cleaned):
        try:
            value, repair_notes = loads_lenient(blob)
        except ValueError:
            continue
        decoded.append((value, repair_notes))
    if not decoded:
        # Nothing balanced decodes. Scan for any decodable object, but accept
        # only complete named calls: a fragment from inside a broken call (one
        # array item, one nested object) must not be mistaken for the call.
        fragments = _raw_decode_objects(cleaned)
        for blob in fragments:
            value = json.loads(blob)
            if (allow_decline and _is_decline(value)) or any(
                    name is not None for name, _, _ in _extract_calls(value, [])):
                decoded.append((value, ["recovered_by_scan"]))
        if not decoded:
            broken = bool(fragments) or "{" in cleaned
            return ParsedCall(ok=False, reason="malformed_json" if broken else "no_json",
                              n_candidates=len(fragments))

    declines: list[Any] = []
    if allow_decline:
        declines = [v for v, _ in decoded if _is_decline(v)]
        decoded = [(v, n) for v, n in decoded if not _is_decline(v)]

    calls: list[tuple[str | None, Any, list[str]]] = []
    for value, repair_notes in decoded:
        calls.extend(_extract_calls(value, list(repair_notes)))
    if declines:
        if any(name is not None for name, _, _ in calls):
            return ParsedCall(ok=False, reason="call_and_decline", n_candidates=len(calls) + len(declines))
        reason_text = declines[0].get(DECLINE_KEY)
        return ParsedCall(ok=False, reason="declined", declined=True,
                          decline_text=reason_text if isinstance(reason_text, str) else json.dumps(reason_text))
    if not calls:
        return ParsedCall(ok=False, reason="not_a_tool_call", n_candidates=len(decoded))

    # Prefer properly named calls over bare-argument guesses when both exist.
    named = [c for c in calls if c[0] is not None]
    if named:
        calls = named

    # De-duplicate identical calls (a model repeating itself is still one call).
    unique: list[tuple[str | None, Any, list[str]]] = []
    seen: set[str] = set()
    for name, args, notes in calls:
        try:
            key = json.dumps([name, args], sort_keys=True, default=str)
        except (TypeError, ValueError):
            key = repr((name, args))
        if key not in seen:
            seen.add(key)
            unique.append((name, args, notes))
    if len(unique) > 1:
        return ParsedCall(ok=False, reason="multiple_calls", n_candidates=len(unique))

    name, args, notes = unique[0]
    if len(calls) > 1 and "repeated_call" not in notes:
        notes.append("repeated_call")
    if name is None:
        if known_tools and len(known_tools) == 1:
            name = known_tools[0]
        else:
            return ParsedCall(ok=False, reason="not_a_tool_call", notes=notes, n_candidates=1)
    if not isinstance(args, dict):
        # arguments must be an object; anything else cannot be validated as a call
        return ParsedCall(ok=False, reason="arguments_not_object", name=name, notes=notes, n_candidates=1)
    return ParsedCall(ok=True, name=name.strip(), arguments=args, notes=notes, n_candidates=1)
