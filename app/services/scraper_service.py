"""Service that periodically fetches headlines from all sources and stores them in DB."""

import asyncio
import logging

from app.db.models import Source
from app.db.repos import HeadlineRepo, SourceRepo
from app.db.session import async_session
from app.scrapers.base import BaseScraper
from app.scrapers.registry import get_all_scrapers

logger = logging.getLogger(__name__)


async def scrape_source(scraper: BaseScraper) -> int:
    """Fetch headlines from a single source and save to DB. Returns count of new headlines."""
    raw_headlines = await scraper.fetch()
    if not raw_headlines:
        return 0

    async with async_session() as session:
        source = await SourceRepo.get_by_slug(session, scraper.slug)
        if source is None:
            source = await SourceRepo.upsert(
                session, scraper.slug, scraper.name, scraper.base_url
            )

        items = [
            {
                "source_id": source.id,
                "title": h.title,
                "url": h.url,
                "published_at": h.published_at,
            }
            for h in raw_headlines
        ]
        count = await HeadlineRepo.bulk_upsert(session, items)

    logger.info("Source %s: saved %d new headlines", scraper.slug, count)
    return count


async def scrape_all_sources() -> dict[str, int]:
    """Scrape all registered sources concurrently. Returns slug -> new count mapping."""
    scrapers = get_all_scrapers()
    results: dict[str, int] = {}

    tasks = [scrape_source(s) for s in scrapers]
    counts = await asyncio.gather(*tasks, return_exceptions=True)

    for scraper, count in zip(scrapers, counts):
        if isinstance(count, Exception):
            logger.error("Error scraping %s: %s", scraper.slug, count)
            results[scraper.slug] = 0
        else:
            results[scraper.slug] = count

    return results


async def ensure_sources_exist() -> None:
    """Make sure all source records exist in the DB."""
    scrapers = get_all_scrapers()
    async with async_session() as session:
        for scraper in scrapers:
            await SourceRepo.upsert(session, scraper.slug, scraper.name, scraper.base_url)
    logger.info("All %d sources ensured in DB", len(scrapers))
