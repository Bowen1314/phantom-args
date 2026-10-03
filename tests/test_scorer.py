"""Scorer tests: one label per fault, label precedence, nested keys, expectations."""
import json
from pathlib import Path

import pytest

from phantom_args.parser import ParsedCall
from phantom_args.scorer import LABEL_ORDER, check_expectation, find_markers, score_call, score_response

ROOT = Path(__file__).resolve().parent.parent
ITEMS = [json.loads(line) for line in (ROOT / "data" / "items.jsonl").read_text(encoding="utf-8").splitlines() if line]


def obj(props, required=()):
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


TOOL = {
    "name": "search_flights",
    "description": "Search flights.",
    "parameters": obj(
        {
            "origin": {"type": "string"},
            "passengers": obj({"adults": {"type": "integer", "minimum": 1}, "children": {"type": "integer"}}, ["adults"]),
            "cabin": {"type": "string", "enum": ["economy", "business"]},
            "legs": {"type": "array", "items": obj({"to": {"type": "string"}}, ["to"])},
        },
        ["origin", "passengers"],
    ),
}
ITEM = {"id": "t-1", "family": "nested", "tools": [TOOL], "target_tool": "search_flights", "expect": [],
        "markers": ["nonstop"]}


def call(args, name="search_flights", item=ITEM):
    return score_response(item, json.dumps({"name": name, "arguments": args}))


def test_valid():
    s = call({"origin": "SFO", "passengers": {"adults": 1}, "cabin": "economy"})
    assert s.label == "valid" and s.flags == [] and s.schema_valid and s.correct


def test_top_level_phantom_records_the_key():
    s = call({"origin": "SFO", "passengers": {"adults": 1}, "limit": 5})
    assert s.label == "phantom_arg"
    assert [(p["key"], p["path"], p["value"]) for p in s.phantom_keys] == [("limit", "", 5)]
    assert not s.schema_valid and not s.correct


def test_nested_object_phantom():
    s = call({"origin": "SFO", "passengers": {"adults": 1, "infants": 1}})
    assert s.label == "phantom_arg"
    assert [(p["key"], p["path"], p["nested"]) for p in s.phantom_keys] == [("infants", "passengers", True)]


def test_array_item_phantom():
    s = call({"origin": "SFO", "passengers": {"adults": 1}, "legs": [{"to": "JFK"}, {"to": "BOS", "stopover": True}]})
    assert s.label == "phantom_arg"
    assert [(p["key"], p["path"]) for p in s.phantom_keys] == [("stopover", "legs.1")]


def test_several_phantoms_at_several_depths():
    s = call({"origin": "SFO", "passengers": {"adults": 1, "pets": 1}, "sort": "price", "page": 2})
    assert sorted(p["key"] for p in s.phantom_keys) == ["page", "pets", "sort"]


def test_out_of_enum():
    s = call({"origin": "SFO", "passengers": {"adults": 1}, "cabin": "first"})
    assert s.label == "out_of_enum" and s.enum_violations == [{"path": "cabin", "value": "first"}]


def test_wrong_type():
    s = call({"origin": "SFO", "passengers": {"adults": "two"}})
    assert s.label == "wrong_type" and s.type_violations[0]["path"] == "passengers.adults"


def test_missing_required_top_and_nested():
    s = call({"passengers": {"children": 1}})
    assert s.label == "missing_required"
    assert sorted(s.missing_required) == ["origin", "passengers.adults"]


def test_other_invalid_minimum():
    s = call({"origin": "SFO", "passengers": {"adults": 0}})
    assert s.label == "other_invalid" and s.other_violations[0]["validator"] == "minimum"


def test_wrong_tool():
    s = call({"origin": "SFO", "passengers": {"adults": 1}}, name="flight_search")
    assert s.label == "wrong_tool" and s.flags == ["wrong_tool"] and not s.correct


def test_unparseable_is_not_a_phantom():
    s = score_response(ITEM, "The tool has no nonstop filter, so I cannot do that.")
    assert s.label == "unparseable" and s.parse_reason == "no_json" and s.phantom_keys == []


