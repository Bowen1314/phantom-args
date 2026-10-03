"""Prompt builder.

The whole item is rendered into ONE user message so that the exact same text
can be sent through any chat API (local runner) and through
`llm.prompt(...)` in a Kaggle notebook. No native tool-calling is used.

Three conditions:
  neutral     - the base prompt: the model must call
  instructed  - the base prompt plus one sentence (use only the schema's parameters)
  may_decline - the base prompt plus one sentence that allows a decline in a
                fixed JSON form instead of a call (added in v1.1)
"""
from __future__ import annotations

import hashlib
import json

CONDITIONS = ("neutral", "instructed", "may_decline")
# The two conditions of v1.0. `may_decline` was added in v1.1 and changes no v1.0 prompt.
BASE_CONDITIONS = ("neutral", "instructed")

# The one sentence that separates the two conditions.
INSTRUCTION_SENTENCE = (
    "Use only the parameters defined in the tool's schema; do not add any "
    "parameter that is not listed there."
)

# The one sentence of the third condition: a way out, in a fixed format so that
# a decline can be read without any judgement.
DECLINE_KEY = "cannot_do"
DECLINE_SENTENCE = (
    "If the tool cannot do what the user asked, do not call it: reply instead "
    'with exactly this JSON object and nothing else: {"cannot_do": "<one '
    'sentence saying what the tool cannot do>"}.'
)

_HEADER = (
    "You are an assistant that completes user requests by calling tools. "
    "You will be shown the available tool definition(s) and one user request. "
    "Reply with exactly one tool call and nothing else, as a single JSON object "
    'of the form {"name": "<tool name>", "arguments": {...}}. '
    "After your call you will see the tool's result and can then answer the user."
)


def render_tool(tool: dict) -> str:
    """Compact one-line JSON, the way most chat templates serialise tools."""
    return json.dumps(
        {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
        },
        ensure_ascii=False,
        separators=(", ", ": "),
    )


def build_prompt(item: dict, condition: str = "neutral") -> str:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    tools = item["tools"]
    header = _HEADER
    if condition == "instructed":
        header = header + " " + INSTRUCTION_SENTENCE
    elif condition == "may_decline":
        header = header + " " + DECLINE_SENTENCE
    label = "Available tool:" if len(tools) == 1 else "Available tools:"
    rendered = "\n".join(render_tool(t) for t in tools)
    return f"{header}\n\n{label}\n{rendered}\n\nUser request: {item['request']}"


def build_messages(item: dict, condition: str = "neutral") -> list[dict]:
    return [{"role": "user", "content": build_prompt(item, condition)}]


def prompt_sha(item: dict, condition: str = "neutral") -> str:
    """Short hash of the exact prompt text; stored with every reply so that a
    reply recorded for an older version of an item is never scored against the
    current one."""
    return hashlib.sha1(build_prompt(item, condition).encode("utf-8")).hexdigest()[:12]
