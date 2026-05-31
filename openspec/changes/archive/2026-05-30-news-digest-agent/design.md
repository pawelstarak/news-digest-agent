## Context

Greenfield Python application to be hosted on Azure. The owner receives daily email news digests. Key constraints: minimal operational overhead, low cost (free Azure tier where possible, ~$15/month Claude API budget), and high output quality (no sensationalism, substantive context).

The system runs on a schedule once per day in the morning. Some categories (entertainment: music, movies, gaming) run weekly instead of daily. There is no web UI, no user accounts, and no interactive interface — it's a personal automation tool.

## Goals / Non-Goals

**Goals:**
- Reliable daily/weekly digest delivery via email
- LLM-based noise filtering that catches substantive stories regardless of who they're about
- Full-text article synthesis with context (not just headline rephrasing)
- Simple YAML config for feed management
- Azure Functions hosting on the free consumption plan
- Deduplication across consecutive runs

**Non-Goals:**
- Multi-user support
- Web dashboard or UI
- Real-time or on-demand digests
- Social media sources (RSS only for now)
- Feedback loops or personalization learning
- Archiving or search over past digests

## Decisions

### D1: Azure Functions (Consumption Plan) over Container Apps

Azure Functions with a timer trigger is the right fit for a single scheduled daily job. The Consumption Plan is free for this workload (one daily invocation, ~5-10 min runtime). Container Apps adds unnecessary complexity and cost for what is essentially a cron job.

**Alternative considered:** GitHub Actions scheduled workflow — simpler local dev story but tighter to GitHub, harder to manage secrets, and less appropriate for a standalone Azure-hosted service.

### D2: Two-tier Claude model strategy (Haiku triage + Sonnet synthesis)

Triage is a bulk classification task (40 headlines → pick 3-5). Haiku is fast and cheap enough ($0.80/MTok in) and sufficiently accurate for this. Synthesis requires nuanced writing with context — Sonnet 4.6 is used here for quality. This brings estimated monthly Claude API spend to ~$10-15.

**Alternative considered:** Sonnet for everything — doubles cost without meaningful improvement on the triage step.

### D3: Prompt caching on synthesis system prompt

The synthesis system prompt (persona, anti-clickbait instructions, output format) is identical across all story calls per run. Enabling Anthropic prompt caching on this block reduces input token cost by ~90% on cached content after the first call.

### D4: Gmail SMTP for email delivery

The recipient is a single Gmail user. Using Gmail SMTP with an App Password is the simplest, most reliable option — no Azure Communication Services domain setup, no SendGrid account. Appropriate for a personal tool.

**Alternative considered:** Azure Communication Services Email — free tier exists but requires custom domain provisioning and more complex setup for zero added value at this scale.

### D5: Azure Blob Storage for deduplication state

A single JSON blob (`processed_articles.json`) holds a rolling set of article URLs seen in the last 48 hours. On each run: load the blob, filter already-seen URLs from candidates, process remaining, append new URLs, trim entries older than 48h, write back.

**Alternative considered:** No deduplication — acceptable for a prototype but a story published at 5:58 AM will appear in two consecutive digests without it. Small complexity, real value.

### D6: Jinja2 for email HTML templating

A Jinja2 template gives clean separation between digest content (categories, stories, summaries) and email formatting (HTML layout, inline styles). Makes the email structure easy to iterate without touching Python logic.

### D7: Category frequency in config (daily vs weekly)

Each category in the YAML config specifies `frequency: daily` or `frequency: weekly` with an optional `day:` field. The Azure Function runs daily; it checks each category's frequency against the current day of week and skips weekly categories on non-matching days.

```yaml
categories:
  world_politics:
    frequency: daily
    feeds:
      - url: https://feeds.bbci.co.uk/news/world/rss.xml
        name: BBC World

  rock_metal:
    frequency: weekly
    day: friday
    feeds:
      - url: https://www.loudwire.com/feed/
        name: Loudwire
```

## Risks / Trade-offs

**[Full article fetching may fail for some sources]** → Mitigation: Fall back to RSS description/summary if HTTP fetch fails or returns a paywall response. Log the failure but don't abort the category.

**[Claude API latency on many sequential calls]** → Mitigation: Process categories concurrently using `asyncio`. Each category's triage + synthesis calls are independent.

**[Gmail SMTP rate limits or app password revocation]** → Mitigation: Low volume (1 email/day) is well within Gmail limits. App password is stored as a Function App environment variable. Document recovery steps.

**[LLM triage misses a story or includes noise]** → Accepted trade-off. The goal is "good enough" daily, not perfect. Prompt iteration can tune this over time.

**[Azure Function cold starts adding latency]** → Acceptable. The digest email arriving 30 seconds later than scheduled is not a problem.

## Migration Plan

1. Provision Azure Function App (Consumption Plan, Python 3.11) and Azure Storage Account
2. Set environment variables: `ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `RECIPIENT_EMAIL`, `AZURE_STORAGE_CONNECTION_STRING`
3. Deploy function code via Azure Functions Core Tools or GitHub Actions
4. Configure timer trigger cron expression (e.g., `0 0 6 * * *` for 6 AM UTC)
5. Validate with a manual invocation before enabling the timer

Rollback: disable the timer trigger. No stateful resources need cleanup beyond the blob storage (which can be left as-is).

## Open Questions

- What timezone should "6 AM" refer to? (UTC vs Europe/Warsaw) — Azure Functions timer uses UTC by default; configure accordingly.
- Should the weekly categories run on the same email as daily categories (combined digest), or a separate email? Initial assumption: combined, clearly sectioned.
