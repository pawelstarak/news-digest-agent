from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import anthropic
import httpx
import trafilatura

from src.feed_ingestion import Article

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a thoughtful editorial analyst writing for a personal news digest. \
Your role is to synthesize news articles into clear, informative prose that goes beyond the headline.

For each article, produce exactly three paragraphs:
1. **Summary**: What happened, stated factually and concisely. Do NOT repeat the headline verbatim.
2. **Context**: Why this matters — relevant background, what led to this, how it fits into a broader pattern.
3. **Implications**: What might happen next, what the consequences or significance are.

Rules:
- Write in plain, direct prose. No bullet points.
- Never use clickbait or emotionally manipulative language.
- Do not include the journalist's speculation unless clearly attributed with "according to" or similar.
- If synthesizing from limited RSS text, say so briefly at the end of the summary paragraph (e.g., "Note: synthesized from limited feed content.").
- Keep total length to 200-300 words."""

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


@dataclass
class Synthesis:
    article: Article
    text: str
    used_fallback: bool


async def _fetch_full_text(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=_HEADERS) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception as exc:
        logger.warning("Failed to fetch full text for %s: %s", url, exc)
        return None

    text = trafilatura.extract(html, include_comments=False, include_tables=False)
    if not text or len(text.strip()) < 100:
        logger.warning("Extracted text too short for %s, will use RSS fallback", url)
        return None

    return text.strip()


def _build_synthesis_prompt(article: Article, full_text: str | None) -> tuple[str, bool]:
    if full_text:
        content = f"Article title: {article.title}\n\nArticle text:\n{full_text[:8000]}"
        used_fallback = False
    else:
        content = (
            f"Article title: {article.title}\n\n"
            f"RSS summary (full text unavailable):\n{article.description or '(no description available)'}"
        )
        used_fallback = True
    return content, used_fallback


async def synthesize_article(
    article: Article,
    client: anthropic.AsyncAnthropic,
) -> Synthesis:
    full_text = await _fetch_full_text(article.url)
    prompt, used_fallback = _build_synthesis_prompt(article, full_text)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
    except Exception as exc:
        logger.error("Synthesis LLM call failed for %s: %s", article.url, exc)
        text = article.description or article.title

    logger.info(
        "Synthesized: %s (fallback=%s, chars=%d)",
        article.url,
        used_fallback,
        len(text),
    )
    return Synthesis(article=article, text=text, used_fallback=used_fallback)


def make_synthesis_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
