"""RSS-based scraper — works for most sources that provide RSS/Atom feeds."""

import datetime
import logging
from email.utils import parsedate_to_datetime
from typing import Any

import aiohttp
import feedparser

from app.scrapers.base import BaseScraper, RawHeadline

logger = logging.getLogger(__name__)


class RssScraper(BaseScraper):
    """Generic RSS/Atom feed scraper."""

    def __init__(self, slug: str, name: str, base_url: str, feed_url: str) -> None:
        self.slug = slug
        self.name = name
        self.base_url = base_url
        self.feed_url = feed_url

    async def fetch(self) -> list[RawHeadline]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.feed_url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": "NewsBotAggregator/1.0"},
                ) as resp:
                    raw = await resp.text()
        except Exception:
            logger.exception("Failed to fetch RSS feed %s", self.feed_url)
            return []

        feed = feedparser.parse(raw)
        headlines: list[RawHeadline] = []

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            published_at = self._parse_date(entry)
            headlines.append(RawHeadline(title=title, url=link, published_at=published_at))

        logger.info("Fetched %d headlines from %s", len(headlines), self.slug)
        return headlines

    @staticmethod
    def _parse_date(entry: Any) -> datetime.datetime:
        """Try multiple date fields; fall back to now()."""
        for field in ("published", "updated"):
            raw = entry.get(field)
            if raw:
                try:
                    return parsedate_to_datetime(raw)
                except Exception:
                    pass

        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed:
            try:
                return datetime.datetime(*parsed[:6], tzinfo=datetime.timezone.utc)
            except Exception:
                pass

        return datetime.datetime.now(datetime.timezone.utc)
