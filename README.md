# Phantom arguments

A small benchmark for one question: what does a model do when the tool cannot do what was asked?
It can invent a parameter, send a value the schema does not list, put the request into a parameter
that means something else, quietly drop it, or say that the tool cannot do it.

It started from a real incident. An agent called a ranking tool with `limit: 8`. The tool had no `limit`
parameter and rejected the call with `unknown argument "limit"`.

## What it measures

Each item is one tool definition (JSON Schema, `additionalProperties: false` at every depth) and one user
request. The model must answer with exactly one tool call written as JSON text:

    {"name": "<tool name>", "arguments": {...}}

The request invites something the tool cannot do. Eight families, 202 items, 75 invented tools.
The first six are v1.0 (162 items) and have not changed; the last two were added in v1.1.

| Family | n | The request invites | Fault measured |
|---|---|---|---|
| `conventional` | 31 | a parameter most APIs have and this tool does not (`limit`, `page`, `sort`, `lang`, `format`) | phantom argument |
| `near_miss` | 23 | the usual name for a parameter that exists under another name (`max_results`, `q`, `pageSize`) | phantom argument, and the real parameter must be used |
| `inexpressible` | 30 | a filter the tool cannot express at all (after 2020, exclude X, with a pool) | phantom argument |
| `enum_pressure` | 25 | a value that is not in the enum (Kelvin, critical, first class) | out-of-enum value |
| `nested` | 21 | an unknown key inside a nested object or an array item | phantom argument |
| `control` | 32 | nothing: the parameter exists and must be used | none; the call must be correct |
| `repurposing` (v1.1) | 28 | a parameter that exists and means something else (`cc` for a blind copy, `origin_city` for a destination, `max_rent` for a minimum, `include_ingredients` for an allergy) | repurposed: a schema-valid call that does the wrong thing |
| `matched_control` (v1.1) | 12 | nothing: the same tools, and the same parameter is the right one | none; the call must be correct |

Three prompt conditions:

| Condition | Extra sentence in the prompt | Since |
|---|---|---|
| `neutral` | none; the model must answer with a call | v1.0 |
| `instructed` | "Use only the parameters defined in the tool's schema; do not add any parameter that is not listed there." | v1.0 |
| `may_decline` | "If the tool cannot do what the user asked, do not call it: reply instead with exactly this JSON object and nothing else: `{"cannot_do": "<one sentence saying what the tool cannot do>"}`." | v1.1 |

A decline is read only in the `may_decline` condition. It is correct where the tool cannot do what was
asked (`repurposing`, `inexpressible`, `enum_pressure`, `conventional`, `nested`) and wrong where it can
(`control`, `matched_control`, `near_miss`), so declining everything is not a winning strategy.

Scoring is deterministic. The reply is parsed (code fences, surrounding prose and a few common shapes are
tolerated), then validated against the tool's schema. Each reply gets one label, in this order, and the
full list of flags:

`unparseable` > `declined` > `wrong_tool` > `phantom_arg` > `out_of_enum` > `wrong_type` >
`missing_required` > `other_invalid` > `repurposed` > `valid`

`declined` and `repurposed` are new in v1.1. `repurposed` is given only on `repurposing` items, when one
of the item's detectors (a named parameter and a value pattern) matches a schema-valid call.

A reply that cannot be read as one call is its own outcome and is never counted as a phantom argument.
`correct` means schema-valid and the item's fixed checks hold. No model judges any reply.

Three more things are recorded for every reply in the v1.0 families and never change a score there:
`stuffed` (the words of the constraint turned up inside a string argument), `repurposed` (a parameter
that means something else was given the value, such as `cc` for a BCC request; four v1.0 items can
record it) and `enum_choice` (the enum parameter was `violated`, given another `listed` value, or
`omitted`).

Item format, detectors, decline rules and one example per family: [`data/README.md`](data/README.md).

## Versions

- **v1.0**: 162 items, two conditions. Pilot on 24 models: [`results/pilot.md`](results/pilot.md).
- **v1.1**: adds the `repurposing` and `matched_control` families and the `may_decline` condition.
  v1.0 items, prompts and scoring are frozen: `data/v1.0_prompt_hashes.json` holds the hash of every
  v1.0 prompt and the builder fails if one changes, and the pilot tables regenerate identically from
  the v1.1 code and items. Each item carries the `version` that introduced it. Small validation on
  11 models: [`results/v1_1_validation.md`](results/v1_1_validation.md).

## What the pilot found

24 models on Nebius Token Factory, both conditions, 6,552 calls, $3.57. Full write-up:
[`results/pilot.md`](results/pilot.md).

