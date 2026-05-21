from __future__ import annotations

import json
import logging
import os

import anthropic

from src.feed_ingestion import Article

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an editorial assistant helping curate a personal news digest. \
Your job is to select the most substantively significant articles from a list.

Selection criteria — INCLUDE stories that:
- Report concrete decisions, events, or findings with real-world consequences
- Involve scientific discoveries or policy changes with broad societal impact
- Represent genuinely novel or important developments in their domain

Selection criteria — EXCLUDE stories that:
- Are driven primarily by sensationalism, outrage, or emotional manipulation
- Focus on celebrity drama, personal conflicts, or social media controversies with no broader consequence
- Derive significance only from who said something (not what was decided or happened)
- Are opinion pieces, editorials, or pure speculation presented as news

Select between 0 and 3 articles. If no articles meet the bar, return an empty list."""


def _build_prompt(category_name: str, context_hint: str, articles: list[Article]) -> str:
    lines = [
        f"Category: {category_name}",
        f"Context: {context_hint}" if context_hint else "",
        "",
        "Articles to evaluate:",
    ]
    for i, article in enumerate(articles, 1):
        lines.append(f"\n[{i}] URL: {article.url}")
        lines.append(f"    Title: {article.title}")
        if article.description:
            desc = article.description[:300].replace("\n", " ")
            lines.append(f"    Description: {desc}")

    lines.append(
        "\nRespond with a JSON array of selected article URLs only. Example: "
        '["https://example.com/a", "https://example.com/b"]\n'
        "If none qualify, respond with: []"
    )
    return "\n".join(line for line in lines if line is not None)


def _parse_response(text: str, valid_urls: set[str]) -> list[str]:
    text = text.strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        logger.warning("Triage response did not contain a JSON array: %r", text[:200])
        return []

    try:
        selected = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse triage JSON response: %s", exc)
        return []

    if not isinstance(selected, list):
        logger.warning("Triage response JSON is not a list")
        return []

    valid = [url for url in selected if isinstance(url, str) and url in valid_urls]
    return valid[:3]


async def triage_articles(
    category_key: str,
    display_name: str,
    context_hint: str,
    articles: list[Article],
) -> list[Article]:
    if not articles:
        logger.info("Triage %s: no articles to evaluate", category_key)
        return []

    url_to_article = {a.url: a for a in articles}
    prompt = _build_prompt(display_name, context_hint, articles)

    client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
    except Exception as exc:
        logger.error("Triage LLM call failed for category %s: %s", category_key, exc)
        return []

    selected_urls = _parse_response(text, set(url_to_article.keys()))

    if not selected_urls:
        logger.info("Triage %s: no articles selected", category_key)
        return []

    selected = [url_to_article[url] for url in selected_urls if url in url_to_article]
    logger.info("Triage %s: selected %d/%d articles", category_key, len(selected), len(articles))
    return selected
