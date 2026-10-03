"""Parser tests: every shape a model reply has been seen to take, plus nasty ones."""
import pytest

from phantom_args.parser import parse_tool_call

ONE = ["web_search"]


def ok(text, name="web_search", args=None, tools=ONE):
    p = parse_tool_call(text, known_tools=tools)
    assert p.ok, (p.reason, p.notes)
    assert p.name == name
    if args is not None:
        assert p.arguments == args
    return p


def bad(text, reason, tools=ONE):
    p = parse_tool_call(text, known_tools=tools)
    assert not p.ok
    assert p.reason == reason, p.reason
    return p


# ---------------------------------------------------------------- happy paths
def test_plain_json():
    p = ok('{"name": "web_search", "arguments": {"query": "x"}}', args={"query": "x"})
    assert p.notes == []


def test_fenced_json():
    ok('```json\n{"name": "web_search", "arguments": {"query": "x", "limit": 5}}\n```',
       args={"query": "x", "limit": 5})


def test_fenced_without_language_and_prose_around():
    text = 'Sure! Here is the call:\n```\n{"name": "web_search", "arguments": {"query": "x"}}\n```\nLet me know.'
    ok(text, args={"query": "x"})


def test_prose_before_and_after():
    ok('I will search now. {"name": "web_search", "arguments": {"query": "a b"}} Done.', args={"query": "a b"})


def test_tool_call_tags():
    ok('<tool_call>\n{"name": "web_search", "arguments": {"query": "x"}}\n</tool_call>', args={"query": "x"})


def test_leaked_think_block_is_ignored():
    text = '<think>Maybe {"name": "web_search", "arguments": {"query": "x", "limit": 5}}</think>\n' \
           '{"name": "web_search", "arguments": {"query": "x"}}'
    ok(text, args={"query": "x"})


def test_dangling_think_closer():
    text = 'thinking about {"limit": 5} ...</think>{"name": "web_search", "arguments": {"query": "x"}}'
    ok(text, args={"query": "x"})


# ---------------------------------------------------------------- repairs
def test_trailing_commas():
    p = ok('{"name": "web_search", "arguments": {"query": "x", "safe_search": true,},}',
           args={"query": "x", "safe_search": True})
    assert "trailing_comma" in p.notes


def test_python_literal_dict():
    p = ok("{'name': 'web_search', 'arguments': {'query': 'x', 'safe_search': True}}",
           args={"query": "x", "safe_search": True})
    assert "python_literal" in p.notes


def test_arguments_as_json_string():
    p = ok('{"name": "web_search", "arguments": "{\\"query\\": \\"x\\", \\"limit\\": 5}"}',
           args={"query": "x", "limit": 5})
    assert "arguments_as_string" in p.notes


def test_arguments_as_double_encoded_string():
    inner = '{\\\\\\"query\\\\\\": \\\\\\"x\\\\\\"}'
    text = '{"name": "web_search", "arguments": "\\"' + inner + '\\""}'
    p = parse_tool_call(text, known_tools=ONE)
    # a doubly encoded string is not silently accepted as an object unless it decodes to one
    assert (p.ok and p.arguments == {"query": "x"}) or p.reason == "arguments_not_object"


def test_apostrophe_in_prose_does_not_swallow_the_call():
    ok("Here's the call, it's simple: {\"name\": \"web_search\", \"arguments\": {\"query\": \"don't panic\"}}",
       args={"query": "don't panic"})


def test_braces_inside_string_values():
    ok('{"name": "web_search", "arguments": {"query": "what does {} mean in {python}"}}',
       args={"query": "what does {} mean in {python}"})


def test_stray_open_brace_in_prose_recovered_by_scan():
    p = ok('I will send { the following: {"name": "web_search", "arguments": {"query": "x"}}', args={"query": "x"})
    assert "recovered_by_scan" in p.notes


# ---------------------------------------------------------------- wrapper shapes and aliases
@pytest.mark.parametrize("text", [
    '{"tool_call": {"name": "web_search", "arguments": {"query": "x"}}}',
    '{"function_call": {"name": "web_search", "arguments": {"query": "x"}}}',
    '{"tool_calls": [{"type": "function", "function": {"name": "web_search", "arguments": "{\\"query\\": \\"x\\"}"}}]}',
    '{"type": "function", "function": {"name": "web_search", "arguments": {"query": "x"}}}',
    '[{"name": "web_search", "arguments": {"query": "x"}}]',
])
def test_wrappers(text):
    ok(text, args={"query": "x"})


