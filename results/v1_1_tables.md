### Per model

Phantom rate = share of parsed replies with at least one argument name the schema does not define, over the four phantom families (conventional, near-miss, inexpressible, nested). Control score = share of control items answered with a schema-valid call that uses the existing parameter correctly. Counts are k/n.

| Model | Items | Phantom, neutral | Phantom, instructed | Paired p | Enum violations, neutral | Enum violations, instructed | Control score, neutral | Control score, instructed | Unparseable (both) | Truncated |
|---|---|---|---|---|---|---|---|---|---|---|
| Hermes-4-405B | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| Qwen3-235B-A22B-Instruct-2507 | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| Qwen3-30B-A3B-Instruct-2507 | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| DeepSeek-V4-Flash-0731 | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| gemma-3-27b-it | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| NVIDIA-Nemotron-3-Nano-30B-A3B | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| Nemotron-3_5-Lightning | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| nemotron-3-super-120b-a12b | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| gpt-oss-120b | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| MiniCPM-V-4_5 | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |
| GLM-5.3-Flash | 100 | n/a | n/a | 1.000 (0 fixed / 0 broken) | n/a | n/a | n/a | n/a | 0/68 | 0 |

### Per family, all models pooled

| Family | Target fault | Neutral | Instructed | Any schema violation, neutral | Any schema violation, instructed |
|---|---|---|---|---|---|
| conventional | phantom_arg | n/a | n/a | n/a | n/a |
| near_miss | phantom_arg | n/a | n/a | n/a | n/a |
| inexpressible | phantom_arg | n/a | n/a | n/a | n/a |
| enum_pressure | out_of_enum | n/a | n/a | n/a | n/a |
| nested | phantom_arg | n/a | n/a | n/a | n/a |
| control | (correct call) | n/a | n/a | n/a | n/a |

### Per family and model, neutral → instructed (target-fault rate, k/n)

| Model | conventional | near_miss | inexpressible | enum_pressure | nested |
|---|---|---|---|---|---|
| Hermes-4-405B | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| Qwen3-235B-A22B-Instruct-2507 | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| Qwen3-30B-A3B-Instruct-2507 | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| DeepSeek-V4-Flash-0731 | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| gemma-3-27b-it | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| NVIDIA-Nemotron-3-Nano-30B-A3B | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| Nemotron-3_5-Lightning | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| nemotron-3-super-120b-a12b | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| gpt-oss-120b | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| MiniCPM-V-4_5 | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |
| GLM-5.3-Flash | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a | n/a → n/a |

### Most-invented argument names (temptation items, all models)

**neutral**: 

**instructed**: 

**may_decline**: `min_rating` ×2 (2 models), `offset` ×1 (1 models), `fragile` ×1 (1 models)

### Models that reasoned before answering vs models that did not

Grouped by whether the provider returned any reasoning at its default setting. The groups are different models, so this is an association, not the effect of reasoning. Core items are the 60 that every model answered.

- No reasoning (5): Hermes-4-405B, Qwen3-235B-A22B-Instruct-2507, Qwen3-30B-A3B-Instruct-2507, gemma-3-27b-it, MiniCPM-V-4_5
- Reasoning (6): DeepSeek-V4-Flash-0731, NVIDIA-Nemotron-3-Nano-30B-A3B, Nemotron-3_5-Lightning, nemotron-3-super-120b-a12b, gpt-oss-120b, GLM-5.3-Flash

| Items | Group | Phantom, neutral | Phantom, instructed | Enum violations, neutral | Enum violations, instructed | Control score, neutral |
|---|---|---|---|---|---|---|
| all answered | no reasoning | n/a | n/a | n/a | n/a | n/a |
| all answered | reasoning | n/a | n/a | n/a | n/a | n/a |
| core 60 | no reasoning | n/a | n/a | n/a | n/a | n/a |
| core 60 | reasoning | n/a | n/a | n/a | n/a | n/a |

Schema-valid ways of getting it wrong, same grouping (all answered items). Repurposed = a value in a parameter that means something else (items with `misuse_params`). Substituted = on enum items where no listed value means what the user asked, a listed value was sent anyway.

| Group | Repurposed, neutral | Repurposed, instructed | Enum substituted, neutral | Enum substituted, instructed |
|---|---|---|---|---|
| no reasoning | n/a | n/a | n/a | n/a |
| reasoning | n/a | n/a | n/a | n/a |

### Schema-valid calls that put the constraint in a parameter meaning something else

