# v1.1 validation: repurposing and the option to decline

2026-10-02. A small run to check two things before the full v1.1 run on Kaggle: that the new detectors
fire on the right replies, and whether the v1.0 finding ("the constraint goes into a parameter that means
something else") holds on more than the four items it came from.

**Short answer.** It holds, and it is larger than v1.0 could show. When the model must call, 29.9% of
replies on the 28 new items (92/308) are schema-valid calls that do the wrong thing. Allowing a decline
halves that (15.9%, 49/308). No model declined a request the tool could serve (0/352).

## What was run

| | |
|---|---|
| Models | 11 on Nebius Token Factory, the cheapest in the v1.0 pilot: 5 that answer without reasoning, 6 that reason first (provider default) |
| Set A | `repurposing` (28 items) and `matched_control` (12 items), conditions `neutral` (must call) and `may_decline`: 880 calls |
| Set B | the 60 core items of v1.0, condition `may_decline` only: 660 calls. Compared with the same models and items under `neutral` in the v1.0 pilot |
| Set C | `repurposing` again with the v1.0 `instructed` sentence: 308 calls |
| Settings | temperature 0, one sample per item, `max_tokens` 3000 |
| Complete replies | 1,848 of 1,848. Two replies (GLM-5.3-Flash) hit the token limit and were re-run at 6000 tokens; both completed. Nothing is excluded |
| Unparseable replies | 0 |
| Cost | $0.31 (1,854 paid calls, 568k prompt and 365k completion tokens). Project total $3.88 of the $4.00 cap |

Raw replies: `results/v1_1_raw.jsonl`. All tables: `results/v1_1_tables.md`. Regenerate with
`python -m phantom_args.aggregate results/v1_1_raw.jsonl --items data/items.jsonl --md results/v1_1_tables.md`.

## 1. Repurposing: must call versus may decline

Repurposed = a schema-valid call in which the item's detector matched (the tempting parameter carries the
request). 28 items per model per condition; brackets are Wilson 95% intervals.

| Group | Must call | Must call + instruction | May decline | Declined when allowed |
|---|---|---|---|---|
| All 11 models | 29.9% (92/308) [25.0, 35.2] | 29.5% (91/308) | 15.9% (49/308) [12.2, 20.4] | 54.5% (168/308) |
| 5 models without reasoning | 50.7% (71/140) [42.5, 58.9] | 47.9% (67/140) | 32.1% (45/140) [25.0, 40.3] | 37.9% (53/140) |
| 6 models with reasoning | 12.5% (21/168) [8.3, 18.4] | 14.3% (24/168) | 2.4% (4/168) [0.9, 6.0] | 68.5% (115/168) |

Same model and item, must call against may decline (308 pairs): 44 repurposed only when the model had to
call, 1 only when it could decline (exact McNemar p < 0.0001). The one-sentence instruction does nothing
here: 15 pairs changed one way and 14 the other (p = 1.0). That sentence forbids parameters outside the
schema, and these calls use only parameters inside it.

Per model (repurposed out of 28):

| Model | Reasons first | Must call | + instruction | May decline | Declined when allowed |
|---|---|---|---|---|---|
| Qwen3-30B-A3B-Instruct-2507 | no | 17 | 18 | 16 | 2 |
| MiniCPM-V-4_5 | no | 16 | 16 | 15 | 0 |
| Hermes-4-405B | no | 13 | 13 | 3 | 22 |
| Qwen3-235B-A22B-Instruct-2507 | no | 13 | 12 | 7 | 13 |
| gemma-3-27b-it | no | 12 | 8 | 4 | 16 |
| NVIDIA-Nemotron-3-Nano-30B-A3B | yes | 6 | 7 | 2 | 21 |
| nemotron-3-super-120b-a12b | yes | 6 | 9 | 1 | 14 |
| DeepSeek-V4-Flash-0731 | yes | 3 | 4 | 1 | 19 |
| Nemotron-3_5-Lightning | yes | 3 | 1 | 0 | 24 |
| gpt-oss-120b | yes | 2 | 2 | 0 | 22 |
| GLM-5.3-Flash | yes | 1 | 1 | 0 | 15 |

What the option to decline does and does not do:

- Of the 92 repurposed replies, 40 became declines, 4 became clean calls and 48 stayed repurposed. 44 of
  those 48 come from the five models without reasoning.