@pytest.mark.parametrize("text,note", [
    ('{"tool": "web_search", "arguments": {"query": "x"}}', "name_key:tool"),
    ('{"name": "web_search", "parameters": {"query": "x"}}', "arguments_key:parameters"),
    ('{"function": "web_search", "args": {"query": "x"}}', "arguments_key:args"),
    ('{"tool_name": "web_search", "input": {"query": "x"}}', "arguments_key:input"),
])
def test_alias_keys(text, note):
    p = ok(text, args={"query": "x"})
    assert note in p.notes


def test_flattened_arguments():
    p = ok('{"name": "web_search", "query": "x", "limit": 5}', args={"query": "x", "limit": 5})
    assert "flattened_arguments" in p.notes


def test_bare_arguments_single_tool():
    p = ok('{"query": "x", "limit": 5}', args={"query": "x", "limit": 5})
    assert "bare_arguments" in p.notes


def test_bare_arguments_with_two_tools_is_not_a_call():
    bad('{"query": "x"}', "not_a_tool_call", tools=["web_search", "news_search"])


def test_name_without_arguments_means_empty_arguments():
    p = ok('{"name": "web_search"}', args={})
    assert "no_arguments_key" in p.notes


def test_nested_objects_survive():
    args = {"location": {"city": "Springfield", "state": "IL"}, "days": 3}
    ok('{"name": "get_weather_forecast", "arguments": {"location": {"city": "Springfield", "state": "IL"}, "days": 3}}',
       name="get_weather_forecast", args=args, tools=["get_weather_forecast"])


# ---------------------------------------------------------------- two JSON objects
def test_two_identical_calls_count_as_one():
    text = '{"name": "web_search", "arguments": {"query": "x"}}\n{"name": "web_search", "arguments": {"query": "x"}}'
    p = ok(text, args={"query": "x"})
    assert "repeated_call" in p.notes


def test_two_different_calls_are_their_own_outcome():
    text = '{"name": "web_search", "arguments": {"query": "x"}}\n{"name": "web_search", "arguments": {"query": "y"}}'
    bad(text, "multiple_calls")


def test_call_plus_unrelated_json_object_prefers_the_named_call():
    text = 'Schema excerpt: {"additionalProperties": false}\n{"name": "web_search", "arguments": {"query": "x"}}'
    ok(text, args={"query": "x"})


def test_echoed_tool_definition_is_not_a_call():
    echoed = ('{"name": "web_search", "description": "Search", "parameters": {"type": "object", '
              '"properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": false}}')
    bad(echoed, "not_a_tool_call")
    ok(echoed + '\n{"name": "web_search", "arguments": {"query": "x"}}', args={"query": "x"})


# ---------------------------------------------------------------- failures are failures, never phantoms
@pytest.mark.parametrize("text,reason", [
    (None, "empty"),
    ("", "empty"),
    ("   \n", "empty"),
    ("I cannot limit the results with this tool. Should I continue?", "no_json"),
    ('{"name": "web_search", "arguments": {"query": "x"', "malformed_json"),   # truncated
    ('{"name": "web_search", "arguments": {query: x}}', "malformed_json"),     # braces, but not JSON
    # a real reply from the pilot: one stray quote breaks the call; the two intact array
    # items inside it must not be read as two bare-argument calls
    ('{"name": "create_poll", "arguments": {"question": "Pick the offsite date", '
     '"options": [{"label": "14 Nov"}, {"label": "21 Nov"}"]}}', "malformed_json"),
    # same, with a single intact fragment: it must not become the call's arguments
    ('{"name": "create_event", "arguments": {"title": "x", "where": {"room": "A"}"}}', "malformed_json"),
    ('{"name": "web_search", "arguments": [1, 2]}', "arguments_not_object"),
    ('{"name": "web_search", "arguments": "top five"}', "arguments_not_object"),
    ('{"name": "web_search", "arguments": null}', "arguments_not_object"),
])
def test_failures(text, reason):
    bad(text, reason)


def test_name_is_stripped():
    ok('{"name": " web_search ", "arguments": {"query": "x"}}', args={"query": "x"})


def test_unknown_tool_name_still_parses():
    p = parse_tool_call('{"name": "search", "arguments": {"query": "x"}}', known_tools=ONE)
    assert p.ok and p.name == "search"   # the scorer, not the parser, calls this wrong_tool