def test_multiple_faults_keep_all_flags_and_primary_follows_label_order():
    s = call({"passengers": {"adults": "2", "infants": 1}, "cabin": "first", "limit": 3})
    assert s.flags == ["phantom_arg", "out_of_enum", "wrong_type", "missing_required"]
    assert s.label == "phantom_arg"
    assert LABEL_ORDER.index("phantom_arg") < LABEL_ORDER.index("out_of_enum") < LABEL_ORDER.index("wrong_type")


def test_markers_note_stuffing_without_making_it_a_fault():
    s = call({"origin": "SFO nonstop", "passengers": {"adults": 1}})
    assert s.label == "valid" and s.stuffed == ["nonstop"]
    assert find_markers({"a": [{"b": "Non-Stop"}]}, ["non-stop", "direct"]) == ["non-stop"]
    assert find_markers({"nonstop": True}, ["nonstop"]) == []      # keys are not searched, only string values


def test_arguments_given_as_json_string_are_scored_normally():
    text = json.dumps({"name": "search_flights", "arguments": json.dumps({"origin": "SFO", "passengers": {"adults": 1}, "limit": 5})})
    s = score_response(ITEM, text)
    assert s.label == "phantom_arg" and "arguments_as_string" in s.parse_notes


def test_fenced_reply_with_nested_unknown_key():
    text = '```json\n{"name": "search_flights", "arguments": {"origin": "SFO", "passengers": {"adults": 2, "seniors": 1},},}\n```'
    s = score_response(ITEM, text)
    assert s.label == "phantom_arg" and s.phantom_keys[0]["key"] == "seniors"


# ---------------------------------------------------------------- expectations
def test_expectations_gate_correct_not_label():
    item = dict(ITEM, expect=[{"path": "cabin", "op": "equals", "value": "business"},
                              {"path": "passengers.adults", "op": "equals", "value": 2}])
    good = call({"origin": "SFO", "passengers": {"adults": 2}, "cabin": "business"}, item=item)
    assert good.label == "valid" and good.expect_met and good.correct
    lazy = call({"origin": "SFO", "passengers": {"adults": 2}}, item=item)
    assert lazy.label == "valid" and lazy.expect_met is False and not lazy.correct
    assert lazy.expect_failed[0]["path"] == "cabin"


@pytest.mark.parametrize("args,exp,want", [
    ({"a": "Hello "}, {"path": "a", "op": "equals", "value": "hello"}, True),
    ({"a": 5.0}, {"path": "a", "op": "equals", "value": 5}, True),
    ({"a": "5"}, {"path": "a", "op": "equals", "value": 5}, False),
    ({"a": True}, {"path": "a", "op": "equals", "value": 1}, False),
    ({"a": {"b": 3}}, {"path": "a.b", "op": "equals", "value": 3}, True),
    ({"a": "pdf"}, {"path": "a", "op": "one_of", "value": ["pdf", ".pdf"]}, True),
    ({"a": "NeurIPS 2020"}, {"path": "a", "op": "contains", "value": "neurips"}, True),
    ({"a": 7}, {"path": "a", "op": "contains", "value": "7"}, False),
    ({}, {"path": "a", "op": "absent"}, True),
    ({"a": 1}, {"path": "a", "op": "present"}, True),
    ({"a": ["x", "Y"]}, {"path": "a", "op": "set_equals", "value": ["y", "x"]}, True),
    ({"a": ["x", "y", "z"]}, {"path": "a", "op": "set_equals", "value": ["y", "x"]}, False),
    ({"a": ["x", "y", "z"]}, {"path": "a", "op": "set_contains", "value": ["y", "x"]}, True),
    ({"a": [{"e": "p@q"}, {"e": "r@s"}]}, {"path": "a", "op": "set_equals", "value": ["r@s", "p@q"], "project": "e"}, True),
    ({"a": [{"e": "p@q", "o": True}]}, {"path": "a", "op": "has_item", "value": {"e": "p@q", "o": True}}, True),
    ({"a": [{"e": "p@q"}]}, {"path": "a", "op": "has_item", "value": {"e": "p@q", "o": True}}, False),
    ({"a": [1, 2, 3]}, {"path": "a", "op": "length", "value": 3}, True),
    ({"a": [{"b": 9}]}, {"path": "a.0.b", "op": "equals", "value": 9}, True),
])
def test_check_expectation(args, exp, want):
    assert check_expectation(args, exp) is want


