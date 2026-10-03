"""Tool library for the phantom-arguments benchmark.

Every tool is invented (no real API is copied) but written the way real tool
definitions look. Every object schema, at every depth, sets
`additionalProperties: false`, so an unknown key is always a schema violation.

Reserved top-level parameter names (never used here, so that a reply such as
{"name": "...", "query": ...} can be parsed without ambiguity):
name, tool, tool_name, function, function_name, arguments, args, parameters,
params, input, tool_input, type, id.
"""
from __future__ import annotations

DATE = "Date in YYYY-MM-DD format."


def S(desc: str) -> dict:
    return {"type": "string", "description": desc}


def I(desc: str, lo: int | None = None, hi: int | None = None) -> dict:
    d: dict = {"type": "integer", "description": desc}
    if lo is not None:
        d["minimum"] = lo
    if hi is not None:
        d["maximum"] = hi
    return d


def N(desc: str) -> dict:
    return {"type": "number", "description": desc}


def B(desc: str) -> dict:
    return {"type": "boolean", "description": desc}


def E(values: list[str], desc: str) -> dict:
    return {"type": "string", "enum": list(values), "description": desc}


def A(items: dict, desc: str) -> dict:
    return {"type": "array", "description": desc, "items": items}


def O(props: dict, required: list[str] | tuple = (), desc: str | None = None) -> dict:
    d: dict = {"type": "object"}
    if desc:
        d["description"] = desc
    d["properties"] = props
    d["required"] = list(required)
    d["additionalProperties"] = False
    return d


TOOLS: dict[str, dict] = {}


def tool(name: str, description: str, props: dict, required: list[str] | tuple = ()) -> None:
    assert name not in TOOLS, name
    TOOLS[name] = {"name": name, "description": description, "parameters": O(props, required)}


# ---------------------------------------------------------------- search / news
tool("web_search",
     "Search the public web. Returns a ranked list of pages, each with title, URL, snippet, language and publication date.",
     {"query": S("The search query."),
      "safe_search": B("Filter explicit content. Defaults to true.")},
     ["query"])

tool("news_search",
     "Search news articles from the last 12 months. Returns headline, outlet, URL and publication time for each article.",
     {"query": S("Keywords to search for."),
      "from_date": S("Earliest publication date. " + DATE),
      "to_date": S("Latest publication date. " + DATE),
      "language": E(["en", "es", "fr", "de", "ja"], "Only articles written in this language (ISO 639-1 code)."),
      "sort_by": E(["relevance", "date"], "Result ordering. Defaults to relevance.")},
     ["query"])

tool("get_top_headlines",
     "Get today's top news headlines. Returns headline, outlet and URL.",
     {"count": I("How many headlines to return. Defaults to 10.", 1, 20),
      "topic": E(["business", "technology", "sports", "science", "health", "entertainment"],
                 "Restrict to one topic. Omit for all topics."),
      "country_code": S("ISO 3166-1 alpha-2 country code, e.g. US.")})

tool("search_videos",
     "Search a video platform. Returns title, channel, duration, upload date and view count.",
     {"query": S("Search terms."),
      "max_results": I("Maximum number of videos to return. Defaults to 20.", 1, 50),
      "uploaded_after": S("Only videos uploaded after this date. " + DATE),
      "duration": E(["short", "medium", "long"], "Filter by video length.")},
     ["query"])

tool("search_podcasts",
     "Search podcast shows. Returns show title, publisher, language and latest episode date.",
     {"query": S("Search terms."),
      "limit": I("Maximum number of shows to return. Defaults to 10.", 1, 50),
      "language": E(["en", "es", "fr", "de", "pt"], "Only shows in this language (ISO 639-1 code)."),
      "sort": E(["relevance", "newest"], "Result ordering. Defaults to relevance.")},
     ["query"])

