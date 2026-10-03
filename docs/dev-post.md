---
title: "'No peanuts' became include_ingredients: [\"peanuts\"]: a benchmark for tool calls a validator cannot catch"
published: false
tags: devchallenge, kagglechallenge, ai, machinelearning
---

*This is a submission for the [DEV x Kaggle Benchmarking Challenge](https://dev.to/challenges/kaggle-2026-09-23).*

## What I Benchmarked

An agent I was running called a ranking tool with `limit: 8`. The tool had no `limit` parameter and rejected
the call: `unknown argument "limit"`. I wanted to know how often models do that, so I built a benchmark
around one question: **what does a model do when the tool cannot do what was asked?**

Each item is one tool, written as a JSON Schema with `additionalProperties: false` everywhere, and one user
request that asks for something just outside it. The model answers with one tool call as JSON text. A
web-search tool with only `query` and `safe_search`, and a user who wants "the top 5 results", is the
classic case: does the model invent `max_results`?

That was the plan. The item the post is really about looks like this instead:

> Thai dinner recipes that take 30 minutes or less and have no peanuts in them. My son is allergic.

The tool has `cuisine`, `max_minutes` and `include_ingredients`. It has no way to exclude anything. A model
that reaches for the closest parameter sends:

```json
{"cuisine": "thai", "max_minutes": 30, "include_ingredients": ["peanuts"]}
```

That call is valid against the schema. A validator passes it. It asks for the one thing the user said
could hurt their child.

The benchmark has 202 items over 75 invented tools, in eight families:

- **conventional** (31): the request invites a parameter most APIs have and this tool lacks (`limit`,
  `page`, `sort`).
- **near_miss** (23): the usual name for a parameter that exists under another name (`max_results` when
  the tool has `pageSize`).
- **inexpressible** (30): a filter the tool cannot express at all ("published after 2020").
- **enum_pressure** (25): a value missing from an enum (Kelvin when the enum is metric/imperial).
- **nested** (21): an unknown key inside an object or array item.
- **repurposing** (28): a parameter that exists and means something else (`cc` for a blind copy,
  `older_than_days` for "modified in the last 7 days", `include_ingredients` for an allergy).
- **control** (32) and **matched_control** (12): nothing is missing; the right parameter must be used.
  The matched controls use the same tools as the repurposing items, with a request where `cc` or
  `author` really is the right parameter. They are there so that a detector that fires on "used `cc`"
  instead of "misused `cc`" would show up as false alarms.

Three prompt conditions:

- `neutral`: answer with exactly one call.
- `instructed`: plus "Use only the parameters defined in the tool's schema; do not add any parameter that
  is not listed there."
- `may_decline`: plus permission to reply `{"cannot_do": "<one sentence>"}` instead of calling. A decline
  is correct where the tool cannot serve the request and wrong where it can, so declining everything does
  not pay.

Scoring is JSON Schema validation plus a fixed check per item, written before the run (for example: on the
peanut item, `include_ingredients` containing "peanut" is a misuse). No model grades any reply.

## Models Tested

**On Kaggle (the leaderboard run).** Eleven models from Kaggle's list, each on all 202 items in all three
conditions, temperature 0, one sample per item, reasoning left at the provider default. Kaggle does not
return reasoning text, so "reasons" below is inferred from output tokens: a model that reports several
times more output tokens than its visible reply is reasoning before it answers.

| Model (Kaggle slug) | Lab | Reasons by default | Mean output tokens (neutral) | Cost, 606 calls |
|---|---|---|---|---|
| claude-opus-5-default | Anthropic | unclear (about 2x the visible reply) | 66 | $2.3730 |
| claude-sonnet-5-default | Anthropic | unclear (about 2.7x) | 88 | $1.0657 |
| gpt-5.5-2026-04-23 | OpenAI | unclear (about 2.4x) | 74 | $2.2980 |
| gemini-3.7-flash | Google | yes (hidden) | 231 | $0.7804 |
| gemini-3.5-flash-lite | Google | no | 39 | $0.1129 |
| gemma-4-31b-it | Google | yes (hidden) | 300 | $0.1461 |
| gemma-4-26b-a4b-it | Google | yes (hidden) | 317 | $0.1636 |
| gpt-5.4-mini-2026-03-17 | OpenAI | no | 33 | $0.2246 |
| gpt-5.4-nano-2026-03-17 | OpenAI | no | 34 | $0.0615 |
| gpt-oss-20b | OpenAI | yes (hidden) | 152 | $0.0295 |
| claude-haiku-4-5-20251001 | Anthropic | no (its tokens are visible prose) | 82 | $0.4172 |

In total: 6,666 calls, $7.67 of Kaggle's free model quota (costs as reported per call by Kaggle's model
proxy). Counting test tasks and superseded runs, the project used $14.43 of the quota.