Items whose tool has a parameter that can absorb the request but means something different. k/n = models whose call was schema-valid and gave that parameter a value, over models with a parsed reply.

| Item | Parameter | Neutral | Instructed | Phantom instead (neutral) |
|---|---|---|---|---|
| inex-14 | `labels` | 0 | 0 | 0 |
| inex-27 | `cc` | 0 | 0 | 0 |

### Inexpressible items: constraint words written into a string argument (schema-valid)

| Item | Neutral | Instructed |
|---|---|---|
| inex-01 | n/a | n/a |
| inex-14 | n/a | n/a |
| inex-27 | n/a | n/a |

### Enum-pressure items: what happened to the enum parameter

violated = a value outside the enum; listed = a listed value the user did not name; omitted = parameter left out. Items are split by what a valid call can do: `nearest` (a listed value is a fair stand-in, e.g. high for critical) and `omit` (no listed value means what the user asked, so leaving the parameter out is the faithful valid call).


Neutral condition, values with counts:

| Item | Fallback | n | Violated | Listed | Omitted | Values chosen |
|---|---|---|---|---|---|---|

### v1.1: repurposing, per model

Share of complete replies. Repurposed = schema-valid call that puts the request into a parameter that means something else (the item's detector matched). Clean call = valid call without the misuse that gets the expressible parts right. Matched controls are requests for which that same parameter is the right one.

| Model | Reasoned | Condition | Repurposed | Declined | Clean call | Schema fault | Unparseable | Matched controls correct | Matched controls declined |
|---|---|---|---|---|---|---|---|---|---|
| Hermes-4-405B | no | must call | 46.4% (13/28) | 0.0% (0/28) | 39.3% (11/28) | 10.7% (3/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| Hermes-4-405B | no | must call + instruction | 46.4% (13/28) | 0.0% (0/28) | 50.0% (14/28) | 0.0% (0/28) | 0.0% (0/28) | n/a | n/a |
| Hermes-4-405B | no | may decline | 10.7% (3/28) | 78.6% (22/28) | 10.7% (3/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| Qwen3-235B-A22B-Instruct-2507 | no | must call | 46.4% (13/28) | 0.0% (0/28) | 42.9% (12/28) | 10.7% (3/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| Qwen3-235B-A22B-Instruct-2507 | no | must call + instruction | 42.9% (12/28) | 0.0% (0/28) | 50.0% (14/28) | 7.1% (2/28) | 0.0% (0/28) | n/a | n/a |
| Qwen3-235B-A22B-Instruct-2507 | no | may decline | 25.0% (7/28) | 46.4% (13/28) | 21.4% (6/28) | 7.1% (2/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| Qwen3-30B-A3B-Instruct-2507 | no | must call | 60.7% (17/28) | 0.0% (0/28) | 21.4% (6/28) | 17.9% (5/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| Qwen3-30B-A3B-Instruct-2507 | no | must call + instruction | 64.3% (18/28) | 0.0% (0/28) | 17.9% (5/28) | 17.9% (5/28) | 0.0% (0/28) | n/a | n/a |
| Qwen3-30B-A3B-Instruct-2507 | no | may decline | 57.1% (16/28) | 7.1% (2/28) | 21.4% (6/28) | 14.3% (4/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemma-3-27b-it | no | must call | 42.9% (12/28) | 0.0% (0/28) | 42.9% (12/28) | 10.7% (3/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemma-3-27b-it | no | must call + instruction | 28.6% (8/28) | 0.0% (0/28) | 53.6% (15/28) | 17.9% (5/28) | 0.0% (0/28) | n/a | n/a |
| gemma-3-27b-it | no | may decline | 14.3% (4/28) | 57.1% (16/28) | 17.9% (5/28) | 10.7% (3/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| MiniCPM-V-4_5 | no | must call | 57.1% (16/28) | 0.0% (0/28) | 28.6% (8/28) | 14.3% (4/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| MiniCPM-V-4_5 | no | must call + instruction | 57.1% (16/28) | 0.0% (0/28) | 28.6% (8/28) | 14.3% (4/28) | 0.0% (0/28) | n/a | n/a |
| MiniCPM-V-4_5 | no | may decline | 53.6% (15/28) | 0.0% (0/28) | 32.1% (9/28) | 14.3% (4/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| DeepSeek-V4-Flash-0731 | yes | must call | 10.7% (3/28) | 0.0% (0/28) | 89.3% (25/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| DeepSeek-V4-Flash-0731 | yes | must call + instruction | 14.3% (4/28) | 0.0% (0/28) | 85.7% (24/28) | 0.0% (0/28) | 0.0% (0/28) | n/a | n/a |
| DeepSeek-V4-Flash-0731 | yes | may decline | 3.6% (1/28) | 67.9% (19/28) | 28.6% (8/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| NVIDIA-Nemotron-3-Nano-30B-A3B | yes | must call | 21.4% (6/28) | 0.0% (0/28) | 78.6% (22/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| NVIDIA-Nemotron-3-Nano-30B-A3B | yes | must call + instruction | 25.0% (7/28) | 0.0% (0/28) | 75.0% (21/28) | 0.0% (0/28) | 0.0% (0/28) | n/a | n/a |
| NVIDIA-Nemotron-3-Nano-30B-A3B | yes | may decline | 7.1% (2/28) | 75.0% (21/28) | 17.9% (5/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| Nemotron-3_5-Lightning | yes | must call | 10.7% (3/28) | 0.0% (0/28) | 89.3% (25/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| Nemotron-3_5-Lightning | yes | must call + instruction | 3.6% (1/28) | 0.0% (0/28) | 92.9% (26/28) | 0.0% (0/28) | 0.0% (0/28) | n/a | n/a |
| Nemotron-3_5-Lightning | yes | may decline | 0.0% (0/28) | 85.7% (24/28) | 14.3% (4/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| nemotron-3-super-120b-a12b | yes | must call | 21.4% (6/28) | 0.0% (0/28) | 78.6% (22/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| nemotron-3-super-120b-a12b | yes | must call + instruction | 32.1% (9/28) | 0.0% (0/28) | 67.9% (19/28) | 0.0% (0/28) | 0.0% (0/28) | n/a | n/a |
| nemotron-3-super-120b-a12b | yes | may decline | 3.6% (1/28) | 50.0% (14/28) | 46.4% (13/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-oss-120b | yes | must call | 7.1% (2/28) | 0.0% (0/28) | 92.9% (26/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-oss-120b | yes | must call + instruction | 7.1% (2/28) | 0.0% (0/28) | 92.9% (26/28) | 0.0% (0/28) | 0.0% (0/28) | n/a | n/a |
| gpt-oss-120b | yes | may decline | 0.0% (0/28) | 78.6% (22/28) | 21.4% (6/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| GLM-5.3-Flash | yes | must call | 3.6% (1/28) | 0.0% (0/28) | 96.4% (27/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| GLM-5.3-Flash | yes | must call + instruction | 3.6% (1/28) | 0.0% (0/28) | 96.4% (27/28) | 0.0% (0/28) | 0.0% (0/28) | n/a | n/a |
| GLM-5.3-Flash | yes | may decline | 0.0% (0/28) | 53.6% (15/28) | 46.4% (13/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |

### v1.1: repurposing, pooled

| Group | Condition | Repurposed | Declined | Clean call | Schema fault | Other wrong | Unparseable |
|---|---|---|---|---|---|---|---|
| all models | must call | 29.9% (92/308) | 0.0% (0/308) | 63.6% (196/308) | 5.8% (18/308) | 0.6% (2/308) | 0.0% (0/308) |
| all models | must call + instruction | 29.5% (91/308) | 0.0% (0/308) | 64.6% (199/308) | 5.2% (16/308) | 0.6% (2/308) | 0.0% (0/308) |
| all models | may decline | 15.9% (49/308) | 54.5% (168/308) | 25.3% (78/308) | 4.2% (13/308) | 0.0% (0/308) | 0.0% (0/308) |
| no reasoning | must call | 50.7% (71/140) | 0.0% (0/140) | 35.0% (49/140) | 12.9% (18/140) | 1.4% (2/140) | 0.0% (0/140) |
| no reasoning | must call + instruction | 47.9% (67/140) | 0.0% (0/140) | 40.0% (56/140) | 11.4% (16/140) | 0.7% (1/140) | 0.0% (0/140) |
| no reasoning | may decline | 32.1% (45/140) | 37.9% (53/140) | 20.7% (29/140) | 9.3% (13/140) | 0.0% (0/140) | 0.0% (0/140) |
| reasoning | must call | 12.5% (21/168) | 0.0% (0/168) | 87.5% (147/168) | 0.0% (0/168) | 0.0% (0/168) | 0.0% (0/168) |
| reasoning | must call + instruction | 14.3% (24/168) | 0.0% (0/168) | 85.1% (143/168) | 0.0% (0/168) | 0.6% (1/168) | 0.0% (0/168) |
| reasoning | may decline | 2.4% (4/168) | 68.5% (115/168) | 29.2% (49/168) | 0.0% (0/168) | 0.0% (0/168) | 0.0% (0/168) |
| pattern: absence | must call | 30.3% (10/33) | 0.0% (0/33) | 69.7% (23/33) | 0.0% (0/33) | 0.0% (0/33) | 0.0% (0/33) |
| pattern: absence | must call + instruction | 18.2% (6/33) | 0.0% (0/33) | 78.8% (26/33) | 3.0% (1/33) | 0.0% (0/33) | 0.0% (0/33) |
| pattern: absence | may decline | 18.2% (6/33) | 54.5% (18/33) | 27.3% (9/33) | 0.0% (0/33) | 0.0% (0/33) | 0.0% (0/33) |
| pattern: bound | must call | 23.6% (13/55) | 0.0% (0/55) | 70.9% (39/55) | 5.5% (3/55) | 0.0% (0/55) | 0.0% (0/55) |
| pattern: bound | must call + instruction | 27.3% (15/55) | 0.0% (0/55) | 69.1% (38/55) | 3.6% (2/55) | 0.0% (0/55) | 0.0% (0/55) |
| pattern: bound | may decline | 18.2% (10/55) | 41.8% (23/55) | 36.4% (20/55) | 3.6% (2/55) | 0.0% (0/55) | 0.0% (0/55) |
| pattern: enum_substitute | must call | 29.5% (13/44) | 0.0% (0/44) | 56.8% (25/44) | 9.1% (4/44) | 4.5% (2/44) | 0.0% (0/44) |
| pattern: enum_substitute | must call + instruction | 27.3% (12/44) | 0.0% (0/44) | 63.6% (28/44) | 6.8% (3/44) | 2.3% (1/44) | 0.0% (0/44) |
| pattern: enum_substitute | may decline | 13.6% (6/44) | 72.7% (32/44) | 9.1% (4/44) | 4.5% (2/44) | 0.0% (0/44) | 0.0% (0/44) |
| pattern: negation | must call | 18.2% (8/44) | 0.0% (0/44) | 72.7% (32/44) | 9.1% (4/44) | 0.0% (0/44) | 0.0% (0/44) |
| pattern: negation | must call + instruction | 20.5% (9/44) | 0.0% (0/44) | 65.9% (29/44) | 11.4% (5/44) | 2.3% (1/44) | 0.0% (0/44) |
| pattern: negation | may decline | 18.2% (8/44) | 25.0% (11/44) | 47.7% (21/44) | 9.1% (4/44) | 0.0% (0/44) | 0.0% (0/44) |
| pattern: role | must call | 36.4% (48/132) | 0.0% (0/132) | 58.3% (77/132) | 5.3% (7/132) | 0.0% (0/132) | 0.0% (0/132) |
| pattern: role | must call + instruction | 37.1% (49/132) | 0.0% (0/132) | 59.1% (78/132) | 3.8% (5/132) | 0.0% (0/132) | 0.0% (0/132) |
| pattern: role | may decline | 14.4% (19/132) | 63.6% (84/132) | 18.2% (24/132) | 3.8% (5/132) | 0.0% (0/132) | 0.0% (0/132) |

Schema faults in which a detector also matched (counted as schema faults, since a strict tool rejects them): must call: 2; must call + instruction: 2; may decline: 2.

Matched controls, all models: must call: correct 100.0% (132/132), declined 0.0% (0/132), flagged as repurposed 0.0% (0/132); may decline: correct 100.0% (132/132), declined 0.0% (0/132), flagged as repurposed 0.0% (0/132).

Same model and item, must call -> may decline (308 pairs): clean_call -> declined: 123; clean_call -> clean_call: 72; repurposed -> repurposed: 48; repurposed -> declined: 40; schema_fault -> schema_fault: 13; repurposed -> clean_call: 4; schema_fault -> declined: 3; schema_fault -> clean_call: 2; other_wrong -> declined: 2; clean_call -> repurposed: 1.
Repurposed only when it had to call: 44. Repurposed only when it could decline: 1. Exact McNemar p < 0.0001.

### v1.1: how often a decline is used when it is allowed

| Family | Declining is | Declined | Correct |
|---|---|---|---|
| conventional | accepted | 14.5% (16/110) | 98.2% (108/110) |
| near_miss | wrong | 0.0% (0/110) | 100.0% (110/110) |
| inexpressible | accepted | 23.6% (26/110) | 97.3% (107/110) |
| enum_pressure | accepted | 61.8% (68/110) | 88.2% (97/110) |
| nested | accepted | 17.3% (19/110) | 99.1% (109/110) |
| control | wrong | 0.0% (0/110) | 98.2% (108/110) |
| repurposing | accepted | 54.5% (168/308) | 79.9% (246/308) |
| matched_control | wrong | 0.0% (0/132) | 100.0% (132/132) |

### v1.1: repurposing, per item (models that repurposed / complete replies)

| Item | must call | must call + instruction | may decline | Declined when allowed |
|---|---|---|---|---|
| rep-01 | 7/11 | 5/11 | 1/11 | 7/11 |
| rep-02 | 7/11 | 8/11 | 4/11 | 6/11 |
| rep-03 | 6/11 | 6/11 | 3/11 | 7/11 |
| rep-04 | 9/11 | 7/11 | 2/11 | 8/11 |
| rep-05 | 5/11 | 6/11 | 2/11 | 9/11 |
| rep-06 | 1/11 | 2/11 | 0/11 | 9/11 |
| rep-07 | 2/11 | 3/11 | 1/11 | 7/11 |
| rep-08 | 6/11 | 7/11 | 2/11 | 9/11 |
| rep-09 | 5/11 | 5/11 | 4/11 | 3/11 |
| rep-10 | 0/11 | 0/11 | 0/11 | 5/11 |
| rep-11 | 0/11 | 0/11 | 0/11 | 4/11 |
| rep-12 | 0/11 | 0/11 | 0/11 | 10/11 |
| rep-13 | 1/11 | 2/11 | 2/11 | 4/11 |
| rep-14 | 0/11 | 0/11 | 0/11 | 4/11 |
| rep-15 | 3/11 | 3/11 | 2/11 | 2/11 |
| rep-16 | 4/11 | 4/11 | 4/11 | 1/11 |
| rep-17 | 5/11 | 6/11 | 5/11 | 4/11 |
| rep-18 | 0/11 | 1/11 | 0/11 | 4/11 |
| rep-19 | 5/11 | 5/11 | 4/11 | 5/11 |
| rep-20 | 0/11 | 0/11 | 0/11 | 3/11 |
| rep-21 | 3/11 | 3/11 | 1/11 | 7/11 |
| rep-22 | 5/11 | 2/11 | 2/11 | 7/11 |
| rep-23 | 3/11 | 3/11 | 2/11 | 4/11 |
| rep-24 | 2/11 | 1/11 | 2/11 | 7/11 |
| rep-25 | 4/11 | 5/11 | 2/11 | 9/11 |
| rep-26 | 2/11 | 3/11 | 2/11 | 8/11 |
| rep-27 | 2/11 | 2/11 | 2/11 | 5/11 |
| rep-28 | 5/11 | 2/11 | 0/11 | 10/11 |

### Usage

| Model | Calls | Prompt tokens | Completion tokens | Reasoning tokens reported | Calls with reasoning | Cost (USD) |
|---|---|---|---|---|---|---|
| Hermes-4-405B | 168 | 52,069 | 5,306 | 0 | 0 | 0.0680 |
| Qwen3-235B-A22B-Instruct-2507 | 168 | 49,933 | 6,176 | 0 | 0 | 0.0137 |
| Qwen3-30B-A3B-Instruct-2507 | 168 | 49,933 | 6,717 | 0 | 0 | 0.0070 |
| DeepSeek-V4-Flash-0731 | 168 | 49,396 | 37,207 | 31,418 | 168 | 0.0173 |
| gemma-3-27b-it | 168 | 51,168 | 6,255 | 0 | 0 | 0.0070 |
| NVIDIA-Nemotron-3-Nano-30B-A3B | 168 | 51,671 | 47,455 | 0 | 168 | 0.0145 |
| Nemotron-3_5-Lightning | 168 | 51,671 | 137,082 | 131,113 | 168 | 0.0360 |
| nemotron-3-super-120b-a12b | 168 | 51,671 | 32,219 | 24,930 | 168 | 0.0445 |
| gpt-oss-120b | 168 | 59,261 | 25,764 | 0 | 168 | 0.0243 |
| MiniCPM-V-4_5 | 168 | 49,933 | 6,615 | 0 | 0 | 0.0402 |
| GLM-5.3-Flash | 168 | 50,096 | 47,810 | 42,197 | 168 | 0.0314 |
| **total** | 1848 | 566,802 | 358,606 | 229,658 | | 0.3040 |