tool("search_music",
     "Search the music catalogue. Returns matching items with title, artist and release year.",
     {"q": S("Search text."),
      "kind": E(["track", "album", "artist", "playlist"], "Restrict results to one kind. Omit to search all kinds."),
      "limit": I("Maximum number of results. Defaults to 20.", 1, 50)},
     ["q"])

tool("search_papers",
     "Search an index of academic papers. Returns title, authors, venue, year, citation count and open-access status.",
     {"query": S("Topic or keywords."),
      "year_from": I("Earliest publication year to include."),
      "year_to": I("Latest publication year to include."),
      "venue": S("Only papers from this conference or journal, e.g. ICML.")},
     ["query"])

# ---------------------------------------------------------------- commerce
tool("search_products",
     "Search the store catalogue. Returns matching products with name, brand, price, average rating and stock status.",
     {"query": S("What to search for."),
      "category": E(["electronics", "home", "clothing", "toys", "books"], "Restrict to one department."),
      "max_price": N("Maximum price in USD."),
      "in_stock_only": B("Only return items that are in stock. Defaults to false.")},
     ["query"])

tool("list_orders",
     "List a customer's orders. Returns order id, order date, status, item count and order total.",
     {"customer_id": S("Customer identifier, e.g. C-10293."),
      "status": E(["processing", "shipped", "delivered", "cancelled"], "Only orders with this status."),
      "placed_after": S("Only orders placed after this date. " + DATE)},
     ["customer_id"])

tool("track_shipment",
     "Get the latest tracking status and scan history for a parcel.",
     {"tracking_number": S("The carrier's tracking number."),
      "carrier": E(["ups", "fedex", "usps", "dhl"], "Carrier. Omit to auto-detect from the tracking number.")},
     ["tracking_number"])

tool("create_shipment_quote",
     "Get a price quote for shipping one or more parcels. Does not book the shipment.",
     {"parcels": A(O({"weight_kg": N("Weight in kilograms."),
                      "length_cm": N("Length in centimetres."),
                      "width_cm": N("Width in centimetres."),
                      "height_cm": N("Height in centimetres.")},
                     ["weight_kg"]),
                   "One entry per parcel."),
      "destination_country": S("ISO 3166-1 alpha-2 code of the destination country.")},
     ["parcels", "destination_country"])

# ---------------------------------------------------------------- calendar / comms
tool("list_calendar_events",
     "List events on a calendar between two dates (inclusive). Returns each event's title, start, end, location and attendees.",
     {"calendar_id": S("Identifier of the calendar."),
      "start_date": S("First day to include. " + DATE),
      "end_date": S("Last day to include. " + DATE)},
     ["calendar_id", "start_date", "end_date"])

tool("create_calendar_event",
     "Create an event on the user's primary calendar and send invitations to the attendees.",
     {"title": S("Event title."),
      "start": S("Start time, ISO 8601 with offset, e.g. 2026-03-01T09:00:00Z."),
      "end": S("End time, ISO 8601 with offset."),
      "attendees": A(O({"email": S("Attendee's email address."),
                        "optional": B("True if attendance is optional. Defaults to false.")},
                       ["email"]),
                     "People to invite."),
      "location": O({"name": S("Name of the venue or office."),
                     "room": S("Room name or number.")},
                    ["name"], "Where the event takes place.")},
     ["title", "start", "end"])

tool("post_message",
     "Post a message to a team chat channel.",
     {"channel": S("Channel name, e.g. #general."),
      "text": S("The message text.")},
     ["channel", "text"])

tool("create_email_draft",
     "Create a draft email in the user's mailbox. The draft is saved, not sent.",
     {"recipient": S("Email address of the main recipient."),
      "subject": S("Subject line."),
      "body": S("Plain-text body of the email."),
      "cc": A(S("An email address."), "Addresses to copy.")},
     ["recipient", "subject", "body"])

