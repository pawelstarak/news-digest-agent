## 1. Project Scaffold

- [x] 1.1 Create project directory structure: `src/`, `templates/`, `tests/`
- [x] 1.2 Create `requirements.txt` with: `feedparser`, `httpx`, `anthropic`, `jinja2`, `pyyaml`, `azure-storage-blob`, `azure-functions`
- [x] 1.3 Create `config.yaml` with all 8 categories, configured feeds, and delivery settings (Europe/Warsaw timezone, 6 AM)
- [x] 1.4 Create `.env.example` documenting required environment variables: `ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `RECIPIENT_EMAIL`, `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER_NAME`

## 2. Configuration Loader

- [x] 2.1 Implement `src/config.py`: load and validate `config.yaml`, expose typed dataclasses for Category, Feed, DeliveryConfig
- [x] 2.2 Implement day-of-week check: given a timezone, determine which categories are active today (daily always, weekly only on configured day)
- [x] 2.3 Write tests for config loading and day-of-week logic (valid config, missing file, invalid YAML, weekly category day matching)

## 3. Feed Ingestion

- [x] 3.1 Implement `src/feed_ingestion.py`: async function to fetch a single RSS/Atom feed URL using `feedparser` and normalize entries to a dataclass (title, url, published, description)
- [x] 3.2 Implement time-window filtering: drop entries older than 24h (daily) or 7 days (weekly); use current time as fallback for missing published dates
- [x] 3.3 Implement category-level fetch: fetch all feeds for a category concurrently, merge and deduplicate by URL
- [x] 3.4 Write tests for feed normalization, time-window filtering, and error handling (failed fetch, missing fields)

## 4. Deduplication Store

- [x] 4.1 Implement `src/deduplication.py`: load deduplication JSON blob from Azure Blob Storage (return empty dict on missing blob or read error)
- [x] 4.2 Implement `filter_seen(articles, store)`: remove articles whose URLs are already in the store
- [x] 4.3 Implement `save_store(store, new_urls)`: add new URLs with current timestamp, trim entries older than 48h, write blob back to storage
- [x] 4.4 Write tests for load (missing blob, read error), filter, and save (trimming, write error handling)

## 5. Article Triage

- [x] 5.1 Implement `src/triage.py`: build triage prompt with category name/context hint and list of article titles + descriptions
- [x] 5.2 Call Claude Haiku with the triage prompt; parse the response to extract selected article URLs (return 0-3 articles)
- [x] 5.3 Handle edge cases: empty article list (skip LLM call), LLM returns no selections, LLM response parse error (log and return empty)
- [x] 5.4 Write tests for prompt construction, response parsing, and edge cases

## 6. Article Synthesis

- [x] 6.1 Implement `src/synthesis.py`: async function to fetch full article text via `httpx` with a browser-like User-Agent; extract main body text (strip nav/ads/footer via basic heuristics or `trafilatura` if acceptable)
- [x] 6.2 Build synthesis prompt using full article text (or RSS fallback); include note in prompt if using fallback content
- [x] 6.3 Call Claude Sonnet with prompt caching enabled on the system prompt; return structured synthesis (summary, context, implications)
- [x] 6.4 Write tests for full-text fetch (success, failure/fallback), prompt construction, and synthesis parsing

## 7. Digest Email

- [x] 7.1 Create `templates/digest.html.j2`: Jinja2 HTML email template with sections per category, story title as link, synthesis text, source name; clean readable layout with inline styles
- [x] 7.2 Implement `src/email_sender.py`: render template with digest data, compose `MIMEMultipart` email with HTML body, send via Gmail SMTP
- [x] 7.3 Implement fallback: if SMTP send fails, write digest HTML to a timestamped file in a `failed_digests/` directory and log the error
- [x] 7.4 Implement subject line generation: "News Digest — {day} {month name} {year}"
- [x] 7.5 Write tests for template rendering (multiple categories, empty categories omitted, weekly categories absent on wrong day) and subject generation

## 8. Orchestrator

- [x] 8.1 Implement `src/orchestrator.py`: main async function that wires together config → active categories → feed ingestion → dedup filter → triage → synthesis → email
- [x] 8.2 Process categories concurrently using `asyncio.gather`; collect results; skip categories with no selected stories
- [x] 8.3 Ensure dedup store is loaded once at start and saved once at end (after email send)
- [x] 8.4 Implement structured logging throughout (category name, article counts at each stage, LLM call outcomes, email send result)

## 9. Azure Function

- [x] 9.1 Create `function_app.py` with a timer trigger using Azure Functions Python v2 SDK; cron expression for 6:00 AM UTC daily
- [x] 9.2 Create `host.json` and `local.settings.json` (with placeholder values for local dev)
- [x] 9.3 Verify local invocation works via Azure Functions Core Tools (`func start` + manual trigger)  ← manual step requiring Azure Functions Core Tools
