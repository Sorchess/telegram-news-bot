"""Main entry point — builds and runs the Telegram bot application."""

import asyncio
import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
)

from app.bot.handlers import (
    cb_news_from,
    cb_set_count,
    cb_set_source,
    cb_settings,
    cb_subscribe,
    cb_unsubscribe,
    cmd_help,
    cmd_my_subs,
    cmd_news,
    cmd_news_all,
    cmd_news_from,
    cmd_settings,
    cmd_sources,
    cmd_start,
    cmd_subscribe,
    cmd_unsubscribe,
)
from app.config import settings
from app.db.models import Base
from app.db.session import engine
from app.services.delivery_service import deliver_new_headlines
from app.services.scraper_service import ensure_sources_exist, scrape_all_sources

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _create_tables() -> None:
    """Create all tables if they don't exist (for development convenience)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def periodic_scrape(context) -> None:  # type: ignore[no-untyped-def]
    """Job callback: scrape all sources."""
    logger.info("Running periodic scrape...")
    results = await scrape_all_sources()
    logger.info("Scrape results: %s", results)


async def periodic_deliver(context) -> None:  # type: ignore[no-untyped-def]
    """Job callback: deliver new headlines to subscribers."""
    logger.info("Running periodic delivery...")
    bot = context.application.bot
    total = await deliver_new_headlines(bot)
    logger.info("Delivered %d headlines", total)


async def post_init(application: Application) -> None:  # type: ignore[type-arg]
    """Called after the application is initialized."""
    await _create_tables()
    await ensure_sources_exist()

    # Run initial scrape
    logger.info("Running initial scrape...")
    await scrape_all_sources()

    # Schedule periodic jobs
    job_queue = application.job_queue
    if job_queue is not None:
        interval = settings.scrape_interval_seconds
        job_queue.run_repeating(periodic_scrape, interval=interval, first=interval)
        # Deliver new headlines shortly after each scrape
        job_queue.run_repeating(periodic_deliver, interval=interval, first=interval + 30)
        logger.info("Scheduled scrape every %d seconds", interval)


def main() -> None:
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler("news_from", cmd_news_from))
    app.add_handler(CommandHandler("news_all", cmd_news_all))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("my_subs", cmd_my_subs))

    # Callback query handlers (inline keyboard buttons)
    app.add_handler(CallbackQueryHandler(cb_news_from, pattern=r"^newsfrom:"))
    app.add_handler(CallbackQueryHandler(cb_settings, pattern=r"^settings:"))
    app.add_handler(CallbackQueryHandler(cb_set_source, pattern=r"^setsource:"))
    app.add_handler(CallbackQueryHandler(cb_set_count, pattern=r"^setcount:"))
    app.add_handler(CallbackQueryHandler(cb_subscribe, pattern=r"^sub:"))
    app.add_handler(CallbackQueryHandler(cb_unsubscribe, pattern=r"^unsub:"))

    logger.info("Starting bot...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