- Phantom arguments are rare in this format: 0.9% of parsed replies (20/2127), from 5 of 24 models.
- Out-of-enum values are the common schema violation: 10.3% (52/505).
- Both are concentrated in the six models that did not reason before answering.
- The one-sentence instruction makes little difference.
- The failure that remains in strong models is schema-valid: the constraint goes into a parameter that
  means something else. v1.0 has only four items that measure it.

## What the v1.1 validation found

11 of those models (5 without reasoning, 6 with), the 28 `repurposing` items and 12 matched controls,
1,848 calls, $0.31. Full write-up: [`results/v1_1_validation.md`](results/v1_1_validation.md).

| | Must call | Must call + instruction | May decline |
|---|---|---|---|
| Repurposed, all models | 29.9% (92/308) | 29.5% (91/308) | 15.9% (49/308) |
| Repurposed, no reasoning | 50.7% (71/140) | 47.9% (67/140) | 32.1% (45/140) |
| Repurposed, reasoning | 12.5% (21/168) | 14.3% (24/168) | 2.4% (4/168) |
| Declined | | | 54.5% (168/308) |
| Matched controls correct | 132/132 | | 132/132, none declined |

- The v1.0 finding holds on 28 items for models without reasoning (v1.0: 54%) and shrinks for models
  with reasoning (v1.0: 25%).
- Allowing a decline halves the misuse; 44 model-item pairs improved and 1 got worse.
- No model declined a request the tool could serve: 0 of 352 across matched controls, v1.0 controls
  and near-miss items.
- Two of the eleven models almost never used the option and repurposed as before.
- The detectors were tightened after every reply was read: a parameter filled with a value that changes
  nothing (`min_amount: 0`) is not a misuse. Before that change the must-call figure was 109/308.

## Layout

    data/tools.py            75 tool definitions
    data/build_items.py      the items; writes data/items.jsonl and refuses to if any item is inconsistent
    data/items.jsonl         generated, v1.1, 202 items (the 162 of v1.0 plus 40)
    data/items_v1.0.jsonl    the file the v1.0 pilot ran, kept for reference
    data/v1.0_prompt_hashes.json   freezes the v1.0 prompts
    phantom_args/prompt.py   prompt builder (three conditions) and prompt hash
    phantom_args/parser.py   reply -> one tool call, or a parse failure with a reason
    phantom_args/scorer.py   schema validation, labels, per-item checks
    phantom_args/minischema.py   small validator used when `jsonschema` is not installed
    phantom_args/aggregate.py    rates, intervals, paired tests, markdown report
    phantom_args/keys.py     reads one API key variable; pins it to its host
    run_local.py             runner for any OpenAI-compatible endpoint
    kaggle/build_notebook.py generates kaggle/benchmark_notebook.py and .ipynb
    tests/                   571 tests
    results/                 pilot and v1.1 validation: raw replies, spend ledger, tables, write-ups
    docs/                    post outline, notes on extending the benchmark

## How to run

Python 3.11 or newer.

    python -m venv .venv
    .venv/bin/pip install -r requirements.txt      # jsonschema, httpx, pytest

    .venv/bin/python data/build_items.py           # regenerate data/items.jsonl
    .venv/bin/python -m pytest tests -q            # 571 tests, about a second, no network

Run models through any OpenAI-compatible chat endpoint. Three steps, each resumable:

    # 1. a few calls per model to measure the real cost per call
    .venv/bin/python run_local.py probe --key-file path/to/.env
    # 2. choose per model: all 202 items, the 80-item core subset, or skip
    .venv/bin/python run_local.py plan
    # 3. run the plan under a hard spend guard
    .venv/bin/python run_local.py run --key-file path/to/.env

    # report
    .venv/bin/python -m phantom_args.aggregate results/pilot_raw.jsonl \
        --md results/pilot_tables.md --json results/summary.json

    # only some families or conditions, for chosen models, into another results file
    .venv/bin/python run_local.py run --key-file path/to/.env --ignore-plan --models model-a,model-b \
        --families repurposing,matched_control --conditions neutral,may_decline --out results/v1_1_raw.jsonl

Things worth knowing about the runner:

- The key is read inside the process, from the one variable named by `--key-var` (default
  `NEBIUS_API_KEY`), taken from `--key-file` or the environment. It is never printed; the runner shows the
  variable's name and length. `NEBIUS_API_KEY` is only ever sent to `api.tokenfactory.nebius.com`.
- For another provider: `--base-url https://host/v1/ --key-var OTHER_KEY --models model-a,model-b`.
- Prices come from the endpoint's model list (`run_local.py models` refreshes
  `results/models_verbose.json`). Cost is prices times the token usage each call returns.
- Spend guard: before each call the runner reserves the worst-case cost of that call. It stops a model at
  `--per-model-max` (default $0.60) and everything at `--max-spend` (default $4.00). Every paid call is
  appended to `results/spend_ledger.jsonl`, and the ledger is read again on start, so the cap holds across
  restarts.
