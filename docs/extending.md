# Extending the benchmark

Notes for whoever takes v1.0 further, including a possible submission to Kaggle's "Gemma 4 Developer
Agent – Paper Track" (Best New Resource: a new evaluation dataset for agentic software engineering).

## 1. Adding tool schemas from coding agents (file edit, shell, search)

Short answer: the pipeline needs no change for single-call items. Writing good items is a day or two of
work. Making the result say something about agentic software engineering needs two additions that are
each a few days.

### What already works

- A tool is a dictionary in `data/tools.py` (`name`, `description`, `parameters` as JSON Schema). An item
  is one `add(...)` call in `data/build_items.py`. The builder checks every schema and refuses to write
  the file unless the item's reference call scores valid and its trap call scores the intended fault.
- The prompt builder, parser and scorer already accept several tools per item (`item["tools"]` is a list
  and `wrong_tool` is a label). v1.0 just never uses more than one.
- Nothing in the scorer knows what a tool is about. Nested objects, arrays of objects, enums and
  numeric bounds are covered.

### Items that carry over directly

The six families map onto coding tools without strain. Tool shapes below are typical of coding agents in
general; they should be written fresh, as the v1.0 tools were, and not copied from a product.

| Family | Coding-agent example |
|---|---|
| conventional | `read_file(path)` and "show me lines 100 to 150": invites `start_line`, `end_line`, `offset`, `limit` |
| conventional | `run_shell(command)` and "give it two minutes at most": invites `timeout`; "run it in ./server": invites `cwd` |
| near_miss | `grep(pattern, path, glob)` where the case switch is `ignore_case` and the request says "case-insensitive": invites `-i`, `case_sensitive` |
| inexpressible | `search_code(query)` and "only in files changed this week", "skip the vendor directory" |
| enum_pressure | `grep(output_mode: content, files, count)` and "just give me the line numbers" |
| nested | `apply_edits(path, edits[{old_text, new_text}])` and "replace every occurrence": invites `replace_all` inside an edit |
| control | the same tools with a request the schema covers |

The pilot says where to aim. Conventional parameter names were almost never invented (3 of 618 replies),
so more items of that kind will mostly produce zeros. The live failure was a schema-valid call that puts
the constraint somewhere it does not belong. Coding tools are rich in exactly that:

- `run_shell(command)` has no `timeout` or `cwd`, and the model writes `cd server && timeout 120 npm test`
  into `command`. Is that correct? It depends on the shell, and that question is the reason these items
  need care.
- `edit_file(path, old_text, new_text)` has no `replace_all`, and the model sends an `old_text` that
  matches once and silently fixes one of five occurrences.
- `write_file(path, content)` has no append mode, and the model overwrites.
- `search_code(query)` has no path filter, and the model types `path:src/` into the query.

Each of these is a deterministic check on the arguments (`misuse_params` and `markers` in the item
format), the same mechanism v1.0 uses for the BCC item.

### What is harder

1. **Several tools at once.** A coding agent sees 10 to 30 tools. With one tool in the prompt, the model
   never has the option of choosing a different tool that can do the job, which is the right answer in
   many real cases. Supported by the code, but every item then needs a decision about which calls count
   as correct, and items with two acceptable tools need an `expect` per tool. Estimate: two to three days
   for 60 items, mostly item writing and review.
2. **Native tool calling.** Coding agents use the provider's tool-calling API, not JSON in text. The
   runner already stores `native_tool_calls` when a reply has them, but it never sends a `tools` field.
   Adding a `--native` mode is about a day: send the item's tools in the request, read
   `message.tool_calls`, feed name and arguments to the existing scorer. Two cautions. Some providers
   apply constrained decoding, which makes a phantom argument impossible and the family meaningless for
   that provider. And no native tool-calling path was found in the parts of the Kaggle benchmarks library's
   documentation that were read for the notebook (text prompts with an optional response schema), so
   check that before assuming a native mode could run on the leaderboard.