# ---------------------------------------------------------------- the shipped data file
def test_item_file_shape():
    ids = [it["id"] for it in ITEMS]
    assert len(ids) == len(set(ids))
    fams = {}
    for it in ITEMS:
        fams[it["family"]] = fams.get(it["family"], 0) + 1
    v1_0 = {"conventional", "near_miss", "inexpressible", "enum_pressure", "nested", "control"}
    assert set(fams) == v1_0 | {"repurposing", "matched_control"}
    assert all(fams[f] >= 15 for f in v1_0) and 24 <= fams["repurposing"] <= 30 and fams["matched_control"] >= 8
    # v1.0 is frozen: the same 162 items, all still marked as version 1.0
    assert sum(fams[f] for f in v1_0) == 162
    assert {it["version"] for it in ITEMS if it["family"] in v1_0} == {"1.0"}
    assert {it["version"] for it in ITEMS if it["family"] not in v1_0} == {"1.1"}
    assert sum(bool(it["core"]) for it in ITEMS if it["family"] in v1_0) == 60


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_reference_is_correct_and_trap_shows_the_family_fault(item):
    ref = score_call(item, ParsedCall(ok=True, name=item["reference"]["name"], arguments=item["reference"]["arguments"]))
    assert ref.label == "valid" and ref.correct
    if item["family"] in ("control", "matched_control"):
        assert item["trap"] is None and item["expect"]
    else:
        trap = score_call(item, ParsedCall(ok=True, name=item["trap"]["name"], arguments=item["trap"]["arguments"]))
        assert trap.label == item["target_fault"] and not trap.correct


# ---------------------------------------------------------------- informational outcomes
def by_id(iid):
    return next(it for it in ITEMS if it["id"] == iid)


def bcc_item():
    return next(it for it in ITEMS if it["misuse_params"] == ["cc"])


def test_repurposed_parameter_is_noted_but_stays_schema_valid():
    item = bcc_item()
    args = dict(item["reference"]["arguments"], cc=["legal@acme.example"])
    s = score_call(item, ParsedCall(ok=True, name=item["target_tool"], arguments=args))
    assert s.label == "valid" and s.repurposed == ["cc"] and s.stuffed == ["legal@acme.example"]
    clean = score_call(item, ParsedCall(ok=True, name=item["target_tool"], arguments=dict(item["reference"]["arguments"], cc=[])))
    assert clean.repurposed == []


def test_empty_string_in_a_misuse_parameter_counts_as_repurposed():
    item = next(it for it in ITEMS if it["misuse_params"] == ["assignee_email"])
    args = dict(item["reference"]["arguments"], assignee_email="")
    s = score_call(item, ParsedCall(ok=True, name=item["target_tool"], arguments=args))
    assert s.label == "valid" and s.repurposed == ["assignee_email"]


def test_enum_choice_three_outcomes():
    item = next(it for it in ITEMS if it["family"] == "enum_pressure" and it["enum_param"] == "status"
                and it["target_tool"] == "list_orders")
    base = item["reference"]["arguments"]

    def choice(extra):
        s = score_call(item, ParsedCall(ok=True, name=item["target_tool"], arguments=dict(base, **extra)))
        return s.enum_choice, s.enum_value, s.label

    assert choice({}) == ("omitted", None, "valid")
    assert choice({"status": "cancelled"}) == ("listed", "cancelled", "valid")
    assert choice({"status": "returned"}) == ("violated", "returned", "out_of_enum")
    assert choice({"status": 7}) == ("violated", 7, "wrong_type") or choice({"status": 7})[0] == "violated"


def test_only_enum_items_have_enum_choice():
    item = by_id("ctrl-01")
    s = score_call(item, ParsedCall(ok=True, name=item["target_tool"], arguments=item["reference"]["arguments"]))
    assert s.enum_choice is None and s.repurposed == []


# ---------------------------------------------------------------- v1.1: repurposing, matched controls, declines
import json as _json
from pathlib import Path as _Path

from phantom_args.prompt import BASE_CONDITIONS, CONDITIONS, DECLINE_SENTENCE, build_prompt, prompt_sha
from phantom_args.scorer import check_expectation

REP = [it for it in ITEMS if it["family"] == "repurposing"]
MCTL = [it for it in ITEMS if it["family"] == "matched_control"]
DECLINE = '{"cannot_do": "The tool has no such filter."}'