**Locally, before Kaggle (labelled "local" below).** Two runs on Nebius Token Factory, temperature 0, one
sample per item:

- *Pilot (v1.0):* every text model Nebius listed on 2026-10-02, 24 open-weight models (Qwen, DeepSeek,
  Kimi, GLM, Nemotron, gpt-oss, Gemma 3, Hermes, MiniMax and others), the first six families, `neutral` and
  `instructed`. 6,552 calls, $3.57.
- *Validation (v1.1):* the 11 cheapest of those, 5 that answer directly and 6 that reason first, on the
  repurposing family, the matched controls and the 60 core items, all three conditions. 1,848 calls, $0.31.

## Findings

### 1. The failure I built the benchmark for is almost absent

Local pilot: models invented a parameter name in **0.9%** of replies (20 of 2,127) on the families built to
provoke it. 19 of 24 models never did it. A missing `limit`, `page` or `sort` drew 3 phantom arguments in
618 replies, all from one model. The four NVIDIA Nemotron models, the family from the original incident,
produced none in 838 replies.

Kaggle, neutral: it is near zero for every model. **2 of 1,148** replies (0.2%) on those families named a
parameter the schema does not have, and nine of the eleven models never did. The two: gpt-5.4-mini added
`min_rating: 4` to a product search that has no rating filter, and gpt-oss-20b answered a request to list
files with `{"path": "/", "depth": 2}`, addressed to `repo_browser.print_tree`, a tool it was not given.

This is a text-format test (the schema is in the prompt, the call is JSON text), so it says nothing about
native tool-calling APIs. In this format, the obvious failure is mostly gone.

### 2. What replaces it is a call that passes validation and does something else

Local validation, 28 repurposing items, 11 models, must call: **29.9%** of replies (92 of 308, 95% CI
25-35%) were schema-valid calls that put the request into a parameter that means something else. The same
tools with a request where that parameter is right: 132 of 132 correct, no false alarms.

The cases that stayed with me:

- "Commits reviewed by sam-lee", the tool has `author`: 9 of 11 models sent `"author": "sam-lee"`. One
  reasoned first: "we can only filter by author. Perhaps we assume reviewed means authored? ... We'll use
  author."
- "Files modified within the last 7 days", the tool has `older_than_days`: all five models that answer
  without reasoning sent `older_than_days: 7`, which returns exactly the files that were not asked for.
- "Subscriptions currently on pause", statuses `active`, `trialing`, `canceled`: 4 of 11 sent `canceled`.
- The peanut call above: one model in all three conditions, another in two. Rare (5 of 33 replies), and the
  one I would least want in production.

In the pilot this showed up on four items before I knew to look for it. Asked to BCC an address with a tool
that has only `cc`, 14 of 24 models put it in `cc`. Of the 18 reasoning models, 11 did it, and all 11 had
written in their reasoning that the tool has no BCC. One explained: "There is no way to indicate
limitation. Since must call tool, use cc."

Models that reason first do much better (12.5% against 50.7% for those that do not), but they are not
immune: 5 of 6 still sent reviewed-by as `author`.

Kaggle, neutral, 28 repurposing items per model: the spread runs from **0 to 13**. gemma-4-31b and
claude-opus-5 repurposed nothing; gpt-5.4-nano repurposed 13 of 28 (46.4%). The three frontier models are
near zero but not all at it: claude-opus-5 0, gpt-5.5 1, claude-sonnet-5 2. Pooled over the eleven models,
46 of 308 replies (14.9%). The matched controls again drew no false alarms: 396 replies over all runs,
none flagged.

