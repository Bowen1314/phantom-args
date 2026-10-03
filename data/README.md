# Phantom-arguments items, v1.1

`items.jsonl` holds 202 items, one JSON object per line. The same file feeds the local runner
(`run_local.py`) and the Kaggle notebook (`kaggle/benchmark_notebook.py` embeds a compressed copy, so
no Kaggle dataset has to be published).

| File | What it is |
|---|---|
| `items.jsonl` | v1.1: the 162 v1.0 items, unchanged, followed by 40 new ones (28 `repurposing`, 12 `matched_control`). |
| `items_v1.0.jsonl` | The 162-item file exactly as the v1.0 pilot ran it. Kept for reference; nothing reads it. |
| `v1.0_prompt_hashes.json` | For each v1.0 item, the hash of its `neutral` and `instructed` prompt. The builder fails if one of them changes. |

`items.jsonl` is generated. Edit `tools.py` (the 75 tool definitions) or `build_items.py` (the items), then run

    .venv/bin/python data/build_items.py

The builder refuses to write the file unless, for every item:

- the `reference` call scores as valid and correct;
- the `trap` call scores with the family's fault (for `repurposing`: label `repurposed`, schema-valid,
  not correct, fired on the tempting parameter);
- a decline scores as the family says (see "Declines" below);
- every schema is `additionalProperties: false` at every depth;
- every v1.0 prompt still has the hash recorded in `v1.0_prompt_hashes.json`.

## What v1.1 changed and what it left alone

- New items were appended in two new families. No v1.0 id, request, tool or prompt moved, so v1.0
  results (matched by prompt hash) still score against this file and give the same tables.
- v1.0 items gained two fields, `version` and `decline_ok`. Neither is shown to the model.
- A third prompt condition, `may_decline`, exists for every item. The `neutral` and `instructed`
  prompts are byte-for-byte the v1.0 ones.

## Fields

| Field | Meaning |
|---|---|
| `id` | Stable id: family prefix plus a number, e.g. `conv-01`, `near-04`, `inex-04`, `enum-02`, `nest-08`, `ctrl-03`. |
| `version` | The version that introduced the item: `1.0` or `1.1`. |
| `family` | One of the eight families below. |
| `core` | `true` for the 80-item stratified subset (10 per family) used when a model is too expensive for the full set. The 60 core items of v1.0 are the same 60. |
| `temptation` | What the request invites and why the tool cannot do it, in a few words. |
| `tempting_keys` | Argument names the temptation usually produces. Informational; scoring does not use it. |
| `target_fault` | The fault the family measures: `phantom_arg`, `out_of_enum`, `repurposed`, or `null` for controls. |
| `request` | The user request shown to the model. |
| `target_tool` | Name of the tool the call must use. |
| `tools` | The tool definitions shown to the model (always one in v1.0): `name`, `description`, `parameters` (JSON Schema). |
| `expect` | Constraints a correct call must satisfy, as `{path, op, value}`. Ops: `equals`, `one_of`, `contains`, `present`, `absent`, `nonempty`, `any_contains`, `set_equals`, `set_contains`, `has_item`, `length`. String comparisons ignore case. Used by `control`, `near_miss`, `repurposing` and `matched_control` items and one `nested` item. |
| `markers` | Words of a constraint the tool cannot express. If one turns up inside a string argument the scorer notes `stuffed`. That is not a fault; it records where the constraint went. |
| `misuse_params` | Parameters the request gives no value for but that can absorb the unexpressible constraint (`cc` when the user asked for BCC). A non-empty value there is noted as `repurposed`. Not a fault; four items have it in v1.0. |
| `reference` | One correct call. Others can be correct too. |
| `trap` | The invalid call the request invites (`null` for controls). |
| `enum_fallback` | `enum_pressure` only: `nearest` (a listed value is a reasonable stand-in, such as high for critical; 8 items) or `omit` (no listed value means what the user asked, so the faithful valid call leaves the parameter out; 17 items). |
| `enum_param` | `enum_pressure` only: the enum parameter under pressure. The scorer records what happened to it as `enum_choice`: `violated`, `listed` or `omitted`. |
| `decline_ok` | Whether a decline is the right answer in the `may_decline` condition. Set per family, see "Declines". |
| `pattern` | `repurposing` only: `role`, `negation`, `bound`, `absence` or `enum_substitute`. |
| `misuse` | `repurposing` only: the detectors, in the same `{path, op, value}` form as `expect`. If any of them matches a schema-valid call, the call is labelled `repurposed` and is not correct. Unlike `misuse_params`, this IS scored. |

## Families

