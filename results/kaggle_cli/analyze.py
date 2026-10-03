"""Tables for the Kaggle runs (Kaggle CLI flow). Run from the project root:

    .venv/bin/python results/kaggle_cli/analyze.py

Input: results/kaggle_cli/raw/<task>/<version>/<model>/<run_id>/ as written by
    kaggle b t download phantom-args-<condition> -o results/kaggle_cli/raw
For every (task, model) the highest task version that has a records file is used, and in it the latest run.
Output (results/kaggle_cli/):
    kaggle_raw.jsonl     one record per model, item and condition (the notebook's own record format, plus
                         kaggle_task / kaggle_version / kaggle_run_id)
    runs.json            per run: task score reported by Kaggle, recomputed score, items answered, cost
    kaggle_tables.md     the project's standard report (phantom_args.aggregate) over all Kaggle records
    kaggle_summary.json  the same as JSON
    post_tables.md       the tables the DEV post needs
Scores are recomputed from the saved reply text with the project's scorer, exactly as for the local runs.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from phantom_args.aggregate import (FAMILIES, PHANTOM_FAMILIES, cell, load_items, load_results, mcnemar_exact,  # noqa: E402
                                    outcome, outcome_counts, render_markdown, rescore, summarize)

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
N_ITEMS = 202
TASK_CONDITION = {"phantom-args-neutral": "neutral", "phantom-args-instructed": "instructed",
                  "phantom-args-may-decline": "may_decline"}
CONDS = ("neutral", "instructed", "may_decline")
CANNOT = ("conventional", "inexpressible", "enum_pressure", "nested", "repurposing")   # declining is right
CAN = ("control", "matched_control", "near_miss")                                       # declining is wrong


def pick_runs() -> dict:
    """(condition, model) -> run directory: highest version with records, then the latest run id."""
    best = {}
    for d in glob.glob(str(RAW / "*" / "*" / "*" / "*")):
        task, version, model, run_id = Path(d).parts[-4:]
        if task not in TASK_CONDITION or not os.path.exists(os.path.join(d, "phantom_records.jsonl")):
            continue
        key = (TASK_CONDITION[task], model)
        rank = (int(version) if version.isdigit() else -1, int(run_id) if run_id.isdigit() else -1)
        if key not in best or rank > best[key][0]:
            best[key] = (rank, d, task, version, run_id)
    return {k: v[1:] for k, v in best.items()}


def lab(model: str) -> str:
    vendor = model.split("/", 1)[0]
    return {"google": "Google", "openai": "OpenAI", "anthropic": "Anthropic", "xai": "xAI", "zai": "Z.ai",
            "deepseek-ai": "DeepSeek", "qwen": "Qwen"}.get(vendor, vendor)


def short(model: str) -> str:
    return model.split("/", 1)[-1].split("@")[0]


def pct(k: int, n: int) -> str:
    return f"{100 * k / n:.1f}% ({k}/{n})" if n else "n/a"


def main() -> None:
    items = load_items(ROOT / "data" / "items.jsonl")
    runs = pick_runs()
    if not runs:
        sys.exit("no runs under " + str(RAW))
    merged, run_info = [], []
    for (cond, model_dir), (d, task, version, run_id) in sorted(runs.items()):
        recs = [json.loads(line) for line in open(os.path.join(d, "phantom_records.jsonl"), encoding="utf-8") if line.strip()]
        for r in recs:
            r.update(kaggle_task=task, kaggle_version=version, kaggle_run_id=run_id)
        merged.extend(recs)
        res = glob.glob(os.path.join(d, "*.result.json"))
        reported = json.load(open(res[0]))["verifier_result"]["rewards"]["score"] if res else None
        model = recs[0]["model"] if recs else model_dir
        scored = rescore(recs, items)
        ok = [r for r in scored if r["status"] == "ok"]
        outs = [(r.get("usage") or {}).get("completion_tokens") or 0 for r in recs]
        run_info.append({"condition": cond, "model": model, "task": task, "version": version, "run_id": run_id,
                         "answered": len({r["item_id"] for r in recs}), "truncated": sum(bool(r.get("truncated")) for r in recs),
                         "empty": sum(not str(r.get("content") or "").strip() for r in recs),
                         "max_tokens": sorted({r.get("max_tokens") for r in recs}, key=str),
                         "correct": sum(bool(r["score"]["correct"]) for r in ok), "scored": len(ok),
                         "kaggle_score": reported, "cost": round(sum(r.get("cost") or 0 for r in recs), 4),
                         "mean_out": round(sum(outs) / len(outs)) if outs else None, "max_out": max(outs) if outs else None})
    with open(HERE / "kaggle_raw.jsonl", "w", encoding="utf-8") as fh:
        for r in merged:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (HERE / "runs.json").write_text(json.dumps(run_info, indent=1), encoding="utf-8")

    records = rescore(load_results([HERE / "kaggle_raw.jsonl"]), items)
    summary = summarize(records)
    (HERE / "kaggle_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    (HERE / "kaggle_tables.md").write_text(render_markdown(summary), encoding="utf-8")

    by = defaultdict(list)                       # (model, condition) -> complete replies
    for r in records:
        if r["status"] == "ok":
            by[(r["model"], r["condition"])].append(r)
    models = sorted({m for m, _ in by}, key=lambda m: (lab(m), m))
    L = ["# Kaggle runs: tables for the post", "",
         "Generated by results/kaggle_cli/analyze.py from the runs downloaded with the Kaggle CLI. Every score is "
         "recomputed from the saved reply text with the project's scorer; `Kaggle score` is the number the task "
         "itself reported on Kaggle (same formula: correct / answered). One sample per item, temperature 0, "
         "reasoning at the provider default. Kaggle does not return reasoning text, so hidden reasoning shows up "
         "only as output tokens.", ""]

    L += ["## Runs", "", "| Model | Lab | Condition | Task version | Run | Answered | Kaggle score | Recomputed correct | "
          "Truncated | Mean / max output tokens | Cost |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    tot_cost, tot_calls = 0.0, 0
    for ri in sorted(run_info, key=lambda x: (lab(x["model"]), x["model"], CONDS.index(x["condition"]))):
        tot_cost += ri["cost"]
        tot_calls += ri["answered"]
        ks = f"{100 * ri['kaggle_score']:.1f}%" if ri["kaggle_score"] is not None else "n/a"
        L.append(f"| {short(ri['model'])} | {lab(ri['model'])} | {ri['condition']} | {ri['version']} | {ri['run_id']} | "
                 f"{ri['answered']}/{N_ITEMS} | {ks} | {pct(ri['correct'], ri['scored'])} | {ri['truncated']} | "
                 f"{ri['mean_out']} / {ri['max_out']} | ${ri['cost']:.4f} |")
    L += ["", f"Total: {tot_calls} replies, ${tot_cost:.4f} reported by Kaggle's model proxy (the runs above only; "
          "test tasks and superseded runs are not included).", ""]

    def stat(m, c):
        recs = by.get((m, c), [])
        rep = [r for r in recs if r["family"] == "repurposing"]
        oc = outcome_counts(rep)
        ph = cell([r for r in recs if r["family"] in PHANTOM_FAMILIES])["phantom"]
        en = cell([r for r in recs if r["family"] == "enum_pressure"])["out_of_enum"]
        ctl = [r for r in recs if r["family"] in ("control", "matched_control")]
        cannot = [r for r in recs if r["family"] in CANNOT]
        can = [r for r in recs if r["family"] in CAN]
        return {"n": len(recs), "correct": sum(bool(r["score"]["correct"]) for r in recs), "rep": oc,
                "phantom": ph, "enum": en,
                "ctl": (sum(bool(r["score"]["correct"]) for r in ctl), len(ctl)),
                "decl_right": (sum(r["score"]["label"] == "declined" for r in cannot), len(cannot)),
                "decl_wrong": (sum(r["score"]["label"] == "declined" for r in can), len(can)),
                "unparseable": sum(r["score"]["label"] == "unparseable" for r in recs)}

    L += ["## Per model, all three conditions", "",
          "Correct = the task's score. Phantom = parsed replies with an argument name the schema does not define, "
          "on the four phantom families (conventional, near_miss, inexpressible, nested). Enum = parsed replies on "
          "enum_pressure with a value not on the list. Repurposed = schema-valid call that puts the request into a "
          "parameter that means something else, on the 28 repurposing items. Controls = control + matched_control "
          "answered correctly. Declined: right = on families the tool cannot serve (conventional, inexpressible, "
          "enum_pressure, nested, repurposing); wrong = on control, matched_control, near_miss.", "",
          "| Model | Condition | Correct | Phantom | Enum | Repurposed | Controls | Unparseable | Declined (right) | Declined (wrong) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    pooled = defaultdict(Counter)
    for m in models:
        for c in CONDS:
            if (m, c) not in by:
                continue
            s = stat(m, c)
            ph, en, oc = s["phantom"], s["enum"], s["rep"]
            for k, v in (("n", s["n"]), ("correct", s["correct"]), ("ph_k", ph["k"]), ("ph_n", ph["n"]),
                         ("en_k", en["k"]), ("en_n", en["n"]), ("rep_k", oc["repurposed"]), ("rep_n", oc["n"]),
                         ("ctl_k", s["ctl"][0]), ("ctl_n", s["ctl"][1]), ("dr_k", s["decl_right"][0]),
                         ("dr_n", s["decl_right"][1]), ("dw_k", s["decl_wrong"][0]), ("dw_n", s["decl_wrong"][1]),
                         ("unp", s["unparseable"])):
                pooled[c][k] += v
            md = c == "may_decline"
            L.append(f"| {short(m)} | {c} | {pct(s['correct'], s['n'])} | {pct(ph['k'], ph['n'])} | {pct(en['k'], en['n'])} | "
                     f"{pct(oc['repurposed'], oc['n'])} | {pct(*s['ctl'])} | {s['unparseable']} | "
                     f"{pct(*s['decl_right']) if md else '-'} | {pct(*s['decl_wrong']) if md else '-'} |")
    L += ["", "Pooled over the models in each condition:", ""]
    for c in CONDS:
        p = pooled.get(c)
        if not p:
            continue
        L.append(f"- {c}: correct {pct(p['correct'], p['n'])}; phantom {pct(p['ph_k'], p['ph_n'])}; enum "
                 f"{pct(p['en_k'], p['en_n'])}; repurposed {pct(p['rep_k'], p['rep_n'])}; controls "
                 f"{pct(p['ctl_k'], p['ctl_n'])}; unparseable {p['unp']}"
                 + (f"; declined right {pct(p['dr_k'], p['dr_n'])}, declined wrong {pct(p['dw_k'], p['dw_n'])}"
                    if c == "may_decline" else ""))

    # paired: same model and item, neutral vs the other two conditions, repurposing family
    L += ["", "## Paired comparisons on the repurposing family (same model, same item)", ""]
    for other in ("may_decline", "instructed"):
        sw, b, cc = Counter(), 0, 0
        per_model = {}
        for m in models:
            a = {r["item_id"]: outcome(r) for r in by.get((m, "neutral"), []) if r["family"] == "repurposing"}
            o = {r["item_id"]: outcome(r) for r in by.get((m, other), []) if r["family"] == "repurposing"}
            common = sorted(set(a) & set(o))
            if not common:
                continue
            mb = sum(a[i] == "repurposed" and o[i] != "repurposed" for i in common)
            mc = sum(a[i] != "repurposed" and o[i] == "repurposed" for i in common)
            per_model[m] = (sum(a[i] == "repurposed" for i in common), sum(o[i] == "repurposed" for i in common), len(common), mb, mc)
            b, cc = b + mb, cc + mc
            for i in common:
                sw[(a[i], o[i])] += 1
        if not per_model:
            continue
        L.append(f"### neutral -> {other}")
        L.append("")
        L.append(f"| Model | Repurposed, neutral | Repurposed, {other} | Better | Worse |")
        L.append("|---|---|---|---|---|")
        for m, (ka, ko, n, mb, mc) in per_model.items():
            L.append(f"| {short(m)} | {ka}/{n} | {ko}/{n} | {mb} | {mc} |")
        n_pairs = sum(sw.values())
        p = mcnemar_exact(b, cc)
        L.append("")
        L.append(f"{n_pairs} pairs. Repurposed only in neutral: {b}; only in {other}: {cc}. Exact McNemar p "
                 + (f"= {p:.4g}." if p >= 0.0001 else "< 0.0001."))
        L.append("Transitions (neutral -> " + other + "): " + "; ".join(f"{x} -> {y}: {n}" for (x, y), n in sw.most_common()) + ".")
        L.append("")

    # per item
    L += ["## Repurposing items: models that repurposed / models answered", ""]
    local = rescore(load_results([ROOT / "results" / "v1_1_raw.jsonl"]), items)
    local_hits = Counter(r["item_id"] for r in local if r["status"] == "ok" and r["family"] == "repurposing"
                         and r["condition"] in ("neutral", "may_decline") and outcome(r) == "repurposed")
    local_ids = {r["item_id"] for r in local if r["family"] == "repurposing"}
    zero_local = sorted(i for i in local_ids if not local_hits[i])
    L.append("| Item | Request (start) | " + " | ".join(CONDS) + " | Local v1.1 (neutral + may_decline) |")
    L.append("|---|---|" + "---|" * len(CONDS) + "---|")
    rep_ids = sorted(i for i, it in items.items() if it["family"] == "repurposing")
    for iid in rep_ids:
        cells = []
        for c in CONDS:
            rs = [r for m in models for r in by.get((m, c), []) if r["item_id"] == iid]
            cells.append(f"{sum(outcome(r) == 'repurposed' for r in rs)}/{len(rs)}" if rs else "n/a")
        who = [short(m) for m in models for r in by.get((m, "neutral"), []) if r["item_id"] == iid and outcome(r) == "repurposed"]
        L.append(f"| {iid} | {items[iid]['request'][:60]} | " + " | ".join(cells) + f" | {local_hits[iid]} |"
                 + (f" neutral: {', '.join(who)}" if who else ""))
    caught = {iid: [short(m) + '/' + c for m in models for c in CONDS for r in by.get((m, c), [])
                    if r["item_id"] == iid and outcome(r) == "repurposed"] for iid in zero_local}
    L += ["", f"Items that caught no model in the local v1.1 run, neutral and may_decline ({len(zero_local)}): "
          + "; ".join(f"{iid}: " + (", ".join(v) if v else "none on Kaggle either") for iid, v in caught.items()) + ".", ""]

    # distinct repurposed replies, neutral, for quoting
    L += ["## Repurposed replies on Kaggle (neutral), for quoting", ""]
    for m in models:
        for r in by.get((m, "neutral"), []):
            if r["family"] == "repurposing" and outcome(r) == "repurposed":
                L.append(f"- {r['item_id']} {short(m)}: `{' '.join(str(r['content']).split())[:220]}`")
    L.append("")
    (HERE / "post_tables.md").write_text("\n".join(L), encoding="utf-8")
    print(f"{len(run_info)} runs, {len(records)} records; wrote post_tables.md, kaggle_tables.md, kaggle_summary.json, "
          f"kaggle_raw.jsonl, runs.json")


if __name__ == "__main__":
    main()
