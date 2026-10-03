"""Aggregation over a small synthetic result set (no network, no model)."""
import json

from phantom_args import aggregate as agg
from phantom_args.prompt import CONDITIONS, prompt_sha

ITEMS = agg.load_items("data/items.jsonl")


def call(item, args):
    return json.dumps({"name": item["target_tool"], "arguments": args})


def record(model, item, cond, args, reasoning=0):
    return {"model": model, "item_id": item["id"], "condition": cond, "status": "ok",
            "content": call(item, args), "prompt_sha": prompt_sha(item, cond),
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "reasoning_tokens": reasoning},
            "reasoning_chars": reasoning, "cost": 0.0}


def synthetic():
    """Model `plain` falls for every trap and does not reason; model `think` answers with the reference and reasons."""
    recs = []
    for item in ITEMS.values():
        for cond in CONDITIONS:
            trap = item["trap"]["arguments"] if item["trap"] else item["reference"]["arguments"]
            recs.append(record("x/plain", item, cond, trap))
            recs.append(record("x/think", item, cond, item["reference"]["arguments"], reasoning=40))
    return agg.rescore(recs, ITEMS)


def test_wilson_and_mcnemar_basics():
    lo, hi = agg.wilson(0, 100)
    assert lo == 0.0 and 0.03 < hi < 0.04
    assert agg.wilson(0, 0) == (0.0, 1.0)      # no data: the whole interval
    assert agg.mcnemar_exact(0, 0) == 1.0
    assert agg.mcnemar_exact(5, 0) == 0.0625
    assert agg.mcnemar_exact(3, 2) == 1.0


def test_stale_and_unknown_records_are_dropped():
    item = ITEMS["ctrl-01"]
    good = record("m", item, "neutral", item["reference"]["arguments"])
    stale = dict(good, condition="instructed", prompt_sha="000000000000")
    unknown = dict(good, item_id="gone-99")
    assert [r["condition"] for r in agg.rescore([good, stale, unknown], ITEMS)] == ["neutral"]


def test_last_record_per_key_wins(tmp_path):
    item = ITEMS["ctrl-01"]
    first = dict(record("m", item, "neutral", {}), status="truncated")
    second = record("m", item, "neutral", item["reference"]["arguments"])
    path = tmp_path / "r.jsonl"
    path.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n" + '{"model": "m", "item_')
    loaded = agg.load_results([path])
    assert len(loaded) == 1 and loaded[0]["status"] == "ok"


def test_summary_on_synthetic_models():
    summary = agg.summarize(synthetic())
    plain = summary["models"]["x/plain"]["conditions"]["neutral"]
    think = summary["models"]["x/think"]["conditions"]["neutral"]
    n_phantom = sum(it["family"] in agg.PHANTOM_FAMILIES for it in ITEMS.values())
    assert plain["phantom_families"]["phantom"] == {**plain["phantom_families"]["phantom"], "k": n_phantom, "n": n_phantom}
    assert think["phantom_families"]["phantom"]["k"] == 0
    assert plain["enum_pressure"]["out_of_enum"]["k"] == 25 and think["enum_pressure"]["out_of_enum"]["k"] == 0
    assert plain["control"]["correct"]["k"] == think["control"]["correct"]["k"] == 32
    # the instruction changes nothing for either synthetic model
    assert summary["models"]["x/plain"]["paired_phantom"]["fixed_by_instruction"] == 0
    assert summary["models"]["x/plain"]["paired_phantom"]["both"] == n_phantom


def test_reasoning_split_groups_models_by_returned_reasoning():
    rs = agg.summarize(synthetic())["reasoning_split"]
    assert rs["models"] == {"reasoning": ["x/think"], "no_reasoning": ["x/plain"]}
    assert rs["all_items"]["no_reasoning"]["neutral"]["out_of_enum"]["rate"] == 1.0
    assert rs["all_items"]["reasoning"]["neutral"]["out_of_enum"]["rate"] == 0.0
    assert rs["core_items"]["reasoning"]["neutral"]["phantom"]["n"] == 40
    assert rs["core_items"]["no_reasoning"]["neutral"]["out_of_enum"]["n"] == 10


def test_item_outcomes_enum_and_repurposed():
    recs = synthetic()
    bcc = next(it for it in ITEMS.values() if it["misuse_params"] == ["cc"])
    extra = record("x/cc", bcc, "neutral", dict(bcc["reference"]["arguments"], cc=["legal@acme.example"]))
    io = agg.summarize(recs + agg.rescore([extra], ITEMS))["item_outcomes"]
    d = io["repurposed"][bcc["id"]]["neutral"]
    assert (d["k"], d["n"], d["params"], d["phantom"]) == (1, 3, {"cc": 1}, 1)
    e = io["enum"]["enum-02"]["neutral"]
    assert e["n"] == 2 and e["choices"] == {"violated": 1, "listed": 1} and e["fallback"] == "nearest"
    assert e["values"] == {'"critical"': 1, '"high"': 1}


def test_markdown_renders_every_section():
    md = agg.render_markdown(agg.summarize(synthetic()))
    for heading in ("### Per model", "### Per family, all models pooled", "### Models that reasoned",
                    "### Enum-pressure items", "### Most-invented argument names", "### Usage"):
        assert heading in md
    assert "plain" in md and "think" in md


def test_misuse_that_breaks_the_schema_is_a_schema_fault_and_is_counted():
    import json as _json
    from pathlib import Path as _Path
    from phantom_args import aggregate as _agg
    items = {}
    for line in (_Path(__file__).resolve().parent.parent / "data" / "items.jsonl").read_text(encoding="utf-8").splitlines():
        it = _json.loads(line)
        items[it["id"]] = it
    item = next(it for it in items.values() if it["family"] == "repurposing" and it["target_tool"] == "crm_search_contacts")
    from phantom_args.prompt import prompt_sha as _sha

    def rec(args):
        return {"model": "m", "item_id": item["id"], "family": "repurposing", "condition": "neutral", "status": "ok",
                "prompt_sha": _sha(item, "neutral"),
                "content": _json.dumps({"name": "crm_search_contacts", "arguments": args})}

    scored = _agg.rescore([rec({"search_term": "Umbra Labs", "owner_email": None}),
                           rec({"search_term": "Umbra Labs", "owner_email": ""})], items)
    assert [_agg.outcome(r) for r in scored] == ["schema_fault", "repurposed"]
    counts = _agg.outcome_counts(scored)
    assert counts["schema_fault"] == 1 and counts["repurposed"] == 1 and counts["schema_fault_with_misuse"] == 1
