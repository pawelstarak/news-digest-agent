from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from src.feed_ingestion import Article

logger = logging.getLogger(__name__)

BLOB_NAME = "processed_articles.json"

# url -> ISO timestamp string of when it was stored
DeduplicationStore = dict[str, str]


def _get_blob_client():
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
    container_name = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "news-digest-state")
    service = BlobServiceClient.from_connection_string(connection_string)
    return service.get_blob_client(container=container_name, blob=BLOB_NAME)


def load_store() -> DeduplicationStore:
    try:
        client = _get_blob_client()
        data = client.download_blob().readall()
        store: DeduplicationStore = json.loads(data)
        logger.info("Deduplication store loaded: %d entries", len(store))
        return store
    except ResourceNotFoundError:
        logger.info("No deduplication blob found, starting with empty store")
        return {}
    except Exception as exc:
        logger.error("Failed to load deduplication store: %s — proceeding with empty store", exc)
        return {}


def filter_seen(articles: list[Article], store: DeduplicationStore) -> list[Article]:
    filtered = [a for a in articles if a.url not in store]
    skipped = len(articles) - len(filtered)
    if skipped:
        logger.info("Deduplication: skipped %d already-seen articles", skipped)
    return filtered


def save_store(store: DeduplicationStore, new_urls: list[str]) -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)

    updated = {
        url: ts
        for url, ts in store.items()
        if datetime.fromisoformat(ts) > cutoff
    }

    for url in new_urls:
        updated[url] = now.isoformat()

    try:
        client = _get_blob_client()
        client.upload_blob(json.dumps(updated), overwrite=True)
        logger.info("Deduplication store saved: %d entries", len(updated))
    except Exception as exc:
        logger.error("Failed to save deduplication store: %s — state for this run is lost", exc)
