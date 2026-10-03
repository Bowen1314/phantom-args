"""Generates kaggle/benchmark_notebook.py and kaggle/benchmark_notebook.ipynb (CONDITION "neutral"), plus
kaggle/benchmark_notebook_instructed.{py,ipynb} and kaggle/benchmark_notebook_may_decline.{py,ipynb} (one per
task). The .py files are what `kaggle b t push` takes; the .ipynb files are for the browser editor.

The notebook is ONE self-contained file: the items (data/items.jsonl,
compressed) and the scoring code (phantom_args/*.py, inlined as readable
source) are embedded, so nothing has to be uploaded or pip-installed on
Kaggle. Re-run this script whenever the items or the package change:

    .venv/bin/python kaggle/build_notebook.py
"""
from __future__ import annotations

import base64
import json
import re
import textwrap
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "phantom_args"
OUT_PY = ROOT / "kaggle" / "benchmark_notebook.py"
OUT_IPYNB = ROOT / "kaggle" / "benchmark_notebook.ipynb"


def inline(module: str, stop_at: str | None = None) -> str:
    """Source of a package module with the package-relative imports removed."""
    src = (PKG / module).read_text(encoding="utf-8")
    if stop_at:
        src = src[: src.index(stop_at)]
    src = src.replace("from __future__ import annotations\n", "")
    src = re.sub(r"^from \.\w+ import [^\n]+\n", "", src, flags=re.MULTILINE)
    return src.strip() + "\n"


def items_blob() -> str:
    raw = (ROOT / "data" / "items.jsonl").read_bytes()
    b64 = base64.b64encode(zlib.compress(raw, 9)).decode("ascii")
    return "\n".join(textwrap.wrap(b64, 120))


HEADER = '''# %% [markdown]
# # Phantom arguments: what does a model do when the tool cannot do what was asked?
#
# Each item shows the model ONE tool definition (JSON Schema, `additionalProperties: false`) and ONE user
# request. The model answers with one JSON tool call written as text. The request asks for something the tool
# cannot do. Scoring is JSON Schema validation plus fixed per-item checks. There is no LLM judge.
#
# - Items v1.1: 202 items, 75 invented tools, eight families.
#   v1.0 (162 items, unchanged): `conventional`, `near_miss`, `inexpressible`, `enum_pressure`, `nested`, `control`.
#   v1.1 adds `repurposing` (28: the tool has a tempting parameter that means something else, e.g. `cc` for a
#   BCC request) and `matched_control` (12: the same parameter is the right one).
# - Three prompt conditions, one task each: `neutral` (the model must call), `instructed` (one extra sentence:
#   use only the schema's parameters), `may_decline` (one extra sentence: it may answer
#   `{"cannot_do": "..."}` instead of calling).
# - Tool calls are rendered as plain text. This is NOT a provider's native tool-calling API.
#
# **Generated file** (kaggle/build_notebook.py in the project repo). Built with AI assistance.
#
# ## What is verified and what is not
# The prompt builder, parser, scorer, report and items are the code that produced the local runs and are
# covered by the project's tests. Every call into `kaggle_benchmarks` lives in ONE cell, "Kaggle adapter",
# except the main task's `@kbench.task(...)` decorator, which the editor's task panel needs to see literally.
# This notebook was run end to end on Kaggle on 2026-10-02 (kaggle-benchmarks 0.6.1, model
# google/gemini-3.7-flash). If something fails on Kaggle later, the adapter cell is the place to patch.
#
# Editor rules learned the hard way: `TASK_NAME` must be a plain string literal, the main task's decorator must
# be a literal, top-level `@kbench.task(name="...")` (the editor panel and `kaggle b t push` both read the name
# without running code), and an HTML/SVG tag name in angle brackets anywhere in the source (the SVG tag "text",
# in a docstring) hides every task from the panel.
#
# Command line (Kaggle CLI 2.2.4): `kaggle b t push phantom-args-neutral -f benchmark_notebook.py --wait`, then
# `kaggle b t run phantom-args-neutral -m MODEL`. Each run executes this file on Kaggle against one model;
# `kaggle b t download` returns the run's files, including phantom_records.jsonl (every reply, its cost and usage).

# %%
# ----------------------------------------------------------------------------- configuration
CONDITION = "neutral"         # "neutral" (must call), "instructed", or "may_decline". One task per condition.
SUBSET = "full"               # "full": all 202 items (the leaderboard setting: every model gets the same items).
                              # "core": 10 items per family (80).
                              # "auto": every item if the probe projects <= PER_MODEL_BUDGET_USD, else the core subset
ONLY_FAMILIES = None          # None = all eight families, or a list such as ["repurposing", "matched_control"]
PER_MODEL_BUDGET_USD = 0.60   # used by SUBSET = "auto"
SESSION_BUDGET_USD = 2.00     # no paid call is started once this run has spent this much (daily quota: $10;
                              # a full run cost at most about $1.20 per model and condition on 2026-10-02)
MAX_CALLS_IF_COST_UNKNOWN = 400   # fallback guard when the library reports no cost for a call
EXTRA_MODELS = []             # model slugs to ALSO run in this session, e.g. ["google/gemini-2.5-flash"]; [] = only the task's model
PARALLEL_JOBS = 8             # 0 = plain sequential loop (smallest API surface, slowest)
TEMPERATURE = 0
MAX_OUTPUT_TOKENS = 8000      # sent as max_tokens. Kaggle's Model Proxy reserves quota for every call from its output
                              # cap and refuses calls (403) once reservations exceed the quota left; without a cap it
                              # reserves the model's full maximum. Largest reply seen on Kaggle: 2,144 tokens (local
                              # runs used 3,000). A reply that reaches the cap is kept, scored, and marked truncated.
CACHE_DIR = "/kaggle/working"  # replies are appended here as they arrive; a re-run never repeats a cached call
TASK_NAME = "phantom_args_neutral"   # a plain literal on purpose: the editor's Benchmark Task panel reads task names
                                     # without running code and shows an f-string unresolved. Change it together with
                                     # CONDITION, the main task's decorator and the %choose line in the last cell.
assert TASK_NAME == f"phantom_args_{CONDITION}", "set TASK_NAME (and the %choose line) to phantom_args_<CONDITION>"

# %%
import base64
import glob
import json
import math
import os
import threading
import time
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

if not os.path.isdir(CACHE_DIR):          # running outside Kaggle
    CACHE_DIR = "."
'''

