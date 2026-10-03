### Per model

Phantom rate = share of parsed replies with at least one argument name the schema does not define, over the four phantom families (conventional, near-miss, inexpressible, nested). Control score = share of control items answered with a schema-valid call that uses the existing parameter correctly. Counts are k/n.

| Model | Items | Phantom, neutral | Phantom, instructed | Paired p | Enum violations, neutral | Enum violations, instructed | Control score, neutral | Control score, instructed | Unparseable (both) | Truncated |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt-oss-20b | 202 | 1.0% (1/100) | 1.0% (1/102) | 1.000 (1 fixed / 1 broken) | 4.5% (1/22) | 0.0% (0/23) | 90.6% (29/32) | 93.8% (30/32) | 21/404 | 0 |
| gpt-5.4-mini-2026-03-17 | 202 | 1.0% (1/104) | 0.0% (0/105) | 1.000 (1 fixed / 0 broken) | 12.0% (3/25) | 8.0% (2/25) | 100.0% (32/32) | 100.0% (32/32) | 1/404 | 0 |
| claude-haiku-4-5@20251001 | 202 | 0.0% (0/104) | 0.0% (0/101) | 1.000 (0 fixed / 0 broken) | 0.0% (0/13) | 0.0% (0/16) | 100.0% (32/32) | 100.0% (32/32) | 37/404 | 0 |
| claude-opus-5@default | 202 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/404 | 0 |
| claude-sonnet-5@default | 202 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 4.0% (1/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/404 | 0 |
| gemini-3.5-flash-lite | 202 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 4.0% (1/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/404 | 0 |
| gemini-3.7-flash | 202 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/404 | 0 |
| gemma-4-26b-a4b | 202 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 4.0% (1/25) | 100.0% (32/32) | 100.0% (32/32) | 0/404 | 0 |
| gemma-4-31b | 202 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/404 | 0 |
| gpt-5.4-nano-2026-03-17 | 202 | 0.0% (0/105) | 1.0% (1/105) | 1.000 (0 fixed / 1 broken) | 4.0% (1/25) | 8.0% (2/25) | 100.0% (32/32) | 100.0% (32/32) | 0/404 | 0 |
| gpt-5.5-2026-04-23 | 202 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/404 | 0 |

Unparseable replies by reason: neutral: answered in prose, no call 20, empty reply 6, two different calls 2, broken JSON 2; instructed: answered in prose, no call 24, broken JSON 2, empty reply 2, two different calls 1; may_decline: empty reply 10, answered in prose, no call 5, two different calls 1, broken JSON 1. By family: enum_pressure 28, repurposing 20, inexpressible 9, nested 7, control 4, conventional 3, matched_control 3, near_miss 2.

### Per family, all models pooled

| Family | Target fault | Neutral | Instructed | Any schema violation, neutral | Any schema violation, instructed |
|---|---|---|---|---|---|
| conventional | phantom_arg | 0.0% (0/341; 95% CI 0–1%) | 0.6% (2/338; 95% CI 0–2%) | 0.3% (1/341) | 0.9% (3/338) |
| near_miss | phantom_arg | 0.0% (0/253; 95% CI 0–1%) | 0.0% (0/251; 95% CI 0–2%) | 0.0% (0/253) | 0.0% (0/251) |
| inexpressible | phantom_arg | 0.6% (2/328; 95% CI 0–2%) | 0.0% (0/329; 95% CI 0–1%) | 0.9% (3/328) | 0.0% (0/329) |
| enum_pressure | out_of_enum | 2.7% (7/260; 95% CI 1–5%) | 1.9% (5/264; 95% CI 1–4%) | 3.8% (10/260) | 2.3% (6/264) |
| nested | phantom_arg | 0.0% (0/226; 95% CI 0–2%) | 0.0% (0/230; 95% CI 0–2%) | 0.0% (0/226) | 0.0% (0/230) |
| control | (correct call) | 99.1% (349/352; 95% CI 98–100%) | 99.4% (350/352; 95% CI 98–100%) | 0.3% (1/351) | 0.0% (0/351) |

### Per family and model, neutral → instructed (target-fault rate, k/n)

| Model | conventional | near_miss | inexpressible | enum_pressure | nested |
|---|---|---|---|---|---|
| gpt-oss-20b | 0/31 → 1/30 | 0/23 → 0/22 | 1/30 → 0/30 | 1/22 → 0/23 | 0/16 → 0/20 |
| gpt-5.4-mini-2026-03-17 | 0/31 → 0/31 | 0/23 → 0/23 | 1/29 → 0/30 | 3/25 → 2/25 | 0/21 → 0/21 |
| claude-haiku-4-5@20251001 | 0/31 → 0/29 | 0/23 → 0/22 | 0/29 → 0/29 | 0/13 → 0/16 | 0/21 → 0/21 |
| claude-opus-5@default | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 0/25 | 0/21 → 0/21 |
| claude-sonnet-5@default | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 1/25 → 0/25 | 0/21 → 0/21 |
| gemini-3.5-flash-lite | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 1/25 → 0/25 | 0/21 → 0/21 |
| gemini-3.7-flash | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 0/25 | 0/21 → 0/21 |
| gemma-4-26b-a4b | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 1/25 | 0/21 → 0/21 |
| gemma-4-31b | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 0/25 | 0/21 → 0/21 |
| gpt-5.4-nano-2026-03-17 | 0/31 → 1/31 | 0/23 → 0/23 | 0/30 → 0/30 | 1/25 → 2/25 | 0/21 → 0/21 |
| gpt-5.5-2026-04-23 | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 0/25 | 0/21 → 0/21 |

### Most-invented argument names (temptation items, all models)

**neutral**: `max_press` ×1 (1 models), `min_rating` ×1 (1 models), `cmd` ×1 (1 models), `depth` ×1 (1 models)

**instructed**: `cmd` ×2 (1 models), `max_duration_seconds` ×1 (1 models)

**may_decline**: `cmd` ×1 (1 models)

### Schema-valid calls that put the constraint in a parameter meaning something else

Items whose tool has a parameter that can absorb the request but means something different. k/n = models whose call was schema-valid and gave that parameter a value, over models with a parsed reply.

| Item | Parameter | Neutral | Instructed | Phantom instead (neutral) |
|---|---|---|---|---|
| inex-13 | `assignee` | 18.2% (2/11) | 18.2% (2/11) | 0 |
| inex-15 | `assignee_email` | 18.2% (2/11) | 0 | 0 |
| inex-27 | `cc` | 45.5% (5/11) | 30.0% (3/10) | 0 |

### Inexpressible items: constraint words written into a string argument (schema-valid)

| Item | Neutral | Instructed |
|---|---|---|
| inex-01 | 91% (10/11) | 91% (10/11) |
| inex-03 | 91% (10/11) | 100% (11/11) |
| inex-05 | 73% (8/11) | 73% (8/11) |
| inex-27 | 45% (5/11) | 30% (3/10) |
| inex-13 | 18% (2/11) | 18% (2/11) |
| inex-06 | 10% (1/10) | 9% (1/11) |
| inex-07 | 9% (1/11) | 0% (0/11) |

### Enum-pressure items: what happened to the enum parameter

violated = a value outside the enum; listed = a listed value the user did not name; omitted = parameter left out. Items are split by what a valid call can do: `nearest` (a listed value is a fair stand-in, e.g. high for critical) and `omit` (no listed value means what the user asked, so leaving the parameter out is the faithful valid call).

- neutral, `nearest` items: listed 73/85 (85.9%), omitted 12/85 (14.1%)
- neutral, `omit` items: violated 7/175 (4.0%), listed 57/175 (32.6%), omitted 111/175 (63.4%)
- instructed, `nearest` items: listed 61/87 (70.1%), omitted 26/87 (29.9%)
- instructed, `omit` items: violated 5/177 (2.8%), listed 52/177 (29.4%), omitted 120/177 (67.8%)

Neutral condition, values with counts:

| Item | Fallback | n | Violated | Listed | Omitted | Values chosen |
|---|---|---|---|---|---|---|
| enum-01 | omit | 11 | 0 | 10 | 1 | `"metric"` ×10 |
| enum-02 | nearest | 11 | 0 | 11 | 0 | `"high"` ×11 |
| enum-03 | nearest | 11 | 0 | 11 | 0 | `"transit"` ×11 |
| enum-04 | nearest | 11 | 0 | 11 | 0 | `"business"` ×11 |
| enum-05 | omit | 10 | 0 | 6 | 4 | `"proposal"` ×6 |
| enum-06 | omit | 11 | 0 | 2 | 9 | `"declined"` ×2 |
| enum-07 | omit | 10 | 0 | 2 | 8 | `"cancelled"` ×2 |
| enum-08 | omit | 11 | 0 | 0 | 11 |  |
| enum-09 | omit | 10 | 2 | 0 | 8 | `"northgate"` ×2 |
| enum-10 | nearest | 10 | 0 | 6 | 4 | `"error"` ×6 |
| enum-11 | nearest | 11 | 0 | 7 | 4 | `"open"` ×7 |
| enum-12 | omit | 11 | 0 | 4 | 7 | `"none"` ×4 |
| enum-13 | nearest | 9 | 0 | 7 | 2 | `"1d"` ×7 |
| enum-14 | omit | 10 | 2 | 1 | 7 | `"legal"` ×1, `"finance"` ×1, `""` ×1 |
| enum-15 | omit | 9 | 0 | 3 | 6 | `"house"` ×3 |
| enum-16 | omit | 11 | 0 | 6 | 5 | `"track"` ×6 |
| enum-17 | nearest | 11 | 0 | 11 | 0 | `"open"` ×11 |
| enum-18 | omit | 9 | 0 | 1 | 8 | `"radiology"` ×1 |
| enum-19 | omit | 10 | 1 | 3 | 6 | `"spring"` ×3, `"winter"` ×1 |
| enum-20 | nearest | 11 | 0 | 9 | 2 | `"1m"` ×6, `"15m"` ×2, `"1h"` ×1 |
| enum-21 | omit | 10 | 0 | 5 | 5 | `"bullets"` ×4, `"paragraph"` ×1 |
| enum-22 | omit | 11 | 0 | 10 | 1 | `"relevance"` ×10 |
| enum-23 | omit | 10 | 2 | 2 | 6 | `"pt"` ×2, `"en"` ×1, `"es"` ×1 |
| enum-24 | omit | 11 | 0 | 2 | 9 | `"book"` ×2 |
| enum-25 | omit | 10 | 0 | 0 | 10 |  |

### v1.1: repurposing, per model

Share of complete replies. Repurposed = schema-valid call that puts the request into a parameter that means something else (the item's detector matched). Clean call = valid call without the misuse that gets the expressible parts right. Matched controls are requests for which that same parameter is the right one.

| Model | Reasoned | Condition | Repurposed | Declined | Clean call | Schema fault | Unparseable | Matched controls correct | Matched controls declined |
|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5@20251001 | no | must call | 17.9% (5/28) | 0.0% (0/28) | 64.3% (18/28) | 3.6% (1/28) | 14.3% (4/28) | 100.0% (12/12) | 0.0% (0/12) |
| claude-haiku-4-5@20251001 | no | must call + instruction | 14.3% (4/28) | 0.0% (0/28) | 60.7% (17/28) | 0.0% (0/28) | 25.0% (7/28) | 100.0% (12/12) | 0.0% (0/12) |
| claude-haiku-4-5@20251001 | no | may decline | 10.7% (3/28) | 57.1% (16/28) | 21.4% (6/28) | 0.0% (0/28) | 10.7% (3/28) | 100.0% (12/12) | 0.0% (0/12) |
| claude-opus-5@default | no | must call | 0.0% (0/28) | 0.0% (0/28) | 100.0% (28/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| claude-opus-5@default | no | must call + instruction | 3.6% (1/28) | 0.0% (0/28) | 96.4% (27/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| claude-opus-5@default | no | may decline | 0.0% (0/28) | 78.6% (22/28) | 21.4% (6/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| claude-sonnet-5@default | no | must call | 7.1% (2/28) | 0.0% (0/28) | 92.9% (26/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| claude-sonnet-5@default | no | must call + instruction | 3.6% (1/28) | 0.0% (0/28) | 96.4% (27/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| claude-sonnet-5@default | no | may decline | 0.0% (0/28) | 92.9% (26/28) | 7.1% (2/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemini-3.5-flash-lite | no | must call | 21.4% (6/28) | 0.0% (0/28) | 78.6% (22/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemini-3.5-flash-lite | no | must call + instruction | 14.3% (4/28) | 0.0% (0/28) | 82.1% (23/28) | 3.6% (1/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemini-3.5-flash-lite | no | may decline | 0.0% (0/28) | 50.0% (14/28) | 50.0% (14/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemini-3.7-flash | no | must call | 3.6% (1/28) | 0.0% (0/28) | 96.4% (27/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemini-3.7-flash | no | must call + instruction | 0.0% (0/28) | 0.0% (0/28) | 100.0% (28/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemini-3.7-flash | no | may decline | 0.0% (0/28) | 89.3% (25/28) | 10.7% (3/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemma-4-26b-a4b | no | must call | 14.3% (4/28) | 0.0% (0/28) | 85.7% (24/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemma-4-26b-a4b | no | must call + instruction | 7.1% (2/28) | 0.0% (0/28) | 92.9% (26/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemma-4-26b-a4b | no | may decline | 0.0% (0/28) | 46.4% (13/28) | 53.6% (15/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemma-4-31b | no | must call | 0.0% (0/28) | 0.0% (0/28) | 100.0% (28/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemma-4-31b | no | must call + instruction | 0.0% (0/28) | 0.0% (0/28) | 100.0% (28/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gemma-4-31b | no | may decline | 0.0% (0/28) | 53.6% (15/28) | 46.4% (13/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-5.4-mini-2026-03-17 | no | must call | 32.1% (9/28) | 0.0% (0/28) | 67.9% (19/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-5.4-mini-2026-03-17 | no | must call + instruction | 28.6% (8/28) | 0.0% (0/28) | 71.4% (20/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-5.4-mini-2026-03-17 | no | may decline | 17.9% (5/28) | 60.7% (17/28) | 21.4% (6/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-5.4-nano-2026-03-17 | no | must call | 46.4% (13/28) | 0.0% (0/28) | 46.4% (13/28) | 7.1% (2/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-5.4-nano-2026-03-17 | no | must call + instruction | 42.9% (12/28) | 0.0% (0/28) | 50.0% (14/28) | 7.1% (2/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-5.4-nano-2026-03-17 | no | may decline | 46.4% (13/28) | 3.6% (1/28) | 39.3% (11/28) | 7.1% (2/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-5.5-2026-04-23 | no | must call | 3.6% (1/28) | 0.0% (0/28) | 96.4% (27/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-5.5-2026-04-23 | no | must call + instruction | 3.6% (1/28) | 0.0% (0/28) | 96.4% (27/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-5.5-2026-04-23 | no | may decline | 0.0% (0/28) | 60.7% (17/28) | 39.3% (11/28) | 0.0% (0/28) | 0.0% (0/28) | 100.0% (12/12) | 0.0% (0/12) |
| gpt-oss-20b | no | must call | 17.9% (5/28) | 0.0% (0/28) | 75.0% (21/28) | 0.0% (0/28) | 7.1% (2/28) | 91.7% (11/12) | 0.0% (0/12) |
| gpt-oss-20b | no | must call + instruction | 3.6% (1/28) | 0.0% (0/28) | 82.1% (23/28) | 7.1% (2/28) | 7.1% (2/28) | 83.3% (10/12) | 0.0% (0/12) |
| gpt-oss-20b | no | may decline | 0.0% (0/28) | 60.7% (17/28) | 28.6% (8/28) | 3.6% (1/28) | 7.1% (2/28) | 91.7% (11/12) | 0.0% (0/12) |

### v1.1: repurposing, pooled

| Group | Condition | Repurposed | Declined | Clean call | Schema fault | Other wrong | Unparseable |
|---|---|---|---|---|---|---|---|
| all models | must call | 14.9% (46/308) | 0.0% (0/308) | 82.1% (253/308) | 1.0% (3/308) | 0.0% (0/308) | 1.9% (6/308) |
| all models | must call + instruction | 11.0% (34/308) | 0.0% (0/308) | 84.4% (260/308) | 1.6% (5/308) | 0.0% (0/308) | 2.9% (9/308) |
| all models | may decline | 6.8% (21/308) | 59.4% (183/308) | 30.8% (95/308) | 1.0% (3/308) | 0.3% (1/308) | 1.6% (5/308) |
| no reasoning | must call | 14.9% (46/308) | 0.0% (0/308) | 82.1% (253/308) | 1.0% (3/308) | 0.0% (0/308) | 1.9% (6/308) |
| no reasoning | must call + instruction | 11.0% (34/308) | 0.0% (0/308) | 84.4% (260/308) | 1.6% (5/308) | 0.0% (0/308) | 2.9% (9/308) |
| no reasoning | may decline | 6.8% (21/308) | 59.4% (183/308) | 30.8% (95/308) | 1.0% (3/308) | 0.3% (1/308) | 1.6% (5/308) |
| pattern: absence | must call | 3.0% (1/33) | 0.0% (0/33) | 97.0% (32/33) | 0.0% (0/33) | 0.0% (0/33) | 0.0% (0/33) |
| pattern: absence | must call + instruction | 3.0% (1/33) | 0.0% (0/33) | 97.0% (32/33) | 0.0% (0/33) | 0.0% (0/33) | 0.0% (0/33) |
| pattern: absence | may decline | 0.0% (0/33) | 63.6% (21/33) | 36.4% (12/33) | 0.0% (0/33) | 0.0% (0/33) | 0.0% (0/33) |
| pattern: bound | must call | 14.5% (8/55) | 0.0% (0/55) | 83.6% (46/55) | 0.0% (0/55) | 0.0% (0/55) | 1.8% (1/55) |
| pattern: bound | must call + instruction | 9.1% (5/55) | 0.0% (0/55) | 87.3% (48/55) | 0.0% (0/55) | 0.0% (0/55) | 3.6% (2/55) |
| pattern: bound | may decline | 9.1% (5/55) | 47.3% (26/55) | 41.8% (23/55) | 1.8% (1/55) | 0.0% (0/55) | 0.0% (0/55) |
| pattern: enum_substitute | must call | 15.9% (7/44) | 0.0% (0/44) | 77.3% (34/44) | 0.0% (0/44) | 0.0% (0/44) | 6.8% (3/44) |
| pattern: enum_substitute | must call + instruction | 9.1% (4/44) | 0.0% (0/44) | 84.1% (37/44) | 2.3% (1/44) | 0.0% (0/44) | 4.5% (2/44) |
| pattern: enum_substitute | may decline | 6.8% (3/44) | 72.7% (32/44) | 15.9% (7/44) | 0.0% (0/44) | 0.0% (0/44) | 4.5% (2/44) |
| pattern: negation | must call | 6.8% (3/44) | 0.0% (0/44) | 90.9% (40/44) | 2.3% (1/44) | 0.0% (0/44) | 0.0% (0/44) |
| pattern: negation | must call + instruction | 11.4% (5/44) | 0.0% (0/44) | 84.1% (37/44) | 4.5% (2/44) | 0.0% (0/44) | 0.0% (0/44) |
| pattern: negation | may decline | 6.8% (3/44) | 31.8% (14/44) | 52.3% (23/44) | 2.3% (1/44) | 0.0% (0/44) | 6.8% (3/44) |
| pattern: role | must call | 20.5% (27/132) | 0.0% (0/132) | 76.5% (101/132) | 1.5% (2/132) | 0.0% (0/132) | 1.5% (2/132) |
| pattern: role | must call + instruction | 14.4% (19/132) | 0.0% (0/132) | 80.3% (106/132) | 1.5% (2/132) | 0.0% (0/132) | 3.8% (5/132) |
| pattern: role | may decline | 7.6% (10/132) | 68.2% (90/132) | 22.7% (30/132) | 0.8% (1/132) | 0.8% (1/132) | 0.0% (0/132) |

Matched controls, all models: must call: correct 99.2% (131/132), declined 0.0% (0/132), flagged as repurposed 0.0% (0/132); must call + instruction: correct 98.5% (130/132), declined 0.0% (0/132), flagged as repurposed 0.0% (0/132); may decline: correct 99.2% (131/132), declined 0.0% (0/132), flagged as repurposed 0.0% (0/132).

Same model and item, must call -> may decline (308 pairs): clean_call -> declined: 155; clean_call -> clean_call: 88; repurposed -> declined: 23; repurposed -> repurposed: 18; unparseable -> declined: 5; clean_call -> unparseable: 5; repurposed -> clean_call: 5; clean_call -> repurposed: 3; schema_fault -> schema_fault: 2; schema_fault -> clean_call: 1; unparseable -> clean_call: 1; clean_call -> other_wrong: 1; clean_call -> schema_fault: 1.
Repurposed only when it had to call: 28. Repurposed only when it could decline: 3. Exact McNemar p < 0.0001.

### v1.1: how often a decline is used when it is allowed

| Family | Declining is | Declined | Correct |
|---|---|---|---|
| conventional | accepted | 23.5% (80/341) | 99.7% (340/341) |
| near_miss | wrong | 0.0% (0/253) | 99.6% (252/253) |
| inexpressible | accepted | 19.4% (64/330) | 97.9% (323/330) |
| enum_pressure | accepted | 69.1% (190/275) | 97.8% (269/275) |
| nested | accepted | 23.4% (54/231) | 99.6% (230/231) |
| control | wrong | 0.6% (2/352) | 98.6% (347/352) |
| repurposing | accepted | 59.4% (183/308) | 90.3% (278/308) |
| matched_control | wrong | 0.0% (0/132) | 99.2% (131/132) |

### v1.1: repurposing, per item (models that repurposed / complete replies)

| Item | must call | must call + instruction | may decline | Declined when allowed |
|---|---|---|---|---|
| rep-01 | 5/11 | 1/11 | 2/11 | 9/11 |
| rep-02 | 3/11 | 3/11 | 1/11 | 5/11 |
| rep-03 | 2/11 | 2/11 | 1/11 | 10/11 |
| rep-04 | 4/11 | 4/11 | 1/11 | 9/11 |
| rep-05 | 2/11 | 0/11 | 0/11 | 11/11 |
| rep-06 | 3/11 | 2/11 | 1/11 | 9/11 |
| rep-07 | 0/11 | 0/11 | 0/11 | 7/11 |
| rep-08 | 7/11 | 6/11 | 1/11 | 9/11 |
| rep-09 | 1/11 | 1/11 | 3/11 | 5/11 |
| rep-10 | 0/11 | 0/11 | 0/11 | 3/11 |
| rep-11 | 0/11 | 0/11 | 0/11 | 3/11 |
| rep-12 | 0/11 | 0/11 | 0/11 | 10/11 |
| rep-13 | 1/11 | 2/11 | 1/11 | 2/11 |
| rep-14 | 0/11 | 0/11 | 0/11 | 7/11 |
| rep-15 | 1/11 | 1/11 | 1/11 | 3/11 |
| rep-16 | 1/11 | 2/11 | 1/11 | 2/11 |
| rep-17 | 3/11 | 1/11 | 1/11 | 7/11 |
| rep-18 | 0/11 | 0/11 | 0/11 | 3/11 |
| rep-19 | 4/11 | 3/11 | 3/11 | 4/11 |
| rep-20 | 0/11 | 0/11 | 0/11 | 2/11 |
| rep-21 | 1/11 | 1/11 | 1/11 | 10/11 |
| rep-22 | 1/11 | 1/11 | 0/11 | 9/11 |
| rep-23 | 0/11 | 0/11 | 0/11 | 3/11 |
| rep-24 | 0/11 | 0/11 | 0/11 | 9/11 |
| rep-25 | 3/11 | 2/11 | 1/11 | 9/11 |
| rep-26 | 2/11 | 0/11 | 1/11 | 8/11 |
| rep-27 | 1/11 | 1/11 | 0/11 | 5/11 |
| rep-28 | 1/11 | 1/11 | 1/11 | 10/11 |

### Usage

| Model | Calls | Prompt tokens | Completion tokens | Reasoning tokens reported | Calls with reasoning | Cost (USD) |
|---|---|---|---|---|---|---|
| claude-haiku-4-5@20251001 | 606 | 190,597 | 45,315 | 0 | 0 | 0.4172 |
| claude-opus-5@default | 606 | 253,069 | 44,304 | 0 | 0 | 2.3729 |
| claude-sonnet-5@default | 606 | 253,069 | 55,967 | 0 | 0 | 1.0658 |
| gemini-3.5-flash-lite | 606 | 183,077 | 23,220 | 0 | 0 | 0.1130 |
| gemini-3.7-flash | 606 | 183,077 | 171,513 | 0 | 0 | 0.7805 |
| gemma-4-26b-a4b | 606 | 183,077 | 226,867 | 0 | 0 | 0.1636 |
| gemma-4-31b | 606 | 183,077 | 197,596 | 0 | 0 | 0.1460 |
| gpt-5.4-mini-2026-03-17 | 606 | 179,497 | 20,001 | 0 | 0 | 0.2246 |
| gpt-5.4-nano-2026-03-17 | 606 | 179,497 | 20,442 | 0 | 0 | 0.0615 |
| gpt-5.5-2026-04-23 | 606 | 179,497 | 46,682 | 0 | 0 | 2.2979 |
| gpt-oss-20b | 606 | 216,463 | 89,219 | 0 | 0 | 0.0294 |
| **total** | 6666 | 2,183,997 | 941,126 | 0 | | 7.6725 |
