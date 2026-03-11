import datetime
import abc
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RawHeadline:
    """Parsed headline before saving to DB."""

    title: str
    url: str
    published_at: datetime.datetime


class BaseScraper(abc.ABC):
    """Base class for all news source scrapers."""

    slug: str
    name: str
    base_url: str

    @abc.abstractmethod
    async def fetch(self) -> list[RawHeadline]:
        """Fetch latest headlines from the source."""
        ...