tool("create_poll",
     "Create a poll in the team workspace.",
     {"question": S("The poll question."),
      "options": A(O({"label": S("Text of the answer option.")}, ["label"]), "Answer options, in display order."),
      "closes_at": S("When voting closes, ISO 8601 with offset.")},
     ["question", "options"])

tool("create_contact",
     "Add a contact to the shared address book.",
     {"full_name": S("The contact's full name."),
      "company": S("Company the contact works for."),
      "emails": A(O({"address": S("Email address."),
                     "label": E(["work", "personal"], "Kind of address.")},
                    ["address"]),
                  "Email addresses."),
      "phones": A(O({"number": S("Phone number in international format."),
                     "label": E(["mobile", "work", "home"], "Kind of number.")},
                    ["number"]),
                  "Phone numbers.")},
     ["full_name"])

tool("export_contacts",
     "Export the shared address book. Returns a download link.",
     {"format": E(["csv", "json", "xlsx"], "File format of the export."),
      "fields": A({"type": "string", "enum": ["name", "email", "phone", "company", "title"]},
                  "Columns to include. Defaults to all columns.")},
     ["format"])

# ---------------------------------------------------------------- CRM / tickets / tasks
tool("crm_search_contacts",
     "Search contacts in the CRM. Returns name, job title, company, email and phone for each match.",
     {"search_term": S("Free text matched against name, email and company."),
      "owner_email": S("Only contacts owned by this sales rep.")},
     ["search_term"])

tool("crm_list_deals",
     "List deals in the sales pipeline. Returns deal name, amount, stage, owner and close date.",
     {"stage": E(["lead", "qualified", "proposal", "won", "lost"], "Only deals in this pipeline stage."),
      "ownerEmail": S("Only deals owned by this sales rep."),
      "minAmount": N("Only deals worth at least this amount, in USD."),
      "pageSize": I("Number of deals to return. Defaults to 25.", 1, 100)})

tool("search_tickets",
     "Search support tickets. Returns ticket number, subject, status, assignee and creation time.",
     {"query": S("Text to search for in the subject and messages."),
      "status": E(["open", "pending", "solved", "closed"], "Only tickets with this status."),
      "assignee_email": S("Only tickets assigned to this agent."),
      "created_after": S("Only tickets created after this date. " + DATE)},
     ["query"])

tool("create_ticket",
     "Create a support ticket in the help desk.",
     {"subject": S("Short summary of the problem."),
      "description": S("Full description of the problem."),
      "priority": E(["low", "normal", "high"], "Ticket priority. Defaults to normal."),
      "tags": A(S("A tag."), "Tags to attach to the ticket.")},
     ["subject", "description"])

tool("list_tasks",
     "List tasks in a project. Returns title, assignee, due date, priority and completion state.",
     {"project_id": S("Project identifier, e.g. PRJ-7."),
      "assignee_email": S("Only tasks assigned to this person."),
      "due_before": S("Only tasks due before this date. " + DATE),
      "order_by": E(["due_date", "priority", "created_at"], "Sort key. Defaults to created_at."),
      "limit": I("Maximum number of tasks to return. Defaults to 50.", 1, 100)},
     ["project_id"])

tool("list_repo_issues",
     "List issues in a code repository. Returns number, title, state, labels, author, assignee and comment count.",
     {"repo": S("Repository in owner/name form."),
      "state": E(["open", "closed", "all"], "Issue state. Defaults to open."),
      "labels": A(S("A label name."), "Only issues that carry all of these labels."),
      "assignee": S("Only issues assigned to this username.")},
     ["repo"])

tool("query_logs",
     "Query recent application logs. Returns matching log lines with timestamp, level and message, newest first.",
     {"service": S("Name of the service."),
      "level": E(["debug", "info", "warn", "error"], "Only lines logged at this level."),
      "since_minutes": I("How far back to look, in minutes. Defaults to 60.", 1),
      "contains": S("Only lines containing this text.")},
     ["service"])

