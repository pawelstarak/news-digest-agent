from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.deduplication import DeduplicationStore, filter_seen, load_store, save_store
from src.feed_ingestion import Article


def _make_article(url: str) -> Article:
    return Article(
        title="Title",
        url=url,
        published=datetime.now(timezone.utc),
        description="desc",
        source_name="Source",
    )


def _ts(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


class TestLoadStore:
    def test_returns_empty_on_missing_blob(self) -> None:
        from azure.core.exceptions import ResourceNotFoundError

        mock_client = MagicMock()
        mock_client.download_blob.side_effect = ResourceNotFoundError("Not found")

        with patch("src.deduplication._get_blob_client", return_value=mock_client):
            store = load_store()

        assert store == {}

    def test_returns_empty_on_read_error(self) -> None:
        mock_client = MagicMock()
        mock_client.download_blob.side_effect = Exception("Storage unavailable")

        with patch("src.deduplication._get_blob_client", return_value=mock_client):
            store = load_store()

        assert store == {}

    def test_loads_existing_store(self) -> None:
        data = {
            "https://example.com/article1": _ts(10),
            "https://example.com/article2": _ts(20),
        }
        mock_blob = MagicMock()
        mock_blob.readall.return_value = json.dumps(data).encode()
        mock_client = MagicMock()
        mock_client.download_blob.return_value = mock_blob

        with patch("src.deduplication._get_blob_client", return_value=mock_client):
            store = load_store()

        assert store == data


class TestFilterSeen:
    def test_removes_seen_articles(self) -> None:
        store: DeduplicationStore = {
            "https://example.com/old": _ts(5),
        }
        articles = [
            _make_article("https://example.com/old"),
            _make_article("https://example.com/new"),
        ]
        result = filter_seen(articles, store)
        assert len(result) == 1
        assert result[0].url == "https://example.com/new"

    def test_empty_store_keeps_all(self) -> None:
        articles = [_make_article(f"https://example.com/{i}") for i in range(5)]
        result = filter_seen(articles, {})
        assert len(result) == 5

    def test_empty_articles_returns_empty(self) -> None:
        result = filter_seen([], {"https://example.com/a": _ts(1)})
        assert result == []


class TestSaveStore:
    def test_adds_new_urls_with_timestamp(self) -> None:
        store: DeduplicationStore = {}
        new_urls = ["https://example.com/a", "https://example.com/b"]

        uploaded_data: list[str] = []
        mock_client = MagicMock()
        mock_client.upload_blob.side_effect = lambda data, **kw: uploaded_data.append(data)

        with patch("src.deduplication._get_blob_client", return_value=mock_client):
            save_store(store, new_urls)

        saved = json.loads(uploaded_data[0])
        assert "https://example.com/a" in saved
        assert "https://example.com/b" in saved

    def test_trims_entries_older_than_48h(self) -> None:
        store: DeduplicationStore = {
            "https://example.com/recent": _ts(10),
            "https://example.com/expired": _ts(50),  # older than 48h
        }

        uploaded_data: list[str] = []
        mock_client = MagicMock()
        mock_client.upload_blob.side_effect = lambda data, **kw: uploaded_data.append(data)

        with patch("src.deduplication._get_blob_client", return_value=mock_client):
            save_store(store, [])

        saved = json.loads(uploaded_data[0])
        assert "https://example.com/recent" in saved
        assert "https://example.com/expired" not in saved

    def test_write_error_is_logged_not_raised(self) -> None:
        mock_client = MagicMock()
        mock_client.upload_blob.side_effect = Exception("Write failed")

        with patch("src.deduplication._get_blob_client", return_value=mock_client):
            save_store({}, ["https://example.com/a"])  # should not raise
