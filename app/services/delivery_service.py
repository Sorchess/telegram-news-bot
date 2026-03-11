"""Service that delivers new headlines to subscribers."""

import logging
from urllib.parse import urlparse

from telegram import Bot

from app.db.repos import (
    DeliveryLogRepo,
    HeadlineRepo,
    SourceRepo,
    SubscriptionRepo,
    UserRepo,
)
from app.db.session import async_session

logger = logging.getLogger(__name__)


def _short_domain(url: str) -> str:
    """Extract short domain from URL for display, e.g. 'kommersant.ru'."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _format_headline(title: str, url: str) -> str:
    domain = _short_domain(url)
    return f"• {title}\n  <a href=\"{url}\">{domain}</a>"


async def deliver_new_headlines(bot: Bot) -> int:
    """Check all subscriptions and deliver unread headlines. Returns total delivered count."""
    total = 0

    async with async_session() as session:
        subscriptions = await SubscriptionRepo.get_all_with_users(session)

        for sub in subscriptions:
            user = sub.user
            source = sub.source

            headlines = await HeadlineRepo.get_undelivered_for_user(
                session, user.id, source.id, limit=user.headlines_count
            )

            if not headlines:
                continue

            lines = [f"📰 <b>{source.name}</b> — новые заголовки:\n"]
            for h in headlines:
                lines.append(_format_headline(h.title, h.url))

            text = "\n".join(lines)
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                await DeliveryLogRepo.mark_delivered(
                    session, user.id, [h.id for h in headlines]
                )
                total += len(headlines)
            except Exception:
                logger.exception(
                    "Failed to deliver headlines to user %d", user.telegram_id
                )

    logger.info("Delivered %d headlines total", total)
    return total