| Model | Repurposed, neutral (of 28) |
|---|---|
| claude-opus-5 | 0 |
| gemma-4-31b | 0 |
| gemini-3.7-flash | 1 |
| gpt-5.5 | 1 |
| claude-sonnet-5 | 2 |
| gemma-4-26b-a4b | 4 |
| claude-haiku-4-5 | 5 |
| gpt-oss-20b | 5 |
| gemini-3.5-flash-lite | 6 |
| gpt-5.4-mini | 9 |
| gpt-5.4-nano | 13 |

The same items did the damage. "Commits reviewed by sam-lee" became `author` for 4 of 11, and so did
"modified within the last 7 days" as `older_than_days: 7`. "Subscriptions on pause" became `canceled` for 3.
The peanut item caught one model, gpt-5.4-mini, which sent `"include_ingredients": ["no peanuts"]`: the
negation went into the inclusion filter as text. The item that caught the most was "songs from 2019 that
Dana Okafor wrote for other singers", with a tool that filters only by performing `artist`: 7 of 11 sent
`"artist": "Dana Okafor"`, which returns the songs she sang herself. That was one of claude-sonnet-5's two
misses and gemini-3.7-flash's only wrong answer in 202. Sonnet's other miss was the BCC item: the blind copy
went into `cc`, as it did for four of the smaller models. gpt-5.5's one miss: "contacts at Umbra Labs that
have no owner assigned" became `owner_email: ""`.

The four models that reason by default repurposed 10 of 112 (8.9%); the four that clearly do not, 33 of 112
(29.5%); the three frontier models, where output tokens do not settle it, 3 of 84. Same direction as
locally, with the same caveat (section 5).

### 3. Let the model say no, and half of it goes away

Local validation. One added sentence (you may reply `{"cannot_do": ...}`) took repurposed replies from
**29.9% to 15.9%** (92 to 49 of 308). Same model and item: 44 got better, 1 got worse (exact McNemar
p < 0.0001). For models that reason first: 12.5% to 2.4%.

Nobody abused the exit: 0 declines in 352 replies where the tool could serve the request.

It only helps a model that takes it. Two of the eleven declined twice in 56 chances and repurposed as often
as before. Hermes-4-405B, which also answers without reasoning, declined 22 of 28 and went from 13
repurposed replies to 3.

Kaggle, all eleven models: repurposed replies went from **14.9% to 6.8%** (46 to 21 of 308). Same model and
item: 28 got better, 3 got worse (exact McNemar p < 0.0001). Eight of the eleven repurposed nothing with the
option to decline, including all three frontier models. The three that did not get there are three of the
four that answer without reasoning: claude-haiku-4-5 went from 5 to 3, gpt-5.4-mini from 9 to 5.

Declines where the tool could not serve the request: 571 of 1,485 (38.5%); on the repurposing items, 183
of 308, with claude-sonnet-5 declining 26 of 28 and gemini-3.7-flash 25. Declines where it could: 2 of 737
(0 of 132 matched controls, 0 of 253 near misses, 2 of 352 controls). Both were the Gemma models on the
same item, news from September 2026 with a tool described as covering the last 12 months. gemma-4-31b
explained that the tool "cannot search for news articles from the future". The prompt gives no date.

The same split as locally: gpt-5.4-nano declined 3 times in 135 chances and repurposed 13 of 28 in both
conditions.

The "only use parameters in the schema" sentence, which is what most people add when tool calls go wrong,
did nothing locally: 92 to 91. It forbids inventing parameters, and these calls use only real ones. On
Kaggle it did something, less than the decline option: 46 to 34 of 308 (18 better, 6 worse, exact McNemar
p = 0.023), four of the twelve from gpt-oss-20b alone.

The part I cannot settle: 123 of the 168 declines replaced a call that was already acceptable (the request
minus the part the tool cannot express). Is "the tool can't do that" better than a wider result the caller
can filter? The benchmark scores both as correct.

