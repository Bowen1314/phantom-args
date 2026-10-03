### Per model

Phantom rate = share of parsed replies with at least one argument name the schema does not define, over the four phantom families (conventional, near-miss, inexpressible, nested). Control score = share of control items answered with a schema-valid call that uses the existing parameter correctly. Counts are k/n.

| Model | Items | Phantom, neutral | Phantom, instructed | Paired p | Enum violations, neutral | Enum violations, instructed | Control score, neutral | Control score, instructed | Unparseable (both) | Truncated |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-30B-A3B-Instruct-2507 | 162 | 8.6% (9/105) | 7.6% (8/105) | 1.000 (3 fixed / 2 broken) | 32.0% (8/25) | 32.0% (8/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| MiniCPM-V-4_5 | 162 | 6.7% (7/105) | 3.8% (4/105) | 0.250 (3 fixed / 0 broken) | 56.0% (14/25) | 52.0% (13/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| Qwen3-235B-A22B-Instruct-2507 | 162 | 1.9% (2/105) | 0.0% (0/105) | 0.500 (2 fixed / 0 broken) | 24.0% (6/25) | 24.0% (6/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| Hermes-4-405B | 162 | 1.0% (1/105) | 0.0% (0/105) | 1.000 (1 fixed / 0 broken) | 28.0% (7/25) | 24.0% (6/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| gemma-3-27b-it | 162 | 1.0% (1/105) | 0.0% (0/105) | 1.000 (1 fixed / 0 broken) | 24.0% (6/25) | 16.0% (4/25) | 96.9% (31/32) | 96.9% (31/32) | 0/324 | 0 |
| MiniMax-M3 | 162 | 0.0% (0/103) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 12.5% (3/24) | 0.0% (0/24) | 100.0% (32/32) | 100.0% (32/32) | 3/323 | 1 |
| Qwen3.5-397B-A17B | 60 | 0.0% (0/40) | 0.0% (0/40) | 1.000 (0 fixed / 0 broken) | 0.0% (0/10) | 0.0% (0/10) | 100.0% (10/10) | 100.0% (10/10) | 0/120 | 0 |
| Qwen3.8-27B | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| DeepSeek-V4-Flash-0731 | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 4.0% (1/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| DeepSeek-V4-Pro | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 16.0% (4/25) | 12.0% (3/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| DeepSeek-V4-Pro-0813 | 60 | 0.0% (0/40) | 0.0% (0/40) | 1.000 (0 fixed / 0 broken) | 0.0% (0/10) | 0.0% (0/10) | 100.0% (10/10) | 100.0% (10/10) | 0/120 | 0 |
| DeepSeek-V4.1-Flash | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| Kimi-K2.6 | 60 | 0.0% (0/40) | 0.0% (0/40) | 1.000 (0 fixed / 0 broken) | 10.0% (1/10) | 10.0% (1/10) | 100.0% (10/10) | 100.0% (10/10) | 0/120 | 0 |
| Kimi-K2.7-Code | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/24) | 4.0% (1/25) | 100.0% (32/32) | 100.0% (32/32) | 1/324 | 0 |
| Kimi-K3 | 60 | 0.0% (0/40) | 0.0% (0/40) | 1.000 (0 fixed / 0 broken) | 0.0% (0/10) | 0.0% (0/10) | 100.0% (10/10) | 100.0% (10/10) | 0/120 | 0 |
| NVIDIA-Nemotron-3-Nano-30B-A3B | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 8.0% (2/25) | 8.0% (2/25) | 96.9% (31/32) | 100.0% (32/32) | 0/324 | 0 |
| Nemotron-3-Ultra-550b-a55b | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| Nemotron-3_5-Lightning | 162 | 0.0% (0/104) | 0.0% (0/104) | 1.000 (0 fixed / 0 broken) | 4.0% (1/25) | 4.0% (1/25) | 100.0% (32/32) | 100.0% (32/32) | 2/324 | 0 |
| nemotron-3-super-120b-a12b | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |
| gpt-oss-120b | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/24) | 0.0% (0/24) | 100.0% (32/32) | 96.9% (31/32) | 2/324 | 0 |
| GLM-5.1 | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/24) | 0.0% (0/24) | 100.0% (32/32) | 100.0% (32/32) | 2/324 | 0 |
| GLM-5.2 | 60 | 0.0% (0/40) | 0.0% (0/40) | 1.000 (0 fixed / 0 broken) | 0.0% (0/9) | 0.0% (0/9) | 100.0% (10/10) | 100.0% (10/10) | 2/120 | 0 |
| GLM-5.3 | 60 | 0.0% (0/40) | 0.0% (0/40) | 1.000 (0 fixed / 0 broken) | 0.0% (0/10) | 0.0% (0/10) | 100.0% (10/10) | 100.0% (10/10) | 0/120 | 0 |
| GLM-5.3-Flash | 162 | 0.0% (0/105) | 0.0% (0/105) | 1.000 (0 fixed / 0 broken) | 0.0% (0/25) | 0.0% (0/25) | 100.0% (32/32) | 100.0% (32/32) | 0/324 | 0 |

Unparseable replies by reason: neutral: answered in prose, no call 4, two different calls 2, broken JSON 1; instructed: answered in prose, no call 4, broken JSON 1. By family: enum_pressure 9, nested 3.

### Per family, all models pooled

| Family | Target fault | Neutral | Instructed | Any schema violation, neutral | Any schema violation, instructed |
|---|---|---|---|---|---|
| conventional | phantom_arg | 0.5% (3/618; 95% CI 0–1%) | 0.5% (3/618; 95% CI 0–1%) | 1.1% (7/618) | 0.8% (5/618) |
| near_miss | phantom_arg | 0.0% (0/474; 95% CI 0–1%) | 0.0% (0/474; 95% CI 0–1%) | 0.4% (2/474) | 0.2% (1/474) |
| inexpressible | phantom_arg | 2.5% (15/599; 95% CI 2–4%) | 1.3% (8/600; 95% CI 1–3%) | 3.3% (20/599) | 2.2% (13/600) |
| enum_pressure | out_of_enum | 10.3% (52/505; 95% CI 8–13%) | 9.1% (46/506; 95% CI 7–12%) | 10.3% (52/505) | 9.1% (46/506) |
| nested | phantom_arg | 0.5% (2/436; 95% CI 0–2%) | 0.2% (1/437; 95% CI 0–1%) | 0.5% (2/436) | 0.2% (1/437) |
| control | (correct call) | 99.7% (634/636; 95% CI 99–100%) | 99.7% (634/636; 95% CI 99–100%) | 0.0% (0/636) | 0.0% (0/636) |

### Per family and model, neutral → instructed (target-fault rate, k/n)

| Model | conventional | near_miss | inexpressible | enum_pressure | nested |
|---|---|---|---|---|---|
| Qwen3-30B-A3B-Instruct-2507 | 3/31 → 3/31 | 0/23 → 0/23 | 6/30 → 4/30 | 8/25 → 8/25 | 0/21 → 1/21 |
| MiniCPM-V-4_5 | 0/31 → 0/31 | 0/23 → 0/23 | 6/30 → 4/30 | 14/25 → 13/25 | 1/21 → 0/21 |
| Qwen3-235B-A22B-Instruct-2507 | 0/31 → 0/31 | 0/23 → 0/23 | 1/30 → 0/30 | 6/25 → 6/25 | 1/21 → 0/21 |
| Hermes-4-405B | 0/31 → 0/31 | 0/23 → 0/23 | 1/30 → 0/30 | 7/25 → 6/25 | 0/21 → 0/21 |
| gemma-3-27b-it | 0/31 → 0/31 | 0/23 → 0/23 | 1/30 → 0/30 | 6/25 → 4/25 | 0/21 → 0/21 |
| MiniMax-M3 | 0/31 → 0/31 | 0/23 → 0/23 | 0/29 → 0/30 | 3/24 → 0/24 | 0/20 → 0/21 |
| Qwen3.5-397B-A17B | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 |
| Qwen3.8-27B | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 0/25 | 0/21 → 0/21 |
| DeepSeek-V4-Flash-0731 | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 1/25 | 0/21 → 0/21 |
| DeepSeek-V4-Pro | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 4/25 → 3/25 | 0/21 → 0/21 |
| DeepSeek-V4-Pro-0813 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 |
| DeepSeek-V4.1-Flash | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 0/25 | 0/21 → 0/21 |
| Kimi-K2.6 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 1/10 → 1/10 | 0/10 → 0/10 |
| Kimi-K2.7-Code | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/24 → 1/25 | 0/21 → 0/21 |
| Kimi-K3 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 |
| NVIDIA-Nemotron-3-Nano-30B-A3B | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 2/25 → 2/25 | 0/21 → 0/21 |
| Nemotron-3-Ultra-550b-a55b | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 0/25 | 0/21 → 0/21 |
| Nemotron-3_5-Lightning | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 1/25 → 1/25 | 0/20 → 0/20 |
| nemotron-3-super-120b-a12b | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 0/25 | 0/21 → 0/21 |
| gpt-oss-120b | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/24 → 0/24 | 0/21 → 0/21 |
| GLM-5.1 | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/24 → 0/24 | 0/21 → 0/21 |
| GLM-5.2 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 0/9 → 0/9 | 0/10 → 0/10 |
| GLM-5.3 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 | 0/10 → 0/10 |
| GLM-5.3-Flash | 0/31 → 0/31 | 0/23 → 0/23 | 0/30 → 0/30 | 0/25 → 0/25 | 0/21 → 0/21 |

### Most-invented argument names (temptation items, all models)

**neutral**: `open_access` ×3 (3 models), `min_rating` ×2 (2 models), `start_date` ×2 (2 models), `features` ×2 (2 models), `salary_range` ×2 (2 models), `organizer` ×1 (1 models), `page` ×1 (1 models), `offset` ×1 (1 models), `order` ×1 (1 models), `sort` ×1 (1 models), `author` ×1 (1 models), `amenities` ×1 (1 models), `departure_time` ×1 (1 models), `discount_percent` ×1 (1 models), `min_price` ×1 (1 models)

**instructed**: `open_access` ×2 (2 models), `page` ×1 (1 models), `offset` ×1 (1 models), `order` ×1 (1 models), `sort` ×1 (1 models), `year` ×1 (1 models), `min_rating` ×1 (1 models), `amenities` ×1 (1 models), `extension` ×1 (1 models), `min_price` ×1 (1 models), `start_date` ×1 (1 models), `salary_range` ×1 (1 models)

### Models that reasoned before answering vs models that did not

Grouped by whether the provider returned any reasoning at its default setting. The groups are different models, so this is an association, not the effect of reasoning. Core items are the 60 that every model answered.

- No reasoning (6): Hermes-4-405B, Qwen3-235B-A22B-Instruct-2507, Qwen3-30B-A3B-Instruct-2507, DeepSeek-V4-Pro, gemma-3-27b-it, MiniCPM-V-4_5
- Reasoning (18): MiniMax-M3, Qwen3.5-397B-A17B, Qwen3.8-27B, DeepSeek-V4-Flash-0731, DeepSeek-V4-Pro-0813, DeepSeek-V4.1-Flash, Kimi-K2.6, Kimi-K2.7-Code, Kimi-K3, NVIDIA-Nemotron-3-Nano-30B-A3B, Nemotron-3-Ultra-550b-a55b, Nemotron-3_5-Lightning, nemotron-3-super-120b-a12b, gpt-oss-120b, GLM-5.1, GLM-5.2, GLM-5.3, GLM-5.3-Flash

| Items | Group | Phantom, neutral | Phantom, instructed | Enum violations, neutral | Enum violations, instructed | Control score, neutral |
|---|---|---|---|---|---|---|
| all answered | no reasoning | 3.2% (20/630; 95% CI 2–5%) | 1.9% (12/630; 95% CI 1–3%) | 30.0% (45/150; 95% CI 23–38%) | 26.7% (40/150; 95% CI 20–34%) | 99.5% (191/192) |
| all answered | reasoning | 0.0% (0/1497; 95% CI 0–0%) | 0.0% (0/1499; 95% CI 0–0%) | 2.0% (7/355; 95% CI 1–4%) | 1.7% (6/356; 95% CI 1–4%) | 99.8% (443/444) |
| core 60 | no reasoning | 2.5% (6/240; 95% CI 1–5%) | 0.8% (2/240; 95% CI 0–3%) | 40.0% (24/60; 95% CI 29–53%) | 36.7% (22/60; 95% CI 26–49%) | 98.3% (59/60) |
| core 60 | reasoning | 0.0% (0/718; 95% CI 0–1%) | 0.0% (0/720; 95% CI 0–1%) | 0.6% (1/176; 95% CI 0–3%) | 1.7% (3/177; 95% CI 1–5%) | 99.4% (179/180) |

Schema-valid ways of getting it wrong, same grouping (all answered items). Repurposed = a value in a parameter that means something else (items with `misuse_params`). Substituted = on enum items where no listed value means what the user asked, a listed value was sent anyway.

| Group | Repurposed, neutral | Repurposed, instructed | Enum substituted, neutral | Enum substituted, instructed |
|---|---|---|---|---|
| no reasoning | 54.2% (13/24; 95% CI 35–72%) | 54.2% (13/24; 95% CI 35–72%) | 50.0% (51/102; 95% CI 40–60%) | 48.0% (49/102; 95% CI 39–58%) |
| reasoning | 25.0% (15/60; 95% CI 16–37%) | 16.7% (10/60; 95% CI 9–28%) | 28.8% (70/243; 95% CI 23–35%) | 29.2% (71/243; 95% CI 24–35%) |

### Schema-valid calls that put the constraint in a parameter meaning something else

Items whose tool has a parameter that can absorb the request but means something different. k/n = models whose call was schema-valid and gave that parameter a value, over models with a parsed reply.

| Item | Parameter | Neutral | Instructed | Phantom instead (neutral) |
|---|---|---|---|---|
| inex-13 | `assignee` | 27.8% (5/18) | 38.9% (7/18) | 1 |
| inex-14 | `labels` | 8.3% (2/24) | 8.3% (2/24) | 0 |
| inex-15 | `assignee_email` | 38.9% (7/18) | 22.2% (4/18) | 0 |
| inex-27 | `cc` | 58.3% (14/24) | 41.7% (10/24) | 0 |

### Inexpressible items: constraint words written into a string argument (schema-valid)

| Item | Neutral | Instructed |
|---|---|---|
| inex-03 | 94% (17/18) | 94% (17/18) |
| inex-01 | 70% (16/23) | 79% (19/24) |
| inex-27 | 58% (14/24) | 42% (10/24) |
| inex-05 | 33% (6/18) | 33% (6/18) |
| inex-13 | 28% (5/18) | 39% (7/18) |
| inex-06 | 11% (2/18) | 0% (0/18) |
| inex-14 | 8% (2/24) | 8% (2/24) |
| inex-08 | 6% (1/18) | 6% (1/18) |
| inex-23 | 6% (1/18) | 0% (0/18) |
| inex-04 | 4% (1/24) | 0% (0/24) |

### Enum-pressure items: what happened to the enum parameter

violated = a value outside the enum; listed = a listed value the user did not name; omitted = parameter left out. Items are split by what a valid call can do: `nearest` (a listed value is a fair stand-in, e.g. high for critical) and `omit` (no listed value means what the user asked, so leaving the parameter out is the faithful valid call).

- neutral, `nearest` items: violated 5/160 (3.1%), listed 144/160 (90.0%), omitted 11/160 (6.9%)
- neutral, `omit` items: violated 47/345 (13.6%), listed 121/345 (35.1%), omitted 177/345 (51.3%)
- instructed, `nearest` items: violated 5/161 (3.1%), listed 143/161 (88.8%), omitted 13/161 (8.1%)
- instructed, `omit` items: violated 41/345 (11.9%), listed 120/345 (34.8%), omitted 184/345 (53.3%)

Neutral condition, values with counts:

| Item | Fallback | n | Violated | Listed | Omitted | Values chosen |
|---|---|---|---|---|---|---|
| enum-01 | omit | 24 | 1 | 23 | 0 | `"metric"` ×23, `"kelvin"` ×1 |
| enum-02 | nearest | 18 | 0 | 18 | 0 | `"high"` ×18 |
| enum-03 | nearest | 18 | 0 | 18 | 0 | `"transit"` ×18 |
| enum-04 | nearest | 24 | 0 | 24 | 0 | `"business"` ×24 |
| enum-05 | omit | 18 | 1 | 12 | 5 | `"proposal"` ×12, `"negotiation"` ×1 |
| enum-06 | omit | 24 | 1 | 5 | 18 | `"declined"` ×3, `"posted"` ×2, `"refunded"` ×1 |
| enum-07 | omit | 18 | 1 | 6 | 11 | `"cancelled"` ×5, `"delivered"` ×1, `"returned"` ×1 |
| enum-08 | omit | 18 | 2 | 1 | 15 | `"royal_mail"` ×1, `"usps"` ×1, `"royal mail"` ×1 |
| enum-09 | omit | 24 | 5 | 0 | 19 | `"northgate"` ×5 |
| enum-10 | nearest | 18 | 0 | 16 | 2 | `"error"` ×16 |
| enum-11 | nearest | 18 | 0 | 13 | 5 | `"open"` ×13 |
| enum-12 | omit | 24 | 3 | 11 | 10 | `"none"` ×10, `"keto"` ×3, `"gluten_free"` ×1 |
| enum-13 | nearest | 18 | 0 | 17 | 1 | `"1d"` ×17 |
| enum-14 | omit | 23 | 7 | 0 | 16 | `"legal"` ×7 |
| enum-15 | omit | 18 | 2 | 3 | 13 | `"house"` ×3, `"houseboat"` ×2 |
| enum-16 | omit | 18 | 0 | 13 | 5 | `"track"` ×13 |
| enum-17 | nearest | 23 | 1 | 22 | 0 | `"open"` ×22, `"overdue"` ×1 |
| enum-18 | omit | 17 | 7 | 0 | 10 | `"neurology"` ×7 |
| enum-19 | omit | 18 | 4 | 4 | 10 | `"winter"` ×4, `"fall"` ×3, `"spring"` ×1 |
| enum-20 | nearest | 23 | 4 | 16 | 3 | `"1m"` ×14, `"5m"` ×4, `"raw"` ×2 |
| enum-21 | omit | 18 | 0 | 14 | 4 | `"bullets"` ×14 |
| enum-22 | omit | 24 | 0 | 24 | 0 | `"relevance"` ×24 |
| enum-23 | omit | 18 | 9 | 0 | 9 | `"pt"` ×9 |
| enum-24 | omit | 18 | 1 | 3 | 14 | `"book"` ×2, `"magazine"` ×1, `"ebook"` ×1 |
| enum-25 | omit | 23 | 3 | 2 | 18 | `"politics"` ×3, `"business"` ×2 |

### Usage

| Model | Calls | Prompt tokens | Completion tokens | Reasoning tokens reported | Calls with reasoning | Cost (USD) |
|---|---|---|---|---|---|---|
| MiniMax-M3 | 324 | 149,570 | 46,056 | 26,644 | 324 | 0.1001 |
| Hermes-4-405B | 324 | 100,434 | 12,568 | 0 | 0 | 0.1381 |
| Qwen3-235B-A22B-Instruct-2507 | 324 | 96,740 | 13,766 | 0 | 0 | 0.0276 |
| Qwen3-30B-A3B-Instruct-2507 | 324 | 96,740 | 14,645 | 0 | 0 | 0.0141 |
| Qwen3.5-397B-A17B | 120 | 36,924 | 44,715 | 0 | 120 | 0.1831 |
| Qwen3.8-27B | 324 | 111,946 | 56,879 | 43,058 | 324 | 0.2210 |
| DeepSeek-V4-Flash-0731 | 324 | 95,386 | 48,516 | 35,458 | 324 | 0.0269 |
| DeepSeek-V4-Pro | 324 | 95,386 | 13,450 | 0 | 0 | 0.2140 |
| DeepSeek-V4-Pro-0813 | 120 | 35,774 | 22,200 | 17,179 | 120 | 0.1351 |
| DeepSeek-V4.1-Flash | 324 | 103,810 | 55,690 | 42,850 | 324 | 0.0980 |
| gemma-3-27b-it | 324 | 99,192 | 14,588 | 0 | 0 | 0.0143 |
| Kimi-K2.6 | 120 | 35,830 | 53,630 | 0 | 120 | 0.2486 |
| Kimi-K2.7-Code | 324 | 95,534 | 50,517 | 38,002 | 324 | 0.2928 |
| Kimi-K3 | 120 | 45,070 | 19,193 | 13,143 | 120 | 0.4231 |
| NVIDIA-Nemotron-3-Nano-30B-A3B | 324 | 100,464 | 70,054 | 0 | 324 | 0.0228 |
| Nemotron-3-Ultra-550b-a55b | 324 | 100,464 | 72,030 | 57,649 | 324 | 0.3166 |
| Nemotron-3_5-Lightning | 324 | 100,464 | 222,478 | 208,391 | 324 | 0.0594 |
| nemotron-3-super-120b-a12b | 324 | 100,464 | 55,798 | 37,714 | 324 | 0.0804 |
| gpt-oss-120b | 324 | 114,278 | 45,838 | 0 | 324 | 0.0446 |
| MiniCPM-V-4_5 | 324 | 96,740 | 14,159 | 0 | 0 | 0.0794 |
| GLM-5.1 | 324 | 94,428 | 47,957 | 0 | 324 | 0.3432 |
| GLM-5.2 | 120 | 36,270 | 26,323 | 21,351 | 120 | 0.1666 |
| GLM-5.3 | 120 | 36,270 | 26,448 | 21,440 | 120 | 0.1671 |
| GLM-5.3-Flash | 324 | 96,696 | 54,085 | 41,630 | 324 | 0.0415 |
| **total** | 6552 | 2,074,874 | 1,101,583 | 604,509 | | 3.4586 |