tool("list_employees",
     "List employees from the company directory. Returns name, email, job title, department, office and start date.",
     {"department": E(["engineering", "sales", "marketing", "finance", "hr", "support"], "Only this department."),
      "office": S("Only employees based in this office, e.g. Dublin."),
      "manager_email": S("Only direct reports of this manager.")})

tool("http_check",
     "Send an HTTP GET request to a URL and report the status code and response time.",
     {"url": S("The URL to request."),
      "timeout_seconds": I("Give up after this many seconds. Defaults to 30.", 1, 60)},
     ["url"])

# ---------------------------------------------------------------- money (read-only)
tool("list_transactions",
     "List transactions on a bank account (read-only). Returns date, amount, currency, counterparty, payment method and status.",
     {"account_id": S("Account identifier, e.g. ACC-1001."),
      "since": S("Earliest transaction date to include. " + DATE),
      "until": S("Latest transaction date to include. Defaults to today. " + DATE),
      "status": E(["pending", "posted", "declined"], "Only transactions with this status.")},
     ["account_id", "since"])

tool("list_invoices",
     "List invoices for a customer (read-only). Returns invoice number, amount, status and due date.",
     {"customerId": S("Customer identifier, e.g. cus_1234."),
      "status": E(["draft", "open", "paid", "void"], "Only invoices with this status."),
      "dueBefore": S("Only invoices due before this date. " + DATE),
      "pageSize": I("Number of invoices to return. Defaults to 20.", 1, 100)},
     ["customerId"])

tool("preview_invoice",
     "Render a preview of an invoice. Nothing is created, charged or sent.",
     {"customer_id": S("Customer identifier, e.g. cus_1234."),
      "currency": E(["USD", "EUR", "GBP"], "Invoice currency."),
      "line_items": A(O({"description": S("What is being billed."),
                         "quantity": N("Number of units."),
                         "unit_price": N("Price per unit in the invoice currency.")},
                        ["description", "quantity", "unit_price"]),
                      "Invoice lines.")},
     ["customer_id", "currency", "line_items"])

tool("get_exchange_rate",
     "Get the latest mid-market exchange rate between two currencies. Returns the price of one unit of the base currency in the quote currency.",
     {"base": S("ISO 4217 code of the base currency, e.g. USD."),
      "quote": S("ISO 4217 code of the quote currency, e.g. EUR.")},
     ["base", "quote"])

tool("get_price_history",
     "Get historical prices for a listed security. Returns open, high, low, close and volume for each interval.",
     {"symbol": S("Exchange symbol of the security, e.g. IBM."),
      "start_date": S("First day to include. " + DATE),
      "end_date": S("Last day to include. " + DATE),
      "interval": E(["1d", "1wk", "1mo"], "Bar size. Defaults to 1d.")},
     ["symbol", "start_date", "end_date"])

# ---------------------------------------------------------------- weather / maps / travel
tool("get_weather_forecast",
     "Get the daily weather forecast for a place. Returns high and low temperature, chance of precipitation and wind for each day.",
     {"location": O({"city": S("City name."),
                     "country_code": S("ISO 3166-1 alpha-2 country code, e.g. FR.")},
                    ["city"], "The place to forecast."),
      "days": I("Number of days to forecast. Defaults to 3.", 1, 10),
      "units": E(["metric", "imperial"], "Unit system. Defaults to metric.")},
     ["location"])

tool("get_current_weather",
     "Get current conditions for a city. Returns temperature, humidity, wind and a short text description in English.",
     {"city": S("City name."),
      "units": E(["celsius", "fahrenheit"], "Temperature unit. Defaults to celsius.")},
     ["city"])

tool("get_directions",
     "Get step-by-step directions between two places. Returns distance, duration and a list of steps in English.",
     {"origin": S("Starting point: an address or place name."),
      "destination": S("End point: an address or place name."),
      "mode": E(["driving", "walking", "cycling", "transit"], "Travel mode. Defaults to driving.")},
     ["origin", "destination"])

