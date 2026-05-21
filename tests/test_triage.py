from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.feed_ingestion import Article
from src.triage import _build_prompt, _parse_response, triage_articles


def _make_article(url: str, title: str = "Test Title", desc: str = "Test description") -> Article:
    return Article(
        title=title,
        url=url,
        published=datetime.now(timezone.utc),
        description=desc,
        source_name="Source",
    )


class TestBuildPrompt:
    def test_includes_category_and_context(self) -> None:
        articles = [_make_article("https://example.com/a")]
        prompt = _build_prompt("Science", "scientific discoveries and research", articles)
        assert "Science" in prompt
        assert "scientific discoveries" in prompt

    def test_includes_article_urls_and_titles(self) -> None:
        articles = [
            _make_article("https://example.com/a", "Article A"),
            _make_article("https://example.com/b", "Article B"),
        ]
        prompt = _build_prompt("Tech", "technology", articles)
        assert "https://example.com/a" in prompt
        assert "https://example.com/b" in prompt
        assert "Article A" in prompt
        assert "Article B" in prompt

    def test_truncates_long_descriptions(self) -> None:
        long_desc = "x" * 1000
        articles = [_make_article("https://example.com/a", desc=long_desc)]
        prompt = _build_prompt("Tech", "", articles)
        assert len(prompt) < 5000  # not bloated


class TestParseResponse:
    def test_parses_valid_json_array(self) -> None:
        valid_urls = {"https://example.com/a", "https://example.com/b"}
        result = _parse_response(
            json.dumps(["https://example.com/a", "https://example.com/b"]),
            valid_urls,
        )
        assert result == ["https://example.com/a", "https://example.com/b"]

    def test_filters_invalid_urls(self) -> None:
        valid_urls = {"https://example.com/a"}
        result = _parse_response(
            json.dumps(["https://example.com/a", "https://not-in-list.com"]),
            valid_urls,
        )
        assert result == ["https://example.com/a"]

    def test_caps_at_three(self) -> None:
        valid_urls = {f"https://example.com/{i}" for i in range(10)}
        urls = [f"https://example.com/{i}" for i in range(5)]
        result = _parse_response(json.dumps(urls), valid_urls)
        assert len(result) <= 3

    def test_empty_array_returns_empty(self) -> None:
        result = _parse_response("[]", {"https://example.com/a"})
        assert result == []

    def test_no_array_in_response_returns_empty(self) -> None:
        result = _parse_response("I couldn't find any good articles today.", set())
        assert result == []

    def test_malformed_json_returns_empty(self) -> None:
        result = _parse_response("[broken json", {"https://example.com/a"})
        assert result == []

    def test_extracts_array_from_prose_response(self) -> None:
        valid_urls = {"https://example.com/a"}
        text = 'Here are the selected articles: ["https://example.com/a"] based on my analysis.'
        result = _parse_response(text, valid_urls)
        assert result == ["https://example.com/a"]


class TestTriageArticles:
    def test_empty_articles_skips_llm(self) -> None:
        async def run():
            with patch("src.triage.anthropic.AsyncAnthropic") as mock_cls:
                result = await triage_articles("tech", "Technology", "tech news", [])
            mock_cls.assert_not_called()
            return result

        result = asyncio.run(run())
        assert result == []

    def test_returns_selected_articles(self) -> None:
        articles = [
            _make_article("https://example.com/a", "Story A"),
            _make_article("https://example.com/b", "Story B"),
        ]

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["https://example.com/a"]')]

        async def run():
            with patch("src.triage.anthropic.AsyncAnthropic") as mock_cls:
                mock_client = AsyncMock()
                mock_cls.return_value = mock_client
                mock_client.messages.create = AsyncMock(return_value=mock_response)
                return await triage_articles("tech", "Technology", "tech news", articles)

        result = asyncio.run(run())
        assert len(result) == 1
        assert result[0].url == "https://example.com/a"

    def test_llm_error_returns_empty(self) -> None:
        articles = [_make_article("https://example.com/a")]

        async def run():
            with patch("src.triage.anthropic.AsyncAnthropic") as mock_cls:
                mock_client = AsyncMock()
                mock_cls.return_value = mock_client
                mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))
                return await triage_articles("tech", "Technology", "", articles)

        result = asyncio.run(run())
        assert result == []

    def test_llm_selects_nothing_returns_empty(self) -> None:
        articles = [_make_article("https://example.com/a")]

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="[]")]

        async def run():
            with patch("src.triage.anthropic.AsyncAnthropic") as mock_cls:
                mock_client = AsyncMock()
                mock_cls.return_value = mock_client
                mock_client.messages.create = AsyncMock(return_value=mock_response)
                return await triage_articles("tech", "Technology", "", articles)

        result = asyncio.run(run())
        assert result == []