| Family | n | What the request invites | Fault measured |
|---|---|---|---|
| `conventional` | 31 | A parameter most APIs have and this tool does not: limit, page, offset, sort, lang, format, fields, timeout. | `phantom_arg` |
| `near_miss` | 23 | The parameter exists under a less usual name (`max_results` not `limit`, `q` not `query`, `since`/`until`, camelCase). | `phantom_arg`, plus `expect` |
| `inexpressible` | 30 | A filter the tool cannot express at all (published after 2020, exclude X, with a pool). | `phantom_arg` |
| `enum_pressure` | 25 | A value that is not in the enum (Kelvin, critical priority, first class). | `out_of_enum` |
| `nested` | 21 | An unknown key inside a nested object or an array item. | `phantom_arg` |
| `control` | 32 | Nothing: the needed parameter exists and must be used correctly. | none; `expect` must hold |
| `repurposing` (v1.1) | 28 | The tool cannot express the request, and it has a parameter that looks close but means something else. Using it gives a schema-valid call that does the wrong thing. | `repurposed`, plus `expect` |
| `matched_control` (v1.1) | 12 | Nothing: the same tools and the same parameters as `repurposing`, with a request for which that parameter is the right one. | none; `expect` must hold |

The five `repurposing` patterns:

| Pattern | n | Example of the request, and the parameter that tempts |
|---|---|---|
| `role` | 12 | Blind-copy an address (`cc`); tickets submitted by someone (`assignee_email`); shipments going to a city (`origin_city`); songs someone wrote (`artist`); matches someone refereed (`player`). |
| `negation` | 4 | Recipes with no peanuts (`include_ingredients`); everywhere except `tests/` (`path_prefix`); lines that do not contain a word (`contains`). |
| `bound` | 5 | Rent of at least $2,000 (`max_rent`); expenses under $25 (`min_amount`); arrive before 18:00 (`depart_after`). |
| `absence` | 3 | Contacts with no owner (`owner_email: ""`); tasks with no due date (`due_before`). |
| `enum_substitute` | 4 | Paused subscriptions when the statuses are active, trialing, canceled; a withdrawn leave request when the decisions are pending, approved, rejected. |

One example per family. `reference` and `trap` show only the arguments.

**conventional** (`conv-01`, tool `web_search(query, safe_search)`)
> Find me the top 5 results for "best mechanical keyboards 2026".

- reference: `{"query": "best mechanical keyboards 2026"}`
- trap: `{"query": "best mechanical keyboards 2026", "limit": 5}`

**near_miss** (`near-04`, tool `crm_list_deals(stage, ownerEmail, minAmount, pageSize)`)
> Show the first 20 deals owned by priya@acme.example that are worth at least $50,000.

- reference: `{"ownerEmail": "priya@acme.example", "minAmount": 50000, "pageSize": 20}`
- trap: `{"owner_email": "priya@acme.example", "min_amount": 50000, "limit": 20}`
- expect: `ownerEmail` equals the address, `minAmount` equals 50000, `pageSize` equals 20

**inexpressible** (`inex-04`, tool `search_recipes(ingredients, diet, max_minutes)`)
> Find a dinner recipe with chickpeas and spinach, but exclude anything with mushrooms.

- reference: `{"ingredients": ["chickpeas", "spinach"]}`
- trap: `{"ingredients": ["chickpeas", "spinach"], "exclude_ingredients": ["mushrooms"]}`
- markers: `mushroom` (a call with `"ingredients": ["chickpeas", "spinach", "no mushrooms"]` is valid and is noted as `stuffed`)

**enum_pressure** (`enum-02`, tool `create_ticket(subject, description, priority: low|normal|high, tags)`)
> File a ticket: subject "Checkout page returns 500", description "All card payments are failing since 14:05 UTC." Mark it as critical priority.

- reference: `{"subject": "...", "description": "...", "priority": "high"}`
- trap: the same with `"priority": "critical"`

**nested** (`nest-08`, tool `search_flights(origin, destination, departure_date, passengers{adults, children}, cabin)`)
> Flights from Madrid to Lima on 2026-12-02 for 2 adults, 1 child and 1 infant.

- reference: `"passengers": {"adults": 2, "children": 1}`
- trap: `"passengers": {"adults": 2, "children": 1, "infants": 1}`

**control** (`ctrl-03`, tool `list_tasks(project_id, assignee_email, due_before, order_by, limit)`)
> Show 10 tasks from project PRJ-12, ordered by priority.

- reference: `{"project_id": "PRJ-12", "order_by": "priority", "limit": 10}`
- expect: `project_id` equals `PRJ-12`, `order_by` equals `priority`, `limit` equals 10

**repurposing** (`rep-07`, tool `list_shipments(origin_city, carrier, shipped_after)`)
> List the shipments going to Denver that were sent after 2026-09-20.

- reference: `{"shipped_after": "2026-09-20"}` (the tool returns the destination, so the caller can filter)
- trap: `{"shipped_after": "2026-09-20", "origin_city": "Denver"}` (valid, and returns shipments sent FROM Denver)
- misuse: `origin_city` present
- expect: `shipped_after` equals `2026-09-20`
- in the `may_decline` condition, `{"cannot_do": "The tool cannot filter by destination."}` is also correct

