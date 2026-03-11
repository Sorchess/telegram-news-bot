"""Registry of all available news source scrapers.

Sources:
  1. Reuters (international, English)
  2. BBC News (international, English)
  3. Коммерсантъ (Russian, financial/business)
  4. РБК (Russian, business/finance)
"""

from app.scrapers.base import BaseScraper
from app.scrapers.rss import RssScraper


def get_all_scrapers() -> list[BaseScraper]:
    return [
        RssScraper(
            slug="reuters",
            name="Reuters",
            base_url="https://www.reuters.com",
            feed_url="https://www.reuters.com/rssFeed/worldNews/",
        ),
        RssScraper(
            slug="bbc",
            name="BBC News",
            base_url="https://www.bbc.com",
            feed_url="https://feeds.bbci.co.uk/news/rss.xml",
        ),
        RssScraper(
            slug="kommersant",
            name="Коммерсантъ",
            base_url="https://www.kommersant.ru",
            feed_url="https://www.kommersant.ru/RSS/news.xml",
        ),
        RssScraper(
            slug="rbc",
            name="РБК",
            base_url="https://www.rbc.ru",
            feed_url="https://rssexport.rbc.ru/rbcnews/news/20/full.rss",
        ),
    ]


def get_scraper_map() -> dict[str, BaseScraper]:
    return {s.slug: s for s in get_all_scrapers()}