3. **Context.** The incident behind this benchmark happened inside a running agent, after many turns.
   v1.0 has a single turn of about 330 tokens. A more realistic item puts the request after a short
   transcript (a few earlier calls and results). The prompt builder would need a `history` field. A day
   for the code; the items are the cost.
4. **Ground truth for shell and edit items.** Whether a call does what was asked depends on the
   repository's state. v1.0 never executes anything and should stay that way: restrict items to cases
   where the arguments alone decide it.
5. **A way to decline.** v1.0 allows exactly one call and no text. Eight pilot replies refused in prose
   and were scored unparseable. For agent work the right behaviour is often "call a different tool" or
   "tell the user", so an extended version should offer a `report_limitation(reason)` tool or allow text
   after the call, and score declining as its own outcome.

### For the Gemma 4 track specifically

- The pilot had one Gemma-family model, `google/gemma-3-27b-it`: phantom arguments 1.0% (1/105) neutral and
  0/105 instructed, enum violations 24.0% (6/25) and 16.0% (4/25), control score 96.9% (31/32), clean-call
  rate 92.6% (150/162) and 95.7% (155/162). It returned no reasoning. Details in `results/pilot.md`.
- No Gemma 4 model was on the endpoint, so nothing here is evidence about Gemma 4.
- Gemma models are usually run with a chat template in which tools are text in the prompt and the call is
  text in the reply. For that family the text-rendered format of this benchmark is close to how the model
  is really used, which is a stronger position than for models with a dedicated tool-calling API.
- A "new evaluation dataset for agentic software engineering" would need items 1 and 3 above at least.
  The v1.0 items are generic business tools and would not qualify as they are.

## 2. What the pilot said v1.1 should be, and what was done

Status on 2026-10-02: points 1 and 3 are built and validated on 11 models
(`results/v1_1_validation.md`). Point 2 is open. The text below is the plan as written after the pilot.

- Point 1 became the `repurposing` family (28 items, five patterns) plus 12 `matched_control` items.
- Point 3 became the `may_decline` condition, with the fixed reply `{"cannot_do": "..."}`.
- Lessons for anyone adding items to the family: make sure no free-text parameter can carry the request
  (four draft items failed that); write the detector for the specific misuse, not for "the parameter is
  present" (models fill parameters with no-op values such as `min_amount: 0`); give every tempting
  parameter a matched control; read every distinct reply once before trusting a detector.
- Open after v1.1: point 2 below; a decline whose sentence is checked against the item (a keyword list
  per item would keep it deterministic); more `negation` and `bound` items, the two patterns with the
  fewest items and the least effect from the option to decline.

v1.0 is close to saturated: 13 of 24 models score 99% or more. Three changes, in order of value:

1. **A `repurposing` family, 20 to 30 items.** Every tool has a parameter that can absorb the request and
   means something else: `cc` for BCC, `assignee` for author, `labels` for "not labelled", `max_price` for
   "at least", `end_date` for "starting from". Score the call as wrong when that parameter carries the
   value. v1.0 has four such items, found after the fact, and they were the only place where strong
   reasoning models failed (25%, 15 of 60 replies).
2. **Promote `enum_choice` to a score on the `omit` items**, after reviewing each one. Some substitutions
   are fine (Kelvin to `metric`) and some change the question (returned to `cancelled`). The 17 items need
   a per-item list of acceptable values before this can count.
3. **Let the model decline**, as in point 5 above, and report decline, comply-validly, comply-invalidly
   and misuse as four separate rates.

## 3. Cheap experiments the pilot leaves open

- Reasoning on and off inside the same model, where the provider exposes the switch. The pilot's split
  (enum violations 30.0% of 150 without reasoning, 2.0% of 355 with) compares different models.
- Native tool calling for the four Nemotron models, to see whether the original incident reproduces there.
  About 100 phantom-family items per model; at pilot prices under $0.50 for all four.
- Three samples per item at a non-zero temperature for the two models with the most phantom arguments, to
  put an interval on a per-model rate.
