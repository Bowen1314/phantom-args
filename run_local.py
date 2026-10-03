#!/usr/bin/env python3
"""Run the phantom-arguments benchmark against any OpenAI-compatible endpoint.

Three steps, each resumable (results are appended line by line and flushed, so
an interrupted run loses nothing and a re-run never repeats a paid call):

  1. probe   a few calls per model to measure real cost per call
  2. plan    choose, per model, the full item set, the 60-item core subset, or
             skip, so that the projected total stays inside the budget
  3. run     execute the plan under a hard spend guard

Example (Nebius Token Factory):

  .venv/bin/python run_local.py probe --key-file path/to/.env
  .venv/bin/python run_local.py plan
  .venv/bin/python run_local.py run   --key-file path/to/.env

The API key is read inside this process from --key-file (dotenv format) or,
without --key-file, from the single environment variable named by --key-var.
It is never printed or written anywhere, and NEBIUS_API_KEY is refused for any
host other than api.tokenfactory.nebius.com.

Spend guard: before every request the worst-case cost of that request
(estimated prompt tokens + max_tokens at the model's listed prices) is
reserved; a request is not sent if ledger + reservations + its own worst case
would exceed --max-spend. The ledger file persists across runs.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

from phantom_args.aggregate import load_items, load_results
from phantom_args.keys import check_host, describe, load_key
from phantom_args.prompt import CONDITIONS, build_messages, prompt_sha
from phantom_args.scorer import score_response

ROOT = Path(__file__).resolve().parent
FAMILY_ORDER = ("conventional", "near_miss", "inexpressible", "enum_pressure", "nested", "control",
                "repurposing", "matched_control")


class BudgetExceeded(RuntimeError):
    pass


# --------------------------------------------------------------------------
# models and prices
# --------------------------------------------------------------------------
def load_models(path: Path) -> dict[str, dict]:
    """Chat models from a saved GET /v1/models?verbose=true response, with prices per token."""
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["data"] if isinstance(data, dict) else data
    out = {}
    for m in rows:
        modality = (m.get("architecture") or {}).get("modality") or ""
        if not modality.endswith("->text"):
            continue                                   # embeddings, image generation, ...
        pricing = m.get("pricing") or {}
        try:
            p_in, p_out = float(pricing["prompt"]), float(pricing["completion"])
        except (KeyError, TypeError, ValueError):
            continue
        out[m["id"]] = {"id": m["id"], "price_in": p_in, "price_out": p_out,
                        "features": m.get("supported_features") or [], "modality": modality}
    return out


def select_models(all_models: dict[str, dict], spec: str) -> list[str]:
    if spec == "all":
        return sorted(all_models)
    names = [s.strip() for s in spec.split(",") if s.strip()]
    missing = [n for n in names if n not in all_models]
    if missing:
        raise SystemExit(f"unknown model(s): {missing}")
    return names


# --------------------------------------------------------------------------
# spend ledger
# --------------------------------------------------------------------------
class Ledger:
    """Append-only record of what every call cost; the source of truth for the guard."""

    def __init__(self, path: Path, max_spend: float, per_model_max: float):
        self.path = path
        self.max_spend = max_spend
        self.per_model_max = per_model_max
        self.spent = 0.0
        self.by_model: dict[str, float] = defaultdict(float)
        self.reserved = 0.0
        self.reserved_by_model: dict[str, float] = defaultdict(float)
        self.tokens = defaultdict(int)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self.spent += e["cost"]
                self.by_model[e["model"]] += e["cost"]
                self.tokens["prompt"] += e.get("prompt_tokens") or 0
                self.tokens["completion"] += e.get("completion_tokens") or 0
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8")

    def reserve(self, model: str, worst: float) -> None:
        if self.spent + self.reserved + worst > self.max_spend:
            raise BudgetExceeded(
                f"total spend guard: spent ${self.spent:.4f} + reserved ${self.reserved:.4f} "
                f"+ next call up to ${worst:.4f} would exceed ${self.max_spend:.2f}")
        if self.by_model[model] + self.reserved_by_model[model] + worst > self.per_model_max:
            raise BudgetExceeded(
                f"per-model guard for {model}: ${self.by_model[model]:.4f} spent, cap ${self.per_model_max:.2f}")
        self.reserved += worst
        self.reserved_by_model[model] += worst

    def settle(self, model: str, worst: float, cost: float, **info) -> None:
        self.reserved -= worst
        self.reserved_by_model[model] -= worst
        self.spent += cost
        self.by_model[model] += cost
        self.tokens["prompt"] += info.get("prompt_tokens") or 0
        self.tokens["completion"] += info.get("completion_tokens") or 0
        self._fh.write(json.dumps({"ts": time.time(), "model": model, "cost": cost, **info}) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


# --------------------------------------------------------------------------
# one call
# --------------------------------------------------------------------------
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529}


def estimate_prompt_tokens(messages: list[dict]) -> int:
    """Deliberately high estimate (about 3 characters per token) for the spend guard."""
    return sum(len(m["content"]) for m in messages) // 3 + 16


async def call_model(client: httpx.AsyncClient, url: str, headers: dict, model: dict, messages: list[dict],
                     args, ledger: Ledger, no_temperature: set[str]) -> dict:
    """One chat completion with retries. Returns a partial result record."""
    worst = estimate_prompt_tokens(messages) * model["price_in"] + args.max_tokens * model["price_out"]
    last_error = None
    for attempt in range(1, args.retries + 2):
        body = {"model": model["id"], "messages": messages, "max_tokens": args.max_tokens}
        sent_temperature = model["id"] not in no_temperature
        if sent_temperature:
            body["temperature"] = args.temperature
        ledger.reserve(model["id"], worst)              # may raise BudgetExceeded
        t0 = time.time()
        try:
            resp = await client.post(url, headers=headers, json=body, timeout=args.timeout)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            # The server may have generated (and billed) tokens we never saw: book the worst case.
            ledger.settle(model["id"], worst, worst, note="assumed_worst_case_after_" + type(exc).__name__)
            last_error = f"{type(exc).__name__}"
            await asyncio.sleep(min(30, 2 ** attempt) + random.random())
            continue
        latency = time.time() - t0
        if resp.status_code != 200:
            ledger.settle(model["id"], worst, 0.0, note=f"http_{resp.status_code}")
            text = resp.text[:300]
            last_error = f"http_{resp.status_code}: {text}"
            if resp.status_code == 400 and "temperature" in text.lower() and sent_temperature:
                no_temperature.add(model["id"])
                continue
            if resp.status_code in RETRY_STATUS:
                wait = min(60, 2 ** attempt) + random.random()
                retry_after = resp.headers.get("retry-after")
                if retry_after and retry_after.replace(".", "", 1).isdigit():
                    wait = max(wait, float(retry_after))
                await asyncio.sleep(wait)
                continue
            break                                           # 4xx that will not get better
        try:
            data = resp.json()
            choice = data["choices"][0]
            msg = choice.get("message") or {}
        except (ValueError, KeyError, IndexError):
            ledger.settle(model["id"], worst, worst, note="assumed_worst_case_bad_body")
            last_error = "bad_response_body"
            continue
        usage = data.get("usage") or {}
        pt = usage.get("prompt_tokens") or 0
        ct = usage.get("completion_tokens") or 0
        details = usage.get("completion_tokens_details") or {}
        reasoning_tokens = details.get("reasoning_tokens") or usage.get("reasoning_tokens") or 0
        cost = pt * model["price_in"] + ct * model["price_out"]
        if not usage:
            cost = worst
        ledger.settle(model["id"], worst, cost, prompt_tokens=pt, completion_tokens=ct)
        reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
        if not isinstance(reasoning, str):
            reasoning = json.dumps(reasoning)
        content = msg.get("content")
        if isinstance(content, list):                        # content parts
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        finish = choice.get("finish_reason")
        return {
            "status": "truncated" if finish == "length" else "ok",
            "finish_reason": finish,
            "content": content,
            "native_tool_calls": msg.get("tool_calls") or None,
            "reasoning": reasoning[: args.keep_reasoning_chars],
            "reasoning_chars": len(reasoning),
            "usage": {"prompt_tokens": pt, "completion_tokens": ct, "reasoning_tokens": reasoning_tokens},
            "cost": cost,
            "latency_s": round(latency, 2),
            "attempts": attempt,
            "sent_temperature": sent_temperature,
        }
    return {"status": "error", "error": last_error, "content": None, "cost": 0.0, "attempts": args.retries + 1}


# --------------------------------------------------------------------------
# task selection
# --------------------------------------------------------------------------
def stratified(items: list[dict], per_family: int) -> list[dict]:
    """First `per_family` core items of every family (falls back to non-core)."""
    out = []
    for fam in FAMILY_ORDER:
        fam_items = [it for it in items if it["family"] == fam]
        fam_items.sort(key=lambda it: (not it.get("core"), it["id"]))
        out.extend(fam_items[:per_family])
    return out


def tasks_for(model_id: str, items: list[dict], conditions: list[str], done: set) -> list[tuple[dict, str]]:
    return [(it, c) for it in items for c in conditions if (model_id, it["id"], c) not in done]


def done_keys(out_path: Path, redo_truncated: bool, items: list[dict]) -> set:
    """Calls already on disk for the CURRENT text of each item (stale prompts do not count)."""
    keep = {"ok"} if redo_truncated else {"ok", "truncated"}
    by_id = {it["id"]: it for it in items}
    done = set()
    for r in load_results([out_path]):
        it = by_id.get(r["item_id"])
        if it is None or r.get("status") not in keep:
            continue
        if r.get("prompt_sha") != prompt_sha(it, r["condition"]):
            continue
        done.add((r["model"], r["item_id"], r["condition"]))
    return done


# --------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------
async def run_tasks(model: dict, tasks: list[tuple[dict, str]], args, ledger: Ledger, client, url, headers,
                    out_fh, write_lock: asyncio.Lock, no_temperature: set[str]) -> dict:
    sem = asyncio.Semaphore(args.concurrency)
    stats = {"ok": 0, "truncated": 0, "error": 0, "stopped": None}
    stop = asyncio.Event()

    async def one(item: dict, condition: str) -> None:
        async with sem:
            if stop.is_set():
                return
            messages = build_messages(item, condition)
            try:
                res = await call_model(client, url, headers, model, messages, args, ledger, no_temperature)
            except BudgetExceeded as exc:
                stats["stopped"] = str(exc)
                stop.set()
                return
            rec = {"ts": time.time(), "model": model["id"], "item_id": item["id"], "family": item["family"],
                   "condition": condition, "prompt_sha": prompt_sha(item, condition),
                   "max_tokens": args.max_tokens, "temperature": args.temperature, **res}
            if rec["status"] == "ok":
                rec["score"] = score_response(item, rec["content"], rec["condition"]).to_dict()
            stats[rec["status"]] += 1
            async with write_lock:
                out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out_fh.flush()

    await asyncio.gather(*(one(it, c) for it, c in tasks))
    return stats


def model_cost_stats(out_path: Path) -> dict[str, dict]:
    """Observed mean cost per call and truncation counts per model, from the results file."""
    agg: dict[str, dict] = defaultdict(lambda: {"calls": 0, "cost": 0.0, "truncated": 0, "reasoning_calls": 0,
                                                "completion_tokens": 0, "prompt_tokens": 0})
    for r in load_results([out_path]):
        if r.get("status") not in ("ok", "truncated"):
            continue
        a = agg[r["model"]]
        a["calls"] += 1
        a["cost"] += r.get("cost") or 0.0
        a["truncated"] += r["status"] == "truncated"
        u = r.get("usage") or {}
        a["completion_tokens"] += u.get("completion_tokens") or 0
        a["prompt_tokens"] += u.get("prompt_tokens") or 0
        a["reasoning_calls"] += bool(u.get("reasoning_tokens")) or bool(r.get("reasoning_chars"))
    return agg


async def execute(args, per_model_tasks: dict[str, list], models: dict[str, dict]) -> None:
    key = load_key(args.key_var, args.key_file)
    check_host(args.key_var, args.base_url)
    print(f"key: {describe(args.key_var, key)}; endpoint host pinned and https verified")
    url = args.base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    ledger = Ledger(Path(args.ledger), args.max_spend, args.per_model_max)
    print(f"ledger: ${ledger.spent:.4f} already spent; cap ${args.max_spend:.2f} total, ${args.per_model_max:.2f} per model")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_lock = asyncio.Lock()
    no_temperature: set[str] = set()
    model_sem = asyncio.Semaphore(args.model_parallel)
    limits = httpx.Limits(max_connections=args.concurrency * args.model_parallel + 4)

    with out_path.open("a", encoding="utf-8") as out_fh:
        async with httpx.AsyncClient(limits=limits) as client:
            async def one_model(mid: str, tasks: list) -> None:
                async with model_sem:
                    if not tasks:
                        return
                    t0 = time.time()
                    stats = await run_tasks(models[mid], tasks, args, ledger, client, url, headers, out_fh,
                                            write_lock, no_temperature)
                    note = f" STOPPED: {stats['stopped']}" if stats["stopped"] else ""
                    print(f"{mid}: {len(tasks)} tasks -> ok {stats['ok']}, truncated {stats['truncated']}, "
                          f"error {stats['error']} in {time.time() - t0:.0f}s; model spend ${ledger.by_model[mid]:.4f}, "
                          f"total ${ledger.spent:.4f}{note}", flush=True)

            await asyncio.gather(*(one_model(mid, tasks) for mid, tasks in per_model_tasks.items()))
    if no_temperature:
        print("models that rejected the temperature parameter (sent without it):", sorted(no_temperature))
    print(f"done. total spend ${ledger.spent:.4f}; tokens in {ledger.tokens['prompt']:,} out {ledger.tokens['completion']:,}")
    ledger.close()


# --------------------------------------------------------------------------
# sub-commands
# --------------------------------------------------------------------------
def cmd_models(args) -> None:
    """Refresh the saved model list (GET /models?verbose=true)."""
    key = load_key(args.key_var, args.key_file)
    check_host(args.key_var, args.base_url)
    resp = httpx.get(args.base_url.rstrip("/") + "/models", params={"verbose": "true"},
                     headers={"Authorization": f"Bearer {key}"}, timeout=60)
    resp.raise_for_status()
    Path(args.models_file).write_text(json.dumps(resp.json(), indent=1), encoding="utf-8")
    print(f"saved {len(resp.json().get('data', []))} models to {args.models_file}")


def cmd_probe(args) -> None:
    models = load_models(Path(args.models_file))
    chosen = select_models(models, args.models)
    items = list(load_items(args.items).values())
    probe_items = stratified(items, args.per_family)
    done = done_keys(Path(args.out), redo_truncated=False, items=items)
    per_model = {m: tasks_for(m, probe_items, args.conditions, done) for m in chosen}
    n = sum(len(t) for t in per_model.values())
    print(f"probe: {len(chosen)} models x {len(probe_items)} items x {len(args.conditions)} conditions; {n} calls to make")
    asyncio.run(execute(args, per_model, models))


def cmd_plan(args) -> None:
    """Decide full / core / skip per model from the cost per call seen so far."""
    models = load_models(Path(args.models_file))
    chosen = select_models(models, args.models)
    items = list(load_items(args.items).values())
    n_full = len(items) * len(args.conditions)
    n_core = sum(bool(it.get("core")) for it in items) * len(args.conditions)
    stats = model_cost_stats(Path(args.out))
    ledger_spent = 0.0
    if Path(args.ledger).exists():
        for line in Path(args.ledger).read_text(encoding="utf-8").splitlines():
            try:
                ledger_spent += json.loads(line)["cost"]
            except (json.JSONDecodeError, KeyError):
                pass
    plan = {}
    for m in chosen:
        s = stats.get(m)
        if not s or not s["calls"]:
            plan[m] = {"mode": "skip", "reason": "no successful probe calls"}
            continue
        mean = s["cost"] / s["calls"] * args.safety
        full = mean * max(0, n_full - s["calls"])
        core = mean * max(0, n_core - s["calls"])
        entry = {"calls_seen": s["calls"], "mean_cost_per_call": s["cost"] / s["calls"],
                 "mean_completion_tokens": s["completion_tokens"] / s["calls"],
                 "truncated_seen": s["truncated"], "reasoning_calls_seen": s["reasoning_calls"],
                 "projected_full": s["cost"] + full, "projected_core": s["cost"] + core}
        if entry["projected_full"] <= args.per_model_max:
            entry["mode"] = "full"
        elif entry["projected_core"] <= args.per_model_max:
            entry["mode"] = "core"
            entry["reason"] = f"full matrix projected at ${entry['projected_full']:.2f} > ${args.per_model_max:.2f} per-model cap"
        else:
            entry["mode"] = "skip"
            entry["reason"] = f"even the core subset is projected at ${entry['projected_core']:.2f} > ${args.per_model_max:.2f}"
        plan[m] = entry

    def remaining(e):
        if e["mode"] == "full":
            return e["projected_full"] - e["calls_seen"] * e["mean_cost_per_call"]
        if e["mode"] == "core":
            return e["projected_core"] - e["calls_seen"] * e["mean_cost_per_call"]
        return 0.0

    budget = args.max_spend * args.budget_fraction - ledger_spent
    # Downgrade the most expensive models first until the plan fits: full -> core -> skip.
    while sum(remaining(e) for e in plan.values() if "mean_cost_per_call" in e) > budget:
        candidates = [(remaining(e), m) for m, e in plan.items() if e["mode"] in ("full", "core")]
        if not candidates:
            break
        _, m = max(candidates)
        e = plan[m]
        if e["mode"] == "full":
            e["mode"] = "core"
            e["reason"] = "downgraded to the core subset to fit the total budget"
        else:
            e["mode"] = "skip"
            e["reason"] = "skipped to fit the total budget"
    total = sum(remaining(e) for e in plan.values() if "mean_cost_per_call" in e)
    Path(args.plan).write_text(json.dumps({"n_full": n_full, "n_core": n_core, "ledger_spent": ledger_spent,
                                           "projected_remaining": total, "models": plan}, indent=1), encoding="utf-8")
    print(f"already spent ${ledger_spent:.4f}; budget for the run ${budget:.2f}; projected ${total:.2f}")
    for m in chosen:
        e = plan[m]
        extra = f"  ({e['reason']})" if e.get("reason") else ""
        if "mean_cost_per_call" in e:
            print(f"  {e['mode']:5s} {m:45s} ${e['mean_cost_per_call'] * 1000:.3f}/1k calls-> full ${e['projected_full']:.3f} core ${e['projected_core']:.3f} "
                  f"out_tok/call {e['mean_completion_tokens']:.0f} trunc {e['truncated_seen']}{extra}")
        else:
            print(f"  {e['mode']:5s} {m}{extra}")
    print(f"plan written to {args.plan}")


def cmd_run(args) -> None:
    models = load_models(Path(args.models_file))
    items = list(load_items(args.items).values())
    if args.families:
        wanted_fams = {f.strip() for f in args.families.split(",") if f.strip()}
        unknown = wanted_fams - {it["family"] for it in items}
        if unknown:
            raise SystemExit(f"unknown families: {sorted(unknown)}")
        items = [it for it in items if it["family"] in wanted_fams]
    core = [it for it in items if it.get("core")]
    done = done_keys(Path(args.out), redo_truncated=args.redo_truncated, items=items)
    if args.plan and Path(args.plan).exists() and not args.ignore_plan:
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))["models"]
    else:
        plan = {m: {"mode": args.subset} for m in select_models(models, args.models)}
    wanted = set(select_models(models, args.models))
    per_model = {}
    for m, e in plan.items():
        if m not in wanted or e["mode"] == "skip":
            continue
        subset = items if e["mode"] in ("full", "all") else core
        per_model[m] = tasks_for(m, subset, args.conditions, done)
    n = sum(len(t) for t in per_model.values())
    print(f"run: {len(per_model)} models, {n} calls to make ({len(done)} already on disk)")
    asyncio.run(execute(args, per_model, models))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["models", "probe", "plan", "run"])
    ap.add_argument("--base-url", default="https://api.tokenfactory.nebius.com/v1/")
    ap.add_argument("--key-var", default="NEBIUS_API_KEY", help="name of the ONE variable to read the key from")
    ap.add_argument("--key-file", help="dotenv file holding the key variable (otherwise os.environ is used)")
    ap.add_argument("--models-file", default=str(ROOT / "results" / "models_verbose.json"))
    ap.add_argument("--models", default="all", help="'all' or a comma-separated list of model ids")
    ap.add_argument("--items", default=str(ROOT / "data" / "items.jsonl"))
    ap.add_argument("--conditions", default=",".join(CONDITIONS), type=lambda s: s.split(","))
    ap.add_argument("--out", default=str(ROOT / "results" / "pilot_raw.jsonl"))
    ap.add_argument("--ledger", default=str(ROOT / "results" / "spend_ledger.jsonl"))
    ap.add_argument("--plan", default=str(ROOT / "results" / "run_plan.json"))
    ap.add_argument("--ignore-plan", action="store_true", help="run --subset for --models regardless of the plan file")
    ap.add_argument("--subset", default="full", choices=["full", "core"])
    ap.add_argument("--families", help="run: only items of these families (comma-separated), e.g. repurposing,matched_control")
    ap.add_argument("--per-family", type=int, default=2, help="probe: items per family")
    ap.add_argument("--max-spend", type=float, default=4.0, help="hard cap in USD across all runs sharing the ledger")
    ap.add_argument("--per-model-max", type=float, default=0.60)
    ap.add_argument("--budget-fraction", type=float, default=0.9, help="plan: share of --max-spend the plan may use")
    ap.add_argument("--safety", type=float, default=1.15, help="plan: multiplier on the observed mean cost per call")
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--concurrency", type=int, default=8, help="parallel requests per model")
    ap.add_argument("--model-parallel", type=int, default=4, help="models run at the same time")
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--redo-truncated", action="store_true", help="re-run replies that hit max_tokens")
    ap.add_argument("--keep-reasoning-chars", type=int, default=6000)
    args = ap.parse_args(argv)
    bad = [c for c in args.conditions if c not in CONDITIONS]
    if bad:
        raise SystemExit(f"unknown conditions {bad}; choose from {list(CONDITIONS)}")
    {"models": cmd_models, "probe": cmd_probe, "plan": cmd_plan, "run": cmd_run}[args.command](args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
