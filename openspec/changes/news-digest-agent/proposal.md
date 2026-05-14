## Why

Sorting through daily news is time-consuming and increasingly dominated by sensationalism, outrage cycles, and low-signal clickbait. This agent automates the triage and synthesis of RSS feeds across curated topic categories, delivering a high-quality morning digest via email — so the reader gets substantive, contextualized news without touching a single news website.

## What Changes

- New Python application: a scheduled Azure Functions job that runs daily
- Fetches articles from configured RSS feeds, grouped by category
- Uses Claude (Haiku for triage, Sonnet for synthesis) to filter noise and produce summaries with context
- Sends a formatted HTML email digest to a configured recipient each morning
- Categories split into daily (politics, science, nature) and weekly (music, movies, gaming)
- Article deduplication via a rolling 48h state store in Azure Blob Storage
- All feed sources and categories configured in a YAML config file

## Capabilities

### New Capabilities

- `feed-ingestion`: Fetches and normalizes RSS/Atom feed entries per category, filtering to the last 24h (or 7 days for weekly categories)
- `article-triage`: LLM-based filtering of fetched articles to select 1-3 substantively significant stories per category, rejecting sensationalism and low-impact noise
- `article-synthesis`: Fetches full article text for selected stories and uses Claude to write a summary with context and interpretation
- `digest-email`: Composes and sends a formatted HTML email digest grouping stories by category
- `deduplication`: Tracks processed article URLs in Azure Blob Storage to prevent the same story appearing in consecutive digests
- `category-config`: YAML-based configuration of feed sources, categories, frequency (daily/weekly), and delivery settings

### Modified Capabilities

## Impact

- New Azure resources: Azure Functions (Consumption Plan), Azure Blob Storage
- External dependencies: Anthropic Claude API, Gmail SMTP
- Python dependencies: `feedparser`, `httpx`, `anthropic`, `jinja2` (email templating), `pyyaml`, `azure-storage-blob`
- No existing codebase — greenfield project