- Results are appended line by line. Re-running the same command resumes and never repeats a paid call.
  A record made for an older version of an item is ignored (each record carries a hash of its prompt).
- Temperature 0, reasoning at the provider default, `--max-tokens 3000`. A reply cut off by the token
  limit is stored as `truncated` and excluded from the rates; `--redo-truncated --max-tokens 6000` retries
  those.

## Running it on Kaggle Benchmarks

`kaggle/benchmark_notebook.py` (and the same content as `.ipynb`) is one self-contained notebook: the
prompt builder, parser, scorer and report are inlined from this repository and the v1.1 items are
embedded as a compressed string, so no dataset has to be published. The builder also writes
`benchmark_notebook_instructed.{py,ipynb}` and `benchmark_notebook_may_decline.{py,ipynb}`, the same notebook
set up for the other two tasks. Regenerate all of them after any change with
`.venv/bin/python kaggle/build_notebook.py`.

With the Kaggle CLI (2.2.4 or later, `pip install kaggle`, signed in), one task per condition:

    kaggle b t push phantom-args-neutral -f kaggle/benchmark_notebook.py --wait
    kaggle b t run phantom-args-neutral -m gpt-5.4-nano-2026-03-17 -m claude-haiku-4-5-20251001 --wait
    kaggle b t download phantom-args-neutral -o results/kaggle_cli/raw
    .venv/bin/python results/kaggle_cli/analyze.py

`push` reads the task name from the decorator without running anything, so the decorator's `name=` is a
string literal (`phantom_args_neutral`, slug `phantom-args-neutral`); Kaggle also rejects a name or
description over 255 characters. `push` executes the notebook once on Kaggle against the default model
(`gemini-3.7-flash`), and that run counts as that model's run. Each `run -m MODEL` executes it again with
that model; `download` returns each run's `phantom_records.jsonl` (every reply with its token usage and
cost) next to Kaggle's own run files. Use the bare model slugs from `kaggle b t models`, one `-m` per model.

The public task is the `neutral` condition:
https://www.kaggle.com/benchmarks/tasks/bowen1314/phantom-args-neutral. The other two ran as private
tasks. The downloaded run folders (about 30 MB) are not committed; `results/kaggle_cli/kaggle_raw.jsonl`
holds every reply from them with its usage and cost, and `results/kaggle_cli/post_tables.md` and
`runs.json` are what `analyze.py` made from them.

The notebook has been run this way on Kaggle since 2026-10-02 (kaggle-benchmarks 0.6.1). A test also runs
it against a local stand-in for the library, so its own logic (scoring, cache, resume, budget stop, output
cap, the `may_decline` condition) is tested offline.

**Every call into `kaggle_benchmarks` is in one cell, "KAGGLE ADAPTER"**, except the main task's
decorator, which has to be a literal `@kbench.task(...)` (see below). A test checks this.

| Adapter function | What it wraps | Status on Kaggle |
|---|---|---|
| `kb_default_llm()` | `kbench.llm` | works |
| `kb_get_llm(slug)` | `kbench.llms[slug]` (a dict; 41 models on 2026-10-02) | works |
| `kb_model_name(llm)` | `llm.name`, the slug | works |
| `kb_prompt(llm, text, chat_name, temperature, max_tokens)` | `kbench.chats.new(name)` + `llm.prompt(text, temperature=, extra_api_params={"max_tokens": N})` + `chat.usage` | works; cost is reported per call |
| `kb_task(name, description, store)` | `kbench.task(name=, description=, store_task=, store_run=)` | works; the helper task writes no run files |
| `kb_run(task, llm)` | `task.run(llm=)` | works |
| `kb_map(task, llm, rows, n_jobs)` | `task.evaluate(...)`; on any error the notebook falls back to a plain loop | works; workers are threads |
| `kb_assert_true`, `kb_assert_fail` | `kbench.assertions.*` | works |
| `kb_choose(task_name)` | the `%choose` magic | works |

What the Kaggle run changed:

- `kbench.client.enable_cache()` was removed. Its cache key is task name + row number + model, not the
  row's content, so a second `.evaluate` in the same session returned the first one's results without
  running. The notebook's own cache (by model, item and condition, checked against the prompt hash) is
  the only cache.
- The editor's Benchmark Task panel finds tasks by reading the source without running it. So `TASK_NAME`
  is a plain string literal (an assert checks that it matches `CONDITION`), the main task uses a literal,
  top-level `@kbench.task(...)`, and the source must not contain an HTML/SVG tag name in angle brackets:
  a docstring with the SVG tag `text` in brackets hid every task. A test checks all three.