tool("find_places",
     "Find points of interest near a coordinate. Returns name, address, distance, rating and opening hours.",
     {"query": S("What to look for, e.g. pharmacy."),
      "center": O({"lat": N("Latitude in decimal degrees."),
                   "lng": N("Longitude in decimal degrees.")},
                  ["lat", "lng"], "Point to search around."),
      "radius_m": I("Search radius in metres. Defaults to 1000.", 1)},
     ["query", "center"])

tool("geocode_address",
     "Convert a postal address to latitude and longitude.",
     {"address": O({"street": S("House number and street."),
                    "city": S("City or town."),
                    "postal_code": S("Postal or ZIP code."),
                    "country_code": S("ISO 3166-1 alpha-2 country code.")},
                   ["street", "city"], "The address to look up.")},
     ["address"])

tool("search_flights",
     "Search one-way flights. Returns airline, departure and arrival times, number of stops and price.",
     {"origin": S("Departure city or IATA airport code."),
      "destination": S("Arrival city or IATA airport code."),
      "departure_date": S("Day of departure. " + DATE),
      "passengers": O({"adults": I("Number of adults (12 and over).", 1),
                       "children": I("Number of children aged 2 to 11.", 0)},
                      ["adults"], "Who is travelling."),
      "cabin": E(["economy", "premium_economy", "business"], "Cabin class. Defaults to economy.")},
     ["origin", "destination", "departure_date", "passengers"])

tool("search_hotels",
     "Search hotels with rooms available for a stay. Returns name, star rating, amenities and nightly price.",
     {"city": S("City to stay in."),
      "check_in": S("Arrival date. " + DATE),
      "check_out": S("Departure date. " + DATE),
      "guests": I("Number of guests. Defaults to 2.", 1),
      "max_price_per_night": N("Maximum nightly price in the hotel's local currency.")},
     ["city", "check_in", "check_out"])

tool("search_vacation_rentals",
     "Search vacation rentals. Returns title, nightly price, bedrooms and house rules.",
     {"location": O({"city": S("City name."),
                     "country_code": S("ISO 3166-1 alpha-2 country code.")},
                    ["city"], "Where to stay."),
      "stay": O({"check_in": S("Arrival date. " + DATE),
                 "check_out": S("Departure date. " + DATE)},
                ["check_in", "check_out"], "Dates of the stay."),
      "guests": O({"adults": I("Number of adults.", 1),
                   "children": I("Number of children.", 0)},
                  ["adults"], "Who is staying.")},
     ["location", "stay", "guests"])

tool("find_restaurants",
     "Find restaurants with a free table. Returns name, cuisine, rating, price level and features such as outdoor seating.",
     {"city": S("City to search in."),
      "cuisine": S("Type of food, e.g. thai."),
      "party_size": I("Number of diners.", 1),
      "date": S("Day of the reservation. " + DATE)},
     ["city"])

# ---------------------------------------------------------------- files / library / misc
tool("list_files",
     "List the entries in a directory. Returns name, size in bytes, type and last-modified time for each entry.",
     {"path": S("Absolute path of the directory."),
      "recursive": B("Also list the contents of subdirectories. Defaults to false."),
      "include_hidden": B("Include hidden entries. Defaults to false.")},
     ["path"])

tool("search_files",
     "Search for files by name within a directory tree. Returns matching paths with size and last-modified time.",
     {"directory": S("Absolute path of the directory to search under."),
      "name_contains": S("Only files whose name contains this text."),
      "extension": S("Only files with this extension, without the dot, e.g. pdf."),
      "modified_after": S("Only files modified after this date. " + DATE)},
     ["directory"])

tool("search_catalog",
     "Search the public library catalogue. Returns title, author, publication year, format and language for each record. Provide at least one of title, author or subject.",
     {"title": S("Words from the title."),
      "author": S("Author name."),
      "subject": S("Subject heading or topic."),
      "format": E(["book", "ebook", "audiobook", "dvd"], "Only records in this format.")})

