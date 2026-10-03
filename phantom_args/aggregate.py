"""Aggregation: per model, per family, per condition, most-invented names.

Works on the raw result records written by run_local.py (one JSON object per
line). Scores are always recomputed from the saved reply text, so a change to
the parser or scorer never requires re-running any model.

Denominators (stated next to every rate):
  scored  - replies that came back complete (not truncated, no API error)
  parsed  - scored replies from which one tool call could be recovered
Phantom and enum rates use `parsed`; control score and parse failures use
`scored` (an unparseable reply to a control item is not a correct call).

CLI:
  python -m phantom_args.aggregate results/pilot_raw.jsonl \
      --items data/items.jsonl --json results/summary.json --md results/pilot_tables.md
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from .prompt import BASE_CONDITIONS, CONDITIONS, prompt_sha
from .scorer import score_response

V1_0_FAMILIES = ("conventional", "near_miss", "inexpressible", "enum_pressure", "nested", "control")
FAMILIES = V1_0_FAMILIES + ("repurposing", "matched_control")          # the last two were added in v1.1
SCHEMA_FAULTS = ("wrong_tool", "phantom_arg", "out_of_enum", "wrong_type", "missing_required", "other_invalid")
OUTCOMES = ("repurposed", "declined", "clean_call", "schema_fault", "other_wrong", "unparseable")
PHANTOM_FAMILIES = ("conventional", "near_miss", "inexpressible", "nested")
TEMPTATION_FAMILIES = ("conventional", "near_miss", "inexpressible", "enum_pressure", "nested")


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the two discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (k / n) if n else None, "lo": lo, "hi": hi}


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def load_items(path: str | Path) -> dict[str, dict]:
    items = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            it = json.loads(line)
            items[it["id"]] = it
    return items


def load_results(paths: Iterable[str | Path]) -> list[dict]:
    """Read result files; the LAST record for a (model, item, condition) wins."""
    latest: dict[tuple, dict] = {}
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue            # a half-written last line after a crash
                latest[(rec["model"], rec["item_id"], rec["condition"])] = rec
    return list(latest.values())


def rescore(records: list[dict], items: dict[str, dict]) -> list[dict]:
    """Attach a fresh `score` to every complete reply; drop records of unknown items."""
    out = []
    for rec in records:
        item = items.get(rec["item_id"])
        if item is None:
            continue
        if rec.get("prompt_sha") and rec["prompt_sha"] != prompt_sha(item, rec["condition"]):
            continue                    # recorded against an older version of this item
        rec = dict(rec)
        rec["family"] = item["family"]
        rec["core"] = bool(item.get("core"))
        rec["enum_fallback"] = item.get("enum_fallback")
        rec["misuse_item"] = bool(item.get("misuse_params"))
        rec["pattern"] = item.get("pattern")
        if rec.get("status") == "ok":
            rec["score"] = score_response(item, rec.get("content"), rec["condition"]).to_dict()
        else:
            rec["score"] = None
        out.append(rec)
    return out


# --------------------------------------------------------------------------
# cells
# --------------------------------------------------------------------------
def cell(records: list[dict]) -> dict:
    """Counts for one group of records."""
    n_total = len(records)
    n_error = sum(r["status"] == "error" for r in records)
    n_trunc = sum(r["status"] == "truncated" for r in records)
    scored = [r for r in records if r["status"] == "ok"]
    parsed = [r for r in scored if r["score"]["label"] != "unparseable"]
    labels = Counter(r["score"]["label"] for r in scored)
    return {
        "n_total": n_total,
        "n_error": n_error,
        "n_truncated": n_trunc,
        "n_scored": len(scored),
        "n_parsed": len(parsed),
        "labels": dict(labels),
        "unparseable": rate(len(scored) - len(parsed), len(scored)),
        "phantom": rate(sum("phantom_arg" in r["score"]["flags"] for r in parsed), len(parsed)),
        "out_of_enum": rate(sum("out_of_enum" in r["score"]["flags"] for r in parsed), len(parsed)),
        "invalid": rate(sum(r["score"]["label"] != "valid" for r in parsed), len(parsed)),
        "correct": rate(sum(bool(r["score"]["correct"]) for r in scored), len(scored)),
        "stuffed": rate(sum(bool(r["score"]["stuffed"]) and r["score"]["label"] == "valid" for r in parsed), len(parsed)),
        "wrong_tool": rate(sum("wrong_tool" in r["score"]["flags"] for r in parsed), len(parsed)),
        "declined": rate(sum(r["score"]["label"] == "declined" for r in scored), len(scored)),
        "format_deviation": rate(sum(bool(r["score"]["parse_notes"]) for r in parsed), len(parsed)),
    }


def _by(records, *keys):
    groups = defaultdict(list)
    for r in records:
        groups[tuple(r[k] for k in keys)].append(r)
    return groups


def phantom_key_counts(records: list[dict]) -> Counter:
    c: Counter = Counter()
    for r in records:
        if r["status"] == "ok" and r["score"]["phantom_keys"]:
            for key in sorted({p["key"].lower() for p in r["score"]["phantom_keys"]}):   # sorted: stable order for ties
                c[key] += 1
    return c


def paired_effect(records: list[dict], families=PHANTOM_FAMILIES, flag="phantom_arg") -> dict:
    """Neutral vs instructed on the same items (both replies parsed)."""
    by_item: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in records:
        if r["family"] in families and r["status"] == "ok" and r["score"]["label"] != "unparseable":
            by_item[r["item_id"]][r["condition"]] = r
    both = b = c = neither = 0
    for conds in by_item.values():
        if "neutral" not in conds or "instructed" not in conds:
            continue
        n = flag in conds["neutral"]["score"]["flags"]
        i = flag in conds["instructed"]["score"]["flags"]
        if n and i:
            both += 1
        elif n:
            b += 1
        elif i:
            c += 1
        else:
            neither += 1
    return {"pairs": both + b + c + neither, "both": both, "fixed_by_instruction": b,
            "broken_by_instruction": c, "neither": neither, "p_mcnemar": mcnemar_exact(b, c)}


def summarize(records: list[dict]) -> dict:
    models = sorted({r["model"] for r in records})
    summary: dict = {"models": {}, "families": {}, "pooled": {}, "keys": {}, "usage": {}}

    for model in models:
        mrecs = [r for r in records if r["model"] == model]
        entry: dict = {"conditions": {}, "families": {}}
        for cond in CONDITIONS:
            crecs = [r for r in mrecs if r["condition"] == cond]
            if not crecs:
                continue
            entry["conditions"][cond] = {
                "all": cell(crecs),
                "phantom_families": cell([r for r in crecs if r["family"] in PHANTOM_FAMILIES]),
                "enum_pressure": cell([r for r in crecs if r["family"] == "enum_pressure"]),
                "control": cell([r for r in crecs if r["family"] == "control"]),
                "near_miss": cell([r for r in crecs if r["family"] == "near_miss"]),
            }
            for fam in FAMILIES:
                frecs = [r for r in crecs if r["family"] == fam]
                if frecs:
                    entry["families"].setdefault(fam, {})[cond] = cell(frecs)
        entry["paired_phantom"] = paired_effect(mrecs)
        entry["paired_enum"] = paired_effect(mrecs, families=("enum_pressure",), flag="out_of_enum")
        done = [r for r in mrecs if r["status"] in ("ok", "truncated")]
        entry["usage"] = {
            "calls": len(done),
            "prompt_tokens": sum((r.get("usage") or {}).get("prompt_tokens") or 0 for r in done),
            "completion_tokens": sum((r.get("usage") or {}).get("completion_tokens") or 0 for r in done),
            "reasoning_tokens": sum((r.get("usage") or {}).get("reasoning_tokens") or 0 for r in done),
            "calls_with_reasoning": sum(bool((r.get("usage") or {}).get("reasoning_tokens")) or bool(r.get("reasoning_chars")) for r in done),
            "cost": sum(r.get("cost") or 0.0 for r in done),
            "items": len({r["item_id"] for r in mrecs}),
        }
        summary["models"][model] = entry

    for cond in CONDITIONS:
        crecs = [r for r in records if r["condition"] == cond]
        summary["pooled"][cond] = {
            "all": cell(crecs),
            "phantom_families": cell([r for r in crecs if r["family"] in PHANTOM_FAMILIES]),
            "enum_pressure": cell([r for r in crecs if r["family"] == "enum_pressure"]),
            "control": cell([r for r in crecs if r["family"] == "control"]),
        }
        for fam in FAMILIES:
            summary["families"].setdefault(fam, {})[cond] = cell([r for r in crecs if r["family"] == fam])
        temptation = [r for r in crecs if r["family"] in TEMPTATION_FAMILIES]
        counts = phantom_key_counts(temptation)
        models_per_key: dict[str, set] = defaultdict(set)
        for r in temptation:
            if r["status"] == "ok":
                for p in r["score"]["phantom_keys"]:
                    models_per_key[p["key"].lower()].add(r["model"])
        summary["keys"][cond] = [
            {"key": k, "count": n, "models": len(models_per_key[k])} for k, n in counts.most_common(40)
        ]
    summary["paired_phantom_pooled"] = paired_effect_pooled(records)
    summary["reasoning_split"] = reasoning_split(records)
    summary["v1_1"] = v1_1_summary(records)
    summary["unparseable_reasons"] = {
        cond: dict(Counter(r["score"]["parse_reason"] for r in records
                           if r["condition"] == cond and r["status"] == "ok" and r["score"]["label"] == "unparseable"))
        for cond in CONDITIONS}
    summary["unparseable_by_family"] = dict(Counter(
        r["family"] for r in records if r["status"] == "ok" and r["score"]["label"] == "unparseable"))
    summary["item_outcomes"] = item_outcomes(records)
    pooled_enum = Counter()
    for conds in summary["item_outcomes"]["enum"].values():
        for cond, d in conds.items():
            for choice, n in d["choices"].items():
                pooled_enum[(cond, d["fallback"], choice)] += n
    summary["enum_choices_pooled"] = {
        cond: {fb: {c: pooled_enum[(cond, fb, c)] for c in ("violated", "listed", "omitted", "other") if pooled_enum[(cond, fb, c)]}
               for fb in ("omit", "nearest")}
        for cond in CONDITIONS}
    return summary


def _flag_rate(records: list[dict], pred) -> dict:
    parsed = [r for r in records if r["status"] == "ok" and r["score"]["label"] != "unparseable"]
    return rate(sum(bool(pred(r["score"])) for r in parsed), len(parsed))


def reasons_by_default(mrecs: list[dict]) -> bool:
    """True if the provider returned any reasoning (tokens or text) for this model."""
    return any(bool((r.get("usage") or {}).get("reasoning_tokens")) or bool(r.get("reasoning_chars"))
               for r in mrecs if r["status"] in ("ok", "truncated"))


def reasoning_split(records: list[dict]) -> dict:
    """Pool models by whether they reasoned before answering (provider default).

    An association, not an experiment: the two groups are different models, and
    the non-reasoning ones are on the whole older. `core` restricts to the items
    every model answered, so both groups are compared on the same items.
    """
    groups: dict[str, list[str]] = {"reasoning": [], "no_reasoning": []}
    for model in sorted({r["model"] for r in records}):
        mrecs = [r for r in records if r["model"] == model]
        groups["reasoning" if reasons_by_default(mrecs) else "no_reasoning"].append(model)
    out: dict = {"models": groups, "all_items": {}, "core_items": {}}
    for scope, keep in (("all_items", lambda r: True), ("core_items", lambda r: r["core"])):
        for g, members in groups.items():
            for cond in CONDITIONS:
                recs = [r for r in records if r["model"] in members and r["condition"] == cond and keep(r)]
                out[scope].setdefault(g, {})[cond] = {
                    "phantom": cell([r for r in recs if r["family"] in PHANTOM_FAMILIES])["phantom"],
                    "out_of_enum": cell([r for r in recs if r["family"] == "enum_pressure"])["out_of_enum"],
                    "control_correct": cell([r for r in recs if r["family"] == "control"])["correct"],
                    "repurposed": _flag_rate([r for r in recs if r.get("misuse_item")],
                                             lambda sc: bool(sc["repurposed"]) and sc["schema_valid"]),
                    "enum_substituted": _flag_rate([r for r in recs if r.get("enum_fallback") == "omit"],
                                                   lambda sc: sc.get("enum_choice") == "listed"),
                }
    return out


def item_outcomes(records: list[dict]) -> dict:
    """Per-item counts of where an unexpressible request went, over models.

    repurposed  - items with `misuse_params`: schema-valid calls that put a
                  value in a parameter the request gives no value for
    stuffed     - inexpressible items: schema-valid calls with the constraint's
                  words inside a string argument
    enum        - enum_pressure items: violated / listed / omitted, and the
                  values chosen
    """
    out: dict = {"repurposed": {}, "stuffed": {}, "enum": {}}
    for (iid, cond), recs in sorted(_by(records, "item_id", "condition").items()):
        parsed = [r for r in recs if r["status"] == "ok" and r["score"]["label"] != "unparseable"]
        if not parsed:
            continue
        fam = parsed[0]["family"]
        if fam != "repurposing" and any(r["score"].get("repurposed") for r in parsed):
            k = sum(bool(r["score"]["repurposed"]) and r["score"]["schema_valid"] for r in parsed)
            out["repurposed"].setdefault(iid, {})[cond] = {
                **rate(k, len(parsed)),
                "params": dict(Counter(p for r in parsed for p in r["score"]["repurposed"])),
                "phantom": sum("phantom_arg" in r["score"]["flags"] for r in parsed),
            }
        if fam == "inexpressible":
            k = sum(bool(r["score"]["stuffed"]) and r["score"]["schema_valid"] for r in parsed)
            out["stuffed"].setdefault(iid, {})[cond] = {
                **rate(k, len(parsed)), "phantom": sum("phantom_arg" in r["score"]["flags"] for r in parsed)}
        if fam == "enum_pressure":
            choices = Counter(r["score"].get("enum_choice") or "other" for r in parsed)
            values = Counter(json.dumps(r["score"].get("enum_value"), ensure_ascii=False)
                             for r in parsed if r["score"].get("enum_choice") in ("violated", "listed"))
            out["enum"].setdefault(iid, {})[cond] = {
                "n": len(parsed), "fallback": parsed[0].get("enum_fallback"),
                "choices": dict(choices), "values": dict(values.most_common())}
    return out


def outcome(rec: dict) -> str:
    """One of OUTCOMES for a complete reply. Used for the v1.1 families."""
    sc = rec["score"]
    if sc["label"] in ("unparseable", "declined", "repurposed"):
        return sc["label"]       # repurposed = schema-valid; a misuse that also breaks the schema is a schema fault
    if sc["label"] in SCHEMA_FAULTS:
        return "schema_fault"
    return "clean_call" if sc["correct"] else "other_wrong"


def outcome_counts(records: list[dict]) -> dict:
    scored = [r for r in records if r["status"] == "ok"]
    c = Counter(outcome(r) for r in scored)
    return {"n": len(scored), **{o: c.get(o, 0) for o in OUTCOMES},
            "correct": sum(bool(r["score"]["correct"]) for r in scored),
            # a detector matched, but the call is also schema-invalid (e.g. owner_email: null): a strict tool
            # rejects it, so it is a schema fault, counted here so that it is not lost
            "schema_fault_with_misuse": sum(r["score"]["label"] in SCHEMA_FAULTS and bool(r["score"].get("misuse_fired"))
                                            for r in scored)}


def v1_1_summary(records: list[dict]) -> dict:
    """Everything about the repurposing family, the matched controls and the may_decline condition."""
    rep = [r for r in records if r["family"] == "repurposing"]
    ctl = [r for r in records if r["family"] == "matched_control"]
    out: dict = {"models": {}, "pooled": {}, "patterns": {}, "items": {}, "matched_control": {},
                 "decline_by_family": {}, "switch": {}, "reasoning": {}}
    if not rep and not any(r["condition"] == "may_decline" for r in records):
        return out
    conds = [c for c in CONDITIONS if any(r["condition"] == c for r in rep + ctl)]
    out["conditions"] = conds
    models = sorted({r["model"] for r in rep + ctl})
    reasoning = {m: reasons_by_default([r for r in records if r["model"] == m]) for m in models}
    for c in conds:
        out["pooled"][c] = outcome_counts([r for r in rep if r["condition"] == c])
        for g, flag in (("reasoning", True), ("no_reasoning", False)):
            out["reasoning"].setdefault(g, {})[c] = outcome_counts(
                [r for r in rep if r["condition"] == c and reasoning[r["model"]] is flag])
        for pat in sorted({r["pattern"] for r in rep if r["pattern"]}):
            out["patterns"].setdefault(pat, {})[c] = outcome_counts(
                [r for r in rep if r["condition"] == c and r["pattern"] == pat])
        for iid in sorted({r["item_id"] for r in rep}):
            out["items"].setdefault(iid, {})[c] = outcome_counts(
                [r for r in rep if r["condition"] == c and r["item_id"] == iid])
    for m in models:
        out["models"][m] = {"reasoning": reasoning[m],
                            "repurposing": {c: outcome_counts([r for r in rep if r["model"] == m and r["condition"] == c]) for c in conds},
                            "matched_control": {c: outcome_counts([r for r in ctl if r["model"] == m and r["condition"] == c]) for c in conds}}
    for c in conds:
        out["matched_control"][c] = outcome_counts([r for r in ctl if r["condition"] == c])
    # how often a decline is used, per family, when it is allowed
    md = [r for r in records if r["condition"] == "may_decline" and r["status"] == "ok"]
    for fam in FAMILIES:
        fr = [r for r in md if r["family"] == fam]
        if fr:
            out["decline_by_family"][fam] = {**rate(sum(r["score"]["label"] == "declined" for r in fr), len(fr)),
                                             "correct": rate(sum(bool(r["score"]["correct"]) for r in fr), len(fr))}
    # same model, same item: what the must-call outcome turns into when a decline is allowed
    pairs: dict = defaultdict(dict)
    for r in rep:
        if r["status"] == "ok" and r["condition"] in ("neutral", "may_decline"):
            pairs[(r["model"], r["item_id"])][r["condition"]] = outcome(r)
    sw = Counter((p["neutral"], p["may_decline"]) for p in pairs.values() if len(p) == 2)
    out["switch"] = {"pairs": sum(sw.values()), "table": {f"{a} -> {b}": n for (a, b), n in sorted(sw.items(), key=lambda t: -t[1])}}
    b = sum(n for (a, bb), n in sw.items() if a == "repurposed" and bb != "repurposed")
    cc = sum(n for (a, bb), n in sw.items() if a != "repurposed" and bb == "repurposed")
    out["switch"].update({"repurposed_only_when_must_call": b, "repurposed_only_when_may_decline": cc,
                          "p_mcnemar": mcnemar_exact(b, cc)})
    return out


def paired_effect_pooled(records: list[dict]) -> dict:
    tot = Counter()
    for model in sorted({r["model"] for r in records}):
        pe = paired_effect([r for r in records if r["model"] == model])
        for k in ("pairs", "both", "fixed_by_instruction", "broken_by_instruction", "neither"):
            tot[k] += pe[k]
    d = dict(tot)
    d["p_mcnemar"] = mcnemar_exact(tot["fixed_by_instruction"], tot["broken_by_instruction"])
    return d


# --------------------------------------------------------------------------
# markdown
# --------------------------------------------------------------------------
def pct(r: dict, digits: int = 1) -> str:
    if not r["n"]:
        return "n/a"
    return f"{100 * r['rate']:.{digits}f}% ({r['k']}/{r['n']})"


def pct_ci(r: dict) -> str:
    if not r["n"]:
        return "n/a"
    return f"{100 * r['rate']:.1f}% ({r['k']}/{r['n']}; 95% CI {100 * r['lo']:.0f}–{100 * r['hi']:.0f}%)"


def short(model: str) -> str:
    return model.split("/", 1)[-1]


def _oc(d: dict, key: str) -> str:
    return f"{100 * d[key] / d['n']:.1f}% ({d[key]}/{d['n']})" if d and d["n"] else "n/a"


def render_v1_1(v: dict) -> list[str]:
    """Tables for the repurposing family, its matched controls and the may_decline condition."""
    if not v.get("models"):
        return []
    conds = v["conditions"]
    names = {"neutral": "must call", "instructed": "must call + instruction", "may_decline": "may decline"}
    L = ["### v1.1: repurposing, per model\n",
         "Share of complete replies. Repurposed = schema-valid call that puts the request into a parameter that means "
         "something else (the item's detector matched). Clean call = valid call without the misuse that gets the "
         "expressible parts right. Matched controls are requests for which that same parameter is the right one.\n",
         "| Model | Reasoned | Condition | Repurposed | Declined | Clean call | Schema fault | Unparseable | Matched controls correct | Matched controls declined |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    order = sorted(v["models"], key=lambda m: (v["models"][m]["reasoning"], m))
    for m in order:
        e = v["models"][m]
        for c in conds:
            d, k = e["repurposing"].get(c), e["matched_control"].get(c)
            if not d or not d["n"]:
                continue
            L.append(f"| {short(m)} | {'yes' if e['reasoning'] else 'no'} | {names.get(c, c)} | {_oc(d, 'repurposed')} | {_oc(d, 'declined')} | "
                     f"{_oc(d, 'clean_call')} | {_oc(d, 'schema_fault')} | {_oc(d, 'unparseable')} | {_oc(k, 'correct')} | {_oc(k, 'declined')} |")
    L.append("\n### v1.1: repurposing, pooled\n")
    L.append("| Group | Condition | Repurposed | Declined | Clean call | Schema fault | Other wrong | Unparseable |")
    L.append("|---|---|---|---|---|---|---|---|")
    groups = [("all models", v["pooled"])] + [(g.replace("_", " "), v["reasoning"].get(g, {})) for g in ("no_reasoning", "reasoning")]
    groups += [(f"pattern: {p}", d) for p, d in v["patterns"].items()]
    for label, by_cond in groups:
        for c in conds:
            d = by_cond.get(c)
            if d and d["n"]:
                L.append(f"| {label} | {names.get(c, c)} | {_oc(d, 'repurposed')} | {_oc(d, 'declined')} | {_oc(d, 'clean_call')} | "
                         f"{_oc(d, 'schema_fault')} | {_oc(d, 'other_wrong')} | {_oc(d, 'unparseable')} |")
    both = {c: v["pooled"][c].get("schema_fault_with_misuse", 0) for c in conds if v["pooled"].get(c)}
    if any(both.values()):
        L.append("\nSchema faults in which a detector also matched (counted as schema faults, since a strict tool rejects "
                 "them): " + "; ".join(f"{names.get(c, c)}: {n}" for c, n in both.items()) + ".")
    mc = v["matched_control"]
    L.append("\nMatched controls, all models: " + "; ".join(
        f"{names.get(c, c)}: correct {_oc(mc[c], 'correct')}, declined {_oc(mc[c], 'declined')}, flagged as repurposed {_oc(mc[c], 'repurposed')}"
        for c in conds if mc.get(c) and mc[c]["n"]) + ".")
    sw = v.get("switch") or {}
    if sw.get("pairs"):
        L.append(f"\nSame model and item, must call -> may decline ({sw['pairs']} pairs): " +
                 "; ".join(f"{k}: {n}" for k, n in sw["table"].items()) + ".")
        L.append(f"Repurposed only when it had to call: {sw['repurposed_only_when_must_call']}. Repurposed only when it could decline: "
                 f"{sw['repurposed_only_when_may_decline']}. Exact McNemar p "
                 + (f"= {sw['p_mcnemar']:.4f}." if sw['p_mcnemar'] >= 0.0001 else "< 0.0001."))
    if v.get("decline_by_family"):
        L.append("\n### v1.1: how often a decline is used when it is allowed\n")
        L.append("| Family | Declining is | Declined | Correct |")
        L.append("|---|---|---|---|")
        wrong = ("near_miss", "control", "matched_control")
        for fam, d in v["decline_by_family"].items():
            L.append(f"| {fam} | {'wrong' if fam in wrong else 'accepted'} | {pct(d)} | {pct(d['correct'])} |")
    L.append("\n### v1.1: repurposing, per item (models that repurposed / complete replies)\n")
    L.append("| Item | " + " | ".join(names.get(c, c) for c in conds) + " | Declined when allowed |")
    L.append("|---|" + "---|" * (len(conds) + 1))
    for iid, by_cond in v["items"].items():
        cells = [f"{by_cond[c]['repurposed']}/{by_cond[c]['n']}" if by_cond.get(c) and by_cond[c]["n"] else "n/a" for c in conds]
        dd = by_cond.get("may_decline")
        tail = f"{dd['declined']}/{dd['n']}" if dd and dd["n"] else "n/a"
        L.append(f"| {iid} | " + " | ".join(cells) + f" | {tail} |")
    L.append("")
    return L


def render_markdown(summary: dict) -> str:
    L: list[str] = []
    models = summary["models"]

    def cond(m, c, group):
        return models[m]["conditions"].get(c, {}).get(group)

    def neutral_phantom(m):
        g = cond(m, "neutral", "phantom_families")
        return g["phantom"]["rate"] if g and g["phantom"]["n"] else -1.0

    order = sorted(models, key=lambda m: (-neutral_phantom(m), m))

    L.append("### Per model\n")
    L.append("Phantom rate = share of parsed replies with at least one argument name the schema does not define, "
             "over the four phantom families (conventional, near-miss, inexpressible, nested). "
             "Control score = share of control items answered with a schema-valid call that uses the existing parameter correctly. "
             "Counts are k/n.\n")
    L.append("| Model | Items | Phantom, neutral | Phantom, instructed | Paired p | Enum violations, neutral | Enum violations, instructed | Control score, neutral | Control score, instructed | Unparseable (both) | Truncated |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for m in order:
        e = models[m]
        row = [short(m), str(e["usage"]["items"])]
        for c in BASE_CONDITIONS:
            g = cond(m, c, "phantom_families")
            row.append(pct(g["phantom"]) if g else "n/a")
        pe = e["paired_phantom"]
        row.append(f"{pe['p_mcnemar']:.3f} ({pe['fixed_by_instruction']} fixed / {pe['broken_by_instruction']} broken)")
        for c in BASE_CONDITIONS:
            g = cond(m, c, "enum_pressure")
            row.append(pct(g["out_of_enum"]) if g else "n/a")
        for c in BASE_CONDITIONS:
            g = cond(m, c, "control")
            row.append(pct(g["correct"]) if g else "n/a")
        k = sum(cond(m, c, "all")["unparseable"]["k"] for c in BASE_CONDITIONS if cond(m, c, "all"))
        n = sum(cond(m, c, "all")["unparseable"]["n"] for c in BASE_CONDITIONS if cond(m, c, "all"))
        row.append(f"{k}/{n}")
        row.append(str(sum(cond(m, c, "all")["n_truncated"] for c in BASE_CONDITIONS if cond(m, c, "all"))))
        L.append("| " + " | ".join(row) + " |")

    ur = summary.get("unparseable_reasons") or {}
    if any(ur.values()):
        names = {"no_json": "answered in prose, no call", "multiple_calls": "two different calls",
                 "malformed_json": "broken JSON", "not_a_tool_call": "JSON that is not a call",
                 "empty": "empty reply", "arguments_not_object": "arguments not an object"}
        L.append("\nUnparseable replies by reason: " + "; ".join(
            f"{c}: " + (", ".join(f"{names.get(k, k)} {v}" for k, v in sorted(ur[c].items(), key=lambda t: -t[1])) or "none")
            for c in CONDITIONS if c in BASE_CONDITIONS or ur.get(c)) + ". By family: " + ", ".join(
            f"{k} {v}" for k, v in sorted(summary["unparseable_by_family"].items(), key=lambda t: -t[1])) + ".")
    L.append("\n### Per family, all models pooled\n")
    L.append("| Family | Target fault | Neutral | Instructed | Any schema violation, neutral | Any schema violation, instructed |")
    L.append("|---|---|---|---|---|---|")
    for fam in V1_0_FAMILIES:
        f = summary["families"][fam]
        if fam == "control":
            L.append(f"| control | (correct call) | {pct_ci(f['neutral']['correct'])} | {pct_ci(f['instructed']['correct'])} | "
                     f"{pct(f['neutral']['invalid'])} | {pct(f['instructed']['invalid'])} |")
            continue
        key = "out_of_enum" if fam == "enum_pressure" else "phantom"
        L.append(f"| {fam} | {key.replace('phantom', 'phantom_arg')} | {pct_ci(f['neutral'][key])} | {pct_ci(f['instructed'][key])} | "
                 f"{pct(f['neutral']['invalid'])} | {pct(f['instructed']['invalid'])} |")

    L.append("\n### Per family and model, neutral → instructed (target-fault rate, k/n)\n")
    fams = [f for f in V1_0_FAMILIES if f != "control"]
    L.append("| Model | " + " | ".join(fams) + " |")
    L.append("|---|" + "---|" * len(fams))
    for m in order:
        row = [short(m)]
        for fam in fams:
            key = "out_of_enum" if fam == "enum_pressure" else "phantom"
            cells = models[m]["families"].get(fam, {})
            parts = []
            for c in BASE_CONDITIONS:
                if c in cells:
                    r = cells[c][key]
                    parts.append(f"{r['k']}/{r['n']}")
                else:
                    parts.append("n/a")
            row.append(" → ".join(parts))
        L.append("| " + " | ".join(row) + " |")

    L.append("\n### Most-invented argument names (temptation items, all models)\n")
    for c in CONDITIONS:
        if c in BASE_CONDITIONS or summary["keys"][c]:
            L.append(f"**{c}**: " + ", ".join(f"`{k['key']}` ×{k['count']} ({k['models']} models)" for k in summary["keys"][c][:25]) + "\n")

    rs = summary.get("reasoning_split")
    if rs and rs["models"]["reasoning"] and rs["models"]["no_reasoning"]:
        L.append("### Models that reasoned before answering vs models that did not\n")
        L.append("Grouped by whether the provider returned any reasoning at its default setting. "
                 "The groups are different models, so this is an association, not the effect of reasoning. "
                 "Core items are the 60 that every model answered.\n")
        L.append(f"- No reasoning ({len(rs['models']['no_reasoning'])}): " + ", ".join(short(m) for m in rs["models"]["no_reasoning"]))
        L.append(f"- Reasoning ({len(rs['models']['reasoning'])}): " + ", ".join(short(m) for m in rs["models"]["reasoning"]) + "\n")
        L.append("| Items | Group | Phantom, neutral | Phantom, instructed | Enum violations, neutral | Enum violations, instructed | Control score, neutral |")
        L.append("|---|---|---|---|---|---|---|")
        for scope, label in (("all_items", "all answered"), ("core_items", "core 60")):
            for g, glabel in (("no_reasoning", "no reasoning"), ("reasoning", "reasoning")):
                d = rs[scope][g]
                L.append(f"| {label} | {glabel} | {pct_ci(d['neutral']['phantom'])} | {pct_ci(d['instructed']['phantom'])} | "
                         f"{pct_ci(d['neutral']['out_of_enum'])} | {pct_ci(d['instructed']['out_of_enum'])} | {pct(d['neutral']['control_correct'])} |")
        L.append("")
        L.append("Schema-valid ways of getting it wrong, same grouping (all answered items). Repurposed = a value in a parameter "
                 "that means something else (items with `misuse_params`). Substituted = on enum items where no listed value "
                 "means what the user asked, a listed value was sent anyway.\n")
        L.append("| Group | Repurposed, neutral | Repurposed, instructed | Enum substituted, neutral | Enum substituted, instructed |")
        L.append("|---|---|---|---|---|")
        for g, glabel in (("no_reasoning", "no reasoning"), ("reasoning", "reasoning")):
            d = rs["all_items"][g]
            L.append(f"| {glabel} | {pct_ci(d['neutral']['repurposed'])} | {pct_ci(d['instructed']['repurposed'])} | "
                     f"{pct_ci(d['neutral']['enum_substituted'])} | {pct_ci(d['instructed']['enum_substituted'])} |")
        L.append("")

    io = summary.get("item_outcomes") or {}
    if io.get("repurposed"):
        L.append("### Schema-valid calls that put the constraint in a parameter meaning something else\n")
        L.append("Items whose tool has a parameter that can absorb the request but means something different. "
                 "k/n = models whose call was schema-valid and gave that parameter a value, over models with a parsed reply.\n")
        L.append("| Item | Parameter | Neutral | Instructed | Phantom instead (neutral) |")
        L.append("|---|---|---|---|---|")
        for iid, conds in io["repurposed"].items():
            params = sorted({p for d in conds.values() for p in d["params"]})
            cells = [pct(conds[c]) if c in conds else "0" for c in CONDITIONS]
            ph = conds.get("neutral", {}).get("phantom", 0)
            L.append(f"| {iid} | `{', '.join(params)}` | {cells[0]} | {cells[1]} | {ph} |")
        L.append("")
    if io.get("stuffed"):
        rows = [(iid, conds) for iid, conds in io["stuffed"].items() if any(d["k"] for d in conds.values())]
        rows.sort(key=lambda t: -(t[1].get("neutral", {}).get("rate") or 0))
        L.append("### Inexpressible items: constraint words written into a string argument (schema-valid)\n")
        L.append("| Item | Neutral | Instructed |")
        L.append("|---|---|---|")
        for iid, conds in rows:
            L.append(f"| {iid} | " + " | ".join(pct(conds[c], 0) if c in conds else "n/a" for c in BASE_CONDITIONS) + " |")
        L.append("")
    if io.get("enum"):
        ep = summary["enum_choices_pooled"]
        L.append("### Enum-pressure items: what happened to the enum parameter\n")
        L.append("violated = a value outside the enum; listed = a listed value the user did not name; omitted = parameter left out. "
                 "Items are split by what a valid call can do: `nearest` (a listed value is a fair stand-in, e.g. high for critical) "
                 "and `omit` (no listed value means what the user asked, so leaving the parameter out is the faithful valid call).\n")
        for c in BASE_CONDITIONS:
            for fb in ("nearest", "omit"):
                d = ep[c].get(fb) or {}
                tot = sum(d.values())
                if tot:
                    L.append(f"- {c}, `{fb}` items: " + ", ".join(f"{k} {v}/{tot} ({100 * v / tot:.1f}%)" for k, v in d.items()))
        L.append("")
        L.append("Neutral condition, values with counts:\n")
        L.append("| Item | Fallback | n | Violated | Listed | Omitted | Values chosen |")
        L.append("|---|---|---|---|---|---|---|")
        for iid, conds in io["enum"].items():
            d = conds.get("neutral")
            if not d:
                continue
            ch = d["choices"]
            vals = ", ".join(f"`{v}` ×{n}" for v, n in d["values"].items())
            L.append(f"| {iid} | {d['fallback']} | {d['n']} | {ch.get('violated', 0)} | {ch.get('listed', 0)} | {ch.get('omitted', 0)} | {vals} |")
        L.append("")

    L.extend(render_v1_1(summary.get("v1_1") or {}))

    L.append("### Usage\n")
    L.append("| Model | Calls | Prompt tokens | Completion tokens | Reasoning tokens reported | Calls with reasoning | Cost (USD) |")
    L.append("|---|---|---|---|---|---|---|")
    tot = Counter()
    for m in sorted(models):
        u = models[m]["usage"]
        L.append(f"| {short(m)} | {u['calls']} | {u['prompt_tokens']:,} | {u['completion_tokens']:,} | {u['reasoning_tokens']:,} | {u['calls_with_reasoning']} | {u['cost']:.4f} |")
        for k in ("calls", "prompt_tokens", "completion_tokens", "reasoning_tokens"):
            tot[k] += u[k]
        tot["cost"] += u["cost"]
    L.append(f"| **total** | {tot['calls']} | {tot['prompt_tokens']:,} | {tot['completion_tokens']:,} | {tot['reasoning_tokens']:,} | | {tot['cost']:.4f} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", nargs="+")
    ap.add_argument("--items", default="data/items.jsonl")
    ap.add_argument("--json")
    ap.add_argument("--md")
    args = ap.parse_args(argv)
    items = load_items(args.items)
    records = rescore(load_results(args.results), items)
    summary = summarize(records)
    md = render_markdown(summary)
    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=1), encoding="utf-8")
    if args.md:
        Path(args.md).write_text(md, encoding="utf-8")
    else:
        print(md)


if __name__ == "__main__":
    main()