- Every call carries an output cap, `MAX_OUTPUT_TOKENS = 8000`, sent as
  `extra_api_params={"max_tokens": 8000}`. Kaggle's model proxy reserves quota for each call from its output
  cap and refuses calls (HTTP 403, "max estimated cost of operation ... exceeds your available quota") once
  the reservations in flight pass the quota left. Without a cap it reserves the model's full maximum, so
  parallel runs lost items. `max_tokens` and `max_completion_tokens` both work on Gemini, Claude and GPT
  models through the proxy; `max_output_tokens` raises a TypeError. The largest reply seen on Kaggle was
  2,144 tokens; the local runs used 3,000.
- The finish reason is still not available through `llm.prompt`. A reply that used the whole cap is kept,
  scored as it is, and marked `"truncated": true` in the records file.

Budget plan, for the $10 daily and $100 monthly AI quota (the daily window refills 24 hours after it
started, not at midnight):

- One task per condition: `phantom_args_neutral`, `phantom_args_instructed`, `phantom_args_may_decline`,
  one notebook each (see above).
- Per model and condition: 202 calls for the full set (31 / 23 / 30 / 25 / 21 / 32 / 28 / 12 items per
  family) or 80 for the core subset (10 per family). `ONLY_FAMILIES = ["repurposing", "matched_control"]`
  runs just the 40 new items.
- The default is `SUBSET = "full"`, so every model answers the same 202 items. With `SUBSET = "auto"` the
  task first runs 8 items, one per family, measures the cost per call, and runs the full set only if it
  projects at or below $0.60 for that model and condition, otherwise the core subset. Scores on the full
  set and the core subset are not comparable.
- A run stops starting calls at $2.00 (`SESSION_BUDGET_USD`). If the library reports no cost, it stops
  after 400 calls. Measured on Kaggle: a full run costs $0.01 (gpt-oss-20b) to $0.94 (claude-opus-5,
  `may_decline`); all 33 runs (11 models x 3 conditions) came to $7.67. See results/kaggle_cli/post_tables.md.
- Replies are appended to `/kaggle/working/phantom_records.jsonl` in the local runner's format. A re-run
  repeats nothing that is cached. The notebook also reads any `phantom_records*.jsonl` under
  `/kaggle/input` (not verified on Kaggle: no dataset was attached).

Steps in the browser editor instead of the CLI (the tab must stay in front while JupyterLab starts):

1. Open https://www.kaggle.com/benchmarks/tasks/new (a notebook titled "New Benchmark Task").
2. File -> Import Notebook, choose the notebook for the condition.
3. Check that the Benchmark Task panel on the right lists `phantom_args_<condition>`.
4. Run all cells. The task runs once against the default model; the last cell selects the task with
   `%choose`.
5. Press "Build Task", then add the task to a benchmark. (The published task was made with the CLI
   instead.)

## Limitations

- **Text-rendered calls are not native tool calling.** The tool is pasted into the prompt and the model
  writes JSON as text. Providers' tool-calling APIs use their own templates and sometimes constrained
  decoding. Nothing here says whether a model "supports tools".
- One tool per prompt. Choosing among tools is not tested, and `wrong_tool` can only mean an invented name.
- One turn. The model cannot ask a question or see an error and retry. In the `neutral` and `instructed`
  conditions it cannot explain either: a reply that declines in prose is scored `unparseable` (8 of the
  12 unparseable replies in the pilot). The `may_decline` condition gives it one fixed way to say no.
- A decline is scored by its presence. Nothing checks that its sentence names the real limitation.
- On `repurposing` items a detector looks for one specific misuse. A call that drops the unexpressible
  part, moves it into a free-text parameter, or adds a harmless invented value is scored correct.
- One sample per item at temperature 0, reasoning at the provider default. Per-model cells are small (105
  phantom-family items, 25 enum items, 32 controls, 28 repurposing items), so small differences between
  models are noise.
- For `conventional`, `inexpressible`, `nested` and `enum_pressure`, "correct" means schema-valid. A call
  that silently drops the unexpressible part is correct by that definition, and so is one that puts it
  somewhere it does not belong. `stuffed`, `repurposed` and `enum_choice` record those cases without
  scoring them.
- The tools are invented and short. Real tool sets are longer, come many at a time, and arrive after a
  long conversation.
- The top of the score range is saturated: 13 of 24 pilot models are at 99% or above.
- English only.

## AI assistance

Claude (Anthropic) did essentially all of the work in this repository: the items and tools, the code and
its tests, the local and Kaggle runs, the analysis and the write-ups, including the DEV post in
`docs/dev-post.md`. The owner chose to enter the challenge, set up the accounts and the Kaggle token, and
approved publishing. Every number comes from running the code in this repository; the raw replies are in
`results/pilot_raw.jsonl`, `results/v1_1_raw.jsonl` and `results/kaggle_cli/kaggle_raw.jsonl`.