tool("check_availability",
     "Check whether a title is on the shelf. Returns the number of copies available per library branch.",
     {"isbn": S("ISBN-13 of the title."),
      "branch": E(["central", "eastside", "riverside", "university"], "Check a single branch. Omit to check all branches.")},
     ["isbn"])

tool("search_recipes",
     "Search recipes by ingredients. Returns title, full ingredient list, total time and rating.",
     {"ingredients": A(S("An ingredient."), "Ingredients the recipe should use."),
      "diet": E(["none", "vegetarian", "vegan", "gluten_free"], "Dietary restriction. Defaults to none."),
      "max_minutes": I("Maximum total cooking time in minutes.", 1)},
     ["ingredients"])

tool("search_jobs",
     "Search job postings. Returns title, company, location, salary range when published, and posting date.",
     {"keywords": S("Job title or skills to search for."),
      "location": S("City or region."),
      "remote_only": B("Only fully remote jobs. Defaults to false."),
      "posted_within_days": I("Only jobs posted within this many days.", 1)},
     ["keywords"])

tool("search_listings",
     "Search homes for sale. Returns address, price, bedrooms, bathrooms, year built and features.",
     {"city": S("City to search in."),
      "min_bedrooms": I("Minimum number of bedrooms.", 0),
      "max_price": N("Maximum asking price in USD."),
      "property_type": E(["house", "apartment", "condo", "townhouse"], "Only this kind of property.")},
     ["city"])

tool("list_appointments",
     "List a patient's appointments within a date range. Returns date, time, department and clinician.",
     {"patient_id": S("Patient identifier, e.g. P-12345."),
      "from": S("First day to include. " + DATE),
      "to": S("Last day to include. " + DATE),
      "department": E(["cardiology", "dermatology", "orthopedics", "pediatrics", "radiology"], "Only this department.")},
     ["patient_id", "from", "to"])

tool("search_courses",
     "Search the university course catalogue. Returns course code, title, level, term, meeting days and delivery mode.",
     {"subject": S("Subject area, e.g. statistics."),
      "level": E(["introductory", "intermediate", "advanced"], "Course level."),
      "term": E(["fall", "spring", "summer"], "Term in which the course is offered.")},
     ["subject"])

tool("get_sensor_readings",
     "Get time-series readings from a building sensor. Returns timestamped values.",
     {"device_id": S("Identifier of the sensor device."),
      "metric": E(["temperature", "humidity", "co2", "pressure"], "Which measurement to return."),
      "start_time": S("Start of the window, ISO 8601 with offset."),
      "end_time": S("End of the window, ISO 8601 with offset."),
      "resolution": E(["raw", "1m", "15m", "1h"], "Aggregation interval. Defaults to raw.")},
     ["device_id", "metric", "start_time", "end_time"])

tool("summarize_document",
     "Summarize a stored document. The summary is written in the document's own language.",
     {"document_id": S("Identifier of the document, e.g. DOC-1001."),
      "max_words": I("Upper bound on the summary length, in words.", 1),
      "style": E(["bullets", "paragraph"], "Layout of the summary. Defaults to paragraph.")},
     ["document_id"])

tool("translate_text",
     "Translate text into another language.",
     {"text": S("The text to translate."),
      "target_language": E(["en", "es", "fr", "de", "it", "pt", "ja", "zh"], "Language to translate into (ISO 639-1 code)."),
      "formality": E(["default", "formal", "informal"], "Register of the translation. Defaults to default.")},
     ["text", "target_language"])

