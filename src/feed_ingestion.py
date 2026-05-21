from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import feedparser

from src.config import Category, Feed

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    url: str
    published: datetime
    description: str
    source_name: str


def _parse_entry(entry: feedparser.FeedParserDict, source_name: str) -> Article | None:
    url = entry.get("link", "").strip()
    if not url:
        return None

    title = entry.get("title", "").strip() or url

    description = (
        entry.get("summary", "")
        or entry.get("description", "")
        or ""
    ).strip()

    published: datetime
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        published = datetime(*published_parsed[:6], tzinfo=timezone.utc)
    else:
        published = datetime.now(timezone.utc)

    return Article(
        title=title,
        url=url,
        published=published,
        description=description,
        source_name=source_name,
    )


def _fetch_feed(feed: Feed, cutoff: datetime) -> list[Article]:
    try:
        parsed = feedparser.parse(feed.url)
    except Exception as exc:
        logger.error("Failed to fetch feed %s (%s): %s", feed.name, feed.url, exc)
        return []

    if parsed.get("bozo") and not parsed.get("entries"):
        logger.warning("Feed %s (%s) returned no entries (bozo=%s)", feed.name, feed.url, parsed.bozo_exception)

    articles: list[Article] = []
    for entry in parsed.get("entries", []):
        article = _parse_entry(entry, feed.name)
        if article is None:
            continue
        if article.published < cutoff:
            continue
        articles.append(article)

    logger.info("Feed %s: %d articles after time filter", feed.name, len(articles))
    return articles


async def fetch_feed_async(feed: Feed, cutoff: datetime) -> list[Article]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_feed, feed, cutoff)


async def fetch_category(category: Category) -> list[Article]:
    now = datetime.now(timezone.utc)
    if category.frequency == "weekly":
        cutoff = now - timedelta(days=7)
    else:
        cutoff = now - timedelta(hours=24)

    tasks = [fetch_feed_async(feed, cutoff) for feed in category.feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls: set[str] = set()
    merged: list[Article] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Feed fetch raised exception: %s", result)
            continue
        for article in result:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                merged.append(article)

    logger.info("Category %s: %d unique articles fetched", category.key, len(merged))
    return merged