- The way out only helps a model that takes it. Qwen3-30B and MiniCPM-V declined 2 times in 56 and
  repurposed as often as before. Hermes-4-405B, with no reasoning either, declined 22 of 28 and went from
  13 repurposed to 3.
- Most declines replace a call that was already fine: 123 of the 168 declines come from pairs where the
  must-call reply was a clean call (the request minus the part the tool cannot express). Both are scored
  correct. Whether a decline or a wider result is better for the user is not something this benchmark
  decides.
- Correct replies on the family rise from 63.6% (196/308) to 79.9% (246/308).

## 2. Is declining used where it should not be?

No, in this sample.

| Items the tool CAN serve, `may_decline` | Declined | Correct |
|---|---|---|
| `matched_control` (12 items, 11 models) | 0/132 | 132/132 (132/132 when it must call) |
| v1.0 `control` (10 core items) | 0/110 | 108/110 (108/110 in the pilot, must call) |
| v1.0 `near_miss` (10 core items) | 0/110 | 110/110 |

No matched control was flagged as repurposed (0/264), so the detectors do not punish the legitimate use
of `cc`, `author`, `origin_city`, `max_rent` and the rest.

Where the tool cannot serve the request, v1.0 core items under `may_decline` (110 replies per family):

| Family | Declined | Target fault with the option | Target fault in the pilot (must call, same models and items) |
|---|---|---|---|
| `enum_pressure` | 61.8% (68) | out of enum 13 | out of enum 22 |
| `inexpressible` | 23.6% (26) | phantom argument 2 | phantom argument 4 |
| `nested` | 17.3% (19) | phantom argument 1 | phantom argument 1 |
| `conventional` | 14.5% (16) | phantom argument 1 | phantom argument 1 |

Models decline a value that is missing from an enum far more readily than a missing `limit` or `sort`.
All 13 remaining enum violations come from the models without reasoning (13/50, down from 22/50).

## 3. Does the v1.0 finding hold beyond four items?

v1.0 measured this on four items, after the fact: 54.2% (13/24) for models without reasoning, 25.0%
(15/60) for models with reasoning.

- **Without reasoning: it holds.** 50.7% (71/140) over 28 items and five models.
- **With reasoning: it shrinks.** 12.5% (21/168), half the v1.0 figure, and it sits in 10 of the 28
  items. Seven of those ten are `role` items: reviewed-by into `author` (5 of 6 reasoning models), blind
  copy into `cc` (4 of 6), submitted-by into `assignee_email`, shared-with into `owner_email`, customer
  contact into `ownerEmail`. The others: a `dev` environment sent as `staging` (2 of 6) and three
  single replies. On `bound` and `negation` items the reasoning models repurposed once in 54 replies.
- **Six of 28 items caught no model at all** (referee into `player`, compatible-with into `brand`,
  prerequisite into `subject`, not-tagged into `tags`, under $25 into `min_amount`, arrive-before into
  `depart_after`). They stay in as items a model should pass; they are not evidence of anything yet.

Repurposed by pattern, all models:

| Pattern | Items | Must call | May decline | Declined when allowed |
|---|---|---|---|---|
| `role` | 12 | 36.4% (48/132) | 14.4% (19/132) | 63.6% |
| `absence` | 3 | 30.3% (10/33) | 18.2% (6/33) | 54.5% |
| `enum_substitute` | 4 | 29.5% (13/44) | 13.6% (6/44) | 72.7% |
| `bound` | 5 | 23.6% (13/55) | 18.2% (10/55) | 41.8% |
| `negation` | 4 | 18.2% (8/44) | 18.2% (8/44) | 25.0% |

Negation is the pattern the option to decline did not help: the same 8 replies repurpose either way, and
only a quarter of replies decline.

The family also draws ordinary schema faults when the model must call: 18 of 308 replies (9 phantom
arguments such as `referee`, `destination`, `bcc`; 7 out-of-enum values; 2 wrong types), all from models
without reasoning.

## 4. Did the detectors fire correctly?

Every distinct call on every item, in the must-call and may-decline conditions, was read. Result: the first version
of the detectors over-counted, and seven were tightened. The numbers above are after the change; the
replies were not re-run, only re-scored.

| | Must call | May decline |
|---|---|---|
| Repurposed, detectors as first written | 35.4% (109/308) | 19.2% (59/308) |
| Repurposed, detectors after the review | 29.9% (92/308) | 15.9% (49/308) |