tool("run_report",
     "Run an analytics report over a date range. Returns one row per group.",
     {"metric": E(["signups", "active_users", "revenue", "churn"], "What to measure."),
      "group_by": E(["day", "week", "country", "device"], "How to break the metric down."),
      "date_range": O({"start": S("First day. " + DATE), "end": S("Last day. " + DATE)},
                      ["start", "end"], "Reporting period (inclusive)."),
      "filters": O({"country": S("ISO 3166-1 alpha-2 country code."),
                    "device": E(["desktop", "mobile", "tablet"], "Device category.")},
                   [], "Optional filters.")},
     ["metric", "date_range"])


# =============================================================================
# v1.1 additions. Nothing above this line may change: the v1.0 prompts are
# hashed (data/v1.0_prompt_hashes.json) and the builder checks them.
#
# Each tool below has one parameter whose description says exactly what it
# means, and that meaning is close to, but not the same as, something a user
# may ask for.
# =============================================================================
TIME = "Time in HH:MM, 24-hour."

tool("draft_email",
     "Create a draft email in the user's mailbox. The draft is saved, not sent.",
     {"to": A(S("Email address."), "Addresses of the main recipients."),
      "cc": A(S("Email address."), "Addresses to copy. Every recipient of the email can see who is copied."),
      "subject": S("Subject line."),
      "body": S("Plain-text body of the email.")},
     ["to", "subject", "body"])

tool("search_documents",
     "Search documents in the shared drive. Returns title, owner, last-modified time and link.",
     {"query": S("Text to search for in titles and content."),
      "owner_email": S("Only documents owned by this person."),
      "modified_after": S("Only documents modified after this date. " + DATE)},
     ["query"])

tool("list_commits",
     "List commits on a repository's default branch, newest first. Returns hash, author, date and message.",
     {"repo": S("Repository as owner/name."),
      "author": S("Only commits authored by this username."),
      "since": S("Only commits on or after this date. " + DATE),
      "until": S("Only commits on or before this date. " + DATE)},
     ["repo"])

tool("search_messages",
     "Search messages in the team chat. Returns sender, channel, time and text.",
     {"query": S("Text to search for in message bodies."),
      "from_user": S("Only messages sent by this user handle, without the @."),
      "channel": S("Only messages posted in this channel, without the #."),
      "after": S("Only messages posted after this date. " + DATE)},
     [])

tool("list_shipments",
     "List outbound shipments. Returns tracking number, origin, destination, carrier and status.",
     {"origin_city": S("Only shipments sent from this city."),
      "carrier": E(["ups", "fedex", "dhl"], "Only shipments handled by this carrier."),
      "shipped_after": S("Only shipments sent after this date. " + DATE)},
     [])

tool("search_tracks",
     "Search the music catalogue for tracks. Returns title, performing artist, album and year.",
     {"title": S("Words to match in the track title."),
      "artist": S("Only tracks performed by this artist."),
      "year": I("Only tracks released in this year.")},
     [])

tool("search_books",
     "Search the library catalogue. Returns title, author, genre, year and availability.",
     {"author": S("Only books written by this author."),
      "genre": E(["biography", "history", "science", "fiction"], "Only books of this genre."),
      "published_after": I("Only books published after this year.")},
     [])

tool("search_matches",
     "Search football match records. Returns date, teams, score, referee and line-ups.",
     {"player": S("Only matches in which this player appeared."),
      "season": I("Only matches of the season that started in this year."),
      "competition": S("Only matches of this competition, e.g. league or cup.")},
     [])

tool("search_accessories",
     "Search the store's accessories catalogue. Returns product name, category, brand, price and stock.",
     {"category": E(["charger", "case", "cable", "dock"], "Only products in this category."),
      "brand": S("Only products made by this brand."),
      "max_price": N("Maximum price in USD.")},
     [])

tool("find_classes",
     "Find classes in the course catalogue. Returns code, title, subject, level and instructor.",
     {"subject": S("Only classes that belong to this subject area, e.g. physics."),
      "level": E(["intro", "intermediate", "advanced"], "Only classes at this level."),
      "instructor": S("Only classes taught by this instructor.")},
     [])

