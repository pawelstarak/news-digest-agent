from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from src.config import Category, Config, get_active_categories, load_config
from src.deduplication import filter_seen, load_store, save_store
from src.email_sender import DigestSection, DigestStory, send_digest, syntheses_to_sections
from src.feed_ingestion import Article, fetch_category
from src.synthesis import Synthesis, make_synthesis_client, synthesize_article
from src.triage import triage_articles

logger = logging.getLogger(__name__)


async def _process_category(
    category: Category,
    dedup_store: dict,
    synthesis_client,
) -> tuple[str, str, list[Synthesis]]:
    logger.info("[%s] Starting category processing", category.key)

    articles = await fetch_category(category)
    logger.info("[%s] Fetched %d articles", category.key, len(articles))

    articles = filter_seen(articles, dedup_store)
    logger.info("[%s] %d articles after dedup filter", category.key, len(articles))

    selected = await triage_articles(
        category_key=category.key,
        display_name=category.display_name,
        context_hint=category.context_hint,
        articles=articles,
    )
    logger.info("[%s] Triage selected %d articles", category.key, len(selected))

    if not selected:
        return category.display_name, category.frequency, []

    synthesis_tasks = [synthesize_article(a, synthesis_client) for a in selected]
    syntheses = await asyncio.gather(*synthesis_tasks, return_exceptions=True)

    valid_syntheses: list[Synthesis] = []
    for result in syntheses:
        if isinstance(result, Exception):
            logger.error("[%s] Synthesis failed: %s", category.key, result)
        else:
            valid_syntheses.append(result)

    logger.info("[%s] Produced %d syntheses", category.key, len(valid_syntheses))
    return category.display_name, category.frequency, valid_syntheses


async def run_digest(config_path: Path | None = None) -> None:
    config = load_config(config_path)
    active_categories = get_active_categories(config)
    logger.info(
        "Active categories: %s",
        [c.key for c in active_categories],
    )

    dedup_store = load_store()
    logger.info("Loaded dedup store: %d entries", len(dedup_store))

    synthesis_client = make_synthesis_client()

    category_tasks = [
        _process_category(cat, dedup_store, synthesis_client)
        for cat in active_categories
    ]
    results = await asyncio.gather(*category_tasks, return_exceptions=True)

    all_selected_urls: list[str] = []
    category_results: list[tuple[str, str, list[Synthesis]]] = []

    for cat, result in zip(active_categories, results):
        if isinstance(result, Exception):
            logger.error("[%s] Category processing failed: %s", cat.key, result)
            continue
        display_name, frequency, syntheses = result
        category_results.append((display_name, frequency, syntheses))
        for s in syntheses:
            all_selected_urls.append(s.article.url)

    sections = syntheses_to_sections(category_results)

    total_stories = sum(len(s.stories) for s in sections)
    logger.info(
        "Digest ready: %d sections, %d total stories",
        len(sections),
        total_stories,
    )

    if sections:
        send_digest(sections)
    else:
        logger.info("No stories selected across all categories — no email sent")

    save_store(dedup_store, all_selected_urls)
    logger.info("Run complete. Dedup store updated with %d new URLs.", len(all_selected_urls))