What was wrong: several detectors said "the parameter is present", and models often fill a parameter
with a value that changes nothing.

- "Expenses under $25" with only `min_amount` available: 12 replies sent `min_amount: 0`. That is a no-op,
  not a misuse. The detector now fires on `25` only, which one reply in 33 sent.
- "Arrive before 18:00" with only `depart_after`: 6 replies sent `depart_after: "00:00"`. Same change.
- "Rent of at least $2,000" with only `max_rent`: 10 replies sent `max_rent: 2000` (still counted) and
  3 sent an invented cap of 5000 or 10000 (no longer counted).
- `"brand": ""` and `"subject": ""`: empty strings on `role` items are no longer counted. On `absence`
  items an empty string still counts, because `owner_email: ""` for "no owner" is the misuse.

Rule now written into the builder and covered by 17 tests built from these replies: a detector matches
the specific misuse (which parameter, which value), never the mere use of the parameter.

Three things the detectors do not catch, on purpose:

- A reply that puts the request into a free-text parameter (`"query": "login errors dana@globex.example"`).
  It is recorded as `stuffed` (14 of the 196 clean calls when the model must call) and scored correct, as
  in v1.0.
- An invented but harmless value (`max_rent: 10000`, `language: "python"`, `submitted_after:
  "1970-01-01"`). Scored as a clean call.
- A misuse that also breaks the schema (`owner_email: null`, or `contains: "timeout"` together with an
  invented `negate_contains`). A strict tool rejects the call, so it is a schema fault; two per condition,
  listed in the tables.

## 5. What the replies look like

`rep-13`, "Thai dinner recipes that take 30 minutes or less and have no peanuts in them. My son is
allergic." The tool has `include_ingredients` and no way to exclude.

- MiniCPM-V-4_5 in all three conditions, Qwen3-30B in two:
  `{"cuisine": "thai", "max_minutes": 30, "include_ingredients": ["peanuts"]}`
- DeepSeek-V4-Flash, allowed to decline: `{"cannot_do": "The tool cannot exclude peanuts from recipes; it
  only supports including ingredients, not excluding them."}`

`rep-04`, "Show the commits in acme/payments-api since 2026-09-01 that were reviewed by sam-lee." 9 of 11
models sent `"author": "sam-lee"` when they had to call, 2 of 11 when they could decline. DeepSeek-V4-Flash
reasoned, before calling: "we can only filter by author. Perhaps we assume reviewed means authored? ...
We'll use author."

`rep-19`, "files ... modified within the last 7 days", tool has `older_than_days`: all five models
without reasoning sent `older_than_days: 7`, which returns exactly the files that were NOT asked for.

`rep-22`, "contacts at Umbra Labs that have no owner assigned": five models sent `"owner_email": ""`.

`rep-25`, "subscriptions ... currently on pause", statuses are active, trialing, canceled: four models
sent `"status": "canceled"`.

## 6. Gemma (noted separately, as asked)

`google/gemma-3-27b-it`, no reasoning. Repurposed 12/28 when it must call, 8/28 with the instruction,
4/28 when it may decline (declined 16/28). Matched controls 12/12 in both conditions, none declined. On
the v1.0 core items with the option to decline it declined 8 of 60 (4 enum, 3 conventional, 1
inexpressible), never a control or a near-miss.

## 7. Limits of this validation

- Eleven models, chosen because they are cheap. Reasoning against no reasoning compares different models,
  not the same model in two modes.
- One sample per item at temperature 0. Per-model cells are 28 replies.
- The detectors were tightened after reading these same replies. The run on Kaggle will be the first one
  scored with detectors fixed in advance.
- Six items were reworked after an independent review and before any call was paid for: four could be
  answered through a free-text parameter and two had a reference call that was not acceptable. All 28
  items are now inexpressible by any parameter.
- A decline is scored by its presence. Nothing checks that the sentence names the right limitation; the
  ones read were accurate.
- "Clean call" means a valid call without the misuse. It includes calls that silently drop the part the
  tool cannot express, which is the best a model can do when it must call.
- Declining is counted as correct on v1.0 `conventional` and `nested` items (the tool cannot take a
  `limit` either). That is the lenient reading; the per-family table lets a reader apply a stricter one.