tool("find_recipes",
     "Find recipes. Returns name, cuisine, ingredients and total time.",
     {"include_ingredients": A(S("Ingredient name."), "Ingredients the recipe must contain."),
      "cuisine": S("Only recipes of this cuisine, e.g. thai."),
      "max_minutes": I("Maximum total time in minutes.", 1)},
     [])

tool("search_photos",
     "Search the photo library. Returns file name, date taken, album and tags.",
     {"tags": A(S("Tag."), "Only photos that carry every one of these tags."),
      "taken_after": S("Only photos taken after this date. " + DATE),
      "album": S("Only photos in this album.")},
     [])

tool("search_code",
     "Search the repository's source code. Returns file path, line number and the matching line.",
     {"query": S("Text or regular expression to search for."),
      "path_prefix": S("Only files whose path starts with this prefix, e.g. src/."),
      "language": E(["python", "typescript", "go", "java"], "Only files written in this language.")},
     ["query"])

tool("search_apartments",
     "Search apartments for rent. Returns address, monthly rent, bedrooms and availability date.",
     {"city": S("City to search in."),
      "max_rent": N("Maximum monthly rent in USD."),
      "bedrooms": I("Number of bedrooms.", 0),
      "pets_allowed": B("If true, only apartments that allow pets.")},
     ["city"])

tool("list_expenses",
     "List submitted expense claims. Returns employee, category, amount, date and approval state.",
     {"employee_email": S("Only expenses submitted by this employee."),
      "category": E(["travel", "meals", "software", "other"], "Only expenses in this category."),
      "min_amount": N("Only expenses of at least this amount, in USD."),
      "submitted_after": S("Only expenses submitted after this date. " + DATE)},
     [])

tool("list_folder_contents",
     "List the files in a folder. Returns path, size and last-modified time.",
     {"folder": S("Folder path."),
      "older_than_days": I("Only files last modified more than this many days ago. Omit to list every file.", 0),
      "extension": S("Only files with this extension, e.g. csv.")},
     ["folder"])

tool("search_trains",
     "Search train connections. Returns departure time, arrival time, changes and price.",
     {"from_station": S("Departure station."),
      "to_station": S("Arrival station."),
      "travel_date": S(DATE),
      "depart_after": S("Only trains that depart at or after this time. " + TIME)},
     ["from_station", "to_station", "travel_date"])

tool("list_subscriptions",
     "List a customer's subscriptions. Returns plan, status, start date and next billing date.",
     {"customer_id": S("Customer identifier, e.g. C-10293."),
      "status": E(["active", "trialing", "canceled"],
                  "Only subscriptions with this status. active: billing normally. trialing: in a free trial. "
                  "canceled: ended by the customer or by us."),
      "plan": S("Only subscriptions to this plan.")},
     ["customer_id"])

tool("list_leave_requests",
     "List leave requests. Returns employee, dates, leave kind and decision.",
     {"employee_email": S("Only requests made by this employee."),
      "status": E(["pending", "approved", "rejected"],
                  "Only requests with this decision. pending: no decision yet. approved or rejected: decided by the manager."),
      "year": I("Only requests for leave in this year.")},
     [])

tool("list_openings",
     "List open positions. Returns title, team, location and employment type.",
     {"team": S("Only positions on this team."),
      "employment_type": E(["full_time", "part_time", "contract"],
                           "Only positions of this employment type. full_time and part_time: permanent "
                           "employees. contract: external contractors on a fixed term."),
      "location": S("Only positions based in this city.")},
     [])

tool("get_deploy_status",
     "Show the latest deploy of a service in each environment. Returns environment, version, time, who deployed it and health.",
     {"service": S("Name of the service."),
      "environment": E(["staging", "production"],
                       "Only this environment. staging: the shared pre-release environment. production: live "
                       "traffic. Omit to get every environment.")},
     ["service"])
