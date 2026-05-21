from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Category, Feed
from src.feed_ingestion import Article, _fetch_feed, _parse_entry, fetch_category


def _make_entry(
    title: str = "Test Article",
    link: str = "https://example.com/article",
    summary: str = "Test summary",
    published_parsed: tuple | None = None,
) -> MagicMock:
    entry = MagicMock()
    entry.get = lambda key, default=None: {
        "title": title,
        "link": link,
        "summary": summary,
        "description": "",
        "published_parsed": published_parsed,
        "updated_parsed": None,
    }.get(key, default)
    return entry


def _recent_time() -> tuple:
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    return (now.year, now.month, now.day, now.hour, now.minute, now.second)


def _old_time() -> tuple:
    old = datetime.now(timezone.utc) - timedelta(hours=48)
    return (old.year, old.month, old.day, old.hour, old.minute, old.second)


class TestParseEntry:
    def test_normal_entry(self) -> None:
        entry = _make_entry(published_parsed=_recent_time())
        article = _parse_entry(entry, "Test Source")
        assert article is not None
        assert article.title == "Test Article"
        assert article.url == "https://example.com/article"
        assert article.description == "Test summary"
        assert article.source_name == "Test Source"
        assert article.published.tzinfo is not None

    def test_missing_link_returns_none(self) -> None:
        entry = _make_entry(link="")
        article = _parse_entry(entry, "Test Source")
        assert article is None

    def test_missing_published_uses_now(self) -> None:
        entry = _make_entry()  # no published_parsed
        before = datetime.now(timezone.utc)
        article = _parse_entry(entry, "Source")
        after = datetime.now(timezone.utc)
        assert article is not None
        assert before <= article.published <= after

    def test_missing_description_empty_string(self) -> None:
        entry = MagicMock()
        entry.get = lambda key, default=None: {
            "title": "Title",
            "link": "https://example.com",
            "summary": "",
            "description": "",
            "published_parsed": _recent_time(),
            "updated_parsed": None,
        }.get(key, default)
        article = _parse_entry(entry, "Source")
        assert article is not None
        assert article.description == ""


class TestFetchFeed:
    def test_filters_old_entries(self) -> None:
        feed = Feed(url="https://example.com/feed.rss", name="Test Feed")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        recent_entry = _make_entry(
            link="https://example.com/new",
            published_parsed=_recent_time(),
        )
        old_entry = _make_entry(
            link="https://example.com/old",
            published_parsed=_old_time(),
        )

        mock_parsed = MagicMock()
        mock_parsed.get.side_effect = lambda key, default=None: {
            "bozo": False,
            "entries": [recent_entry, old_entry],
        }.get(key, default)

        with patch("src.feed_ingestion.feedparser.parse", return_value=mock_parsed):
            articles = _fetch_feed(feed, cutoff)

        assert len(articles) == 1
        assert articles[0].url == "https://example.com/new"

    def test_failed_fetch_returns_empty(self) -> None:
        feed = Feed(url="https://broken.example.com/feed.rss", name="Broken Feed")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        with patch("src.feed_ingestion.feedparser.parse", side_effect=Exception("Network error")):
            articles = _fetch_feed(feed, cutoff)

        assert articles == []


class TestFetchCategory:
    def test_deduplicates_by_url(self) -> None:
        category = Category(
            key="tech",
            display_name="Tech",
            frequency="daily",
            feeds=[
                Feed(url="https://feed1.com/rss", name="Feed 1"),
                Feed(url="https://feed2.com/rss", name="Feed 2"),
            ],
        )

        shared_article = Article(
            title="Shared Story",
            url="https://example.com/shared",
            published=datetime.now(timezone.utc),
            description="desc",
            source_name="Feed 1",
        )
        unique_article = Article(
            title="Unique Story",
            url="https://example.com/unique",
            published=datetime.now(timezone.utc),
            description="desc",
            source_name="Feed 2",
        )

        async def run():
            mock_fetch = AsyncMock(side_effect=[
                [shared_article],
                [shared_article, unique_article],
            ])
            with patch("src.feed_ingestion.fetch_feed_async", mock_fetch):
                return await fetch_category(category)

        articles = asyncio.run(run())
        urls = [a.url for a in articles]
        assert len(urls) == len(set(urls))  # no duplicates
        assert "https://example.com/shared" in urls
        assert "https://example.com/unique" in urls
        assert len(articles) == 2

    def test_weekly_category_uses_7day_window(self) -> None:
        """Weekly categories should use a 7-day cutoff, not 24h."""
        category = Category(
            key="music",
            display_name="Music",
            frequency="weekly",
            feeds=[Feed(url="https://feed.com/rss", name="Feed")],
            day="friday",
        )

        captured_cutoffs: list[datetime] = []

        async def mock_fetch(feed, cutoff):
            captured_cutoffs.append(cutoff)
            return []

        async def run():
            with patch("src.feed_ingestion.fetch_feed_async", side_effect=mock_fetch):
                await fetch_category(category)

        asyncio.run(run())
        assert len(captured_cutoffs) == 1
        age = datetime.now(timezone.utc) - captured_cutoffs[0]
        assert timedelta(days=6, hours=23) < age < timedelta(days=7, hours=1)


