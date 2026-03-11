"""Helper utilities shared across bot handlers."""

from urllib.parse import urlparse

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import Source


def short_domain(url: str) -> str:
    """Extract short domain from URL for display."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host


def format_headline(title: str, url: str) -> str:
    domain = short_domain(url)
    return f"• {title}\n  <a href=\"{url}\">{domain}</a>"


def sources_keyboard(
    sources: list[Source], callback_prefix: str
) -> InlineKeyboardMarkup:
    """Build an inline keyboard with one button per source."""
    buttons = [
        [InlineKeyboardButton(f"{s.name}", callback_data=f"{callback_prefix}:{s.slug}")]
        for s in sources
    ]
    return InlineKeyboardMarkup(buttons)