### 4. Where the schema does break, it breaks at the enum

Local pilot: **10.3%** of replies sent a value not on the enum list (52 of 505), against 0.5% for a missing
`limit` or `page`. Portuguese for a language enum without it (9 of 18 models), a "legal" department that
does not exist (7 of 23). One model's reasoning: "Since "neurology" is not in the enum, I should still
attempt the call - the system will handle the validation."

When no listed value fits, models split: leave the parameter out (51%), send some other listed value
(35%), send the unlisted one (14%). "Which orders were returned?" became `status: "cancelled"` for 5 of 18.

Kaggle, neutral: 7 of 260 parsed replies (2.7%) sent a value off the list, and only one model stands out.
gpt-5.4-mini did it 3 times in 25: a library branch "northgate", a "legal" department, a "winter" term.
gemini-3.5-flash-lite and claude-sonnet-5 each sent "pt" for Portuguese once, gpt-5.4-nano sent "northgate"
once, gpt-oss-20b sent an empty department once, and the other six never did.

claude-haiku-4-5 handled the enum items differently: on 12 of 25 it did not call at all and explained in
prose that the tool could not do it, although the prompt asks for exactly one call. Those 12, and 3 more on
repurposing items, are 15 of its 23 wrong answers in `neutral` (88.6%). gpt-oss-20b did the same on 5
items and returned an empty reply on 6.

### 5. What the data does not support

- That reasoning causes the gap. The models that do not reason are different models, mostly older. Running
  one model with reasoning on and off is the obvious next experiment. The Kaggle run has the same problem:
  its reasoning and non-reasoning groups are different models, no model was run both ways, and for the
  three frontier models the token counts do not say whether they reasoned.
- Rankings between models one or two items apart. Per-model cells are 28 items on the repurposing family.
- Anything about native tool calling.
- The detectors on the new family were tightened after I read every local reply: several fired on
  `min_amount: 0`, a value that changes nothing. That took the local figure from 109 to 92. The Kaggle run
  is the first scored with detectors fixed in advance.
- Six of the 28 repurposing items caught no model locally, and none of the six caught any of the eleven
  Kaggle models in any condition either.
- On the original 162 items the score saturates: 13 of 24 local models scored 99% or above. The new family
  is what separates models. That held on Kaggle: in `neutral`, five of the eleven models scored 162 of 162
  on the original items and three more scored 160 or 161, while on the 28 repurposing items the same eleven
  ranged from 0 to 13 repurposed replies.

## My Benchmark

https://www.kaggle.com/benchmarks/tasks/bowen1314/phantom-args-neutral

The public task is the `neutral` condition; `instructed` and `may_decline` ran as separate private tasks
from the same notebook, and every reply from all three is in the repository
(`results/kaggle_cli/kaggle_raw.jsonl`). The task reports one number per model: the share of requests
answered correctly, meaning a schema-valid call that does not misuse a parameter, or, in `may_decline`, a
decline where declining is right. 100% means every call would pass a strict validator and none of them quietly asked for
the wrong thing. It does not mean the model asks the user a clarifying question when it should; the format
does not allow one.

Limits, in short: text-format calls only; temperature 0 and one sample per item; per-item checks are
narrow by design (they catch the specific misuse, not every bad call); a decline is scored by its
presence, not by whether its sentence is accurate.

How it got here: v1.0 had six families and was built to catch invented parameters. The pilot found almost
none, and four items that happened to allow a parameter swap showed the bigger effect. v1.1 turned those
four into a family of 28 with matched controls and added the option to decline. The v1.0 items, prompts
and scoring are frozen by a hash of every prompt, so v1.0 numbers stay comparable.

Code, items, every reply and both local write-ups: https://github.com/Bowen1314/phantom-args.

*AI assistance: Claude (Anthropic) did essentially all of the work: the items and tools, the scoring code
and its tests, the local and Kaggle runs, the analysis, and this post. I chose to enter, set up the
accounts and the Kaggle token, and approved publishing. Every number comes from code in the repository,
and Claude checked each one against the raw reply files.*