ITEMS_CELL = '''# %%
# ----------------------------------------------------------------------------- items
# The benchmark data (data/items.jsonl, v{version}, {n} items), zlib + base64. If a dataset containing
# items.jsonl is attached to the notebook it takes precedence, so the data can be updated without touching code.
ITEMS_B64 = """
{blob}
"""


def load_benchmark_items() -> dict:
    attached = sorted(glob.glob("/kaggle/input/**/items.jsonl", recursive=True))   # UNVERIFIED: dataset mount path (CLI docs: /kaggle/input/<dataset-slug>/)
    if attached:
        text = Path(attached[0]).read_text(encoding="utf-8")
        print("items: attached dataset", attached[0])
    else:
        text = zlib.decompress(base64.b64decode("".join(ITEMS_B64.split()))).decode("utf-8")
        print("items: embedded copy")
    out = {{}}
    for line in text.splitlines():
        if line.strip():
            it = json.loads(line)
            out[it["id"]] = it
    return out


ITEMS = load_benchmark_items()
print(len(ITEMS), "items;", dict(Counter(it["family"] for it in ITEMS.values())))
'''

RUNTIME = r'''# %%
# ============================================================================= KAGGLE ADAPTER
# Every call into `kaggle_benchmarks` is in this cell. The one exception is the main task's decorator further
# down, a literal `@kbench.task(...)`: the editor's Benchmark Task panel reads the source and cannot see a wrapper.
# Checked on Kaggle on 2026-10-02 (kaggle-benchmarks 0.6.1, model google/gemini-3.7-flash): every call below
# works as written; the two changes that run showed were needed are marked CHANGED.
#
#   kb_default_llm()                      the model this task is being run for
#   kb_get_llm(slug)                      another model by slug
#   kb_model_name(llm)                    a stable string used as the cache key
#   kb_prompt(llm, text, chat_name, t, n) ONE isolated request, output capped at n tokens -> (reply, usage dict)
#   kb_task(name, description, store)     the task decorator
#   kb_run(task, llm)                     run a task once
#   kb_map(task, llm, rows, n_jobs)       run a task over rows in parallel (may raise; the caller falls back)
#   kb_assert_true / kb_assert_fail       assertions shown in the task result
#   kb_choose(task_name)                  mark the task this notebook publishes
import kaggle_benchmarks as kbench


def kb_default_llm():
    """ASSUMED (quick_start.md): `kbench.llm` is the model the task runs for (LLM_DEFAULT)."""
    return kbench.llm


def kb_get_llm(slug: str):
    """ASSUMED (cookbook.md, "Multi-Model Comparison"): `kbench.llms["vendor/model"]`."""
    return kbench.llms[slug]


def kb_model_name(llm) -> str:
    """ASSUMED: the attribute that holds a model's slug is not documented; try the likely ones."""
    for attr in ("name", "model", "model_name", "slug", "id"):
        value = getattr(llm, attr, None)
        if isinstance(value, str) and value:
            return value
    return os.environ.get("LLM_DEFAULT") or str(llm)


def _kb_usage(chat) -> dict:
    """ASSUMED (user_guide.md, "Token Usage and Cost Tracking"; examples/usage_tracking.py):
    chat.usage.input_tokens / output_tokens / total_cost_nanodollars, None unless the Kaggle Model Proxy is used."""
    usage = getattr(chat, "usage", None)
    get = lambda name: getattr(usage, name, None) if usage is not None else None
    nano = get("total_cost_nanodollars")
    if nano is None:
        parts = [get("input_tokens_cost_nanodollars"), get("output_tokens_cost_nanodollars")]
        nano = sum(p for p in parts if p is not None) if any(p is not None for p in parts) else None
    return {"prompt_tokens": get("input_tokens"), "completion_tokens": get("output_tokens"),
            "cost": (nano / 1e9) if nano is not None else None}


def kb_prompt(llm, text: str, chat_name: str, temperature=0, max_tokens=None) -> tuple:
    """One isolated request. Returns (reply text, {"prompt_tokens", "completion_tokens", "cost"}).

    Verified on Kaggle: `with kbench.chats.new(name) as chat:` opens a fresh conversation; `llm.prompt(text,
    temperature=...)` returns the reply as a string.
    CHANGED (2026-10-03): the output cap goes in as `extra_api_params={"max_tokens": N}`, which reaches the OpenAI
    client's chat.completions.create. Checked on gemini-3.7-flash, claude-haiku-4-5 and gpt-5.4-nano: `max_tokens`
    and `max_completion_tokens` both cap the reply; `max_output_tokens` raises TypeError; inside `extra_body` it is
    ignored. An older library without `extra_api_params` falls back to a call without the cap.
    NOT AVAILABLE: the finish reason. ask() marks a reply truncated when it used the whole cap.
    """
    def send():
        if max_tokens:
            try:
                return llm.prompt(text, temperature=temperature, extra_api_params={"max_tokens": max_tokens})
            except TypeError as exc:
                if "extra_api_params" not in str(exc):
                    raise
        try:
            return llm.prompt(text, temperature=temperature)
        except TypeError:
            return llm.prompt(text)

    try:
        chat_cm = kbench.chats.new(chat_name)
    except AttributeError:                      # no chats.new: send without isolation rather than fail
        reply, usage = send(), {"prompt_tokens": None, "completion_tokens": None, "cost": None}
    else:
        with chat_cm as chat:
            reply = send()
            usage = _kb_usage(chat)
    return (reply if isinstance(reply, str) else str(reply)), usage


def kb_task(name: str, description: str | None = None, store: bool = True):
    """Verified: kbench.task(name, *, description, version, store_task, store_run) used as a decorator.
    `store_task=False` (examples/dataset_evaluation.py) keeps a helper task off the task list."""
    kwargs = {"name": name}
    if description:
        kwargs["description"] = description
    if not store:
        kwargs["store_task"] = False
        kwargs["store_run"] = False         # CHANGED: no run files for the helper (60-200 x 3 files otherwise)
    try:
        return kbench.task(**kwargs)
    except TypeError:
        kwargs.pop("store_task", None)
        kwargs.pop("store_run", None)
        return kbench.task(**kwargs)


def kb_run(task, llm):
    """ASSUMED (quick_start.md): `task.run(llm=...)` returns a run whose `.result` is the task's return value."""
    return task.run(llm=llm)


def kb_map(task, llm, rows: list, n_jobs: int) -> None:
    """Run `task(llm, **row)` for every row, in parallel.
    Verified: workers are threads in this process (joblib ThreadingBackend), so ask() fills RECORDS directly.
    CHANGED: no `kbench.client.enable_cache()`. Its cache key is task name + row index + model, not the row, so
    a second evaluate in one session (probe then full set, another condition) got the first one's results
    back without running. ask() already caches by (model, item, condition). Any exception here makes the
    caller fall back to a plain sequential loop."""
    import pandas as pd
    task.evaluate(llm=[llm], evaluation_data=pd.DataFrame(rows), on_failure="continue", max_attempts=2,
                  retry_delay=5, n_jobs=n_jobs, timeout=300)


def kb_assert_true(condition: bool, expectation: str) -> None:
    """ASSUMED (user_guide.md): `kbench.assertions.assert_true(value, expectation=...)`."""
    try:
        kbench.assertions.assert_true(condition, expectation=expectation)
    except AttributeError:
        print("assertion", "passed" if condition else "FAILED", "-", expectation)


def kb_assert_fail(expectation: str) -> None:
    try:
        kbench.assertions.assert_fail(expectation=expectation)
    except AttributeError:
        print("assertion FAILED -", expectation)


def kb_choose(task_name: str) -> None:
    """ASSUMED (quick_start.md): the leaderboard takes ONE task per notebook, selected with the cell magic
    `%choose <task name>`. In the .ipynb this cell is the literal magic; here it is invoked from code."""
    try:
        get_ipython().run_line_magic("choose", task_name)
    except NameError:
        pass                                    # not running inside IPython
# ============================================================================= END OF KAGGLE ADAPTER

# %%
# ----------------------------------------------------------------------------- cache, budget, one call
FAMILY_ORDER = FAMILIES_ALL = ("conventional", "near_miss", "inexpressible", "enum_pressure", "nested", "control",
                               "repurposing", "matched_control")
if CONDITION not in CONDITIONS:
    raise ValueError(f"CONDITION must be one of {CONDITIONS}")
if ONLY_FAMILIES:
    unknown = set(ONLY_FAMILIES) - set(FAMILIES_ALL)
    if unknown:
        raise ValueError(f"unknown families {sorted(unknown)}")
    ITEMS = {iid: it for iid, it in ITEMS.items() if it["family"] in ONLY_FAMILIES}
_LOCK = threading.Lock()
CACHE_FILE = Path(CACHE_DIR) / "phantom_records.jsonl"
RECORDS: dict = {}            # (model, item_id, condition) -> record, same schema as the local runner's results file


class BudgetStop(RuntimeError):
    pass


def _load_cache() -> None:
    """Read every record file we can find: this session's, and any attached as a dataset from an earlier
    session (attach the previous notebook version's output to resume across days without paying again)."""
    paths = [str(CACHE_FILE)] + sorted(glob.glob("/kaggle/input/**/phantom_records*.jsonl", recursive=True))
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                item = ITEMS.get(rec.get("item_id"))
                if item is None or rec.get("status") != "ok" or rec.get("condition") not in CONDITIONS:
                    continue
                if rec.get("prompt_sha") != prompt_sha(item, rec["condition"]):
                    continue                                   # recorded for an older version of the item
                RECORDS[(rec["model"], rec["item_id"], rec["condition"])] = rec
    print(f"cache: {len(RECORDS)} replies already on disk")


SESSION = {"spent_usd": 0.0, "paid_calls": 0, "calls_without_cost": 0}


def ask(llm, item: dict, condition: str) -> dict:
    """One benchmark call, cached. Never repeats a call whose reply is already on disk."""
    model = kb_model_name(llm)
    key = (model, item["id"], condition)
    with _LOCK:
        if key in RECORDS:
            return RECORDS[key]
        if SESSION["spent_usd"] >= SESSION_BUDGET_USD:
            raise BudgetStop(f"session budget of ${SESSION_BUDGET_USD:.2f} reached (${SESSION['spent_usd']:.2f} spent)")
        if SESSION["calls_without_cost"] >= MAX_CALLS_IF_COST_UNKNOWN:
            raise BudgetStop(f"{MAX_CALLS_IF_COST_UNKNOWN} calls made without any cost information; stopping to be safe")
    t0 = time.time()
    reply, usage = kb_prompt(llm, build_prompt(item, condition), f"{item['id']}:{condition}", TEMPERATURE,
                             MAX_OUTPUT_TOKENS)
    rec = {"ts": time.time(), "model": model, "item_id": item["id"], "family": item["family"], "condition": condition,
           "prompt_sha": prompt_sha(item, condition), "status": "ok", "content": reply, "usage": usage,
           "cost": usage["cost"] or 0.0, "latency_s": round(time.time() - t0, 2), "source": "kaggle",
           "max_tokens": MAX_OUTPUT_TOKENS,
           "truncated": bool(MAX_OUTPUT_TOKENS and (usage["completion_tokens"] or 0) >= MAX_OUTPUT_TOKENS)}
    with _LOCK:
        RECORDS[key] = rec
        SESSION["paid_calls"] += 1
        if usage["cost"] is None:
            SESSION["calls_without_cost"] += 1
        else:
            SESSION["spent_usd"] += usage["cost"]
        with open(CACHE_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def print_spend(prefix: str = "") -> None:
    note = "" if not SESSION["calls_without_cost"] else f" ({SESSION['calls_without_cost']} calls reported no cost)"
    print(f"{prefix}session spend so far: ${SESSION['spent_usd']:.4f} over {SESSION['paid_calls']} paid calls{note}; "
          f"session budget ${SESSION_BUDGET_USD:.2f}. Account-level figure: run `kaggle benchmarks quota` or see the notebook's quota panel.")


_load_cache()

# %%
# ----------------------------------------------------------------------------- cost estimate BEFORE running
# Token counts per call measured in the local pilot (24 open-weight models, Nebius, 2026-10-02):
#   prompt: about 330 tokens.  completion: about 45 tokens without reasoning, 140-690 with reasoning on by default.
# Fill PRICES with Kaggle's per-million-token prices for the models you plan to run to get a table up front;
# the task also measures the real cost on a few probe items before it commits to the full item set.
PRICES_USD_PER_MTOK = {
    # "vendor/model-slug": (input_price, output_price),
}
PROMPT_TOKENS_PER_CALL = 330
COMPLETION_TOKENS_PER_CALL = {"no reasoning": 45, "light reasoning": 200, "heavy reasoning": 600}
N_FULL = len(ITEMS)
N_CORE = sum(bool(it.get("core")) for it in ITEMS.values())


def estimate_table() -> None:
    per_family = dict(Counter(it["family"] for it in ITEMS.values()))
    print(f"calls per model and condition: full {N_FULL} {per_family}, core {N_CORE} (at most 10 per family)")
    for slug, (p_in, p_out) in PRICES_USD_PER_MTOK.items():
        for label, out_tok in COMPLETION_TOKENS_PER_CALL.items():
            per_call = (PROMPT_TOKENS_PER_CALL * p_in + out_tok * p_out) / 1e6
            print(f"  {slug:40s} {label:16s} full ${per_call * N_FULL:.2f}  core ${per_call * N_CORE:.2f}   (one condition)")
    if not PRICES_USD_PER_MTOK:
        print("  PRICES_USD_PER_MTOK is empty: no up-front table; the probe inside the task decides full vs core.")


estimate_table()

# %%
# ----------------------------------------------------------------------------- the tasks
def choose_items(model: str, condition: str) -> list:
    """Items to run for this model: probe first, then the full set or the core subset."""
    everything = sorted(ITEMS.values(), key=lambda it: it["id"])
    core = [it for it in everything if it.get("core")]
    if SUBSET == "full":
        return everything
    if SUBSET == "core":
        return core
    # auto: project the cost of the full set from what this model's replies have cost so far
    seen = [r for (m, _, c), r in RECORDS.items() if m == model and r.get("cost")]
    if not seen:
        return core                       # no cost information yet (or the proxy reports none): stay small
    mean = sum(r["cost"] for r in seen) / len(seen)
    projected = mean * len(everything)
    choice = everything if projected <= PER_MODEL_BUDGET_USD else core
    print(f"{model}: ${mean * 1000:.3f} per 1k calls -> full set projected at ${projected:.2f} per condition; "
          f"running {'FULL' if choice is everything else 'CORE'} ({len(choice)} items)")
    return choice


@kb_task("phantom_args_item", store=False)
def phantom_item(llm, item_id: str, condition: str) -> dict:
    """One item: prompt, parse, validate against the tool's JSON Schema."""
    rec = ask(llm, ITEMS[item_id], condition)
    score = score_response(ITEMS[item_id], rec["content"], condition)
    return {"item_id": item_id, "label": score.label, "correct": score.correct}


def run_items(llm, items: list, condition: str) -> None:
    """Fill the cache for these items. Parallel through the library when possible, else a plain loop."""
    model = kb_model_name(llm)
    todo = [it for it in items if (model, it["id"], condition) not in RECORDS]
    if not todo:
        return
    if PARALLEL_JOBS > 0:
        try:
            kb_map(phantom_item, llm, [{"item_id": it["id"], "condition": condition} for it in todo], PARALLEL_JOBS)
        except BudgetStop:
            raise
        except Exception as exc:                                  # API mismatch: fall back to the plain loop
            print(f"parallel run failed ({type(exc).__name__}: {str(exc)[:200]}); falling back to a sequential loop")
        missing = [it for it in todo if (model, it["id"], condition) not in RECORDS]
        if missing and SESSION["spent_usd"] < SESSION_BUDGET_USD:
            print(f"{len(missing)} items still unanswered after the parallel pass; retrying them one at a time")
    for it in todo:                                               # sequential pass: only items still missing
        if (model, it["id"], condition) in RECORDS:
            continue
        try:
            ask(llm, it, condition)
        except BudgetStop as stop:
            print("STOPPED:", stop)
            break
        except Exception as exc:
            print(f"{it['id']}: call failed ({type(exc).__name__}: {str(exc)[:160]}); skipped, will be retried on the next run")


def probe_items() -> list:
    """One core item per family: a few calls that measure the real cost per call for this model."""
    out = []
    for fam in FAMILY_ORDER:
        fam_items = sorted((it for it in ITEMS.values() if it["family"] == fam and it.get("core")), key=lambda it: it["id"])
        out.extend(fam_items[:1])
    return out


def scored_records(model: str, condition: str | None = None) -> list:
    recs = [r for (m, _, c), r in RECORDS.items() if m == model and (condition is None or c == condition)]
    return rescore(recs, ITEMS)


# The main task uses the library decorator itself with a literal name, not kb_task or TASK_NAME: the editor's
# Benchmark Task panel and `kaggle b t push` find the task by reading the source, and see neither a wrapper nor a
# variable. Keep this literal equal to TASK_NAME (the project's tests check it in every generated notebook).
@kbench.task(name="phantom_args_neutral",
             description="Share of requests answered correctly when the tool cannot do what was asked: a schema-valid call "
         "that misuses no parameter (in the may_decline condition, a decline where declining is right). JSON Schema "
         "checks only, no LLM judge.")   # Kaggle rejects a task name or description over 255 characters
def phantom_args(llm) -> float:
    """Leaderboard score = share of items answered correctly. Higher is better.

    correct = a schema-valid call to the right tool that meets the item's checks and, on `repurposing` items,
    does not put the request into a parameter that means something else. In the `may_decline` condition a
    decline counts as correct on items the tool cannot serve and as wrong on controls."""
    model = kb_model_name(llm)
    if SUBSET == "auto":
        run_items(llm, probe_items(), CONDITION)
    run_items(llm, choose_items(model, CONDITION), CONDITION)
    recs = scored_records(model, CONDITION)
    print_spend(f"[{model}] ")
    if not recs:
        kb_assert_fail("At least one item should have been answered.")
        return 0.0
    correct = sum(bool(r["score"]["correct"]) for r in recs)
    print(render_markdown(summarize(scored_records(model))))
    kb_assert_true(len(recs) >= len({it["family"] for it in ITEMS.values()}),
                   "The run should cover at least one item per family.")
    return correct / len(recs)


# %%
# ----------------------------------------------------------------------------- run
run = kb_run(phantom_args, kb_default_llm())
run

# %%
# Optional: more models in this interactive session (does not create leaderboard entries by itself;
# leaderboard entries come from running the saved task against each model).
for slug in EXTRA_MODELS:
    try:
        kb_run(phantom_args, kb_get_llm(slug))
    except BudgetStop as stop:
        print("STOPPED:", stop)
        break
    except Exception as exc:
        print(f"{slug}: {type(exc).__name__}: {str(exc)[:200]}")

# %%
# ----------------------------------------------------------------------------- report over everything cached
all_records = rescore(list(RECORDS.values()), ITEMS)
if all_records:
    print(render_markdown(summarize(all_records)))
print_spend()
print(f"raw replies: {CACHE_FILE} (same format as the local runner; `python -m phantom_args.aggregate` reads it)")

# %%
# CHOOSE-CELL: the leaderboard takes ONE task per notebook.
kb_choose(TASK_NAME)
'''


