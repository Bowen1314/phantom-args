"""Builds data/items.jsonl from the tool library (tools.py) and the item list below.

Run:  .venv/bin/python data/build_items.py

Every item carries
  reference  - one call that is correct (must score valid + correct)
  trap       - the call the temptation invites (must score with the family's
               fault label; controls have no trap)
and the script refuses to write the file unless both hold for every item, so
the data file cannot drift away from the scorer.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from tools import TOOLS  # noqa: E402

from phantom_args.parser import ARG_KEYS, NAME_KEYS, ParsedCall  # noqa: E402
from phantom_args.scorer import score_call  # noqa: E402

VERSION = "1.1"            # version of the data file
V1_0_FAMILIES = ("conventional", "near_miss", "inexpressible", "enum_pressure", "nested", "control")

FAMILIES = {
    "conventional": "conv",
    "near_miss": "near",
    "inexpressible": "inex",
    "enum_pressure": "enum",
    "nested": "nest",
    "control": "ctrl",
    "repurposing": "rep",              # v1.1
    "matched_control": "mctl",         # v1.1
}
# Is "the tool cannot do this" a correct reply (may_decline condition)?
DECLINE_OK = {
    "conventional": True, "near_miss": False, "inexpressible": True, "enum_pressure": True, "nested": True,
    "control": False, "repurposing": True, "matched_control": False,
}
MIN_ITEMS = {"matched_control": 8}     # every other family: at least 15
FAMILY_FAULT = {
    "conventional": "phantom_arg",
    "near_miss": "phantom_arg",
    "inexpressible": "phantom_arg",
    "enum_pressure": "out_of_enum",
    "nested": "phantom_arg",
    "control": None,
    "repurposing": "repurposed",
    "matched_control": None,
}

ITEMS: list[dict] = []


# ---- expectation shorthands -------------------------------------------------
def eq(path, value):
    return {"path": path, "op": "equals", "value": value}


def has(path, value):
    return {"path": path, "op": "contains", "value": value}


def oneof(path, values):
    return {"path": path, "op": "one_of", "value": values}


def seteq(path, values, project=None):
    e = {"path": path, "op": "set_equals", "value": values}
    if project:
        e["project"] = project
    return e


def item_(path, value):
    return {"path": path, "op": "has_item", "value": value}


def plus(base: dict, **extra) -> dict:
    d = copy.deepcopy(base)
    d.update(extra)
    return d


def add(family, tool, request, temptation, keys, ref, *, trap=None, expect=None,
        markers=None, fallback=None, misuse=None):
    """Register one item.

    keys     - the argument names the temptation typically produces (informational)
    ref      - arguments of a correct call
    trap     - arguments of the tempting, schema-invalid call
    expect   - constraints a *correct* call must satisfy (controls, near-miss)
    markers  - words of the unexpressible constraint; if they show up inside a
               string argument the scorer notes `stuffed` (not a fault)
    fallback - enum_pressure only: what a valid call can do instead
               (omit | nearest)
    misuse   - parameters the request gives no value for; a non-empty value
               there means the model forced the unexpressible constraint into
               a parameter that means something else (scorer notes `repurposed`)
    """
    ITEMS.append({
        "family": family, "tool": tool, "request": request, "temptation": temptation,
        "tempting_keys": keys, "reference": ref, "trap": trap, "expect": expect or [],
        "markers": markers or [], "fallback": fallback, "misuse": misuse or [],
    })


# =============================================================================
# 1. conventional-but-absent parameters
#    limit/top_k, page/offset, sort/order, lang, format, fields, timeout
# =============================================================================
F = "conventional"

r = {"query": "best mechanical keyboards 2026"}
add(F, "web_search", "Find me the top 5 results for \"best mechanical keyboards 2026\".",
    "result count; the tool has no limit parameter", ["limit", "top_k", "num_results", "count"], r,
    trap=plus(r, limit=5))

r = {"search_term": "Northwind Traders"}
add(F, "crm_search_contacts", "Pull up the first 10 contacts at Northwind Traders.",
    "result count; the tool has no limit parameter", ["limit", "max_results"], r, trap=plus(r, limit=10))

r = {"query": "diffusion models for protein design"}
add(F, "search_papers", "What are the 3 most cited papers on diffusion models for protein design?",
    "result count and ordering; the tool has neither", ["limit", "sort_by", "top_k"], r,
    trap=plus(r, limit=3, sort_by="citations"))

r = {"customer_id": "C-20418"}
add(F, "list_orders", "Show me the last 5 orders for customer C-20418.",
    "result count; the tool has no limit parameter", ["limit", "sort"], r, trap=plus(r, limit=5))

r = {"service": "checkout", "level": "error"}
add(F, "query_logs", "Get the last 50 error lines from the checkout service.",
    "result count; the tool has no limit parameter", ["limit", "tail", "max_lines"], r, trap=plus(r, limit=50))

r = {"city": "Portland", "cuisine": "sushi"}
add(F, "find_restaurants", "Give me the top 3 sushi places in Portland.",
    "result count; the tool has no limit parameter", ["limit", "top_k", "sort_by"], r, trap=plus(r, limit=3))

r = {"ingredients": ["chicken", "leeks"]}
add(F, "search_recipes", "Give me the 3 best recipes that use chicken and leeks.",
    "result count; the tool has no limit parameter", ["limit", "top_k", "sort"], r, trap=plus(r, limit=3))

r = {"query": "coffee shop", "center": {"lat": 51.5074, "lng": -0.1278}, "radius_m": 800}
add(F, "find_places", "Coffee shops within 800 metres of 51.5074, -0.1278 — just the closest 5.",
    "result count; the tool has no limit parameter", ["limit", "max_results", "sort_by"], r, trap=plus(r, limit=5))

r = {"repo": "acme/payments-api", "state": "open"}
add(F, "list_repo_issues", "Show me page 2 of the open issues in acme/payments-api.",
    "pagination; the tool has no page parameter", ["page", "per_page"], r, trap=plus(r, page=2))

r = {"query": "login failures", "status": "open"}
add(F, "search_tickets", "Show me the next 25 open tickets about login failures — I've already seen the first 25.",
    "pagination; the tool has no offset parameter", ["offset", "page", "limit", "skip"], r,
    trap=plus(r, offset=25, limit=25))

r = {"query": "kubernetes ingress tutorial"}
add(F, "web_search", "Search for \"kubernetes ingress tutorial\" and skip the first 10 results.",
    "pagination; the tool has no offset parameter", ["offset", "start", "skip", "page"], r, trap=plus(r, offset=10))

r = {"author": "Ursula K. Le Guin", "format": "book"}
add(F, "search_catalog", "Search the catalogue for books by Ursula K. Le Guin, 20 per page.",
    "page size; the tool has no pagination parameters", ["per_page", "page_size", "limit"], r,
    trap=plus(r, per_page=20))

r = {"subject": "statistics", "level": "intermediate", "term": "spring"}
add(F, "search_courses", "Show me page 3 of the intermediate statistics courses offered in spring.",
    "pagination; the tool has no page parameter", ["page", "offset"], r, trap=plus(r, page=3))

r = {"path": "/srv/reports"}
add(F, "list_files", "List the files in /srv/reports sorted by size, biggest first.",
    "ordering; the tool has no sort parameter", ["sort_by", "sort", "order"], r,
    trap=plus(r, sort_by="size", order="desc"))

r = {"calendar_id": "team-eng", "start_date": "2026-11-02", "end_date": "2026-11-06"}
add(F, "list_calendar_events", "What's on calendar team-eng from 2026-11-02 to 2026-11-06? Latest events first.",
    "ordering; the tool has no sort parameter", ["order", "sort", "order_by"], r, trap=plus(r, order="desc"))

r = {"query": "wireless earbuds"}
add(F, "search_products", "Find wireless earbuds, sorted by price from low to high.",
    "ordering; the tool has no sort parameter", ["sort", "sort_by", "order"], r, trap=plus(r, sort_by="price_asc"))

r = {"department": "marketing"}
add(F, "list_employees", "List everyone in marketing in alphabetical order by last name.",
    "ordering; the tool has no sort parameter", ["sort_by", "order_by", "sort"], r, trap=plus(r, sort_by="last_name"))

r = {"keywords": "data engineer", "location": "Austin"}
add(F, "search_jobs", "Find data engineer jobs in Austin, most recent first.",
    "ordering; the tool has no sort parameter", ["sort", "sort_by", "order"], r, trap=plus(r, sort_by="date"))

r = {"city": "Lisbon", "check_in": "2026-12-10", "check_out": "2026-12-14", "guests": 2}
add(F, "search_hotels", "Hotels in Lisbon for 2 guests from 2026-12-10 to 2026-12-14, cheapest first.",
    "ordering; the tool has no sort parameter", ["sort", "sort_by", "order_by"], r, trap=plus(r, sort_by="price"))

r = {"city": "Lisbon"}
add(F, "get_current_weather", "What's the weather in Lisbon right now? Give me the description in Portuguese.",
    "response language; the tool has no lang parameter", ["lang", "language", "locale"], r, trap=plus(r, lang="pt"))

r = {"origin": "Shibuya Station", "destination": "Meiji Shrine", "mode": "walking"}
add(F, "get_directions", "Walking directions from Shibuya Station to Meiji Shrine, with the steps written in Japanese.",
    "response language; the tool has no language parameter", ["language", "lang", "locale"], r,
    trap=plus(r, language="ja"))

r = {"tracking_number": "JD014600006281234567", "carrier": "dhl"}
add(F, "track_shipment", "Track DHL parcel JD014600006281234567 and get the status updates in German.",
    "response language; the tool has no lang parameter", ["lang", "language", "locale"], r, trap=plus(r, lang="de"))

r = {"symbol": "AAPL", "start_date": "2026-06-01", "end_date": "2026-06-30", "interval": "1d"}
add(F, "get_price_history", "Get AAPL daily prices from 2026-06-01 to 2026-06-30 as CSV.",
    "output format; the tool has no format parameter", ["format", "output_format"], r, trap=plus(r, format="csv"))

r = {"device_id": "hvac-07", "metric": "co2", "start_time": "2026-09-01T00:00:00Z", "end_time": "2026-09-02T00:00:00Z"}
add(F, "get_sensor_readings",
    "Export the CO2 readings for device hvac-07 from 2026-09-01T00:00:00Z to 2026-09-02T00:00:00Z in JSON format.",
    "output format; the tool has no format parameter", ["format", "output"], r, trap=plus(r, format="json"))

r = {"account_id": "ACC-5521", "since": "2026-08-01", "status": "posted"}
add(F, "list_transactions", "Get all posted transactions on account ACC-5521 since 2026-08-01 as a PDF statement.",
    "output format; the tool has no format parameter", ["format", "export", "output_format"], r,
    trap=plus(r, format="pdf"))

r = {"department": "finance"}
add(F, "list_employees", "I just need the names and email addresses of the people in the finance department.",
    "field selection; the tool has no fields parameter", ["fields", "select", "columns"], r,
    trap=plus(r, fields=["name", "email"]))

r = {"symbol": "MSFT", "start_date": "2026-01-05", "end_date": "2026-03-30", "interval": "1wk"}
add(F, "get_price_history", "Weekly prices for MSFT from 2026-01-05 to 2026-03-30 — only the closing price, please.",
    "field selection; the tool has no fields parameter", ["fields", "columns", "field"], r,
    trap=plus(r, fields=["close"]))

r = {"search_term": "Globex"}
add(F, "crm_search_contacts", "Look up the contacts at Globex — I only need their phone numbers.",
    "field selection; the tool has no fields parameter", ["fields", "select", "return_fields"], r,
    trap=plus(r, fields=["phone"]))

r = {"query": "city council budget vote results"}
add(F, "web_search", "Search for \"city council budget vote results\" with a 5-second timeout.",
    "timeout; the tool has no timeout parameter", ["timeout", "timeout_seconds", "timeout_ms"], r,
    trap=plus(r, timeout=5))

r = {"service": "billing", "level": "warn", "since_minutes": 30}
add(F, "query_logs",
    "Check the warn-level logs of the billing service for the last 30 minutes; don't let the query run longer than 10 seconds.",
    "timeout; the tool has no timeout parameter", ["timeout", "timeout_seconds", "max_duration"], r,
    trap=plus(r, timeout=10))

r = {"tracking_number": "1Z999AA10123456784", "carrier": "ups"}
add(F, "track_shipment", "Track UPS package 1Z999AA10123456784, with a 3-second timeout on the lookup.",
    "timeout; the tool has no timeout parameter", ["timeout", "timeout_seconds", "timeout_ms"], r,
    trap=plus(r, timeout=3))

# =============================================================================
# 2. near-miss names: the parameter exists, under a less conventional name
# =============================================================================
F = "near_miss"

r = {"query": "sourdough starter", "max_results": 5}
add(F, "search_videos", "Find the top 5 videos about sourdough starter.",
    "schema says max_results; convention says limit", ["limit", "top_k"], r,
    trap={"query": "sourdough starter", "limit": 5}, expect=[eq("max_results", 5)])

r = {"query": "Artemis launch", "uploaded_after": "2026-09-01"}
add(F, "search_videos", "Videos about the Artemis launch that were published after 2026-09-01.",
    "schema says uploaded_after; convention says published_after", ["published_after", "after", "since"], r,
    trap={"query": "Artemis launch", "published_after": "2026-09-01"}, expect=[eq("uploaded_after", "2026-09-01")])

r = {"count": 3, "topic": "technology", "country_code": "US"}
add(F, "get_top_headlines", "Give me the top 3 technology headlines for the US.",
    "schema says count; convention says limit", ["limit", "top_k", "country"], r,
    trap={"limit": 3, "topic": "technology", "country_code": "US"},
    expect=[eq("count", 3), eq("topic", "technology"), eq("country_code", "US")])

r = {"ownerEmail": "priya@acme.example", "minAmount": 50000, "pageSize": 20}
add(F, "crm_list_deals", "Show the first 20 deals owned by priya@acme.example that are worth at least $50,000.",
    "camelCase schema; snake_case habit", ["owner_email", "min_amount", "page_size", "limit"], r,
    trap={"owner_email": "priya@acme.example", "min_amount": 50000, "limit": 20},
    expect=[eq("ownerEmail", "priya@acme.example"), eq("minAmount", 50000), eq("pageSize", 20)])

r = {"subject": "beekeeping", "format": "ebook"}
add(F, "search_catalog", "Find ebooks on the topic of beekeeping.",
    "schema says subject; the user says topic", ["topic", "query", "keywords"], r,
    trap={"topic": "beekeeping", "format": "ebook"}, expect=[has("subject", "beekeeping"), eq("format", "ebook")])

r = {"customerId": "cus_8841", "status": "open", "dueBefore": "2026-11-01"}
add(F, "list_invoices", "Open invoices for customer cus_8841 that are due before 2026-11-01.",
    "camelCase schema; snake_case habit", ["customer_id", "due_before"], r,
    trap={"customer_id": "cus_8841", "status": "open", "due_before": "2026-11-01"},
    expect=[eq("customerId", "cus_8841"), eq("status", "open"), eq("dueBefore", "2026-11-01")])

r = {"customerId": "cus_1207", "status": "paid", "pageSize": 50}
add(F, "list_invoices", "Show me 50 paid invoices for customer cus_1207.",
    "schema says pageSize; convention says limit / page_size", ["limit", "page_size", "customer_id"], r,
    trap={"customerId": "cus_1207", "status": "paid", "limit": 50},
    expect=[eq("customerId", "cus_1207"), eq("status", "paid"), eq("pageSize", 50)])

r = {"q": "Kind of Blue", "kind": "album"}
add(F, "search_music", "Search for the album \"Kind of Blue\".",
    "schema says q; convention says query", ["query", "type"], r,
    trap={"query": "Kind of Blue", "kind": "album"}, expect=[has("q", "kind of blue"), eq("kind", "album")])

r = {"base": "CHF", "quote": "JPY"}
add(F, "get_exchange_rate", "What's the exchange rate from Swiss francs to Japanese yen?",
    "schema says base and quote; convention says from and to", ["from", "to", "from_currency", "to_currency"], r,
    trap={"from": "CHF", "to": "JPY"}, expect=[eq("base", "CHF"), eq("quote", "JPY")])

r = {"search_term": "Maria Okafor"}
add(F, "crm_search_contacts", "Find the contact named Maria Okafor.",
    "schema says search_term; convention says query / name", ["query", "name", "q"], r,
    trap={"query": "Maria Okafor"}, expect=[has("search_term", "okafor")])

r = {"account_id": "ACC-5521", "since": "2026-07-01", "until": "2026-07-31"}
add(F, "list_transactions", "Transactions on account ACC-5521 from 2026-07-01 to 2026-07-31.",
    "schema says since/until; convention says start_date/end_date", ["start_date", "end_date", "from", "to"], r,
    trap={"account_id": "ACC-5521", "start_date": "2026-07-01", "end_date": "2026-07-31"},
    expect=[eq("since", "2026-07-01"), eq("until", "2026-07-31")])

r = {"service": "gateway", "since_minutes": 20, "contains": "connection reset"}
add(F, "query_logs", "Search the gateway service logs from the last 20 minutes for \"connection reset\".",
    "schema says contains and since_minutes; convention says query and since", ["query", "search", "since", "minutes"], r,
    trap={"service": "gateway", "since_minutes": 20, "query": "connection reset"},
    expect=[eq("since_minutes", 20), has("contains", "connection reset"), has("service", "gateway")])

r = {"patient_id": "P-88213", "from": "2026-10-05", "to": "2026-10-09"}
add(F, "list_appointments", "Appointments for patient P-88213, starting 2026-10-05 and ending 2026-10-09.",
    "schema says from/to; convention says start_date/end_date", ["start_date", "end_date", "date_from"], r,
    trap={"patient_id": "P-88213", "start_date": "2026-10-05", "end_date": "2026-10-09"},
    expect=[eq("from", "2026-10-05"), eq("to", "2026-10-09")])

r = {"question": "Which day for the retro?", "options": [{"label": "Tuesday"}, {"label": "Thursday"}],
     "closes_at": "2026-10-09T18:00:00Z"}
add(F, "create_poll",
    "Create a poll \"Which day for the retro?\" with the options Tuesday and Thursday. The deadline for voting is 2026-10-09T18:00:00Z.",
    "schema says closes_at; the user says deadline", ["deadline", "ends_at", "expires_at", "end_time"], r,
    trap={"question": "Which day for the retro?", "options": [{"label": "Tuesday"}, {"label": "Thursday"}],
          "deadline": "2026-10-09T18:00:00Z"},
    expect=[has("closes_at", "2026-10-09T18:00"), seteq("options", ["Tuesday", "Thursday"], project="label")])

r = {"document_id": "DOC-3391", "max_words": 150}
add(F, "summarize_document", "Summarize document DOC-3391 in no more than 150 words.",
    "schema says max_words; convention says max_length / length", ["max_length", "length", "word_limit"], r,
    trap={"document_id": "DOC-3391", "max_length": 150}, expect=[eq("max_words", 150)])

r = {"recipient": "sam.lee@northwind.example", "subject": "Q3 numbers",
     "body": "The Q3 deck is ready, see slide 4."}
add(F, "create_email_draft",
    "Draft an email to sam.lee@northwind.example with the subject \"Q3 numbers\" that says \"The Q3 deck is ready, see slide 4.\"",
    "schema says recipient and body; convention says to and message", ["to", "message", "content", "text"], r,
    trap={"to": "sam.lee@northwind.example", "subject": "Q3 numbers", "body": "The Q3 deck is ready, see slide 4."},
    expect=[eq("recipient", "sam.lee@northwind.example"), has("body", "slide 4")])

r = {"keywords": "product designer", "remote_only": True, "posted_within_days": 7}
add(F, "search_jobs", "Remote product designer jobs posted in the last 7 days.",
    "schema says keywords, remote_only, posted_within_days; convention says query, remote, days",
    ["query", "remote", "days", "posted_within"], r,
    trap={"query": "product designer", "remote": True, "posted_within_days": 7},
    expect=[has("keywords", "designer"), eq("remote_only", True), eq("posted_within_days", 7)])

r = {"full_name": "Priya Raman", "company": "Vandelay Industries",
     "emails": [{"address": "priya.raman@vandelay.example"}]}
add(F, "create_contact",
    "Add Priya Raman from Vandelay Industries to the address book, email priya.raman@vandelay.example.",
    "schema says full_name and emails[].address; convention says name and email", ["name", "email"], r,
    trap={"name": "Priya Raman", "company": "Vandelay Industries",
          "emails": [{"email": "priya.raman@vandelay.example"}]},
    expect=[has("full_name", "priya raman"), item_("emails", {"address": "priya.raman@vandelay.example"})])

r = {"address": {"street": "88 Harbour Lane", "city": "Portsmouth", "postal_code": "03801",
                 "country_code": "US"}}
add(F, "geocode_address", "Geocode 88 Harbour Lane, Portsmouth, zip 03801, US.",
    "schema says postal_code and country_code (nested); the user says zip", ["zip", "zip_code", "country"], r,
    trap={"address": {"street": "88 Harbour Lane", "city": "Portsmouth", "zip": "03801",
                      "country_code": "US"}},
    expect=[eq("address.postal_code", "03801"), has("address.street", "88 harbour"),
            eq("address.country_code", "US")])

r = {"symbol": "NVDA", "start_date": "2025-01-01", "end_date": "2025-12-31", "interval": "1mo"}
add(F, "get_price_history", "Monthly prices for ticker NVDA from 2025-01-01 to 2025-12-31.",
    "schema says symbol; the user says ticker", ["ticker", "from", "to"], r,
    trap={"ticker": "NVDA", "start_date": "2025-01-01", "end_date": "2025-12-31", "interval": "1mo"},
    expect=[eq("symbol", "NVDA"), eq("interval", "1mo"), eq("start_date", "2025-01-01"),
            eq("end_date", "2025-12-31")])

r = {"subject": "VPN drops every hour", "description": "Disconnects on the hour since Monday.", "tags": ["network"]}
add(F, "create_ticket",
    "Open a ticket titled \"VPN drops every hour\" with the description \"Disconnects on the hour since Monday.\" and label it network.",
    "schema says subject and tags; the user says title and label", ["title", "labels", "label"], r,
    trap={"title": "VPN drops every hour", "description": "Disconnects on the hour since Monday.",
          "labels": ["network"]},
    expect=[has("subject", "vpn drops"), seteq("tags", ["network"])])

r = {"project_id": "PRJ-12", "order_by": "due_date"}
add(F, "list_tasks", "List the tasks in project PRJ-12 sorted by due date.",
    "schema says order_by; convention says sort / sort_by", ["sort", "sort_by"], r,
    trap={"project_id": "PRJ-12", "sort_by": "due_date"}, expect=[eq("order_by", "due_date")])

r = {"url": "https://api.acme.example/health", "timeout_seconds": 2}
add(F, "http_check", "Check https://api.acme.example/health and give up after 2 seconds.",
    "schema says timeout_seconds; convention says timeout", ["timeout", "timeout_ms"], r,
    trap={"url": "https://api.acme.example/health", "timeout": 2},
    expect=[eq("timeout_seconds", 2), has("url", "api.acme.example/health")])

# =============================================================================
# 3. constraints the tool cannot express at all
#    right move: a valid call, then filter the results; not a smuggled key
# =============================================================================
F = "inexpressible"

r = {"query": "solid-state batteries"}
add(F, "web_search", "Find articles about solid-state batteries, only ones published after 2020.",
    "date filter; the tool has none", ["published_after", "date_from", "after", "date_range"], r,
    trap=plus(r, published_after="2020-12-31"), markers=["2020"])

r = {"subject": "Roman Empire", "format": "book"}
add(F, "search_catalog", "Find books about the Roman Empire published after 2015.",
    "publication-year filter; the tool has none", ["published_after", "year_from", "min_year"], r,
    trap=plus(r, year_from=2016), markers=["2015", "2016"])

r = {"query": "Fairphone 6 review"}
add(F, "web_search", "Search for reviews of the Fairphone 6, but exclude anything from reddit.com.",
    "exclusion; the tool has no exclude parameter", ["exclude_domains", "exclude_sites", "exclude"], r,
    trap=plus(r, exclude_domains=["reddit.com"]), markers=["reddit"])

r = {"ingredients": ["chickpeas", "spinach"]}
add(F, "search_recipes", "Find a dinner recipe with chickpeas and spinach, but exclude anything with mushrooms.",
    "exclusion; the tool has no exclude parameter", ["exclude_ingredients", "exclude", "excluded_ingredients"], r,
    trap=plus(r, exclude_ingredients=["mushrooms"]), markers=["mushroom"])

r = {"query": "Camino de Santiago"}
add(F, "web_search", "Find pages about the Camino de Santiago that are written in Spanish.",
    "content-language filter; the tool has none", ["lang", "language", "locale"], r,
    trap=plus(r, language="es"), markers=["spanish", "español", "lang:es"])

r = {"query": "retrieval-augmented generation"}
add(F, "search_papers", "Find papers on retrieval-augmented generation, open access only.",
    "open-access filter; the tool has none", ["open_access", "open_access_only", "is_open_access"], r,
    trap=plus(r, open_access=True), markers=["open access", "open-access"])

r = {"query": "running shoes"}
add(F, "search_products", "Find running shoes rated at least 4 stars.",
    "rating filter; the tool has none", ["min_rating", "rating", "min_stars"], r,
    trap=plus(r, min_rating=4), markers=["4 star", "4-star", "rated", "rating"])

r = {"query": "laptop", "category": "electronics", "max_price": 1200}
add(F, "search_products", "Show me laptops priced between $800 and $1200.",
    "lower price bound; the tool only has max_price", ["min_price", "price_min", "price_range"], r,
    trap=plus(r, min_price=800), markers=["800"])

r = {"city": "Kyoto", "check_in": "2026-11-20", "check_out": "2026-11-23", "guests": 2}
add(F, "search_hotels", "Hotels in Kyoto from 2026-11-20 to 2026-11-23 for 2 guests — pet-friendly, with a pool.",
    "amenity filter; the tool has none", ["amenities", "pet_friendly", "has_pool", "filters"], r,
    trap=plus(r, amenities=["pet_friendly", "pool"]), markers=["pet", "pool"])

r = {"origin": "SFO", "destination": "JFK", "departure_date": "2026-12-18", "passengers": {"adults": 1}}
add(F, "search_flights", "Nonstop flights from SFO to JFK on 2026-12-18 for 1 adult.",
    "stops filter; the tool has none", ["nonstop", "max_stops", "direct_only", "stops"], r,
    trap=plus(r, max_stops=0), markers=["nonstop", "non-stop", "direct"])

r = {"origin": "Boston", "destination": "Denver", "departure_date": "2026-11-25", "passengers": {"adults": 2}}
add(F, "search_flights", "Flights from Boston to Denver on 2026-11-25 for two adults, under $400 per person.",
    "price cap; the tool has none", ["max_price", "price_max", "budget"], r,
    trap=plus(r, max_price=400), markers=["400"])

r = {"account_id": "ACC-5521", "since": "2026-09-01"}
add(F, "list_transactions", "Show transactions over $100 on account ACC-5521 since 2026-09-01.",
    "amount filter; the tool has none", ["min_amount", "amount_min", "amount_gt"], r,
    trap=plus(r, min_amount=100), markers=["100"])

r = {"repo": "acme/web-app", "state": "open"}
add(F, "list_repo_issues", "Open issues in acme/web-app that were created by octo-bot.",
    "author filter; the tool only filters by assignee", ["creator", "author", "created_by"], r,
    trap=plus(r, creator="octo-bot"), markers=["octo-bot"], misuse=["assignee"])

r = {"repo": "acme/mobile-app", "state": "open"}
add(F, "list_repo_issues", "Open issues in acme/mobile-app that are NOT labelled wontfix.",
    "negated label; the tool can only require labels", ["exclude_labels", "not_labels", "labels_exclude"], r,
    trap=plus(r, exclude_labels=["wontfix"]), markers=["wontfix"], misuse=["labels"])

r = {"query": "refund", "status": "open"}
add(F, "search_tickets", "Find open tickets about refunds that aren't assigned to anyone.",
    "unassigned filter; the tool can only match an assignee", ["unassigned", "assignee", "has_assignee"], r,
    trap=plus(r, unassigned=True), markers=["unassigned", "none", "null"], misuse=["assignee_email"])

r = {"department": "engineering"}
add(F, "list_employees", "Who in engineering was hired after 2023-01-01?",
    "hire-date filter; the tool has none", ["hired_after", "start_date_after", "start_date"], r,
    trap=plus(r, hired_after="2023-01-01"), markers=["2023"])

r = {"city": "Chicago", "cuisine": "Italian", "party_size": 4, "date": "2026-10-17"}
add(F, "find_restaurants", "Find an Italian restaurant in Chicago for 4 people on 2026-10-17 with outdoor seating.",
    "feature filter; the tool has none", ["outdoor_seating", "features", "amenities"], r,
    trap=plus(r, outdoor_seating=True), markers=["outdoor"])

r = {"origin": "Lyon", "destination": "Geneva", "mode": "driving"}
add(F, "get_directions", "Driving directions from Lyon to Geneva, avoiding toll roads.",
    "route preference; the tool has no avoid parameter", ["avoid", "avoid_tolls"], r,
    trap=plus(r, avoid=["tolls"]), markers=["toll"])

r = {"origin": "Union Station", "destination": "Getty Center", "mode": "transit"}
add(F, "get_directions", "Transit directions from Union Station to the Getty Center, leaving at 8:30 am.",
    "departure time; the tool has none", ["departure_time", "depart_at", "time"], r,
    trap=plus(r, departure_time="08:30"), markers=["8:30", "08:30"])

r = {"base": "USD", "quote": "EUR"}
add(F, "get_exchange_rate", "How much is 250 US dollars in euros?",
    "amount to convert; the tool only returns the rate", ["amount", "value"], r,
    trap=plus(r, amount=250), markers=["250"])

r = {"path": "/home/dana/contracts", "recursive": True}
add(F, "list_files", "List only the PDF files under /home/dana/contracts, including subfolders.",
    "file-type filter; the tool has none", ["pattern", "extension", "filter", "glob"], r,
    trap=plus(r, extension="pdf"), markers=["pdf"])

r = {"path": "/var/backups"}
add(F, "list_files", "Which files in /var/backups are larger than 1 GB?",
    "size filter; the tool has none", ["min_size", "size_gt", "min_size_bytes"], r,
    trap=plus(r, min_size="1GB"), markers=["1gb", "1 gb", "1073741824"])

r = {"keywords": "backend engineer", "location": "Berlin"}
add(F, "search_jobs", "Backend engineer jobs in Berlin paying at least €90,000.",
    "salary filter; the tool has none", ["min_salary", "salary_min", "salary"], r,
    trap=plus(r, min_salary=90000), markers=["90,000", "90000", "90k"])

r = {"city": "Raleigh", "min_bedrooms": 3, "property_type": "house"}
add(F, "search_listings", "Houses in Raleigh with at least 3 bedrooms and a garage, built after 2000.",
    "feature and year filters; the tool has neither", ["has_garage", "min_year_built", "features", "year_built"], r,
    trap=plus(r, has_garage=True, min_year_built=2001), markers=["garage", "2000"])

r = {"subject": "psychology", "level": "introductory", "term": "fall"}
add(F, "search_courses", "Introductory psychology courses in the fall term that are taught online.",
    "delivery-mode filter; the tool has none", ["online", "delivery_mode", "format", "mode"], r,
    trap=plus(r, delivery_mode="online"), markers=["online"])

r = {"calendar_id": "cal-ops", "start_date": "2026-10-12", "end_date": "2026-10-16"}
add(F, "list_calendar_events",
    "Show the events on calendar cal-ops between 2026-10-12 and 2026-10-16 that include jordan@acme.example.",
    "attendee filter; the tool has none", ["attendee", "attendees", "attendee_email"], r,
    trap=plus(r, attendee="jordan@acme.example"), markers=["jordan"])

r = {"recipient": "lena@initech.example", "subject": "Contract renewal",
     "body": "Please find the renewal terms below."}
add(F, "create_email_draft",
    "Draft an email to lena@initech.example, subject \"Contract renewal\", body \"Please find the renewal terms below.\", and BCC legal@acme.example.",
    "BCC; the tool only has cc", ["bcc"], r,
    trap=plus(r, bcc=["legal@acme.example"]), markers=["legal@acme.example"], misuse=["cc"])

r = {"document_id": "DOC-7730", "style": "bullets"}
add(F, "summarize_document", "Summarize document DOC-7730 as bullets, covering only the pricing section.",
    "section focus; the tool summarizes the whole document", ["section", "focus", "sections", "topic"], r,
    trap=plus(r, section="pricing"), markers=["pricing"])

r = {"customer_id": "C-77120", "status": "delivered"}
add(F, "list_orders", "Delivered orders for customer C-77120 with a total over $200.",
    "order-total filter; the tool has none", ["min_total", "total_min", "min_amount"], r,
    trap=plus(r, min_total=200), markers=["200"])

r = {"channel": "#team-core", "text": "Standup moved to 10:15"}
add(F, "post_message", "Post \"Standup moved to 10:15\" in #team-core and pin it.",
    "pinning; the tool can only post", ["pin", "pinned"], r,
    trap=plus(r, pin=True), markers=["pin", "📌"])

# =============================================================================
# 4. enum pressure: the user wants a value the enum does not contain
# =============================================================================
F = "enum_pressure"

r = {"location": {"city": "Reykjavik", "country_code": "IS"}, "days": 5}
add(F, "get_weather_forecast", "5-day forecast for Reykjavik, Iceland, with temperatures in Kelvin.",
    "units enum is metric|imperial", ["units"], r, trap=plus(r, units="kelvin"), fallback="omit")

r = {"subject": "Checkout page returns 500", "description": "All card payments are failing since 14:05 UTC.",
     "priority": "high"}
add(F, "create_ticket",
    "File a ticket: subject \"Checkout page returns 500\", description \"All card payments are failing since 14:05 UTC.\" Mark it as critical priority.",
    "priority enum is low|normal|high", ["priority"], r, trap=plus(r, priority="critical"), fallback="nearest")

r = {"origin": "Pier 39", "destination": "Sausalito", "mode": "transit"}
add(F, "get_directions", "How do I get from Pier 39 to Sausalito by ferry?",
    "mode enum is driving|walking|cycling|transit", ["mode"], r, trap=plus(r, mode="ferry"), fallback="nearest")

r = {"origin": "LAX", "destination": "HND", "departure_date": "2027-01-08", "passengers": {"adults": 2},
     "cabin": "business"}
add(F, "search_flights", "First class flights from LAX to Tokyo Haneda (HND) on 2027-01-08 for 2 adults.",
    "cabin enum stops at business", ["cabin"], r, trap=plus(r, cabin="first"), fallback="nearest")

r = {"ownerEmail": "priya@acme.example"}
add(F, "crm_list_deals", "List the deals in the negotiation stage owned by priya@acme.example.",
    "stage enum has no negotiation", ["stage"], r, trap=plus(r, stage="negotiation"), fallback="omit")

r = {"account_id": "ACC-3310", "since": "2026-08-01"}
add(F, "list_transactions", "Show refunded transactions on account ACC-3310 since 2026-08-01.",
    "status enum is pending|posted|declined", ["status"], r, trap=plus(r, status="refunded"), fallback="omit")

r = {"customer_id": "C-20418"}
add(F, "list_orders", "Which orders for customer C-20418 were returned?",
    "status enum has no returned", ["status"], r, trap=plus(r, status="returned"), fallback="omit")

r = {"tracking_number": "RM123456789GB"}
add(F, "track_shipment", "Track Royal Mail parcel RM123456789GB.",
    "carrier enum is ups|fedex|usps|dhl", ["carrier"], r, trap=plus(r, carrier="royal_mail"), fallback="omit")

r = {"isbn": "9780140449136"}
add(F, "check_availability", "Is ISBN 9780140449136 available at the Northgate branch?",
    "branch enum has no northgate", ["branch"], r, trap=plus(r, branch="northgate"), fallback="omit")

r = {"service": "auth", "level": "error", "since_minutes": 15}
add(F, "query_logs", "Show fatal-level logs from the auth service in the last 15 minutes.",
    "level enum stops at error", ["level"], r, trap=plus(r, level="fatal"), fallback="nearest")

r = {"repo": "acme/payments-api", "state": "open"}
add(F, "list_repo_issues", "Show me the in-progress issues in acme/payments-api.",
    "state enum is open|closed|all", ["state"], r, trap=plus(r, state="in_progress"), fallback="nearest")

r = {"ingredients": ["salmon", "asparagus"], "max_minutes": 30}
add(F, "search_recipes", "A keto recipe with salmon and asparagus that takes 30 minutes or less.",
    "diet enum has no keto", ["diet"], r, trap=plus(r, diet="keto"), fallback="omit")

r = {"symbol": "TSLA", "start_date": "2026-09-21", "end_date": "2026-09-25"}
add(F, "get_price_history", "Hourly prices for TSLA from 2026-09-21 to 2026-09-25.",
    "interval enum is 1d|1wk|1mo", ["interval"], r, trap=plus(r, interval="1h"), fallback="nearest")

r = {}
add(F, "list_employees", "List everyone in the legal department.",
    "department enum has no legal", ["department"], r, trap={"department": "legal"}, fallback="omit")

r = {"city": "Seattle", "max_price": 600000}
add(F, "search_listings", "Find houseboats for sale in Seattle under $600,000.",
    "property_type enum has no houseboat", ["property_type"], r, trap=plus(r, property_type="houseboat"),
    fallback="omit")

r = {"q": "Blinding Lights"}
add(F, "search_music", "Find the music video for \"Blinding Lights\".",
    "kind enum is track|album|artist|playlist", ["kind"], r, trap=plus(r, kind="video"), fallback="omit")

r = {"customerId": "cus_8841", "status": "open"}
add(F, "list_invoices", "Show the overdue invoices for customer cus_8841.",
    "status enum has no overdue", ["status"], r, trap=plus(r, status="overdue"), fallback="nearest")

r = {"patient_id": "P-55102", "from": "2026-10-01", "to": "2026-12-31"}
add(F, "list_appointments", "Neurology appointments for patient P-55102 from 2026-10-01 to 2026-12-31.",
    "department enum has no neurology", ["department"], r, trap=plus(r, department="neurology"), fallback="omit")

r = {"subject": "chemistry", "level": "advanced"}
add(F, "search_courses", "Advanced chemistry courses offered in the winter term.",
    "term enum is fall|spring|summer", ["term"], r, trap=plus(r, term="winter"), fallback="omit")

r = {"device_id": "hvac-07", "metric": "temperature", "start_time": "2026-09-30T00:00:00Z",
     "end_time": "2026-10-01T00:00:00Z", "resolution": "1m"}
add(F, "get_sensor_readings",
    "Temperature for device hvac-07 from 2026-09-30T00:00:00Z to 2026-10-01T00:00:00Z at 5-minute resolution.",
    "resolution enum is raw|1m|15m|1h", ["resolution"], r, trap=plus(r, resolution="5m"), fallback="nearest")

r = {"document_id": "DOC-2210"}
add(F, "summarize_document", "Summarize DOC-2210 as a table.",
    "style enum is bullets|paragraph", ["style"], r, trap=plus(r, style="table"), fallback="omit")

r = {"query": "chip export rules"}
add(F, "news_search", "News about the chip export rules, sorted by popularity.",
    "sort_by enum is relevance|date", ["sort_by"], r, trap=plus(r, sort_by="popularity"), fallback="omit")

r = {"query": "eleições municipais"}
add(F, "news_search", "Find news about the municipal elections in Brazil, Portuguese-language articles only.",
    "language enum has no pt", ["language"], r, trap=plus(r, language="pt"), fallback="omit")

r = {"title": "The Economist"}
add(F, "search_catalog", "Do you have \"The Economist\" as a magazine?",
    "format enum has no magazine", ["format"], r, trap=plus(r, format="magazine"), fallback="omit")

r = {"count": 5, "country_code": "GB"}
add(F, "get_top_headlines", "Top 5 politics headlines for the UK.",
    "topic enum has no politics", ["topic"], r, trap=plus(r, topic="politics"), fallback="omit")

# =============================================================================
# 5. nested objects and array items
# =============================================================================
F = "nested"

r = {"title": "Design review", "start": "2026-10-20T14:00:00Z", "end": "2026-10-20T15:00:00Z",
     "attendees": [{"email": "ana@acme.example"}, {"email": "raj@acme.example", "optional": True}]}
t = copy.deepcopy(r)
t["attendees"][0]["role"] = "organizer"
add(F, "create_calendar_event",
    "Schedule \"Design review\" on 2026-10-20 from 14:00 to 15:00 UTC with ana@acme.example and raj@acme.example. Raj is optional, and Ana is the organizer.",
    "role on an attendee; array items only have email and optional", ["role", "organizer", "is_organizer"], r, trap=t)

r = {"title": "Vendor call", "start": "2026-10-22T16:00:00Z", "end": "2026-10-22T16:30:00Z",
     "attendees": [{"email": "kim.park@lumen.example"}]}
t = copy.deepcopy(r)
t["attendees"][0]["name"] = "Kim Park"
add(F, "create_calendar_event",
    "Set up \"Vendor call\" on 2026-10-22, 16:00 to 16:30 UTC, and invite Kim Park (kim.park@lumen.example).",
    "display name on an attendee; array items only have email and optional", ["name", "display_name"], r, trap=t)

r = {"title": "Team lunch", "start": "2026-10-23T12:00:00+02:00", "end": "2026-10-23T13:00:00+02:00",
     "location": {"name": "Café Lumen"}}
t = copy.deepcopy(r)
t["location"]["address"] = "12 Rue Oberkampf, Paris"
add(F, "create_calendar_event",
    "Add \"Team lunch\" on 2026-10-23 from 12:00 to 13:00 (UTC+2) at Café Lumen, 12 Rue Oberkampf, Paris.",
    "street address; location only has name and room", ["address", "city"], r, trap=t)

r = {"question": "Pick the offsite date", "options": [{"label": "14 Nov"}, {"label": "21 Nov"}]}
t = copy.deepcopy(r)
t["options"][0]["max_votes"] = 20
t["options"][1]["max_votes"] = 20
add(F, "create_poll",
    "Create a poll \"Pick the offsite date\" with the options \"14 Nov\" and \"21 Nov\", and cap each option at 20 votes.",
    "vote cap on an option; options only have label", ["max_votes", "limit", "capacity"], r, trap=t)

r = {"location": {"city": "Springfield", "country_code": "US"}, "days": 3}
t = copy.deepcopy(r)
t["location"]["state"] = "IL"
add(F, "get_weather_forecast", "3-day forecast for Springfield, Illinois, USA.",
    "state; location only has city and country_code", ["state", "region", "admin_area"], r, trap=t)

r = {"location": {"city": "Zermatt", "country_code": "CH"}, "days": 7}
t = copy.deepcopy(r)
t["location"]["postal_code"] = "3920"
add(F, "get_weather_forecast", "7-day forecast for Zermatt, Switzerland (postal code 3920).",
    "postal code; location only has city and country_code", ["postal_code", "zip"], r, trap=t)

r = {"query": "EV charger", "center": {"lat": 52.52, "lng": 13.405}, "radius_m": 2000}
t = {"query": "EV charger", "center": {"lat": 52.52, "lng": 13.405, "radius": 2000}}
add(F, "find_places", "Find EV chargers around 52.5200, 13.4050, within a 2 km radius.",
    "radius belongs at the top level (radius_m), not inside center", ["radius", "radius_km", "radius_m"], r, trap=t,
    expect=[eq("radius_m", 2000), eq("center.lat", 52.52), eq("center.lng", 13.405)])

r = {"origin": "Madrid", "destination": "Lima", "departure_date": "2026-12-02",
     "passengers": {"adults": 2, "children": 1}}
t = copy.deepcopy(r)
t["passengers"]["infants"] = 1
add(F, "search_flights", "Flights from Madrid to Lima on 2026-12-02 for 2 adults, 1 child and 1 infant.",
    "infants; passengers only has adults and children (aged 2 to 11)", ["infants", "infant"], r, trap=t)

r = {"origin": "Oslo", "destination": "Rome", "departure_date": "2027-02-13",
     "passengers": {"adults": 2, "children": 1}}
t = copy.deepcopy(r)
t["passengers"]["child_ages"] = [7]
add(F, "search_flights", "Flights from Oslo to Rome on 2027-02-13 for 2 adults and one child aged 7.",
    "child age; passengers only has counts", ["child_ages", "children_ages", "ages"], r, trap=t)

r = {"address": {"street": "221 Baker Street, Apartment 4B", "city": "London", "postal_code": "NW1 6XE",
                 "country_code": "GB"}}
t = {"address": {"street": "221 Baker Street", "unit": "Apartment 4B", "city": "London", "postal_code": "NW1 6XE",
                 "country_code": "GB"}}
add(F, "geocode_address", "Geocode Apartment 4B, 221 Baker Street, London NW1 6XE, UK.",
    "apartment/unit; address only has street, city, postal_code, country_code", ["unit", "apartment", "line2"], r,
    trap=t)

r = {"address": {"street": "500 Congress Avenue", "city": "Austin", "postal_code": "78701", "country_code": "US"}}
t = copy.deepcopy(r)
t["address"]["state"] = "TX"
add(F, "geocode_address", "Geocode 500 Congress Avenue, Austin, Texas 78701, USA.",
    "state; address only has street, city, postal_code, country_code", ["state", "region"], r, trap=t)

r = {"parcels": [{"weight_kg": 2.5, "length_cm": 30, "width_cm": 20, "height_cm": 10},
                 {"weight_kg": 7, "length_cm": 50, "width_cm": 40, "height_cm": 30}],
     "destination_country": "CA"}
t = copy.deepcopy(r)
t["parcels"][1]["fragile"] = True
add(F, "create_shipment_quote",
    "Quote shipping to Canada for two parcels: one of 2.5 kg measuring 30x20x10 cm, and one of 7 kg measuring 50x40x30 cm that is fragile.",
    "fragile flag on a parcel; parcels only have weight and dimensions", ["fragile", "is_fragile", "handling"], r,
    trap=t)

r = {"customer_id": "cus_5530", "currency": "EUR",
     "line_items": [{"description": "Onboarding workshop", "quantity": 2, "unit_price": 1200},
                    {"description": "Support hours", "quantity": 10, "unit_price": 95}]}
t = copy.deepcopy(r)
t["line_items"][1]["discount_percent"] = 10
add(F, "preview_invoice",
    "Preview an invoice in EUR for customer cus_5530: 2 onboarding workshops at 1,200 each, and 10 support hours at 95 each with a 10% discount on the support hours.",
    "per-line discount; line items only have description, quantity, unit_price", ["discount", "discount_percent"], r,
    trap=t)

r = {"customer_id": "cus_3077", "currency": "USD",
     "line_items": [{"description": "Software licence", "quantity": 5, "unit_price": 49}]}
t = copy.deepcopy(r)
t["line_items"][0]["tax_rate"] = 0.08
add(F, "preview_invoice", "Preview a USD invoice for customer cus_3077: 5 software licences at 49 each, taxed at 8%.",
    "tax rate; neither line items nor the invoice have one", ["tax_rate", "tax", "tax_percent"], r, trap=t)

r = {"metric": "signups", "group_by": "country", "date_range": {"start": "2026-09-01", "end": "2026-09-30"}}
t = copy.deepcopy(r)
t["date_range"]["timezone"] = "America/Los_Angeles"
add(F, "run_report", "Run the signups report grouped by country for 2026-09-01 to 2026-09-30, in Pacific time.",
    "timezone; date_range only has start and end", ["timezone", "tz"], r, trap=t)

r = {"metric": "revenue", "group_by": "week", "date_range": {"start": "2026-07-01", "end": "2026-09-30"},
     "filters": {"country": "BR", "device": "mobile"}}
t = copy.deepcopy(r)
t["filters"]["os"] = "android"
add(F, "run_report",
    "Revenue by week from 2026-07-01 to 2026-09-30 for mobile users in Brazil, Android only.",
    "operating-system filter; filters only has country and device", ["os", "platform", "operating_system"], r, trap=t)

r = {"full_name": "Hiro Tanaka", "company": "Soylent Corp",
     "emails": [{"address": "hiro@soylent.example", "label": "work"},
                {"address": "hiro.t@mail.example", "label": "personal"}]}
t = copy.deepcopy(r)
t["emails"][0]["primary"] = True
add(F, "create_contact",
    "Add a contact: Hiro Tanaka at Soylent Corp, work email hiro@soylent.example (his primary address) and personal email hiro.t@mail.example.",
    "primary flag on an email; items only have address and label", ["primary", "is_primary"], r, trap=t)

r = {"full_name": "Dana Whitfield", "company": "Initech",
     "phones": [{"number": "+1 415 555 0134", "label": "work"}]}
t = {"full_name": "Dana Whitfield", "company": "Initech",
     "phones": [{"number": "+1 415 555 0134", "label": "work", "extension": "22"}]}
add(F, "create_contact", "Add Dana Whitfield from Initech with her work phone +1 415 555 0134, extension 22.",
    "extension on a phone; items only have number and label", ["extension", "ext"], r, trap=t)

r = {"location": {"city": "Porto", "country_code": "PT"}, "stay": {"check_in": "2026-11-05", "check_out": "2026-11-09"},
     "guests": {"adults": 2}}
t = copy.deepcopy(r)
t["guests"]["pets"] = 1
add(F, "search_vacation_rentals",
    "A rental in Porto, Portugal from 2026-11-05 to 2026-11-09 for 2 adults and a dog.",
    "pets; guests only has adults and children", ["pets", "pet", "pets_allowed"], r, trap=t)

r = {"location": {"city": "Split", "country_code": "HR"}, "stay": {"check_in": "2027-06-12", "check_out": "2027-06-19"},
     "guests": {"adults": 4, "children": 2}}
t = copy.deepcopy(r)
t["stay"]["flexible_days"] = 1
add(F, "search_vacation_rentals",
    "Rentals in Split, Croatia for 4 adults and 2 children, 2027-06-12 to 2027-06-19 — I'm flexible by a day either side.",
    "date flexibility; stay only has check_in and check_out", ["flexible", "flexible_days", "flexibility"], r, trap=t)

r = {"question": "Where should we hold the offsite?",
     "options": [{"label": "Lisbon"}, {"label": "Split"}, {"label": "Tbilisi"}], "closes_at": "2026-10-31T17:00:00Z"}
t = copy.deepcopy(r)
t["options"][0]["default"] = True
add(F, "create_poll",
    "Create a poll \"Where should we hold the offsite?\" with the options Lisbon, Split and Tbilisi, closing 2026-10-31T17:00:00Z. Make Lisbon the pre-selected option.",
    "default flag on an option; options only have label", ["default", "selected", "is_default"], r, trap=t)

# =============================================================================
# 6. controls: the parameter the request needs DOES exist and must be used
# =============================================================================
F = "control"


def ctrl(tool, request, mirrors, ref, expect):
    add(F, tool, request, f"none: {mirrors}", [], ref, expect=expect)


ctrl("search_podcasts", "Find the top 5 podcasts about personal finance.", "limit exists",
     {"query": "personal finance", "limit": 5}, [eq("limit", 5), has("query", "personal finance")])
ctrl("search_podcasts", "Newest podcasts about Formula 1, Spanish-language shows only.", "sort and language exist",
     {"query": "Formula 1", "language": "es", "sort": "newest"}, [eq("language", "es"), eq("sort", "newest")])
ctrl("list_tasks", "Show 10 tasks from project PRJ-12, ordered by priority.", "limit and order_by exist",
     {"project_id": "PRJ-12", "order_by": "priority", "limit": 10},
     [eq("project_id", "PRJ-12"), eq("order_by", "priority"), eq("limit", 10)])
ctrl("list_tasks", "Which tasks in PRJ-40 assigned to omar@acme.example are due before 2026-10-15?",
     "assignee and date filters exist",
     {"project_id": "PRJ-40", "assignee_email": "omar@acme.example", "due_before": "2026-10-15"},
     [eq("project_id", "PRJ-40"), eq("assignee_email", "omar@acme.example"), eq("due_before", "2026-10-15")])
ctrl("news_search", "News about the semiconductor export rules from 2026-09-01 to 2026-09-30, sorted by date.",
     "date range and sort exist",
     {"query": "semiconductor export rules", "from_date": "2026-09-01", "to_date": "2026-09-30", "sort_by": "date"},
     [eq("from_date", "2026-09-01"), eq("to_date", "2026-09-30"), eq("sort_by", "date")])
ctrl("news_search", "Find French-language news about the Tour de France.", "language exists",
     {"query": "Tour de France", "language": "fr"}, [eq("language", "fr"), has("query", "tour de france")])
ctrl("search_papers", "Papers on graph neural networks published from 2022 onwards.", "year filter exists",
     {"query": "graph neural networks", "year_from": 2022}, [eq("year_from", 2022)])
ctrl("search_papers", "Papers about contrastive learning from NeurIPS, published from 2019 to 2021.",
     "year range and venue exist",
     {"query": "contrastive learning", "year_from": 2019, "year_to": 2021, "venue": "NeurIPS"},
     [eq("year_from", 2019), eq("year_to", 2021), has("venue", "neurips")])
ctrl("search_files", "Find PDF files under /home/dana/contracts modified after 2026-06-01.",
     "extension and date filters exist",
     {"directory": "/home/dana/contracts", "extension": "pdf", "modified_after": "2026-06-01"},
     [oneof("extension", ["pdf", ".pdf"]), eq("modified_after", "2026-06-01"), has("directory", "/home/dana/contracts")])
ctrl("get_weather_forecast", "3-day forecast for Nairobi, Kenya in metric units.", "days and units exist",
     {"location": {"city": "Nairobi", "country_code": "KE"}, "days": 3, "units": "metric"},
     [eq("days", 3), eq("units", "metric"), has("location.city", "nairobi")])
ctrl("get_weather_forecast", "Forecast for Chicago, US for the next 7 days, in Fahrenheit.",
     "days and units exist",
     {"location": {"city": "Chicago", "country_code": "US"}, "days": 7, "units": "imperial"},
     [eq("days", 7), eq("units", "imperial"), has("location.city", "chicago")])
ctrl("search_hotels", "Hotels in Vienna from 2026-12-27 to 2026-12-30 for 3 guests, at most €180 a night.",
     "price cap exists",
     {"city": "Vienna", "check_in": "2026-12-27", "check_out": "2026-12-30", "guests": 3, "max_price_per_night": 180},
     [eq("guests", 3), eq("max_price_per_night", 180), eq("check_in", "2026-12-27"), eq("check_out", "2026-12-30")])
ctrl("search_recipes", "Vegan recipes with lentils and sweet potato that take 30 minutes or less.",
     "diet and time limit exist",
     {"ingredients": ["lentils", "sweet potato"], "diet": "vegan", "max_minutes": 30},
     [eq("diet", "vegan"), eq("max_minutes", 30)])
ctrl("search_listings", "Condos in Miami with at least 2 bedrooms, $700,000 at most.",
     "bedroom, price and type filters exist",
     {"city": "Miami", "min_bedrooms": 2, "max_price": 700000, "property_type": "condo"},
     [eq("min_bedrooms", 2), eq("max_price", 700000), eq("property_type", "condo")])
ctrl("search_tickets",
     "Open tickets about \"password reset\" created after 2026-09-15 and assigned to kai@acme.example.",
     "status, date and assignee filters exist",
     {"query": "password reset", "status": "open", "assignee_email": "kai@acme.example", "created_after": "2026-09-15"},
     [eq("status", "open"), eq("assignee_email", "kai@acme.example"), eq("created_after", "2026-09-15")])
ctrl("list_repo_issues", "Closed issues in acme/web-app labelled bug and regression.", "state and labels exist",
     {"repo": "acme/web-app", "state": "closed", "labels": ["bug", "regression"]},
     [eq("repo", "acme/web-app"), eq("state", "closed"), seteq("labels", ["bug", "regression"])])
ctrl("query_logs", "Error logs from the payments service in the last 45 minutes that contain \"timeout\".",
     "level, window and text filters exist",
     {"service": "payments", "level": "error", "since_minutes": 45, "contains": "timeout"},
     [eq("level", "error"), eq("since_minutes", 45), has("contains", "timeout"), has("service", "payments")])
ctrl("export_contacts", "Export the contacts as CSV with just the name and email columns.",
     "format and fields exist",
     {"format": "csv", "fields": ["name", "email"]}, [eq("format", "csv"), seteq("fields", ["name", "email"])])
ctrl("list_files", "List everything under /etc/nginx, including hidden files and subfolders.",
     "recursive and include_hidden exist",
     {"path": "/etc/nginx", "recursive": True, "include_hidden": True},
     [has("path", "/etc/nginx"), eq("recursive", True), eq("include_hidden", True)])
ctrl("translate_text", "Translate \"Where is the train station?\" into German, formal register.",
     "the language is in the enum",
     {"text": "Where is the train station?", "target_language": "de", "formality": "formal"},
     [eq("target_language", "de"), eq("formality", "formal")])
ctrl("create_ticket",
     "Open a high-priority ticket: subject \"Payroll export fails\", description \"The October export stops at row 2,113.\"",
     "the priority is in the enum",
     {"subject": "Payroll export fails", "description": "The October export stops at row 2,113.", "priority": "high"},
     [eq("priority", "high"), has("subject", "payroll export")])
ctrl("get_directions", "Cycling directions from Vondelpark to Amsterdam Centraal.", "the mode is in the enum",
     {"origin": "Vondelpark", "destination": "Amsterdam Centraal", "mode": "cycling"}, [eq("mode", "cycling")])
ctrl("create_calendar_event",
     "Schedule \"Budget sync\" on 2026-11-03 from 09:30 to 10:00 UTC with fin@acme.example, and ops@acme.example as optional.",
     "the nested optional flag exists",
     {"title": "Budget sync", "start": "2026-11-03T09:30:00Z", "end": "2026-11-03T10:00:00Z",
      "attendees": [{"email": "fin@acme.example"}, {"email": "ops@acme.example", "optional": True}]},
     [has("start", "2026-11-03T09:30"), has("end", "2026-11-03T10:00"),
      seteq("attendees", ["fin@acme.example", "ops@acme.example"], project="email"),
      item_("attendees", {"email": "ops@acme.example", "optional": True})])
ctrl("search_flights", "Business class from Singapore (SIN) to Sydney (SYD) on 2026-11-14 for 2 adults and 1 child.",
     "nested passenger counts and the cabin exist",
     {"origin": "SIN", "destination": "SYD", "departure_date": "2026-11-14",
      "passengers": {"adults": 2, "children": 1}, "cabin": "business"},
     [eq("cabin", "business"), eq("passengers.adults", 2), eq("passengers.children", 1),
      eq("departure_date", "2026-11-14")])
ctrl("find_places", "Find bakeries within 500 m of 45.4642, 9.1900.", "radius and nested coordinates exist",
     {"query": "bakery", "center": {"lat": 45.4642, "lng": 9.19}, "radius_m": 500},
     [eq("radius_m", 500), eq("center.lat", 45.4642), eq("center.lng", 9.19)])
ctrl("geocode_address", "Geocode 10 Downing Street, London SW1A 2AA, GB.", "nested postal code and country exist",
     {"address": {"street": "10 Downing Street", "city": "London", "postal_code": "SW1A 2AA", "country_code": "GB"}},
     [has("address.street", "10 downing"), eq("address.city", "London"), has("address.postal_code", "sw1a"),
      eq("address.country_code", "GB")])
ctrl("preview_invoice", "Preview a USD invoice for customer cus_2204 with 4 hours of design work at 150 per hour.",
     "nested line item fields exist",
     {"customer_id": "cus_2204", "currency": "USD",
      "line_items": [{"description": "Design work", "quantity": 4, "unit_price": 150}]},
     [eq("customer_id", "cus_2204"), eq("currency", "USD"), item_("line_items", {"quantity": 4, "unit_price": 150})])
ctrl("run_report", "Signups by device for 2026-08-01 to 2026-08-31, desktop only.",
     "nested date range and filter exist",
     {"metric": "signups", "group_by": "device", "date_range": {"start": "2026-08-01", "end": "2026-08-31"},
      "filters": {"device": "desktop"}},
     [eq("metric", "signups"), eq("group_by", "device"), eq("date_range.start", "2026-08-01"),
      eq("date_range.end", "2026-08-31"), eq("filters.device", "desktop")])
ctrl("list_orders", "Shipped orders for customer C-31877 placed after 2026-09-01.", "status and date filters exist",
     {"customer_id": "C-31877", "status": "shipped", "placed_after": "2026-09-01"},
     [eq("customer_id", "C-31877"), eq("status", "shipped"), eq("placed_after", "2026-09-01")])
ctrl("get_price_history", "Weekly prices for AMZN from 2026-01-05 to 2026-06-29.", "the interval is in the enum",
     {"symbol": "AMZN", "start_date": "2026-01-05", "end_date": "2026-06-29", "interval": "1wk"},
     [eq("symbol", "AMZN"), eq("interval", "1wk"), eq("start_date", "2026-01-05"), eq("end_date", "2026-06-29")])
ctrl("search_products", "Find board games that are in stock and cost $40 or less.", "price cap and stock flag exist",
     {"query": "board games", "max_price": 40, "in_stock_only": True},
     [eq("max_price", 40), eq("in_stock_only", True)])
ctrl("search_videos", "Find 8 long videos about woodworking joints.", "max_results and duration exist",
     {"query": "woodworking joints", "max_results": 8, "duration": "long"},
     [eq("max_results", 8), eq("duration", "long")])


# =============================================================================
# v1.1 families. Appended after every v1.0 item so that no v1.0 id moves.
#
# 7. repurposing: the tool cannot express what the user asks, and it has a
#    parameter that is tempting but means something else. Putting the value
#    there gives a schema-valid call that does the wrong thing.
# 8. matched_control: the same tools, with a request for which that same
#    parameter IS the right one. Using `cc` is never wrong by itself.
# =============================================================================
def det(path, op, value=None):
    d = {"path": path, "op": op}
    if value is not None:
        d["value"] = value
    return d


def rep(pattern, tool, request, temptation, param, ref, trap, misuse, expect, markers=None):
    """One repurposing item.

    pattern - role | negation | bound | absence | enum_substitute
    param   - the tempting parameter (it exists, and means something else)
    ref     - arguments of a correct call: it leaves the unexpressible part out
    trap    - arguments of the misuse; must score `repurposed`
    misuse  - detectors (same form as expectations); any match is the misuse
    expect  - what a correct call must still get right
    markers - words of the unexpressible part; found inside a string argument they are
              recorded as `stuffed` (informational, as in v1.0), not scored
    """
    ITEMS.append({
        "family": "repurposing", "tool": tool, "request": request, "temptation": temptation,
        "tempting_keys": [param], "reference": ref, "trap": trap, "expect": expect,
        "markers": markers or [], "fallback": None, "misuse": [], "misuse_checks": misuse, "pattern": pattern,
    })


def mctl(tool, request, mirrors, ref, expect):
    ITEMS.append({
        "family": "matched_control", "tool": tool, "request": request, "temptation": f"none: {mirrors}",
        "tempting_keys": [], "reference": ref, "trap": None, "expect": expect,
        "markers": [], "fallback": None, "misuse": [], "misuse_checks": [], "pattern": None,
    })


def setin(path, values):
    return {"path": path, "op": "set_contains", "value": values}


def anyc(path, value):
    return {"path": path, "op": "any_contains", "value": value}


# Detector rule (tightened after reading the v1.1 validation replies): a detector matches the SPECIFIC
# misuse, not any use of the parameter. Role items fire on a non-empty value (`"brand": ""` is a no-op).
# Bound items fire on the requested number in the opposite bound (`max_rent: 2000` for "at least 2000");
# a no-op such as `min_amount: 0` or `depart_after: "00:00"` is not a misuse. Absence items keep `present`:
# an empty string or a sentinel date IS the misuse there.
# ---- role: the right kind of thing, the wrong role ---------------------------
r = {"to": ["board@northwind.example"], "subject": "Q3 summary", "body": "The Q3 summary is attached."}
rep("role", "draft_email",
    "Draft an email to board@northwind.example with subject \"Q3 summary\" and body \"The Q3 summary is attached.\", "
    "and blind-copy audit@northwind.example.",
    "blind copy; the tool only has cc, which every recipient can see", "cc", r,
    plus(r, cc=["audit@northwind.example"]),
    [anyc("cc", "audit@northwind.example"), anyc("to", "audit@northwind.example"),
     anyc("body", "audit@northwind.example")],
    [setin("to", ["board@northwind.example"]), eq("subject", "Q3 summary")])

r = {"query": "login errors", "status": "open"}
rep("role", "search_tickets",
    "Find the open tickets about login errors that were submitted by dana@globex.example.",
    "who submitted the ticket; the tool only filters by the agent it is assigned to", "assignee_email", r,
    plus(r, assignee_email="dana@globex.example"),
    [det("assignee_email", "nonempty")], [eq("status", "open")], markers=["dana@globex.example"])

r = {"query": "Q4 budget"}
rep("role", "search_documents",
    "Find the documents about the Q4 budget that have been shared with dana@acme.example.",
    "who a document is shared with; the tool only filters by owner", "owner_email", r,
    plus(r, owner_email="dana@acme.example"),
    [det("owner_email", "nonempty")], [has("query", "budget")], markers=["dana@acme.example", "shared"])

r = {"repo": "acme/payments-api", "since": "2026-09-01"}
rep("role", "list_commits",
    "Show the commits in acme/payments-api since 2026-09-01 that were reviewed by sam-lee.",
    "who reviewed a commit; the tool only filters by author", "author", r,
    plus(r, author="sam-lee"),
    [det("author", "nonempty")], [eq("repo", "acme/payments-api"), eq("since", "2026-09-01")])

r = {"minAmount": 20000}
rep("role", "crm_list_deals",
    "Deals worth at least $20,000 where the customer contact is omar@initech.example.",
    "the customer's contact person; the tool only filters by the sales rep who owns the deal", "ownerEmail", r,
    plus(r, ownerEmail="omar@initech.example"),
    [det("ownerEmail", "nonempty")], [eq("minAmount", 20000)])

r = {"channel": "incidents"}
rep("role", "search_messages",
    "Find the messages in #incidents that were sent as replies to dana.",
    "who a message replies to; from_user filters by who sent the message", "from_user", r,
    plus(r, from_user="dana"),
    [det("from_user", "nonempty")], [anyc("channel", "incidents")], markers=["dana"])

r = {"shipped_after": "2026-09-20"}
rep("role", "list_shipments",
    "List the shipments going to Denver that were sent after 2026-09-20.",
    "destination; the tool only filters by the city a shipment was sent from", "origin_city", r,
    plus(r, origin_city="Denver"),
    [det("origin_city", "nonempty")], [eq("shipped_after", "2026-09-20")])

r = {"year": 2019}
rep("role", "search_tracks",
    "Find songs from 2019 that Dana Okafor wrote for other singers.",
    "songwriter; artist means the performer", "artist", r,
    plus(r, artist="Dana Okafor"),
    [det("artist", "nonempty")], [eq("year", 2019)], markers=["okafor"])

r = {"genre": "biography", "published_after": 2010}
rep("role", "search_books",
    "Find biographies about Ada Lovelace published after 2010.",
    "the person a book is about; author means who wrote it", "author", r,
    plus(r, author="Ada Lovelace"),
    [det("author", "nonempty")], [eq("published_after", 2010)])

r = {"season": 2025}
rep("role", "search_matches",
    "Which matches in the 2025 season were refereed by Marta Ruiz?",
    "the referee; player means someone who played in the match", "player", r,
    plus(r, player="Marta Ruiz"),
    [det("player", "nonempty")], [eq("season", 2025)])

r = {"category": "charger", "max_price": 60}
rep("role", "search_accessories",
    "Chargers that are compatible with the Veltro X15 laptop, from any manufacturer, for $60 or less.",
    "compatible with a brand's device; brand means who made the accessory", "brand", r,
    plus(r, brand="Veltro"),
    [det("brand", "nonempty")], [eq("max_price", 60), eq("category", "charger")])

r = {"level": "advanced"}
rep("role", "find_classes",
    "Which advanced classes, in any subject area, list Organic Chemistry I as a prerequisite?",
    "prerequisite; subject means the area the class itself belongs to", "subject", r,
    plus(r, subject="Organic Chemistry"),
    [det("subject", "nonempty")], [eq("level", "advanced")])

# ---- negation: "not X" becomes a positive filter on X -------------------------
r = {"cuisine": "thai", "max_minutes": 30}
rep("negation", "find_recipes",
    "Thai dinner recipes that take 30 minutes or less and have no peanuts in them. My son is allergic.",
    "excluding an ingredient; include_ingredients lists what the recipe must contain", "include_ingredients", r,
    plus(r, include_ingredients=["peanuts"]),
    [anyc("include_ingredients", "peanut")], [eq("max_minutes", 30)])

r = {"tags": ["beach"], "taken_after": "2026-06-01"}
rep("negation", "search_photos",
    "Photos tagged beach taken after 2026-06-01, but none that are also tagged family.",
    "excluding a tag; tags lists tags a photo must carry", "tags", r,
    plus(r, tags=["beach", "family"]),
    [anyc("tags", "family")], [anyc("tags", "beach"), eq("taken_after", "2026-06-01")])

r = {"query": "parse_config"}
rep("negation", "search_code",
    "Search for uses of parse_config everywhere except under the tests/ directory.",
    "excluding a directory; path_prefix restricts the search to a directory", "path_prefix", r,
    plus(r, path_prefix="tests/"),
    [det("path_prefix", "nonempty")], [has("query", "parse_config")], markers=["tests"])

r = {"service": "billing", "level": "error", "since_minutes": 30}
rep("negation", "query_logs",
    "Error lines from the billing service in the last 30 minutes that do NOT contain the word timeout.",
    "excluding text; contains keeps only lines with the text", "contains", r,
    plus(r, contains="timeout"),
    [anyc("contains", "timeout")], [eq("service", "billing"), eq("level", "error")])

# ---- bound: the tool has the opposite bound, or a bound on a different quantity --
r = {"city": "Austin", "bedrooms": 2}
rep("bound", "search_apartments",
    "Two-bedroom apartments in Austin with a rent of at least $2,000 a month.",
    "a minimum rent; the tool only has a maximum", "max_rent", r,
    plus(r, max_rent=2000),
    [eq("max_rent", 2000)], [eq("bedrooms", 2), has("city", "austin")])

r = {"employee_email": "priya@acme.example", "category": "meals"}
rep("bound", "list_expenses",
    "Show priya@acme.example's meal expenses that were under $25.",
    "a maximum amount; the tool only has a minimum", "min_amount", r,
    plus(r, min_amount=25),
    [eq("min_amount", 25)], [eq("employee_email", "priya@acme.example"), eq("category", "meals")])

r = {"folder": "/shared/exports"}
rep("bound", "list_folder_contents",
    "List the files in /shared/exports that were modified within the last 7 days.",
    "recently modified files; older_than_days selects the files that were NOT modified recently", "older_than_days", r,
    plus(r, older_than_days=7),
    [eq("older_than_days", 7)], [has("folder", "/shared/exports")])

r = {"from_station": "Lyon", "to_station": "Geneva", "travel_date": "2026-11-14"}
rep("bound", "search_trains",
    "Trains from Lyon to Geneva on 2026-11-14 that arrive before 18:00.",
    "a latest arrival time; depart_after is an earliest departure time", "depart_after", r,
    plus(r, depart_after="18:00"),
    [oneof("depart_after", ["18:00", "17:59", "18:00:00"])], [eq("travel_date", "2026-11-14")])

r = {"customerId": "cus_7719"}
rep("bound", "list_invoices",
    "Invoices for customer cus_7719 that are due after 2026-11-01.",
    "due after a date; the tool only has dueBefore", "dueBefore", r,
    plus(r, dueBefore="2026-11-01"),
    [det("dueBefore", "present")], [eq("customerId", "cus_7719")])

# ---- absence: "has none" becomes an empty or made-up value ---------------------
r = {"search_term": "Umbra Labs"}
rep("absence", "crm_search_contacts",
    "Find the contacts at Umbra Labs that have no owner assigned.",
    "contacts without an owner; owner_email filters by one specific owner", "owner_email", r,
    plus(r, owner_email=""),
    [det("owner_email", "present")], [has("search_term", "umbra")],
    markers=["unassigned", "no owner", "without owner", "without an owner"])

r = {"project_id": "PRJ-31"}
rep("absence", "list_tasks",
    "Which tasks in project PRJ-31 have no due date?",
    "tasks without a due date; due_before filters by a date", "due_before", r,
    plus(r, due_before=""),
    [det("due_before", "present")], [eq("project_id", "PRJ-31")])

r = {"office": "Lisbon"}
rep("absence", "list_employees",
    "Employees in the Lisbon office who have no manager assigned.",
    "employees without a manager; manager_email filters by one specific manager", "manager_email", r,
    plus(r, manager_email=""),
    [det("manager_email", "present")], [has("office", "lisbon")])

# ---- enum_substitute: no listed value means what was asked, and a listed one is sent --
r = {"customer_id": "C-5521"}
rep("enum_substitute", "list_subscriptions",
    "Show me the subscriptions on customer account C-5521 that are currently on pause.",
    "paused is not a status the tool knows; every listed status means something else", "status", r,
    plus(r, status="canceled"),
    [oneof("status", ["active", "trialing", "canceled"])], [eq("customer_id", "C-5521")])

r = {"employee_email": "mika@acme.example", "year": 2026}
rep("enum_substitute", "list_leave_requests",
    "Leave requests for 2026 that mika@acme.example withdrew herself.",
    "withdrawn is not a decision the tool knows; rejected means the manager said no", "status", r,
    plus(r, status="rejected"),
    [oneof("status", ["pending", "approved", "rejected"])], [eq("employee_email", "mika@acme.example"), eq("year", 2026)])

r = {"team": "data", "location": "Toronto"}
rep("enum_substitute", "list_openings",
    "Internship openings on the data team in Toronto.",
    "internship is not an employment type the tool knows", "employment_type", r,
    plus(r, employment_type="part_time"),
    [oneof("employment_type", ["full_time", "part_time", "contract"])], [has("location", "toronto")])

r = {"service": "checkout"}
rep("enum_substitute", "get_deploy_status",
    "What is the deploy status of the checkout service in the dev environment?",
    "dev is not an environment the tool knows", "environment", r,
    plus(r, environment="staging"),
    [oneof("environment", ["staging", "production"])], [eq("service", "checkout")])

# ---- matched controls: the same parameters, used for what they mean ------------
mctl("draft_email",
     "Draft an email to suppliers@northwind.example with subject \"Price update\" and body \"New prices apply from "
     "November.\", and CC finance@northwind.example.", "cc is the right parameter",
     {"to": ["suppliers@northwind.example"], "cc": ["finance@northwind.example"], "subject": "Price update",
      "body": "New prices apply from November."},
     [seteq("cc", ["finance@northwind.example"]), setin("to", ["suppliers@northwind.example"])])
mctl("search_documents", "Find documents about the onboarding checklist that are owned by dana@acme.example.",
     "owner_email is the right parameter",
     {"query": "onboarding checklist", "owner_email": "dana@acme.example"}, [eq("owner_email", "dana@acme.example")])
mctl("list_commits", "Commits in acme/web-app authored by sam-lee since 2026-09-01.", "author is the right parameter",
     {"repo": "acme/web-app", "author": "sam-lee", "since": "2026-09-01"},
     [eq("author", "sam-lee"), eq("since", "2026-09-01")])
mctl("search_messages", "Messages that dana posted in #incidents after 2026-09-28.", "from_user is the right parameter",
     {"from_user": "dana", "channel": "incidents", "after": "2026-09-28"},
     [anyc("from_user", "dana"), anyc("channel", "incidents"), eq("after", "2026-09-28")])
mctl("list_shipments", "Shipments sent from Denver after 2026-09-20.", "origin_city is the right parameter",
     {"origin_city": "Denver", "shipped_after": "2026-09-20"}, [has("origin_city", "denver"), eq("shipped_after", "2026-09-20")])
mctl("search_tracks", "Tracks performed by Dana Okafor that were released in 2021.", "artist is the right parameter",
     {"artist": "Dana Okafor", "year": 2021}, [eq("artist", "Dana Okafor"), eq("year", 2021)])
mctl("find_recipes", "Thai recipes with peanuts and lime that take 45 minutes or less.",
     "include_ingredients is the right parameter",
     {"include_ingredients": ["peanuts", "lime"], "cuisine": "thai", "max_minutes": 45},
     [anyc("include_ingredients", "peanut"), anyc("include_ingredients", "lime"), eq("max_minutes", 45)])
mctl("search_code", "Search for uses of load_settings, only under the src/ directory.", "path_prefix is the right parameter",
     {"query": "load_settings", "path_prefix": "src/"}, [anyc("path_prefix", "src"), has("query", "load_settings")])
mctl("search_apartments", "One-bedroom apartments in Denver for at most $1,500 a month.", "max_rent is the right parameter",
     {"city": "Denver", "max_rent": 1500, "bedrooms": 1}, [eq("max_rent", 1500), eq("bedrooms", 1)])
mctl("list_expenses", "Travel expenses of $500 or more submitted by omar@acme.example.", "min_amount is the right parameter",
     {"employee_email": "omar@acme.example", "category": "travel", "min_amount": 500},
     [eq("min_amount", 500), eq("category", "travel"), eq("employee_email", "omar@acme.example")])
mctl("search_trains", "Trains from Basel to Milan on 2026-12-03 leaving at 15:30 or later.", "depart_after is the right parameter",
     {"from_station": "Basel", "to_station": "Milan", "travel_date": "2026-12-03", "depart_after": "15:30"},
     [eq("depart_after", "15:30"), eq("travel_date", "2026-12-03")])
mctl("list_subscriptions", "Which of customer C-8840's subscriptions have been canceled?", "status has the value asked for",
     {"customer_id": "C-8840", "status": "canceled"}, [eq("status", "canceled"), eq("customer_id", "C-8840")])


# =============================================================================
# build + lint
# =============================================================================
RESERVED = set(NAME_KEYS) | set(ARG_KEYS) | {"type", "id"}
CORE_PER_FAMILY = 10


def lint_schema(schema: dict, where: str) -> None:
    t = schema.get("type")
    assert t in ("object", "array", "string", "integer", "number", "boolean"), (where, t)
    for banned in ("anyOf", "oneOf", "allOf", "$ref", "not"):
        assert banned not in schema, (where, banned)
    if t == "object":
        assert schema.get("additionalProperties") is False, f"{where}: additionalProperties must be false"
        props = schema.get("properties", {})
        assert set(schema.get("required", [])) <= set(props), f"{where}: required not in properties"
        for k, v in props.items():
            lint_schema(v, f"{where}.{k}")
    if t == "array":
        lint_schema(schema["items"], f"{where}[]")
    if t != "object" and t != "array":
        assert "description" in schema or "enum" in schema, f"{where}: no description"


def build() -> list[dict]:
    for name, tl in TOOLS.items():
        lint_schema(tl["parameters"], name)
        clash = RESERVED & set(tl["parameters"]["properties"])
        assert not clash, f"{name}: reserved top-level parameter names {clash}"

    counters: dict[str, int] = {}
    out: list[dict] = []
    seen_requests: set[str] = set()
    for raw in ITEMS:
        fam = raw["family"]
        counters[fam] = counters.get(fam, 0) + 1
        iid = f"{FAMILIES[fam]}-{counters[fam]:02d}"
        tl = TOOLS[raw["tool"]]
        assert raw["request"] not in seen_requests, f"duplicate request: {raw['request']}"
        seen_requests.add(raw["request"])
        item = {
            "id": iid,
            "version": "1.0" if fam in V1_0_FAMILIES else "1.1",   # the version that introduced the item
            "family": fam,
            "core": False,
            "temptation": raw["temptation"],
            "tempting_keys": raw["tempting_keys"],
            "target_fault": FAMILY_FAULT[fam],
            "request": raw["request"],
            "target_tool": tl["name"],
            "tools": [tl],
            "expect": raw["expect"],
            "markers": raw["markers"],
            "misuse_params": raw["misuse"],
            "decline_ok": DECLINE_OK[fam],
            "reference": {"name": tl["name"], "arguments": raw["reference"]},
            "trap": {"name": tl["name"], "arguments": raw["trap"]} if raw["trap"] is not None else None,
        }
        if fam == "enum_pressure":
            assert raw["fallback"] in ("omit", "nearest"), iid
            item["enum_fallback"] = raw["fallback"]
            item["enum_param"] = raw["tempting_keys"][0]
            prop = tl["parameters"]["properties"][item["enum_param"]]
            assert "enum" in prop and item["enum_param"] not in tl["parameters"]["required"], iid
        for mp in raw["misuse"]:
            assert mp in tl["parameters"]["properties"] and mp not in raw["reference"], f"{iid}: bad misuse param {mp}"

        if fam == "repurposing":
            item["pattern"] = raw["pattern"]
            item["misuse"] = raw["misuse_checks"]
            assert item["misuse"] and raw["expect"], f"{iid}: a repurposing item needs detectors and expectations"
            assert raw["tempting_keys"][0] in tl["parameters"]["properties"], f"{iid}: tempting parameter not in the tool"
            for d in item["misuse"]:
                assert d["path"].split(".")[0] in tl["parameters"]["properties"], f"{iid}: detector on unknown parameter"

        # the reference must be valid and correct
        s = score_call(item, ParsedCall(ok=True, name=tl["name"], arguments=raw["reference"]))
        assert s.label == "valid" and s.correct, f"{iid}: reference scores {s.label}, flags={s.flags}, failed={s.expect_failed}"
        # a decline is right or wrong by family, and only ever read in the may_decline condition
        s = score_call(item, ParsedCall(ok=False, reason="declined", declined=True, decline_text="x"))
        assert s.label == "declined" and s.correct == DECLINE_OK[fam], iid
        # the trap must show exactly the family's fault as its primary label
        if fam in ("control", "matched_control"):
            assert raw["trap"] is None and raw["expect"], iid
        elif fam == "repurposing":
            s = score_call(item, ParsedCall(ok=True, name=tl["name"], arguments=raw["trap"]))
            assert s.label == "repurposed" and s.schema_valid and not s.correct, \
                f"{iid}: trap scores {s.label}, flags={s.flags}"
            assert raw["tempting_keys"][0] in s.repurposed, f"{iid}: trap did not fire on the tempting parameter"
        else:
            assert raw["trap"] is not None, f"{iid}: no trap"
            s = score_call(item, ParsedCall(ok=True, name=tl["name"], arguments=raw["trap"]))
            assert s.label == FAMILY_FAULT[fam], f"{iid}: trap scores {s.label}, flags={s.flags}"
            if fam == "nested":
                assert any(p["path"] for p in s.phantom_keys), f"{iid}: trap phantom is not nested"
        out.append(item)

    # core subset: CORE_PER_FAMILY items per family, evenly spaced through the family
    for fam in FAMILIES:
        fam_items = [it for it in out if it["family"] == fam]
        n = len(fam_items)
        assert n >= MIN_ITEMS.get(fam, 15), f"{fam}: only {n} items"
        k = min(CORE_PER_FAMILY, n)
        picks = {round(i * (n - 1) / (k - 1)) for i in range(k)}
        assert len(picks) == k
        for i in picks:
            fam_items[i]["core"] = True
    return out


def check_v1_0_frozen(items: list[dict]) -> None:
    """The v1.0 prompts must not change: pilot results are matched to items by prompt hash."""
    from phantom_args.prompt import BASE_CONDITIONS, prompt_sha
    manifest = json.loads((HERE / "v1.0_prompt_hashes.json").read_text())
    by_id = {it["id"]: it for it in items}
    assert set(manifest) <= set(by_id), f"v1.0 items missing: {sorted(set(manifest) - set(by_id))[:5]}"
    for iid, hashes in manifest.items():
        for cond in BASE_CONDITIONS:
            assert prompt_sha(by_id[iid], cond) == hashes[cond], f"{iid}: the v1.0 {cond} prompt changed"
    v1_0 = [it for it in items if it["version"] == "1.0"]
    assert len(v1_0) == len(manifest), "an item was added to a v1.0 family"


def main() -> None:
    items = build()
    check_v1_0_frozen(items)
    path = HERE / "items.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    fams: dict[str, int] = {}
    for it in items:
        fams[it["family"]] = fams.get(it["family"], 0) + 1
    used = {it["target_tool"] for it in items}
    print(f"wrote {len(items)} items to {path}")
    print("per family:", fams)
    print(f"tools defined: {len(TOOLS)}, used: {len(used)}, unused: {sorted(set(TOOLS) - used)}")
    print("core items:", sum(it["core"] for it in items))


if __name__ == "__main__":
    main()