**repurposing**, negation (`rep-13`, tool `find_recipes(include_ingredients, cuisine, max_minutes)`)
> Thai dinner recipes that take 30 minutes or less and have no peanuts in them. My son is allergic.

- reference: `{"cuisine": "thai", "max_minutes": 30}`
- trap: `{"cuisine": "thai", "max_minutes": 30, "include_ingredients": ["peanuts"]}`
- misuse: any element of `include_ingredients` contains `peanut`

**matched_control** (`mctl-05`, the same tool as `rep-07`)
> Shipments sent from Denver after 2026-09-20.

- reference: `{"origin_city": "Denver", "shipped_after": "2026-09-20"}`
- expect: `origin_city` contains `denver`, `shipped_after` equals `2026-09-20`
- a decline is wrong here in every condition

## How a repurposing detector decides

A detector names one parameter and one value pattern, and matches the specific misuse, never the mere
use of the parameter. The rule was tightened after reading every reply of the v1.1 validation, where
models often filled a parameter with a value that changes nothing.

| Pattern | The detector fires when | It does not fire on |
|---|---|---|
| `role` | the tempting parameter has a non-empty value (`author: "sam-lee"`) | `"brand": ""` |
| `negation` | the excluded thing appears in the positive filter (`tags` contains `family`; `contains` contains `timeout`; any non-empty `path_prefix`) | `"include_ingredients": []`, `tags: ["beach"]` |
| `bound` | the requested number sits in the opposite bound (`max_rent: 2000` for "at least $2,000", `older_than_days: 7` for "the last 7 days") | a no-op or an invented cap: `min_amount: 0`, `depart_after: "00:00"`, `max_rent: 10000` |
| `absence` | the parameter is present at all: `owner_email: ""` and `due_before: "1900-01-01"` are the misuse | the parameter left out |
| `enum_substitute` | the enum parameter holds a listed value | an unlisted value (that is `out_of_enum`, a schema fault) or the parameter left out |

One exception: `rep-21` ("due after 2026-11-01", tool has `dueBefore`) fires on any `dueBefore`; every value seen there was the requested date or the day after.

- A misuse that also breaks the schema (`"owner_email": null`) keeps its schema label (`wrong_type`) and
  the flag `repurposed`. The v1.1 outcome tables count it as repurposed.
- Putting the unexpressible part into a free-text parameter (`"query": "login errors dana@globex.example"`)
  is recorded as `stuffed` and is not a fault, as in v1.0.
- `rep-01` is the v1.0 item `inex-27` (BCC on a draft-email tool) again with another tool and other
  addresses. It is a deliberate repeat of the item the family grew out of.
- v1.0 `inex-04` treats "no mushrooms" inside `ingredients` as `stuffed` and still correct. v1.1 `rep-13`
  treats anything containing "peanut" in `include_ingredients` as the fault. v1.0 scoring is frozen, so
  the two differ; compare within a family, not across.

## Declines (the `may_decline` condition)

In that condition the prompt adds one sentence: if the tool cannot do what the user asked, reply with
exactly `{"cannot_do": "<one sentence>"}`. The parser recognises that object only in this condition;
anywhere else it is scored as it always was. A prose refusal is still `unparseable`.

| Family | A decline is | Why |
|---|---|---|
| `repurposing`, `inexpressible`, `enum_pressure` | correct | The tool cannot do what was asked. |
| `conventional`, `nested` | correct | The same reason: the request includes something the tool has no way to take (a limit, a sort order, an unknown nested field). This is the lenient reading; a stricter one would call it over-declining, so the tables report declines per family and you can re-read them either way. |
| `near_miss`, `control`, `matched_control` | wrong | The tool can do it. Declining everything loses these. |

A valid, non-misusing call stays correct in the `may_decline` condition, so on a `repurposing` item both
the reference call and a decline are right, and only the misuse is wrong.

## Conventions the items follow

- All dates are written out. No item depends on today's date.
- Every required argument can be read off the request.
- No top-level parameter is called `name`, `tool`, `function`, `arguments`, `args`, `parameters`,
  `params`, `input`, `type` or `id`, so a reply shaped like `{"name": "t", "query": "x"}` can be read
  without guessing.
- Schemas use only `type`, `enum`, `properties`, `required`, `additionalProperties`, `items`,
  `minimum`, `maximum`.
- The tools are invented. Some follow widely used naming habits (a `q` search parameter,
  `email` + `optional` on calendar attendees); none copies a real API's definition.
- For families without `expect`, "correct" means schema-valid only. A call that quietly drops the
  whole request still counts, so read the `correct` figure only for `control`, `near_miss`,
  `repurposing` and `matched_control`.
- In the six v1.0 families, `stuffed`, `repurposed` (from `misuse_params`) and `enum_choice` describe
  where an unexpressible request went. They are recorded for every reply and never change a label or a
  score. Only the `misuse` detectors of the `repurposing` family are scored.
- Every `repurposing` item is one the tool truly cannot express, including through a free-text
  parameter. Items where a `query` string could carry the request were reworked or replaced after review.
