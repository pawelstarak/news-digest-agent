from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.feed_ingestion import Article
from src.synthesis import Synthesis, _build_synthesis_prompt, _fetch_full_text, synthesize_article


def _make_article(
    url: str = "https://example.com/story",
    title: str = "Test Story",
    description: str = "Test RSS description.",
) -> Article:
    return Article(
        title=title,
        url=url,
        published=datetime.now(timezone.utc),
        description=description,
        source_name="Test Source",
    )


class TestFetchFullText:
    def test_returns_extracted_text_on_success(self) -> None:
        html = "<html><body><article>" + ("Word " * 200) + "</article></body></html>"
        extracted = "Word " * 200

        async def run():
            mock_response = MagicMock()
            mock_response.text = html
            mock_response.raise_for_status = MagicMock()

            with patch("src.synthesis.trafilatura.extract", return_value=extracted):
                with patch("httpx.AsyncClient") as mock_cls:
                    mock_client = AsyncMock()
                    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                    mock_client.get = AsyncMock(return_value=mock_response)
                    return await _fetch_full_text("https://example.com/story")

        result = asyncio.run(run())
        assert result is not None
        assert len(result) > 50

    def test_returns_none_on_http_error(self) -> None:
        async def run():
            with patch("httpx.AsyncClient") as mock_cls:
                mock_client = AsyncMock()
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
                return await _fetch_full_text("https://broken.example.com/story")

        result = asyncio.run(run())
        assert result is None

    def test_returns_none_when_extracted_text_too_short(self) -> None:
        async def run():
            mock_response = MagicMock()
            mock_response.text = "<html><body>Short</body></html>"
            mock_response.raise_for_status = MagicMock()

            with patch("src.synthesis.trafilatura.extract", return_value="Short text"):
                with patch("httpx.AsyncClient") as mock_cls:
                    mock_client = AsyncMock()
                    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                    mock_client.get = AsyncMock(return_value=mock_response)
                    return await _fetch_full_text("https://example.com/short")

        result = asyncio.run(run())
        assert result is None


class TestBuildSynthesisPrompt:
    def test_uses_full_text_when_available(self) -> None:
        article = _make_article()
        prompt, used_fallback = _build_synthesis_prompt(article, "Full article content here.")
        assert "Full article content" in prompt
        assert used_fallback is False

    def test_uses_rss_description_as_fallback(self) -> None:
        article = _make_article(description="RSS description text")
        prompt, used_fallback = _build_synthesis_prompt(article, None)
        assert "RSS description text" in prompt
        assert used_fallback is True

    def test_fallback_notes_limited_content(self) -> None:
        article = _make_article()
        prompt, _ = _build_synthesis_prompt(article, None)
        assert "unavailable" in prompt.lower() or "rss" in prompt.lower()


class TestSynthesizeArticle:
    def test_synthesizes_with_full_text(self) -> None:
        article = _make_article()
        full_text = "Full article content. " * 50

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary.\n\nContext.\n\nImplications.")]

        async def run():
            mock_anthropic_client = AsyncMock()
            mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

            with patch("src.synthesis._fetch_full_text", return_value=full_text):
                return await synthesize_article(article, mock_anthropic_client)

        result = asyncio.run(run())
        assert isinstance(result, Synthesis)
        assert result.used_fallback is False
        assert "Summary" in result.text

    def test_synthesizes_with_rss_fallback(self) -> None:
        article = _make_article()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary from RSS.\n\nContext.\n\nImplications.")]

        async def run():
            mock_anthropic_client = AsyncMock()
            mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

            with patch("src.synthesis._fetch_full_text", return_value=None):
                return await synthesize_article(article, mock_anthropic_client)

        result = asyncio.run(run())
        assert result.used_fallback is True

    def test_uses_prompt_caching_on_system_prompt(self) -> None:
        article = _make_article()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Some synthesis text.")]

        captured_calls: list[dict] = []

        async def run():
            async def mock_create(**kwargs):
                captured_calls.append(kwargs)
                return mock_response

            mock_client = AsyncMock()
            mock_client.messages.create = mock_create

            with patch("src.synthesis._fetch_full_text", return_value=None):
                await synthesize_article(article, mock_client)

        asyncio.run(run())
        assert len(captured_calls) == 1
        system = captured_calls[0]["system"]
        assert isinstance(system, list)
        assert any(
            block.get("cache_control", {}).get("type") == "ephemeral"
            for block in system
            if isinstance(block, dict)
        )