def test_v1_0_prompts_are_frozen():
    manifest = _json.loads(_Path("data/v1.0_prompt_hashes.json").read_text())
    assert len(manifest) == 162
    for iid, hashes in manifest.items():
        for cond in BASE_CONDITIONS:
            assert prompt_sha(by_id(iid), cond) == hashes[cond]


def test_third_condition_adds_exactly_one_sentence():
    item = by_id("rep-01")
    assert CONDITIONS == ("neutral", "instructed", "may_decline")
    neutral, decline = build_prompt(item, "neutral"), build_prompt(item, "may_decline")
    assert decline.replace(" " + DECLINE_SENTENCE, "") == neutral
    assert '{"cannot_do": ' in DECLINE_SENTENCE


@pytest.mark.parametrize("item", REP, ids=[it["id"] for it in REP])
def test_repurposing_item_contract(item):
    tool = item["tools"][0]["name"]
    ref = score_call(item, ParsedCall(ok=True, name=tool, arguments=item["reference"]["arguments"]))
    assert ref.label == "valid" and ref.correct and not ref.misuse_fired
    trap = score_call(item, ParsedCall(ok=True, name=tool, arguments=item["trap"]["arguments"]))
    assert trap.label == "repurposed" and trap.schema_valid and not trap.correct
    assert item["tempting_keys"][0] in trap.repurposed
    assert item["decline_ok"] is True and item["pattern"] in ("role", "negation", "bound", "absence", "enum_substitute")
    # a decline is correct here, but only when the condition allows one
    assert score_response(item, DECLINE, "may_decline").label == "declined"
    assert score_response(item, DECLINE, "may_decline").correct
    for cond in (None, "neutral", "instructed"):
        s = score_response(item, DECLINE, cond)
        assert s.label != "declined" and not s.correct


@pytest.mark.parametrize("item", MCTL, ids=[it["id"] for it in MCTL])
def test_matched_control_contract(item):
    tool = item["tools"][0]["name"]
    ref = score_call(item, ParsedCall(ok=True, name=tool, arguments=item["reference"]["arguments"]))
    assert ref.label == "valid" and ref.correct
    assert not item.get("misuse") and item["decline_ok"] is False
    declined = score_response(item, DECLINE, "may_decline")
    assert declined.label == "declined" and not declined.correct


def test_every_tempting_parameter_has_a_matched_control_somewhere():
    """Using the parameter is not wrong by itself: for most tools a control exists where it is the right one."""
    rep_tools = {it["target_tool"] for it in REP}
    ctl_tools = {it["target_tool"] for it in ITEMS if it["family"] in ("matched_control", "control")}
    assert len(rep_tools & ctl_tools) >= 12


def test_decline_is_scored_by_family():
    for it in ITEMS:
        s = score_response(it, DECLINE, "may_decline")
        expected = it["family"] in ("conventional", "inexpressible", "enum_pressure", "nested", "repurposing")
        assert s.label == "declined" and s.correct == expected, it["id"]


def test_decline_parsing_edge_cases():
    item = by_id("rep-01")
    ok = lambda text: score_response(item, text, "may_decline")
    assert ok('```json\n{"cannot_do": "no BCC"}\n```').label == "declined"
    assert ok('I cannot do that.\n{"cannot_do": "no BCC"}').decline_text == "no BCC"
    assert ok('{"cannot_do": "x"}\n{"cannot_do": "x"}').label == "declined"
    both = ok('{"cannot_do": "no BCC"}\n{"name": "draft_email", "arguments": {"to": ["a@b.example"], "subject": "s", "body": "b"}}')
    assert both.label == "unparseable" and both.parse_reason == "call_and_decline"
    prose = ok("The tool cannot blind-copy anyone.")
    assert prose.label == "unparseable" and prose.parse_reason == "no_json"
    assert ok('{"cannot_do": "no BCC", "name": "draft_email", "arguments": {}}').label != "declined"
    # v1.0 behaviour is untouched: without the condition the object is read as bare arguments
    assert score_response(item, '{"cannot_do": "no BCC"}').label == "phantom_arg"