def build_py() -> str:
    version = json.loads((ROOT / "data" / "items.jsonl").read_text(encoding="utf-8").splitlines()[0])["version"]
    n = sum(1 for line in (ROOT / "data" / "items.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
    parts = [HEADER]
    banner = "# %%\n# ----------------------------------------------------------------------------- {title}\n# Inlined verbatim from phantom_args/{module} (project repo); covered by the project's tests.\n"
    for module, title, stop in [
        ("prompt.py", "prompt builder", None),
        ("parser.py", "tolerant parser", None),
        ("minischema.py", "fallback validator (used only if `jsonschema` is not installed)", None),
        ("scorer.py", "deterministic scorer", None),
        ("aggregate.py", "aggregation and report", "def main("),
    ]:
        parts.append(banner.format(title=title, module=module) + inline(module, stop))
    parts.append(ITEMS_CELL.format(version=version, n=n, blob=items_blob()))
    parts.append(RUNTIME)
    # The items cell must come before the runtime; prompt/scorer cells before both.
    text = "\n".join(p.rstrip() + "\n" for p in parts)
    return text


CONDITION_VARIANTS = ("instructed", "may_decline")     # neutral is the default build; one .ipynb per other task


def for_condition(py: str, condition: str) -> str:
    """The same notebook set up for another condition: CONDITION, the literal TASK_NAME and (in to_ipynb) the
    %choose line must agree, and the editor's panel reads TASK_NAME without running anything."""
    old_task = 'TASK_NAME = "phantom_args_neutral"   '
    new_task = f'TASK_NAME = "phantom_args_{condition}"'
    new_task = new_task.ljust(len(old_task)) if len(new_task) < len(old_task) else new_task + " "
    out, n1 = re.subn(r'^CONDITION = "neutral"', f'CONDITION = "{condition}"', py, count=1, flags=re.MULTILINE)
    out, n2 = re.subn("^" + re.escape(old_task), new_task, out, count=1, flags=re.MULTILINE)
    out, n3 = re.subn(r'^@kbench\.task\(name="phantom_args_neutral",', f'@kbench.task(name="phantom_args_{condition}",',
                      out, count=1, flags=re.MULTILINE)
    if (n1, n2, n3) != (1, 1, 1):
        raise SystemExit("for_condition: CONDITION, TASK_NAME or the main task's decorator not found")
    return out


def to_ipynb(py: str) -> dict:
    task_name = re.search(r'^TASK_NAME = "(phantom_args_[a-z_]+)"', py, flags=re.MULTILINE).group(1)
    cells = []
    for chunk in re.split(r"^# %%", py, flags=re.MULTILINE)[1:]:
        first, _, body = chunk.partition("\n")
        body = body.strip("\n")
        if "[markdown]" in first:
            md = "\n".join(line[2:] if line.startswith("# ") else line.lstrip("#") for line in body.splitlines())
            cells.append({"cell_type": "markdown", "metadata": {}, "source": md.splitlines(keepends=True)})
        else:
            if body.startswith("# CHOOSE-CELL"):
                body = ("# The leaderboard takes ONE task per notebook (quick_start.md, \"%choose\").\n"
                        "# The name must match CONDITION: phantom_args_neutral, phantom_args_instructed or phantom_args_may_decline.\n"
                        f"%choose {task_name}")
            cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                          "source": body.splitlines(keepends=True)})
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                         "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    py = build_py()
    compile(py, str(OUT_PY), "exec")                 # must at least be valid Python
    OUT_PY.write_text(py, encoding="utf-8")
    OUT_IPYNB.write_text(json.dumps(to_ipynb(py), indent=1), encoding="utf-8")
    print(f"wrote {OUT_PY} ({len(py):,} chars) and {OUT_IPYNB}")
    for condition in CONDITION_VARIANTS:
        variant = for_condition(py, condition)
        compile(variant, str(OUT_PY), "exec")
        # The .py is what `kaggle b t push` takes (it converts the "# %%" cells itself); the .ipynb is for the editor.
        OUT_PY.with_name(f"benchmark_notebook_{condition}.py").write_text(variant, encoding="utf-8")
        path = OUT_IPYNB.with_name(f"benchmark_notebook_{condition}.ipynb")
        path.write_text(json.dumps(to_ipynb(variant), indent=1), encoding="utf-8")
        print(f"wrote {path} and its .py")


if __name__ == "__main__":
    main()