def test_misuse_detector_does_not_fire_on_the_legitimate_use():
    photos = next(it for it in REP if it["target_tool"] == "search_photos")
    good = score_call(photos, ParsedCall(ok=True, name="search_photos", arguments={"tags": ["beach"], "taken_after": "2026-06-01"}))
    assert good.correct and not good.misuse_fired
    bad = score_call(photos, ParsedCall(ok=True, name="search_photos", arguments={"tags": ["beach", "Family"], "taken_after": "2026-06-01"}))
    assert bad.label == "repurposed" and bad.repurposed == ["tags"]
    # a schema fault outranks the misuse as the label; the flag is kept
    worse = score_call(photos, ParsedCall(ok=True, name="search_photos", arguments={"tags": ["beach", "family"], "exclude": ["family"]}))
    assert worse.label == "phantom_arg" and "repurposed" in worse.flags and not worse.correct


def test_new_ops():
    args = {"a": "", "b": ["Peanut butter", "lime"], "c": "tests/unit", "d": None, "e": 0}
    assert check_expectation(args, {"path": "a", "op": "present"})
    assert not check_expectation(args, {"path": "a", "op": "nonempty"})
    assert not check_expectation(args, {"path": "d", "op": "nonempty"})
    assert check_expectation(args, {"path": "e", "op": "nonempty"})
    assert not check_expectation(args, {"path": "zz", "op": "nonempty"})
    assert check_expectation(args, {"path": "b", "op": "any_contains", "value": "peanut"})
    assert check_expectation(args, {"path": "c", "op": "any_contains", "value": ["src", "test"]})
    assert not check_expectation(args, {"path": "b", "op": "any_contains", "value": "family"})
    assert not check_expectation(args, {"path": "e", "op": "any_contains", "value": "0"})


# Replies seen in the v1.1 validation. A detector must match the specific misuse, not any use of the parameter.
SEEN = [
    # (tool, arguments, repurposed?)
    ("search_accessories", {"category": "charger", "max_price": 60, "brand": ""}, False),          # empty value: a no-op
    ("search_accessories", {"category": "charger", "max_price": 60, "brand": "Veltro"}, True),
    ("list_expenses", {"employee_email": "priya@acme.example", "category": "meals", "min_amount": 0}, False),   # no-op bound
    ("list_expenses", {"employee_email": "priya@acme.example", "category": "meals", "min_amount": 25}, True),
    ("search_trains", {"from_station": "Lyon", "to_station": "Geneva", "travel_date": "2026-11-14", "depart_after": "00:00"}, False),
    ("search_trains", {"from_station": "Lyon", "to_station": "Geneva", "travel_date": "2026-11-14", "depart_after": "18:00"}, True),
    ("search_apartments", {"city": "Austin", "bedrooms": 2, "max_rent": 10000}, False),            # an invented cap, not the misuse
    ("search_apartments", {"city": "Austin", "bedrooms": 2, "max_rent": 2000}, True),
    ("list_folder_contents", {"folder": "/shared/exports", "older_than_days": 0}, False),
    ("list_folder_contents", {"folder": "/shared/exports", "older_than_days": 7}, True),
    ("crm_search_contacts", {"search_term": "Umbra Labs", "owner_email": ""}, True),               # absence: "" IS the misuse
    ("list_tasks", {"project_id": "PRJ-31", "due_before": "1900-01-01"}, True),                    # absence: a sentinel date
    ("query_logs", {"service": "billing", "level": "error", "since_minutes": 30, "contains": "-timeout"}, True),
    ("search_code", {"query": "parse_config", "path_prefix": ""}, False),
    ("search_code", {"query": "parse_config", "path_prefix": "src/"}, True),
    ("find_recipes", {"cuisine": "thai", "max_minutes": 30, "include_ingredients": []}, False),
    ("draft_email", {"to": ["board@northwind.example"], "cc": [], "subject": "Q3 summary", "body": "The Q3 summary is attached."}, False),
]


@pytest.mark.parametrize("tool,args,misuse", SEEN, ids=[f"{t}-{i}" for i, (t, _, _) in enumerate(SEEN)])
def test_detectors_match_the_specific_misuse(tool, args, misuse):
    item = next(it for it in REP if it["target_tool"] == tool)
    s = score_call(item, ParsedCall(ok=True, name=tool, arguments=args))
    assert s.schema_valid
    assert (s.label == "repurposed") == misuse and s.correct == (not misuse), (s.label, s.misuse_fired)
